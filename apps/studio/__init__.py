"""Manifest de apps/studio — modo Studio."""
import tkinter as tk
from tkinter import ttk


def _crear_frame(parent, callback_volver):
    from apps.studio.ui.frame import StudioFrame
    return StudioFrame(parent, callback_volver=callback_volver)


MANIFEST = {
    "id": "studio",
    "nombre": "Studio",
    "descripcion": (
        "Medidas IV con Keithley 2450.\n\n"
        "Ejes combinables:\n"
        "• Motores\n"
        "• LEDs\n"
        "• Estructuras.\n\n"
    ),
    "icono": "🔬",
    "icono_archivo": "studio",
    "crear_frame": _crear_frame,
}
