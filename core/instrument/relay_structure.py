"""Relé de selección de estructura para Studio/Lite.

Implementa la conmutación por serial del Arduino paralelo que soporta:
    HELLO
    OFF ALL
    SELECT A..G
    STATUS?

La selección se hace una estructura a la vez, siguiendo el orden solicitado
por Studio: fijar motor, fijar LED, elegir estructura y medir.
"""
import re
import time

from core.exceptions import ErrorRele, MedidaAbortadaPorUsuario
from core.instrument import registry


class RelayEstructuraArduinoSerial:
    """Controlador del relé paralelo de estructuras."""

    def __init__(self, cfg, event=None):
        self.cfg = cfg or {}
        self.event = event
        self.serial = None

    @staticmethod
    def _normalizar_nombre(nombre: str) -> str:
        texto = str(nombre).strip()
        if not texto:
            raise ErrorRele("Nombre de estructura vacío.")
        return texto

    def _mapear_estructura_a_letra(self, nombre: str) -> str:
        nombre = self._normalizar_nombre(nombre)
        estructuras = self.cfg.get("estructuras") or [
            "Estructura 1", "Estructura 2", "Estructura 3", "Estructura 4",
            "Estructura 5", "Estructura 6", "Estructura 7",
        ]
        try:
            idx = [str(item) for item in estructuras].index(nombre)
        except ValueError as exc:
            raise ErrorRele(f"La estructura '{nombre}' no está configurada en el relé.") from exc
        if idx < 0 or idx >= 7:
            raise ErrorRele(f"La estructura '{nombre}' queda fuera del rango soportado por el relé (A..G).")
        return chr(ord("A") + idx)

    def connect(self):
        try:
            import serial
        except ImportError as exc:
            raise ErrorRele("Falta pyserial para controlar el relé de estructura.") from exc

        port = re.sub(r"\s+", "", str(self.cfg.get("puerto_serie", "")))
        if not port:
            raise ErrorRele("Configura el puerto COM del relé de estructura.")

        baudrate = int(self.cfg.get("baudrate", 115200))
        try:
            self.serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=float(self.cfg.get("timeout_s", 0.15)),
                write_timeout=2,
            )
            time.sleep(float(self.cfg.get("espera_arranque_arduino_s", 2)))
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.cmd("HELLO", ("OK RELAY_V1",), timeout_s=3)
            self.off()
            registry.registrar("rele", self)
        except Exception as exc:
            self.close()
            if isinstance(exc, ErrorRele):
                raise
            raise ErrorRele(
                f"Arduino no respondió correctamente en {port} ({baudrate} baudios). "
                "Comprueba que el firmware con relay_controller_parallel.ino esté cargado."
            ) from exc

    def cmd(self, command, valid_responses, timeout_s=None):
        if not self.serial or not self.serial.is_open:
            raise ErrorRele("El puerto serie del relé no está abierto.")

        self.serial.write((str(command).strip() + "\n").encode("ascii"))
        self.serial.flush()

        deadline = time.monotonic() + float(timeout_s if timeout_s is not None else self.cfg.get("timeout_s", 3.0))
        while time.monotonic() < deadline:
            if self.event is not None and self.event.is_set():
                raise MedidaAbortadaPorUsuario("Selección de estructura abortada por el usuario.")
            linea = self.serial.readline().decode("ascii", errors="replace").strip()
            if linea:
                if linea.startswith("ERROR"):
                    raise ErrorRele(linea)
                if any(linea.startswith(prefijo) for prefijo in valid_responses):
                    return linea
                raise ErrorRele(
                    f"Respuesta Arduino inesperada para {command}: {linea!r}. "
                    f"Se esperaba: {', '.join(valid_responses)}."
                )
        raise ErrorRele(f"Timeout Arduino: {command}. No recibió respuesta válida en el relé de estructura.")

    def select(self, nombre: str):
        if self.serial is None or not self.serial.is_open:
            raise ErrorRele("El relé de estructura no está conectado.")
        letra = self._mapear_estructura_a_letra(nombre)
        command = f"SELECT {letra}"
        try:
            self.cmd(command, (f"OK {command}",), timeout_s=float(self.cfg.get("timeout_s", 3.0)))
        except ErrorRele as exc:
            raise ErrorRele(f"Fallo al ejecutar {command}: {exc}") from exc

        espera = float(self.cfg.get("espera_estabilizacion_s", self.cfg.get("espera_tras_conmutacion_s", 0.5)))
        fin = time.monotonic() + espera
        while time.monotonic() < fin:
            if self.event is not None and self.event.is_set():
                raise MedidaAbortadaPorUsuario("Conmutación del relé abortada por el usuario.")
            time.sleep(min(0.05, max(0.0, fin - time.monotonic())))
        return letra

    def off(self):
        if self.serial is None or not self.serial.is_open:
            return
        self.cmd("OFF ALL", ("OK OFF ALL",), timeout_s=float(self.cfg.get("timeout_s", 3.0)))

    def status(self):
        if self.serial is None or not self.serial.is_open:
            raise ErrorRele("El relé de estructura no está conectado.")
        linea = self.cmd("STATUS?", ("STATUS",), timeout_s=float(self.cfg.get("timeout_s", 3.0)))
        valores = re.findall(r"\d+", linea)
        return tuple(int(v) for v in valores)

    def stop(self):
        try:
            self.off()
        except Exception:
            pass

    def close(self):
        self.stop()
        registry.limpiar("rele", self)
        if self.serial is not None:
            try:
                self.serial.close()
            except Exception:
                pass
        self.serial = None


RelayEstructura = RelayEstructuraArduinoSerial


def crear_rele_estructura(cfg, event=None) -> RelayEstructuraArduinoSerial:
    """Factoría: devuelve el controlador del relé de estructura."""
    estructura_cfg = cfg.get("estructura", {})
    config = {**estructura_cfg, **cfg.get("rele_estructura", {})}
    return RelayEstructuraArduinoSerial(config, event=event)
