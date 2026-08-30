"""Motor lineal Arduino-Serial — portado desde iv-maker/src/instrument/motor.py.

Carpeta motors/ preparada para futuros grados de libertad adicionales.
Cada script expone su propia API: connect(), zero(), move_absolute_steps(),
move_relative_steps(), stop(), close().
"""
import re
import time

import numpy as np

from core.exceptions import MedidaAbortadaPorUsuario, ErrorMotor


class ControladorMotorBase:
    def __init__(self, cfg_motor, evento_aborto=None):
        self.cfg = cfg_motor
        self.evento_aborto = evento_aborto
        self.posicion_pasos = 0
        self.conectado = False

    def connect(self):
        raise NotImplementedError

    def zero(self):
        raise NotImplementedError

    def move_absolute_steps(self, posicion_pasos):
        raise NotImplementedError

    def move_relative_steps(self, desplazamiento_pasos):
        destino = int(self.posicion_pasos) + int(desplazamiento_pasos)
        return self.move_absolute_steps(destino)

    def stop(self):
        raise NotImplementedError

    def close(self):
        self.conectado = False

    def _comprobar_aborto(self):
        if self.evento_aborto is not None and self.evento_aborto.is_set():
            raise MedidaAbortadaPorUsuario("Barrido con motor abortado por el usuario.")


class MotorArduinoSerial(ControladorMotorBase):
    def __init__(self, cfg_motor, evento_aborto=None):
        super().__init__(cfg_motor, evento_aborto)
        self.serial = None

    def connect(self):
        try:
            import serial
        except ImportError as exc:
            raise ErrorMotor(
                "Falta la librería pyserial. Instálala con: pip install pyserial"
            ) from exc

        puerto_raw = str(self.cfg.get("puerto_serie", ""))
        puerto = re.sub(r"\s+", "", puerto_raw)
        if not puerto:
            raise ErrorMotor(
                "Configura el puerto del Arduino en cfg['motor']['puerto_serie']."
            )

        baudrate = int(self.cfg.get("baudrate", 115200))
        self.serial = serial.Serial(
            port=puerto,
            baudrate=baudrate,
            timeout=0.20,
            write_timeout=2.0,
        )
        time.sleep(2.0)
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

        ultimo_error = None
        for _ in range(3):
            try:
                self._orden("HELLO", respuestas=("OK",), timeout_s=3.0)
                ultimo_error = None
                break
            except ErrorMotor as exc:
                ultimo_error = exc
                time.sleep(0.5)

        if ultimo_error is not None:
            raise ErrorMotor(
                f"Arduino no respondió a HELLO en {puerto}. "
                "Comprueba el firmware y que el puerto esté libre."
            ) from ultimo_error

        self.conectado = True
        if self.cfg.get("poner_cero_al_conectar", True):
            self.zero()

    def _orden(self, texto, respuestas=("OK", "DONE"), timeout_s=None):
        if self.serial is None or not self.serial.is_open:
            raise ErrorMotor("El puerto serie del motor no está abierto.")

        self._comprobar_aborto()
        self.serial.write((texto.strip() + "\n").encode("ascii"))
        self.serial.flush()

        limite = time.monotonic() + float(
            self.cfg.get("timeout_s", 120.0) if timeout_s is None else timeout_s
        )

        while time.monotonic() < limite:
            if self.evento_aborto is not None and self.evento_aborto.is_set():
                try:
                    self.serial.write(b"STOP\n")
                    self.serial.flush()
                except Exception:
                    pass
                raise MedidaAbortadaPorUsuario("Movimiento del motor abortado por el usuario.")

            linea = self.serial.readline().decode("utf-8", errors="replace").strip()
            if not linea:
                continue
            if linea.startswith("ERROR"):
                raise ErrorMotor(linea)
            if any(linea.startswith(prefijo) for prefijo in respuestas):
                return linea

        raise ErrorMotor(
            f"Timeout esperando respuesta del motor a la orden: {texto}"
        )

    @staticmethod
    def _extraer_ultimo_entero(linea):
        numeros = re.findall(r"[-+]?\d+", linea)
        if not numeros:
            raise ErrorMotor(
                f"La respuesta del motor no contiene una posición: {linea!r}"
            )
        return int(numeros[-1])

    def zero(self):
        linea = self._orden("ZERO", respuestas=("OK",))
        self.posicion_pasos = self._extraer_ultimo_entero(linea)
        return self.posicion_pasos

    def move_absolute_steps(self, posicion_pasos):
        destino = int(posicion_pasos)
        desplazamiento = abs(destino - int(self.posicion_pasos))
        velocidad = max(float(self.cfg.get("pasos_por_segundo_motor", 50.0)), 1e-6)
        margen = max(float(self.cfg.get("margen_timeout_movimiento_s", 8.0)), 0.0)
        timeout_movimiento = max(5.0, desplazamiento / velocidad + margen)

        linea = self._orden(
            f"MOVE_ABS {destino}",
            respuestas=("DONE",),
            timeout_s=timeout_movimiento,
        )
        self.posicion_pasos = self._extraer_ultimo_entero(linea)
        return self.posicion_pasos

    def stop(self):
        if self.serial is None or not self.serial.is_open:
            return
        try:
            self.serial.write(b"STOP\n")
            self.serial.flush()
        except Exception:
            pass

    def close(self):
        try:
            self.stop()
        finally:
            if self.serial is not None:
                try:
                    self.serial.close()
                except Exception:
                    pass
            self.conectado = False


# ---------------------------------------------------------------------------
# Factoría y helpers de validación
# ---------------------------------------------------------------------------

def crear_controlador_motor(cfg, evento_aborto=None):
    cfg_motor = cfg["motor"]
    return MotorArduinoSerial(cfg_motor, evento_aborto=evento_aborto)


def _convertir_a_entero_exacto(valor, nombre):
    numero = float(valor)
    if not np.isfinite(numero) or not numero.is_integer():
        raise ValueError(f"{nombre} debe ser un número entero.")
    return int(numero)


def construir_barrido_pasos(step_pasos, stop_pasos):
    step = _convertir_a_entero_exacto(step_pasos, "Step")
    stop = _convertir_a_entero_exacto(stop_pasos, "Stop")

    if step == 0:
        raise ValueError("Step no puede ser 0.")
    if stop == 0:
        return np.array([0], dtype=np.int64)
    if (step > 0) != (stop > 0):
        raise ValueError(
            "Step y Stop deben tener el mismo signo."
        )
    if abs(stop) % abs(step) != 0:
        raise ValueError(
            "Stop debe ser múltiplo exacto de Step."
        )
    numero_intervalos = abs(stop) // abs(step)
    return np.arange(numero_intervalos + 1, dtype=np.int64) * step


def validar_configuracion_motor(cfg):
    if not cfg.get("barrido_motor_activo", False):
        return np.array([], dtype=np.int64)

    m = cfg["motor"]
    resolucion = float(m["resolucion_mm_paso"])
    espera = float(m.get("espera_estabilizacion_s", 0.5))

    if not np.isfinite(resolucion) or resolucion <= 0:
        raise ValueError("La Resolución debe ser mayor que 0 mm/paso.")
    if not np.isfinite(espera) or espera < 0:
        raise ValueError("La espera de estabilización no puede ser negativa.")

    posiciones = construir_barrido_pasos(m["step_pasos"], m["stop_pasos"])
    if posiciones.size > 10000:
        raise ValueError("El control motor supera 10000 posiciones. Revisa Step y Stop.")
    if not str(m.get("puerto_serie", "")).strip():
        raise ValueError("Configura el puerto COM en cfg['motor']['puerto_serie'].")

    return posiciones
