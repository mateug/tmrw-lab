"""
TMRW Lab — Punto de entrada único.

Lanza el menú de bienvenida, inyectando los modos registrados en apps/__init__.py.
"""
from apps import APP_REGISTRY
from core.ui_kit.menu import launch

if __name__ == "__main__":
    launch(app_registry=APP_REGISTRY)
