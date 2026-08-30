import re
import time

from core.exceptions import ErrorRele, MedidaAbortadaPorUsuario
from core.instrument import registry


class RelayArduinoSerial:
    def __init__(self, cfg, event=None):
        self.cfg = cfg
        self.event = event
        self.serial = None

    def connect(self):
        try:
            import serial
        except ImportError as error:
            raise ErrorRele("Falta pyserial.") from error

        port = re.sub(r"\s+", "", str(self.cfg.get("puerto_serie", "")))
        if not port:
            raise ErrorRele("Configura el puerto COM del Arduino.")
        baudrate = int(self.cfg.get("baudrate", 115200))
        try:
            self.serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=0.15,
                write_timeout=2,
            )
            time.sleep(float(self.cfg.get("espera_arranque_arduino_s", 2)))
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            self.cmd("HELLO", ("OK RELAY_V1",), 3)
            self.off()
            registry.registrar("rele", self)
        except Exception as error:
            self.close()
            if isinstance(error, ErrorRele):
                raise
            raise ErrorRele(
                f"Arduino no respondió correctamente en {port} a {baudrate} baudios. "
                "Comprueba que tenga cargado relay_controller.ino y que el puerto esté libre."
            ) from error

    def cmd(self, command, valid_responses, timeout=None):
        if not self.serial or not self.serial.is_open:
            raise ErrorRele("Puerto serie no abierto.")
        self.serial.write((command.strip() + "\n").encode("ascii"))
        self.serial.flush()
        end = time.monotonic() + float(
            timeout or self.cfg.get("timeout_s", 3)
        )
        while time.monotonic() < end:
            if self.event and self.event.is_set():
                raise MedidaAbortadaPorUsuario()
            line = self.serial.readline().decode("ascii", errors="replace").strip()
            if line:
                self.cfg.get("log_callback", lambda _message: None)(
                    f"Arduino -> {line}"
                )
            if line.startswith("ERROR"):
                raise ErrorRele(line)
            if any(line.startswith(response) for response in valid_responses):
                return line
            if line:
                expected = ", ".join(valid_responses)
                raise ErrorRele(
                    f"Respuesta Arduino inesperada para {command}: {line!r}. "
                    f"Se esperaba: {expected}. Comprueba el firmware cargado."
                )
        raise ErrorRele(
            f"Timeout Arduino: {command}. No recibió una respuesta válida en "
            f"{self.serial.port} a {self.serial.baudrate} baudios."
        )

    def off(self):
        self.cmd("OFF ALL", ("OK OFF ALL",))

    def select(self, device):
        device = device.upper()
        if device not in "AB":
            raise ErrorRele("Estructura inválida.")
        command = f"SELECT {device}"
        try:
            self.cmd(command, (f"OK SELECT {device}",))
        except ErrorRele as error:
            raise ErrorRele(f"Fallo al ejecutar {command}: {error}") from error
        deadline = time.monotonic() + float(self.cfg.get("espera_tras_conmutacion_s", 0.5))
        while time.monotonic() < deadline:
            if self.event and self.event.is_set():
                raise MedidaAbortadaPorUsuario()
            time.sleep(min(0.05, deadline - time.monotonic()))

    def status(self):
        numbers = re.findall(r"\d+", self.cmd("STATUS?", ("STATUS",)))
        if len(numbers) != 2:
            raise ErrorRele("STATUS inválido.")
        return tuple(map(int, numbers))

    def test(self):
        result = {}
        for device in "AB":
            try:
                self.select(device)
                result[device] = self.status()
            except ErrorRele as error:
                raise ErrorRele(f"Error comprobando estructura {device}: {error}") from error
            expected = (0, 0) if device == "A" else (1, 1)
            if result[device] != expected:
                raise ErrorRele(
                    f"Estado {result[device]}, esperado {expected}."
                )
        self.off()
        if self.status() != (0, 0):
            raise ErrorRele("Los relés no quedaron apagados.")
        return result

    def stop(self):
        try:
            self.off()
        except Exception:
            pass

    def close(self):
        self.stop()
        registry.limpiar("rele", self)
        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass
