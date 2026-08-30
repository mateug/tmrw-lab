"""Carga de assets (logos, iconos) para la UI de TMRW Lab.

Los archivos de imagen viven en core/ui_kit/assets/.
"""
from __future__ import annotations
from pathlib import Path

_ASSETS_DIR = Path(__file__).parent / "assets"


def load_logo(filename: str, size: tuple[int, int] | None = None):
    """Carga un logo y devuelve un PhotoImage de Tkinter (o None si falla).

    Args:
        filename: nombre del archivo dentro de core/ui_kit/assets/
        size: tupla (ancho, alto) en píxeles para redimensionar. None = tamaño original.
    """
    ruta = _ASSETS_DIR / filename
    if not ruta.exists():
        return None
    try:
        from PIL import Image, ImageTk
        img = Image.open(ruta)
        if size is not None:
            img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def assets_dir() -> Path:
    """Devuelve el directorio de assets."""
    return _ASSETS_DIR
