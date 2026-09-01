"""Panel completo del eje de Iluminación y Simulador Solar para Studio.

Implementa con máxima fidelidad los submodos de construcción manual de iv-maker:
  1. Submodo A: Potencia Absoluta (mW/cm²)
  2. Submodo B: Longitudes de Onda Individuales (11 canales Ossila)
  3. Submodo C: Combinación Multi-Canal Dinámica (matriz con scroll)
  4. Submodo D: Múltiples Recetas Encadenadas

Incluye explicaciones claras para los tiempos de estabilización, encendido previo y enfriamiento térmico.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui, ui_font, UIConfig
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

    # Mapeo de submodos ordenados según la pestaña (índice 0, 1, 2, 3)
    MAPEO_SUBMODOS = [
        "potencia",
        "longitud_onda",
        "combinacion",
        "multiples_combinaciones",
    ]

    def __init__(self, parent, vars_dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.vars = vars_dict
        self._filas_comb_widgets = []
        self._build()

    def _build(self):
        t = theme_mgr.get_current_theme()
        self.configure(style="Params.TFrame")

        f_sec = crear_seccion_frame(self, "Eje de Iluminación — Simulador Solar / LEDs Ossila", "params")
        f_sec.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        # 1. BARRA SUPERIOR (Puerto, Conexión, Activar)
        f_top = ttk.Frame(f_sec, style="Params.TFrame")
        f_top.pack(fill="x", side="top", padx=ui(6), pady=ui(3))

        ttk.Checkbutton(
            f_top,
            text="Activar eje de iluminación en la secuencia",
            variable=self.vars["simulador_solar_activo"],
            style="Params.TCheckbutton",
        ).pack(side="left")

        ttk.Label(f_top, text="Puerto COM:", style="Params.TLabel").pack(side="left", padx=(ui(20), ui(4)))
        ttk.Entry(f_top, textvariable=self.vars["solar_puerto_serie"], width=8).pack(side="left", padx=(0, ui(12)))
        ttk.Label(f_top, text="Baudrate:", style="Params.TLabel").pack(side="left")
        ttk.Entry(f_top, textvariable=self.vars["solar_baudrate"], width=8).pack(side="left", padx=(0, ui(6)))

        # 2. BLOQUE INFERIOR (Tiempos globales) - Empaquetado ANTES del Notebook en side="bottom" para garantizar su presencia
        f_tiempos = ttk.LabelFrame(f_sec, text=" Control Temporal y Enfriamiento Térmico ", padding=ui(6), style="Params.TLabelframe")
        f_tiempos.pack(fill="x", side="bottom", padx=ui(4), pady=ui(4))

        f_t_grid = ttk.Frame(f_tiempos, style="Params.TFrame")
        f_t_grid.pack(fill="x", pady=ui(2))
        ttk.Label(f_t_grid, text="Espera encendido previo (s):", style="Params.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4))
        ttk.Entry(f_t_grid, textvariable=self.vars["solar_espera_encendido_s"], width=8).grid(row=0, column=1, sticky="w", padx=ui(4))
        ttk.Label(f_t_grid, text="Espera estabilización óptica (s):", style="Params.TLabel").grid(row=0, column=2, sticky="w", padx=(ui(12), ui(4)))
        ttk.Entry(f_t_grid, textvariable=self.vars["solar_espera_estab_s"], width=8).grid(row=0, column=3, sticky="w", padx=ui(4))
        ttk.Label(f_t_grid, text="Tiempo enfriamiento/reposo (s):", style="Params.TLabel").grid(row=0, column=4, sticky="w", padx=(ui(12), ui(4)))
        ttk.Entry(f_t_grid, textvariable=self.vars["solar_tiempo_enfriado_s"], width=8).grid(row=0, column=5, sticky="w", padx=ui(4))

        f_exp = ttk.Frame(f_tiempos, style="Params.TFrame")
        f_exp.pack(fill="x", pady=(ui(4), ui(2)))
        ttk.Label(
            f_exp,
            text=(
                "• Espera encendido previo (s): Tiempo transcurrido con el LED encendido antes de que el SMU inicie el barrido I-V.\n"
                "• Espera estabilización óptica (s): Retardo tras modificar potencia o cambiar de canal LED para asentar la emisión.\n"
                "• Tiempo enfriamiento/reposo (s): Tiempo con luz apagada entre medidas consecutivas para evitar sobrecalentamiento."
            ),
            font=ui_font("Segoe UI", 4.5),
            foreground=t.get("fg_muted", "#475569"),
            style="Params.TLabel",
            justify="left",
        ).pack(anchor="w", padx=ui(4))

        f_t_opt = ttk.Frame(f_tiempos, style="Params.TFrame")
        f_t_opt.pack(fill="x", pady=(ui(3), 0))
        ttk.Checkbutton(f_t_opt, text="Apagar LEDs al finalizar la secuencia", variable=self.vars["solar_apagar_al_final"], style="Params.TCheckbutton").pack(side="left", padx=ui(4))

        # 3. NOTEBOOK CENTRAL (Submodos) - Ocupa el espacio central restante
        self.nb_submodos = ttk.Notebook(f_sec)
        self.nb_submodos.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        self._build_submodo_a()
        self._build_submodo_b()
        self._build_submodo_c()
        self._build_submodo_d()

        self.nb_submodos.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._sincronizar_pestana_inicial()

    def _on_tab_changed(self, event):
        idx = self.nb_submodos.index(self.nb_submodos.select())
        if 0 <= idx < len(self.MAPEO_SUBMODOS):
            self.vars["irradiancia_modo"].set(self.MAPEO_SUBMODOS[idx])

    def _sincronizar_pestana_inicial(self):
        modo_actual = self.vars["irradiancia_modo"].get()
        if modo_actual in self.MAPEO_SUBMODOS:
            idx = self.MAPEO_SUBMODOS.index(modo_actual)
            self.nb_submodos.select(idx)

    # ── Submodo A: Potencia Absoluta ─────────────────────────────────────────
    def _build_submodo_a(self):
        f = ttk.Frame(self.nb_submodos, style="Params.TFrame")
        self.nb_submodos.add(f, text="A) Potencia Absoluta")

        f_grid = ttk.Frame(f, style="Params.TFrame")
        f_grid.pack(fill="x", padx=ui(6), pady=ui(6))

        ttk.Label(f_grid, text="P inicial (mW/cm²):", style="Params.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_ini"], width=10).grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Label(f_grid, text="P final (mW/cm²):", style="Params.TLabel").grid(row=0, column=2, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_fin"], width=10).grid(row=0, column=3, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Label(f_grid, text="Paso (mW/cm²):", style="Params.TLabel").grid(row=0, column=4, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_paso"], width=10).grid(row=0, column=5, sticky="w", padx=ui(4), pady=ui(2))

        ttk.Label(f_grid, text="Lista potencias personalizada (mW/cm²):", style="Params.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=ui(4), pady=ui(4))
        ttk.Entry(f_grid, textvariable=self.vars["solar_p_custom"], width=35).grid(row=1, column=2, columnspan=4, sticky="w", padx=ui(4), pady=ui(4))

    # ── Submodo B: Longitudes de Onda Individuales ───────────────────────────
    def _build_submodo_b(self):
        f = ttk.Frame(self.nb_submodos, style="Params.TFrame")
        self.nb_submodos.add(f, text="B) Longitudes Individuales")

        f_ch_grid = ttk.Frame(f, style="Params.TFrame")
        f_ch_grid.pack(fill="x", padx=ui(4), pady=ui(2))

        for idx, (display, raw) in enumerate(self.SOLAR_CANALES):
            r = idx // 6
            c = idx % 6
            ttk.Checkbutton(f_ch_grid, text=display, variable=self.vars["solar_canales_seleccionados_dict"][raw], style="Params.TCheckbutton").grid(
                row=r, column=c, sticky="w", padx=ui(3), pady=ui(1)
            )

        f_btns_ch = ttk.Frame(f, style="Params.TFrame")
        f_btns_ch.pack(fill="x", padx=ui(4), pady=(ui(2), ui(4)))
        ttk.Button(f_btns_ch, text="Seleccionar todos", command=self._sel_todos_canales, style="Tool.TButton").pack(side="left", padx=ui(3))
        ttk.Button(f_btns_ch, text="Limpiar todos", command=self._desel_todos_canales, style="Tool.TButton").pack(side="left", padx=ui(3))

        f_int = ttk.Frame(f, style="Params.TFrame")
        f_int.pack(fill="x", padx=ui(4), pady=ui(2))
        ttk.Label(f_int, text="I inicial (%):", style="Params.TLabel").grid(row=0, column=0, sticky="w", padx=ui(3))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_ini"], width=8).grid(row=0, column=1, sticky="w", padx=ui(3))
        ttk.Label(f_int, text="I final (%):", style="Params.TLabel").grid(row=0, column=2, sticky="w", padx=ui(3))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_fin"], width=8).grid(row=0, column=3, sticky="w", padx=ui(3))
        ttk.Label(f_int, text="Paso (%):", style="Params.TLabel").grid(row=0, column=4, sticky="w", padx=ui(3))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_paso"], width=8).grid(row=0, column=5, sticky="w", padx=ui(3))

        ttk.Label(f_int, text="Lista personalizada (%):", style="Params.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=ui(3), pady=ui(2))
        ttk.Entry(f_int, textvariable=self.vars["solar_i_custom"], width=30).grid(row=1, column=2, columnspan=4, sticky="w", padx=ui(3), pady=ui(2))

    def _sel_todos_canales(self):
        for v in self.vars["solar_canales_seleccionados_dict"].values():
            v.set(True)

    def _desel_todos_canales(self):
        for v in self.vars["solar_canales_seleccionados_dict"].values():
            v.set(False)

    # ── Submodo C: Combinación Multi-Canal Dinámica ──────────────────────────
    def _build_submodo_c(self):
        f = ttk.Frame(self.nb_submodos, style="Params.TFrame")
        self.nb_submodos.add(f, text="C) Combinación Multi-Canal")

        f_top = ttk.Frame(f, style="Params.TFrame")
        f_top.pack(fill="x", padx=ui(4), pady=ui(2))
        ttk.Label(
            f_top,
            text="Define canales e intensidades (separadas por comas, ej: 0, 50, 100):",
            style="Params.TLabel",
        ).pack(side="left")
        ttk.Button(f_top, text="+ Añadir Canal", command=self._anadir_fila_comb, style="Tool.TButton").pack(side="right", padx=ui(4))

        f_scroll = ttk.Frame(f, style="Params.TFrame")
        f_scroll.pack(fill="both", expand=True, padx=ui(4), pady=ui(2))

        t = theme_mgr.get_current_theme()
        bg_color = t.get("bg_panel", "#ffffff")

        self.canvas_comb = tk.Canvas(f_scroll, bg=bg_color, highlightthickness=0, bd=0, height=120)
        scrollbar = ttk.Scrollbar(f_scroll, orient="vertical", command=self.canvas_comb.yview)

        self.canvas_comb.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas_comb.pack(side="left", fill="both", expand=True)

        self.f_matriz = ttk.Frame(self.canvas_comb, style="Params.TFrame")
        self.canvas_window = self.canvas_comb.create_window((0, 0), window=self.f_matriz, anchor="nw")

        self.f_matriz.bind("<Configure>", lambda e: self.canvas_comb.configure(scrollregion=self.canvas_comb.bbox("all")))
        self.canvas_comb.bind("<Configure>", lambda e: self.canvas_comb.itemconfig(self.canvas_window, width=e.width))

        self.canvas_comb.bind("<Enter>", lambda e: self.canvas_comb.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas_comb.bind("<Leave>", lambda e: self.canvas_comb.unbind_all("<MouseWheel>"))

        self._render_filas_comb()

    def _on_mousewheel(self, event):
        if self.canvas_comb.winfo_exists():
            self.canvas_comb.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _render_filas_comb(self):
        for w in self.f_matriz.winfo_children():
            w.destroy()
        self._filas_comb_widgets.clear()

        for idx, item in enumerate(self.vars["solar_canales_comb_lista"]):
            row_frame = ttk.Frame(self.f_matriz, style="Params.TFrame")
            row_frame.pack(fill="x", pady=ui(2))

            ttk.Label(row_frame, text=f"Canal {idx + 1}:", style="Params.TLabel").pack(side="left", padx=ui(3))
            cb = ttk.Combobox(
                row_frame,
                values=[d for d, _ in self.SOLAR_CANALES],
                state="readonly",
                width=12,
            )
            curr_raw = item.get("canal", "390")
            display_val = next((d for d, r in self.SOLAR_CANALES if r == curr_raw), curr_raw)
            cb.set(display_val)
            cb.pack(side="left", padx=ui(3))

            ttk.Label(row_frame, text="Intensidades (%):", style="Params.TLabel").pack(side="left", padx=(ui(8), ui(3)))
            entry_ints = ttk.Entry(row_frame, width=22)
            entry_ints.insert(0, str(item.get("intensidades", "100")))
            entry_ints.pack(side="left", padx=ui(3))

            btn_del = ttk.Button(row_frame, text="✕", width=3, command=lambda i=idx: self._quitar_fila_comb(i), style="Tool.TButton")
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
        f = ttk.Frame(self.nb_submodos, style="Params.TFrame")
        self.nb_submodos.add(f, text="D) Múltiples Recetas")

        ttk.Label(
            f,
            text="Secuencia de combinaciones predefinidas:",
            style="Params.TLabel",
        ).pack(anchor="w", padx=ui(6), pady=ui(2))

        self.txt_recetas = tk.Text(
            f, height=4, width=45,
            font=ui_font("Consolas", 4.5),
            bg=theme_mgr.get_current_theme()["bg_input"],
            fg=theme_mgr.get_current_theme()["fg_input"],
            borderwidth=1,
            relief="solid",
        )
        self.txt_recetas.pack(fill="both", expand=True, padx=ui(6), pady=ui(2))
        self.txt_recetas.insert("end", "# Formato: nombre_receta: canal1=val, canal2=val\nreceta_1: 950=100, 660=50\nreceta_2: 450=100, 515=80\n")


def crear_panel_led(parent, vars_dict):
    return PanelEjeIluminacion(parent, vars_dict)