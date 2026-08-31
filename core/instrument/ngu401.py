"""Driver R&S NGU401 — portado desde devices-degradation.

Añade verificación *IDN? en connect(): si el instrumento detectado no es
un NGU401, se lanza ErrorSMU con un mensaje claro antes de medir.
"""
from __future__ import annotations

import numpy as np
import time
from dataclasses import dataclass
from typing import Any, Protocol, cast

from core.exceptions import ErrorSMU, MedidaAbortadaPorUsuario
from core.instrument import registry

MODELO_ESPERADO = "NGU401"
MIN_COMPLIANCE_A = 20e-6
READ_RANGES = np.array([10e-6, 1e-3, 10e-3, 100e-3, 3.0, 10.0])
PROG_RANGES = np.array([10e-3, 100e-3, 3.0, 8.0])


class VisaInstrument(Protocol):
    timeout: int
    write_termination: str
    read_termination: str

    def write(self, command: str) -> Any: ...
    def query(self, command: str) -> str: ...
    def close(self) -> Any: ...


def pick(value, ranges):
    candidates = ranges[ranges >= abs(float(value))]
    if not candidates.size:
        raise ErrorSMU("Rango NGU401 no disponible.")
    return float(candidates[0])


@dataclass
class LecturaVI:
    voltaje_V: float
    corriente_A: float


