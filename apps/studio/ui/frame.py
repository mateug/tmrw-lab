"""Marco principal de Studio (StudioFrame).

Orquesta las medidas I-V con Keithley 2450 y la combinación de ejes activos
(Motor Lineal con centrado y simulador solar, Iluminación multicanal A/B/C/D y Estructura).
"""
from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext

from core.instrument.keithley import liberar_control_manual_keithley, conectar_y_verificar
from core.instrument.registry import abortar_instrumento_activo, abortar_motor_activo
from core.plot.plotter import generar_imagen_tk_curvas_iv_pv
from core.ui_kit.scaler import ui, ui_font, ui_font_console, ui_font_label, UIConfig
from core.ui_kit.shared import crear_barra_superior, crear_seccion_frame, mostrar_error, mostrar_info
from core.ui_kit.theme import theme_mgr

from apps.studio.config import get_default_config
from apps.studio.plan_engine import generar_plan_estudio
from apps.studio.ui.panel_medida import crear_panel_medida_fijo
from apps.studio.ui.panel_motor import PanelEjesMotor
from apps.studio.ui.panel_led import PanelEjeIluminacion
from apps.studio.ui.panel_estructura import PanelEjeEstructura
from core.instrument.relay_structure import crear_rele_estructura
from core.instrument.solar_simulator import crear_controlador_simulador_solar, normalizar_canal_ossila


