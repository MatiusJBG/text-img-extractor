# Text IMG Extractor

> Capturador de pantalla con extracción de texto (OCR) en tiempo real para **Windows** y **Linux**.

## ✨ Características

| Función | Atajo de teclado |
|---------|-----------------|
| 🖥️ Captura pantalla completa | `Ctrl + Shift + F` |
| 🪟 Captura ventana activa | `Ctrl + Shift + W` |
| ✂️ Selección de región | `Ctrl + Shift + S` |

- **OCR automático** al tomar la captura (Tesseract 5, español + inglés)
- **Diálogo de resultados** con botón "Copiar" y feedback visual
- **Icono de bandeja** del sistema con menú contextual
- **Ejecución en segundo plano** sin ventana visible
- **Sin instalación de dependencias** (ejecutable auto-contenedor vía PyInstaller)

---

## 📁 Estructura del proyecto

```
text-img-extractor/
├── main.py                      # Punto de entrada principal
├── requirements.txt             # Dependencias Python
├── text_img_extractor.spec      # Configuración PyInstaller
├── src/
│   ├── capture.py               # Módulos de captura (full/window/region)
│   ├── region_selector.py       # Overlay Qt para seleccionar región
│   ├── ocr.py                   # Extracción de texto con Tesseract
│   ├── result_dialog.py         # Diálogo de resultados
│   ├── hotkeys.py               # Atajos de teclado globales
│   └── tray.py                  # Icono de bandeja del sistema
├── tests/
│   ├── conftest.py
│   └── test_modules.py
├── tesseract/                   # (Generado) Binarios de Tesseract
│   ├── tesseract.exe / tesseract
│   └── tessdata/
│       ├── spa.traineddata
│       └── eng.traineddata
└── dist/                        # (Generado) Ejecutables
```

---

## 🚀 Instalación y uso en desarrollo

### 1. Clonar el repositorio

```bash
git clone <url-repositorio>
cd text-img-extractor
```

### 2. Crear entorno virtual e instalar dependencias

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Instalar Tesseract OCR

#### Windows
1. Descarga el instalador desde: https://github.com/UB-Mannheim/tesseract/wiki
2. Instala en `C:\Program Files\Tesseract-OCR\`
3. **O bien**: coloca los binarios en la carpeta `tesseract/` del proyecto (para distribución).

#### Linux (Ubuntu/Debian)
```bash
sudo apt install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng
```

### 4. Ejecutar la aplicación

```bash
python main.py
```

La aplicación se iniciará en **segundo plano** (bandeja del sistema).  
Usa los atajos de teclado o el menú de la bandeja para capturar.

---

## 📦 Generar ejecutable

```bash
# Asegúrate de tener los binarios de Tesseract en tesseract/
pyinstaller text_img_extractor.spec
```

El ejecutable se genera en `dist/text_img_extractor.exe` (Windows) o `dist/text_img_extractor` (Linux).

---

## ⌨️ Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl + Shift + F` | Captura la pantalla completa |
| `Ctrl + Shift + W` | Captura la ventana activa |
| `Ctrl + Shift + S` | Abre el overlay para seleccionar región |
| `Ctrl + C` (en diálogo) | Copia el texto extraído |
| `Escape` (en diálogo) | Cierra el diálogo |

---

## 🧪 Ejecutar pruebas

```bash
pytest tests/ -v
```

---

## ⚙️ Configuración avanzada

### Variable de entorno para Tesseract personalizado

```bash
# Windows
set TESSERACT_PATH=C:\ruta\a\tesseract.exe

# Linux
export TESSERACT_PATH=/ruta/a/tesseract
```

### Idiomas de OCR

Por defecto se usan español (`spa`) e inglés (`eng`). Para agregar más idiomas:

1. Descarga el archivo `.traineddata` de: https://github.com/tesseract-ocr/tessdata
2. Colócalo en `tesseract/tessdata/`
3. Modifica el parámetro `langs` en `src/ocr.py`

---

## 🐛 Solución de problemas

| Problema | Solución |
|----------|----------|
| `TesseractNotFoundError` | Asegúrate de que Tesseract está instalado o configura `TESSERACT_PATH` |
| Hotkeys no funcionan en Linux | Wayland tiene restricciones; usa X11 (`DISPLAY=:0 python main.py`) |
| Portapapeles no funciona en Linux | Instala `xclip`: `sudo apt install xclip` |
| El tray no aparece | Algunos entornos de escritorio Linux requieren extensiones de bandeja del sistema |

---

## 📄 Licencia

MIT License — Libre para uso personal y comercial.
