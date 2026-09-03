"""Panel de usuario para el Modo Lite con soporte completo para recetas Excel (Submodo E de iv-maker)."""
from __future__ import annotations

import queue
import copy
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from pathlib import Path
import pandas as pd

from core.instrument.keithley import (
    liberar_control_manual_keithley,
    recuperar_control_automatico_keithley,
)
from core.instrument.registry import (
    abortar_instrumento_activo,
    abortar_motor_activo,
    registrar_simulador_solar_activo,
    limpiar_simulador_solar_activo,
)
from core.instrument.motors.motor_lineal import crear_controlador_motor
from core.instrument.relay_structure import crear_rele_estructura
from core.instrument.solar_simulator import crear_controlador_simulador_solar, configurar_paso_solar
from core.plot.plotter import generar_imagen_tk_curvas_iv_pv
from core.ui_kit.scaler import ui, ui_font, ui_font_console, UIConfig
from core.ui_kit.shared import (
    crear_barra_superior,
    crear_seccion_frame,
    crear_campo_directorio,
    mostrar_error,
    mostrar_info,
)
from core.ui_kit.theme import theme_mgr

from apps.lite.config import get_default_config
from apps.lite.plan_engine import LitePlan, build_lite_plan, construir_nombre_iteracion_lite, insertar_enfriamientos_lite
from core.postprocess.data import guardar_resumen_studio_excel


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
        self.modo_automatico = True
        self._imagenes_log = []
        self._df_receta = None
        self._ejes_detectados = {}
        self._filas_receta = []
        self._plan_lite: LitePlan | None = None
        self._estructuras_keithley: dict[str, dict[str, tk.Variable]] = {}
        self._nombres_estructuras: dict[str, tk.StringVar] = {}
        self._motores_activos = []

        self._inicializar_variables()
        self._crear_ui()
        self._procesar_cola_ui()

    def _inicializar_variables(self):
        c = self.cfg_base
        estructura_cfg = c.get("estructura", {})
        self.vars = {
            # Guardado de Datos (al principio)
            "carpeta_salida": tk.StringVar(value=c.get("carpeta_salida", "")),
            "nombre_carpeta_medida": tk.StringVar(value=c.get("nombre_carpeta_medida", "")),
            "nombre_medida": tk.StringVar(value=c.get("nombre_medida", "medida_lite")),
            # SMU Keithley 2450
            "recurso_visa": tk.StringVar(value=c.get("recurso_visa", "AUTO")),
            "modo_medida": tk.StringVar(value=c.get("modo_medida", "completa")),
            "v_ini_dir": tk.StringVar(value=str(c["directa"]["v_inicial_mV"])),
            "v_fin_dir": tk.StringVar(value=str(c["directa"]["v_final_mV"])),
            "paso_dir": tk.StringVar(value=str(c["directa"]["paso_mV"])),
            "v_fin_inv": tk.StringVar(value=str(c["inversa"]["v_final_V"])),
            "paso_inv": tk.StringVar(value=str(c["inversa"]["paso_mV"])),
            "i_max_uA": tk.StringVar(value=str(c.get("i_max_uA", 10.0))),
            "superficie_um2": tk.StringVar(value="" if c.get("superficie_um2") is None else str(c["superficie_um2"])),
            "irradiancia_mW_cm2": tk.StringVar(value="" if c.get("irradiancia_mW_cm2") is None else str(c["irradiancia_mW_cm2"])),
            "invertir_eje_y": tk.BooleanVar(value=c.get("invertir_eje_y_graficas", True)),
            "medir_tension_real": tk.BooleanVar(value=c.get("medir_tension_real", False)),
            # Receta Excel (Submodo E)
            "ruta_excel": tk.StringVar(value=c.get("ruta_excel_receta", "")),
            "hoja_excel": tk.StringVar(value=c.get("hoja_excel", "")),
            "excel_valores_0_1": tk.BooleanVar(value=c.get("excel_valores_0_1", False)),
            "plantilla_comando": tk.StringVar(value=c.get("plantilla_comando_excel", "<ch{channel}:{intensity}>")),
            "espera_luz_on_s": tk.StringVar(value=str(c.get("espera_luz_encendida_s", 0.0))),
            "espera_conmutacion_s": tk.StringVar(value=str(estructura_cfg.get("espera_conmutacion_s", estructura_cfg.get("espera_estabilizacion_s", 0.5)))),
            "espera_motor_s": tk.StringVar(value=str(c.get("espera_motor_s", 0.0))),
            "tiempo_enfriado_s": tk.StringVar(value=str(c.get("tiempo_enfriado_s", 0.0))),
            "cada_n_medidas_estructura": tk.StringVar(value=str(c.get("cada_n_medidas_estructura", 0))),
            "apagar_al_final": tk.BooleanVar(value=c.get("apagar_al_final", True)),
        }

    def _crear_ui(self):
        t = theme_mgr.get_current_theme()
        crear_barra_superior(self, "Modo 2: Lite — Ejecución Guiada de Recetas Excel", self.callback_volver)

        body = ttk.Frame(self, style="Window.TFrame")
        body.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        # Columna Izquierda: Configuración
        col_izq = ttk.Frame(body, style="Window.TFrame")
        col_izq.grid(row=0, column=0, sticky="nsew", padx=(0, ui(4)))

        # =========================================================================
        # [1] Guardado de Datos (AL PRINCIPIO, igual que en Studio)
        # =========================================================================
        f_salida = crear_seccion_frame(col_izq, "[1] Guardado de Datos", "params")
        f_salida.pack(fill="x", pady=(0, ui(4)))

        f_dir = ttk.Frame(f_salida, style="Params.TFrame")
        f_dir.pack(fill="x", padx=ui(6), pady=ui(2))
        crear_campo_directorio(f_dir, self.vars["carpeta_salida"], 0, "Carpeta base:")

        f_nom = ttk.Frame(f_salida, style="Params.TFrame")
        f_nom.pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Label(f_nom, text="Subcarpeta:", style="Params.TLabel").pack(side="left", padx=ui(4))
        ttk.Entry(f_nom, textvariable=self.vars["nombre_carpeta_medida"], width=16).pack(side="left", padx=ui(4))
        ttk.Label(f_nom, text="Prefijo medida:", style="Params.TLabel").pack(side="left", padx=(ui(10), ui(4)))
        ttk.Entry(f_nom, textvariable=self.vars["nombre_medida"], width=20).pack(side="left", padx=ui(4))

        # [2] Control de Medición
        f_ctrl_sec = crear_seccion_frame(col_izq, "[2] Control de Medición", "control")
        f_ctrl_sec.pack(fill="x", pady=ui(4))
        f_ctrl = ttk.Frame(f_ctrl_sec, style="Control.TFrame")
        f_ctrl.pack(fill="x", padx=ui(4), pady=ui(4))
        self.btn_iniciar = ttk.Button(f_ctrl, text="▶ INICIAR MEDIDA DE RECETA", style="Primary.TButton", command=self._on_iniciar, state="disabled")
        self.btn_iniciar.pack(side="left", padx=ui(4))
        self.btn_abortar = ttk.Button(f_ctrl, text="⏹ DETENER / ABORTAR", style="Danger.TButton", command=self._on_abortar, state="disabled")
        self.btn_abortar.pack(side="left", padx=ui(4))
        self.btn_manual = ttk.Button(f_ctrl, text="⚙ Liberar Keithley", style="Tool.TButton", command=self._on_modo_manual)
        self.btn_manual.pack(side="left", padx=ui(4))
        self.btn_test_reles = ttk.Button(
            f_ctrl, text="🧪 TEST RELÉS / ESTRUCTURAS", style="Tool.TButton",
            command=self._on_prueba_reles,
        )
        self.btn_test_reles.pack(side="left", padx=ui(4))
        self.btn_test_solar = ttk.Button(
            f_ctrl, text="☀ TEST SIMULADOR SOLAR", style="Tool.TButton",
            command=self._on_prueba_solar,
        )
        self.btn_test_solar.pack(side="left", padx=ui(4))

        # [3] Receta Excel, resumen y tiempos aplicables
        f_receta = crear_seccion_frame(col_izq, "[3] Receta Excel y Parámetros (Submodo E)", "params")
        f_receta.pack(fill="x", pady=(0, ui(4)))

        f_file = ttk.Frame(f_receta, style="Params.TFrame")
        f_file.pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Label(f_file, text="Archivo Excel:", style="Params.TLabel").pack(side="left", padx=ui(4))
        ttk.Entry(f_file, textvariable=self.vars["ruta_excel"], width=28).pack(side="left", padx=ui(4))
        ttk.Button(f_file, text="Buscar...", command=self._on_examinar_excel, style="Tool.TButton").pack(side="left", padx=ui(2))
        ttk.Button(f_file, text="Cargar y Analizar", command=self._on_cargar_receta, style="Tool.TButton").pack(side="left", padx=ui(4))

        f_sheet = ttk.Frame(f_receta, style="Params.TFrame")
        f_sheet.pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Label(f_sheet, text="Hoja del Excel:", style="Params.TLabel").pack(side="left", padx=ui(4))
        self.cb_hoja = ttk.Combobox(f_sheet, textvariable=self.vars["hoja_excel"], width=16)
        self.cb_hoja.pack(side="left", padx=ui(4))
        ttk.Radiobutton(f_sheet, text="Valores en tanto por uno (0.0 - 1.0)", variable=self.vars["excel_valores_0_1"], value=True, style="Params.TRadiobutton").pack(side="left", padx=ui(6))
        ttk.Radiobutton(f_sheet, text="Valores en porcentaje (0 - 100%)", variable=self.vars["excel_valores_0_1"], value=False, style="Params.TRadiobutton").pack(side="left", padx=ui(4))

        self.lbl_resumen = ttk.Label(f_receta, text="Ningún archivo Excel cargado.", style="Results.TLabel")
        self.lbl_resumen.pack(anchor="w", padx=ui(6), pady=ui(4))
        self.f_tiempos = ttk.LabelFrame(f_receta, text=" Control de Tiempos Aplicable ", padding=ui(4), style="Params.TLabelframe")
        self.f_tiempos.pack(fill="x", padx=ui(6), pady=ui(3))
        self._render_tiempos(frozenset())

        # [4] Configuraciones Keithley por estructura detectada
        self.f_keithley = crear_seccion_frame(col_izq, "[4] Configuraciones del Keithley", "keithley")
        self.f_keithley.pack(fill="both", expand=True, pady=ui(2))
        self.btn_copiar_keithley = ttk.Button(
            self.f_keithley,
            text="Copiar configuración del primer Keithley a todos",
            command=self._copiar_configuracion_keithley,
            style="Tool.TButton",
        )
        self.btn_copiar_keithley.pack(anchor="w", padx=ui(6), pady=(0, ui(4)))
        self.canvas_keithley = tk.Canvas(self.f_keithley, height=250, bg="#f8fafc", highlightthickness=0)
        self.scrollbar_keithley = ttk.Scrollbar(self.f_keithley, orient="vertical", command=self.canvas_keithley.yview)
        self.canvas_keithley.configure(yscrollcommand=self.scrollbar_keithley.set)
        self.scrollbar_keithley.pack(side="right", fill="y")
        self.canvas_keithley.pack(side="left", fill="both", expand=True)
        self.keithley_frame = ttk.Frame(self.canvas_keithley, style="Keithley.TFrame")
        self.keithley_window = self.canvas_keithley.create_window((0, 0), window=self.keithley_frame, anchor="nw")
        self.keithley_frame.bind("<Configure>", lambda event: self.canvas_keithley.configure(scrollregion=self.canvas_keithley.bbox("all")))
        self.canvas_keithley.bind("<Configure>", lambda event: self.canvas_keithley.itemconfigure(self.keithley_window, width=event.width))
        self._render_configuraciones_keithley(())

        # Columna Derecha: Consola de Progreso
        col_der = ttk.Frame(body, style="Window.TFrame")
        col_der.grid(row=0, column=1, sticky="nsew", padx=(ui(4), 0))

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

    def _render_tiempos(self, active_axes):
        for child in self.f_tiempos.winfo_children():
            child.destroy()
        fields = []
        if "led" in active_axes:
            fields.extend([
                ("Espera luz encendida (s):", "espera_luz_on_s", "Tiempo con luz activa antes del disparo del Keithley."),
            ])
        if any(axis.startswith("motor_") for axis in active_axes):
            fields.append(("Espera motor (s):", "espera_motor_s", "Tiempo de asentamiento después de mover el motor."))
        if "estructura" in active_axes:
            fields.append(("Espera conmutación (s):", "espera_conmutacion_s", "Tiempo después de cambiar la estructura."))
        if "estructura" in active_axes and len(self._plan_lite.steps) > 1 if self._plan_lite else False:
            fields.extend([
                ("Medidas de estructuras antes de enfriar:", "cada_n_medidas_estructura", "Número de medidas de estructuras antes de apagar los LEDs."),
                ("Enfriamiento entre medidas (s):", "tiempo_enfriado_s", "Tiempo con los LEDs apagados entre medidas."),
            ])
        if not fields:
            ttk.Label(self.f_tiempos, text="Carga una receta para mostrar los tiempos necesarios.", style="Params.TLabel").pack(anchor="w")
            return
        grid = ttk.Frame(self.f_tiempos, style="Params.TFrame")
        grid.pack(fill="x")
        for index, (label, variable, explanation) in enumerate(fields):
            field = ttk.Frame(grid, style="Params.TFrame")
            field.grid(row=0, column=index, sticky="nw", padx=ui(4), pady=ui(2))
            ttk.Label(field, text=label, style="Params.TLabel").pack(anchor="w")
            ttk.Entry(field, textvariable=self.vars[variable], width=7).pack(anchor="w", pady=(ui(1), 0))
            ttk.Label(
                field,
                text=explanation,
                wraplength=ui(150),
                foreground=theme_mgr.get_current_theme().get("fg_muted", "#475569"),
                style="Params.TLabel",
            ).pack(anchor="w", pady=(ui(2), 0))
        ttk.Label(
            self.f_tiempos,
            text="Los tiempos se aplican globalmente a las medidas del Excel y solo se muestran para ejes activos.",
            foreground=theme_mgr.get_current_theme().get("fg_muted", "#475569"),
            style="Params.TLabel",
        ).pack(anchor="w", padx=ui(2), pady=(ui(3), 0))
        ttk.Checkbutton(
            self.f_tiempos,
            text="Apagar LEDs al finalizar la secuencia",
            variable=self.vars["apagar_al_final"],
            style="Params.TCheckbutton",
        ).pack(anchor="w", padx=ui(4), pady=(ui(3), 0))

    def _render_configuraciones_keithley(self, structures):
        for child in self.keithley_frame.winfo_children():
            child.destroy()
        structures = tuple(structures) or ("Medida única",)
        common = ttk.LabelFrame(self.keithley_frame, text=" Barrido I-V común ", padding=ui(6), style="Params.TLabelframe")
        common.pack(fill="x", padx=ui(4), pady=ui(4))
        common_fields = [
            ("V ini directa (mV):", "v_ini_dir"), ("V fin directa (mV):", "v_fin_dir"),
            ("Paso directa (mV):", "paso_dir"), ("V fin inversa (V):", "v_fin_inv"),
            ("Paso inversa (mV):", "paso_inv"), ("Superficie (um2):", "superficie_um2"),
            ("Irradiancia (mW/cm2):", "irradiancia_mW_cm2"),
        ]
        for index, (label, variable) in enumerate(common_fields):
            row, column = divmod(index, 4)
            ttk.Label(common, text=label, style="Keithley.TLabel").grid(row=row, column=column * 2, sticky="w", padx=ui(3), pady=ui(2))
            ttk.Entry(common, textvariable=self.vars[variable], width=10).grid(row=row, column=column * 2 + 1, sticky="w", padx=ui(3), pady=ui(2))
        ttk.Checkbutton(common, text="Sense 4 hilos", variable=self.vars["medir_tension_real"], style="Keithley.TCheckbutton").grid(row=2, column=0, sticky="w", padx=ui(3), pady=ui(2))
        for structure in structures:
            nombre_var = self._nombres_estructuras.setdefault(
                structure, tk.StringVar(value=structure)
            )
            values = self._estructuras_keithley.setdefault(structure, {
                "recurso_visa": tk.StringVar(value=self.vars["recurso_visa"].get()),
                "modo_medida": tk.StringVar(value=self.vars["modo_medida"].get()),
                "i_max_uA": tk.StringVar(value=self.vars["i_max_uA"].get()),
                "v_inicial_mV": tk.StringVar(value=self.vars["v_ini_dir"].get()),
                "v_final_mV": tk.StringVar(value=self.vars["v_fin_dir"].get()),
                "paso_mV": tk.StringVar(value=self.vars["paso_dir"].get()),
                "v_final_inversa_V": tk.StringVar(value=self.vars["v_fin_inv"].get()),
                "paso_inversa_mV": tk.StringVar(value=self.vars["paso_inv"].get()),
                "invertir_eje_y": tk.BooleanVar(value=self.vars["invertir_eje_y"].get()),
            })
            block = ttk.LabelFrame(self.keithley_frame, text=f" {structure} ", padding=ui(6), style="Params.TLabelframe")
            block.pack(fill="x", padx=ui(4), pady=ui(4))
            row = ttk.Frame(block, style="Keithley.TFrame")
            row.pack(fill="x")
            ttk.Label(row, text="Nombre estructura:", style="Keithley.TLabel").pack(side="left")
            ttk.Entry(row, textvariable=nombre_var, width=16).pack(side="left", padx=(ui(3), ui(10)))
            ttk.Label(row, text="Recurso VISA:", style="Keithley.TLabel").pack(side="left")
            ttk.Entry(row, textvariable=values["recurso_visa"], width=16).pack(side="left", padx=(ui(3), ui(10)))
            ttk.Label(row, text="Modo:", style="Keithley.TLabel").pack(side="left")
            ttk.Combobox(row, textvariable=values["modo_medida"], values=["completa", "directa", "inversa"], state="readonly", width=11).pack(side="left", padx=(ui(3), ui(10)))
            ttk.Label(row, text="I máx (µA):", style="Keithley.TLabel").pack(side="left")
            ttk.Entry(row, textvariable=values["i_max_uA"], width=8).pack(side="left", padx=(ui(3), ui(8)))
            ttk.Checkbutton(row, text="Invertir eje Y", variable=values["invertir_eje_y"], style="Keithley.TCheckbutton").pack(side="left")
            detail = ttk.Frame(block, style="Keithley.TFrame")
            detail.pack(fill="x", pady=(ui(3), 0))
            for label, key in (("V ini dir (mV)", "v_inicial_mV"), ("V fin dir (mV)", "v_final_mV"), ("Paso dir (mV)", "paso_mV"), ("V fin inv (V)", "v_final_inversa_V"), ("Paso inv (mV)", "paso_inversa_mV")):
                ttk.Label(detail, text=f"{label}:", style="Keithley.TLabel").pack(side="left", padx=(ui(3), ui(2)))
                ttk.Entry(detail, textvariable=values[key], width=8).pack(side="left", padx=(0, ui(6)))
        self.canvas_keithley.configure(scrollregion=self.canvas_keithley.bbox("all"))

    def _copiar_configuracion_keithley(self):
        estructuras = tuple(self._estructuras_keithley)
        if len(estructuras) < 2:
            return
        origen = self._estructuras_keithley[estructuras[0]]
        for estructura in estructuras[1:]:
            destino = self._estructuras_keithley[estructura]
            for clave, variable in origen.items():
                destino[clave].set(variable.get())

    def _recoger_config(self) -> dict:
        v = self.vars
        cfg = get_default_config()

        cfg["carpeta_salida"] = v["carpeta_salida"].get().strip()
        cfg["nombre_carpeta_medida"] = v["nombre_carpeta_medida"].get().strip()
        cfg["nombre_medida"] = v["nombre_medida"].get().strip() or "medida_lite"

        cfg["recurso_visa"] = v["recurso_visa"].get().strip()
        cfg["modo_medida"] = v["modo_medida"].get().strip()
        cfg["directa"]["v_inicial_mV"] = float(v["v_ini_dir"].get() or 0.0)
        cfg["directa"]["v_final_mV"] = float(v["v_fin_dir"].get() or 550.0)
        cfg["directa"]["paso_mV"] = float(v["paso_dir"].get() or 10.0)
        cfg["inversa"]["v_final_V"] = float(v["v_fin_inv"].get() or -11.0)
        cfg["inversa"]["paso_mV"] = float(v["paso_inv"].get() or 100.0)
        cfg["i_max_uA"] = float(v["i_max_uA"].get() or 10.0)
        cfg["superficie_um2"] = float(v["superficie_um2"].get()) if v["superficie_um2"].get() else None
        cfg["irradiancia_mW_cm2"] = float(v["irradiancia_mW_cm2"].get()) if v["irradiancia_mW_cm2"].get() else None
        cfg["invertir_eje_y_graficas"] = v["invertir_eje_y"].get()
        cfg["medir_tension_real"] = v["medir_tension_real"].get()

        cfg["ruta_excel_receta"] = v["ruta_excel"].get().strip()
        cfg["hoja_excel"] = v["hoja_excel"].get().strip()
        cfg["excel_valores_0_1"] = v["excel_valores_0_1"].get()
        cfg["plantilla_comando_excel"] = v["plantilla_comando"].get().strip()
        cfg["espera_luz_encendida_s"] = float(v["espera_luz_on_s"].get() or 0.0)
        cfg["espera_motor_s"] = float(v["espera_motor_s"].get() or 0.0)
        cfg["tiempo_enfriado_s"] = float(v["tiempo_enfriado_s"].get() or 0.0)
        cfg["cada_n_medidas_estructura"] = int(v["cada_n_medidas_estructura"].get() or 0)
        cfg["apagar_al_final"] = v["apagar_al_final"].get()

        cfg["barrido_motor_activo"] = any(axis.startswith("motor_") for axis in (self._plan_lite.active_axes if self._plan_lite else ()))
        cfg["simulador_solar_activo"] = "led" in (self._plan_lite.active_axes if self._plan_lite else ())
        cfg["eje_estructura_activo"] = "estructura" in (self._plan_lite.active_axes if self._plan_lite else ())
        cfg["estructura"]["estructuras"] = [
            self._nombres_estructuras.get(estructura, tk.StringVar(value=estructura)).get().strip() or estructura
            for estructura in (self._plan_lite.structures if self._plan_lite else [])
        ]
        cfg["estructura"]["puerto_serie"] = str(cfg.get("estructura", {}).get("puerto_serie", "COM5"))
        cfg["estructura"]["baudrate"] = int(cfg.get("estructura", {}).get("baudrate", 9600))
        cfg["estructura"]["espera_conmutacion_s"] = float(self.vars["espera_conmutacion_s"].get() or 0.0)
        cfg["estructura"]["keithley_por_estructura"] = {
            (self._nombres_estructuras.get(name, tk.StringVar(value=name)).get().strip() or name): {
                "recurso_visa": values["recurso_visa"].get().strip(),
                "modo_medida": values["modo_medida"].get().strip(),
                "i_max_uA": float(values["i_max_uA"].get() or 10.0),
                "v_inicial_mV": float(values["v_inicial_mV"].get() or 0.0),
                "v_final_mV": float(values["v_final_mV"].get() or 550.0),
                "paso_mV": float(values["paso_mV"].get() or 10.0),
                "v_final_inversa_V": float(values["v_final_inversa_V"].get() or -11.0),
                "paso_inversa_mV": float(values["paso_inversa_mV"].get() or 100.0),
                "invertir_eje_y": bool(values["invertir_eje_y"].get()),
            }
            for name, values in self._estructuras_keithley.items()
        }
        return cfg

    def _configurar_medida_lite(self, cfg, step):
        local = copy.deepcopy(cfg)
        local["directa"] = dict(cfg.get("directa", {}))
        local["inversa"] = dict(cfg.get("inversa", {}))
        estructura = step.get("estructura")
        nombre_estructura = self._nombres_estructuras.get(
            estructura, tk.StringVar(value=estructura or "")
        ).get().strip() or estructura
        local["estructura"] = dict(cfg.get("estructura", {}), estructuras=[nombre_estructura] if nombre_estructura else [])
        estructura_cfg = cfg.get("estructura", {}).get("keithley_por_estructura", {}).get(estructura, {})
        if nombre_estructura:
            estructura_cfg = cfg.get("estructura", {}).get("keithley_por_estructura", {}).get(nombre_estructura, estructura_cfg)
        if not estructura_cfg and estructura is None:
            estructura_cfg = cfg.get("estructura", {}).get("keithley_por_estructura", {}).get("Medida única", {})
        local["modo_medida"] = estructura_cfg.get("modo_medida", cfg.get("modo_medida", "completa"))
        local["i_max_uA"] = float(estructura_cfg.get("i_max_uA", cfg.get("i_max_uA", 10.0)))
        local["i_max_A"] = local["i_max_uA"] * 1e-6
        local["recurso_visa"] = estructura_cfg.get("recurso_visa", cfg.get("recurso_visa", "AUTO"))
        local["invertir_eje_y_graficas"] = bool(estructura_cfg.get("invertir_eje_y", cfg.get("invertir_eje_y_graficas", True)))
        local["directa"].update({
            "v_inicial_mV": float(estructura_cfg.get("v_inicial_mV", local["directa"].get("v_inicial_mV", 0.0))),
            "v_final_mV": float(estructura_cfg.get("v_final_mV", local["directa"].get("v_final_mV", 550.0))),
            "paso_mV": float(estructura_cfg.get("paso_mV", local["directa"].get("paso_mV", 10.0))),
        })
        local["inversa"].update({
            "v_final_V": float(estructura_cfg.get("v_final_inversa_V", local["inversa"].get("v_final_V", -11.0))),
            "paso_mV": float(estructura_cfg.get("paso_inversa_mV", local["inversa"].get("paso_mV", 100.0))),
        })
        step = dict(step)
        step["estructura"] = nombre_estructura
        step["resolucion_lineal_mm_paso"] = float(
            cfg.get("motor", {}).get("resolucion_mm_paso", 0.00128)
        )
        local["nombre_medida"] = construir_nombre_iteracion_lite(
            cfg.get("nombre_medida", "medida_lite"), step
        )
        local["log_callback"] = lambda message: self.cola_ui.put(("log", str(message)))
        local["grafica_callback"] = lambda data, graph_cfg: self.cola_ui.put(("grafica", (data, graph_cfg)))
        return local

    def _on_examinar_excel(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar Receta Excel",
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")],
        )
        if ruta:
            self.vars["ruta_excel"].set(ruta)
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
            plan = build_lite_plan(df, self.vars["excel_valores_0_1"].get())
            self._df_receta = df
            self._ejes_detectados = ejes
            self._filas_receta = filas
            self._plan_lite = plan
            ejes_activos = ", ".join(sorted(plan.active_axes))
            self.lbl_resumen.configure(
                text=(
                    f"✓ Receta válida: {len(filas)} filas, {plan.measure_count} medidas.\n"
                    f"Ejes activos: {ejes_activos or 'ninguno'} | "
                    f"Estructuras: {', '.join(plan.structures) or 'ninguna'}"
                )
            )
            self._render_tiempos(plan.active_axes)
            self._render_configuraciones_keithley(plan.structures or ("Medida única",))

            self.btn_iniciar.configure(state="normal")
            self.txt_log.insert("end", f"\n[✓] Receta cargada: {plan.measure_count} medidas planificadas.\n")

        except Exception as exc:
            mostrar_error("Error Receta", f"No se pudo leer la receta Excel:\n{exc}")
            self._plan_lite = None
            self.btn_iniciar.configure(state="disabled")

    def _on_iniciar(self):
        if not self._comprobar_modo_automatico() or self.ejecutando or not self._plan_lite:
            return

        cfg = self._recoger_config()
        cfg["log_callback"] = lambda mensaje: self.cola_ui.put(("log", str(mensaje)))
        cfg["grafica_callback"] = lambda datos, grafica_cfg: self.cola_ui.put(
            ("grafica", (datos, grafica_cfg))
        )
        self.ejecutando = True
        self.evento_aborto.clear()
        self.btn_iniciar.configure(state="disabled")
        self.btn_test_reles.configure(state="disabled")
        self.btn_test_solar.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        plan = insertar_enfriamientos_lite(
            self._plan_lite,
            cfg["cada_n_medidas_estructura"],
            cfg["tiempo_enfriado_s"],
        )
        self.txt_log.insert("end", f"\n>>> INICIANDO EJECUCIÓN DE RECETA ({plan.measure_count} medidas)...\n")
        threading.Thread(target=self._hilo_receta, args=(cfg, plan), daemon=True).start()

    def _on_prueba_solar(self):
        if not self._comprobar_modo_automatico() or self.ejecutando:
            return
        cfg = self._recoger_config()
        self.ejecutando = True
        self.evento_aborto.clear()
        for button in (self.btn_iniciar, self.btn_test_reles, self.btn_test_solar):
            button.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self.txt_log.insert("end", "\n>>> Probando simulador solar: potencia y 11 LEDs...\n")
        threading.Thread(target=self._hilo_prueba_solar, args=(cfg,), daemon=True).start()

    def _hilo_prueba_solar(self, cfg):
        simulador = None
        try:
            simulador = crear_controlador_simulador_solar(
                {**cfg, "simulador_solar_activo": True}, self.evento_aborto
            )
            simulador.connect()
            registrar_simulador_solar_activo(simulador)
            self.cola_ui.put(("log", "[TEST] Encendiendo potencia: 100 mW/cm2\n"))
            simulador.encender_y_verificar(100.0)
            self._esperar_abortable(1.0)
            canales = ["390", "450", "515", "cool_white", "warm_white", "600", "630", "660", "730", "850", "950"]
            for index, canal in enumerate(canales, 1):
                self._esperar_abortable(0.2)
                simulador.apagar()
                simulador.enviar_comando_personalizado(
                    cfg.get("plantilla_comando_excel", "<ch{channel}:{intensity}>"),
                    channel=canal,
                    intensity=50,
                )
                self.cola_ui.put(("log", f"[TEST] LED {index}/{len(canales)}: {canal} al 50%\n"))
            simulador.apagar()
            self.cola_ui.put(("log", "[OK] Prueba del simulador solar completada.\n"))
        except Exception as exc:
            self.cola_ui.put(("log", f"[ERROR] Prueba del simulador solar: {exc}\n"))
        finally:
            if simulador is not None:
                limpiar_simulador_solar_activo(simulador)
                try:
                    simulador.close()
                except Exception:
                    pass
            self.cola_ui.put(("fin", False))

    def _on_prueba_reles(self):
        if not self._comprobar_modo_automatico() or self.ejecutando:
            return
        cfg = self._recoger_config()
        self.ejecutando = True
        self.evento_aborto.clear()
        for button in (self.btn_iniciar, self.btn_test_reles, self.btn_test_solar):
            button.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self.txt_log.insert("end", "\n>>> Probando relés y estructuras...\n")
        threading.Thread(target=self._hilo_prueba_reles, args=(cfg,), daemon=True).start()

    def _hilo_prueba_reles(self, cfg):
        rele = None
        try:
            estructuras = cfg.get("estructura", {}).get("estructuras") or ["Estructura 1", "Estructura 2"]
            rele = crear_rele_estructura(cfg, self.evento_aborto)
            rele.connect()
            for index, estructura in enumerate(estructuras, 1):
                if self.evento_aborto.is_set():
                    raise RuntimeError("Prueba abortada por el usuario.")
                letra = rele.select(estructura)
                self.cola_ui.put(("log", f"[TEST] Estructura {index}/{len(estructuras)}: {estructura} ({letra})\n"))
            self.cola_ui.put(("log", "[OK] Prueba de relés completada.\n"))
        except Exception as exc:
            self.cola_ui.put(("log", f"[ERROR] Prueba de relés: {exc}\n"))
        finally:
            if rele is not None:
                try:
                    rele.close()
                except Exception:
                    pass
            self.cola_ui.put(("fin", False))

    def _esperar_abortable(self, segundos):
        limite = time.monotonic() + max(0.0, float(segundos))
        while time.monotonic() < limite:
            if self.evento_aborto.is_set():
                raise RuntimeError("Secuencia abortada por el usuario.")
            time.sleep(min(0.05, limite - time.monotonic()))

    def _hilo_receta(self, cfg, plan):
        rele = None
        simulador = None
        motores = {}
        completada = False
        filas_resumen = []
        try:
            if cfg.get("barrido_motor_activo"):
                ejes_motor = set()
                for step in plan.steps:
                    ejes_motor.update(step["motores"])
                for eje in ejes_motor:
                    motor_cfg = dict(cfg.get("motor", {}))
                    motor_cfg.update(cfg.get("motor", {}).get(eje, {}))
                    controlador = crear_controlador_motor({"motor": motor_cfg}, self.evento_aborto)
                    controlador.connect()
                    motores[eje] = controlador
                self._motores_activos = list(motores.values())
            if cfg.get("simulador_solar_activo"):
                simulador = crear_controlador_simulador_solar(cfg, self.evento_aborto)
                registrar_simulador_solar_activo(simulador)
                simulador.connect()
            if cfg.get("eje_estructura_activo"):
                rele = crear_rele_estructura(cfg, self.evento_aborto)
                rele.connect()

            from core.measure.run_keithley import run as run_keithley
            for index, step in enumerate(plan.steps, 1):
                if self.evento_aborto.is_set():
                    raise RuntimeError("Secuencia abortada por el usuario.")
                if step.get("tipo") == "enfriar":
                    if simulador:
                        simulador.apagar()
                    self.cola_ui.put(("log", f"[{index}/{len(plan.steps)}] Enfriando durante {step['duracion_s']} s\n"))
                    self._esperar_abortable(step["duracion_s"])
                    continue
                self.cola_ui.put(("log", f"[{index}/{plan.measure_count}] Fila Excel {step['fila_excel']}: preparando medida\n"))
                nombre_estructura = self._nombres_estructuras.get(
                    step.get("estructura"), tk.StringVar(value=step.get("estructura") or "")
                ).get().strip() or step.get("estructura")
                for eje, posicion in step["motores"].items():
                    controlador = motores.get(eje)
                    if controlador is not None:
                        controlador.move_absolute_steps(posicion["pasos"])
                    self._esperar_abortable(cfg.get("espera_motor_s", 0.0))
                if simulador:
                    configurar_paso_solar(
                        simulador,
                        "combinacion",
                        {
                            "canales": list(step["leds"]),
                            "intensidades": list(step["leds"].values()),
                        },
                        cfg.get("plantilla_comando_excel", "<ch{channel}:{intensity}>"),
                    )
                    self._esperar_abortable(cfg.get("espera_luz_encendida_s", 0.0))
                if rele and step.get("estructura"):
                    rele.select(nombre_estructura)
                    self._esperar_abortable(cfg.get("estructura", {}).get("espera_conmutacion_s", 0.0))
                cfg_medida = self._configurar_medida_lite(cfg, step)
                resultado = run_keithley(cfg_medida)
                fila = {
                    "Iteración": index,
                    "Nombre iteración": cfg_medida["nombre_medida"],
                    "Estructura": nombre_estructura if step.get("estructura") else None,
                    "Estado": resultado.get("estado_medida"),
                    "Puntos": resultado.get("puntos_medidos"),
                }
                for motor, posicion in step["motores"].items():
                    if motor == "motor_lineal":
                        fila["Motor lineal (mm)"] = posicion["valor"] * float(cfg.get("motor", {}).get("resolucion_mm_paso", 0.00128))
                    elif motor == "motor_inclinacion":
                        fila["Inclinación (deg)"] = posicion["valor"]
                    elif motor == "motor_rotacion":
                        fila["Rotación (deg)"] = posicion["valor"]
                for channel, intensity in step["leds"].items():
                    fila[f"LED {channel} (%)"] = intensity
                rfv = resultado.get("resultados_fv") or {}
                for key, value in (("Voc_V", "Voc (V)"), ("Isc_A", "Isc (A)"), ("Pmax_W", "Pmax (W)"), ("Vmp_V", "Vmp (V)"), ("Imp_A", "Imp (A)"), ("Jsc_mA_cm2", "Jsc (mA/cm^2)"), ("Densidad_potencia_mW_cm2", "Densidad de potencia (mW/cm^2)"), ("Eff", "Eff (%)")):
                    if key in rfv:
                        fila[key] = rfv[key]
                if "FF" in rfv:
                    fila["FF (%)"] = float(rfv["FF"]) * 100.0
                filas_resumen.append(fila)
            if filas_resumen:
                ruta_resumen = guardar_resumen_studio_excel(cfg, filas_resumen)
                self.cola_ui.put(("log", f"Resumen combinado guardado en: {ruta_resumen}\n"))
            completada = True
            self.cola_ui.put(("log", "\n[✓] Receta completada con éxito.\n"))
        except Exception as exc:
            self.cola_ui.put(("log", f"\n[{'⏹' if self.evento_aborto.is_set() else 'ERROR'}] Secuencia finalizada: {exc}\n"))
        finally:
            if simulador is not None:
                limpiar_simulador_solar_activo(simulador)
                try:
                    simulador.close(apagar=cfg.get("apagar_al_final", True))
                except Exception:
                    pass
            if rele is not None:
                try:
                    rele.close()
                except Exception:
                    pass
            for motor in motores.values():
                try:
                    motor.close()
                except Exception:
                    pass
            self._motores_activos = []
            self.cola_ui.put(("fin", completada))

    def _on_abortar(self):
        if not self.ejecutando:
            return
        self.evento_aborto.set()
        for motor in self._motores_activos:
            try:
                motor.stop()
            except Exception:
                pass
        abortar_instrumento_activo()
        abortar_motor_activo()
        self.txt_log.insert("end", "\n[⏹] Solicitud de aborto enviada...\n")

    def _on_modo_manual(self):
        if self.ejecutando:
            self.txt_log.insert("end", "\n[AVISO] Espera a que termine la operación actual.\n")
            return
        self.ejecutando = True
        self.btn_manual.configure(state="disabled")
        recurso = self.vars["recurso_visa"].get().strip()
        recuperar = not self.modo_automatico
        accion = "Recuperando control automático" if recuperar else "Liberando Keithley para control manual"
        self.txt_log.insert("end", f"\n>>> {accion}...\n")
        threading.Thread(
            target=self._hilo_cambiar_modo,
            args=(recurso, recuperar),
            daemon=True,
        ).start()

    def _hilo_cambiar_modo(self, recurso, recuperar):
        try:
            if recuperar:
                recuperar_control_automatico_keithley(recurso)
            else:
                liberar_control_manual_keithley(recurso)
            self.cola_ui.put(("modo_manual", "automatico" if recuperar else "manual"))
        except Exception as exc:
            self.cola_ui.put(("error_modo_manual", str(exc)))

    def _comprobar_modo_automatico(self):
        if self.modo_automatico:
            return True
        mensaje = "No se puede ejecutar la receta mientras el Keithley está en modo manual. Recupera primero el modo automático."
        self.txt_log.insert("end", f"\n[AVISO] {mensaje}\n")
        self.txt_log.see("end")
        mostrar_info("Modo manual", mensaje)
        return False

    def _procesar_cola_ui(self):
        while not self.cola_ui.empty():
            tipo, dato = self.cola_ui.get_nowait()
            if tipo == "log":
                self.txt_log.insert("end", str(dato))
                self.txt_log.see("end")
            elif tipo == "grafica":
                self._mostrar_grafica(*dato)
            elif tipo == "fin":
                self.ejecutando = False
                self.btn_iniciar.configure(state="normal")
                self.btn_test_reles.configure(state="normal")
                self.btn_test_solar.configure(state="normal")
                self.btn_abortar.configure(state="disabled")
            elif tipo == "modo_manual":
                self.ejecutando = False
                self.modo_automatico = dato == "automatico"
                self.btn_manual.configure(
                    state="normal",
                    text=(
                        "⚙ Liberar Keithley"
                        if self.modo_automatico
                        else "↩ Modo automático"
                    ),
                )
                self.txt_log.insert(
                    "end",
                    "[OK] Control automático recuperado.\n"
                    if self.modo_automatico
                    else "[OK] Keithley liberado para control manual.\n",
                )
                self.txt_log.see("end")
            elif tipo == "error_modo_manual":
                self.ejecutando = False
                self.btn_manual.configure(state="normal")
                self.txt_log.insert("end", f"[ERROR] No se pudo cambiar el modo del Keithley: {dato}\n")
                self.txt_log.see("end")
                mostrar_error("Error de control", f"No se pudo cambiar el modo del Keithley:\n{dato}")

        self.after(100, self._procesar_cola_ui)

    def _mostrar_grafica(self, datos, cfg):
        try:
            imagen = generar_imagen_tk_curvas_iv_pv(datos, cfg)
            if imagen is None:
                return
            self._imagenes_log.append(imagen)
            self.txt_log.insert("end", "\n")
            self.txt_log.image_create("end", image=imagen)
            self.txt_log.insert("end", "\n")
            self.txt_log.see("end")
        except Exception as exc:
            self.txt_log.insert("end", f"[AVISO] No se pudo mostrar la curva: {exc}\n")
