#!/usr/bin/env python3
"""
Live Translate -> virtual microphone (BlackHole).

Before first run:
1. brew install blackhole-2ch
2. python3 -m pip install --user google-genai sounddevice numpy scipy
3. Run the script — on first start, a window will appear to enter your
   Gemini API key. The key is saved to ~/.live_translate/config.json
   (permissions 600 — readable only by your user) and auto-loaded on
   subsequent runs.
4. Set TARGET_LANGUAGE in config.py for your language pair.
5. In Google Meet, select "BlackHole 2ch" as your microphone.

The app will warn you on startup if BlackHole is not installed.
"""

import ui

if __name__ == "__main__":
    ui.create_gui()
