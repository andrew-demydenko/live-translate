#!/bin/bash
set -e

echo "=== Live Translate — macOS App Builder ==="

# ── 1. Check python3 ─────────────────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Install Python 3 from https://python.org"
    exit 1
fi

PYTHON=python3
echo "Python: $($PYTHON --version)"

# ── 2. Create virtual environment ────────────────────────────────────────────
# This ensures pip, PyInstaller, and all dependencies share the same Python
# environment, regardless of how many Python versions are installed on the system.
VENV_DIR=".venv_build"

if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment ($VENV_DIR)..."
    $PYTHON -m venv "$VENV_DIR"
fi

# All subsequent commands use Python from venv
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "Using: $($PYTHON --version) from $VENV_DIR"

# ── 3. Install dependencies inside venv ──────────────────────────────────────
echo ""
echo "Installing dependencies..."

$PIP install --quiet --upgrade pip
$PIP install --quiet --upgrade \
    pyinstaller \
    google-genai \
    sounddevice \
    numpy \
    scipy

echo "Dependencies installed."

# ── 4. Check system dependencies ─────────────────────────────────────────────
echo ""
echo "Checking system dependencies..."

MISSING_DEPS=""

if ! system_profiler SPAudioDataType 2>/dev/null | grep -qi "BlackHole 2ch"; then
    echo "  ⚠  BlackHole 2ch not found."
    echo "     Install it: brew install blackhole-2ch"
    echo "     Without it, the app won't be able to send translated audio."
    MISSING_DEPS="yes"
fi

if [ -n "$MISSING_DEPS" ]; then
    echo ""
    echo "──────────────────────────────────────────────────"
    echo "  WARNING: System dependencies are missing."
    echo "  Install them before running the application."
    echo "──────────────────────────────────────────────────"
fi

# ── 5. Build .app ────────────────────────────────────────────────────────────
echo ""
echo "Building Live Translate.app..."

rm -rf build dist

$PYTHON -m PyInstaller \
    --clean \
    --noconfirm \
    live_translate.spec

# ── 6. Verify result ─────────────────────────────────────────────────────────
APP_PATH="dist/Live Translate.app"

if [ ! -d "$APP_PATH" ]; then
    echo ""
    echo "Error: .app was not created. Check PyInstaller output above."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Done!  →  $APP_PATH"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  • Double-click the .app to run."
echo "  • Drag it to /Applications to install as a regular app."
echo ""
echo "  IMPORTANT on first launch:"
echo "  macOS may show a \"developer cannot be verified\" warning."
echo "  To open it, run in Terminal:"
echo "    xattr -cr \"$APP_PATH\""
echo "  OR: System Settings → Privacy & Security → \"Open Anyway\""
echo ""
echo "  macOS will ask for microphone permission on first launch —"
echo "  grant it, otherwise translation won't work."
