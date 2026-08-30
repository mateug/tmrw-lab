"""Panel de configuración del eje de estructura para Studio."""
import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui, ui_font_label
from core.ui_kit.shared import crear_seccion_frame


def crear_panel_estructura(parent, vars_dict):
    """Crea el panel de configuración del eje de estructura."""
    f_main = ttk.Frame(parent, style="Window.TFrame")

    f_sec = crear_seccion_frame(f_main, "Eje de Estructura — Conmutación por Relé", "params")
    f_sec.pack(fill="x", padx=ui(6), pady=ui(4))

    # Toggle activar eje
    f_act = ttk.Frame(f_sec, style="Window.TFrame")
    f_act.pack(fill="x", padx=ui(6), pady=ui(4))
    cb_act = ttk.Checkbutton(
        f_act,
        text="Activar eje de estructura en la secuencia",
        variable=vars_dict["eje_estructura_activo"],
        style="Window.TCheckbutton",
    )
    cb_act.pack(side="left")

    # Lista de estructuras disponibles
    f_info = ttk.Frame(f_sec, style="Window.TFrame")
    f_info.pack(fill="x", padx=ui(6), pady=ui(4))
    ttk.Label(
        f_info,
        text="Estructuras a barrer (separadas por comas):",
        style="Window.TLabel",
    ).grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(2))

    ttk.Entry(
        f_info,
        textvariable=vars_dict["estructuras_lista"],
        width=40,
    ).grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(2))

    # Hardware status note
    f_hw = ttk.Frame(f_sec, style="Window.TFrame")
    f_hw.pack(fill="x", padx=ui(6), pady=ui(6))
    ttk.Label(
        f_hw,
        text="Hardware: relé de estructura gestionado por core/instrument/relay_structure.py",
        foreground="#64748b",
        font=ui_font_label(),
    ).pack(side="left", padx=ui(4))

    return f_main
