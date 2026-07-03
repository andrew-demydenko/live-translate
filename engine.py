# Translation engine: audio capture, Gemini Live API streaming, playback.

import asyncio
import threading

import numpy as np
import sounddevice as sd
import scipy.signal
from google import genai
from google.genai import types

import config
import storage


def find_device(name, kind):
    """Find audio device by name substring. Returns device index or None."""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if name and name.lower() in d["name"].lower():
            if kind == "input" and d["max_input_channels"] > 0:
                return i
            if kind == "output" and d["max_output_channels"] > 0:
                return i
    return None


def check_blackhole():
    """Check if BlackHole 2ch virtual audio device is installed."""
    try:
        devices = sd.query_devices()
        for d in devices:
            if "blackhole 2ch" in d["name"].lower():
                return True
        return False
    except Exception:
        return False


def resample_24k_to_48k(audio_int16: np.ndarray) -> np.ndarray:
    """Upsample audio from 24 kHz to 48 kHz."""
    if len(audio_int16) == 0:
        return audio_int16
    resampled = scipy.signal.resample_poly(audio_int16.astype(np.float32), 2, 1)
    resampled = np.clip(resampled, -32768, 32767)
    return resampled.astype(np.int16)


async def translation_loop(initial_api_key, set_status, quit_event: asyncio.Event):
    """
    Long-lived session. Audio streams live for the entire engine lifetime.
    Only the Gemini session (send/recv) is restarted when the API key changes.
    """
    out_device = find_device(config.OUTPUT_DEVICE_NAME, "output")
    if out_device is None:
        set_status("Error: BlackHole not found!")
        return

    in_device = find_device(config.INPUT_DEVICE_NAME, "input") if config.INPUT_DEVICE_NAME else None
    mon_device = (
        find_device(config.MONITOR_DEVICE_NAME, "output")
        if config.MONITOR_ENABLED and config.MONITOR_DEVICE_NAME
        else None
    )

    chunk_samples_in = int(config.INPUT_SAMPLE_RATE * config.CHUNK_MS / 1000)

    loop = asyncio.get_event_loop()
    mic_queue: asyncio.Queue = asyncio.Queue()
    buffer_lock = threading.Lock()

    state = {
        "out_buf": np.array([], dtype=np.int16),
        "mon_buf": np.array([], dtype=np.int16),
        "out_ready": False,
        "mon_ready": False,
    }
    mute_state = {"muted": False}
    mic_holder = {"stream": None}

    prebuffer_samples = int(config.DEVICE_OUTPUT_RATE * config.PREBUFFER_SECONDS)

    # --- Microphone input stream ---
    def mic_callback(indata, frames, time_info, status):
        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32767.0
        with config.app_state["audio_level_lock"]:
            config.app_state["audio_level"] = min(rms * 3.0, 1.0)
        loop.call_soon_threadsafe(mic_queue.put_nowait, indata.copy().tobytes())

    def start_mic():
        s = sd.InputStream(
            samplerate=config.INPUT_SAMPLE_RATE, channels=1, dtype="int16",
            device=in_device, blocksize=chunk_samples_in, callback=mic_callback,
        )
        s.start()
        return s

    # --- Output stream callbacks ---
    def out_callback(outdata, frames, time_info, status):
        with buffer_lock:
            buf = state["out_buf"]
            if not state["out_ready"]:
                if len(buf) < prebuffer_samples:
                    outdata.fill(0)
                    return
                state["out_ready"] = True

            need = frames
            if len(buf) >= need:
                outdata[:, 0] = buf[:need]
                state["out_buf"] = buf[need:]
            else:
                outdata[:len(buf), 0] = buf
                outdata[len(buf):, 0] = 0
                state["out_buf"] = np.array([], dtype=np.int16)
                state["out_ready"] = False

    def mon_callback(outdata, frames, time_info, status):
        with buffer_lock:
            buf = state["mon_buf"]
            if not state["mon_ready"]:
                if len(buf) < prebuffer_samples:
                    outdata.fill(0)
                    return
                state["mon_ready"] = True

            need = frames
            if len(buf) >= need:
                outdata[:, 0] = buf[:need]
                state["mon_buf"] = buf[need:]
            else:
                outdata[:len(buf), 0] = buf
                outdata[len(buf):, 0] = 0
                state["mon_buf"] = np.array([], dtype=np.int16)
                state["mon_ready"] = False

    # --- Create audio streams ONCE ---
    out_stream = sd.OutputStream(
        samplerate=config.DEVICE_OUTPUT_RATE, channels=1, dtype="int16",
        device=out_device, latency="high", callback=out_callback,
    )

    monitor_stream = None
    if config.MONITOR_ENABLED:
        monitor_stream = sd.OutputStream(
            samplerate=config.DEVICE_OUTPUT_RATE, channels=1, dtype="int16",
            device=mon_device, latency="high", callback=mon_callback,
        )

    # Start audio streams immediately (they'll idle with silence until data arrives)
    out_stream.start()
    if monitor_stream is not None:
        monitor_stream.start()

    # Restart event — set when API key changes (engine reconnects without touching streams)
    restart_event = asyncio.Event()
    config.app_state["restart_event"] = restart_event

    current_api_key = initial_api_key

    try:
        while not quit_event.is_set():
            # Clear buffers for a fresh session
            with buffer_lock:
                state["out_buf"] = np.array([], dtype=np.int16)
                state["mon_buf"] = np.array([], dtype=np.int16)
                state["out_ready"] = False
                state["mon_ready"] = False
                mute_state["muted"] = False

            # Clear mic queue from previous session
            while not mic_queue.empty():
                try:
                    mic_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            # Stop mic from previous session if any
            if mic_holder["stream"] is not None:
                try:
                    mic_holder["stream"].stop()
                    mic_holder["stream"].close()
                except Exception:
                    pass
                mic_holder["stream"] = None

            # Create Gemini client with current key
            client = genai.Client(api_key=current_api_key, http_options={"api_version": "v1beta"})

            session_config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                translation_config=types.TranslationConfig(
                    target_language_code=config.TARGET_LANGUAGE,
                    echo_target_language=config.ECHO_TARGET_LANGUAGE,
                ),
            )

            set_status("Connecting...")

            try:
                async with client.aio.live.connect(model=config.MODEL, config=session_config) as session:
                    mic_holder["stream"] = start_mic()
                    set_status("Translation active")

                    async def send_audio():
                        while True:
                            if mute_state["muted"]:
                                await asyncio.sleep(0.05)
                                continue
                            pcm_bytes = await mic_queue.get()
                            await session.send_realtime_input(
                                audio=types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000")
                            )

                    async def receive_audio():
                        async for response in session.receive():
                            sc = response.server_content
                            if sc is None:
                                continue

                            if sc.input_transcription and sc.input_transcription.text:
                                print(f"[IN ] {sc.input_transcription.text}")
                            if sc.output_transcription and sc.output_transcription.text:
                                print(f"[OUT] {sc.output_transcription.text}")

                            if sc.model_turn and not mute_state["muted"]:
                                for part in sc.model_turn.parts:
                                    if part.inline_data:
                                        audio_np = np.frombuffer(part.inline_data.data, dtype=np.int16)
                                        audio_np = resample_24k_to_48k(audio_np)

                                        with buffer_lock:
                                            if mute_state["muted"]:
                                                continue
                                            state["out_buf"] = np.concatenate([state["out_buf"], audio_np])
                                            if monitor_stream is not None:
                                                with config.app_state["monitor_volume_lock"]:
                                                    vol = config.app_state["monitor_volume"]
                                                if vol > 0.0:
                                                    quiet = (audio_np.astype(np.float32) * vol).astype(np.int16)
                                                    state["mon_buf"] = np.concatenate([state["mon_buf"], quiet])

                    async def do_pause():
                        if mic_holder["stream"] is not None:
                            mic_holder["stream"].stop()
                            mic_holder["stream"].close()
                            mic_holder["stream"] = None

                        with buffer_lock:
                            mute_state["muted"] = True
                            state["out_buf"] = np.array([], dtype=np.int16)
                            state["mon_buf"] = np.array([], dtype=np.int16)
                            state["out_ready"] = False
                            state["mon_ready"] = False

                        set_status("Paused")

                        try:
                            await session.send_realtime_input(audio_stream_end=True)
                        except Exception as e:
                            print(f"Error sending audio_stream_end: {e}")

                    async def do_resume():
                        if mic_holder["stream"] is None:
                            mic_holder["stream"] = start_mic()
                        mute_state["muted"] = False
                        set_status("Translation active")

                    config.app_state["do_pause"] = do_pause
                    config.app_state["do_resume"] = do_resume

                    send_task = asyncio.ensure_future(send_audio())
                    recv_task = asyncio.ensure_future(receive_audio())

                    # Wait for either quit or restart
                    await asyncio.wait(
                        [asyncio.ensure_future(quit_event.wait()),
                         asyncio.ensure_future(restart_event.wait())],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    send_task.cancel()
                    recv_task.cancel()
                    await asyncio.gather(send_task, recv_task, return_exceptions=True)

                    config.app_state["do_pause"] = None
                    config.app_state["do_resume"] = None

                    if quit_event.is_set():
                        break
                    # restart_event is set — reload key and retry session
                    restart_event.clear()
                    current_api_key = storage.load_api_key()
                    set_status("Restarting...")
                    continue

            except Exception as e:
                print(f"Session error: {e}")
                set_status("Connection error! Check your API key.")
                config.app_state["do_pause"] = None
                config.app_state["do_resume"] = None

                if quit_event.is_set():
                    break

                # Wait for restart signal (user fixes the key)
                await asyncio.wait(
                    [asyncio.ensure_future(quit_event.wait()),
                     asyncio.ensure_future(restart_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if quit_event.is_set():
                    break

                restart_event.clear()
                current_api_key = storage.load_api_key()
                set_status("Restarting...")
                continue

    finally:
        print("Stopping audio streams...")
        config.app_state["restart_event"] = None
        config.app_state["do_pause"] = None
        config.app_state["do_resume"] = None
        # Abort streams immediately instead of graceful stop to avoid
        # PortAudio callback races during shutdown.
        if mic_holder["stream"] is not None:
            try:
                mic_holder["stream"].abort()
                mic_holder["stream"].close()
            except Exception:
                pass
        for stream in (out_stream, monitor_stream):
            if stream is None:
                continue
            try:
                stream.abort()
                stream.close()
            except Exception:
                pass


# --- Thread-level engine control ---

def run_async_loop(api_key, set_status):
    """Create and run the asyncio event loop in the current thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    quit_event = asyncio.Event()
    config.app_state["loop"] = loop
    config.app_state["quit_event"] = quit_event

    config.app_state["main_task"] = loop.create_task(
        translation_loop(api_key, set_status, quit_event)
    )
    try:
        loop.run_until_complete(config.app_state["main_task"])
    except asyncio.CancelledError:
        pass
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        config.app_state["loop"] = None
        config.app_state["main_task"] = None
        config.app_state["quit_event"] = None
        config.app_state["session_thread"] = None


def start_engine(api_key, set_status):
    """Start translation engine in a background thread."""
    # Prevent starting a new engine if one is already running.
    t = config.app_state["session_thread"]
    if t is not None and t.is_alive():
        print("Engine already running, ignoring duplicate start_engine call.")
        return
    t = threading.Thread(
        target=run_async_loop, args=(api_key, set_status), daemon=True
    )
    config.app_state["session_thread"] = t
    t.start()


def stop_engine_sync():
    """Stop engine and wait for full shutdown. Call from non-GUI thread only."""
    loop = config.app_state["loop"]
    quit_event = config.app_state["quit_event"]
    if loop is not None and quit_event is not None:
        loop.call_soon_threadsafe(quit_event.set)
    t = config.app_state["session_thread"]
    if t is not None:
        t.join()
    config.app_state["session_thread"] = None


def request_restart_sync():
    """Signal the running engine to restart the Gemini session with the saved API key."""
    loop = config.app_state["loop"]
    restart_event = config.app_state["restart_event"]
    if loop is not None and restart_event is not None:
        loop.call_soon_threadsafe(restart_event.set)


def request_pause_sync():
    loop = config.app_state["loop"]
    coro_fn = config.app_state["do_pause"]
    if loop is None or coro_fn is None:
        return
    fut = asyncio.run_coroutine_threadsafe(coro_fn(), loop)
    fut.result()


def request_resume_sync():
    loop = config.app_state["loop"]
    coro_fn = config.app_state["do_resume"]
    if loop is None or coro_fn is None:
        return
    fut = asyncio.run_coroutine_threadsafe(coro_fn(), loop)
    fut.result()
