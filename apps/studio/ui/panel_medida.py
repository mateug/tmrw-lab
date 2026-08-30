"""Panel fijo de configuración de medida, guardado y SMU Keithley 2450 para Studio."""
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
    """Crea la sección fija izquierda de Studio: Guardado de datos, Keithley 2450 y Relación de ejes."""
    t = theme_mgr.get_current_theme()
    f_main = ttk.Frame(parent, style="Window.TFrame")

    # =========================================================================
    # [1] Guardado de Datos (ENCIMA de Keithley 2450)
    # =========================================================================
    f_salida = crear_seccion_frame(f_main, "[1] Guardado de Datos", "params")
    f_salida.pack(fill="x", padx=ui(4), pady=(ui(2), ui(4)))

    f_dir = ttk.Frame(f_salida, style="Window.TFrame")
    f_dir.pack(fill="x", padx=ui(6), pady=ui(2))
    crear_campo_directorio(f_dir, vars_dict["carpeta_salida"], 0, "Carpeta base:")

    f_nom = ttk.Frame(f_salida, style="Window.TFrame")
    f_nom.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_nom, text="Subcarpeta:", style="Window.TLabel").pack(side="left", padx=ui(4))
    ttk.Entry(f_nom, textvariable=vars_dict["nombre_carpeta_medida"], width=16).pack(side="left", padx=ui(4))
    ttk.Label(f_nom, text="Prefijo medida:", style="Window.TLabel").pack(side="left", padx=(ui(10), ui(4)))
    ttk.Entry(f_nom, textvariable=vars_dict["nombre_medida"], width=20).pack(side="left", padx=ui(4))

    # =========================================================================
    # [2] Keithley 2450 — Barrido I-V
    # =========================================================================
    f_smu = crear_seccion_frame(f_main, "[2] Keithley 2450 — Barrido I-V", "keithley")
    f_smu.pack(fill="x", padx=ui(4), pady=ui(4))

    # Hardware requerido y VISA
    f_top_smu = ttk.Frame(f_smu, style="Window.TFrame")
    f_top_smu.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_top_smu, text="Hardware requerido:", style="Window.TLabel").pack(side="left")
    ttk.Label(f_top_smu, text="Keithley 2450 (SMU)", foreground="#0284c7").pack(side="left", padx=ui(6))

    ttk.Label(f_top_smu, text="Recurso VISA:", style="Window.TLabel").pack(side="left", padx=(ui(14), ui(4)))
    ttk.Entry(f_top_smu, textvariable=vars_dict["recurso_visa"], width=18).pack(side="left")

    # Grid de parámetros I-V
    f_grid = ttk.Frame(f_smu, style="Window.TFrame")
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
        ttk.Label(f_grid, text=lbl, style="Window.TLabel").grid(row=row, column=col, sticky="w", padx=ui(4), pady=ui(2))
        if options:
            cb = ttk.Combobox(f_grid, textvariable=vars_dict[var_name], values=options, state="readonly", width=11)
            cb.grid(row=row, column=col + 1, sticky="w", padx=ui(4), pady=ui(2))
        else:
            ttk.Entry(f_grid, textvariable=vars_dict[var_name], width=12).grid(row=row, column=col + 1, sticky="w", padx=ui(4), pady=ui(2))

    # Opciones de medición y delays
    f_opts = ttk.Frame(f_smu, style="Window.TFrame")
    f_opts.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Checkbutton(f_opts, text="Invertir eje Y", variable=vars_dict["invertir_eje_y"]).pack(side="left", padx=ui(4))
    ttk.Checkbutton(f_opts, text="Sense 4 hilos (tensión real)", variable=vars_dict["medir_tension_real"]).pack(side="left", padx=ui(10))

    # =========================================================================
    # [3] Relación entre Ejes Activos (Con explicación didáctica y ejemplo)
    # =========================================================================
    f_comb = crear_seccion_frame(f_main, "[3] Combinatoria de Ejes Activos", "params")
    f_comb.pack(fill="x", padx=ui(4), pady=ui(4))

    f_radios = ttk.Frame(f_comb, style="Window.TFrame")
    f_radios.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_radios, text="Relación entre ejes:", style="Window.TLabel").pack(side="left", padx=ui(4))
    ttk.Radiobutton(f_radios, text="Producto cartesiano (1-N)", variable=vars_dict["relacion_ejes"], value="1-N").pack(side="left", padx=ui(8))
    ttk.Radiobutton(f_radios, text="Emparejamiento directo (1-1)", variable=vars_dict["relacion_ejes"], value="1-1").pack(side="left", padx=ui(8))

    # Explicación con ejemplos
    f_expl = ttk.Frame(f_comb, style="Window.TFrame")
    f_expl.pack(fill="x", padx=ui(6), pady=(ui(2), ui(4)))
    ttk.Label(
        f_expl,
        text=(
            "• Producto cartesiano (1-N): Se miden todas las combinaciones posibles entre los ejes activos.\n"
            "  Ejemplo: 3 posiciones de motor × 4 longitudes de onda LED = 12 medidas en total.\n"
            "• Emparejamiento directo (1-1): Se empareja el paso i de un eje con el paso i del otro.\n"
            "  Ejemplo: Posición 1 con LED 1, Posición 2 con LED 2, etc. (3 medidas en total)."
        ),
        font=ui_font("Segoe UI", 4.5),
        foreground=t.get("fg_muted", "#475569"),
        justify="left",
    ).pack(anchor="w", padx=ui(4))

    # =========================================================================
    # Botonera de Control de Studio
    # =========================================================================
    f_ctrl = ttk.Frame(f_main, style="Window.TFrame")
    f_ctrl.pack(fill="x", padx=ui(4), pady=ui(6))

    btn_start = tk.Button(
        f_ctrl, text="▶ INICIAR SECUENCIA",
        bg=t["buttons"]["primary_bg"], fg=t["buttons"]["primary_fg"],
        activebackground=t["buttons"]["primary_hover"], activeforeground="#ffffff",
        font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
        command=callback_iniciar, padx=ui(12), pady=ui(5), relief="flat", cursor="hand2",
    )
    btn_start.pack(side="left", padx=ui(4))

    btn_quick = tk.Button(
        f_ctrl, text="⚡ Medida Rápida",
        bg=t["buttons"]["quick_bg"], fg=t["buttons"]["quick_fg"],
        activebackground=t["buttons"]["quick_hover"], activeforeground="#ffffff",
        font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
        command=callback_rapida, padx=ui(10), pady=ui(5), relief="flat", cursor="hand2",
    )
    btn_quick.pack(side="left", padx=ui(4))

    btn_stop = tk.Button(
        f_ctrl, text="⏹ DETENER / ABORTAR",
        bg=t["buttons"]["danger_bg"], fg=t["buttons"]["danger_fg"],
        activebackground=t["buttons"]["danger_hover"], activeforeground="#ffffff",
        font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
        command=callback_abortar, padx=ui(10), pady=ui(5), relief="flat", cursor="hand2",
        state="disabled",
    )
    btn_stop.pack(side="left", padx=ui(4))

    btn_manual = tk.Button(
        f_ctrl, text="⚙ Liberar Keithley",
        bg=t["buttons"]["tool_bg"], fg=t["buttons"]["tool_fg"],
        activebackground=t["buttons"]["tool_hover"], activeforeground="#ffffff",
        font=ui_font("Segoe UI", UIConfig.SIZE_LABEL),
        command=callback_modo_manual, padx=ui(8), pady=ui(5), relief="flat", cursor="hand2",
    )
    btn_manual.pack(side="left", padx=ui(4))

    return f_main, btn_start, btn_quick, btn_stop, btn_manual
