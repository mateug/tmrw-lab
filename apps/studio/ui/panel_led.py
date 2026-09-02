"""Panel completo del eje de Iluminación y Simulador Solar para Studio.

Implementa con máxima fidelidad los submodos de construcción manual de iv-maker:
  1. Submodo A: Potencia Absoluta (mW/cm²)
  2. Submodo B: Longitudes de Onda Individuales (11 canales Ossila)
  3. Submodo C: Combinación Multi-Canal (matriz dinámica con relaciones 1-1 / 1-N)
  4. Submodo D: Múltiples Combinaciones Multi-Canal (varias combinaciones tipo C, con nombre propio)

Los submodos C y D replican exactamente el comportamiento que tenían las pestañas
"Combinación Multi-Canal" y "Múltiples Combinaciones Multi-Canal" del antiguo
Modo 3 (Irradiancia LED): filas dinámicas de canal + intensidades, un widget de
relación (1-1 / 1-N) entre cada par de canales consecutivos con su propia
representación gráfica de flechas, y un resumen en vivo del número total de
medidas resultante.

Incluye explicaciones claras para los tiempos de estabilización, encendido previo y enfriamiento térmico.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui, ui_font, ui_font_info, UIConfig
from core.ui_kit.shared import ScrollableFrame, crear_seccion_frame, mostrar_info
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
        # Submodo C: filas de canal/intensidad y relaciones 1-1 / 1-N entre ellas.
        self._filas_comb_widgets = []
        self._relaciones_comb_widgets = []
        # Submodo D: lista de combinaciones (cada una con sus propias filas/relaciones).
        self._combos_multi_widgets = []
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
        ttk.Label(f_t_grid, text="Cada N medidas estructura:", style="Params.TLabel").grid(row=0, column=6, sticky="w", padx=(ui(12), ui(4)))
        ttk.Entry(f_t_grid, textvariable=self.vars["solar_cada_n_medidas_estructura"], width=8).grid(row=0, column=7, sticky="w", padx=ui(4))

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

    def _canal_a_display(self, canal_raw):
        """Traduce un valor crudo de canal (p.ej. '950') a su etiqueta visible ('950 nm')."""
        canal_raw = str(canal_raw)
        for disp, val in self.SOLAR_CANALES:
            if canal_raw.lower() == val.lower() or canal_raw.lower() == disp.lower():
                return disp
        return canal_raw

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

    # ── Utilidades compartidas C/D: relaciones 1-1 / 1-N entre canales ───────
    # Portadas tal cual del antiguo Modo 3 (src/ui/modes/irradiance.py) para
    # conservar exactamente el mismo comportamiento visual y de cálculo.
    def _parsear_intensidades_ui(self, texto):
        try:
            valores = [
                float(x.strip())
                for x in str(texto).split(",")
                if x.strip()
            ]
            return valores or [0.0]
        except (ValueError, TypeError):
            return []

    def _crear_widget_relacion(self, parent, relacion_var, callback_cambio):
        """Crea el bloque visual entre dos canales consecutivos."""
        frame = ttk.Frame(parent, style="Params.TFrame")

        # Separamos la zona gráfica del resto del bloque. Esto evita
        # mezclar place() y pack() sobre el mismo contenedor y garantiza
        # que el Combobox quede realmente visible sobre la flecha.
        visual_frame = ttk.Frame(frame, width=ui(360), height=ui(62), style="Params.TFrame")
        visual_frame.pack_propagate(False)
        visual_frame.pack(side="left", padx=(ui(30), ui(10)), anchor="center")

        canvas = tk.Canvas(
            visual_frame,
            width=ui(300),
            height=ui(58),
            highlightthickness=0,
            bd=0,
        )
        canvas.place(relx=0.5, rely=0.5, anchor="center")

        combo = ttk.Combobox(
            visual_frame,
            textvariable=relacion_var,
            values=("1-1", "1-N"),
            width=7,
            state="readonly",
        )
        combo.place(relx=0.5, rely=0.5, anchor="center")
        combo.lift()

        info_frame = ttk.Frame(frame, style="Params.TFrame")
        info_frame.pack(side="left", fill="x", expand=True, padx=(ui(8), 0))

        medidas_var = tk.StringVar(value="")
        explicacion_var = tk.StringVar(value="")

        ttk.Label(
            info_frame,
            textvariable=medidas_var,
            font=ui_font_info(),
            style="Params.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            info_frame,
            textvariable=explicacion_var,
            font=ui_font_info(),
            style="Params.TLabel",
            justify="left",
            wraplength=ui(430),
        ).pack(anchor="w")

        def _dibujar(_event=None):
            canvas.delete("all")
            ancho = ui(300)
            alto = ui(58)
            centro = ancho // 2

            if relacion_var.get() == "1-N":
                for offset in (-ui(28), -ui(9), ui(9), ui(28)):
                    canvas.create_line(
                        centro,
                        ui(4),
                        centro + offset,
                        alto - ui(5),
                        arrow=tk.LAST,
                        width=max(1, ui(1)),
                    )
            else:
                canvas.create_line(
                    centro,
                    ui(2),
                    centro,
                    alto - ui(5),
                    arrow=tk.LAST,
                    width=max(1, ui(2)),
                )

        def _cambio_relacion(_event=None):
            _dibujar()
            callback_cambio()

        combo.bind("<<ComboboxSelected>>", _cambio_relacion)
        relacion_var.trace_add("write", lambda *_args: _dibujar())
        _dibujar()

        return {
            "frame": frame,
            "var": relacion_var,
            "canvas": canvas,
            "combo": combo,
            "medidas_var": medidas_var,
            "explicacion_var": explicacion_var,
            "_dibujar": _dibujar,
        }

    def _reconstruir_relaciones(self, filas, relaciones, container, relation_defaults=None, callback_cambio=None):
        relation_defaults = relation_defaults or []
        callback_cambio = callback_cambio or (lambda: None)

        # Destruir relaciones sobrantes.
        while len(relaciones) > max(0, len(filas) - 1):
            relacion = relaciones.pop()
            relacion["frame"].destroy()

        # Crear las que falten.
        while len(relaciones) < max(0, len(filas) - 1):
            idx = len(relaciones)
            valor = "1-1"
            if idx < len(relation_defaults) and relation_defaults[idx] in {"1-1", "1-N"}:
                valor = relation_defaults[idx]
            var = tk.StringVar(value=valor)
            relaciones.append(
                self._crear_widget_relacion(container, var, callback_cambio)
            )

        # Orden visual: fila -> relación -> fila -> relación...
        widgets = []
        for idx, fila in enumerate(filas):
            widgets.append(fila["frame"])
            if idx < len(filas) - 1:
                widgets.append(relaciones[idx]["frame"])

        for widget in widgets:
            widget.pack_forget()

        for widget in widgets:
            widget.pack(fill="x", expand=True, pady=ui(2))

    def _calcular_total_relaciones(self, listas, relaciones):
        if not listas:
            return 0, None

        total = len(listas[0])
        for idx in range(1, len(listas)):
            anterior = listas[idx - 1]
            actual = listas[idx]
            relacion = relaciones[idx - 1] if idx - 1 < len(relaciones) else "1-1"

            if relacion == "1-N":
                total *= len(actual)
                continue

            if len(anterior) == 1:
                total *= len(actual)
            elif len(actual) == 1:
                pass
            elif len(anterior) == len(actual):
                pass
            else:
                return 0, (
                    f"La relación 1-1 entre los dos canales requiere el mismo número "
                    f"de intensidades, salvo que uno de ellos tenga una única intensidad fija. "
                    f"Se han encontrado {len(anterior)} y {len(actual)}."
                )

        return total, None

    def _actualizar_info_relaciones(self, filas, relaciones, total_var=None, resumen_var=None):
        listas = [self._parsear_intensidades_ui(f["var_ints"].get()) for f in filas]
        if any(not x for x in listas):
            if total_var is not None:
                total_var.set("0 medidas")
            if resumen_var is not None:
                resumen_var.set("Corrige las intensidades para poder calcular las medidas.")
            return

        total, error = self._calcular_total_relaciones(
            listas,
            [r["var"].get() for r in relaciones],
        )

        if total_var is not None:
            total_var.set("Configuración no válida" if error else f"{total} medidas")

        if resumen_var is not None:
            if error:
                resumen_var.set(error)
            else:
                resumen_var.set(
                    " · ".join(
                        f"{filas[i]['var_canal'].get()} → {filas[i + 1]['var_canal'].get()}: "
                        f"{relaciones[i]['var'].get()}"
                        for i in range(len(relaciones))
                    )
                    if relaciones
                    else "Un solo canal: se mide cada intensidad configurada."
                )

        for i, relacion in enumerate(relaciones):
            canal_a = filas[i]["var_canal"].get()
            canal_b = filas[i + 1]["var_canal"].get()
            ints_a = listas[i]
            ints_b = listas[i + 1]
            tipo = relacion["var"].get()

            if tipo == "1-1":
                n = len(ints_a) if len(ints_a) > 1 and len(ints_a) == len(ints_b) else (
                    len(ints_b) if len(ints_a) == 1 else len(ints_a) if len(ints_b) == 1 else 0
                )
                if len(ints_a) > 1 and len(ints_b) > 1 and len(ints_a) != len(ints_b):
                    relacion["medidas_var"].set("Configuración no válida")
                    relacion["explicacion_var"].set(
                        f"{canal_a} → {canal_b}: 1-1. Debe existir correspondencia por posición. "
                        "Ambos canales necesitan el mismo número de intensidades, salvo que uno sea fijo."
                    )
                else:
                    relacion["medidas_var"].set(f"{n} medidas")
                    relacion["explicacion_var"].set(
                        f"{canal_a} → {canal_b}: 1-1. Cada intensidad se combina con la intensidad "
                        f"correspondiente del siguiente canal."
                    )
            else:
                n = len(ints_a) * len(ints_b)
                relacion["medidas_var"].set(f"{n} combinaciones")
                relacion["explicacion_var"].set(
                    f"{canal_a} → {canal_b}: 1-N. Cada intensidad del primer canal se combina "
                    f"con todas las intensidades del siguiente. Las cuatro flechas son solo una representación visual."
                )

            relacion["_dibujar"]()

    # ── Submodo C: Combinación Multi-Canal ────────────────────────────────────
    def _build_submodo_c(self):
        f = ttk.Frame(self.nb_submodos, style="Params.TFrame")
        self.nb_submodos.add(f, text="C) Combinación Multi-Canal")

        sf = ScrollableFrame(f)
        sf.pack(fill="both", expand=True)
        content = sf.scroll_content
        sf.canvas.configure(background=theme_mgr.get_current_theme()["params"]["bg"])
        content.configure(style="Params.TFrame")

        f_info = ttk.Frame(content, style="Params.TFrame")
        f_info.pack(fill="x", expand=True, pady=(ui(6), ui(6)))
        ttk.Label(
            f_info,
            text=(
                "Especifica las intensidades en % para cada canal. Entre cada par de canales consecutivos "
                "puedes elegir una relación 1-1 o 1-N. 1-1 empareja por posición; 1-N combina cada valor "
                "con todos los valores del siguiente canal."
            ),
            font=ui_font_info(),
            style="Params.TLabel",
            justify="left",
            wraplength=ui(900),
        ).pack(anchor="w", padx=ui(4))

        self.container_filas_comb = ttk.Frame(content, style="Params.TFrame")
        self.container_filas_comb.pack(fill="x", expand=True, pady=ui(4))

        self._filas_comb_widgets = []
        self._relaciones_comb_widgets = []
        relation_defaults = list(self.vars.get("solar_canales_comb_relaciones", []))

        datos_iniciales = self.vars.get("solar_canales_comb_lista") or [
            {"canal": "950", "intensidades": "100"},
            {"canal": "660", "intensidades": "0, 50, 100"},
        ]
        for item in datos_iniciales:
            self._add_fila_comb(
                item.get("canal", "950"),
                item.get("intensidades", "100"),
                actualizar=False,
            )

        if not self._filas_comb_widgets:
            self._add_fila_comb("950", "100", actualizar=False)
            self._add_fila_comb("660", "0, 50, 100", actualizar=False)

        self._actualizar_relaciones_comb(relation_defaults=relation_defaults)

        f_btns_row = ttk.Frame(content, style="Params.TFrame")
        f_btns_row.pack(fill="x", expand=True, pady=ui(6), padx=ui(4))
        ttk.Button(
            f_btns_row,
            text="➕ Añadir Canal a la Combinación",
            command=lambda: self._add_fila_comb("390", "50"),
            style="Tool.TButton",
        ).pack(side="left")

        resumen = ttk.Frame(content, style="Params.TFrame")
        resumen.pack(fill="x", expand=True, pady=(ui(6), ui(4)), padx=ui(4))
        self.total_comb_var = tk.StringVar(value="0 medidas")
        self.resumen_comb_var = tk.StringVar(value="")
        ttk.Label(resumen, text="Total de medidas:", font=ui_font_info(), style="Params.TLabel").pack(side="left")
        ttk.Label(resumen, textvariable=self.total_comb_var, font=ui_font_info(), style="Params.TLabel").pack(
            side="left", padx=(ui(5), ui(20))
        )
        ttk.Label(
            resumen,
            textvariable=self.resumen_comb_var,
            font=ui_font_info(),
            style="Params.TLabel",
            justify="left",
            wraplength=ui(700),
        ).pack(side="left", fill="x", expand=True)

    def _add_fila_comb(self, canal_default="950", intensidades_default="100", actualizar=True):
        row_frame = ttk.Frame(self.container_filas_comb, style="Params.TFrame")
        row_frame.pack(fill="x", expand=True, pady=ui(3))

        ttk.Label(row_frame, text="Longitud de Onda:", style="Params.TLabel").pack(side="left", padx=(0, ui(4)))

        var_canal = tk.StringVar(value=self._canal_a_display(canal_default))
        combo = ttk.Combobox(
            row_frame,
            textvariable=var_canal,
            values=[disp for disp, _ in self.SOLAR_CANALES],
            width=15,
            state="readonly",
        )
        combo.pack(side="left", padx=(0, ui(15)))

        ttk.Label(row_frame, text="Intensidades (%):", style="Params.TLabel").pack(side="left", padx=(0, ui(4)))
        var_ints = tk.StringVar(value=str(intensidades_default))
        entry_ints = ttk.Entry(row_frame, textvariable=var_ints, width=30)
        entry_ints.pack(side="left", padx=(0, ui(15)))

        widget_dict = {
            "frame": row_frame,
            "var_canal": var_canal,
            "var_ints": var_ints,
            "entry_ints": entry_ints,
            "combo_canal": combo,
        }

        ttk.Button(
            row_frame,
            text="❌ Eliminar",
            command=lambda w=widget_dict: self._remove_fila_comb(w),
            style="Tool.TButton",
        ).pack(side="left")

        self._filas_comb_widgets.append(widget_dict)

        var_ints.trace_add("write", lambda *_args: self._actualizar_relaciones_comb())
        var_canal.trace_add("write", lambda *_args: self._actualizar_relaciones_comb())

        if actualizar:
            self._actualizar_relaciones_comb()

    def _remove_fila_comb(self, widget_dict):
        if len(self._filas_comb_widgets) <= 1:
            mostrar_info("Información", "Debe haber al menos un canal en la combinación.")
            return
        if widget_dict in self._filas_comb_widgets:
            self._filas_comb_widgets.remove(widget_dict)
            widget_dict["frame"].destroy()
            self._actualizar_relaciones_comb()

    def _actualizar_relaciones_comb(self, relation_defaults=None):
        if relation_defaults is None and not self._relaciones_comb_widgets:
            relation_defaults = self.vars.get("solar_canales_comb_relaciones", [])
        self._reconstruir_relaciones(
            self._filas_comb_widgets,
            self._relaciones_comb_widgets,
            self.container_filas_comb,
            relation_defaults=relation_defaults,
            callback_cambio=lambda: self._actualizar_relaciones_comb(),
        )
        self._actualizar_info_relaciones(
            self._filas_comb_widgets,
            self._relaciones_comb_widgets,
            total_var=getattr(self, "total_comb_var", None),
            resumen_var=getattr(self, "resumen_comb_var", None),
        )
        self._sincronizar_comb_data()

    def _sincronizar_comb_data(self):
        nuevos = []
        for fila in self._filas_comb_widgets:
            display_txt = fila["var_canal"].get()
            raw_val = next((r for d, r in self.SOLAR_CANALES if d == display_txt), display_txt)
            nuevos.append({"canal": raw_val, "intensidades": fila["var_ints"].get().strip()})
        self.vars["solar_canales_comb_lista"] = nuevos
        self.vars["solar_canales_comb_relaciones"] = [r["var"].get() for r in self._relaciones_comb_widgets]

    # ── Submodo D: Múltiples Combinaciones Multi-Canal ────────────────────────
    def _build_submodo_d(self):
        f = ttk.Frame(self.nb_submodos, style="Params.TFrame")
        self.nb_submodos.add(f, text="D) Múltiples Combinaciones Multi-Canal")

        sf = ScrollableFrame(f)
        sf.pack(fill="both", expand=True)
        content = sf.scroll_content
        sf.canvas.configure(background=theme_mgr.get_current_theme()["params"]["bg"])
        content.configure(style="Params.TFrame")

        f_info = ttk.Frame(content, style="Params.TFrame")
        f_info.pack(fill="x", expand=True, pady=(ui(6), ui(6)))
        ttk.Label(
            f_info,
            text=(
                "Define varias combinaciones multicanal con nombre propio. Cada combinación se comporta "
                "igual que en la pestaña C: intensidades por canal y una relación 1-1 / 1-N entre cada par "
                "de canales consecutivos. La secuencia mide cada combinación, una tras otra."
            ),
            font=ui_font_info(),
            style="Params.TLabel",
            justify="left",
            wraplength=ui(900),
        ).pack(anchor="w", padx=ui(4))

        self.container_multi_combos = ttk.Frame(content, style="Params.TFrame")
        self.container_multi_combos.pack(fill="x", expand=True, pady=ui(4))

        self._combos_multi_widgets = []
        datos_iniciales = self.vars.get("solar_recetas_lista") or [
            {
                "nombre": "combo_950_660",
                "canales": [
                    {"canal": "950", "intensidades": "100"},
                    {"canal": "660", "intensidades": "0, 50, 100"},
                ],
                "relaciones": [],
            },
        ]
        for combo in datos_iniciales:
            self._add_combo_multi(
                combo.get("nombre", ""),
                combo.get("canales", []),
                combo.get("relaciones", None),
            )

        if not self._combos_multi_widgets:
            self._add_combo_multi(
                "combo_950_660",
                [
                    {"canal": "950", "intensidades": "100"},
                    {"canal": "660", "intensidades": "0, 50, 100"},
                ],
                None,
            )

        f_btns = ttk.Frame(content, style="Params.TFrame")
        f_btns.pack(fill="x", expand=True, pady=ui(6), padx=ui(4))
        ttk.Button(
            f_btns,
            text="➕ Añadir Combinación",
            command=lambda: self._add_combo_multi(),
            style="Tool.TButton",
        ).pack(side="left")

    def _add_combo_multi(self, nombre_default="", canales_default=None, relaciones_default=None):
        canales_default = canales_default or [
            {"canal": "950", "intensidades": "100"},
            {"canal": "660", "intensidades": "0, 50, 100"},
        ]
        idx = len(self._combos_multi_widgets) + 1

        combo_frame = ttk.LabelFrame(
            self.container_multi_combos,
            text=f" Combinación {idx} ",
            padding=ui(8),
            style="Params.TLabelframe",
        )
        combo_frame.pack(fill="x", expand=True, pady=ui(7))

        header = ttk.Frame(combo_frame, style="Params.TFrame")
        header.pack(fill="x", expand=True, pady=(0, ui(5)))
        ttk.Label(header, text="Nombre:", style="Params.TLabel").pack(side="left", padx=(0, ui(4)))
        var_nombre = tk.StringVar(value=nombre_default or f"combo_{idx}")
        ttk.Entry(header, textvariable=var_nombre, width=24).pack(side="left", padx=(0, ui(12)))

        filas_frame = ttk.Frame(combo_frame, style="Params.TFrame")
        filas_frame.pack(fill="x", expand=True)

        combo_dict = {
            "frame": combo_frame,
            "var_nombre": var_nombre,
            "filas_frame": filas_frame,
            "filas": [],
            "relaciones": [],
            "relaciones_default": relaciones_default or [],
            "medidas_var": tk.StringVar(value="0 medidas"),
            "resumen_var": tk.StringVar(value=""),
        }

        for item in canales_default:
            self._add_fila_combo_multi(
                combo_dict,
                item.get("canal", "950"),
                item.get("intensidades", "100"),
                actualizar=False,
            )

        if not combo_dict["filas"]:
            self._add_fila_combo_multi(combo_dict, "950", "100", actualizar=False)
            self._add_fila_combo_multi(combo_dict, "660", "0, 50, 100", actualizar=False)

        self._combos_multi_widgets.append(combo_dict)
        self._actualizar_relaciones_combo_multi(combo_dict)

        acciones = ttk.Frame(combo_frame, style="Params.TFrame")
        acciones.pack(fill="x", expand=True, pady=(ui(7), 0))
        ttk.Button(
            acciones,
            text="Añadir canal",
            command=lambda c=combo_dict: self._add_fila_combo_multi(c, "390", "50"),
            style="Tool.TButton",
        ).pack(side="left")
        ttk.Button(
            acciones,
            text="Eliminar combinación",
            command=lambda c=combo_dict: self._remove_combo_multi(c),
            style="Tool.TButton",
        ).pack(side="left", padx=ui(8))

        resumen = ttk.Frame(combo_frame, style="Params.TFrame")
        resumen.pack(fill="x", expand=True, pady=(ui(7), 0))
        ttk.Label(resumen, text="Total de medidas:", font=ui_font_info(), style="Params.TLabel").pack(side="left")
        ttk.Label(resumen, textvariable=combo_dict["medidas_var"], font=ui_font_info(), style="Params.TLabel").pack(
            side="left", padx=(ui(5), ui(20))
        )
        ttk.Label(
            resumen,
            textvariable=combo_dict["resumen_var"],
            font=ui_font_info(),
            style="Params.TLabel",
            justify="left",
            wraplength=ui(700),
        ).pack(side="left", fill="x", expand=True)

    def _add_fila_combo_multi(self, combo_dict, canal_default="950", intensidades_default="100", actualizar=True):
        row_frame = ttk.Frame(combo_dict["filas_frame"], style="Params.TFrame")
        row_frame.pack(fill="x", expand=True, pady=ui(3))

        ttk.Label(row_frame, text="Longitud de Onda / Canal:", style="Params.TLabel").pack(side="left", padx=(0, ui(4)))

        var_canal = tk.StringVar(value=self._canal_a_display(canal_default))
        combo_canal = ttk.Combobox(
            row_frame,
            textvariable=var_canal,
            values=[disp for disp, _ in self.SOLAR_CANALES],
            width=15,
            state="readonly",
        )
        combo_canal.pack(side="left", padx=(0, ui(15)))

        ttk.Label(row_frame, text="Intensidades (%):", style="Params.TLabel").pack(side="left", padx=(0, ui(4)))
        var_ints = tk.StringVar(value=str(intensidades_default))
        entry_ints = ttk.Entry(row_frame, textvariable=var_ints, width=30)
        entry_ints.pack(side="left", padx=(0, ui(15)))

        fila = {
            "frame": row_frame,
            "var_canal": var_canal,
            "var_ints": var_ints,
            "entry_ints": entry_ints,
            "combo_canal": combo_canal,
        }
        ttk.Button(
            row_frame,
            text="Eliminar",
            command=lambda f=fila, c=combo_dict: self._remove_fila_combo_multi(c, f),
            style="Tool.TButton",
        ).pack(side="left")
        combo_dict["filas"].append(fila)

        var_ints.trace_add("write", lambda *_args, c=combo_dict: self._actualizar_relaciones_combo_multi(c))
        var_canal.trace_add("write", lambda *_args, c=combo_dict: self._actualizar_relaciones_combo_multi(c))

        if actualizar:
            self._actualizar_relaciones_combo_multi(combo_dict)

    def _remove_fila_combo_multi(self, combo_dict, fila):
        if len(combo_dict["filas"]) <= 1:
            mostrar_info("Información", "Cada combinación debe tener al menos un canal.")
            return
        if fila in combo_dict["filas"]:
            combo_dict["filas"].remove(fila)
            fila["frame"].destroy()
            self._actualizar_relaciones_combo_multi(combo_dict)

    def _remove_combo_multi(self, combo_dict):
        if len(self._combos_multi_widgets) <= 1:
            mostrar_info("Información", "Debe haber al menos una combinación.")
            return
        if combo_dict in self._combos_multi_widgets:
            self._combos_multi_widgets.remove(combo_dict)
            combo_dict["frame"].destroy()
            self._sincronizar_recetas_data()

    def _actualizar_relaciones_combo_multi(self, combo_dict):
        self._reconstruir_relaciones(
            combo_dict["filas"],
            combo_dict["relaciones"],
            combo_dict["filas_frame"],
            relation_defaults=combo_dict.get("relaciones_default", []),
            callback_cambio=lambda c=combo_dict: self._actualizar_relaciones_combo_multi(c),
        )
        # Una vez creadas, el estado actual pasa a ser el default si después se añade un canal.
        combo_dict["relaciones_default"] = [r["var"].get() for r in combo_dict["relaciones"]]
        self._actualizar_info_relaciones(
            combo_dict["filas"],
            combo_dict["relaciones"],
            total_var=combo_dict["medidas_var"],
            resumen_var=combo_dict["resumen_var"],
        )
        self._sincronizar_recetas_data()

    def _sincronizar_recetas_data(self):
        """Vuelca el estado de todas las combinaciones del submodo D a self.vars["solar_recetas_lista"].

        Se mantiene el nombre de variable histórico ("solar_recetas_lista") por
        compatibilidad con StudioFrame, aunque cada elemento ahora sigue el
        mismo formato que las "combinaciones" del antiguo Modo 3: nombre,
        lista de canales con sus intensidades (posible lista separada por
        comas) y las relaciones 1-1 / 1-N entre canales consecutivos.
        """
        nuevas = []
        for combo in getattr(self, "_combos_multi_widgets", []):
            nombre = combo["var_nombre"].get().strip() or f"combo_{len(nuevas) + 1}"
            canales = []
            for fila in combo["filas"]:
                display_txt = fila["var_canal"].get()
                raw_val = next((r for d, r in self.SOLAR_CANALES if d == display_txt), display_txt)
                canales.append({"canal": raw_val, "intensidades": fila["var_ints"].get().strip()})
            relaciones = [r["var"].get() for r in combo["relaciones"]]
            if canales:
                nuevas.append({"nombre": nombre, "canales": canales, "relaciones": relaciones})
        self.vars["solar_recetas_lista"] = nuevas


def crear_panel_led(parent, vars_dict):
    return PanelEjeIluminacion(parent, vars_dict)
