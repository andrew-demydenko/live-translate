# Application constants and global state.

import threading

# --- Translation settings ---
TARGET_LANGUAGE = "en"
ECHO_TARGET_LANGUAGE = False

# --- Audio settings ---
INPUT_SAMPLE_RATE = 16000
MODEL_OUTPUT_RATE = 24000
DEVICE_OUTPUT_RATE = 48000
CHUNK_MS = 100

# --- Model ---
MODEL = "models/gemini-3.5-live-translate-preview"

# --- Device names (None = system default) ---
OUTPUT_DEVICE_NAME = "BlackHole 2ch"
INPUT_DEVICE_NAME = None

# --- Monitor settings ---
MONITOR_ENABLED = True
MONITOR_DEVICE_NAME = None
MONITOR_VOLUME = 0.1  # 0.0 to 0.5, mapped from slider

# --- Output buffer ---
PREBUFFER_SECONDS = 0.1

# --- macOS UI colors ---
MAC_BG = "#f5f5f7"
MAC_CARD_BG = "#ffffff"
MAC_TEXT = "#1d1d1f"
MAC_SECONDARY = "#86868b"
MAC_ACCENT = "#4C9AFF"
MAC_ACCENT_HOVER = "#6DB5FF"
MAC_RED = "#E8827A"
MAC_RED_HOVER = "#EE9C95"
MAC_BORDER = "#d2d2d7"
MAC_DISABLED_TEXT = "#aeaeb2"

# --- Fonts ---
FONT_FAMILY = ".AppleSystemUIFont"
FONT_MONO = "Menlo"

# --- Global application state (shared between engine and UI) ---
app_state = {
    "loop": None,
    "main_task": None,
    "session_thread": None,
    "quit_event": None,
    "do_pause": None,
    "do_resume": None,
    "monitor_volume": MONITOR_VOLUME,
    "monitor_volume_lock": threading.Lock(),
}
