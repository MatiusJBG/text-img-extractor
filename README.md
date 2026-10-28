<div align="center">

# 📸 Text IMG Extractor

**Captura de pantalla + extracción de texto OCR en tiempo real**  
para **Windows** y **Linux**, con atajos de teclado globales y bandeja del sistema.

[![Release](https://img.shields.io/github/v/release/MatiusJBG/text-img-extractor?color=6366f1&label=release)](https://github.com/MatiusJBG/text-img-extractor/releases/latest)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)](https://github.com/MatiusJBG/text-img-extractor)

</div>

---

## ✨ Características

| Función | Atajo de teclado |
|---------|-----------------|
| 🖥️ Captura pantalla completa | `Ctrl + Shift + F` |
| 🪟 Captura ventana activa | `Ctrl + Shift + W` |
| ✂️ Selección de región | `Ctrl + Shift + S` |

- **OCR de alta precisión** con Tesseract 5 (español + inglés), preprocesamiento multi-etapa con denoising, deskew y binarización adaptativa.
- **Ejecución en segundo plano** — vive en la bandeja del sistema sin ventanas.
- **Diálogo de resultados** con botón "Copiar" y feedback visual animado.
- **Screen Freeze** al seleccionar región: la pantalla se congela para mayor precisión.
- **Soporte HiDPI/4K** — captura a resolución nativa en pantallas escalonadas.
- **Ejecutable portable** — sin instalación de Python ni dependencias (`TextImgExtractor.exe`).

---

## 🚀 Descarga rápida (ejecutable)

> **Windows — Sin instalación necesaria**

1. Ve a la página de [**Releases**](https://github.com/MatiusJBG/text-img-extractor/releases/latest).
2. Descarga `TextImgExtractor-v1.0.0-windows.zip`.
3. Extrae el ZIP y ejecuta `TextImgExtractor.exe`.
4. Aparecerá un icono **T** en la bandeja del sistema.
5. Usa los atajos de teclado o el menú del tray para capturar texto.

> [!IMPORTANT]
> El ejecutable requiere que **Tesseract OCR** esté instalado en el sistema  
> (ver sección [Instalar Tesseract](#3-instalar-tesseract-ocr)).

---

## 🛠️ Instalación en modo desarrollo

### 1. Clonar el repositorio

```bash
git clone https://github.com/MatiusJBG/text-img-extractor.git
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
1. Descarga el instalador desde: [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
2. Instala en `C:\Program Files\Tesseract-OCR\` (ruta por defecto — detectada automáticamente).
3. Asegúrate de incluir los idiomas **Spanish** y **English** durante la instalación.

> [!TIP]
> También puedes usar la variable de entorno `TESSERACT_PATH` para apuntar a una instalación personalizada:
> ```bash
> set TESSERACT_PATH=C:\mi-carpeta\tesseract.exe
> ```

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

## 📁 Estructura del proyecto

```
text-img-extractor/
├── main.py                      # Punto de entrada principal
├── requirements.txt             # Dependencias Python
├── text_img_extractor.spec      # Configuración PyInstaller
├── src/
│   ├── capture.py               # Captura de pantalla (full/window/region) + DPI awareness
│   ├── region_selector.py       # Overlay Qt para seleccionar región (Screen Freeze)
│   ├── ocr.py                   # OCR multi-etapa con preprocesamiento avanzado
│   ├── result_dialog.py         # Diálogo de resultados (dark UI)
│   ├── hotkeys.py               # Atajos de teclado globales (Windows/Linux)
│   └── tray.py                  # Icono de bandeja del sistema
├── assets/
│   ├── icon.ico                 # Icono de la aplicación
│   └── generate_icon.py        # Script para regenerar el icono
├── tessdata/
│   ├── eng.traineddata          # Modelo OCR inglés
│   └── spa.traineddata          # Modelo OCR español
└── tests/
    ├── conftest.py
    └── test_modules.py
```

---

## 📦 Generar el ejecutable (distribución)

```bash
# 1. Activar entorno virtual
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Linux

# 2. Generar
pyinstaller text_img_extractor.spec

# El ejecutable quedará en:
#   dist/TextImgExtractor.exe   (Windows)
#   dist/TextImgExtractor       (Linux)
```

> [!NOTE]
> Para incluir Tesseract en el ejecutable (distribución sin dependencias), coloca los binarios en `tesseract/`:
> ```
> tesseract/
> ├── tesseract.exe     ← copiado de C:\Program Files\Tesseract-OCR\
> ├── *.dll             ← todas las DLLs del directorio de Tesseract
> └── tessdata/
>     ├── eng.traineddata
>     └── spa.traineddata
> ```

---

## ⌨️ Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl + Shift + F` | Captura la pantalla completa |
| `Ctrl + Shift + W` | Captura la ventana activa |
| `Ctrl + Shift + S` | Abre el overlay para seleccionar región |
| `Ctrl + C` (en diálogo) | Copia el texto extraído al portapapeles |
| `Escape` (en diálogo) | Cierra el diálogo |
| `Escape` (en overlay) | Cancela la selección |

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

### Agregar idiomas adicionales de OCR

1. Descarga el archivo `.traineddata` desde: [tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata)
2. Colócalo en `tessdata/`
3. Modifica el parámetro `langs` en la llamada a `extract_text()` en `main.py`:
   ```python
   text = extract_text(image, langs="spa+eng+fra")  # ejemplo: + francés
   ```

---

## 🐛 Solución de problemas

| Problema | Solución |
|----------|----------|
| `TesseractNotFoundError` | Instala Tesseract o configura `TESSERACT_PATH` |
| Hotkeys no funcionan en Linux | Wayland tiene restricciones; usa X11: `DISPLAY=:0 python main.py` |
| Portapapeles no funciona en Linux | Instala `xclip`: `sudo apt install xclip` |
| El tray no aparece en Linux | Algunos DEs requieren extensiones; prueba GNOME Shell Extension: *AppIndicator* |
| Texto vacío en capturas oscuras | El modo oscuro se detecta automáticamente; si falla, reporta un issue |

---

## 📄 Licencia

MIT License — Libre para uso personal y comercial.  
Ver [LICENSE](LICENSE) para detalles.
