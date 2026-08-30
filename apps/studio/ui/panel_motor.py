"""Panel de configuración del eje de motor(es) para Studio."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core.ui_kit.scaler import ui, ui_font_label
from core.ui_kit.shared import crear_seccion_frame, mostrar_error, mostrar_info
from core.instrument.motors.motor_lineal import crear_controlador_motor
from core.instrument.registry import registrar_motor_activo, limpiar_motor_activo


def crear_panel_motor(parent, vars_dict, evento_aborto):
    """Crea el panel de control y barrido del eje de motor."""
    f_main = ttk.Frame(parent, style="Window.TFrame")

    f_sec = crear_seccion_frame(f_main, "Eje de Movimiento — Motor Lineal", "params")
    f_sec.pack(fill="x", padx=ui(6), pady=ui(4))

    # Toggle activar eje
    f_act = ttk.Frame(f_sec, style="Window.TFrame")
    f_act.pack(fill="x", padx=ui(6), pady=ui(4))
    cb_act = ttk.Checkbutton(
        f_act,
        text="Activar eje de motor en la secuencia",
        variable=vars_dict["barrido_motor_activo"],
        style="Window.TCheckbutton",
    )
    cb_act.pack(side="left")

    # Driver selector (preparado para múltiples motores)
    ttk.Label(f_act, text="Controlador:", style="Window.TLabel").pack(side="left", padx=(ui(20), ui(4)))
    cb_driver = ttk.Combobox(
        f_act,
        values=["motor_lineal (Arduino Serial)"],
        state="readonly",
        width=26,
    )
    cb_driver.current(0)
    cb_driver.pack(side="left")

    # Parámetros del barrido motor
    f_grid = ttk.Frame(f_sec, style="Window.TFrame")
    f_grid.pack(fill="x", padx=ui(6), pady=ui(4))

    params = [
        ("Puerto COM Arduino:", "motor_puerto_serie", 12),
        ("Step (pasos):", "motor_step_pasos", 10),
        ("Stop (pasos):", "motor_stop_pasos", 10),
        ("Resolución (mm/paso):", "motor_resolucion_mm_paso", 12),
        ("Espera estabilización (s):", "motor_espera_s", 10),
        ("Baudrate:", "motor_baudrate", 10),
    ]

    for idx, (lbl, var_name, width) in enumerate(params):
        r = idx // 3
        c = (idx % 3) * 2
        ttk.Label(f_grid, text=lbl, style="Window.TLabel").grid(row=r, column=c, sticky="w", padx=ui(4), pady=ui(3))
        ttk.Entry(f_grid, textvariable=vars_dict[var_name], width=width).grid(row=r, column=c + 1, sticky="w", padx=ui(4), pady=ui(3))

    # Botonera de control manual y puesta a cero
    f_manual = ttk.LabelFrame(f_sec, text="Control Manual y Calibración")
    f_manual.pack(fill="x", padx=ui(6), pady=ui(6))

    def _ejecutar_accion_motor(accion_fn):
        def _hilo():
            cfg_motor = {
                "motor": {
                    "puerto_serie": vars_dict["motor_puerto_serie"].get(),
                    "baudrate": int(vars_dict["motor_baudrate"].get() or 115200),
                    "resolucion_mm_paso": float(vars_dict["motor_resolucion_mm_paso"].get() or 0.00128),
                    "pasos_por_segundo_motor": 50.0,
                    "margen_timeout_movimiento_s": 8.0,
                    "timeout_s": 120.0,
                    "poner_cero_al_conectar": False,
                }
            }
            ctrl = None
            try:
                ctrl = crear_controlador_motor(cfg_motor, evento_aborto=evento_aborto)
                ctrl.connect()
                registrar_motor_activo(ctrl)
                accion_fn(ctrl)
            except Exception as exc:
                mostrar_error("Error Motor", f"Fallo al mover motor:\n{exc}")
            finally:
                if ctrl:
                    ctrl.close()
                limpiar_motor_activo(ctrl)

        threading.Thread(target=_hilo, daemon=True).start()

    def _poner_cero():
        def _accion(ctrl):
            pos = ctrl.zero()
            mostrar_info("Motor", f"Posición puesta a cero (0 pasos, {pos} confirmado).")
        _ejecutar_accion_motor(_accion)

    def _mover_relativo(pasos):
        def _accion(ctrl):
            ctrl.move_relative_steps(pasos)
        _ejecutar_accion_motor(_accion)

    ttk.Button(f_manual, text="Poner CERO actual", command=_poner_cero).pack(side="left", padx=ui(4), pady=ui(4))
    ttk.Button(f_manual, text="◄ -100 pasos", command=lambda: _mover_relativo(-100)).pack(side="left", padx=ui(2), pady=ui(4))
    ttk.Button(f_manual, text="◄ -10 pasos", command=lambda: _mover_relativo(-10)).pack(side="left", padx=ui(2), pady=ui(4))
    ttk.Button(f_manual, text="+10 pasos ►", command=lambda: _mover_relativo(10)).pack(side="left", padx=ui(2), pady=ui(4))
    ttk.Button(f_manual, text="+100 pasos ►", command=lambda: _mover_relativo(100)).pack(side="left", padx=ui(2), pady=ui(4))

    return f_main
