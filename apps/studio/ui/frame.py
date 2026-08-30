"""Marco principal del modo Studio de TMRW Lab."""
import copy
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path
import pandas as pd

from apps.studio.config import get_default_config
from apps.studio.plan_engine import generar_plan_estudio
from apps.studio.ui.panel_medida import crear_panel_medida
from apps.studio.ui.panel_motor import crear_panel_motor
from apps.studio.ui.panel_led import crear_panel_led
from apps.studio.ui.panel_estructura import crear_panel_estructura

from core.instrument import keithley
from core.instrument.motors.motor_lineal import crear_controlador_motor
from core.instrument.solar_simulator import crear_controlador_simulador_solar
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
from core.postprocess.data import guardar_resumen_barrido_motor_excel
from core.ui_kit.scaler import ui, ui_font, ui_font_console, ui_font_label, UIConfig
from core.ui_kit.shared import ScrollableFrame, crear_barra_superior, mostrar_error, mostrar_info
from core.ui_kit.theme import theme_mgr
from core.utils import preparar_carpeta_medida, emitir_log
from core.exceptions import LimiteCorrienteAlcanzado, MedidaAbortadaPorUsuario, ErrorSMU, ErrorMotor, ErrorSimuladorSolar, ErrorRele


class StudioFrame(ttk.Frame):
    """Contenedor integral del modo Studio con ejes combinables."""

    def __init__(self, master, callback_volver=None, **kwargs):
        super().__init__(master, **kwargs)
        self.callback_volver = callback_volver
        self.cfg_base = get_default_config()

        self.evento_aborto = threading.Event()
        self.cola_ui = queue.Queue()
        self.ejecutando = False
        self._imagenes_log = []

        self._inicializar_variables()
        self._crear_ui()
        self._procesar_cola_ui()

    def _inicializar_variables(self):
        c = self.cfg_base
        self.vars = {
            # SMU & IV
            "recurso_visa": tk.StringVar(value=c.get("recurso_visa", "AUTO")),
            "carpeta_salida": tk.StringVar(value=c.get("carpeta_salida", "")),
            "nombre_carpeta_medida": tk.StringVar(value=c.get("nombre_carpeta_medida", "")),
            "nombre_medida": tk.StringVar(value=c.get("nombre_medida", "medida_studio")),
            "modo_medida": tk.StringVar(value=c.get("modo_medida", "completa")),
            "v_ini_dir": tk.StringVar(value=str(c["directa"]["v_inicial_mV"])),
            "v_fin_dir": tk.StringVar(value=str(c["directa"]["v_final_mV"])),
            "paso_dir": tk.StringVar(value=str(c["directa"]["paso_mV"])),
            "v_fin_inv": tk.StringVar(value=str(c["inversa"]["v_final_V"])),
            "paso_inv": tk.StringVar(value=str(c["inversa"]["paso_mV"])),
            "i_max_uA": tk.StringVar(value=str(c.get("i_max_uA", 10))),
            "superficie_um2": tk.StringVar(value="" if c.get("superficie_um2") is None else str(c["superficie_um2"])),
            "irradiancia_mW_cm2": tk.StringVar(value="" if c.get("irradiancia_mW_cm2") is None else str(c["irradiancia_mW_cm2"])),
            "invertir_eje_y": tk.BooleanVar(value=c.get("invertir_eje_y_graficas", True)),
            "medir_tension_real": tk.BooleanVar(value=c.get("medir_tension_real", False)),
            "relacion_ejes": tk.StringVar(value=c.get("relacion_ejes", "1-N")),

            # Eje Motor
            "barrido_motor_activo": tk.BooleanVar(value=c.get("barrido_motor_activo", False)),
            "motor_puerto_serie": tk.StringVar(value=c["motor"]["puerto_serie"]),
            "motor_step_pasos": tk.StringVar(value=str(c["motor"]["step_pasos"])),
            "motor_stop_pasos": tk.StringVar(value=str(c["motor"]["stop_pasos"])),
            "motor_resolucion_mm_paso": tk.StringVar(value=str(c["motor"]["resolucion_mm_paso"])),
            "motor_espera_s": tk.StringVar(value=str(c["motor"].get("espera_estabilizacion_s", 0.0))),
            "motor_baudrate": tk.StringVar(value=str(c["motor"].get("baudrate", 115200))),

            # Eje LEDs
            "simulador_solar_activo": tk.BooleanVar(value=c.get("simulador_solar_activo", False)),
            "solar_puerto_serie": tk.StringVar(value=c["simulador_solar"]["puerto_serie"]),
            "irradiancia_modo": tk.StringVar(value=c.get("irradiancia_modo", "potencia")),
            "solar_p_ini": tk.StringVar(value=str(c["irradiancia_potencia"]["p_inicial_mW_cm2"])),
            "solar_p_fin": tk.StringVar(value=str(c["irradiancia_potencia"]["p_final_mW_cm2"])),
            "solar_p_paso": tk.StringVar(value=str(c["irradiancia_potencia"]["paso_mW_cm2"])),
            "solar_p_custom": tk.StringVar(value=""),
            "solar_canal_seleccionado": tk.StringVar(value="390"),
            "solar_i_ini": tk.StringVar(value=str(c["irradiancia_longitud_onda"]["i_inicial_pct"])),
            "solar_i_fin": tk.StringVar(value=str(c["irradiancia_longitud_onda"]["i_final_pct"])),
            "solar_i_paso": tk.StringVar(value=str(c["irradiancia_longitud_onda"]["paso_pct"])),
            "solar_comb_ch1": tk.StringVar(value="950"),
            "solar_comb_val1": tk.StringVar(value="100"),
            "solar_comb_ch2": tk.StringVar(value="660"),
            "solar_comb_val2": tk.StringVar(value="0, 50, 100"),
            "solar_espera_encendido_s": tk.StringVar(value="3.0"),
            "solar_espera_estab_s": tk.StringVar(value="3.0"),
            "solar_apagar_al_final": tk.BooleanVar(value=True),

            # Eje Estructura
            "eje_estructura_activo": tk.BooleanVar(value=c.get("eje_estructura_activo", False)),
            "estructuras_lista": tk.StringVar(value="Estructura 1, Estructura 2"),
        }

    def _crear_ui(self):
        t = theme_mgr.get_current_theme()
        self.configure(style="Window.TFrame")

        # Barra superior con botón volver y selector de tema
        top = crear_barra_superior(self, "TMRW Lab — Studio", self.callback_volver)
        top.pack(fill="x", padx=ui(10), pady=(ui(8), 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=ui(6))

        # Contenedor principal: izquierda (ejes y parámetros) / derecha (consola y gráfica)
        cuerpo = ttk.Frame(self, style="Window.TFrame")
        cuerpo.pack(fill="both", expand=True, padx=ui(10), pady=ui(4))
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        # ---- PANEL IZQUIERDO (Pestañas de Ejes) ----
        scroll_izq = ScrollableFrame(cuerpo)
        scroll_izq.grid(row=0, column=0, sticky="nsew", padx=(0, ui(6)))
        f_izq = scroll_izq.scroll_content

        nb_ejes = ttk.Notebook(f_izq)
        nb_ejes.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        # Pestaña 1: Medida / SMU
        f_tab_smu, self.btn_start, self.btn_stop = crear_panel_medida(
            nb_ejes, self.vars, self._iniciar_medida, self._abortar_medida
        )
        nb_ejes.add(f_tab_smu, text="1. SMU & Barrido I-V")

        # Pestaña 2: Eje Motor
        f_tab_motor = crear_panel_motor(nb_ejes, self.vars, self.evento_aborto)
        nb_ejes.add(f_tab_motor, text="2. Eje Motor")

        # Pestaña 3: Eje LEDs
        f_tab_led = crear_panel_led(nb_ejes, self.vars)
        nb_ejes.add(f_tab_led, text="3. Eje Iluminación")

        # Pestaña 4: Eje Estructura
        f_tab_est = crear_panel_estructura(nb_ejes, self.vars)
        nb_ejes.add(f_tab_est, text="4. Eje Estructura")

        # ---- PANEL DERECHO (Consola y Vista Previa) ----
        f_der = ttk.Frame(cuerpo, style="Window.TFrame")
        f_der.grid(row=0, column=1, sticky="nsew", padx=(ui(6), 0))
        f_der.rowconfigure(1, weight=1)
        f_der.columnconfigure(0, weight=1)

        # Header consola con badges de estado
        f_header_cons = ttk.Frame(f_der, style="Window.TFrame")
        f_header_cons.grid(row=0, column=0, sticky="ew", pady=(0, ui(4)))
        ttk.Label(f_header_cons, text="Consola de Ejecución", font=ui_font_label("bold"), style="Window.TLabel").pack(side="left")

        self.badge_estado = tk.Label(
            f_header_cons,
            text="Listo",
            bg=t["results"]["badge_ready_bg"],
            fg=t["results"]["badge_ready_fg"],
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            padx=ui(8), pady=ui(2),
        )
        self.badge_estado.pack(side="right")

        # Widget de texto de consola
        self.txt_consola = scrolledtext.ScrolledText(
            f_der,
            wrap="word",
            bg=t["results"]["bg_console"],
            fg=t["results"]["fg_console"],
            insertbackground=t["results"]["fg_console"],
            font=ui_font_console(),
            relief="flat",
            borderwidth=0,
        )
        self.txt_consola.grid(row=1, column=0, sticky="nsew", pady=(0, ui(6)))

        # Miniatura de gráfica previa
        self.lbl_grafica = ttk.Label(f_der, text="La vista previa de la curva I-V aparecerá aquí al medir.", anchor="center")
        self.lbl_grafica.grid(row=2, column=0, sticky="ew", pady=(0, ui(4)))

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

    def _recoger_configuracion(self) -> dict:
        cfg = copy.deepcopy(self.cfg_base)
        v = self.vars

        # SMU & IV
        cfg["recurso_visa"] = v["recurso_visa"].get().strip() or "AUTO"
        cfg["carpeta_salida"] = v["carpeta_salida"].get().strip()
        cfg["nombre_carpeta_medida"] = v["nombre_carpeta_medida"].get().strip()
        cfg["nombre_medida"] = v["nombre_medida"].get().strip()
        cfg["modo_medida"] = v["modo_medida"].get().strip()
        cfg["directa"]["v_inicial_mV"] = float(v["v_ini_dir"].get())
        cfg["directa"]["v_final_mV"] = float(v["v_fin_dir"].get())
        cfg["directa"]["paso_mV"] = float(v["paso_dir"].get())
        cfg["inversa"]["v_final_V"] = float(v["v_fin_inv"].get())
        cfg["inversa"]["paso_mV"] = float(v["paso_inv"].get())
        cfg["i_max_uA"] = float(v["i_max_uA"].get())
        cfg["i_max_A"] = cfg["i_max_uA"] * 1e-6
        cfg["superficie_um2"] = float(v["superficie_um2"].get()) if v["superficie_um2"].get().strip() else None
        cfg["irradiancia_mW_cm2"] = float(v["irradiancia_mW_cm2"].get()) if v["irradiancia_mW_cm2"].get().strip() else None
        cfg["invertir_eje_y_graficas"] = v["invertir_eje_y"].get()
        cfg["medir_tension_real"] = v["medir_tension_real"].get()
        cfg["relacion_ejes"] = v["relacion_ejes"].get()

        # Eje Motor
        cfg["barrido_motor_activo"] = v["barrido_motor_activo"].get()
        cfg["motor"]["puerto_serie"] = v["motor_puerto_serie"].get().strip()
        cfg["motor"]["step_pasos"] = int(v["motor_step_pasos"].get())
        cfg["motor"]["stop_pasos"] = int(v["motor_stop_pasos"].get())
        cfg["motor"]["resolucion_mm_paso"] = float(v["motor_resolucion_mm_paso"].get())
        cfg["motor"]["espera_estabilizacion_s"] = float(v["motor_espera_s"].get() or 0.0)

        # Eje LEDs
        cfg["simulador_solar_activo"] = v["simulador_solar_activo"].get()
        cfg["simulador_solar"]["puerto_serie"] = v["solar_puerto_serie"].get().strip()
        cfg["irradiancia_modo"] = v["irradiancia_modo"].get()
        cfg["irradiancia_potencia"]["p_inicial_mW_cm2"] = float(v["solar_p_ini"].get())
        cfg["irradiancia_potencia"]["p_final_mW_cm2"] = float(v["solar_p_fin"].get())
        cfg["irradiancia_potencia"]["paso_mW_cm2"] = float(v["solar_p_paso"].get())
        cfg["irradiancia_potencia"]["lista_potencias_custom"] = v["solar_p_custom"].get().strip() or None
        cfg["irradiancia_longitud_onda"]["canales_seleccionados"] = v["solar_canal_seleccionado"].get()
        cfg["irradiancia_longitud_onda"]["i_inicial_pct"] = float(v["solar_i_ini"].get())
        cfg["irradiancia_longitud_onda"]["i_final_pct"] = float(v["solar_i_fin"].get())
        cfg["irradiancia_longitud_onda"]["paso_pct"] = float(v["solar_i_paso"].get())
        cfg["irradiancia_combinacion"]["canales_combinacion"] = [
            {"canal": v["solar_comb_ch1"].get(), "intensidades": v["solar_comb_val1"].get()},
            {"canal": v["solar_comb_ch2"].get(), "intensidades": v["solar_comb_val2"].get()},
        ]

        # Eje Estructura
        cfg["eje_estructura_activo"] = v["eje_estructura_activo"].get()
        cfg["estructuras_disponibles"] = [
            x.strip() for x in v["estructuras_lista"].get().split(",") if x.strip()
        ]

        # Callbacks y eventos runtime
        cfg["evento_aborto"] = self.evento_aborto
        cfg["log_callback"] = self._log
        cfg["grafica_callback"] = self._actualizar_grafica
        return cfg

    def _iniciar_medida(self):
        if self.ejecutando:
            return
        try:
            cfg = self._recoger_configuracion()
            plan = generar_plan_estudio(cfg)
        except Exception as exc:
            mostrar_error("Configuración no válida", f"Error al generar el plan de medidas:\n{exc}")
            return

        self.ejecutando = True
        self.evento_aborto.clear()
        self.btn_start.configure(state="disabled")
        self._actualizar_estado("Midiendo...", "running")
        self._log("=" * 60)
        self._log(f"Iniciando secuencia Studio: {len(plan)} combinaciones a medir.")

        threading.Thread(target=self._hilo_ejecucion, args=(cfg, plan), daemon=True).start()

    def _abortar_medida(self):
        if not self.ejecutando:
            return
        self.evento_aborto.set()
        self._log("\n⏹ Solicitud de aborto recibida. Deteniendo hardware...")
        self._actualizar_estado("Abortando...", "abort")
        abortar_instrumento_activo()

    def _hilo_ejecucion(self, cfg, plan):
        ctrl_motor = None
        ctrl_solar = None
        ctrl_rele = None
        try:
            preparar_carpeta_medida(cfg)

            # Inicializar hardware de ejes activos
            if cfg.get("barrido_motor_activo", False):
                ctrl_motor = crear_controlador_motor(cfg, evento_aborto=self.evento_aborto)
                ctrl_motor.connect()
                registrar_motor_activo(ctrl_motor)
                self._log("✓ Motor lineal conectado.")

            if cfg.get("simulador_solar_activo", False):
                ctrl_solar = crear_controlador_simulador_solar(cfg, evento_aborto=self.evento_aborto)
                ctrl_solar.connect()
                registrar_simulador_solar_activo(ctrl_solar)
                self._log("✓ Simulador solar conectado.")

            if cfg.get("eje_estructura_activo", False):
                ctrl_rele = crear_rele_estructura(cfg, event=self.evento_aborto)
                self._log("✓ Relé de estructura preparado.")

            # Bucle de ejecución del plan
            for paso in plan:
                if self.evento_aborto.is_set():
                    raise MedidaAbortadaPorUsuario()

                idx = paso["indice"]
                total = paso["total_pasos"]
                self._log(f"\n--- [Paso {idx}/{total}] ---")

                # 1. Estructura
                if paso.get("estructura_activa") and paso.get("estructura"):
                    self._log(f"Seleccionando estructura: {paso['estructura']}")
                    # ctrl_rele.select(paso["estructura"])

                # 2. Motor
                if paso.get("motor_activo") and ctrl_motor:
                    pos = paso["posicion_motor_pasos"]
                    self._log(f"Moviendo motor a {pos} pasos ({paso['posicion_motor_mm']:.3f} mm)...")
                    ctrl_motor.move_absolute_steps(pos)
                    time.sleep(float(cfg["motor"].get("espera_estabilizacion_s", 0.0)))

                # 3. LEDs
                if paso.get("solar_modo") != "off" and ctrl_solar:
                    s_modo = paso["solar_modo"]
                    sparams = paso["solar_params"]
                    if s_modo == "potencia":
                        self._log(f"Ajustando potencia solar a {sparams['potencia_mW_cm2']} mW/cm²...")
                        ctrl_solar.establecer_potencia(sparams["potencia_mW_cm2"])
                    elif s_modo == "longitud_onda":
                        self._log(f"Ajustando canal {sparams['canal']} a {sparams['intensidad_pct']}%...")
                        ctrl_solar.establecer_canal(sparams["canal"], sparams["intensidad_pct"])
                    elif s_modo == "combinacion":
                        self._log(f"Ajustando combinación de canales: {sparams['canales']} -> {sparams['intensidades']}...")
                        ctrl_solar.establecer_combinacion_canales(sparams["canales"], sparams["intensidades"])
                    time.sleep(float(sparams.get("espera_estabilizacion_s", 3.0)))

                # 4. Medida atómica Keithley 2450
                cfg_paso = copy.deepcopy(cfg)
                cfg_paso["nombre_medida"] = f"{cfg['nombre_medida']}_p{idx:03d}"
                cfg_paso["posicion_motor_pasos"] = paso.get("posicion_motor_pasos")
                cfg_paso["posicion_motor_mm"] = paso.get("posicion_motor_mm")

                t_medida, df_datos, res_fv = run_keithley_atomic(cfg_paso)
                self._actualizar_grafica(df_datos, cfg_paso)

            self._log("\n✓ Secuencia completada con éxito.")
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
            # Apagar y liberar instrumentos
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
