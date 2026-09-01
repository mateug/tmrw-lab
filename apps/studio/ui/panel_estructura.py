"""Panel de configuración del eje de estructura para Studio."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.ui_kit.scaler import ui
from core.ui_kit.shared import crear_seccion_frame


class PanelEjeEstructura(ttk.Frame):
    """Panel de configuración de conmutación de estructuras."""

    def __init__(self, parent, vars_dict, **kwargs):
        super().__init__(parent, **kwargs)
        self.vars = vars_dict
        self._build()

    def _build(self):
        self.configure(style="Params.TFrame")

        f_sec = crear_seccion_frame(self, "Eje de Estructura — Conmutación por Relé", "params")
        f_sec.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        f_act = ttk.Frame(f_sec, style="Params.TFrame")
        f_act.pack(fill="x", padx=ui(6), pady=ui(4))
        ttk.Checkbutton(
            f_act,
            text="Activar eje de estructura en la secuencia",
            variable=self.vars["eje_estructura_activo"],
            style="Params.TCheckbutton",
        ).pack(side="left")

        f_layout = ttk.Frame(f_sec, style="Params.TFrame")
        f_layout.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))

        f_sel = ttk.LabelFrame(f_layout, text=" Estructuras a barrer ", padding=ui(6), style="Params.TLabelframe")
        f_sel.pack(side="left", fill="y", padx=(0, ui(8)))

        btns = ttk.Frame(f_sel, style="Params.TFrame")
        btns.pack(fill="x", pady=(0, ui(4)))
        ttk.Button(btns, text="Seleccionar todas", command=self._seleccionar_todas, style="Tool.TButton").pack(side="left", padx=ui(3))
        ttk.Button(btns, text="Limpiar todas", command=self._limpiar_todas, style="Tool.TButton").pack(side="left", padx=ui(3))

        self.lista_frame = ttk.Frame(f_sel, style="Params.TFrame")
        self.lista_frame.pack(fill="both", expand=True)
        self._render_estructuras()

        f_cfg = ttk.LabelFrame(f_layout, text=" Configuración Keithley por estructura ", padding=ui(6), style="Params.TLabelframe")
        f_cfg.pack(side="right", fill="both", expand=True)

        self.canvas_cfg = tk.Canvas(f_cfg, height=220, bg="#f8fafc", highlightthickness=0)
        self.scrollbar_cfg = ttk.Scrollbar(f_cfg, orient="vertical", command=self.canvas_cfg.yview)
        self.canvas_cfg.configure(yscrollcommand=self.scrollbar_cfg.set)
        self.scrollbar_cfg.pack(side="right", fill="y")
        self.canvas_cfg.pack(side="left", fill="both", expand=True)

        self.cfg_frame = ttk.Frame(self.canvas_cfg, style="Params.TFrame")
        self.canvas_window_cfg = self.canvas_cfg.create_window((0, 0), window=self.cfg_frame, anchor="nw")
        self.cfg_frame.bind("<Configure>", self._on_configure_cfg_list)
        self.canvas_cfg.bind("<Configure>", self._on_configure_cfg_canvas)

        self._render_configuracion_keithley()

        f_info = ttk.Frame(f_sec, style="Params.TFrame")
        f_info.pack(fill="x", padx=ui(6), pady=ui(4))
        ttk.Label(f_info, text="Espera conmutación relé (s):", style="Params.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_info, textvariable=self.vars.get("estructura_espera_s"), width=8).grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(2))

        f_hw = ttk.Frame(f_sec, style="Params.TFrame")
        f_hw.pack(fill="x", padx=ui(6), pady=ui(6))
        ttk.Label(
            f_hw,
            text="Hardware: relé de conmutación de dispositivo (controlado vía core/instrument/relay_structure.py)",
            foreground="#64748b",
            style="Params.TLabel",
        ).pack(side="left", padx=ui(4))

    def _on_configure_cfg_canvas(self, event):
        if self.canvas_cfg.winfo_exists():
            self.canvas_cfg.itemconfig(self.canvas_window_cfg, width=event.width)

    def _on_configure_cfg_list(self, event):
        if self.canvas_cfg.winfo_exists():
            self.canvas_cfg.configure(scrollregion=self.canvas_cfg.bbox("all"))

    def _seleccionar_todas(self):
        for v in self.vars["estructura_seleccionadas_dict"].values():
            v.set(True)
        self._sincronizar_lista_estructuras()
        self._render_configuracion_keithley()

    def _limpiar_todas(self):
        for v in self.vars["estructura_seleccionadas_dict"].values():
            v.set(False)
        self._sincronizar_lista_estructuras()
        self._render_configuracion_keithley()

    def _sincronizar_lista_estructuras(self):
        seleccionadas = [
            self.vars["estructura_nombres_dict"].get(nombre, tk.StringVar(value=nombre)).get().strip() or nombre
            for nombre, var in self.vars["estructura_seleccionadas_dict"].items()
            if var.get()
        ]
        self.vars["estructura_lista"].set(", ".join(seleccionadas))

    def _render_estructuras(self):
        for w in self.lista_frame.winfo_children():
            w.destroy()

        items = self.vars.get("estructura_disponibles", ["Estructura 1", "Estructura 2"])
        for idx, nombre in enumerate(items):
            row = ttk.Frame(self.lista_frame, style="Params.TFrame")
            row.pack(fill="x", pady=ui(2), padx=ui(2))
            var = self.vars["estructura_seleccionadas_dict"].setdefault(nombre, tk.BooleanVar(value=True))
            name_var = self.vars["estructura_nombres_dict"].setdefault(nombre, tk.StringVar(value=nombre))
            ttk.Checkbutton(row, variable=var, style="Params.TCheckbutton").pack(side="left")
            ttk.Entry(row, textvariable=name_var, width=18).pack(side="left", padx=(ui(8), 0))
        self._sincronizar_lista_estructuras()

    def _render_configuracion_keithley(self):
        for w in self.cfg_frame.winfo_children():
            w.destroy()

        seleccionadas = [
            nombre for nombre, var in self.vars["estructura_seleccionadas_dict"].items() if var.get()
        ]

        if not seleccionadas:
            ttk.Label(
                self.cfg_frame,
                text="No hay estructuras seleccionadas.",
                foreground="#64748b",
                style="Params.TLabel",
            ).pack(anchor="w", padx=ui(6), pady=ui(8))
            return

        for nombre in seleccionadas:
            display_name = self.vars["estructura_nombres_dict"][nombre].get().strip() or nombre
            block = ttk.LabelFrame(self.cfg_frame, text=f" {display_name} ", padding=ui(6), style="Params.TLabelframe")
            block.pack(fill="x", padx=ui(4), pady=ui(4))
            kvars = self.vars["estructura_keithley_vars"][nombre]

            row1 = ttk.Frame(block, style="Params.TFrame")
            row1.pack(fill="x", pady=ui(2))
            ttk.Label(row1, text="Recurso VISA:", style="Params.TLabel").pack(side="left")
            ttk.Entry(row1, textvariable=kvars["recurso_visa"], width=16).pack(side="left", padx=(ui(2), ui(10)))
            ttk.Label(row1, text="Modo medida:", style="Params.TLabel").pack(side="left")
            ttk.Combobox(row1, textvariable=kvars["modo_medida"], values=["completa", "directa", "inversa"], state="readonly", width=12).pack(side="left", padx=(ui(2), ui(10)))

            row2 = ttk.Frame(block, style="Params.TFrame")
            row2.pack(fill="x", pady=ui(2))
            ttk.Label(row2, text="I máx (µA):", style="Params.TLabel").pack(side="left")
            ttk.Entry(row2, textvariable=kvars["i_max_uA"], width=10).pack(side="left", padx=(ui(2), ui(8)))
            ttk.Label(row2, text="V ini directa (mV):", style="Params.TLabel").pack(side="left")
            ttk.Entry(row2, textvariable=kvars["v_ini_dir"], width=10).pack(side="left", padx=(ui(2), ui(8)))
            ttk.Label(row2, text="V fin directa (mV):", style="Params.TLabel").pack(side="left")
            ttk.Entry(row2, textvariable=kvars["v_fin_dir"], width=10).pack(side="left", padx=(ui(2), ui(8)))

            row3 = ttk.Frame(block, style="Params.TFrame")
            row3.pack(fill="x", pady=ui(2))
            ttk.Label(row3, text="Paso directa (mV):", style="Params.TLabel").pack(side="left")
            ttk.Entry(row3, textvariable=kvars["paso_dir"], width=10).pack(side="left", padx=(ui(2), ui(8)))
            ttk.Label(row3, text="V fin inversa (V):", style="Params.TLabel").pack(side="left")
            ttk.Entry(row3, textvariable=kvars["v_fin_inv"], width=10).pack(side="left", padx=(ui(2), ui(8)))
            ttk.Label(row3, text="Paso inversa (mV):", style="Params.TLabel").pack(side="left")
            ttk.Entry(row3, textvariable=kvars["paso_inv"], width=10).pack(side="left", padx=(ui(2), ui(8)))

        self._on_configure_cfg_list(None)


def crear_panel_estructura(parent, vars_dict):
    return PanelEjeEstructura(parent, vars_dict)
