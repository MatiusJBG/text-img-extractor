# Changelog

All notable changes to **Text IMG Extractor** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning: [Semantic Versioning](https://semver.org/).

---

## [1.0.0] - 2026-10-28

### Added
- First public release 🎉
- **OCR multi-stage preprocessing** with `fastNlMeansDenoising`, adaptive Gaussian binarization, and automatic deskew correction.
- **Robust dark mode detection** using percentile-based analysis (p25/p75) instead of simple mean — more accurate with large text.
- **3× adaptive scaling** for very small images (< 100px in any dimension) to maximize OCR accuracy.
- **Expanded PSM strategy**: tries PSM 6, 4, 3, 11 in order and keeps the best result.
- **Binary fallback preprocessing** with Otsu thresholding + morphological opening for fine text.
- **Tesseract path caching** via `functools.lru_cache` — eliminates path resolution overhead per call.
- **DPI Awareness on Windows** (`SetProcessDpiAwarenessContext`) for native-resolution captures on HiDPI/4K screens.
- **Numpy-based BGRA→RGB conversion** in `capture.py` — eliminates color artifacts from `mss`.
- **Performance timing logs** at DEBUG level for each capture operation.
- **Enhanced text cleaning**: broken hyphens, ambiguous pipe characters, URL slashes, technical underscores.
- **Application icon** (`assets/icon.ico`) with multi-resolution ICO (16–256px).
- **Complete README** with installation guide, GitHub usage instructions, and troubleshooting.
- **PyInstaller spec** updated: proper tessdata inclusion, icon support, unused module exclusions.

### Changed
- Renamed executable output from `text_img_extractor.exe` → `TextImgExtractor.exe`.
- `preprocess_image()` now uses `INTER_CUBIC` instead of `INTER_LANCZOS4` for upscaling (faster, comparable quality for text).
- `_configure_tesseract()` is now idempotent (safe to call multiple times, only runs once).
- OCR breaks early on PSM 6/4 only when ≥ 10 characters are found (was ≥ 2).

### Fixed
- `capture_full()` fallback to `PIL.ImageGrab` used `all_screens=True` which could include wrong monitor; changed to `all_screens=False`.
- Tessdata directory detection now checks that the directory is non-empty before returning it.
- Region selector correctly handles multi-monitor virtual geometry.

---

## [Unreleased]

- [ ] Settings dialog (configurable hotkeys, language selection)
- [ ] History of recent extractions
- [ ] Auto-copy mode (copy to clipboard without dialog)
- [ ] Linux packaging (.deb / AppImage)