class StudioFrame(ttk.Frame):
    """Marco principal del Modo Studio."""

    def __init__(self, master, callback_volver=None, **kwargs):
        super().__init__(master, **kwargs)
        self.callback_volver = callback_volver
        self.cfg_base = get_default_config()

        self.evento_aborto = threading.Event()
        self.cola_ui = queue.Queue()
        self.ejecutando = False
        self.modo_automatico = True
        self._imagenes_log = []

        self._inicializar_variables()
        self._crear_ui()
        self._procesar_cola_ui()

    def _inicializar_variables(self):
        c = self.cfg_base
        m = c.get("motor", {})
        s = c.get("simulador_solar", {})
        ip = c.get("irradiancia_potencia", {})
        iw = c.get("irradiancia_longitud_onda", {})

        canales_11 = ["390", "450", "515", "cool_white", "warm_white", "600", "630", "660", "730", "850", "950"]
        estructuras_base = [
            "Estructura 1",
            "Estructura 2",
            "Estructura 3",
            "Estructura 4",
            "Estructura 5",
            "Estructura 6",
            "Estructura 7",
        ]

        self.vars = {
            # Salida y Guardado
            "carpeta_salida": tk.StringVar(value=c.get("carpeta_salida", "")),
            "nombre_carpeta_medida": tk.StringVar(value=c.get("nombre_carpeta_medida", "")),
            "nombre_medida": tk.StringVar(value=c.get("nombre_medida", "medida_studio")),
            # SMU Keithley
            "recurso_visa": tk.StringVar(value=c.get("recurso_visa", "")),
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
            # Combinatoria entre ejes
            "relacion_ejes": tk.StringVar(value=c.get("relacion_ejes", "1-N")),
            # Ejes activos
            "barrido_motor_activo": tk.BooleanVar(value=c.get("barrido_motor_activo", False)),
            "simulador_solar_activo": tk.BooleanVar(value=c.get("simulador_solar_activo", False)),
            "eje_estructura_activo": tk.BooleanVar(value=c.get("eje_estructura_activo", False)),
            # Motores (lineal, inclinación y rotación)
            "motor_lineal_activo": tk.BooleanVar(value=c.get("motor_lineal_activo", True)),
            "motor_inclinacion_activo": tk.BooleanVar(value=c.get("motor_inclinacion_activo", False)),
            "motor_rotacion_activo": tk.BooleanVar(value=c.get("motor_rotacion_activo", False)),
            "motor_puerto_serie": tk.StringVar(value=m.get("puerto_serie", "COM4")),
            "motor_baudrate": tk.StringVar(value=str(m.get("baudrate", 115200))),
            "motor_step_pasos": tk.StringVar(value=str(m.get("step_pasos", -625))),
            "motor_stop_pasos": tk.StringVar(value=str(m.get("stop_pasos", -62500))),
            "motor_resolucion_mm_paso": tk.StringVar(value=str(m.get("resolucion_mm_paso", 0.00128))),
            "motor_espera_s": tk.StringVar(value=str(m.get("espera_estabilizacion_s", 0.0))),
            "motor_poner_cero_conectar": tk.BooleanVar(value=m.get("poner_cero_al_conectar", True)),
            "motor_volver_cero_final": tk.BooleanVar(value=m.get("volver_cero_al_final", False)),
            "motor_manual_pasos": tk.StringVar(value=str(m.get("pasos_centrado_pulsacion", 1))),
            "motor_inclinacion_puerto_serie": tk.StringVar(value=m.get("inclinacion", {}).get("puerto_serie", "COM5")),
            "motor_inclinacion_baudrate": tk.StringVar(value=str(m.get("inclinacion", {}).get("baudrate", 115200))),
            "motor_inclinacion_step_pasos": tk.StringVar(value=str(m.get("inclinacion", {}).get("step_pasos", -625))),
            "motor_inclinacion_stop_pasos": tk.StringVar(value=str(m.get("inclinacion", {}).get("stop_pasos", -62500))),
            "motor_inclinacion_resolucion_mm_paso": tk.StringVar(value=str(m.get("inclinacion", {}).get("resolucion_mm_paso", 0.00128))),
            "motor_inclinacion_espera_s": tk.StringVar(value=str(m.get("inclinacion", {}).get("espera_estabilizacion_s", 0.0))),
            "motor_inclinacion_poner_cero_conectar": tk.BooleanVar(value=m.get("inclinacion", {}).get("poner_cero_al_conectar", True)),
            "motor_inclinacion_volver_cero_final": tk.BooleanVar(value=m.get("inclinacion", {}).get("volver_cero_al_final", False)),
            "motor_inclinacion_manual_pasos": tk.StringVar(value=str(m.get("inclinacion", {}).get("pasos_centrado_pulsacion", 1))),
            "motor_rotacion_puerto_serie": tk.StringVar(value=m.get("rotacion", {}).get("puerto_serie", "COM6")),
            "motor_rotacion_baudrate": tk.StringVar(value=str(m.get("rotacion", {}).get("baudrate", 115200))),
            "motor_rotacion_step_pasos": tk.StringVar(value=str(m.get("rotacion", {}).get("step_pasos", -625))),
            "motor_rotacion_stop_pasos": tk.StringVar(value=str(m.get("rotacion", {}).get("stop_pasos", -62500))),
            "motor_rotacion_resolucion_mm_paso": tk.StringVar(value=str(m.get("rotacion", {}).get("resolucion_mm_paso", 0.00128))),
            "motor_rotacion_espera_s": tk.StringVar(value=str(m.get("rotacion", {}).get("espera_estabilizacion_s", 0.0))),
            "motor_rotacion_poner_cero_conectar": tk.BooleanVar(value=m.get("rotacion", {}).get("poner_cero_al_conectar", True)),
            "motor_rotacion_volver_cero_final": tk.BooleanVar(value=m.get("rotacion", {}).get("volver_cero_al_final", False)),
            "motor_rotacion_manual_pasos": tk.StringVar(value=str(m.get("rotacion", {}).get("pasos_centrado_pulsacion", 1))),
            "motor_solar_puerto": tk.StringVar(value=s.get("puerto_serie", "COM3")),
            "motor_solar_baudrate": tk.StringVar(value=str(s.get("baudrate", 9600))),
            "motor_solar_modo": tk.StringVar(value=m.get("simulador_solar_modo", "off")),
            "motor_solar_potencia": tk.StringVar(value="" if m.get("solar_potencia_mW_cm2") is None else str(m.get("solar_potencia_mW_cm2"))),
            "motor_solar_longitud_onda": tk.StringVar(value="950 nm"),
            "motor_solar_intensidad_pct": tk.StringVar(value=str(m.get("solar_intensidad_pct", 100))),
            "motor_espera_luz": tk.StringVar(value=str(m.get("espera_luz_encendida_s", 0.0))),
            # Iluminación
            "solar_puerto_serie": tk.StringVar(value=s.get("puerto_serie", "COM3")),
            "solar_baudrate": tk.StringVar(value=str(s.get("baudrate", 9600))),
            "irradiancia_modo": tk.StringVar(value=c.get("irradiancia_modo", "potencia")),
            "solar_p_ini": tk.StringVar(value=str(ip.get("p_inicial_mW_cm2", 0.0))),
            "solar_p_fin": tk.StringVar(value=str(ip.get("p_final_mW_cm2", 100.0))),
            "solar_p_paso": tk.StringVar(value=str(ip.get("paso_mW_cm2", 10.0))),
            "solar_p_custom": tk.StringVar(value=""),
            "solar_canales_seleccionados_dict": {ch: tk.BooleanVar(value=(ch == "950")) for ch in canales_11},
            "solar_i_ini": tk.StringVar(value=str(iw.get("i_inicial_pct", 0))),
            "solar_i_fin": tk.StringVar(value=str(iw.get("i_final_pct", 100))),
            "solar_i_paso": tk.StringVar(value=str(iw.get("paso_pct", 10))),
            "solar_i_custom": tk.StringVar(value=""),
            # Submodo C: filas canal/intensidades + relaciones 1-1 / 1-N entre canales consecutivos
            # (mismo formato que usaba la pestaña "Combinación Multi-Canal" del antiguo Modo 3).
            "solar_canales_comb_lista": [
                {"canal": "950", "intensidades": "100"},
                {"canal": "660", "intensidades": "0, 50, 100"},
            ],
            "solar_canales_comb_relaciones": ["1-1"],
            # Submodo D: lista de combinaciones con nombre propio, cada una con sus propias filas
            # canal/intensidades y relaciones (mismo formato que "Múltiples Combinaciones Multi-Canal").
            "solar_recetas_lista": [{
                "nombre": "combo_950_660",
                "canales": [
                    {"canal": "950", "intensidades": "100"},
                    {"canal": "660", "intensidades": "0, 50, 100"},
                ],
                "relaciones": ["1-1"],
            }, {
                "nombre": "combo_450_515",
                "canales": [
                    {"canal": "450", "intensidades": "100"},
                    {"canal": "515", "intensidades": "80"},
                ],
                "relaciones": ["1-1"],
            }],
            "solar_espera_encendido_s": tk.StringVar(value="0.0"),
            "solar_espera_estab_s": tk.StringVar(value="1.0"),
            "solar_tiempo_enfriado_s": tk.StringVar(value="0.0"),
            "solar_tiempo_espera_cada_n": tk.StringVar(value="0.0"),
            "solar_cada_n_medidas_estructura": tk.StringVar(value="0"),
            "solar_apagar_al_final": tk.BooleanVar(value=True),
            # Estructura
            "estructura_disponibles": estructuras_base,
            "estructura_seleccionadas_dict": {name: tk.BooleanVar(value=name in {"Estructura 1", "Estructura 2"}) for name in estructuras_base},
            "estructura_nombres_dict": {name: tk.StringVar(value=name) for name in estructuras_base},
            "estructura_keithley_vars": {
                name: {
                    "recurso_visa": tk.StringVar(value=c.get("recurso_visa", "AUTO")),
                    "modo_medida": tk.StringVar(value=c.get("modo_medida", "completa")),
                    "i_max_uA": tk.StringVar(value=str(c.get("i_max_uA", 10.0))),
                    "v_ini_dir": tk.StringVar(value=str(c["directa"]["v_inicial_mV"])),
                    "v_fin_dir": tk.StringVar(value=str(c["directa"]["v_final_mV"])),
                    "paso_dir": tk.StringVar(value=str(c["directa"]["paso_mV"])),
                    "v_fin_inv": tk.StringVar(value=str(c["inversa"]["v_final_V"])),
                    "paso_inv": tk.StringVar(value=str(c["inversa"]["paso_mV"])),
                }
                for name in estructuras_base
            },
            "estructura_lista": tk.StringVar(value="Estructura 1, Estructura 2"),
            "estructura_puerto_serie": tk.StringVar(value=c.get("estructura", {}).get("puerto_serie", "COM5")),
            "estructura_baudrate": tk.StringVar(value=str(c.get("estructura", {}).get("baudrate", 9600))),
            "estructura_espera_s": tk.StringVar(value="0.5"),
        }

    def _crear_ui(self):
        t = theme_mgr.get_current_theme()
        crear_barra_superior(self, "Modo 1: Studio — Medidas I-V y Combinatoria Multieje", self.callback_volver)

        # Contenedor dividido en 2 columnas
        body = ttk.Frame(self, style="Window.TFrame")
        body.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))

        # Columna Izquierda: Panel de Configuración SIN scroll envolvente
        col_izq = ttk.Frame(body, style="Window.TFrame")
        col_izq.pack(side="left", fill="both", expand=True, padx=(0, ui(4)))

        # 1. Panel Fijo: Guardado de datos (encima) + Keithley 2450 + Relación de ejes
        (
            f_medida,
            self.btn_iniciar,
            self.btn_rapida,
            self.btn_abortar,
            self.btn_manual,
            self.btn_test,
        ) = crear_panel_medida_fijo(
            col_izq,
            self.vars,
            callback_iniciar=self._on_iniciar,
            callback_rapida=self._on_medida_rapida,
            callback_abortar=self._on_abortar,
            callback_modo_manual=self._on_modo_manual,
            callback_prueba=self._on_prueba_hardware,
        )
        f_medida.pack(fill="x", pady=(0, ui(4)))

        # 2. Notebook de Ejes Activos (Ejes Motor, Eje Iluminación, Eje Estructura)
        self.nb_ejes = ttk.Notebook(col_izq)
        self.nb_ejes.pack(fill="both", expand=True, pady=ui(2))

        self.panel_motor = PanelEjesMotor(self.nb_ejes, self.vars, self.evento_aborto)
        self.nb_ejes.add(self.panel_motor, text="Ejes Motor")

        self.panel_led = PanelEjeIluminacion(self.nb_ejes, self.vars)
        self.nb_ejes.add(self.panel_led, text="Eje Iluminación")

        self.panel_estructura = PanelEjeEstructura(self.nb_ejes, self.vars)
        self.nb_ejes.add(self.panel_estructura, text="Eje Estructura")

        # Columna Derecha: Consola de Resultados y Previsualización
        col_der = ttk.Frame(body, width=ui(460), style="Window.TFrame")
        col_der.pack(side="right", fill="both", expand=False, padx=(ui(4), 0))
        col_der.pack_propagate(False)

        f_res = crear_seccion_frame(col_der, "Resultados y Progreso", "results")
        f_res.pack(fill="both", expand=True)

        # Badge de Estado
        f_status = ttk.Frame(f_res, style="Results.TFrame")
        f_status.pack(fill="x", pady=(0, ui(3)))

        res_c = t.get("results", {})
        self.lbl_badge = tk.Label(
            f_status,
            text="[✓ LISTO]",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            bg=res_c.get("badge_ready_bg", "#10b981"),
            fg=res_c.get("badge_ready_fg", "#ffffff"),
            padx=6, pady=2, relief="solid", bd=1,
        )
        self.lbl_badge.pack(side="right", padx=ui(4))

        # Consola de Texto
        self.txt_log = scrolledtext.ScrolledText(
            f_res,
            font=ui_font_console(),
            bg=res_c.get("bg_console", "#1e293b"),
            fg=res_c.get("fg_console", "#f8fafc"),
            insertbackground="#0284c7",
            borderwidth=1,
            relief="solid",
            height=UIConfig.CONSOLE_HEIGHT,
        )
        self.txt_log.pack(fill="both", expand=True, pady=ui(4))
        self.txt_log.insert("end", "Listo para configurar e iniciar la secuencia en Studio.\n")

    def _parsear_recetas_iluminacion(self) -> list[dict]:
        """Parsea las combinaciones del submodo D al formato usado por el plan de estudio.

        Cada combinación conserva el mismo formato que usaba la pestaña
        "Múltiples Combinaciones Multi-Canal" del antiguo Modo 3: nombre,
        lista de canales con sus intensidades (posiblemente varias separadas
        por comas) y las relaciones 1-1 / 1-N entre canales consecutivos.
        """
        if hasattr(self, "panel_led") and hasattr(self.panel_led, "_sincronizar_recetas_data"):
            self.panel_led._sincronizar_recetas_data()

        combinaciones = list(self.vars.get("solar_recetas_lista", []))
        salida = []
        for idx, combo in enumerate(combinaciones, start=1):
            nombre = str(combo.get("nombre", "")).strip() or f"combo_{idx}"
            canales = []
            for canal_info in combo.get("canales", []):
                canal_raw = str(canal_info.get("canal", "")).strip()
                canal = normalizar_canal_ossila(canal_raw)
                intensidades_raw = str(canal_info.get("intensidades", "0")).strip()
                if not canal or not intensidades_raw:
                    continue
                canales.append({"canal": canal, "intensidades": intensidades_raw})
            if canales:
                relaciones = [str(r).strip() or "1-1" for r in combo.get("relaciones", [])]
                salida.append({"nombre": nombre, "canales": canales, "relaciones": relaciones})
        return salida

    def _recoger_config(self) -> dict:
        v = self.vars
        cfg = get_default_config()

        cfg["carpeta_salida"] = v["carpeta_salida"].get().strip()
        cfg["nombre_carpeta_medida"] = v["nombre_carpeta_medida"].get().strip()
        cfg["nombre_medida"] = v["nombre_medida"].get().strip() or "medida_studio"

        cfg["recurso_visa"] = v["recurso_visa"].get().strip()
        cfg["modo_medida"] = v["modo_medida"].get().strip()
        cfg["directa"]["v_inicial_mV"] = float(v["v_ini_dir"].get() or 0.0)
        cfg["directa"]["v_final_mV"] = float(v["v_fin_dir"].get() or 600.0)
        cfg["directa"]["paso_mV"] = float(v["paso_dir"].get() or 10.0)
        cfg["inversa"]["v_final_V"] = float(v["v_fin_inv"].get() or -0.5)
        cfg["inversa"]["paso_mV"] = float(v["paso_inv"].get() or 10.0)
        cfg["i_max_uA"] = float(v["i_max_uA"].get() or 10.0)
        cfg["superficie_um2"] = float(v["superficie_um2"].get()) if v["superficie_um2"].get() else None
        cfg["irradiancia_mW_cm2"] = float(v["irradiancia_mW_cm2"].get()) if v["irradiancia_mW_cm2"].get() else None
        cfg["invertir_eje_y_graficas"] = v["invertir_eje_y"].get()
        cfg["medir_tension_real"] = v["medir_tension_real"].get()

        cfg["relacion_ejes"] = "1-N"
        cfg["barrido_motor_activo"] = v["barrido_motor_activo"].get()
        cfg["motor_lineal_activo"] = v["motor_lineal_activo"].get()
        cfg["motor_inclinacion_activo"] = v["motor_inclinacion_activo"].get()
        cfg["motor_rotacion_activo"] = v["motor_rotacion_activo"].get()
        cfg["simulador_solar_activo"] = v["simulador_solar_activo"].get()
        cfg["eje_estructura_activo"] = v["eje_estructura_activo"].get()

        # Motor
        cfg["motor"]["puerto_serie"] = v["motor_puerto_serie"].get().strip()
        cfg["motor"]["baudrate"] = int(v["motor_baudrate"].get() or 115200)
        cfg["motor"]["step_pasos"] = int(v["motor_step_pasos"].get() or -625)
        cfg["motor"]["stop_pasos"] = int(v["motor_stop_pasos"].get() or -62500)
        cfg["motor"]["resolucion_mm_paso"] = float(v["motor_resolucion_mm_paso"].get() or 0.00128)
        cfg["motor"]["espera_estabilizacion_s"] = float(v["motor_espera_s"].get() or 0.0)
        cfg["motor"]["poner_cero_al_conectar"] = v["motor_poner_cero_conectar"].get()
        cfg["motor"]["volver_cero_al_final"] = v["motor_volver_cero_final"].get()
        cfg["motor"]["simulador_solar_modo"] = v["motor_solar_modo"].get()
        cfg["motor"]["solar_potencia_mW_cm2"] = float(v["motor_solar_potencia"].get()) if v["motor_solar_potencia"].get() else None
        cfg["motor"]["solar_longitud_onda"] = v["motor_solar_longitud_onda"].get()
        cfg["motor"]["solar_intensidad_pct"] = float(v["motor_solar_intensidad_pct"].get() or 100)
        cfg["motor"]["espera_luz_encendida_s"] = float(v["motor_espera_luz"].get() or 0.0)
        cfg["motor"]["inclinacion"] = {
            "puerto_serie": v["motor_inclinacion_puerto_serie"].get().strip(),
            "baudrate": int(v["motor_inclinacion_baudrate"].get() or 115200),
            "step_pasos": int(v["motor_inclinacion_step_pasos"].get() or -625),
            "stop_pasos": int(v["motor_inclinacion_stop_pasos"].get() or -62500),
            "resolucion_mm_paso": float(v["motor_inclinacion_resolucion_mm_paso"].get() or 0.00128),
            "espera_estabilizacion_s": float(v["motor_inclinacion_espera_s"].get() or 0.0),
            "poner_cero_al_conectar": v["motor_inclinacion_poner_cero_conectar"].get(),
            "volver_cero_al_final": v["motor_inclinacion_volver_cero_final"].get(),
            "pasos_centrado_pulsacion": int(v["motor_inclinacion_manual_pasos"].get() or 1),
        }
        cfg["motor"]["rotacion"] = {
            "puerto_serie": v["motor_rotacion_puerto_serie"].get().strip(),
            "baudrate": int(v["motor_rotacion_baudrate"].get() or 115200),
            "step_pasos": int(v["motor_rotacion_step_pasos"].get() or -625),
            "stop_pasos": int(v["motor_rotacion_stop_pasos"].get() or -62500),
            "resolucion_mm_paso": float(v["motor_rotacion_resolucion_mm_paso"].get() or 0.00128),
            "espera_estabilizacion_s": float(v["motor_rotacion_espera_s"].get() or 0.0),
            "poner_cero_al_conectar": v["motor_rotacion_poner_cero_conectar"].get(),
            "volver_cero_al_final": v["motor_rotacion_volver_cero_final"].get(),
            "pasos_centrado_pulsacion": int(v["motor_rotacion_manual_pasos"].get() or 1),
        }

        # Iluminación
        cfg["simulador_solar"]["puerto_serie"] = v["solar_puerto_serie"].get().strip()
        cfg["simulador_solar"]["baudrate"] = int(v["solar_baudrate"].get() or 9600)
        cfg["irradiancia_modo"] = v["irradiancia_modo"].get()
        cfg["irradiancia_potencia"]["p_inicial_mW_cm2"] = float(v["solar_p_ini"].get() or 0.0)
        cfg["irradiancia_potencia"]["p_final_mW_cm2"] = float(v["solar_p_fin"].get() or 100.0)
        cfg["irradiancia_potencia"]["paso_mW_cm2"] = float(v["solar_p_paso"].get() or 10.0)
        cfg["irradiancia_potencia"]["lista_potencias_custom"] = v["solar_p_custom"].get().strip() or None
        cfg["irradiancia_longitud_onda"]["i_inicial_pct"] = float(v["solar_i_ini"].get() or 0.0)
        cfg["irradiancia_longitud_onda"]["i_final_pct"] = float(v["solar_i_fin"].get() or 100.0)
        cfg["irradiancia_longitud_onda"]["paso_pct"] = float(v["solar_i_paso"].get() or 10.0)
        cfg["irradiancia_longitud_onda"]["lista_intensidades_custom"] = v["solar_i_custom"].get().strip() or None
        cfg["irradiancia_longitud_onda"]["canales_seleccionados"] = [
            ch for ch, sel in v["solar_canales_seleccionados_dict"].items() if sel.get()
        ]
        cfg["irradiancia_combinacion"]["canales_combinacion"] = v["solar_canales_comb_lista"]
        cfg["irradiancia_combinacion"]["relaciones"] = list(v.get("solar_canales_comb_relaciones", []))
        cfg["irradiancia_combinacion"]["cada_n_medidas_estructura"] = int(v["solar_cada_n_medidas_estructura"].get() or 0)
        cfg["irradiancia_combinacion"]["tiempo_enfriado_s"] = float(v["solar_tiempo_enfriado_s"].get() or 0.0)
        cfg["irradiancia_combinacion"]["tiempo_espera_cada_n_s"] = float(v["solar_tiempo_espera_cada_n"].get() or 0.0)
        cfg["irradiancia_multiples_combinaciones"]["combinaciones"] = self._parsear_recetas_iluminacion()
        cfg["irradiancia_multiples_combinaciones"]["cada_n_medidas_estructura"] = int(v["solar_cada_n_medidas_estructura"].get() or 0)
        cfg["irradiancia_multiples_combinaciones"]["tiempo_enfriado_s"] = float(v["solar_tiempo_enfriado_s"].get() or 0.0)
        cfg["irradiancia_multiples_combinaciones"]["tiempo_espera_cada_n_s"] = float(v["solar_tiempo_espera_cada_n"].get() or 0.0)

        # Estructura
        estructura_seleccionadas = [
            nombre for nombre, sel in v["estructura_seleccionadas_dict"].items() if sel.get()
        ]
        estructura_nombres = [
            v["estructura_nombres_dict"].get(nombre, tk.StringVar(value=nombre)).get().strip() or nombre
            for nombre in estructura_seleccionadas
        ]
        cfg["estructura"]["puerto_serie"] = v["estructura_puerto_serie"].get().strip()
        cfg["estructura"]["baudrate"] = int(v["estructura_baudrate"].get() or 9600)
        cfg["estructura"]["estructuras"] = estructura_nombres
        cfg["estructura"]["espera_estabilizacion_s"] = float(v["estructura_espera_s"].get() or 0.5)
        cfg["estructura"]["keithley_por_estructura"] = {}
        for nombre_base in estructura_seleccionadas:
            nombre_mostrar = v["estructura_nombres_dict"][nombre_base].get().strip() or nombre_base
            kvars = v["estructura_keithley_vars"][nombre_base]
            cfg["estructura"]["keithley_por_estructura"][nombre_mostrar] = {
                "recurso_visa": kvars["recurso_visa"].get().strip(),
                "modo_medida": kvars["modo_medida"].get().strip(),
                "i_max_uA": float(kvars["i_max_uA"].get() or 10.0),
                "v_inicial_mV": float(kvars["v_ini_dir"].get() or 0.0),
                "v_final_mV": float(kvars["v_fin_dir"].get() or 600.0),
                "paso_mV": float(kvars["paso_dir"].get() or 10.0),
                "v_final_inversa_V": float(kvars["v_fin_inv"].get() or -0.5),
                "paso_inversa_mV": float(kvars["paso_inv"].get() or 10.0),
            }
        v["estructura_lista"].set(", ".join(estructura_nombres))

        return cfg

    def _conectar_smu_studio(self, cfg):
        """Conecta el Keithley 2450 usado por el modo Studio."""
        recurso = str(cfg.get("recurso_visa", "AUTO")).strip()
        return "Keithley 2450", conectar_y_verificar(recurso or "AUTO")

    def _on_iniciar(self):
        if self.ejecutando:
            return
        cfg = self._recoger_config()
        try:
            plan = generar_plan_estudio(cfg)
        except Exception as exc:
            mostrar_error("Error Plan", f"No se pudo generar el plan de estudio:\n{exc}")
            return

        self.ejecutando = True
        self.evento_aborto.clear()
        self.btn_iniciar.configure(state="disabled")
        self.btn_rapida.configure(state="disabled")
        self.btn_test.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self._set_badge("MIDIENDO", "#f59e0b", "#ffffff")
        self.txt_log.insert("end", f"\n>>> INICIANDO SECUENCIA ({len(plan)} pasos planificados)...\n")

        threading.Thread(target=self._hilo_secuencia, args=(cfg, plan), daemon=True).start()

    def _on_medida_rapida(self):
        if self.ejecutando:
            return
        cfg = self._recoger_config()
        self.ejecutando = True
        self.evento_aborto.clear()
        self.btn_iniciar.configure(state="disabled")
        self.btn_rapida.configure(state="disabled")
        self.btn_test.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self._set_badge("MEDIDA RÁPIDA", "#0284c7", "#ffffff")
        self.txt_log.insert("end", "\n>>> Ejecutando medida rápida de diagnóstico puntual...\n")

        def _hilo_rapida():
            try:
                from core.measure.run_keithley import run as run_k
                smu = conectar_y_verificar(cfg.get("recurso_visa", ""))
                self.cola_ui.put(("log", "[i] Instrumento de diagnóstico: Keithley 2450\n"))
                datos = run_k(cfg)
                self.cola_ui.put(("log", f"[✓] Medida rápida completada ({len(datos.get('voltaje_V', []))} puntos).\n"))
            except Exception as exc:
                self.cola_ui.put(("log", f"[ERROR] Fallo en medida rápida: {exc}\n"))
            finally:
                self.cola_ui.put(("fin_secuencia", None))

        threading.Thread(target=_hilo_rapida, daemon=True).start()

    def _on_abortar(self):
        if not self.ejecutando:
            return
        self.evento_aborto.set()
        abortar_instrumento_activo()
        abortar_motor_activo()
        self.txt_log.insert("end", "\n[⏹] Solicitud de aborto enviada...\n")

    def _on_modo_manual(self):
        try:
            liberar_control_manual_keithley(self.vars["recurso_visa"].get().strip())
            mostrar_info("Modo Manual", "Keithley 2450 liberado para control manual local.")
        except Exception as exc:
            mostrar_error("Error", f"No se pudo liberar el SMU:\n{exc}")

    def _on_prueba_hardware(self):
        if self.ejecutando:
            return
        cfg = self._recoger_config()
        self.ejecutando = True
        self.evento_aborto.clear()
        self.btn_iniciar.configure(state="disabled")
        self.btn_rapida.configure(state="disabled")
        self.btn_test.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self._set_badge("TEST RELÉS", "#7c3aed", "#ffffff")
        self.txt_log.insert("end", "\n>>> Probando relés y estructuras del eje Studio...\n")
        threading.Thread(target=self._hilo_prueba_hardware, args=(cfg,), daemon=True).start()

    def _hilo_prueba_hardware(self, cfg):
        rele = None
        try:
            estructuras = cfg.get("estructura", {}).get("estructuras") or ["Estructura 1", "Estructura 2"]
            rele = crear_rele_estructura(cfg, self.evento_aborto)
            rele.connect()
            for nombre in estructuras:
                if self.evento_aborto.is_set():
                    raise RuntimeError("Prueba abortada por el usuario.")
                rele.select(nombre)
                self.cola_ui.put(("log", f"[TEST] Estructura seleccionada: {nombre}\n"))
                time.sleep(0.2)
            self.cola_ui.put(("log", "[✓] Prueba de relés y estructuras completada correctamente.\n"))
        except Exception as exc:
            self.cola_ui.put(("log", f"[ERROR] Prueba de relés/estructuras: {exc}\n"))
        finally:
            if rele is not None:
                try:
                    rele.close()
                except Exception:
                    pass
            self.cola_ui.put(("fin_secuencia", None))

    def _hilo_secuencia(self, cfg, plan):
        rele = None
        simulador = None
        try:
            if cfg.get("eje_estructura_activo", False):
                rele = crear_rele_estructura(cfg, self.evento_aborto)
                rele.connect()

            if cfg.get("simulador_solar_activo", False):
                simulador = crear_controlador_simulador_solar(cfg, self.evento_aborto)
                if simulador is not None:
                    simulador.connect()

            smu_obj = conectar_y_verificar(cfg.get("recurso_visa", ""))

            for idx, paso in enumerate(plan, 1):
                if self.evento_aborto.is_set():
                    self.cola_ui.put(("log", "\n[⏹] Secuencia abortada por el usuario.\n"))
                    break

                if paso.get("tipo") == "medida":
                    estructura = paso.get("estructura")
                    keithley_cfg = paso.get("keithley", {})
                    if estructura and rele is not None:
                        self.cola_ui.put(("log", f"[{idx}/{len(plan)}] Seleccionando estructura: {estructura}\n"))
                        rele.select(estructura)
                    self.cola_ui.put(("log", f"[{idx}/{len(plan)}] Ejecutando medida para {estructura or 'estructura no seleccionada'} (Keithley 2450)\n"))
                    cfg_local = dict(cfg)
                    cfg_local["estructura"] = dict(cfg.get("estructura", {}), estructuras=[estructura] if estructura else [])
                    cfg_local["estructura"]["keithley_por_estructura"] = cfg.get("estructura", {}).get("keithley_por_estructura", {})
                    if keithley_cfg:
                        cfg_local["modo_medida"] = str(keithley_cfg.get("modo_medida", cfg.get("modo_medida", "directa"))).strip() or cfg.get("modo_medida", "directa")
                        cfg_local["i_max_uA"] = float(keithley_cfg.get("i_max_uA", cfg.get("i_max_uA", 10.0)))
                        cfg_local["i_max_A"] = cfg_local["i_max_uA"] * 1e-6
                        cfg_local["directa"] = dict(cfg.get("directa", {}))
                        cfg_local["directa"]["v_inicial_mV"] = float(keithley_cfg.get("v_inicial_mV", cfg_local["directa"].get("v_inicial_mV", 0.0)))
                        cfg_local["directa"]["v_final_mV"] = float(keithley_cfg.get("v_final_mV", cfg_local["directa"].get("v_final_mV", 550.0)))
                        cfg_local["directa"]["paso_mV"] = float(keithley_cfg.get("paso_mV", cfg_local["directa"].get("paso_mV", 10.0)))
                        cfg_local["inversa"] = dict(cfg.get("inversa", {}))
                        cfg_local["inversa"]["v_final_V"] = float(keithley_cfg.get("v_final_V", cfg_local["inversa"].get("v_final_V", -0.5)))
                        cfg_local["inversa"]["paso_mV"] = float(keithley_cfg.get("paso_mV", cfg_local["inversa"].get("paso_mV", 10.0)))
                        cfg_local["invertir_eje_y_graficas"] = bool(keithley_cfg.get("invertir_eje_y", cfg.get("invertir_eje_y_graficas", False)))
                    from core.measure.run_keithley import run as run_keithley_medida
                    run_keithley_medida(cfg_local)
                    time.sleep(0.1)
                elif paso.get("tipo") == "enfriar":
                    self.cola_ui.put(("log", f"[{idx}/{len(plan)}] Enfriamiento LED: apagando fuente durante {paso.get('duracion_s', 0.0)} s\n"))
                    if simulador is not None:
                        try:
                            simulador.apagar()
                        except Exception:
                            pass
                    time.sleep(float(paso.get("duracion_s", 0.0)))
                else:
                    self.cola_ui.put(("log", f"[{idx}/{len(plan)}] Ejecutando paso: {paso}\n"))
                    time.sleep(0.1)

            self.cola_ui.put(("log", "\n[✓] Secuencia finalizada con éxito.\n"))
        except Exception as exc:
            self.cola_ui.put(("log", f"\n[ERROR] Secuencia interrumpida: {exc}\n"))
        finally:
            if rele is not None:
                try:
                    rele.close()
                except Exception:
                    pass
            if simulador is not None:
                try:
                    simulador.close()
                except Exception:
                    pass
            if smu_obj is not None:
                try:
                    smu_obj.close()
                except Exception:
                    pass
            self.cola_ui.put(("fin_secuencia", None))

    def _set_badge(self, texto, bg, fg):
        self.lbl_badge.configure(text=f"[{texto}]", bg=bg, fg=fg)

    def _procesar_cola_ui(self):
        while not self.cola_ui.empty():
            tipo, dato = self.cola_ui.get_nowait()
            if tipo == "log":
                self.txt_log.insert("end", str(dato))
                self.txt_log.see("end")
            elif tipo == "fin_secuencia":
                self.ejecutando = False
                self.btn_iniciar.configure(state="normal")
                self.btn_rapida.configure(state="normal")
                if hasattr(self, "btn_test"):
                    self.btn_test.configure(state="normal")
                self.btn_abortar.configure(state="disabled")
                t = theme_mgr.get_current_theme()
                res_c = t.get("results", {})
                self._set_badge("✓ LISTO", res_c.get("badge_ready_bg", "#10b981"), res_c.get("badge_ready_fg", "#ffffff"))

        self.after(100, self._procesar_cola_ui)
