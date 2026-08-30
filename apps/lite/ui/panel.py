"""Panel único del modo Lite de TMRW Lab.

Carga un archivo Excel con las combinaciones a medir (estructura, motor, LEDs),
muestra un resumen y vista previa interactiva antes de medir, y ejecuta
la secuencia de forma desatendida con el Keithley 2450.
"""
from __future__ import annotations

import copy
import queue
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk, scrolledtext

import numpy as np
import pandas as pd

from apps.lite.config import get_default_config
from core.instrument import keithley
from core.instrument.motors.motor_lineal import crear_controlador_motor
from core.instrument.solar_simulator import crear_controlador_simulador_solar, normalizar_canal_ossila
from core.instrument.relay_structure import crear_rele_estructura
from core.instrument.registry import (
    registrar_instrumento_activo,
    limpiar_instrumento_activo,
    registrar_motor_activo,
    limpiar_motor_activo,
    registrar_simulador_solar_activo,
    limpiar_simulador_solar_activo,
    abortar_instrumento_activo,
)
from core.measure.run_keithley import run as run_keithley_atomic
from core.plot.plotter import generar_imagen_tk_curvas_iv_pv
from core.ui_kit.scaler import ui, ui_font, ui_font_console, ui_font_label, UIConfig
from core.ui_kit.shared import ScrollableFrame, crear_barra_superior, crear_seccion_frame, mostrar_error, mostrar_info
from core.ui_kit.theme import theme_mgr
from core.utils import preparar_carpeta_medida
from core.exceptions import LimiteCorrienteAlcanzado, MedidaAbortadaPorUsuario, ErrorSMU


# Patrones de columnas por eje
COL_PATTERNS_ESTRUCTURA = {"estructura", "structure", "device", "dispositivo", "rele", "relay"}
COL_PATTERNS_MOTOR = {"motor", "posicion", "position", "pasos", "steps", "posicion_mm", "posicion_pasos", "x", "pos_mm"}
COL_PATTERNS_LED = {
    "390", "450", "515", "cool_white", "cool white", "warm_white", "warm white",
    "600", "630", "660", "730", "850", "950", "potencia", "power", "irradiancia", "irradiance",
    "ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "ch9", "ch10", "ch11",
}


def clasificar_columna(nombre: str) -> str:
    """Clasifica el nombre de una columna de Excel en su eje correspondiente."""
    n = nombre.strip().lower()
    if n in COL_PATTERNS_ESTRUCTURA or any(p in n for p in ["estruc", "device", "disp"]):
        return "Estructura"
    if n in COL_PATTERNS_MOTOR or any(p in n for p in ["paso", "motor", "posic"]):
        return "Motor"
    if n in COL_PATTERNS_LED or any(p in n for p in ["390", "450", "515", "600", "630", "660", "730", "850", "950", "white", "potencia", "irrad"]):
        return "Iluminación LED"
    return "Desconocido / Extra"


