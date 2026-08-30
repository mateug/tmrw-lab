"""Panel de configuración de Ejes Motor para Studio.

Incluye sub-pestañas para cada motor disponible, soporte para simulación solar
durante el movimiento y controles interactivos de centrado manual continuo.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import ttk

from core.instrument.motors.motor_lineal import crear_controlador_motor
from core.instrument.registry import registrar_motor_activo, limpiar_motor_activo
from core.ui_kit.scaler import ui, ui_font, ui_font_label, UIConfig
from core.ui_kit.shared import crear_seccion_frame, mostrar_error, mostrar_info
from core.ui_kit.theme import theme_mgr


class PanelEjesMotor(ttk.Frame):
    """Panel de configuración y centrado de los ejes de motor."""

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

    def __init__(self, parent, vars_dict, evento_aborto, **kwargs):
        super().__init__(parent, **kwargs)
        self.vars = vars_dict
        self.evento_aborto = evento_aborto
        self._centrado_hilo = None
        self._centrado_activo = False
        self._build()

    def _build(self):
        t = theme_mgr.get_current_theme()
        self.configure(style="Window.TFrame")

        f_sec = crear_seccion_frame(self, "Ejes Motor — Control Espacial de Posición", "params")
        f_sec.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        # Toggle activar eje motor general
        f_top = ttk.Frame(f_sec, style="Window.TFrame")
        f_top.pack(fill="x", padx=ui(6), pady=ui(3))

        ttk.Checkbutton(
            f_top,
            text="Activar eje de motor en la secuencia de medidas",
            variable=self.vars["barrido_motor_activo"],
        ).pack(side="left")

        # Sub-Notebook para soportar múltiples motores
        nb_motores = ttk.Notebook(f_sec)
        nb_motores.pack(fill="both", expand=True, padx=ui(4), pady=ui(4))

        # ── Sub-pestaña 1: Motor Lineal 1 (Eje X) ────────────────────────────
        f_m1 = ttk.Frame(nb_motores, style="Window.TFrame")
        nb_motores.add(f_m1, text="Motor Lineal 1 (Eje X)")
        self._build_motor_lineal_1(f_m1)

    def _build_motor_lineal_1(self, parent):
        t = theme_mgr.get_current_theme()

        # 1. Conexión y Parámetros cinemáticos
        f_params = ttk.LabelFrame(parent, text=" Parámetros de Barrido Lineal ", padding=ui(6))
        f_params.pack(fill="x", padx=ui(4), pady=ui(4))

        f_p1 = ttk.Frame(f_params, style="Window.TFrame")
        f_p1.pack(fill="x", pady=ui(2))
        ttk.Label(f_p1, text="Puerto COM:").pack(side="left")
        ttk.Entry(f_p1, textvariable=self.vars["motor_puerto_serie"], width=8).pack(side="left", padx=(ui(2), ui(12)))
        ttk.Label(f_p1, text="Baudrate:").pack(side="left")
        ttk.Entry(f_p1, textvariable=self.vars["motor_baudrate"], width=10).pack(side="left", padx=(ui(2), ui(12)))

        f_p2 = ttk.Frame(f_params, style="Window.TFrame")
        f_p2.pack(fill="x", pady=ui(3))
        ttk.Label(f_p2, text="Step (pasos):").pack(side="left")
        ttk.Entry(f_p2, textvariable=self.vars["motor_step_pasos"], width=10).pack(side="left", padx=(ui(2), ui(10)))
        ttk.Label(f_p2, text="Stop (pasos):").pack(side="left")
        ttk.Entry(f_p2, textvariable=self.vars["motor_stop_pasos"], width=10).pack(side="left", padx=(ui(2), ui(10)))
        ttk.Label(f_p2, text="Resolución (mm/paso):").pack(side="left")
        ttk.Entry(f_p2, textvariable=self.vars["motor_resolucion_mm_paso"], width=10).pack(side="left", padx=(ui(2), ui(10)))
        ttk.Label(f_p2, text="Espera estabilización (s):").pack(side="left")
        ttk.Entry(f_p2, textvariable=self.vars["motor_espera_s"], width=8).pack(side="left", padx=(ui(2), ui(6)))

        f_p3 = ttk.Frame(f_params, style="Window.TFrame")
        f_p3.pack(fill="x", pady=ui(2))
        ttk.Checkbutton(f_p3, text="Poner a cero al conectar", variable=self.vars["motor_poner_cero_conectar"]).pack(side="left", padx=(0, ui(14)))
        ttk.Checkbutton(f_p3, text="Volver a cero al finalizar", variable=self.vars["motor_volver_cero_final"]).pack(side="left", padx=ui(14))

        # 2. Simulador Solar integrado durante el barrido de motor
        lf_solar = ttk.LabelFrame(parent, text=" Simulador Solar para Medidas Motorizadas ", padding=ui(6))
        lf_solar.pack(fill="x", padx=ui(4), pady=ui(4))

        f_s1 = ttk.Frame(lf_solar, style="Window.TFrame")
        f_s1.pack(fill="x", pady=ui(2))
        ttk.Label(f_s1, text="Puerto COM Ossila:").pack(side="left")
        ttk.Entry(f_s1, textvariable=self.vars["motor_solar_puerto"], width=8).pack(side="left", padx=(ui(2), ui(14)))
        ttk.Label(f_s1, text="Baudrate:").pack(side="left")
        ttk.Entry(f_s1, textvariable=self.vars["motor_solar_baudrate"], width=10).pack(side="left", padx=(ui(2), ui(12)))

        f_s2 = ttk.Frame(lf_solar, style="Window.TFrame")
        f_s2.pack(fill="x", pady=ui(2))
        ttk.Label(f_s2, text="Modo luz:").pack(side="left")
        for txt, val in [("Desactivado", "off"), ("Irradiancia (mW/cm²)", "potencia"), ("Longitud de onda", "longitud_onda")]:
            ttk.Radiobutton(f_s2, text=txt, variable=self.vars["motor_solar_modo"], value=val, command=self._actualizar_ui_solar_motor).pack(side="left", padx=ui(6))

        f_s3 = ttk.Frame(lf_solar, style="Window.TFrame")
        f_s3.pack(fill="x", pady=ui(2))
        ttk.Label(f_s3, text="Irradiancia objetivo (mW/cm²):").pack(side="left")
        self.entry_mot_pot = ttk.Entry(f_s3, textvariable=self.vars["motor_solar_potencia"], width=8)
        self.entry_mot_pot.pack(side="left", padx=(ui(2), ui(14)))
        ttk.Label(f_s3, text="Tiempo luz encendida hasta medir (s):").pack(side="left")
        ttk.Entry(f_s3, textvariable=self.vars["motor_espera_luz"], width=8).pack(side="left", padx=(ui(2), ui(10)))

        f_s4 = ttk.Frame(lf_solar, style="Window.TFrame")
        f_s4.pack(fill="x", pady=ui(2))
        ttk.Label(f_s4, text="Canal / Longitud de onda:").pack(side="left")
        self.cb_mot_ch = ttk.Combobox(
            f_s4, textvariable=self.vars["motor_solar_longitud_onda"],
            values=[d for d, _ in self.SOLAR_CANALES], state="readonly", width=14,
        )
        self.cb_mot_ch.pack(side="left", padx=(ui(2), ui(14)))
        ttk.Label(f_s4, text="Intensidad (%):").pack(side="left")
        self.entry_mot_intens = ttk.Entry(f_s4, textvariable=self.vars["motor_solar_intensidad_pct"], width=8)
        self.entry_mot_intens.pack(side="left", padx=(ui(2), ui(10)))

        self._actualizar_ui_solar_motor()

        # 3. Acciones Manuales de Centrado y Jogging
        f_centrado = ttk.LabelFrame(parent, text=" Acciones Manuales de Centrado y Posición ", padding=ui(6))
        f_centrado.pack(fill="x", padx=ui(4), pady=ui(4))

        f_c1 = ttk.Frame(f_centrado, style="Window.TFrame")
        f_c1.pack(fill="x", pady=ui(2))

        ttk.Label(f_c1, text="Pasos:").pack(side="left", padx=(0, ui(4)))
        ttk.Entry(f_c1, textvariable=self.vars["motor_manual_pasos"], width=10).pack(side="left", padx=(0, ui(6)))
        ttk.Button(f_c1, text="Mover pasos exactos", command=self._on_mover_pasos_exactos).pack(side="left", padx=(0, ui(10)))

        btn_menos = ttk.Button(f_c1, text="◄ -Mover Continuo")
        btn_menos.pack(side="left", padx=ui(3))
        btn_menos.bind("<ButtonPress-1>", lambda e: self._iniciar_centrado_continuo(-1))
        btn_menos.bind("<ButtonRelease-1>", lambda e: self._detener_centrado_continuo())
        btn_menos.bind("<Leave>", lambda e: self._detener_centrado_continuo())

        ttk.Button(f_c1, text="📍 Fijar Cero Actual", command=self._on_fijar_cero).pack(side="left", padx=ui(8))

        btn_mas = ttk.Button(f_c1, text="+Mover Continuo ►")
        btn_mas.pack(side="left", padx=ui(3))
        btn_mas.bind("<ButtonPress-1>", lambda e: self._iniciar_centrado_continuo(+1))
        btn_mas.bind("<ButtonRelease-1>", lambda e: self._detener_centrado_continuo())
        btn_mas.bind("<Leave>", lambda e: self._detener_centrado_continuo())

    def _actualizar_ui_solar_motor(self):
        modo = self.vars["motor_solar_modo"].get()
        if modo == "potencia":
            self.entry_mot_pot.configure(state="normal")
            self.cb_mot_ch.configure(state="disabled")
            self.entry_mot_intens.configure(state="disabled")
        elif modo == "longitud_onda":
            self.entry_mot_pot.configure(state="disabled")
            self.cb_mot_ch.configure(state="readonly")
            self.entry_mot_intens.configure(state="normal")
        else:
            self.entry_mot_pot.configure(state="disabled")
            self.cb_mot_ch.configure(state="disabled")
            self.entry_mot_intens.configure(state="disabled")

    def _ejecutar_accion_motor(self, accion_fn):
        def _hilo():
            cfg_motor = {
                "motor": {
                    "puerto_serie": self.vars["motor_puerto_serie"].get().strip(),
                    "baudrate": int(self.vars["motor_baudrate"].get() or 115200),
                    "resolucion_mm_paso": float(self.vars["motor_resolucion_mm_paso"].get() or 0.00128),
                    "pasos_por_segundo_motor": 50.0,
                    "margen_timeout_movimiento_s": 8.0,
                    "timeout_s": 120.0,
                    "poner_cero_al_conectar": False,
                }
            }
            ctrl = None
            try:
                ctrl = crear_controlador_motor(cfg_motor, evento_aborto=self.evento_aborto)
                ctrl.connect()
                registrar_motor_activo(ctrl)
                accion_fn(ctrl)
            except Exception as exc:
                mostrar_error("Error Motor", f"Fallo al comunicar con motor:\n{exc}")
            finally:
                if ctrl:
                    ctrl.close()
                limpiar_motor_activo(ctrl)

        threading.Thread(target=_hilo, daemon=True).start()

    def _on_fijar_cero(self):
        def _accion(ctrl):
            pos = ctrl.zero()
            mostrar_info("Motor", f"Posición actual fijada como CERO (0 pasos / {pos} mm).")
        self._ejecutar_accion_motor(_accion)

    def _on_mover_pasos_exactos(self):
        try:
            pasos = int(self.vars["motor_manual_pasos"].get())
        except ValueError:
            mostrar_error("Error", "Introduce un número entero de pasos válido.")
            return

        def _accion(ctrl):
            ctrl.move_relative_steps(pasos)
        self._ejecutar_accion_motor(_accion)

    def _iniciar_centrado_continuo(self, direccion):
        self._centrado_activo = True
        try:
            pasos_por_pulso = abs(int(self.vars["motor_manual_pasos"].get() or 5)) * direccion
        except Exception:
            pasos_por_pulso = 5 * direccion

        def _bucle_centrado():
            cfg_motor = {
                "motor": {
                    "puerto_serie": self.vars["motor_puerto_serie"].get().strip(),
                    "baudrate": int(self.vars["motor_baudrate"].get() or 115200),
                    "resolucion_mm_paso": float(self.vars["motor_resolucion_mm_paso"].get() or 0.00128),
                    "pasos_por_segundo_motor": 50.0,
                    "margen_timeout_movimiento_s": 8.0,
                    "timeout_s": 120.0,
                    "poner_cero_al_conectar": False,
                }
            }
            ctrl = None
            try:
                ctrl = crear_controlador_motor(cfg_motor, evento_aborto=self.evento_aborto)
                ctrl.connect()
                registrar_motor_activo(ctrl)
                while self._centrado_activo and not self.evento_aborto.is_set():
                    ctrl.move_relative_steps(pasos_por_pulso)
                    time.sleep(0.08)
            except Exception:
                pass
            finally:
                if ctrl:
                    ctrl.close()
                limpiar_motor_activo(ctrl)

        self._centrado_hilo = threading.Thread(target=_bucle_centrado, daemon=True)
        self._centrado_hilo.start()

    def _detener_centrado_continuo(self):
        self._centrado_activo = False


def crear_panel_motor(parent, vars_dict, evento_aborto):
    return PanelEjesMotor(parent, vars_dict, evento_aborto)
