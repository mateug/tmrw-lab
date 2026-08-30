"""Panel UI de Analytics — integrado con la arquitectura visual y temática de TMRW Lab.

Funcionalidades conservadas de IV-Curves-Generator:
- Escaneo de carpeta recursivo de Excels IV
- Lista de archivos con selección manual / Seleccionar todos
- Selector de unidades I/V
- Pestaña IV: curvas comparativas con tooltip hover
- Pestaña Isc: Isc vs tiempo con leyenda
- Controles de gráfico (límites X/Y, invertir ejes, estilo de línea)
- Exportar Excel combinado
- Exportar gráfico PNG/PDF
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from apps.analytics.engine import (
    UNIT_FACTORS, COL_ARCHIVO, COL_DATETIME,
    escanear_carpeta, combinar_iv,
)
from core.ui_kit.theme import theme_mgr
from core.ui_kit.scaler import scaler, ui, ui_font, UIConfig
from core.ui_kit.shared import crear_barra_superior, crear_seccion_frame


_LINE_STYLES = {
    "Línea continua (-)": "-",
    "Línea rayada (--)": "--",
    "Puntos (.)": ".",
    "Puntos y línea (.-)": ".-",
}

_HOVER_RADIUS_PX = 10


class AnalyticsFrame(ttk.Frame):
    """Pantalla principal del modo Analytics."""

    def __init__(self, parent, callback_volver, **kwargs):
        super().__init__(parent, **kwargs)
        self._callback_volver = callback_volver
        self._entradas: list[dict] = []
        self._seleccionadas: set[str] = set()
        self._carpeta = str(Path.home())
        self._fig = Figure(figsize=(8, 5))
        self._ax = self._fig.subplots()
        self._graph_generated_iv = False
        self._graph_generated_isc = False
        self._last_summary: pd.DataFrame | None = None
        self._hover_cid = None
        self._annot = None
        self._build()

    def _t(self):
        return theme_mgr.get_current_theme()

    def _build(self):
        self.configure(style="Window.TFrame")

        # ── Barra superior compartida ───────────────────────────────────────
        crear_barra_superior(
            self,
            "Modo 3: Analytics — Análisis de Curvas I-V y Degradación",
            self._callback_volver,
        )

        # ── Cuerpo ──────────────────────────────────────────────────────────
        body = ttk.Frame(self, style="Window.TFrame")
        body.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))

        self._build_left(body)
        self._build_right(body)

    # ── Panel izquierdo ─────────────────────────────────────────────────────

    def _build_left(self, parent):
        left = ttk.Frame(parent, style="Window.TFrame", width=ui(320))
        left.pack(side="left", fill="y", padx=(0, ui(6)))
        left.pack_propagate(False)

        # [1] Carpeta de datos
        grp_folder = crear_seccion_frame(left, "[1] Carpeta de Datos", "params")

        self._lbl_folder = ttk.Label(
            grp_folder, text=self._carpeta, wraplength=ui(270), style="Params.TLabel"
        )
        self._lbl_folder.pack(padx=ui(6), pady=ui(2))

        f_fbtns = ttk.Frame(grp_folder, style="Params.TFrame")
        f_fbtns.pack(fill="x", padx=ui(4), pady=ui(2))
        ttk.Button(
            f_fbtns, text="Buscar...", command=self._browse_folder, style="Tool.TButton"
        ).pack(side="left", fill="x", expand=True, padx=ui(2))
        ttk.Button(
            f_fbtns, text="Actualizar", command=lambda: self._scan(self._carpeta), style="Tool.TButton"
        ).pack(side="left", fill="x", expand=True, padx=ui(2))

        # [2] Archivos encontrados
        grp_list = crear_seccion_frame(left, "[2] Archivos Encontrados", "results")

        self._lbl_summary = ttk.Label(grp_list, text="", style="Results.TLabel")
        self._lbl_summary.pack(padx=ui(4), pady=(0, ui(2)))

        cols = ("Sel", "Estado", "Archivo", "I", "V")
        self._tree = ttk.Treeview(grp_list, columns=cols, show="headings", selectmode="none", height=6)
        for col, w in zip(cols, (36, 28, 130, 44, 44)):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=ui(w), anchor="center" if col != "Archivo" else "w")
        self._tree.pack(fill="both", expand=True, padx=ui(4), pady=ui(2))
        self._tree.bind("<Button-1>", self._on_tree_click)

        self._btn_select_all = ttk.Button(
            grp_list, text="Seleccionar todos", command=self._toggle_select_all, state="disabled", style="Tool.TButton"
        )
        self._btn_select_all.pack(fill="x", padx=ui(4), pady=ui(2))

        # [3] Unidades del gráfico
        grp_units = crear_seccion_frame(left, "[3] Unidades del Gráfico", "params")

        f_u_grid = ttk.Frame(grp_units, style="Params.TFrame")
        f_u_grid.pack(fill="x", padx=ui(4), pady=ui(2))

        ttk.Label(f_u_grid, text="Intensidad:", style="Params.TLabel").grid(
            row=0, column=0, padx=ui(4), pady=ui(2), sticky="w"
        )
        self._cb_unit_i = ttk.Combobox(
            f_u_grid, values=list(UNIT_FACTORS["I"].keys()), width=6, state="readonly"
        )
        self._cb_unit_i.set("mA")
        self._cb_unit_i.grid(row=0, column=1, padx=ui(4), pady=ui(2))
        self._cb_unit_i.bind("<<ComboboxSelected>>", lambda e: setattr(self, "_needs_regen", True))

        ttk.Label(f_u_grid, text="Voltaje:", style="Params.TLabel").grid(
            row=0, column=2, padx=(ui(8), ui(4)), pady=ui(2), sticky="w"
        )
        self._cb_unit_v = ttk.Combobox(
            f_u_grid, values=list(UNIT_FACTORS["V"].keys()), width=6, state="readonly"
        )
        self._cb_unit_v.set("V")
        self._cb_unit_v.grid(row=0, column=3, padx=ui(4), pady=ui(2))
        self._cb_unit_v.bind("<<ComboboxSelected>>", lambda e: setattr(self, "_needs_regen", True))

        self._needs_regen = False

        # [4] Control de Acciones
        grp_act = crear_seccion_frame(left, "[4] Control y Exportación", "control")

        self._btn_generate = ttk.Button(
            grp_act, text="▶ GENERAR GRÁFICO I-V", command=self._generate_plot, state="disabled", style="Primary.TButton"
        )
        self._btn_generate.pack(fill="x", padx=ui(4), pady=ui(2))

        self._btn_export_excel = ttk.Button(
            grp_act, text="Exportar Excel Combinado", command=self._export_excel, state="disabled", style="Tool.TButton"
        )
        self._btn_export_excel.pack(fill="x", padx=ui(4), pady=ui(2))

    # ── Panel derecho ────────────────────────────────────────────────────────

    def _build_right(self, parent):
        right = ttk.Frame(parent, style="Window.TFrame")
        right.pack(side="right", fill="both", expand=True)

        # Notebook IV / Isc
        self._notebook = ttk.Notebook(right)
        self._notebook.pack(fill="both", expand=True)
        self._iv_tab = ttk.Frame(self._notebook, style="Window.TFrame")
        self._isc_tab = ttk.Frame(self._notebook, style="Window.TFrame")
        self._notebook.add(self._iv_tab, text="Curvas I-V")
        self._notebook.add(self._isc_tab, text="Isc vs Tiempo")
        self._notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_change())

        self._canvas = FigureCanvasTkAgg(self._fig, master=self._iv_tab)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._toolbar = NavigationToolbar2Tk(self._canvas, self._iv_tab)
        self._toolbar.update()

        # Controles del gráfico
        grp_ctrl = crear_seccion_frame(right, "Controles y Ajuste del Gráfico", "params")
        grp_ctrl.pack(fill="x", pady=ui(3))

        f_c_grid = ttk.Frame(grp_ctrl, style="Params.TFrame")
        f_c_grid.pack(fill="x", padx=ui(4), pady=ui(2))

        for label, attr in (("X min:", "_entry_xmin"), ("X max:", "_entry_xmax"),
                             ("Y min:", "_entry_ymin"), ("Y max:", "_entry_ymax")):
            row_offset = 0 if "min" in label.lower() else 1
            col_offset = 0 if "X" in label else 2
            ttk.Label(f_c_grid, text=label, style="Params.TLabel").grid(
                row=row_offset, column=col_offset, padx=ui(3), pady=ui(1), sticky="w")
            entry = ttk.Entry(f_c_grid, width=7)
            entry.grid(row=row_offset, column=col_offset + 1, padx=ui(3), pady=ui(1))
            setattr(self, attr, entry)

        ttk.Button(f_c_grid, text="Aplicar Límites", command=self._apply_limits, style="Tool.TButton").grid(
            row=0, column=4, rowspan=2, padx=ui(6), pady=ui(1))
        ttk.Button(f_c_grid, text="Autoajuste", command=self._reset_limits, style="Tool.TButton").grid(
            row=0, column=5, rowspan=2, padx=ui(3), pady=ui(1))

        self._var_swap = tk.BooleanVar(value=False)
        self._var_inv_x = tk.BooleanVar(value=False)
        self._var_inv_y = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_c_grid, text="Intercambiar X/Y", variable=self._var_swap,
                        command=lambda: self._generate_plot() if self._graph_generated_iv else None,
                        style="Params.TCheckbutton").grid(row=0, column=6, padx=ui(6), sticky="w")
        ttk.Checkbutton(f_c_grid, text="Invertir X", variable=self._var_inv_x,
                        command=self._update_axes_dir,
                        style="Params.TCheckbutton").grid(row=1, column=6, padx=ui(6), sticky="w")
        ttk.Checkbutton(f_c_grid, text="Invertir Y", variable=self._var_inv_y,
                        command=self._update_axes_dir,
                        style="Params.TCheckbutton").grid(row=0, column=7, padx=ui(6), sticky="w")

        self._cb_line_style = ttk.Combobox(f_c_grid,
                                           values=list(_LINE_STYLES.keys()),
                                           width=16, state="readonly")
        self._cb_line_style.set("Línea continua (-)")
        self._cb_line_style.grid(row=1, column=7, padx=ui(4))
        self._cb_line_style.bind("<<ComboboxSelected>>",
                                 lambda e: self._generate_plot() if self._graph_generated_iv else None)

        ttk.Button(f_c_grid, text="Exportar Gráfico...",
                   command=self._export_plot, style="Tool.TButton").grid(row=0, column=8, rowspan=2, padx=ui(6))

    # ── Lógica de datos ──────────────────────────────────────────────────────

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self._carpeta)
        if folder:
            self._scan(folder)

    def _scan(self, carpeta: str):
        self._carpeta = carpeta
        self._lbl_folder.configure(text=carpeta)
        self._entradas = escanear_carpeta(carpeta)

        self._tree.delete(*self._tree.get_children())
        self._seleccionadas.clear()
        self._graph_generated_iv = False
        self._graph_generated_isc = False

        count_ok = 0
        for e in self._entradas:
            estado = "✓" if not e["error"] else "✗"
            iid = self._tree.insert(
                "", "end",
                values=("☐", estado, e["nombre"], e["unidad_i"], e["unidad_v"]),
            )
            e["iid"] = iid
            if not e["error"]:
                count_ok += 1

        total = len(self._entradas)
        self._lbl_summary.configure(
            text=f"{count_ok}/{total} archivos válidos" if total else "Sin archivos Excel."
        )
        self._btn_select_all.configure(state="normal" if count_ok > 0 else "disabled")
        self._btn_generate.configure(state="disabled")
        self._btn_export_excel.configure(state="disabled")

    def _on_tree_click(self, event):
        item = self._tree.identify_row(event.y)
        if not item:
            return
        entrada = next((e for e in self._entradas if e.get("iid") == item), None)
        if entrada is None or entrada.get("error"):
            return

        nombre = entrada["nombre"]
        vals = list(self._tree.item(item, "values"))
        if nombre in self._seleccionadas:
            self._seleccionadas.discard(nombre)
            vals[0] = "☐"
        else:
            self._seleccionadas.add(nombre)
            vals[0] = "☑"
        self._tree.item(item, values=vals)
        self._btn_generate.configure(
            state="normal" if self._seleccionadas else "disabled"
        )
        self._btn_export_excel.configure(
            state="normal" if self._seleccionadas else "disabled"
        )

    def _toggle_select_all(self):
        validas = [e for e in self._entradas if not e.get("error")]
        if len(self._seleccionadas) == len(validas):
            for e in validas:
                self._seleccionadas.discard(e["nombre"])
                vals = list(self._tree.item(e["iid"], "values"))
                vals[0] = "☐"
                self._tree.item(e["iid"], values=vals)
            self._btn_select_all.configure(text="Seleccionar todos")
        else:
            for e in validas:
                self._seleccionadas.add(e["nombre"])
                vals = list(self._tree.item(e["iid"], "values"))
                vals[0] = "☑"
                self._tree.item(e["iid"], values=vals)
            self._btn_select_all.configure(text="Deseleccionar todos")

        state = "normal" if self._seleccionadas else "disabled"
        self._btn_generate.configure(state=state)
        self._btn_export_excel.configure(state=state)

    # ── Gráficas ─────────────────────────────────────────────────────────────

    def _generate_plot(self):
        seleccionadas = [e for e in self._entradas if e["nombre"] in self._seleccionadas]
        if not seleccionadas:
            messagebox.showwarning("Aviso", "No hay archivos seleccionados.")
            return

        u_i = self._cb_unit_i.get()
        u_v = self._cb_unit_v.get()
        df_iv, df_sum = combinar_iv(seleccionadas, u_i, u_v)
        self._last_summary = df_sum

        self._ax.clear()
        ls = _LINE_STYLES.get(self._cb_line_style.get(), "-")
        swap = self._var_swap.get()

        archivos = df_iv.columns.levels[0]
        self._lines_data = []
        for arch in archivos:
            sub = df_iv[arch]
            x_vals = sub["V"] if not swap else sub["I"]
            y_vals = sub["I"] if not swap else sub["V"]
            line, = self._ax.plot(x_vals, y_vals, ls, label=arch, picker=5)
            self._lines_data.append((line, arch, x_vals.values, y_vals.values))

        x_lbl = f"Voltaje ({u_v})" if not swap else f"Intensidad ({u_i})"
        y_lbl = f"Intensidad ({u_i})" if not swap else f"Voltaje ({u_v})"
        self._ax.set_xlabel(x_lbl)
        self._ax.set_ylabel(y_lbl)
        self._ax.set_title("Curvas I-V Comparativas")
        self._ax.grid(True, linestyle="--", alpha=0.5)
        if len(archivos) <= 15:
            self._ax.legend(fontsize=7, loc="best")

        self._update_axes_dir()
        self._update_entry_limits()
        self._setup_hover()
        self._canvas.draw()
        self._graph_generated_iv = True
        self._needs_regen = False

    def _generate_isc_plot(self):
        seleccionadas = [e for e in self._entradas if e["nombre"] in self._seleccionadas]
        if not seleccionadas:
            return

        u_i = self._cb_unit_i.get()
        u_v = self._cb_unit_v.get()
        _, df_sum = combinar_iv(seleccionadas, u_i, u_v)

        if COL_DATETIME not in df_sum.columns or df_sum[COL_DATETIME].isna().all():
            df_sum["_idx"] = range(len(df_sum))
            x_col = "_idx"
            x_label = "Muestra"
            use_dates = False
        else:
            x_col = COL_DATETIME
            x_label = "Fecha / Hora"
            use_dates = True

        self._ax.clear()
        y_col = f"Isc ({u_i})"
        if y_col not in df_sum.columns:
            y_col = "Isc (A)"

        self._ax.plot(df_sum[x_col], df_sum[y_col], "o-", color="#0284c7", label=y_col)
        self._ax.set_xlabel(x_label)
        self._ax.set_ylabel(y_col)
        self._ax.set_title("Evolución de Isc")
        self._ax.grid(True, linestyle="--", alpha=0.5)

        if use_dates:
            self._ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
            self._fig.autofmt_xdate()

        self._canvas.draw()
        self._graph_generated_isc = True

    def _on_tab_change(self):
        tab_idx = self._notebook.index("current")
        if tab_idx == 0:
            self._canvas.get_tk_widget().pack_forget()
            self._toolbar.pack_forget()
            self._canvas = FigureCanvasTkAgg(self._fig, master=self._iv_tab)
            self._canvas.get_tk_widget().pack(fill="both", expand=True)
            self._toolbar = NavigationToolbar2Tk(self._canvas, self._iv_tab)
            self._toolbar.update()
            if self._graph_generated_iv and not self._needs_regen:
                self._canvas.draw()
            elif self._seleccionadas:
                self._generate_plot()
        else:
            self._canvas.get_tk_widget().pack_forget()
            self._toolbar.pack_forget()
            self._canvas = FigureCanvasTkAgg(self._fig, master=self._isc_tab)
            self._canvas.get_tk_widget().pack(fill="both", expand=True)
            self._toolbar = NavigationToolbar2Tk(self._canvas, self._isc_tab)
            self._toolbar.update()
            self._generate_isc_plot()

    # ── Hover tooltips ───────────────────────────────────────────────────────

    def _setup_hover(self):
        if self._hover_cid is not None:
            self._fig.canvas.mpl_disconnect(self._hover_cid)

        self._annot = self._ax.annotate(
            "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="#0f172a", ec="#38bdf8", lw=1),
            color="#f8fafc", fontsize=8,
        )
        self._annot.set_visible(False)

        def _on_move(event):
            if event.inaxes != self._ax:
                if self._annot.get_visible():
                    self._annot.set_visible(False)
                    self._canvas.draw_idle()
                return

            found = False
            for line, arch, xs, ys in getattr(self, "_lines_data", []):
                cont, ind = line.contains(event)
                if cont and ind["ind"].size:
                    idx = ind["ind"][0]
                    x, y = xs[idx], ys[idx]
                    self._annot.xy = (x, y)
                    u_v = self._cb_unit_v.get()
                    u_i = self._cb_unit_i.get()
                    self._annot.set_text(f"{arch}\nV={x:.3f} {u_v}\nI={y:.3e} {u_i}")
                    self._annot.set_visible(True)
                    self._canvas.draw_idle()
                    found = True
                    break

            if not found and self._annot.get_visible():
                self._annot.set_visible(False)
                self._canvas.draw_idle()

        self._hover_cid = self._fig.canvas.mpl_connect("motion_notify_event", _on_move)

    # ── Controles de ejes ────────────────────────────────────────────────────

    def _update_axes_dir(self):
        if self._var_inv_x.get():
            if not self._ax.xaxis_inverted():
                self._ax.invert_xaxis()
        else:
            if self._ax.xaxis_inverted():
                self._ax.invert_xaxis()

        if self._var_inv_y.get():
            if not self._ax.yaxis_inverted():
                self._ax.invert_yaxis()
        else:
            if self._ax.yaxis_inverted():
                self._ax.invert_yaxis()
        self._canvas.draw_idle()

    def _apply_limits(self):
        try:
            xmin = float(self._entry_xmin.get()) if self._entry_xmin.get() else None
            xmax = float(self._entry_xmax.get()) if self._entry_xmax.get() else None
            ymin = float(self._entry_ymin.get()) if self._entry_ymin.get() else None
            ymax = float(self._entry_ymax.get()) if self._entry_ymax.get() else None
            if xmin is not None and xmax is not None:
                self._ax.set_xlim(xmin, xmax)
            if ymin is not None and ymax is not None:
                self._ax.set_ylim(ymin, ymax)
            self._update_axes_dir()
            self._canvas.draw_idle()
        except ValueError:
            messagebox.showerror("Error", "Los límites deben ser números válidos.")

    def _reset_limits(self):
        self._ax.autoscale()
        self._update_axes_dir()
        self._update_entry_limits()
        self._canvas.draw_idle()

    def _update_entry_limits(self):
        xlim = self._ax.get_xlim()
        ylim = self._ax.get_ylim()
        for entry, val in ((self._entry_xmin, xlim[0]), (self._entry_xmax, xlim[1]),
                           (self._entry_ymin, ylim[0]), (self._entry_ymax, ylim[1])):
            entry.delete(0, "end")
            entry.insert(0, f"{val:.3f}")

    # ── Exportaciones ────────────────────────────────────────────────────────

    def _export_excel(self):
        if self._last_summary is None or self._last_summary.empty:
            messagebox.showwarning("Aviso", "Genera primero el gráfico para preparar los datos.")
            return

        dest = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="Guardar resumen combinado",
        )
        if not dest:
            return

        try:
            with pd.ExcelWriter(dest) as writer:
                self._last_summary.to_excel(writer, sheet_name="Resumen", index=False)
            messagebox.showinfo("Exportado", f"Excel guardado en:\n{dest}")
        except Exception as exc:
            messagebox.showerror("Error al guardar", str(exc))

    def _export_plot(self):
        dest = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
            title="Exportar gráfico",
        )
        if not dest:
            return
        try:
            self._fig.savefig(dest, dpi=300, bbox_inches="tight")
            messagebox.showinfo("Exportado", f"Gráfico guardado en:\n{dest}")
        except Exception as exc:
            messagebox.showerror("Error al guardar", str(exc))
