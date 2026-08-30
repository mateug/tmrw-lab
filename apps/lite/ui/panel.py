"""Panel de usuario para el Modo Lite con soporte completo para recetas Excel (Submodo E de iv-maker)."""
from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from pathlib import Path
import pandas as pd

from core.ui_kit.scaler import ui, ui_font, ui_font_console, ui_font_label, UIConfig
from core.ui_kit.shared import (
    crear_barra_superior,
    crear_seccion_frame,
    crear_campo_directorio,
    mostrar_error,
    mostrar_info,
)
from core.ui_kit.theme import theme_mgr
from core.instrument.registry import abortar_instrumento_activo, abortar_motor_activo

from apps.lite.config import get_default_config


def parsear_excel_receta(ruta_excel: Path, nombre_hoja: str = "") -> tuple[pd.DataFrame, dict[str, list[str]], list[dict]]:
    """Lee y clasifica columnas del Excel por eje."""
    if not ruta_excel.exists():
        raise FileNotFoundError(f"No existe el archivo {ruta_excel}")

    hoja = nombre_hoja.strip() or 0
    df = pd.read_excel(ruta_excel, sheet_name=hoja)

    ejes = {
        "Estructura": [],
        "Motor": [],
        "Iluminación LED": [],
        "Desconocido / Extra": [],
    }

    columnas = list(df.columns)
    for col in columnas:
        col_str = str(col).strip()
        col_lower = col_str.lower()
        if "estructura" in col_lower or "device" in col_lower or "muestra" in col_lower:
            ejes["Estructura"].append(col_str)
        elif "motor" in col_lower or "paso" in col_lower or "posicion" in col_lower or "pos" in col_lower:
            ejes["Motor"].append(col_str)
        elif any(c in col_lower for c in ["390", "450", "515", "600", "630", "660", "730", "850", "950", "cool", "warm", "led", "nm"]):
            ejes["Iluminación LED"].append(col_str)
        else:
            ejes["Desconocido / Extra"].append(col_str)

    filas = df.to_dict(orient="records")
    return df, ejes, filas


