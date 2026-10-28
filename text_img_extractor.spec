# ─────────────────────────────────────────────────────────────────────────────
#  text_img_extractor.spec
#  Configuración de PyInstaller para generar el ejecutable auto-contenedor.
# ─────────────────────────────────────────────────────────────────────────────

import os
import platform
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Directorio raíz del proyecto
ROOT = os.path.dirname(os.path.abspath(SPEC))

# ── Binarios de Tesseract ──────────────────────────────────────────────────
# Coloca los binarios en ROOT/tesseract/
# Windows: tesseract.exe + tessdata/
# Linux:   tesseract  + tessdata/
tesseract_dir = os.path.join(ROOT, "tesseract")

binaries = []
datas = []

if os.path.isdir(tesseract_dir):
    if platform.system() == "Windows":
        tess_exe = os.path.join(tesseract_dir, "tesseract.exe")
        if os.path.isfile(tess_exe):
            binaries.append((tess_exe, "tesseract"))
    else:
        tess_bin = os.path.join(tesseract_dir, "tesseract")
        if os.path.isfile(tess_bin):
            binaries.append((tess_bin, "tesseract"))

    tessdata = os.path.join(tesseract_dir, "tessdata")
    if os.path.isdir(tessdata):
        datas.append((tessdata, "tesseract/tessdata"))

# ── Módulos ocultos necesarios ─────────────────────────────────────────────
hidden_imports = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "mss",
    "mss.darwin",
    "mss.linux",
    "mss.windows",
    "pytesseract",
    "PIL",
    "PIL.Image",
    "cv2",
    "numpy",
    "pyperclip",
    "keyboard",
    "pynput",
    "pynput.keyboard",
    "pynput.mouse",
]

# ─────────────────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[ROOT, os.path.join(ROOT, "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="text_img_extractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # Comprimir con UPX para reducir tamaño
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # Sin ventana de consola
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "icon.ico") if platform.system() == "Windows" else None,
)
