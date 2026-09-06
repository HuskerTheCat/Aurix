# PyInstaller build description for Gab.
#
# Produces dist/Gab/ containing Gab.exe and everything Python needs. The big
# files - the language model, the voice, the speech model, the wake word -
# are NOT bundled in here. They live in runtime/, which the installer copies
# in beside the exe, because burying three gigabytes inside a build makes
# every rebuild take minutes and stops anyone swapping a model out.

from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = []
binaries = []
hiddenimports = []

# These packages carry data files and native libraries that PyInstaller does
# not find by looking at imports alone.
for package in ("faster_whisper", "openwakeword", "piper", "ctranslate2", "ddgs"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

# Piper needs its pronunciation data to turn text into sounds.
datas += collect_data_files("piper", subdir="espeak-ng-data")

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
    name="Gab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # No console window. Anything worth reading goes to gab.log beside the exe.
    console=False,
    icon=None,
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Gab",
)
