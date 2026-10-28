# Text IMG Extractor v1.0.0 🚀

Primera versión oficial de **Text IMG Extractor**, una herramienta moderna y ultrarrápida de captura de pantalla con extracción de texto OCR en tiempo real para Windows y Linux.

---

### ✨ Novedades y Mejoras Principales

#### 🔍 Calidad y Precisión de OCR
- **Preprocesamiento multi-etapa**: Denoising adaptativo (`fastNlMeansDenoising`) para limpiar ruido de compresión en capturas.
- **Detección robusta de modo oscuro**: Basada en distribución de percentiles (p25/p75) en lugar de media simple, evitando falsos positivos con texto de gran tamaño.
- **Binarización adaptativa Gaussian**: Mejora la legibilidad en interfaces con degradados o iluminación irregular.
- **Deskew automático**: Detección y corrección de rotaciones e inclinaciones leves (< 10°).
- **Escalado adaptativo inteligente**:
  - Imágenes < 100px: escalado a **3×** para máxima legibilidad.
  - Imágenes < 300px (alto) o < 600px (ancho): escalado a **2×**.
- **Estrategia multi-PSM**: Intenta secuencialmente PSM 6 (bloque uniforme), PSM 4 (columnas), PSM 3 (automático) y PSM 11 (texto disperso).
- **Fallback binario (Otsu + morfología)**: Recuperación automática para texto ultrafino sobre fondos complejos.
- **Normalización y limpieza de texto**: Reglas heurísticas avanzadas para corregir artefactos OCR comunes (espacios espurios en URLs, extensiones, guiones bajos, saltos de línea en palabras divididas).

#### ⚡ Rendimiento y Captura
- **DPI Awareness en Windows**: Capturas nativas sin distorsión ni escalado borroso en pantallas HiDPI/4K (125%, 150%, 200%).
- **Conversión de color acelerada**: Reordenamiento BGRA → RGB mediante NumPy de alta velocidad.
- **Caché en resolución de rutas**: Tesseract y tessdata se resuelven una sola vez (`lru_cache`).
- **Screen Freeze**: Al seleccionar una región (`Ctrl+Shift+S`), la pantalla se congela instantáneamente para dibujar el rectángulo sin parpadeos ni movimiento.

---

### ⌨️ Atajos de Teclado Globales

| Atajo | Acción |
|---|---|
| `Ctrl + Shift + S` | Seleccionar región (con congelamiento de pantalla) |
| `Ctrl + Shift + F` | Capturar pantalla completa |
| `Ctrl + Shift + W` | Capturar ventana activa |
| `Ctrl + C` | Copiar texto extraído (en ventana de resultado) |
| `Escape` | Cerrar ventana de resultado o cancelar selección |

---

### 📦 Archivos Adjuntos

- **`TextImgExtractor-v1.0.0-windows-x64.zip`**: Paquete completo portable para Windows con instrucciones y licencia.
- **`TextImgExtractor.exe`**: Ejecutable directo auto-contenedor.

> **Requisito previo en Windows:**
> Tener instalado [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (instalación recomendada en `C:\Program Files\Tesseract-OCR\`).
