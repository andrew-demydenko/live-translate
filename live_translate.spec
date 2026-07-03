block_cipher = None

a = Analysis(
    ["live_translate.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # local application modules
        "config",
        "storage",
        "engine",
        "ui",
        # scipy submodules (not always auto-detected)
        "scipy.signal",
        "scipy.signal.windows",
        "scipy._lib.messagestream",
        "scipy.special._ufuncs_cxx",
        "scipy.linalg.cython_blas",
        "scipy.linalg.cython_lapack",
        # google-genai submodules
        "google.genai",
        "google.genai.types",
        "google.auth",
        "google.auth.transport.requests",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "PIL", "PyQt5", "wx"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Live Translate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # без терминального окна
    disable_windowed_traceback=False,
    argv_emulation=False,   # важно для macOS: не эмулируем argv через Apple Events
    target_arch=None,       # None = собрать под текущую архитектуру (Intel или Apple Silicon)
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Live Translate",
)

app = BUNDLE(
    coll,
    name="Live Translate.app",
    icon="icon.icns",
    bundle_identifier="com.livetranslate.app",
    info_plist={
        # Без этой строки macOS будет молча блокировать доступ к микрофону
        "NSMicrophoneUsageDescription": (
            "Live Translate использует микрофон для перевода речи в реальном времени."
        ),
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleName": "Live Translate",
        "CFBundleDisplayName": "Live Translate",
    },
)
