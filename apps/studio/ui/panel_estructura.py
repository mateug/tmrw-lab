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

        f_sel = ttk.LabelFrame(f_sec, text=" Estructuras a barrer ", padding=ui(6), style="Params.TLabelframe")
        f_sel.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))

        btns = ttk.Frame(f_sel, style="Params.TFrame")
        btns.pack(fill="x", pady=(0, ui(4)))
        ttk.Button(btns, text="Seleccionar todas", command=self._seleccionar_todas, style="Tool.TButton").pack(side="left", padx=ui(3))
        ttk.Button(btns, text="Limpiar todas", command=self._limpiar_todas, style="Tool.TButton").pack(side="left", padx=ui(3))

        self.canvas = tk.Canvas(f_sel, height=160, bg="#f8fafc", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(f_sel, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.lista_frame = ttk.Frame(self.canvas, style="Params.TFrame")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.lista_frame, anchor="nw")
        self.lista_frame.bind("<Configure>", self._on_configure_list)
        self.canvas.bind("<Configure>", self._on_configure_canvas)

        self._render_estructuras()

        f_info = ttk.Frame(f_sec, style="Params.TFrame")
        f_info.pack(fill="x", padx=ui(6), pady=ui(4))
        ttk.Label(f_info, text="Espera conmutación relé (s):", style="Params.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4), pady=ui(2))
        ttk.Entry(f_info, textvariable=self.vars.get("estructura_espera_s"), width=8).grid(row=0, column=1, sticky="w", padx=ui(4), pady=ui(2))

        f_keithley = ttk.LabelFrame(f_sec, text=" Configuración Keithley por estructura ", padding=ui(6), style="Params.TLabelframe")
        f_keithley.pack(fill="x", padx=ui(6), pady=ui(4))
        f_k1 = ttk.Frame(f_keithley, style="Params.TFrame")
        f_k1.pack(fill="x", pady=ui(2))
        ttk.Label(f_k1, text="Recurso VISA:", style="Params.TLabel").pack(side="left")
        ttk.Entry(f_k1, textvariable=self.vars["recurso_visa"], width=18).pack(side="left", padx=(ui(2), ui(12)))
        ttk.Label(f_k1, text="Modo de medida:", style="Params.TLabel").pack(side="left")
        ttk.Combobox(f_k1, textvariable=self.vars["modo_medida"], values=["completa", "directa", "inversa"], state="readonly", width=12).pack(side="left", padx=(ui(2), ui(12)))

        f_k2 = ttk.Frame(f_keithley, style="Params.TFrame")
        f_k2.pack(fill="x", pady=ui(2))
        ttk.Label(f_k2, text="I máx (µA):", style="Params.TLabel").pack(side="left")
        ttk.Entry(f_k2, textvariable=self.vars["i_max_uA"], width=10).pack(side="left", padx=(ui(2), ui(10)))
        ttk.Label(f_k2, text="V ini directa (mV):", style="Params.TLabel").pack(side="left")
        ttk.Entry(f_k2, textvariable=self.vars["v_ini_dir"], width=10).pack(side="left", padx=(ui(2), ui(10)))
        ttk.Label(f_k2, text="V fin directa (mV):", style="Params.TLabel").pack(side="left")
        ttk.Entry(f_k2, textvariable=self.vars["v_fin_dir"], width=10).pack(side="left", padx=(ui(2), ui(10)))

        f_hw = ttk.Frame(f_sec, style="Params.TFrame")
        f_hw.pack(fill="x", padx=ui(6), pady=ui(6))
        ttk.Label(
            f_hw,
            text="Hardware: relé de conmutación de dispositivo (controlado vía core/instrument/relay_structure.py)",
            foreground="#64748b",
            style="Params.TLabel",
        ).pack(side="left", padx=ui(4))

    def _on_configure_canvas(self, event):
        if self.canvas.winfo_exists():
            self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_configure_list(self, event):
        if self.canvas.winfo_exists():
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _seleccionar_todas(self):
        for v in self.vars["estructura_seleccionadas_dict"].values():
            v.set(True)
        self._sincronizar_lista_estructuras()

    def _limpiar_todas(self):
        for v in self.vars["estructura_seleccionadas_dict"].values():
            v.set(False)
        self._sincronizar_lista_estructuras()

    def _sincronizar_lista_estructuras(self):
        seleccionadas = [name for name, var in self.vars["estructura_seleccionadas_dict"].items() if var.get()]
        self.vars["estructura_lista"].set(", ".join(seleccionadas))

    def _render_estructuras(self):
        for w in self.lista_frame.winfo_children():
            w.destroy()

        items = self.vars.get("estructura_disponibles", ["Estructura 1", "Estructura 2"])
        for idx, nombre in enumerate(items):
            row = ttk.Frame(self.lista_frame, style="Params.TFrame")
            row.pack(fill="x", pady=ui(2), padx=ui(2))
            var = self.vars["estructura_seleccionadas_dict"].setdefault(nombre, tk.BooleanVar(value=True))
            ttk.Checkbutton(row, text=nombre, variable=var, style="Params.TCheckbutton").pack(side="left")
        self._sincronizar_lista_estructuras()


def crear_panel_estructura(parent, vars_dict):
    return PanelEjeEstructura(parent, vars_dict)
