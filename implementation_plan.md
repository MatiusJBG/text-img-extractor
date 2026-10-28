# Implementación del capturador de pantalla + OCR

## 1️⃣ Requisitos confirmados
| Nº | Requisito | Estado |
|---|-----------|--------|
| 1 | Compatibilidad Windows & Linux | ✅ |
| 2 | Código Python, sin dependencias pre‑instaladas | ✅ (usaremos PyInstaller para empaquetar) |
| 3 | Tres modos de captura (pantalla completa, ventana activa, región dibujada) | ✅ |
| 4 | OCR una sola vez por captura (máxima velocidad) | ✅ |
| 5 | Diálogo de resultados con botón **Copiar** (sin edición) | ✅ |
| 6 | UI de escritorio, framework rápido | ✅ (Qt + QtQuick) |
| 7 | Activación vía atajos de teclado, sin instalación de dependencias | ✅ (hotkeys globales) |
| 8 | Bajo consumo de RAM, uso de CPU/VRAM libre, ejecución en segundo plano | ✅ |
| 9 | Solo extracción y copia de texto | ✅ |

## 2️⃣ Preguntas finales
1. **Atajos de teclado** – ¿Prefieres los mismos atajos que el capturador nativo de Windows (`Win+Shift+S`) o tienes alguna combinación distinta?
2. **Icono en la bandeja** – ¿ deseas un **icono de sistema** (tray) con menú contextual (Abrir, Salir, Configuración) o basta con que la app se inicie sin UI visible?
3. **Idiomas de OCR** – Tesseract soporta varios idiomas; para español e inglés basta con los paquetes `spa` y `eng`. ¿ los necesitas ambos?
4. **Distribución** – ¿ quieres un **único ejecutable** (`.exe` para Windows, binario para Linux) o también un instalador (MSI/DEB) que solo copie el binario?

---

## 3️⃣ Arquitectura propuesta
```mermaid
flowchart TD
    A[Inicio (ejecutable)] --> B[Servicio en segundo plano + Tray icon]
    B --> C{Escucha hotkey}
    C -->|Win+Shift+S| D[Overlay transparente (selección región)]
    C -->|PrintScreen| E[Captura pantalla completa]
    C -->|Alt+PrintScreen| F[Captura ventana activa]
    D --> G[Obtener rectángulo
    seleccionado]
    E & F & G --> H[Captura de píxeles (mss)]
    H --> I[Convertir a OpenCV / Pillow]
    I --> J[OCR (pytesseract + Tesseract binaries)]
    J --> K[Diálogo Qt: resultado + botón Copiar]
    K --> L[Copiar al portapapeles]
    L --> B
```

## 4️⃣ Tecnologías y paquetes (embebidos)
| Área | Biblioteca | Motivo |
|------|------------|--------|
| UI & Tray | **PyQt6** (o PySide6) | Framework rápido, cross‑platform |
| Hotkeys globales | **keyboard** (Windows) + **pynput** (Linux) | Captura combinaciones sin permisos extra |
| Captura de pantalla | **mss** | Muy rápida y nativa |
| Procesado de imágenes | **Pillow** + **OpenCV (cv2)** | Mejora OCR |
| OCR | **pytesseract** + **Tesseract 5.x binaries** | Motor estable y multilingüe |
| Portapapeles | **pyperclip** | Copia sencilla |
| Empaquetado | **PyInstaller** | Ejecutable auto‑contenedor |

## 5️⃣ Paso a paso de desarrollo
| Etapa | Tareas | Salida / Artefacto |
|------|--------|--------------------|
| **0 – Preparación** | Crear repositorio base, `requirements.txt`. | Estructura de proyecto |
| **1 – Captura de pantalla** | Implementar `capture_full()`, `capture_active_window()`, `capture_region(rect)`. Probar con mss. | `capture.py` |
| **2 – Overlay de selección** | UI Qt transparente para arrastrar rectángulo. | `region_selector.py` |
| **3 – OCR** | Integrar Tesseract binario, función `extract_text(image)`. | `ocr.py` |
| **4 – Diálogo de resultados** | Qt Dialog con QTextEdit solo lectura y botón **Copiar**. | `result_dialog.py` |
| **5 – Hotkeys & Tray** | Registrar hotkeys, lanzar overlay, crear icono de bandeja con menú “Salir”. | `main.py` |
| **6 – Optimización** | Pre‑procesamiento (grayscale + Otsu), medir latencia < 300 ms. | `benchmarks.txt` |
| **7 – Empaquetado** | Configurar PyInstaller para incluir binaries y recursos. | `dist/` ejecutables |
| **8 – Documentación** | README con uso rápido y troubleshooting. | `README.md` |
| **9 – Pruebas** | Unit tests (pytest) y pruebas manuales en Windows & Ubuntu. | `tests/` + `test_report.txt` |

## 6️⃣ Cronograma estimado (semanas)
| Semana | Objetivo |
|--------|----------|
| 1 | Setup, captura básica |
| 2 | Overlay y hotkeys |
| 3 | Integración OCR |
| 4 | Diálogo y tray |
| 5 | Optimización y empaquetado |
| 6 | Testing, docs, entrega |

## 7️⃣ Riesgos y mitigaciones
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Tamaño del ejecutable | 50‑80 MB | Usar versión “slim” de Tesseract, comprimir con UPX |
| Permisos de hotkeys en Linux | Puede fallar en Wayland | Detectar entorno, usar `pynput` (X11) y avisar al usuario |
| Latencia OCR | Afecta UX | Redimensionar a 150 DPI, binarizado rápido |
| Portapapeles en Wayland | Copiar puede fallar | Usar Qt `QClipboard` que maneja ambos |

## 8️⃣ Próximos pasos
1. Confirmar atajos de teclado, ícono de bandeja y paquetes de idioma.
2. Con la información, iniciaré la creación del repositorio y la primera iteración del módulo de captura.

---

*Este documento se guardó como artefacto para referencia futura.*