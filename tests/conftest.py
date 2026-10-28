"""Configuración de pytest para el proyecto text-img-extractor."""
import sys
import os

# Asegurar que src/ esté en el path para todos los tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
