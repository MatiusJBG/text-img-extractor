# ─────────────────────────────────────────────────────────────────────────────
#  text_img_extractor.spec
#  Configuración de PyInstaller para generar el ejecutable auto-contenedor.
#
#  Uso:
#      pyinstaller text_img_extractor.spec
#
#  Genera:
#      dist/TextImgExtractor.exe   (Windows)
#      dist/TextImgExtractor       (Linux)
#
#  Requisitos previos:
#      - tessdata/eng.traineddata y tessdata/spa.traineddata en la raíz del proyecto
#      - (Opcional) assets/icon.ico para el icono de la aplicación en Windows
# ─────────────────────────────────────────────────────────────────────────────

import os
import platform
import sys

block_cipher = None

# Directorio raíz del proyecto
ROOT = os.path.dirname(os.path.abspath(SPEC))

# ── Datos adicionales (tessdata local) ────────────────────────────────────────
datas = []
binaries = []

# Incluir tessdata local si existe (idiomas spa + eng)
local_tessdata = os.path.join(ROOT, "tessdata")
if os.path.isdir(local_tessdata):
    datas.append((local_tessdata, "tessdata"))
    print(f"[SPEC] Incluyendo tessdata local: {local_tessdata}")

# ── Binarios de Tesseract empaquetados ─────────────────────────────────────
# Para distribución completa (sin depender de Tesseract instalado),
# copia los binarios en ROOT/tesseract/:
#   Windows: tesseract.exe + todas las DLLs
#   Linux:   tesseract
tesseract_dir = os.path.join(ROOT, "tesseract")
if os.path.isdir(tesseract_dir):
    if platform.system() == "Windows":
        tess_exe = os.path.join(tesseract_dir, "tesseract.exe")
        if os.path.isfile(tess_exe):
            binaries.append((tess_exe, "tesseract"))
            # Incluir DLLs necesarias
            for dll in os.listdir(tesseract_dir):
                if dll.endswith(".dll"):
                    binaries.append((os.path.join(tesseract_dir, dll), "tesseract"))
            print(f"[SPEC] Incluyendo binarios de Tesseract (Windows): {tesseract_dir}")
        tess_tessdata = os.path.join(tesseract_dir, "tessdata")
        if os.path.isdir(tess_tessdata):
            datas.append((tess_tessdata, "tesseract/tessdata"))
    else:
        tess_bin = os.path.join(tesseract_dir, "tesseract")
        if os.path.isfile(tess_bin):
            binaries.append((tess_bin, "tesseract"))
            print(f"[SPEC] Incluyendo binario de Tesseract (Linux): {tess_bin}")

# ── Módulos ocultos necesarios ─────────────────────────────────────────────
hidden_imports = [
    # Qt
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    # Captura de pantalla
    "mss",
    "mss.darwin",
    "mss.linux",
    "mss.windows",
    # OCR
    "pytesseract",
    # Imagen
    "PIL",
    "PIL.Image",
    "PIL.ImageGrab",
    # Visión
    "cv2",
    "numpy",
    # Portapapeles
    "pyperclip",
    # Hotkeys
    "keyboard",
    "pynput",
    "pynput.keyboard",
    "pynput.mouse",
    # Windows API (no falla en Linux al no encontrar el módulo)
    "win32gui",
    "win32con",
    "ctypes",
    "ctypes.wintypes",
]

# ── Icono de la aplicación ─────────────────────────────────────────────────
icon_path = None
if platform.system() == "Windows":
    candidate_icon = os.path.join(ROOT, "assets", "icon.ico")
    if os.path.isfile(candidate_icon):
        icon_path = candidate_icon
        print(f"[SPEC] Usando icono: {icon_path}")
    else:
        print("[SPEC] assets/icon.ico no encontrado; se usará icono por defecto.")

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
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "notebook",
        "pytest",
    ],
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
    name="TextImgExtractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "python3*.dll"],
    runtime_tmpdir=None,
    console=False,      # Sin ventana de consola (aplicación de bandeja)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    version_file=None,
)