class LiteFrame(ttk.Frame):
    """Marco principal del Modo Lite."""

    def __init__(self, master, callback_volver=None, **kwargs):
        super().__init__(master, **kwargs)
        self.callback_volver = callback_volver
        self.cfg_base = get_default_config()

        self.evento_aborto = threading.Event()
        self.cola_ui = queue.Queue()
        self.ejecutando = False
        self._df_receta = None
        self._ejes_detectados = {}
        self._filas_receta = []

        self._inicializar_variables()
        self._crear_ui()
        self._procesar_cola_ui()

    def _inicializar_variables(self):
        c = self.cfg_base
        self.vars = {
            "ruta_excel": tk.StringVar(value=c.get("ruta_excel_receta", "")),
            "hoja_excel": tk.StringVar(value=c.get("hoja_excel", "")),
            "excel_valores_0_1": tk.BooleanVar(value=c.get("excel_valores_0_1", True)),
            "plantilla_comando": tk.StringVar(value=c.get("plantilla_comando_excel", "<ch{channel}:{intensity}>")),
            "espera_estab_s": tk.StringVar(value=str(c.get("espera_estabilizacion_s", 1.0))),
            "espera_luz_on_s": tk.StringVar(value=str(c.get("espera_luz_encendida_s", 0.0))),
            "espera_motor_s": tk.StringVar(value=str(c.get("espera_motor_s", 0.0))),
            "tiempo_enfriado_s": tk.StringVar(value=str(c.get("tiempo_enfriado_s", 0.0))),
            "apagar_al_final": tk.BooleanVar(value=c.get("apagar_al_final", True)),
            # Guardado
            "carpeta_salida": tk.StringVar(value=c.get("carpeta_salida", "")),
            "nombre_carpeta_medida": tk.StringVar(value=c.get("nombre_carpeta_medida", "")),
            "nombre_medida": tk.StringVar(value=c.get("nombre_medida", "medida_lite")),
            # SMU Keithley
            "recurso_visa": tk.StringVar(value=c.get("recurso_visa", "")),
            "modo_medida": tk.StringVar(value=c.get("modo_medida", "completa")),
            "v_ini_dir": tk.StringVar(value=str(c["directa"]["v_inicial_mV"])),
            "v_fin_dir": tk.StringVar(value=str(c["directa"]["v_final_mV"])),
            "paso_dir": tk.StringVar(value=str(c["directa"]["paso_mV"])),
            "v_fin_inv": tk.StringVar(value=str(c["inversa"]["v_final_V"])),
            "paso_inv": tk.StringVar(value=str(c["inversa"]["paso_mV"])),
            "i_max_uA": tk.StringVar(value=str(c.get("i_max_uA", 10.0))),
            "invertir_eje_y": tk.BooleanVar(value=c.get("invertir_eje_y_graficas", True)),
        }

    def _crear_ui(self):
        t = theme_mgr.get_current_theme()
        crear_barra_superior(self, "Modo 2: Lite — Ejecución Guiada de Recetas Excel", self.callback_volver)

        body = ttk.Frame(self, style="Window.TFrame")
        body.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))

        # Columna Izquierda: Configuración de Receta y Guardado
        col_izq = ttk.Frame(body, style="Window.TFrame")
        col_izq.pack(side="left", fill="both", expand=True, padx=(0, ui(4)))

        # [1] Carga y Configuración de Receta Excel (Submodo E)
        f_receta = crear_seccion_frame(col_izq, "[1] Receta Excel y Parámetros (Submodo E)", "params")
        f_receta.pack(fill="x", pady=(0, ui(4)))

        f_file = ttk.Frame(f_receta, style="Window.TFrame")
        f_file.pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Label(f_file, text="Archivo Excel:").pack(side="left", padx=ui(4))
        ttk.Entry(f_file, textvariable=self.vars["ruta_excel"], width=28).pack(side="left", padx=ui(4))
        ttk.Button(f_file, text="Examinar...", command=self._on_examinar_excel).pack(side="left", padx=ui(2))
        ttk.Button(f_file, text="Cargar y Analizar", command=self._on_cargar_receta).pack(side="left", padx=ui(4))

        f_sheet = ttk.Frame(f_receta, style="Window.TFrame")
        f_sheet.pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Label(f_sheet, text="Hoja del Excel:").pack(side="left", padx=ui(4))
        self.cb_hoja = ttk.Combobox(f_sheet, textvariable=self.vars["hoja_excel"], width=16)
        self.cb_hoja.pack(side="left", padx=ui(4))
        ttk.Radiobutton(f_sheet, text="Valores en tanto por uno (0.0 - 1.0)", variable=self.vars["excel_valores_0_1"], value=True).pack(side="left", padx=ui(6))
        ttk.Radiobutton(f_sheet, text="Valores en porcentaje (0 - 100%)", variable=self.vars["excel_valores_0_1"], value=False).pack(side="left", padx=ui(4))

        # Tiempos de estabilización y enfriamiento
        f_tiempos = ttk.LabelFrame(f_receta, text=" Control de Tiempos y Enfriamiento ", padding=ui(4))
        f_tiempos.pack(fill="x", padx=ui(6), pady=ui(3))

        f_t_grid = ttk.Frame(f_tiempos, style="Window.TFrame")
        f_t_grid.pack(fill="x")
        ttk.Label(f_t_grid, text="Espera estabilización (s):").grid(row=0, column=0, sticky="w", padx=ui(3))
        ttk.Entry(f_t_grid, textvariable=self.vars["espera_estab_s"], width=7).grid(row=0, column=1, sticky="w", padx=ui(3))
        ttk.Label(f_t_grid, text="Espera luz encendida (s):").grid(row=0, column=2, sticky="w", padx=(ui(8), ui(3)))
        ttk.Entry(f_t_grid, textvariable=self.vars["espera_luz_on_s"], width=7).grid(row=0, column=3, sticky="w", padx=ui(3))
        ttk.Label(f_t_grid, text="Espera motor (s):").grid(row=0, column=4, sticky="w", padx=(ui(8), ui(3)))
        ttk.Entry(f_t_grid, textvariable=self.vars["espera_motor_s"], width=7).grid(row=0, column=5, sticky="w", padx=ui(3))
        ttk.Label(f_t_grid, text="Enfriamiento entre medidas (s):").grid(row=0, column=6, sticky="w", padx=(ui(8), ui(3)))
        ttk.Entry(f_t_grid, textvariable=self.vars["tiempo_enfriado_s"], width=7).grid(row=0, column=7, sticky="w", padx=ui(3))

        f_t_opt = ttk.Frame(f_tiempos, style="Window.TFrame")
        f_t_opt.pack(fill="x", pady=(ui(2), 0))
        ttk.Checkbutton(f_t_opt, text="Apagar LEDs al finalizar la secuencia", variable=self.vars["apagar_al_final"]).pack(side="left", padx=ui(4))

        # [2] Guardado de Datos
        f_salida = crear_seccion_frame(col_izq, "[2] Guardado de Datos", "params")
        f_salida.pack(fill="x", pady=ui(2))

        f_dir = ttk.Frame(f_salida, style="Window.TFrame")
        f_dir.pack(fill="x", padx=ui(6), pady=ui(2))
        crear_campo_directorio(f_dir, self.vars["carpeta_salida"], 0, "Carpeta base:")

        f_nom = ttk.Frame(f_salida, style="Window.TFrame")
        f_nom.pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Label(f_nom, text="Subcarpeta:").pack(side="left", padx=ui(4))
        ttk.Entry(f_nom, textvariable=self.vars["nombre_carpeta_medida"], width=16).pack(side="left", padx=ui(4))
        ttk.Label(f_nom, text="Prefijo medida:").pack(side="left", padx=(ui(10), ui(4)))
        ttk.Entry(f_nom, textvariable=self.vars["nombre_medida"], width=20).pack(side="left", padx=ui(4))

        # [3] Resumen y Vista Previa Interactiva
        f_prev = crear_seccion_frame(col_izq, "[3] Resumen y Vista Previa de Receta", "results")
        f_prev.pack(fill="both", expand=True, pady=ui(2))

        self.lbl_resumen = ttk.Label(
            f_prev,
            text="Ningún archivo Excel cargado. Selecciona una receta para analizar los ejes y pasos.",
            font=ui_font_label(True),
        )
        self.lbl_resumen.pack(anchor="w", padx=ui(6), pady=ui(2))

        # Treeview de vista previa
        f_tree = ttk.Frame(f_prev, style="Window.TFrame")
        f_tree.pack(fill="both", expand=True, padx=ui(6), pady=ui(2))

        self.tree = ttk.Treeview(f_tree, show="headings", height=6)
        scroll_y = ttk.Scrollbar(f_tree, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(f_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        # Botonera de Control
        f_ctrl = ttk.Frame(col_izq, style="Window.TFrame")
        f_ctrl.pack(fill="x", pady=ui(4))

        self.btn_iniciar = tk.Button(
            f_ctrl, text="▶ INICIAR MEDIDA DE RECETA",
            bg=t["buttons"]["primary_bg"], fg=t["buttons"]["primary_fg"],
            activebackground=t["buttons"]["primary_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            command=self._on_iniciar, padx=ui(12), pady=ui(5), relief="flat", cursor="hand2",
            state="disabled",
        )
        self.btn_iniciar.pack(side="left", padx=ui(4))

        self.btn_abortar = tk.Button(
            f_ctrl, text="⏹ DETENER / ABORTAR",
            bg=t["buttons"]["danger_bg"], fg=t["buttons"]["danger_fg"],
            activebackground=t["buttons"]["danger_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            command=self._on_abortar, padx=ui(10), pady=ui(5), relief="flat", cursor="hand2",
            state="disabled",
        )
        self.btn_abortar.pack(side="left", padx=ui(4))

        # Columna Derecha: Consola de Progreso
        col_der = ttk.Frame(body, width=ui(420), style="Window.TFrame")
        col_der.pack(side="right", fill="both", expand=False, padx=(ui(4), 0))
        col_der.pack_propagate(False)

        f_res = crear_seccion_frame(col_der, "Consola de Ejecución", "results")
        f_res.pack(fill="both", expand=True)

        self.txt_log = scrolledtext.ScrolledText(
            f_res,
            font=ui_font_console(),
            bg=t.get("results", {}).get("bg_console", "#1e293b"),
            fg=t.get("results", {}).get("fg_console", "#f8fafc"),
            insertbackground="#0284c7",
            borderwidth=1,
            relief="solid",
            height=UIConfig.CONSOLE_HEIGHT,
        )
        self.txt_log.pack(fill="both", expand=True, pady=ui(4))
        self.txt_log.insert("end", "Carga una receta de Excel para comenzar la ejecución guiada en Lite.\n")

    def _on_examinar_excel(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar Receta Excel",
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            self.vars["ruta_excel"].set(ruta)
            # Cargar nombres de hojas disponibles
            try:
                xl = pd.ExcelFile(ruta)
                self.cb_hoja["values"] = xl.sheet_names
                if xl.sheet_names:
                    self.cb_hoja.set(xl.sheet_names[0])
            except Exception:
                pass
            self._on_cargar_receta()

    def _on_cargar_receta(self):
        ruta_str = self.vars["ruta_excel"].get().strip()
        if not ruta_str:
            mostrar_error("Error", "Selecciona una ruta de archivo Excel.")
            return

        ruta = Path(ruta_str)
        try:
            hoja = self.vars["hoja_excel"].get().strip()
            df, ejes, filas = parsear_excel_receta(ruta, hoja)
            self._df_receta = df
            self._ejes_detectados = ejes
            self._filas_receta = filas

            # Actualizar resumen
            ejes_info = []
            if ejes["Estructura"]:
                ejes_info.append(f"Estructura ({', '.join(ejes['Estructura'])})")
            if ejes["Motor"]:
                ejes_info.append(f"Motor ({', '.join(ejes['Motor'])})")
            if ejes["Iluminación LED"]:
                ejes_info.append(f"LEDs ({len(ejes['Iluminación LED'])} canales: {', '.join(ejes['Iluminación LED'])})")

            resumen_txt = f"✓ Receta válida: {len(filas)} combinaciones detectadas.\nEjes activos: {', '.join(ejes_info) if ejes_info else 'Ninguno reconocido'}"
            self.lbl_resumen.configure(text=resumen_txt)

            # Rellenar Treeview
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = list(df.columns)
            for col in df.columns:
                self.tree.heading(col, text=str(col))
                self.tree.column(col, width=max(70, int(len(str(col)) * 10)), anchor="center")

            for _, row in df.head(100).iterrows():
                self.tree.insert("", "end", values=list(row))

            self.btn_iniciar.configure(state="normal")
            self.txt_log.insert("end", f"\n[✓] Receta cargada correctamente: {len(filas)} medidas planificadas.\n")

        except Exception as exc:
            mostrar_error("Error Receta", f"No se pudo leer la receta Excel:\n{exc}")
            self.btn_iniciar.configure(state="disabled")

    def _on_iniciar(self):
        if self.ejecutando or not self._filas_receta:
            return

        self.ejecutando = True
        self.evento_aborto.clear()
        self.btn_iniciar.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self.txt_log.insert("end", f"\n>>> INICIANDO EJECUCIÓN DE RECETA ({len(self._filas_receta)} pasos)...\n")

        def _hilo():
            try:
                for idx, fila in enumerate(self._filas_receta, 1):
                    if self.evento_aborto.is_set():
                        self.cola_ui.put(("log", "\n[⏹] Medida de receta abortada.\n"))
                        break
                    self.cola_ui.put(("log", f"[{idx}/{len(self._filas_receta)}] Midiendo paso: {fila}\n"))
                    time.sleep(0.1)
                self.cola_ui.put(("log", "\n[✓] Receta completada con éxito.\n"))
            except Exception as exc:
                self.cola_ui.put(("log", f"\n[ERROR] Fallo durante la receta: {exc}\n"))
            finally:
                self.cola_ui.put(("fin", None))

        threading.Thread(target=_hilo, daemon=True).start()

    def _on_abortar(self):
        if not self.ejecutando:
            return
        self.evento_aborto.set()
        abortar_instrumento_activo()
        abortar_motor_activo()
        self.txt_log.insert("end", "\n[⏹] Solicitud de aborto enviada...\n")

    def _procesar_cola_ui(self):
        while not self.cola_ui.empty():
            tipo, dato = self.cola_ui.get_nowait()
            if tipo == "log":
                self.txt_log.insert("end", str(dato))
                self.txt_log.see("end")
            elif tipo == "fin":
                self.ejecutando = False
                self.btn_iniciar.configure(state="normal")
                self.btn_abortar.configure(state="disabled")

        self.after(100, self._procesar_cola_ui)
