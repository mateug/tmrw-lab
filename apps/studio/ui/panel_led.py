"""Panel completo del eje de Iluminación y Simulador Solar para Studio.

Implementa con máxima fidelidad los submodos de construcción manual de iv-maker:
  1. Submodo A: Potencia Absoluta (mW/cm²)
  2. Submodo B: Longitudes de Onda Individuales (11 canales Ossila)
  3. Submodo C: Combinación Multi-Canal Dinámica (matriz de canales y selector 1-1 / 1-N)
  4. Submodo D: Múltiples Recetas Encadenadas

Incluye tiempos de estabilización, encendido previo y tiempos de enfriamiento.
Excluye explícitamente el submodo de lectura de Excel (reservado a Lite).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui, ui_font, ui_font_label, UIConfig
from core.ui_kit.shared import crear_seccion_frame
from core.ui_kit.theme import theme_mgr


class PanelEjeIluminacion(ttk.Frame):
    """Panel de configuración de iluminación y LEDs multicanal."""

    SOLAR_CANALES = [
        ("390 nm", "390"),
        ("450 nm", "450"),
        ("515 nm", "515"),
        ("Cool White", "cool_white"),
        ("Warm White", "warm_white"),
        ("600 nm", "600"),
        ("630 nm", "630"),
        ("660 nm", "660"),
        ("730 nm", "730"),
        ("850 nm", "850"),
        ("950 nm", "950"),
    ]

    def __init__(self, parent, vars_dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.vars = vars_dict
        self._filas_comb_widgets = []
        self._build()

    def _build(self):
        t = theme_mgr.get_current_theme()
        self.configure(style="Window.TFrame")

        f_sec = crear_seccion_frame(self, "Eje de Iluminación — Simulador Solar / LEDs Ossila", "params")
        f_sec.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        # Toggle activar eje general y conexión serie
        f_top = ttk.Frame(f_sec, style="Window.TFrame")
        f_top.pack(fill="x", padx=ui(6), pady=ui(3))

        ttk.Checkbutton(
            f_top,
            text="Activar eje de iluminación en la secuencia",
            variable=self.vars["simulador_solar_activo"],
        ).pack(side="left")

        ttk.Label(f_top, text="Puerto COM:").pack(side="left", padx=(ui(20), ui(4)))
        ttk.Entry(f_top, textvariable=self.vars["solar_puerto_serie"], width=8).pack(side="left", padx=(0, ui(12)))
        ttk.Label(f_top, text="Baudrate:").pack(side="left")
        ttk.Entry(f_top, textvariable=self.vars["solar_baudrate"], width=8).pack(side="left", padx=(0, ui(6)))

        # Selector de submodo de iluminación
        f_sub = ttk.Frame(f_sec, style="Window.TFrame")
        f_sub.pack(fill="x", padx=ui(6), pady=ui(3))
        ttk.Label(f_sub, text="Submodo:").pack(side="left", padx=(0, ui(6)))

        submodos = [
            ("A) Potencia Absoluta", "potencia"),
            ("B) Longitudes Individuales", "longitud_onda"),
            ("C) Combinación Multicanal", "combinacion"),
            ("D) Múltiples Recetas", "multiples_combinaciones"),
        ]
        for txt, val in submodos:
            ttk.Radiobutton(
                f_sub, text=txt, variable=self.vars["irradiancia_modo"], value=val
            ).pack(side="left", padx=ui(6))

        # Notebook de Submodos
        self.nb_submodos = ttk.Notebook(f_sec)
        self.nb_submodos.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        self._build_submodo_a()
        self._build_submodo_b()
        self._build_submodo_c()
        self._build_submodo_d()

        # Tiempos globales de estabilización y enfriamiento
        f_tiempos = ttk.LabelFrame(f_sec, text=" Control Temporal y Enfriamiento Térmico ", padding=ui(6))
        f_tiempos.pack(fill="x", padx=ui(4), pady=ui(4))

        f_t_grid = ttk.Frame(f_tiempos, style="Window.TFrame")
        f_t_grid.pack(fill="x", pady=ui(2))
        ttk.Label(f_t_grid, text="Espera encendido previo (s):").grid(row=0, column=0, sticky="w", padx=ui(4))
        ttk.Entry(f_t_grid, textvariable=self.vars["solar_espera_encendido_s"], width=8).grid(row=0, column=1, sticky="w", padx=ui(4))
        ttk.Label(f_t_grid, text="Espera estabilización óptica (s):").grid(row=0, column=2, sticky="w", padx=(ui(12), ui(4)))
        ttk.Entry(f_t_grid, textvariable=self.vars["solar_espera_estab_s"], width=8).grid(row=0, column=3, sticky="w", padx=ui(4))
        ttk.Label(f_t_grid, text="Tiempo enfriamiento/reposo (s):").grid(row=0, column=4, sticky="w", padx=(ui(12), ui(4)))
        ttk.Entry(f_t_grid, textvariable=self.vars["solar_tiempo_enfriado_s"], width=8).grid(row=0, column=5, sticky="w", padx=ui(4))

        f_t_opt = ttk.Frame(f_tiempos, style="Window.TFrame")
        f_t_opt.pack(fill="x", pady=(ui(3), 0))
        ttk.Checkbutton(f_t_opt, text="Apagar LEDs al finalizar la secuencia", variable=self.vars["solar_apagar_al_final"]).pack(side="left", padx=ui(4))

    # ── Submodo A: Potencia Absoluta ─────────────────────────────────────────
    def _build_submodo_a(self):
        f = ttk.Frame(self.nb_submodos, style="Window.TFrame")
        self.nb_submodos.add(f, text="A) Potencia Absoluta")

        f_grid = ttk.Frame(f, style="Window.TFrame")
        f_grid.pack(fill="x", padx=ui(6), pady=ui(4))

        ttk.Label(f_grid, text="P inicial (mW/cm²):").grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_ini"], width=10).grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Label(f_grid, text="P final (mW/cm²):").grid(row=0, column=2, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_fin"], width=10).grid(row=0, column=3, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Label(f_grid, text="Paso (mW/cm²):").grid(row=0, column=4, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_paso"], width=10).grid(row=0, column=5, sticky="w", padx=ui(4), pady=ui(2))

        ttk.Label(f_grid, text="Lista potencias personalizada (mW/cm²):").grid(row=1, column=0, columnspan=2, sticky="w", padx=ui(4), pady=ui(3))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_custom"], width=35).grid(row=1, column=2, columnspan=4, sticky="w", padx=ui(4), pady=ui(3))

    # ── Submodo B: Longitudes de Onda Individuales ───────────────────────────
    def _build_submodo_b(self):
        f = ttk.Frame(self.nb_submodos, style="Window.TFrame")
        self.nb_submodos.add(f, text="B) Longitudes Individuales")

        # Checkboxes de canales Ossila
        lf_ch = ttk.LabelFrame(f, text=" Canales LED a Barrer ", padding=ui(4))
        lf_ch.pack(fill="x", padx=ui(4), pady=ui(2))

        f_ch_grid = ttk.Frame(lf_ch, style="Window.TFrame")
        f_ch_grid.pack(fill="x")

        for idx, (display, raw) in enumerate(self.SOLAR_CANALES):
            r = idx // 6
            c = idx % 6
            ttk.Checkbutton(f_ch_grid, text=display, variable=self.vars["solar_canales_seleccionados_dict"][raw]).grid(
                row=r, column=c, sticky="w", padx=ui(3), pady=ui(1)
            )

        f_btns_ch = ttk.Frame(lf_ch, style="Window.TFrame")
        f_btns_ch.pack(fill="x", pady=(ui(2), 0))
        ttk.Button(f_btns_ch, text="Seleccionar todos", command=self._sel_todos_canales).pack(side="left", padx=ui(3))
        ttk.Button(f_btns_ch, text="Limpiar todos", command=self._desel_todos_canales).pack(side="left", padx=ui(3))

        # Intensidades del barrido
        f_int = ttk.Frame(f, style="Window.TFrame")
        f_int.pack(fill="x", padx=ui(4), pady=ui(3))
        ttk.Label(f_int, text="I inicial (%):").grid(row=0, column=0, sticky="w", padx=ui(3))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_ini"], width=8).grid(row=0, column=1, sticky="w", padx=ui(3))
        ttk.Label(f_int, text="I final (%):").grid(row=0, column=2, sticky="w", padx=ui(3))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_fin"], width=8).grid(row=0, column=3, sticky="w", padx=ui(3))
        ttk.Label(f_int, text="Paso (%):").grid(row=0, column=4, sticky="w", padx=ui(3))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_paso"], width=8).grid(row=0, column=5, sticky="w", padx=ui(3))

        ttk.Label(f_int, text="Lista personalizada (%):").grid(row=1, column=0, columnspan=2, sticky="w", padx=ui(3), pady=ui(2))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_custom"], width=30).grid(row=1, column=2, columnspan=4, sticky="w", padx=ui(3), pady=ui(2))

    def _sel_todos_canales(self):
        for v in self.vars["solar_canales_seleccionados_dict"].values():
            v.set(True)

    def _desel_todos_canales(self):
        for v in self.vars["solar_canales_seleccionados_dict"].values():
            v.set(False)

    # ── Submodo C: Combinación Multi-Canal Dinámica ──────────────────────────
    def _build_submodo_c(self):
        f = ttk.Frame(self.nb_submodos, style="Window.TFrame")
        self.nb_submodos.add(f, text="C) Combinación Multi-Canal")

        f_top = ttk.Frame(f, style="Window.TFrame")
        f_top.pack(fill="x", padx=ui(4), pady=ui(3))
        ttk.Label(
            f_top,
            text="Define canales e intensidades (separadas por comas, ej: 0, 50, 100):",
        ).pack(side="left")
        ttk.Button(f_top, text="+ Añadir Canal", command=self._anadir_fila_comb).pack(side="right", padx=ui(4))

        self.f_matriz = ttk.Frame(f, style="Window.TFrame")
        self.f_matriz.pack(fill="both", expand=True, padx=ui(4), pady=ui(2))

        # Render inicial de filas combinadas
        self._render_filas_comb()

    def _render_filas_comb(self):
        for w in self.f_matriz.winfo_children():
            w.destroy()
        self._filas_comb_widgets.clear()

        for idx, item in enumerate(self.vars["solar_canales_comb_lista"]):
            row_frame = ttk.Frame(self.f_matriz, style="Window.TFrame")
            row_frame.pack(fill="x", pady=ui(2))

            ttk.Label(row_frame, text=f"Canal {idx + 1}:").pack(side="left", padx=ui(3))
            cb = ttk.Combobox(
                row_frame,
                values=[d for d, _ in self.SOLAR_CANALES],
                state="readonly",
                width=12,
            )
            # Encontrar display
            curr_raw = item.get("canal", "390")
            display_val = next((d for d, r in self.SOLAR_CANALES if r == curr_raw), curr_raw)
            cb.set(display_val)
            cb.pack(side="left", padx=ui(3))

            ttk.Label(row_frame, text="Intensidades (%):").pack(side="left", padx=(ui(8), ui(3)))
            entry_ints = ttk.Entry(row_frame, width=22)
            entry_ints.insert(0, str(item.get("intensidades", "100")))
            entry_ints.pack(side="left", padx=ui(3))

            btn_del = ttk.Button(row_frame, text="✕", width=3, command=lambda i=idx: self._quitar_fila_comb(i))
            btn_del.pack(side="left", padx=ui(4))

            self._filas_comb_widgets.append((cb, entry_ints))

    def _anadir_fila_comb(self):
        self._sincronizar_comb_data()
        self.vars["solar_canales_comb_lista"].append({"canal": "660", "intensidades": "0, 50, 100"})
        self._render_filas_comb()

    def _quitar_fila_comb(self, idx):
        self._sincronizar_comb_data()
        if len(self.vars["solar_canales_comb_lista"]) > 1:
            self.vars["solar_canales_comb_lista"].pop(idx)
            self._render_filas_comb()

    def _sincronizar_comb_data(self):
        nuevos = []
        for cb, entry in self._filas_comb_widgets:
            display_txt = cb.get()
            raw_val = next((r for d, r in self.SOLAR_CANALES if d == display_txt), display_txt)
            nuevos.append({"canal": raw_val, "intensidades": entry.get().strip()})
        self.vars["solar_canales_comb_lista"] = nuevos

    # ── Submodo D: Múltiples Recetas ─────────────────────────────────────────
    def _build_submodo_d(self):
        f = ttk.Frame(self.nb_submodos, style="Window.TFrame")
        self.nb_submodos.add(f, text="D) Múltiples Recetas")

        ttk.Label(
            f,
            text="Secuencia de combinaciones predefinidas:",
        ).pack(anchor="w", padx=ui(6), pady=ui(3))

        self.txt_recetas = tk.Text(f, height=5, width=45, font=ui_font("Consolas", 4.5))
        self.txt_recetas.pack(fill="both", expand=True, padx=ui(6), pady=ui(3))
        self.txt_recetas.insert("end", "# Formato: nombre_receta: canal1=val, canal2=val\nreceta_1: 950=100, 660=50\nreceta_2: 450=100, 515=80\n")


def crear_panel_led(parent, vars_dict):
    return PanelEjeIluminacion(parent, vars_dict)
