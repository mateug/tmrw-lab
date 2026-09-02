"""Comprobación y test de hardware (relés y NGU401) para Stress."""
from apps.stress.relay_degradation import RelayArduinoSerial
from core.instrument.ngu401 import NGU401
from core.exceptions import ErrorRele, ErrorSMU, MedidaAbortadaPorUsuario
from core.utils import escribir_log


def probar_reles_y_dispositivos(cfg):
    result = {"rele_ok": False, "dispositivos": {}, "estado": "iniciando"}
    cfg.setdefault("evento_aborto", None)
    relay = RelayArduinoSerial(cfg["rele"], cfg.get("evento_aborto"))
    smu = None
    try:
        escribir_log(cfg, "Conectando Arduino / relés de degradación…")
        relay.connect()
        escribir_log(cfg, "Arduino identificado; comprobando estructura A (relé IN1/IN2)…")
        relay_status = relay.test()
        result["rele_ok"] = True
        result["estado"] = "reles_ok"
        escribir_log(
            cfg,
            f"Relés confirmados: A={relay_status.get('A')}, "
            f"B={relay_status.get('B')}, apagado final correcto.",
        )

        escribir_log(cfg, "Conectando R&S NGU401…")
        smu = NGU401(cfg).connect()
        probe = cfg["rele"]["prueba_deteccion"]
        smu.initialize(
            probe["limite_corriente_A"],
            probe["rango_corriente_A"],
        )
        for device in "AB":
            escribir_log(cfg, f"Conmutando y midiendo estructura {device}…")
            relay.select(device)
            smu.set_voltage(probe["tension_V"])
            smu.output_on()
            reading = smu.read_vi()
            smu.output_off()
            detected = abs(reading.corriente_A) >= probe["umbral_corriente_A"]
            result["dispositivos"][device] = {
                "detectado": detected,
                "corriente_A": reading.corriente_A,
                "voltaje_V": reading.voltaje_V,
            }
            estado_txt = "DETECTADA" if detected else "NO DETECTADA"
            escribir_log(
                cfg,
                f"Estructura {device}: {estado_txt} (I = {reading.corriente_A * 1e6:.3f} µA a {probe['tension_V']} V)",
            )

        result["estado"] = "completado"
        return result
    except Exception as exc:
        result["estado"] = "error"
        result["error"] = str(exc)
        escribir_log(cfg, f"Error en test de hardware: {exc}")
        return result
    finally:
        relay.off()
        if smu:
            smu.output_off()
            try:
                smu.close()
            except Exception:
                pass
        try:
            relay.close()
        except Exception:
            pass


