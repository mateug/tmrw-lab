"""Panel fijo de configuración de medida, guardado y SMU Keithley 2450 para Studio.

Sigue la estructura, estilos temáticos y jerarquía visual de iv-maker:
  [1] Guardado de Datos (encima de Keithley)
  [2] Keithley 2450 — Barrido I-V
  [3] Control de Medición (con botonería estilizada: Primary, Quick, Danger, Tool)
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui, ui_font, ui_font_label, UIConfig
from core.ui_kit.shared import crear_seccion_frame, crear_campo_directorio
from core.ui_kit.theme import theme_mgr


def crear_panel_medida_fijo(
    parent,
    vars_dict,
    callback_iniciar,
    callback_rapida,
    callback_abortar,
    callback_modo_manual,
):
    """Crea la sección fija izquierda de Studio con los estilos y temas de iv-maker."""
    f_main = ttk.Frame(parent, style="Window.TFrame")

    # =========================================================================
    # [1] Guardado de Datos (ENCIMA de Keithley 2450)
    # =========================================================================
    f_salida = crear_seccion_frame(f_main, "[1] Guardado de Datos", "params")
    f_salida.pack(fill="x", padx=ui(4), pady=(ui(2), ui(4)))

    f_dir = ttk.Frame(f_salida, style="Params.TFrame")
    f_dir.pack(fill="x", padx=ui(6), pady=ui(2))
    crear_campo_directorio(f_dir, vars_dict["carpeta_salida"], 0, "Carpeta base:")

    f_nom = ttk.Frame(f_salida, style="Params.TFrame")
    f_nom.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_nom, text="Subcarpeta:", style="Params.TLabel").pack(side="left", padx=ui(4))
    ttk.Entry(f_nom, textvariable=vars_dict["nombre_carpeta_medida"], width=16).pack(side="left", padx=ui(4))
    ttk.Label(f_nom, text="Prefijo medida:", style="Params.TLabel").pack(side="left", padx=(ui(10), ui(4)))
    ttk.Entry(f_nom, textvariable=vars_dict["nombre_medida"], width=20).pack(side="left", padx=ui(4))

    # =========================================================================
    # [2] Control de Medición (Botonería estilizada)
    # =========================================================================
    f_ctrl_sec = crear_seccion_frame(f_main, "[2] Control de Medición", "control")
    f_ctrl_sec.pack(fill="x", padx=ui(4), pady=ui(4))

    f_btns = ttk.Frame(f_ctrl_sec, style="Control.TFrame")
    f_btns.pack(fill="x", padx=ui(4), pady=ui(4))

    btn_start = ttk.Button(
        f_btns, text="▶ INICIAR SECUENCIA",
        style="Primary.TButton",
        command=callback_iniciar,
    )
    btn_start.pack(side="left", padx=ui(4))

    btn_quick = ttk.Button(
        f_btns, text="⚡ Medida Rápida",
        style="Quick.TButton",
        command=callback_rapida,
    )
    btn_quick.pack(side="left", padx=ui(4))

    btn_stop = ttk.Button(
        f_btns, text="⏹ DETENER / ABORTAR",
        style="Danger.TButton",
        command=callback_abortar,
        state="disabled",
    )
    btn_stop.pack(side="left", padx=ui(4))

    btn_manual = ttk.Button(
        f_btns, text="⚙ Liberar Keithley",
        style="Tool.TButton",
        command=callback_modo_manual,
    )
    btn_manual.pack(side="left", padx=ui(4))

    return f_main, btn_start, btn_quick, btn_stop, btn_manual
