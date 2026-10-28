"""
hotkeys.py – Registro y gestión de atajos de teclado globales.
Compatible con Windows (keyboard) y Linux (pynput).
"""
import sys
import platform
import threading
import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Mapeo de atajos: nombre -> combinación
DEFAULT_HOTKEYS: Dict[str, str] = {
    "capture_full":   "ctrl+shift+f",
    "capture_window": "ctrl+shift+w",
    "capture_region": "ctrl+shift+s",
}


class HotkeyManager:
    """
    Gestiona atajos de teclado globales de forma cross-platform.
    """

    def __init__(self, callbacks: Dict[str, Callable]):
        """
        Args:
            callbacks: Dict con claves 'capture_full', 'capture_window', 'capture_region'
                       y valores callable que se ejecutan al disparar el hotkey.
        """
        self._callbacks = callbacks
        self._os = platform.system()
        self._listener = None
        self._registered = False
        self._lock = threading.Lock()

    def start(self):
        """Inicia el registro de hotkeys en un hilo daemon."""
        t = threading.Thread(target=self._register, daemon=True)
        t.start()

    def _register(self):
        if self._os == "Windows":
            self._register_windows()
        else:
            self._register_linux()

    def _register_windows(self):
        try:
            import keyboard
            for action, combo in DEFAULT_HOTKEYS.items():
                cb = self._callbacks.get(action)
                if cb:
                    keyboard.add_hotkey(combo, self._safe_call(cb))
                    logger.info(f"Hotkey registrada (Win): {combo} -> {action}")
            self._registered = True
            keyboard.wait()
        except Exception as e:
            logger.error(f"Error registrando hotkeys en Windows: {e}")

    def _register_linux(self):
        try:
            from pynput import keyboard as pynput_kb
            # Construir combinaciones pynput
            combos = {
                frozenset([pynput_kb.Key.ctrl, pynput_kb.Key.shift, pynput_kb.KeyCode.from_char('f')]): "capture_full",
                frozenset([pynput_kb.Key.ctrl, pynput_kb.Key.shift, pynput_kb.KeyCode.from_char('w')]): "capture_window",
                frozenset([pynput_kb.Key.ctrl, pynput_kb.Key.shift, pynput_kb.KeyCode.from_char('s')]): "capture_region",
            }
            pressed = set()

            def on_press(key):
                pressed.add(key)
                for combo_keys, action in combos.items():
                    if combo_keys.issubset(pressed):
                        cb = self._callbacks.get(action)
                        if cb:
                            threading.Thread(target=self._safe_call(cb), daemon=True).start()

            def on_release(key):
                pressed.discard(key)

            self._listener = pynput_kb.Listener(on_press=on_press, on_release=on_release)
            self._listener.start()
            self._registered = True
            logger.info("Hotkeys registradas (Linux/pynput)")
            self._listener.join()
        except Exception as e:
            logger.error(f"Error registrando hotkeys en Linux: {e}")

    def _safe_call(self, fn: Callable) -> Callable:
        """Envuelve el callback con manejo de excepciones."""
        def wrapper(*args, **kwargs):
            try:
                fn()
            except Exception as e:
                logger.error(f"Error en callback hotkey: {e}")
        return wrapper

    def stop(self):
        """Detiene el listener de hotkeys (solo Linux)."""
        if self._listener:
            self._listener.stop()