def parsear_excel_receta(ruta: Path) -> tuple[pd.DataFrame, dict[str, list[str]], list[dict]]:
    """Lee y clasifica las columnas de un Excel de receta Lite.

    Returns:
        (df_original, ejes_detectados, filas_receta)
    """
    df = pd.read_excel(ruta, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    if df.empty or len(df.columns) == 0:
        raise ValueError("El Excel seleccionado no contiene columnas válidas.")

    ejes = {"Estructura": [], "Motor": [], "Iluminación LED": [], "Desconocido / Extra": []}
    for col in df.columns:
        cat = clasificar_columna(col)
        ejes[cat].append(col)

    filas_receta = []
    for idx, row in df.iterrows():
        item = {"indice": idx + 1, "raw": row.to_dict()}
        # Estructura
        if ejes["Estructura"]:
            item["estructura"] = str(row[ejes["Estructura"][0]]).strip()
        else:
            item["estructura"] = None

        # Motor
        if ejes["Motor"]:
            val_mot = row[ejes["Motor"][0]]
            item["posicion_motor"] = float(val_mot) if pd.notna(val_mot) else 0.0
        else:
            item["posicion_motor"] = None

        # LEDs
        item["leds"] = {}
        for col_led in ejes["Iluminación LED"]:
            val_led = row[col_led]
            if pd.notna(val_led):
                canal = normalizar_canal_ossila(col_led)
                item["leds"][canal] = float(val_led)

        filas_receta.append(item)

    return df, ejes, filas_receta


class LiteFrame(ttk.Frame):
    """Panel principal del modo Lite con carga de Excel y resumen previo."""

    def __init__(self, master, callback_volver=None, **kwargs):
        super().__init__(master, **kwargs)
        self.callback_volver = callback_volver
        self.cfg_base = get_default_config()

        self.evento_aborto = threading.Event()
        self.cola_ui = queue.Queue()
        self.ejecutando = False
        self._df_receta = None
        self._filas_receta = []
        self._ejes_detectados = {}
        self._imagenes_log = []

        self._inicializar_variables()
        self._crear_ui()
        self._procesar_cola_ui()

    def _inicializar_variables(self):
        c = self.cfg_base
        self.vars = {
            "ruta_excel": tk.StringVar(value=""),
            "recurso_visa": tk.StringVar(value=c.get("recurso_visa", "AUTO")),
            "carpeta_salida": tk.StringVar(value=c.get("carpeta_salida", "")),
            "nombre_carpeta_medida": tk.StringVar(value=c.get("nombre_carpeta_medida", "")),
            "nombre_medida": tk.StringVar(value=c.get("nombre_medida", "medida_lite")),
            "i_max_uA": tk.StringVar(value=str(c.get("i_max_uA", 10))),
            "v_ini_dir": tk.StringVar(value=str(c["directa"]["v_inicial_mV"])),
            "v_fin_dir": tk.StringVar(value=str(c["directa"]["v_final_mV"])),
            "paso_dir": tk.StringVar(value=str(c["directa"]["paso_mV"])),
            "v_fin_inv": tk.StringVar(value=str(c["inversa"]["v_final_V"])),
            "paso_inv": tk.StringVar(value=str(c["inversa"]["paso_mV"])),
            "motor_puerto": tk.StringVar(value=c["motor"]["puerto_serie"]),
            "solar_puerto": tk.StringVar(value=c["simulador_solar"]["puerto_serie"]),
        }

    def _crear_ui(self):
        t = theme_mgr.get_current_theme()
        self.configure(style="Window.TFrame")

        # Barra superior
        top = crear_barra_superior(self, "TMRW Lab — Lite (Carga de Excel)", self.callback_volver)
        top.pack(fill="x", padx=ui(10), pady=(ui(8), 0))
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=ui(6))

        # Cuerpo principal dividido en izquierda (configuración y preview) y derecha (consola)
        cuerpo = ttk.Frame(self, style="Window.TFrame")
        cuerpo.pack(fill="both", expand=True, padx=ui(10), pady=ui(4))
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        # ---- PANEL IZQUIERDO ----
        scroll_izq = ScrollableFrame(cuerpo)
        scroll_izq.grid(row=0, column=0, sticky="nsew", padx=(0, ui(6)))
        f_izq = scroll_izq.scroll_content

        # 1. Carga de Excel
        f_excel = crear_seccion_frame(f_izq, "1. Selección de Receta Excel", "params")
        f_excel.pack(fill="x", padx=ui(6), pady=ui(4))

        f_file = ttk.Frame(f_excel, style="Window.TFrame")
        f_file.pack(fill="x", padx=ui(6), pady=ui(4))
        ttk.Label(f_file, text="Archivo Excel:", style="Window.TLabel").pack(side="left", padx=ui(4))
        ttk.Entry(f_file, textvariable=self.vars["ruta_excel"], width=28).pack(side="left", padx=ui(4), fill="x", expand=True)
        ttk.Button(f_file, text="Examinar…", command=self._examinar_excel).pack(side="left", padx=ui(4))

        # 2. Resumen de combinaciones leídas (Requisito Arquitectónico)
        self.f_resumen = crear_seccion_frame(f_izq, "2. Resumen de Combinaciones Leídas", "keithley")
        self.f_resumen.pack(fill="x", padx=ui(6), pady=ui(4))

        self.lbl_filas_detectadas = ttk.Label(
            self.f_resumen,
            text="Carga un archivo Excel para ver el resumen de combinaciones.",
            font=ui_font_label("bold"),
            style="Window.TLabel",
        )
        self.lbl_filas_detectadas.pack(anchor="w", padx=ui(6), pady=ui(2))

        self.lbl_ejes_detectados = ttk.Label(
            self.f_resumen,
            text="",
            foreground="#0284c7",
            font=ui_font_label(),
        )
        self.lbl_ejes_detectados.pack(anchor="w", padx=ui(6), pady=ui(2))

        # Tabla interactiva de vista previa
        self.tree_preview = ttk.Treeview(self.f_resumen, show="headings", height=6)
        self.tree_preview.pack(fill="x", padx=ui(6), pady=ui(6))

        # 3. Hardware y Guardado
        f_hw = crear_seccion_frame(f_izq, "3. Configuración de Hardware", "control")
        f_hw.pack(fill="x", padx=ui(6), pady=ui(4))

        f_hw_grid = ttk.Frame(f_hw, style="Window.TFrame")
        f_hw_grid.pack(fill="x", padx=ui(6), pady=ui(4))

        ttk.Label(f_hw_grid, text="Keithley VISA:", style="Window.TLabel").grid(row=0, column=0, sticky="w", padx=ui(4))
        ttk.Entry(f_hw_grid, textvariable=self.vars["recurso_visa"], width=16).grid(row=0, column=1, sticky="w", padx=ui(4))
        ttk.Label(f_hw_grid, text="I máx (µA):", style="Window.TLabel").grid(row=0, column=2, sticky="w", padx=ui(4))
        ttk.Entry(f_hw_grid, textvariable=self.vars["i_max_uA"], width=8).grid(row=0, column=3, sticky="w", padx=ui(4))

        ttk.Label(f_hw_grid, text="Puerto Motor:", style="Window.TLabel").grid(row=1, column=0, sticky="w", padx=ui(4), pady=ui(3))
        ttk.Entry(f_hw_grid, textvariable=self.vars["motor_puerto"], width=16).grid(row=1, column=1, sticky="w", padx=ui(4), pady=ui(3))
        ttk.Label(f_hw_grid, text="Puerto Solar:", style="Window.TLabel").grid(row=1, column=2, sticky="w", padx=ui(4), pady=ui(3))
        ttk.Entry(f_hw_grid, textvariable=self.vars["solar_puerto"], width=16).grid(row=1, column=3, sticky="w", padx=ui(4), pady=ui(3))

        # 4. Botonera
        f_btns = ttk.Frame(f_izq, style="Window.TFrame")
        f_btns.pack(fill="x", padx=ui(6), pady=ui(8))

        self.btn_start = tk.Button(
            f_btns, text="▶ Iniciar Medida",
            bg=t["buttons"]["primary_bg"], fg=t["buttons"]["primary_fg"],
            activebackground=t["buttons"]["primary_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            command=self._iniciar_medida, padx=ui(14), pady=ui(6), relief="flat", cursor="hand2",
            state="disabled",  # Deshabilitado hasta que se cargue un Excel válido
        )
        self.btn_start.pack(side="left", padx=ui(6))

        self.btn_stop = tk.Button(
            f_btns, text="⏹ Abortar",
            bg=t["buttons"]["danger_bg"], fg=t["buttons"]["danger_fg"],
            activebackground=t["buttons"]["danger_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            command=self._abortar_medida, padx=ui(14), pady=ui(6), relief="flat", cursor="hand2",
        )
        self.btn_stop.pack(side="left", padx=ui(6))

        # ---- PANEL DERECHO (Consola) ----
        f_der = ttk.Frame(cuerpo, style="Window.TFrame")
        f_der.grid(row=0, column=1, sticky="nsew", padx=(ui(6), 0))
        f_der.rowconfigure(1, weight=1)
        f_der.columnconfigure(0, weight=1)

        f_header_cons = ttk.Frame(f_der, style="Window.TFrame")
        f_header_cons.grid(row=0, column=0, sticky="ew", pady=(0, ui(4)))
        ttk.Label(f_header_cons, text="Consola de Ejecución", font=ui_font_label("bold"), style="Window.TLabel").pack(side="left")

        self.badge_estado = tk.Label(
            f_header_cons, text="Esperando Excel",
            bg=t["results"]["badge_ready_bg"], fg=t["results"]["badge_ready_fg"],
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            padx=ui(8), pady=ui(2),
        )
        self.badge_estado.pack(side="right")

        self.txt_consola = scrolledtext.ScrolledText(
            f_der, wrap="word",
            bg=t["results"]["bg_console"], fg=t["results"]["fg_console"],
            insertbackground=t["results"]["fg_console"], font=ui_font_console(),
            relief="flat", borderwidth=0,
        )
        self.txt_consola.grid(row=1, column=0, sticky="nsew", pady=(0, ui(6)))

        self.lbl_grafica = ttk.Label(f_der, text="La vista previa de la curva I-V aparecerá aquí al medir.", anchor="center")
        self.lbl_grafica.grid(row=2, column=0, sticky="ew", pady=(0, ui(4)))

    def _examinar_excel(self):
        ruta = filedialog.askopenfilename(
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")]
        )
        if not ruta:
            return
        self.vars["ruta_excel"].set(ruta)
        self._cargar_y_analizar_excel(Path(ruta))

    def _cargar_y_analizar_excel(self, ruta: Path):
        try:
            df, ejes, filas = parsear_excel_receta(ruta)
            self._df_receta = df
            self._ejes_detectados = ejes
            self._filas_receta = filas

            n_filas = len(filas)
            self.lbl_filas_detectadas.configure(
                text=f"✓ Archivo cargado con éxito: {n_filas} combinaciones detectadas."
            )

            # Construir texto de ejes detectados
            ejes_str_list = []
            for eje, cols in ejes.items():
                if cols:
                    ejes_str_list.append(f"{eje}: {', '.join(cols)}")
            self.lbl_ejes_detectados.configure(
                text="Ejes reconocidos:\n  " + "\n  ".join(ejes_str_list)
            )

            # Actualizar tabla de vista previa
            cols_preview = list(df.columns)
            self.tree_preview["columns"] = cols_preview
            for col in cols_preview:
                self.tree_preview.heading(col, text=col)
                self.tree_preview.column(col, width=max(60, ui(80)), anchor="center")

            self.tree_preview.delete(*self.tree_preview.get_children())
            for _, row in df.head(50).iterrows():
                vals = [str(row[c]) if pd.notna(row[c]) else "" for c in cols_preview]
                self.tree_preview.insert("", "end", values=vals)

            self.btn_start.configure(state="normal")
            self._log(f"✓ Excel cargado: {ruta.name} ({n_filas} filas). Listo para medir.")
            self._actualizar_estado("Listo para medir", "ready")

        except Exception as exc:
            self._df_receta = None
            self._filas_receta = []
            self.btn_start.configure(state="disabled")
            self.lbl_filas_detectadas.configure(text="❌ Error al interpretar el archivo Excel.")
            self.lbl_ejes_detectados.configure(text=str(exc))
            mostrar_error("Error Excel", f"No se pudo cargar la receta:\n{exc}")

    def _log(self, mensaje):
        self.cola_ui.put(("log", str(mensaje)))

    def _actualizar_estado(self, texto, tipo="ready"):
        self.cola_ui.put(("badge", texto, tipo))

    def _actualizar_grafica(self, df, cfg):
        try:
            tk_img = generar_imagen_tk_curvas_iv_pv(df, cfg, ancho_px=480, alto_px=220)
            if tk_img:
                self.cola_ui.put(("grafica", tk_img))
        except Exception:
            pass

    def _procesar_cola_ui(self):
        try:
            while not self.cola_ui.empty():
                item = self.cola_ui.get_nowait()
                tipo = item[0]
                if tipo == "log":
                    msg = item[1]
                    self.txt_consola.insert(tk.END, msg + "\n" if not msg.endswith("\n") else msg)
                    self.txt_consola.see(tk.END)
                elif tipo == "badge":
                    texto, stype = item[1], item[2]
                    t = theme_mgr.get_current_theme()
                    if stype == "running":
                        bg, fg = t["results"]["badge_running_bg"], t["results"]["badge_running_fg"]
                    elif stype == "abort":
                        bg, fg = t["results"]["badge_abort_bg"], t["results"]["badge_abort_fg"]
                    else:
                        bg, fg = t["results"]["badge_ready_bg"], t["results"]["badge_ready_fg"]
                    self.badge_estado.configure(text=texto, bg=bg, fg=fg)
                elif tipo == "grafica":
                    img = item[1]
                    self._imagenes_log.append(img)
                    self.lbl_grafica.configure(image=img, text="")
                elif tipo == "fin":
                    self.ejecutando = False
                    self.btn_start.configure(state="normal")
        except Exception:
            pass
        finally:
            self.after(50, self._procesar_cola_ui)

    def _iniciar_medida(self):
        if self.ejecutando or not self._filas_receta:
            return

        cfg = copy.deepcopy(self.cfg_base)
        v = self.vars
        cfg["recurso_visa"] = v["recurso_visa"].get().strip() or "AUTO"
        cfg["carpeta_salida"] = v["carpeta_salida"].get().strip()
        cfg["nombre_carpeta_medida"] = v["nombre_carpeta_medida"].get().strip()
        cfg["nombre_medida"] = v["nombre_medida"].get().strip()
        cfg["i_max_uA"] = float(v["i_max_uA"].get())
        cfg["i_max_A"] = cfg["i_max_uA"] * 1e-6
        cfg["directa"]["v_inicial_mV"] = float(v["v_ini_dir"].get())
        cfg["directa"]["v_final_mV"] = float(v["v_fin_dir"].get())
        cfg["directa"]["paso_mV"] = float(v["paso_dir"].get())
        cfg["inversa"]["v_final_V"] = float(v["v_fin_inv"].get())
        cfg["inversa"]["paso_mV"] = float(v["paso_inv"].get())
        cfg["motor"]["puerto_serie"] = v["motor_puerto"].get().strip()
        cfg["simulador_solar"]["puerto_serie"] = v["solar_puerto"].get().strip()
        cfg["evento_aborto"] = self.evento_aborto
        cfg["log_callback"] = self._log
        cfg["grafica_callback"] = self._actualizar_grafica

        self.ejecutando = True
        self.evento_aborto.clear()
        self.btn_start.configure(state="disabled")
        self._actualizar_estado("Midiendo...", "running")
        self._log("=" * 60)
        self._log(f"Iniciando secuencia Lite: {len(self._filas_receta)} combinaciones a medir.")

        threading.Thread(target=self._hilo_ejecucion, args=(cfg,), daemon=True).start()

    def _abortar_medida(self):
        if not self.ejecutando:
            return
        self.evento_aborto.set()
        self._log("\n⏹ Aborto solicitado. Deteniendo...")
        self._actualizar_estado("Abortando...", "abort")
        abortar_instrumento_activo()

    def _hilo_ejecucion(self, cfg):
        ctrl_motor = None
        ctrl_solar = None
        ctrl_rele = None
        try:
            preparar_carpeta_medida(cfg)

            tiene_motor = bool(self._ejes_detectados.get("Motor"))
            tiene_led = bool(self._ejes_detectados.get("Iluminación LED"))
            tiene_est = bool(self._ejes_detectados.get("Estructura"))

            if tiene_motor:
                ctrl_motor = crear_controlador_motor(cfg, evento_aborto=self.evento_aborto)
                ctrl_motor.connect()
                registrar_motor_activo(ctrl_motor)
                self._log("✓ Motor conectado.")

            if tiene_led:
                ctrl_solar = crear_controlador_simulador_solar(cfg, evento_aborto=self.evento_aborto)
                ctrl_solar.connect()
                registrar_simulador_solar_activo(ctrl_solar)
                self._log("✓ Simulador solar conectado.")

            if tiene_est:
                ctrl_rele = crear_rele_estructura(cfg, event=self.evento_aborto)
                self._log("✓ Relé de estructura preparado.")

            for paso in self._filas_receta:
                if self.evento_aborto.is_set():
                    raise MedidaAbortadaPorUsuario()

                idx = paso["indice"]
                total = len(self._filas_receta)
                self._log(f"\n--- [Paso {idx}/{total}] ---")

                # Estructura
                if paso.get("estructura"):
                    self._log(f"Estructura: {paso['estructura']}")
                    # ctrl_rele.select(paso["estructura"])

                # Motor
                if paso.get("posicion_motor") is not None and ctrl_motor:
                    pos = int(paso["posicion_motor"])
                    self._log(f"Motor a {pos} pasos...")
                    ctrl_motor.move_absolute_steps(pos)

                # LEDs
                if paso.get("leds") and ctrl_solar:
                    canales = list(paso["leds"].keys())
                    intensidades = list(paso["leds"].values())
                    self._log(f"Ajustando LEDs: {canales} -> {intensidades}...")
                    ctrl_solar.establecer_combinacion_canales(canales, intensidades)
                    time.sleep(3.0)

                # Medida Keithley
                cfg_paso = copy.deepcopy(cfg)
                cfg_paso["nombre_medida"] = f"{cfg['nombre_medida']}_p{idx:03d}"
                t_medida, df_datos, res_fv = run_keithley_atomic(cfg_paso)
                self._actualizar_grafica(df_datos, cfg_paso)

            self._log("\n✓ Secuencia Lite completada con éxito.")
            self._actualizar_estado("Completado", "ready")

        except MedidaAbortadaPorUsuario:
            self._log("\n⏹ Secuencia abortada por el usuario.")
            self._actualizar_estado("Abortado", "abort")
        except ErrorSMU as exc:
            self._log(f"\n❌ Error SMU: {exc}")
            self._actualizar_estado("Error SMU", "abort")
        except Exception as exc:
            self._log(f"\n❌ Error en ejecución: {exc}")
            self._actualizar_estado("Error", "abort")
        finally:
            if ctrl_solar:
                try:
                    ctrl_solar.apagar_sin_error()
                    ctrl_solar.close()
                except Exception:
                    pass
                limpiar_simulador_solar_activo(ctrl_solar)
            if ctrl_motor:
                try:
                    ctrl_motor.close()
                except Exception:
                    pass
                limpiar_motor_activo(ctrl_motor)
            if ctrl_rele:
                try:
                    ctrl_rele.close()
                except Exception:
                    pass
            self.cola_ui.put(("fin",))
