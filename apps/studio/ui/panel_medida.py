"""Panel fijo de configuración de medida, guardado y SMU Keithley 2450 para Studio.

Sigue la estructura, estilos temáticos y jerarquía visual de iv-maker:
  [1] Guardado de Datos (encima de Keithley)
  [2] Keithley 2450 — Barrido I-V
  [3] Combinatoria de Ejes Activos (con explicación didáctica y ejemplos)
  [4] Control de Medición (con botonería estilizada: Primary, Quick, Danger, Tool)
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
    # [2] Keithley 2450 — Barrido I-V
    # =========================================================================
    f_smu = crear_seccion_frame(f_main, "[2] Keithley 2450 — Barrido I-V", "keithley")
    f_smu.pack(fill="x", padx=ui(4), pady=ui(4))

    # Fila Hardware y Recurso VISA
    f_top_smu = ttk.Frame(f_smu, style="Keithley.TFrame")
    f_top_smu.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_top_smu, text="Hardware:", style="Keithley.TLabel").pack(side="left")
    ttk.Label(f_top_smu, text="Keithley 2450 (SMU)", foreground="#0284c7", style="Keithley.TLabel").pack(side="left", padx=(ui(4), ui(12)))

    ttk.Label(f_top_smu, text="Recurso VISA:", style="Keithley.TLabel").pack(side="left", padx=(ui(6), ui(4)))
    ttk.Entry(f_top_smu, textvariable=vars_dict["recurso_visa"], width=18).pack(side="left")

    # Grid de parámetros I-V
    f_grid = ttk.Frame(f_smu, style="Keithley.TFrame")
    f_grid.pack(fill="x", padx=ui(6), pady=ui(4))

    labels_entries = [
        ("Modo de medida:", "modo_medida", ["completa", "directa", "inversa"]),
        ("I máx (µA):", "i_max_uA", None),
        ("Superficie (µm²):", "superficie_um2", None),
        ("V ini directa (mV):", "v_ini_dir", None),
        ("V fin directa (mV):", "v_fin_dir", None),
        ("Paso directa (mV):", "paso_dir", None),
        ("V fin inversa (V):", "v_fin_inv", None),
        ("Paso inversa (mV):", "paso_inv", None),
        ("Irradiancia (mW/cm²):", "irradiancia_mW_cm2", None),
    ]

    for idx, (lbl, var_name, options) in enumerate(labels_entries):
        row = idx // 3
        col = (idx % 3) * 2
        ttk.Label(f_grid, text=lbl, style="Keithley.TLabel").grid(row=row, column=col, sticky="w", padx=ui(4), pady=ui(2))
        if options:
            cb = ttk.Combobox(f_grid, textvariable=vars_dict[var_name], values=options, state="readonly", width=11)
            cb.grid(row=row, column=col + 1, sticky="w", padx=ui(4), pady=ui(2))
        else:
            ttk.Entry(f_grid, textvariable=vars_dict[var_name], width=12).grid(row=row, column=col + 1, sticky="w", padx=ui(4), pady=ui(2))

    # Opciones de medición y delays
    f_opts = ttk.Frame(f_smu, style="Keithley.TFrame")
    f_opts.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Checkbutton(f_opts, text="Invertir eje Y", variable=vars_dict["invertir_eje_y"], style="Keithley.TCheckbutton").pack(side="left", padx=ui(4))
    ttk.Checkbutton(f_opts, text="Sense 4 hilos (tensión real)", variable=vars_dict["medir_tension_real"], style="Keithley.TCheckbutton").pack(side="left", padx=ui(10))

    # =========================================================================
    # [3] Relación entre Ejes Activos (Con explicación didáctica y ejemplo)
    # =========================================================================
    f_comb = crear_seccion_frame(f_main, "[3] Combinatoria de Ejes Activos", "params")
    f_comb.pack(fill="x", padx=ui(4), pady=ui(4))

    f_radios = ttk.Frame(f_comb, style="Params.TFrame")
    f_radios.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_radios, text="Relación entre ejes:", style="Params.TLabel").pack(side="left", padx=ui(4))
    ttk.Radiobutton(f_radios, text="Producto cartesiano (1-N)", variable=vars_dict["relacion_ejes"], value="1-N", style="Params.TRadiobutton").pack(side="left", padx=ui(8))
    ttk.Radiobutton(f_radios, text="Emparejamiento directo (1-1)", variable=vars_dict["relacion_ejes"], value="1-1", style="Params.TRadiobutton").pack(side="left", padx=ui(8))

    # Explicación con ejemplos
    f_expl = ttk.Frame(f_comb, style="Params.TFrame")
    f_expl.pack(fill="x", padx=ui(6), pady=(ui(2), ui(4)))

    # Configurar pesos de columna para que distribuyan el espacio equitativamente
    f_expl.columnconfigure(0, weight=1)
    f_expl.columnconfigure(1, weight=1)

    ttk.Label(
        f_expl,
        text=(
            "• Producto cartesiano (1-N): Se miden todas las combinaciones posibles entre los ejes activos.\n"
            "  Ejemplo: 3 posiciones de motor × 4 longitudes de onda LED = 12 medidas en total."
        ),
        font=ui_font("Segoe UI", 4.5),
        foreground=theme_mgr.get_current_theme().get("fg_muted", "#475569"),
        style="Params.TLabel",
        justify="left",
    ).grid(row=0, column=0, sticky="nw", padx=ui(4)) # Añadido row=0 y sticky "nw"

    ttk.Label(
        f_expl,
        text=(
            "• Emparejamiento directo (1-1): Se empareja el paso i de un eje con el paso i del otro.\n"
            "  Ejemplo: Posición 1 con LED 1, Posición 2 con LED 2, etc. (2 medidas en total)."
        ),
        font=ui_font("Segoe UI", 4.5),
        foreground=theme_mgr.get_current_theme().get("fg_muted", "#475569"),
        style="Params.TLabel",
        justify="left",
    ).grid(row=0, column=1, sticky="nw", padx=ui(4)) # Añadido row=0 y sticky "nw"


    # =========================================================================
    # [4] Control de Medición (Botonería estilizada)
    # =========================================================================
    f_ctrl_sec = crear_seccion_frame(f_main, "[4] Control de Medición", "control")
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
