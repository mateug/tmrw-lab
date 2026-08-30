"""Registro explícito de modos de TMRW Lab.

Para añadir un modo nuevo:
  1. Crear su carpeta en apps/<nombre>/
  2. Definir su MANIFEST (id, nombre, descripcion, icono, crear_frame)
  3. Añadir una línea de import y añadirlo a APP_REGISTRY
  No es necesario tocar core/ui_kit/menu.py ni main.py.
"""
from apps.studio import MANIFEST as studio_manifest
from apps.lite import MANIFEST as lite_manifest
from apps.analytics import MANIFEST as analytics_manifest
from apps.stress import MANIFEST as stress_manifest

APP_REGISTRY = [
    studio_manifest,
    lite_manifest,
    analytics_manifest,
    stress_manifest,
]
