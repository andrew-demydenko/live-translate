# Live Translate

Real-time speech translation app for macOS. Captures audio from your microphone, translates it via the **Google Gemini Live API**, and outputs the translated speech to a **BlackHole** virtual audio device.

Perfect for use in **Google Meet**, **Zoom**, and other video conferencing apps — just select BlackHole 2ch as your microphone in the conferencing app.

## How it works

```
Microphone → Gemini Live API (translation) → BlackHole 2ch → Google Meet / Zoom / ...
```

- Speech from your microphone is sent to the Gemini Live API
- Gemini returns translated speech (audio)
- Audio is played to the BlackHole virtual device
- In Google Meet / Zoom, BlackHole is selected as the microphone — participants hear the translation

## System Requirements

- macOS 12.0+
- Python 3.14+
- [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole) (virtual audio device)
- Google Gemini API key

## Installation

### 1. Install BlackHole

```bash
brew install blackhole-2ch
```

After installation, BlackHole will appear in macOS audio device list.

### 2. Clone the repository

```bash
git clone <repo-url>
cd live-translate
```

### 3. Install dependencies

Create a virtual environment and install packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install google-genai sounddevice numpy scipy
```

## Running

```bash
source .venv/bin/activate
python3 live_translate.py
```

On first launch, a window will appear to enter your **Gemini API key**. The key is stored in `~/.live_translate/config.json` (permissions 600).

Get a key: https://aistudio.google.com/apikey

## Usage

1. Launch the app
2. Enter your API key (first launch only)
3. Open Google Meet / Zoom and select **BlackHole 2ch** as your microphone
4. Speak in the source language — participants will hear the translation

### Controls

- **Pause / Resume** — pause / resume translation
- **Monitor Volume** — volume of translated speech heard in your headphones (0% = off)
- **Change API Key** — change the API key
- **Quit** — exit the application

## Configuration

Settings in [`config.py`](config.py):

| Parameter              | Description                         | Default                                      |
| ---------------------- | ----------------------------------- | -------------------------------------------- |
| `TARGET_LANGUAGE`      | Target language (BCP-47 code)       | `"en"`                                       |
| `ECHO_TARGET_LANGUAGE` | Whether to echo the original speech | `False`                                      |
| `INPUT_SAMPLE_RATE`    | Microphone sample rate              | `16000`                                      |
| `MODEL`                | Gemini model                        | `"models/gemini-3.5-live-translate-preview"` |
| `OUTPUT_DEVICE_NAME`   | Output device for translated audio  | `"BlackHole 2ch"`                            |
| `MONITOR_ENABLED`      | Enable headphone monitoring         | `True`                                       |

### Changing the target language

Edit `TARGET_LANGUAGE` in `config.py`. For example, for Russian → English:

```python
TARGET_LANGUAGE = "en"
```

For Russian → German:

```python
TARGET_LANGUAGE = "de"
```

## Building as .app

To build a standalone `.app` bundle that doesn't require Python:

```bash
./build_app.sh
```

The built `.app` will be at `dist/Live Translate.app`.

### Build notes

- Builds with PyInstaller into a self-contained .app
- On first launch, macOS may show a "developer cannot be verified" warning
- To bypass: `xattr -cr "dist/Live Translate.app"` or via System Settings → Privacy & Security
- macOS will ask for microphone permission — grant it