class NGU401:
    def __init__(self, cfg):
        self.cfg = cfg
        self.smu_cfg = cfg["smu"]
        self.rm: Any | None = None
        self.inst: VisaInstrument | None = None

    def _require_inst(self) -> VisaInstrument:
        if self.inst is None:
            raise ErrorSMU("El NGU401 no está conectado.")
        return self.inst

    def _w(self, command: str) -> None:
        self._require_inst().write(command)

    def _q(self, command: str) -> str:
        return self._require_inst().query(command).strip()

    def _opc(self, command):
        self._w(command)
        if self._q("*OPC?") != "1":
            raise ErrorSMU(f"*OPC? falló tras {command}")

    def _channel(self):
        self._w("INST OUT1")
        self._w("OUTP:SEL 1")

    def connect(self):
        try:
            import pyvisa
        except ImportError as error:
            raise ErrorSMU("Falta pyvisa.") from error

        self.rm = pyvisa.ResourceManager()
        resource = str(self.smu_cfg.get("recurso_visa", "AUTO")).strip()

        if resource and resource.upper() != "AUTO":
            self.inst = cast(VisaInstrument, self.rm.open_resource(resource))
        else:
            for candidate in self.rm.list_resources():
                try:
                    instrument = cast(
                        VisaInstrument,
                        self.rm.open_resource(candidate, open_timeout=2500),
                    )
                    instrument.write_termination = "\n"
                    instrument.read_termination = "\n"
                    if MODELO_ESPERADO in instrument.query("*IDN?").upper():
                        self.inst = instrument
                        break
                    instrument.close()
                except Exception:
                    pass

            if self.inst is None:
                raise ErrorSMU(
                    f"No se encontró un R&S {MODELO_ESPERADO} por VISA.\n"
                    "Este modo requiere: R&S NGU401."
                )

        instrument = self._require_inst()
        instrument.timeout = int(self.smu_cfg.get("timeout_ms", 60000))
        instrument.write_termination = "\n"
        instrument.read_termination = "\n"

        # Verificación explícita de modelo
        if self.smu_cfg.get("verificar_modelo", True):
            idn = self._q("*IDN?")
            if MODELO_ESPERADO not in idn.upper():
                try:
                    instrument.close()
                except Exception:
                    pass
                raise ErrorSMU(
                    f"El instrumento detectado no es un R&S {MODELO_ESPERADO}.\n"
                    f"  Esperado: modelo que contenga '{MODELO_ESPERADO}'\n"
                    f"  Encontrado: {idn!r}\n"
                    "Este modo requiere: R&S NGU401."
                )

        registry.registrar("smu", self)
        return self

    def initialize(self, limite_A=None, rango_lectura_A=None):
        limite = max(MIN_COMPLIANCE_A, abs(float(limite_A or self.cfg["i_max_A"])))
        lectura = pick(rango_lectura_A or self.cfg["rango_corriente_A"], READ_RANGES)
        programacion = pick(limite, PROG_RANGES)

        for command in ("*RST", "*CLS", "SYST:REM"):
            self._w(command)
        self._channel()
        self._w("OUTP:GEN 0")
        self._w("SOUR:PRI VOLT")
        self._w("VOLT 0")
        self._opc("SENS:CURR:RANG:AUTO 0")
        self._opc(f"SENS:CURR:RANG {lectura:.12g}")
        self._w(f"CURR:RANG {programacion:.12g}")
        self._w(f"CURR {limite:.12g}")
        self._w(f"CURR:NEG {-limite:.12g}")
        self._w("VOLT:RANG 20")
        self._opc("SENS:VOLT:RANG:AUTO 0")
        self._opc("SENS:VOLT:RANG 20")
        self._w(f"NPLC {self.cfg['nplc']:.12g}")
        if not self._q("SYST:ERR?").startswith("0"):
            raise ErrorSMU("Error SCPI al inicializar.")

    def liberar_control_manual(self) -> None:
        self.output_off()
        self._opc("SYST:LOC")

    def recuperar_control_automatico(self) -> None:
        self._opc("SYST:REM")

    def set_voltage(self, voltage):
        if not -20 <= float(voltage) <= 20:
            raise ErrorSMU("Tensión fuera de ±20 V.")
        self._w(f"VOLT {float(voltage):.12g}")

    def output_on(self):
        self._channel()
        self._w("OUTP:GEN 1")
        end = time.monotonic() + max(0.5, float(self.cfg["timeout_lectura_valida_s"]))
        while time.monotonic() < end:
            if self._q("OUTP? (@1)") in ("1", "1.0"):
                time.sleep(float(self.cfg["espera_tras_activar_s"]))
                return
            time.sleep(0.02)
        raise ErrorSMU("El NGU401 no confirmó la salida.")

    def output_off(self):
        try:
            self._channel()
            self._w("VOLT 0")
            self._w("OUTP:GEN 0")
        except Exception:
            pass

    def read_vi(self):
        end = time.monotonic() + float(self.cfg["timeout_lectura_valida_s"])
        last_response = ""
        while time.monotonic() < end:
            last_response = self._q("READ? (@1)")
            values = np.fromstring(last_response, sep=",")
            if (
                values.size >= 2
                and np.isfinite(values[0])
                and np.isfinite(values[1])
            ):
                return LecturaVI(float(values[0]), float(values[1]))
            time.sleep(float(self.cfg["intervalo_reintento_lectura_s"]))
        raise ErrorSMU(f"READ? inválido: {last_response}")

    def measure_segment(self, voltages, event=None):
        readings = []
        self.output_on()
        try:
            for indice, voltage in enumerate(voltages):
                if event and event.is_set():
                    raise MedidaAbortadaPorUsuario()

                self.set_voltage(voltage)
                delay = max(
                    float(self.cfg["delay_estabilizacion_s"]),
                    float(self.cfg["nplc"]) / float(self.cfg["frecuencia_red_Hz"])
                    + float(self.cfg["margen_lectura_s"]),
                )
                if indice == 0:
                    delay += float(self.cfg.get("delay_primer_punto_s", 0.0))
                time.sleep(delay)

                for _ in range(max(0, int(self.cfg.get("lecturas_descartables_por_punto", 1)))):
                    self.read_vi()
                    time.sleep(max(0.0, float(self.cfg.get("espera_entre_lecturas_s", 0.02))))

                readings.append(self.read_vi())
            return readings
        finally:
            self.output_off()

    def go_to_local(self):
        """Devuelve el control manual al panel frontal del NGU401."""
        if hasattr(self.inst, "control_ren"):
            for mode in (2, 6, 0):
                try:
                    self.inst.control_ren(mode)
                    return
                except Exception:
                    pass

    def stop(self):
        self.output_off()

    def close(self):
        self.output_off()
        registry.limpiar("smu", self)
        for resource in (self.inst, self.rm):
            try:
                if resource:
                    resource.close()
            except Exception:
                pass


def connect_ngu401(resource_name: str, timeout_ms: int = 5000) -> NGU401:
    """Crea y conecta una instancia del SMU R&S NGU401."""
    inst = NGU401(resource_name, timeout_ms)
    inst.connect()
    return inst


def close_ngu401(inst: NGU401 | None) -> None:
    """Cierra de forma segura el SMU NGU401."""
    if inst is not None:
        inst.close()


def liberar_control_manual_ngu401(resource_name: str, timeout_ms: int = 5000) -> None:
    """Libera el NGU401 permitiendo el control manual en su pantalla."""
    if not resource_name:
        return
    inst = None
    try:
        inst = NGU401(resource_name, timeout_ms)
        inst.connect()
        inst.go_to_local()
    finally:
        if inst:
            inst.close()


def recuperar_control_automatico_ngu401(resource_name: str, timeout_ms: int = 5000) -> None:
    """Recupera el control automático SCPI sobre el NGU401."""
    if not resource_name:
        return
    inst = None
    try:
        inst = NGU401(resource_name, timeout_ms)
        inst.connect()
    finally:
        if inst:
            inst.close()

