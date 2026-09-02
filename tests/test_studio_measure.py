import queue
import unittest
from unittest.mock import patch

from apps.studio.ui.frame import StudioFrame
from apps.lite.ui.panel import LiteFrame
from core.instrument.keithley import (
    liberar_control_manual_keithley,
    recuperar_control_automatico_keithley,
)


class FakeInstrument:
    def __init__(self):
        self.timeout = None
        self.write_termination = None
        self.read_termination = None
        self.writes = []
        self.closed = False

    def write(self, command):
        self.writes.append(command)

    def close(self):
        self.closed = True


class FakeText:
    def __init__(self):
        self.messages = []

    def insert(self, _position, message):
        self.messages.append(message)

    def see(self, _position):
        pass


class StudioMeasureTests(unittest.TestCase):
    def setUp(self):
        self.frame = StudioFrame.__new__(StudioFrame)
        self.frame.cola_ui = queue.Queue()

    def test_configura_medida_por_estructura_y_callbacks(self):
        cfg = {
            "recurso_visa": "GPIB0::1::INSTR",
            "modo_medida": "directa",
            "i_max_uA": 10.0,
            "directa": {"v_inicial_mV": 0.0, "v_final_mV": 500.0, "paso_mV": 20.0},
            "inversa": {"v_final_V": -1.0, "paso_mV": 20.0},
            "invertir_eje_y_graficas": False,
            "estructura": {
                "estructuras": ["Celda A"],
                "keithley_por_estructura": {},
            },
        }
        local = self.frame._configurar_medida_estructura(
            cfg,
            "Celda A",
            {
                "modo_medida": "completa",
                "i_max_uA": 25.0,
                "v_inicial_mV": 10.0,
                "v_final_mV": 610.0,
                "paso_mV": 15.0,
                "v_final_inversa_V": -2.5,
                "paso_inversa_mV": 30.0,
                "invertir_eje_y": True,
            },
        )

        self.assertEqual(local["recurso_visa"], "GPIB0::1::INSTR")
        self.assertEqual(local["modo_medida"], "completa")
        self.assertEqual(local["directa"]["paso_mV"], 15.0)
        self.assertEqual(local["inversa"]["v_final_V"], -2.5)
        self.assertEqual(local["inversa"]["paso_mV"], 30.0)
        self.assertTrue(callable(local["log_callback"]))
        self.assertTrue(callable(local["grafica_callback"]))

        local["log_callback"]("mensaje")
        local["grafica_callback"]("datos", local)
        self.assertEqual(self.frame.cola_ui.get(), ("log", "mensaje"))
        self.assertEqual(self.frame.cola_ui.get(), ("grafica", ("datos", local)))

    @patch("core.instrument.keithley.enviar_go_to_local_visa")
    @patch("core.instrument.keithley.conectar_y_verificar")
    def test_liberar_manual_usa_detector_con_auto(self, conectar, go_local):
        instrumento = FakeInstrument()
        conectar.return_value = instrumento

        liberar_control_manual_keithley("AUTO")

        conectar.assert_called_once_with("AUTO", timeout_ms=5000)
        go_local.assert_called_once_with(instrumento)
        self.assertEqual(instrumento.writes, [":ABOR", ":SYST:ACC FULL", ":DISP:CLE"])
        self.assertTrue(instrumento.closed)

    @patch("core.instrument.keithley.enviar_go_to_remote_visa")
    @patch("core.instrument.keithley.conectar_y_verificar")
    def test_recuperar_automatico_usa_detector_y_control_remoto(self, conectar, go_remote):
        instrumento = FakeInstrument()
        conectar.return_value = instrumento
        go_remote.return_value = True

        recuperar_control_automatico_keithley("AUTO")

        conectar.assert_called_once_with("AUTO", timeout_ms=5000)
        go_remote.assert_called_once_with(instrumento)
        self.assertTrue(instrumento.closed)

    @patch("apps.lite.ui.panel.mostrar_info")
    def test_lite_avisa_si_se_intenta_ejecutar_en_manual(self, mostrar_info_mock):
        frame = LiteFrame.__new__(LiteFrame)
        frame.modo_automatico = False
        frame.txt_log = FakeText()

        self.assertFalse(frame._comprobar_modo_automatico())
        self.assertIn("modo manual", frame.txt_log.messages[0].lower())
        mostrar_info_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
