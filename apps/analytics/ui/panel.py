"""Panel UI de Analytics — integra el theme del resto de apps.

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
from core.ui_kit.assets import load_logo


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
        self._logo = None
        self._build()

    def _t(self):
        return theme_mgr.get_current_theme()

    def _build(self):
        t = self._t()
        self.configure(style="Window.TFrame")

        # ── Barra superior ──────────────────────────────────────────────────
        top = ttk.Frame(self, style="Header.TFrame")
        top.pack(fill="x", padx=ui(12), pady=(ui(8), 0))

        self._logo = load_logo("logo_y_texto.png", (120, 92))
        if self._logo:
            tk.Label(top, image=self._logo, bg=t["bg_window"],
                     borderwidth=0, highlightthickness=0).pack(side="left")

        btn_back = ttk.Button(top, text="← Menú",
                              command=self._callback_volver)
        btn_back.pack(side="right", padx=ui(6))

        ttk.Label(top, text="Analytics — Análisis de curvas IV",
                  font=ui_font("Segoe UI", UIConfig.SIZE_SECTION_HEADER, "bold"),
                  style="Window.TLabel").pack(side="left", padx=ui(12))

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=ui(6))

        # ── Cuerpo ──────────────────────────────────────────────────────────
        body = ttk.Frame(self, style="Window.TFrame")
        body.pack(fill="both", expand=True, padx=ui(10), pady=ui(6))
        body.columnconfigure(0, weight=0, minsize=ui(280))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    # ── Panel izquierdo ─────────────────────────────────────────────────────

    def _build_left(self, parent):
        left = ttk.Frame(parent, style="Window.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, ui(8)))

        # Carpeta
        grp_folder = ttk.LabelFrame(left, text="Carpeta de datos")
        grp_folder.pack(fill="x", pady=ui(4))

        self._lbl_folder = ttk.Label(grp_folder, text=self._carpeta,
                                     wraplength=ui(250), style="Window.TLabel")
        self._lbl_folder.pack(padx=ui(6), pady=ui(4))

        ttk.Button(grp_folder, text="Seleccionar carpeta…",
                   command=self._browse_folder).pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Button(grp_folder, text="Actualizar / Escanear",
                   command=lambda: self._scan(self._carpeta)).pack(fill="x", padx=ui(6), pady=ui(2))

        self._lbl_summary = ttk.Label(left, text="", style="Window.TLabel")
        self._lbl_summary.pack(pady=ui(4))

        # Lista de archivos
        grp_list = ttk.LabelFrame(left, text="Archivos encontrados")
        grp_list.pack(fill="both", expand=True, pady=ui(4))

        cols = ("Sel", "Estado", "Archivo", "I", "V")
        self._tree = ttk.Treeview(grp_list, columns=cols, show="headings",
                                  selectmode="none")
        for col, w in zip(cols, (36, 28, 130, 44, 44)):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=ui(w), anchor="center" if col != "Archivo" else "w")
        self._tree.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))
        self._tree.bind("<Button-1>", self._on_tree_click)

        self._btn_select_all = ttk.Button(grp_list, text="Seleccionar todos",
                                          command=self._toggle_select_all,
                                          state="disabled")
        self._btn_select_all.pack(fill="x", padx=ui(4), pady=(0, ui(4)))

        # Unidades
        grp_units = ttk.LabelFrame(left, text="Unidades del gráfico")
        grp_units.pack(fill="x", pady=ui(4))

        ttk.Label(grp_units, text="Intensidad:", style="Window.TLabel").grid(
            row=0, column=0, padx=ui(4), pady=ui(4), sticky="w")
        self._cb_unit_i = ttk.Combobox(grp_units,
                                       values=list(UNIT_FACTORS["I"].keys()),
                                       width=5, state="readonly")
        self._cb_unit_i.set("mA")
        self._cb_unit_i.grid(row=0, column=1, padx=ui(4), pady=ui(4))
        self._cb_unit_i.bind("<<ComboboxSelected>>", lambda e: setattr(self, "_needs_regen", True))

        ttk.Label(grp_units, text="Voltaje:", style="Window.TLabel").grid(
            row=1, column=0, padx=ui(4), pady=ui(4), sticky="w")
        self._cb_unit_v = ttk.Combobox(grp_units,
                                       values=list(UNIT_FACTORS["V"].keys()),
                                       width=5, state="readonly")
        self._cb_unit_v.set("V")
        self._cb_unit_v.grid(row=1, column=1, padx=ui(4), pady=ui(4))
        self._cb_unit_v.bind("<<ComboboxSelected>>", lambda e: setattr(self, "_needs_regen", True))

        self._needs_regen = False

        self._btn_generate = ttk.Button(left, text="Generar gráfico IV",
                                        command=self._generate_plot,
                                        state="disabled")
        self._btn_generate.pack(fill="x", pady=ui(6))

        self._btn_export_excel = ttk.Button(left, text="Exportar Excel combinado",
                                            command=self._export_excel,
                                            state="disabled")
        self._btn_export_excel.pack(fill="x", pady=(0, ui(6)))

    # ── Panel derecho ────────────────────────────────────────────────────────

    def _build_right(self, parent):
        right = ttk.Frame(parent, style="Window.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        # Notebook IV / Isc
        self._notebook = ttk.Notebook(right)
        self._notebook.grid(row=0, column=0, sticky="nsew")
        self._iv_tab = ttk.Frame(self._notebook)
        self._isc_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._iv_tab, text="IV")
        self._notebook.add(self._isc_tab, text="Isc")
        self._notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_change())

        self._canvas = FigureCanvasTkAgg(self._fig, master=self._iv_tab)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._toolbar = NavigationToolbar2Tk(self._canvas, self._iv_tab)
        self._toolbar.update()

        # Controles del gráfico
        grp_ctrl = ttk.LabelFrame(right, text="Controles del gráfico")
        grp_ctrl.grid(row=1, column=0, sticky="ew", pady=ui(4))

        r, c = 0, 0
        for label, attr in (("X min:", "_entry_xmin"), ("X max:", "_entry_xmax"),
                             ("Y min:", "_entry_ymin"), ("Y max:", "_entry_ymax")):
            row_offset = 0 if "min" in label.lower() else 1
            col_offset = 0 if "X" in label else 2
            ttk.Label(grp_ctrl, text=label, style="Window.TLabel").grid(
                row=row_offset, column=col_offset, padx=ui(3))
            entry = ttk.Entry(grp_ctrl, width=8)
            entry.grid(row=row_offset, column=col_offset + 1, padx=ui(3))
            setattr(self, attr, entry)

        ttk.Button(grp_ctrl, text="Aplicar", command=self._apply_limits).grid(
            row=0, column=4, rowspan=2, padx=ui(8))
        ttk.Button(grp_ctrl, text="Reiniciar", command=self._reset_limits).grid(
            row=0, column=5, rowspan=2, padx=ui(4))

        self._var_swap = tk.BooleanVar(value=False)
        self._var_inv_x = tk.BooleanVar(value=False)
        self._var_inv_y = tk.BooleanVar(value=False)
        ttk.Checkbutton(grp_ctrl, text="Intercambiar X/Y", variable=self._var_swap,
                        command=lambda: self._generate_plot() if self._graph_generated_iv else None
                        ).grid(row=0, column=6, padx=ui(8))
        ttk.Checkbutton(grp_ctrl, text="Invertir X", variable=self._var_inv_x,
                        command=self._update_axes_dir).grid(row=1, column=6, sticky="w")
        ttk.Checkbutton(grp_ctrl, text="Invertir Y", variable=self._var_inv_y,
                        command=self._update_axes_dir).grid(row=2, column=6, sticky="w")

        self._cb_line_style = ttk.Combobox(grp_ctrl,
                                           values=list(_LINE_STYLES.keys()),
                                           width=18, state="readonly")
        self._cb_line_style.set("Línea continua (-)")
        self._cb_line_style.grid(row=0, column=7, columnspan=2, padx=ui(6))
        self._cb_line_style.bind("<<ComboboxSelected>>",
                                 lambda e: self._generate_plot() if self._graph_generated_iv else None)

        ttk.Button(grp_ctrl, text="Exportar gráfico…",
                   command=self._export_plot).grid(row=2, column=7, padx=ui(6))

    # ── Lógica de datos ──────────────────────────────────────────────────────

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self._carpeta)
        if folder:
            self._scan(folder)

    def _scan(self, carpeta: str):
        self._carpeta = carpeta
        self._lbl_folder.configure(text=carpeta)
        self._entradas = escanear_carpeta(carpeta)

        # Poblar árbol
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
        # Encontrar entrada
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
            # Deselect all
            for e in validas:
                self._seleccionadas.discard(e["nombre"])
                vals = list(self._tree.item(e["iid"], "values"))
                vals[0] = "☐"
                self._tree.item(e["iid"], values=vals)
            self._btn_select_all.configure(text="Seleccionar todos")
        else:
            # Select all
            for e in validas:
                self._seleccionadas.add(e["nombre"])
                vals = list(self._tree.item(e["iid"], "values"))
                vals[0] = "☑"
                self._tree.item(e["iid"], values=vals)
            self._btn_select_all.configure(text="Deseleccionar todos")

        state = "normal" if self._seleccionadas else "disabled"
        self._btn_generate.configure(state=state)
        self._btn_export_excel.configure(state=state)

    def _entradas_seleccionadas(self) -> list[dict]:
        return [e for e in self._entradas if e["nombre"] in self._seleccionadas]

    # ── Gráficas ─────────────────────────────────────────────────────────────

    def _generate_plot(self):
        entradas = self._entradas_seleccionadas()
        if not entradas:
            messagebox.showwarning("Sin selección", "Selecciona al menos un archivo.")
            return

        unidad_i = self._cb_unit_i.get()
        unidad_v = self._cb_unit_v.get()
        combined_iv, combined_summary = combinar_iv(entradas, unidad_i, unidad_v)

        if combined_iv.empty:
            messagebox.showwarning("Sin datos", "No se pudieron combinar los datos IV.")
            return

        self._last_summary = combined_summary
        self._graph_generated_iv = True
        self._needs_regen = False

        self._ax.clear()
        self._desconectar_hover()

        linestyle = _LINE_STYLES.get(self._cb_line_style.get(), "-")
        swap = self._var_swap.get()

        scatter_data = {}
        for archivo in combined_iv.columns.get_level_values(0).unique():
            df_a = combined_iv[archivo].dropna()
            i_vals = df_a.iloc[:, 0].to_numpy()
            v_vals = df_a.iloc[:, 1].to_numpy()
            x, y = (i_vals, v_vals) if swap else (v_vals, i_vals)
            line, = self._ax.plot(x, y, linestyle=linestyle, marker="o",
                                  markersize=3, linewidth=1, label=archivo)
            scatter_data[archivo] = (x, y, line)

        xlabel = f"I ({unidad_i})" if swap else f"V ({unidad_v})"
        ylabel = f"V ({unidad_v})" if swap else f"I ({unidad_i})"
        self._ax.set_xlabel(xlabel)
        self._ax.set_ylabel(ylabel)
        self._ax.set_title("Curvas IV comparativas")
        self._ax.grid(True, alpha=0.4)
        self._update_axes_dir()

        # Tooltip hover
        self._annot = self._ax.annotate(
            "", xy=(0, 0), xytext=(10, 10),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", ec="gray", alpha=0.9),
            fontsize=8, visible=False,
        )

        scatter_list = list(scatter_data.values())

        def _hover(event):
            if event.inaxes != self._ax:
                return
            for x_data, y_data, line in scatter_list:
                if len(x_data) == 0:
                    continue
                try:
                    xd, yd = self._ax.transData.transform(
                        np.c_[x_data, y_data]
                    ).T
                    dist = np.hypot(xd - event.x, yd - event.y)
                    idx = dist.argmin()
                    if dist[idx] < _HOVER_RADIUS_PX:
                        self._annot.set_text(
                            f"X={x_data[idx]:.4g}\nY={y_data[idx]:.4g}"
                        )
                        self._annot.xy = (x_data[idx], y_data[idx])
                        self._annot.set_visible(True)
                        self._canvas.draw_idle()
                        return
                except Exception:
                    pass
            self._annot.set_visible(False)
            self._canvas.draw_idle()

        self._hover_cid = self._canvas.mpl_connect("motion_notify_event", _hover)

        if len(scatter_data) > 1:
            self._ax.legend(fontsize=7)
        self._canvas.draw()

    def _generate_isc_plot(self):
        if self._last_summary is None or self._last_summary.empty:
            messagebox.showwarning("Sin datos", "Genera primero el gráfico IV.")
            return

        self._ax.clear()
        self._desconectar_hover()
        self._graph_generated_isc = True

        df = self._last_summary.copy()
        col_dt = COL_DATETIME if COL_DATETIME in df.columns else None
        col_isc = "Isc" if "Isc" in df.columns else ("Isc (A)" if "Isc (A)" in df.columns else None)

        if col_dt is None or col_isc is None:
            messagebox.showwarning(
                "Sin datos temporales",
                "El Excel no contiene columna de fecha/hora o Isc para este gráfico."
            )
            return

        df[col_dt] = pd.to_datetime(df[col_dt], dayfirst=True, errors="coerce")
        df[col_isc] = pd.to_numeric(df[col_isc], errors="coerce")
        df = df.dropna(subset=[col_dt, col_isc])

        for nombre, group in df.groupby(COL_ARCHIVO):
            xd = group[col_dt].dt.to_pydatetime()
            yd = group[col_isc].to_numpy(dtype=float)
            self._ax.plot(xd, yd, marker="o", linestyle="-", label=nombre)

        self._ax.set_xlabel("Fecha y hora inicio")
        self._ax.set_ylabel("Isc")
        self._ax.set_title("Isc en función del tiempo")
        self._ax.grid(True, alpha=0.4)
        self._ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        self._fig.autofmt_xdate(rotation=30)
        self._ax.legend(fontsize=7)
        self._canvas.draw()

    def _on_tab_change(self):
        selected = self._notebook.tab(self._notebook.select(), "text")
        parent = self._iv_tab if selected == "IV" else self._isc_tab

        try:
            self._toolbar.destroy()
        except Exception:
            pass
        try:
            self._canvas.get_tk_widget().pack_forget()
        except Exception:
            pass

        self._canvas = FigureCanvasTkAgg(self._fig, master=parent)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._toolbar = NavigationToolbar2Tk(self._canvas, parent)
        self._toolbar.update()

        if selected == "IV":
            if self._graph_generated_iv:
                self._generate_plot()
            else:
                self._ax.clear()
                self._ax.set_title("Pulsa «Generar gráfico IV» para empezar")
                self._canvas.draw()
        else:
            if self._graph_generated_isc:
                self._generate_isc_plot()
            else:
                self._ax.clear()
                self._ax.set_title("Genera el gráfico IV primero")
                self._canvas.draw()

    def _desconectar_hover(self):
        if self._hover_cid is not None:
            try:
                self._canvas.mpl_disconnect(self._hover_cid)
            except Exception:
                pass
            self._hover_cid = None

    def _apply_limits(self):
        try:
            xmin = float(self._entry_xmin.get()) if self._entry_xmin.get() else None
            xmax = float(self._entry_xmax.get()) if self._entry_xmax.get() else None
            ymin = float(self._entry_ymin.get()) if self._entry_ymin.get() else None
            ymax = float(self._entry_ymax.get()) if self._entry_ymax.get() else None
            if xmin is not None or xmax is not None:
                self._ax.set_xlim(xmin, xmax)
            if ymin is not None or ymax is not None:
                self._ax.set_ylim(ymin, ymax)
            self._canvas.draw()
        except ValueError:
            messagebox.showwarning("Error", "Introduce valores numéricos válidos.")

    def _reset_limits(self):
        self._ax.relim()
        self._ax.autoscale()
        self._canvas.draw()

    def _update_axes_dir(self):
        if self._var_inv_x.get():
            self._ax.invert_xaxis()
        if self._var_inv_y.get():
            self._ax.invert_yaxis()
        self._canvas.draw()

    def _export_excel(self):
        entradas = self._entradas_seleccionadas()
        unidad_i = self._cb_unit_i.get()
        unidad_v = self._cb_unit_v.get()
        combined_iv, combined_summary = combinar_iv(entradas, unidad_i, unidad_v)

        if combined_iv.empty:
            messagebox.showwarning("Sin datos", "No hay datos para exportar.")
            return

        save_path = filedialog.asksaveasfilename(
            initialdir=self._carpeta,
            initialfile="iv_combinado.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("Todos", "*.*")],
        )
        if not save_path:
            return

        try:
            with pd.ExcelWriter(save_path, engine="openpyxl") as writer:
                df_write = combined_iv.copy()
                if isinstance(df_write.columns, pd.MultiIndex):
                    df_write.columns = [f"{a}_{b}" for a, b in df_write.columns]
                df_write.to_excel(writer, sheet_name="datos_IV", index=False)
                if not combined_summary.empty:
                    combined_summary.to_excel(writer, sheet_name="resumen", index=False)
            messagebox.showinfo("Éxito", f"Archivo exportado a:\n{save_path}")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo exportar:\n{exc}")

    def _export_plot(self):
        tab = self._notebook.tab(self._notebook.select(), "text")
        if tab == "IV" and not self._graph_generated_iv:
            messagebox.showwarning("Sin gráfico", "Genera primero el gráfico IV.")
            return
        if tab == "Isc" and not self._graph_generated_isc:
            messagebox.showwarning("Sin gráfico", "Genera primero el gráfico Isc.")
            return

        default = "grafico_iv.png" if tab == "IV" else "grafico_isc.png"
        save_path = filedialog.asksaveasfilename(
            initialdir=self._carpeta,
            initialfile=default,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("Todos", "*.*")],
        )
        if not save_path:
            return

        try:
            if tab == "Isc":
                self._generate_isc_plot()
            else:
                self._generate_plot()
            self._fig.savefig(save_path, dpi=300, bbox_inches="tight")
            messagebox.showinfo("Éxito", f"Gráfico exportado a:\n{save_path}")
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo exportar:\n{exc}")
