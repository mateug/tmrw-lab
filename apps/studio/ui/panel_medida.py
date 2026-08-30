"""Panel de configuración de medida y SMU Keithley 2450 para Studio."""
import tkinter as tk
from tkinter import ttk, scrolledtext

from core.ui_kit.scaler import ui, ui_font, ui_font_console, ui_font_label, UIConfig
from core.ui_kit.shared import crear_seccion_frame, crear_campo_directorio
from core.ui_kit.theme import theme_mgr


def crear_panel_medida(parent, vars_dict, callback_iniciar, callback_abortar):
    """Crea el panel principal de parámetros del Keithley 2450 y controles de ejecución."""
    t = theme_mgr.get_current_theme()
    f_main = ttk.Frame(parent, style="Window.TFrame")

    # ---- 1. Parámetros del Keithley 2450 ----
    f_smu = crear_seccion_frame(f_main, "1. Keithley 2450 — Barrido I-V", "keithley")
    f_smu.pack(fill="x", padx=ui(6), pady=ui(4))

    # Recurso VISA e indicación de hardware
    f_top_smu = ttk.Frame(f_smu, style="Window.TFrame")
    f_top_smu.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_top_smu, text="Hardware requerido:", font=ui_font_label("bold"), style="Window.TLabel").pack(side="left")
    ttk.Label(f_top_smu, text="Keithley 2450 (SMU)", foreground="#0284c7", font=ui_font_label("bold")).pack(side="left", padx=ui(6))

    ttk.Label(f_top_smu, text="Recurso VISA:", style="Window.TLabel").pack(side="left", padx=(ui(16), ui(4)))
    ttk.Entry(f_top_smu, textvariable=vars_dict["recurso_visa"], width=20).pack(side="left")

    # Grid de parámetros I-V
    f_grid = ttk.Frame(f_smu, style="Window.TFrame")
    f_grid.pack(fill="x", padx=ui(6), pady=ui(4))

    labels_entries = [
        ("Modo de medida:", "modo_medida", ["completa", "directa", "inversa"]),
        ("I máx (µA):", "i_max_uA", None),
        ("V ini directa (mV):", "v_ini_dir", None),
        ("V fin directa (mV):", "v_fin_dir", None),
        ("Paso directa (mV):", "paso_dir", None),
        ("V fin inversa (V):", "v_fin_inv", None),
        ("Paso inversa (mV):", "paso_inv", None),
        ("Superficie (µm²):", "superficie_um2", None),
        ("Irradiancia (mW/cm²):", "irradiancia_mW_cm2", None),
    ]

    for idx, (lbl, var_name, options) in enumerate(labels_entries):
        row = idx // 3
        col = (idx % 3) * 2
        ttk.Label(f_grid, text=lbl, style="Window.TLabel").grid(row=row, column=col, sticky="w", padx=ui(4), pady=ui(3))
        if options:
            cb = ttk.Combobox(f_grid, textvariable=vars_dict[var_name], values=options, state="readonly", width=12)
            cb.grid(row=row, column=col + 1, sticky="w", padx=ui(4), pady=ui(3))
        else:
            ttk.Entry(f_grid, textvariable=vars_dict[var_name], width=14).grid(row=row, column=col + 1, sticky="w", padx=ui(4), pady=ui(3))

    # Opciones adicionales
    f_opts = ttk.Frame(f_smu, style="Window.TFrame")
    f_opts.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Checkbutton(f_opts, text="Invertir eje Y en gráficas", variable=vars_dict["invertir_eje_y"]).pack(side="left", padx=ui(4))
    ttk.Checkbutton(f_opts, text="Medir tensión real (4 hilos / Sense)", variable=vars_dict["medir_tension_real"]).pack(side="left", padx=ui(12))

    # ---- 2. Carpeta de salida y nombre ----
    f_salida = crear_seccion_frame(f_main, "2. Guardado de Datos", "params")
    f_salida.pack(fill="x", padx=ui(6), pady=ui(4))

    f_dir = ttk.Frame(f_salida, style="Window.TFrame")
    f_dir.pack(fill="x", padx=ui(6), pady=ui(2))
    crear_campo_directorio(f_dir, vars_dict["carpeta_salida"], 0, "Carpeta base:")

    f_nom = ttk.Frame(f_salida, style="Window.TFrame")
    f_nom.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_nom, text="Subcarpeta:", style="Window.TLabel").pack(side="left", padx=ui(4))
    ttk.Entry(f_nom, textvariable=vars_dict["nombre_carpeta_medida"], width=18).pack(side="left", padx=ui(4))
    ttk.Label(f_nom, text="Prefijo medida:", style="Window.TLabel").pack(side="left", padx=(ui(12), ui(4)))
    ttk.Entry(f_nom, textvariable=vars_dict["nombre_medida"], width=22).pack(side="left", padx=ui(4))

    # Combinatoria de ejes
    f_comb = ttk.Frame(f_salida, style="Window.TFrame")
    f_comb.pack(fill="x", padx=ui(6), pady=ui(4))
    ttk.Label(f_comb, text="Relación entre ejes activos:", font=ui_font_label("bold"), style="Window.TLabel").pack(side="left", padx=ui(4))
    ttk.Radiobutton(f_comb, text="Producto cartesiano (1-N)", variable=vars_dict["relacion_ejes"], value="1-N").pack(side="left", padx=ui(6))
    ttk.Radiobutton(f_comb, text="Emparejamiento directo (1-1)", variable=vars_dict["relacion_ejes"], value="1-1").pack(side="left", padx=ui(6))

    # ---- 3. Botonera de Control ----
    f_ctrl = ttk.Frame(f_main, style="Window.TFrame")
    f_ctrl.pack(fill="x", padx=ui(6), pady=ui(8))

    btn_start = tk.Button(
        f_ctrl, text="▶ Iniciar Secuencia",
        bg=t["buttons"]["primary_bg"], fg=t["buttons"]["primary_fg"],
        activebackground=t["buttons"]["primary_hover"], activeforeground="#ffffff",
        font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
        command=callback_iniciar, padx=ui(14), pady=ui(6), relief="flat", cursor="hand2",
    )
    btn_start.pack(side="left", padx=ui(6))

    btn_stop = tk.Button(
        f_ctrl, text="⏹ Abortar Medida",
        bg=t["buttons"]["danger_bg"], fg=t["buttons"]["danger_fg"],
        activebackground=t["buttons"]["danger_hover"], activeforeground="#ffffff",
        font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
        command=callback_abortar, padx=ui(14), pady=ui(6), relief="flat", cursor="hand2",
    )
    btn_stop.pack(side="left", padx=ui(6))

    return f_main, btn_start, btn_stop
