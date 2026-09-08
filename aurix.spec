# Builds dist/Aurix, which runs without Python. Models aren't in here - the
# installer drops them next to the exe.

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Stuff PyInstaller can't work out on its own. espeakng_loader carries the
# espeak-ng dll and its data, which Kokoro shells out to for pronunciation -
# without it the voice loads and then dies on the first word.
for package in (
    "faster_whisper", "openwakeword", "ctranslate2", "ddgs",
    "kokoro_onnx", "espeakng_loader", "phonemizer",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

analysis = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["sounddevice", "pystray._win32"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore"],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Aurix",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # output goes to aurix.log instead
    icon=None,
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Aurix",
)
