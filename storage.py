# API key storage in ~/.live_translate/config.json

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".live_translate"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_api_key():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = (data.get("gemini_api_key") or "").strip()
        return key or None
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_api_key(key: str):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"gemini_api_key": key}, f)
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def clear_api_key():
    try:
        CONFIG_PATH.unlink()
    except FileNotFoundError:
        pass
