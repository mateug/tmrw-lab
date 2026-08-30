"""Panel de configuración del eje de LEDs y Simulador Solar para Studio.

Incluye los submodos de construcción manual:
  1. Barrido por potencia absoluta (mW/cm²)
  2. Barrido por longitud de onda individual (%)
  3. Combinación multicanal
  4. Múltiples combinaciones encadenadas

Excluye explícitamente el submodo de lectura desde Excel (reservado a Lite).
"""
import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui, ui_font_label
from core.ui_kit.shared import crear_seccion_frame


def crear_panel_led(parent, vars_dict):
    """Crea el panel de control del eje de simulación solar y LEDs."""
    f_main = ttk.Frame(parent, style="Window.TFrame")

    f_sec = crear_seccion_frame(f_main, "Eje de Iluminación — Simulador Solar / LEDs", "params")
    f_sec.pack(fill="x", padx=ui(6), pady=ui(4))

    # Toggle activar eje
    f_act = ttk.Frame(f_sec, style="Window.TFrame")
    f_act.pack(fill="x", padx=ui(6), pady=ui(4))
    cb_act = ttk.Checkbutton(
        f_act,
        text="Activar eje de iluminación en la secuencia",
        variable=vars_dict["simulador_solar_activo"],
        style="Window.TCheckbutton",
    )
    cb_act.pack(side="left")

    ttk.Label(f_act, text="Puerto COM:", style="Window.TLabel").pack(side="left", padx=(ui(20), ui(4)))
    ttk.Entry(f_act, textvariable=vars_dict["solar_puerto_serie"], width=10).pack(side="left")

    # Selector de submodo de iluminación
    f_submodo = ttk.Frame(f_sec, style="Window.TFrame")
    f_submodo.pack(fill="x", padx=ui(6), pady=ui(4))
    ttk.Label(f_submodo, text="Submodo:", font=ui_font_label("bold"), style="Window.TLabel").pack(side="left", padx=ui(4))

    submodos = [
        ("Potencia Absoluta", "potencia"),
        ("Longitud de Onda", "longitud_onda"),
        ("Combinación Multicanal", "combinacion"),
        ("Múltiples Recetas", "multiples_combinaciones"),
    ]
    for texto, valor in submodos:
        ttk.Radiobutton(
            f_submodo,
            text=texto,
            variable=vars_dict["irradiancia_modo"],
            value=valor,
        ).pack(side="left", padx=ui(6))

    # Notebook con pestañas para cada submodo
    nb = ttk.Notebook(f_sec)
    nb.pack(fill="x", padx=ui(6), pady=ui(6))

    # --- Pestaña 1: Potencia Absoluta ---
    f_pot = ttk.Frame(nb, style="Window.TFrame")
    nb.add(f_pot, text="Potencia (mW/cm²)")
    f_p_grid = ttk.Frame(f_pot, style="Window.TFrame")
    f_p_grid.pack(fill="x", padx=ui(6), pady=ui(4))

    ttk.Label(f_p_grid, text="P inicial (mW/cm²):", style="Window.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_p_grid, textvariable=vars_dict["solar_p_ini"], width=10).grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Label(f_p_grid, text="P final (mW/cm²):", style="Window.TLabel").grid(row=0, column=2, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_p_grid, textvariable=vars_dict["solar_p_fin"], width=10).grid(row=0, column=3, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Label(f_p_grid, text="Paso (mW/cm²):", style="Window.TLabel").grid(row=0, column=4, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_p_grid, textvariable=vars_dict["solar_p_paso"], width=10).grid(row=0, column=5, sticky="w", padx=ui(4), pady=ui(3))

    ttk.Label(f_p_grid, text="Lista personalizada (ej. 10,25,50,100):", style="Window.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_p_grid, textvariable=vars_dict["solar_p_custom"], width=30).grid(row=1, column=2, columnspan=3, sticky="w", padx=ui(4), pady=ui(3))

    # --- Pestaña 2: Longitud de Onda ---
    f_wavelen = ttk.Frame(nb, style="Window.TFrame")
    nb.add(f_wavelen, text="Longitud de Onda")
    f_w_grid = ttk.Frame(f_wavelen, style="Window.TFrame")
    f_w_grid.pack(fill="x", padx=ui(6), pady=ui(4))

    ttk.Label(f_w_grid, text="Canal / Longitud:", style="Window.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(3))
    canales_disponibles = ["390", "450", "515", "cool_white", "warm_white", "600", "630", "660", "730", "850", "950"]
    cb_ch = ttk.Combobox(f_w_grid, textvariable=vars_dict["solar_canal_seleccionado"], values=canales_disponibles, state="readonly", width=14)
    cb_ch.grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(3))

    ttk.Label(f_w_grid, text="I inicial (%):", style="Window.TLabel").grid(row=0, column=2, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_w_grid, textvariable=vars_dict["solar_i_ini"], width=8).grid(row=0, column=3, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Label(f_w_grid, text="I final (%):", style="Window.TLabel").grid(row=0, column=4, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_w_grid, textvariable=vars_dict["solar_i_fin"], width=8).grid(row=0, column=5, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Label(f_w_grid, text="Paso (%):", style="Window.TLabel").grid(row=0, column=6, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_w_grid, textvariable=vars_dict["solar_i_paso"], width=8).grid(row=0, column=7, sticky="w", padx=ui(4), pady=ui(3))

    # --- Pestaña 3: Combinación Multicanal ---
    f_comb = ttk.Frame(nb, style="Window.TFrame")
    nb.add(f_comb, text="Combinación Multicanal")
    f_c_grid = ttk.Frame(f_comb, style="Window.TFrame")
    f_c_grid.pack(fill="x", padx=ui(6), pady=ui(4))

    ttk.Label(f_c_grid, text="Canal 1:", style="Window.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4))
    ttk.Entry(f_c_grid, textvariable=vars_dict["solar_comb_ch1"], width=8).grid(row=0, column=1, sticky="w", padx=ui(4))
    ttk.Label(f_c_grid, text="Intensidades (%):", style="Window.TLabel").grid(row=0, column=2, sticky="w", padx=ui(4))
    ttk.Entry(f_c_grid, textvariable=vars_dict["solar_comb_val1"], width=18).grid(row=0, column=3, sticky="w", padx=ui(4))

    ttk.Label(f_c_grid, text="Canal 2:", style="Window.TLabel").grid(row=1, column=0, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_c_grid, textvariable=vars_dict["solar_comb_ch2"], width=8).grid(row=1, column=1, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Label(f_c_grid, text="Intensidades (%):", style="Window.TLabel").grid(row=1, column=2, sticky="w", padx=ui(4), pady=ui(3))
    ttk.Entry(f_c_grid, textvariable=vars_dict["solar_comb_val2"], width=18).grid(row=1, column=3, sticky="w", padx=ui(4), pady=ui(3))

    # Tiempos de estabilización
    f_times = ttk.Frame(f_sec, style="Window.TFrame")
    f_times.pack(fill="x", padx=ui(6), pady=ui(2))
    ttk.Label(f_times, text="Espera encendido (s):", style="Window.TLabel").pack(side="left", padx=ui(4))
    ttk.Entry(f_times, textvariable=vars_dict["solar_espera_encendido_s"], width=8).pack(side="left", padx=ui(4))
    ttk.Label(f_times, text="Espera estabilización (s):", style="Window.TLabel").pack(side="left", padx=(ui(12), ui(4)))
    ttk.Entry(f_times, textvariable=vars_dict["solar_espera_estab_s"], width=8).pack(side="left", padx=ui(4))
    ttk.Checkbutton(f_times, text="Apagar al finalizar secuencia", variable=vars_dict["solar_apagar_al_final"]).pack(side="left", padx=ui(12))

    return f_main
