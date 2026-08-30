"""Panel de configuración del eje de estructura para Studio."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui, ui_font_label
from core.ui_kit.shared import crear_seccion_frame


class PanelEjeEstructura(ttk.Frame):
    """Panel de configuración de conmutación de estructuras."""

    def __init__(self, parent, vars_dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.vars = vars_dict
        self._build()

    def _build(self):
        self.configure(style="Window.TFrame")

        f_sec = crear_seccion_frame(self, "Eje de Estructura — Conmutación por Relé", "params")
        f_sec.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        # Toggle activar eje
        f_act = ttk.Frame(f_sec, style="Window.TFrame")
        f_act.pack(fill="x", padx=ui(6), pady=ui(4))
        ttk.Checkbutton(
            f_act,
            text="Activar eje de estructura en la secuencia",
            variable=self.vars["eje_estructura_activo"],
        ).pack(side="left")

        # Lista de estructuras disponibles y espera
        f_info = ttk.Frame(f_sec, style="Window.TFrame")
        f_info.pack(fill="x", padx=ui(6), pady=ui(4))

        ttk.Label(f_info, text="Estructuras a barrer (separadas por comas):").grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_info, textvariable=self.vars.get("estructura_lista", self.vars.get("estructuras_lista")), width=30).grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(2))

        ttk.Label(f_info, text="Espera conmutación relé (s):").grid(row=1, column=0, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_info, textvariable=self.vars.get("estructura_espera_s"), width=8).grid(row=1, column=1, sticky="w", padx=ui(4), pady=ui(2))

        # Nota de hardware
        f_hw = ttk.Frame(f_sec, style="Window.TFrame")
        f_hw.pack(fill="x", padx=ui(6), pady=ui(6))
        ttk.Label(
            f_hw,
            text="Hardware: relé de conmutación de dispositivo (controlado vía core/instrument/relay_structure.py)",
            foreground="#64748b",
        ).pack(side="left", padx=ui(4))


def crear_panel_estructura(parent, vars_dict):
    return PanelEjeEstructura(parent, vars_dict)
