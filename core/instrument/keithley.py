"""Driver Keithley 2450 — portado desde iv-maker.

Añade verificación *IDN? en conectar_y_verificar(): si el instrumento detectado
no es un Keithley 2450, se lanza ErrorSMU con un mensaje claro antes de medir.
"""
import time

import numpy as np
import pandas as pd
import pyvisa

from core.utils import imprimir
from core.exceptions import LimiteCorrienteAlcanzado, MedidaAbortadaPorUsuario, ErrorSMU
from core.instrument.registry import (
    registrar_instrumento_activo,
    limpiar_instrumento_activo,
)

MODELO_ESPERADO = "2450"

RANGOS_TENSION_2450 = np.array([0.02, 0.2, 2.0, 20.0, 200.0])
RANGOS_CORRIENTE_2450 = np.array([
    10e-9, 100e-9, 1e-6, 10e-6, 100e-6,
    1e-3, 10e-3, 100e-3, 1.0
])


# ---------------------------------------------------------------------------
# Conexión con verificación de modelo
# ---------------------------------------------------------------------------

def conectar_y_verificar(recurso_visa: str, timeout_ms: int = 20000):
    """Abre el recurso VISA y verifica que es un Keithley 2450.

    Lanza ErrorSMU con un mensaje descriptivo si:
    - No se puede abrir el recurso.
    - La respuesta a *IDN? no contiene '2450'.
    """
    recurso = str(recurso_visa or "AUTO").strip()
    rm = pyvisa.ResourceManager()

    if recurso.upper() == "AUTO":
        candidatos = rm.list_resources()
        errores = []
        for candidato in candidatos:
            inst = None
            try:
                inst = rm.open_resource(candidato, open_timeout=2500)
                inst.timeout = timeout_ms
                inst.write_termination = "\n"
                inst.read_termination = "\n"
                idn = inst.query("*IDN?").strip()
                if MODELO_ESPERADO in idn:
                    return inst
                inst.close()
            except Exception as exc:
                errores.append(f"{candidato}: {exc}")
                if inst is not None:
                    try:
                        inst.close()
                    except Exception:
                        pass

        detalle = ", ".join(candidatos) if candidatos else "ninguno"
        if errores:
            detalle += f" (errores: {'; '.join(errores)})"
        try:
            rm.close()
        except Exception:
            pass
        raise ErrorSMU(
            "No se encontró un Keithley 2450 por VISA. "
            f"Recursos detectados: {detalle}. "
            "Comprueba NI-VISA/ Keysight VISA, el cableado y que el instrumento esté encendido."
        )

    try:
        inst = rm.open_resource(recurso)
        inst.timeout = timeout_ms
        inst.write_termination = "\n"
        inst.read_termination = "\n"
    except Exception as exc:
        try:
            rm.close()
        except Exception:
            pass
        raise ErrorSMU(
            f"No se pudo conectar al recurso VISA '{recurso}': {exc}\n"
            "Comprueba que la dirección coincide con la mostrada por NI MAX o rm.list_resources(). "
            "Este modo requiere: Keithley 2450."
        ) from exc

    try:
        idn = inst.query("*IDN?").strip()
    except Exception as exc:
        try:
            inst.close()
        except Exception:
            pass
        raise ErrorSMU(
            f"El instrumento en '{recurso}' no responde a *IDN?.\n"
            f"Este modo requiere: Keithley 2450. Error: {exc}"
        ) from exc

    if MODELO_ESPERADO not in idn:
        try:
            inst.close()
        except Exception:
            pass
        raise ErrorSMU(
            f"El instrumento detectado no es un Keithley 2450.\n"
            f"  Esperado: modelo que contenga '{MODELO_ESPERADO}'\n"
            f"  Encontrado: {idn!r}\n"
            f"  Recurso: '{recurso}'\n"
            "Comprueba que el Keithley 2450 está encendido y conectado."
        )

    return inst


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def elegir_rango(valor_maximo, rangos_disponibles, nombre):
    valor_maximo = abs(float(valor_maximo))
    candidatos = rangos_disponibles[rangos_disponibles >= valor_maximo]
    if candidatos.size == 0:
        raise ValueError(
            f"No hay rango disponible para {nombre}={valor_maximo:g}. "
            f"Rango máximo permitido: {rangos_disponibles[-1]:g}."
        )
    return float(candidatos[0])


def aborto_solicitado(cfg):
    evento = cfg.get("evento_aborto") if isinstance(cfg, dict) else None
    return evento is not None and evento.is_set()


def comprobar_aborto_usuario(cfg):
    if aborto_solicitado(cfg):
        raise MedidaAbortadaPorUsuario()


def inicializar_instrumento(inst, cfg):
    inst.write("*RST")
    inst.write("*CLS")
    inst.write(":OUTP OFF")
    inst.write(":SOUR:FUNC VOLT")

    if cfg.get("medir_tension_real", False):
        inst.write(":SOUR:VOLT:READ:BACK ON")
    else:
        inst.write(":SOUR:VOLT:READ:BACK OFF")

    inst.write(':SENS:FUNC "CURR"')

    rango_i_inicial = cfg.get("rango_corriente_A")
    if rango_i_inicial is None:
        rango_i_inicial = elegir_rango(cfg["i_max_A"], RANGOS_CORRIENTE_2450, "corriente")
    else:
        rango_i_inicial = elegir_rango(rango_i_inicial, RANGOS_CORRIENTE_2450, "corriente")

    inst.write(f":SENS:CURR:RANG {rango_i_inicial}")
    cfg["_rango_corriente_actual_A"] = float(rango_i_inicial)
    inst.write(":SENS:CURR:RANG:AUTO OFF")
    inst.write(":SENS:CURR:AZER OFF")
    inst.write(":SENS:CURR:AVER OFF")

    try:
        inst.write(":OUTP:SMOD ZERO")
    except Exception:
        pass


def configurar_sweep_interno(inst, segmento, cfg):
    inst.write(":OUTP OFF")
    inst.write(':TRAC:CLE "defbuffer1"')
    inst.write(f":SOUR:VOLT:RANG {segmento['rango_tension_V']}")
    inst.write(f":SENS:CURR:NPLC {cfg['nplc']}")

    rango_objetivo = float(segmento["rango_corriente_A"])
    rango_actual = cfg.get("_rango_corriente_actual_A")
    if rango_actual is None or not np.isclose(float(rango_actual), rango_objetivo, rtol=0.0, atol=1e-15):
        inst.write(f":SENS:CURR:RANG {rango_objetivo}")
        cfg["_rango_corriente_actual_A"] = rango_objetivo

    inst.write(f":SOUR:VOLT:ILIM {segmento['limite_corriente_A']}")
    inst.write("*CLS")
    inst.write(
        f":SOUR:SWE:VOLT:LIN "
        f"{segmento['v_inicial_V']}, "
        f"{segmento['v_final_V']}, "
        f"{segmento['n_puntos']}, "
        f"{cfg['delay_estabilizacion_s']}, "
        f"1, "
        f"FIXED"
    )


def cancelar_medida_y_apagar(inst):
    for cmd in (":ABOR", ":SOUR:VOLT 0", ":OUTP OFF"):
        try:
            inst.write(cmd)
            time.sleep(0.05)
        except Exception:
            pass


def corriente_en_limite(corriente_A, limite_A, rango_A, fraccion=0.98):
    i_abs = abs(float(corriente_A))
    limite_efectivo = min(abs(float(limite_A)), abs(float(rango_A)))
    return i_abs >= fraccion * limite_efectivo


def leer_corriente_puntual(inst):
    respuesta = inst.query(":READ?").strip()
    valores = np.fromstring(respuesta, sep=",")
    if valores.size == 0 or not np.isfinite(valores[0]):
        raise RuntimeError(f"Respuesta no válida al leer corriente: {respuesta!r}")
    return float(valores[0])


def ejecutar_sweep_seguro_punto_a_punto(inst, segmento, cfg):
    filas = []
    t_medida_ini = time.perf_counter()
    timeout_original = inst.timeout
    inst.timeout = int(cfg.get("timeout_lectura_segura_ms", timeout_original))

    try:
        inst.write(":OUTP ON")
        for idx, voltaje in enumerate(segmento["tensiones_V"], start=1):
            if aborto_solicitado(cfg):
                df_parcial = pd.DataFrame(filas)
                cancelar_medida_y_apagar(inst)
                raise MedidaAbortadaPorUsuario(df_parcial=df_parcial)

            inst.write(f":SOUR:VOLT {float(voltaje)}")
            time.sleep(float(cfg["delay_estabilizacion_s"]))

            if aborto_solicitado(cfg):
                df_parcial = pd.DataFrame(filas)
                cancelar_medida_y_apagar(inst)
                raise MedidaAbortadaPorUsuario(df_parcial=df_parcial)

            corriente = leer_corriente_puntual(inst)
            tiempo_rel = time.perf_counter() - t_medida_ini

            filas.append({
                "segmento": segmento["segmento"],
                "indice_segmento": idx,
                "tiempo_relativo_s": tiempo_rel,
                "voltaje_V": float(voltaje),
                "corriente_medida_A": corriente,
                "potencia_W": float(voltaje) * corriente,
            })

            if corriente_en_limite(
                corriente,
                segmento["limite_corriente_A"],
                segmento["rango_corriente_A"],
                cfg.get("fraccion_limite_warning", 0.98),
            ):
                df_parcial = pd.DataFrame(filas)
                cancelar_medida_y_apagar(inst)
                mensaje = (
                    "WARNING: límite de corriente alcanzado. "
                    f"Segmento={segmento['segmento']}, punto={idx}, "
                    f"V={float(voltaje):.6g} V, I={corriente:.6g} A, "
                    f"I_limit={segmento['limite_corriente_A']:.6g} A, "
                    f"rango_I={segmento['rango_corriente_A']:.6g} A. "
                    "La medida se ha abortado y el SMU se ha detenido."
                )
                raise LimiteCorrienteAlcanzado(mensaje, df_parcial=df_parcial)

    finally:
        inst.timeout = timeout_original
        cancelar_medida_y_apagar(inst)

    tiempo_medida = time.perf_counter() - t_medida_ini
    return tiempo_medida, pd.DataFrame(filas)


def ejecutar_sweep(inst, cfg=None):
    if cfg is not None:
        comprobar_aborto_usuario(cfg)
    inst.write(":OUTP ON")
    t_medida_ini = time.perf_counter()
    try:
        if cfg is not None:
            comprobar_aborto_usuario(cfg)
        inst.write(":INIT")
        inst.query("*OPC?")
        if cfg is not None:
            comprobar_aborto_usuario(cfg)
    except Exception:
        cancelar_medida_y_apagar(inst)
        raise
    finally:
        t_medida_fin = time.perf_counter()
        cancelar_medida_y_apagar(inst)
    return t_medida_fin - t_medida_ini


def leer_buffer(inst, n_puntos, segmento):
    respuesta = inst.query(
        f':TRAC:DATA? 1, {n_puntos}, "defbuffer1", SOUR, READ, REL'
    ).strip()
    valores = np.fromstring(respuesta, sep=",")
    valores_esperados = 3 * n_puntos
    if valores.size != valores_esperados:
        raise RuntimeError(
            f"Se esperaban {valores_esperados} valores, pero se recibieron {valores.size}."
        )
    matriz = valores.reshape(n_puntos, 3)
    voltaje = matriz[:, 0]
    corriente = matriz[:, 1]
    tiempo = matriz[:, 2]
    potencia = voltaje * corriente
    return pd.DataFrame({
        "segmento": segmento,
        "indice_segmento": np.arange(1, n_puntos + 1),
        "tiempo_relativo_s": tiempo,
        "voltaje_V": voltaje,
        "corriente_medida_A": corriente,
        "potencia_W": potencia,
    })


def apagar_seguro(inst):
    cancelar_medida_y_apagar(inst)


def enviar_go_to_local_visa(inst):
    """Envía comando GTL (Go To Local) para devolver control frontal al usuario."""
    if not hasattr(inst, "control_ren"):
        return False

    modos = []
    try:
        modos.append(pyvisa.constants.RENLineOperation.go_to_local)
    except Exception:
        pass

    for nombre_constante in (
        "VI_GPIB_REN_DEASSERT_GTL",
        "VI_GPIB_REN_ADDRESS_GTL",
        "VI_GPIB_REN_DEASSERT",
    ):
        try:
            modos.append(getattr(pyvisa.constants, nombre_constante))
        except Exception:
            pass

    modos.extend([2, 6, 0])

    for modo in modos:
        try:
            inst.control_ren(modo)
            return True
        except Exception:
            pass
    return False


def enviar_go_to_remote_visa(inst):
    """Devuelve el control remoto VISA al programa de medida."""
    modos = []
    try:
        modos.append(pyvisa.constants.RENLineOperation.go_to_remote)
    except Exception:
        pass

    for nombre_constante in (
        "VI_GPIB_REN_ASSERT_ADDRESS",
        "VI_GPIB_REN_ASSERT_REMOTE",
    ):
        try:
            modos.append(getattr(pyvisa.constants, nombre_constante))
        except Exception:
            pass

    modos.extend([1, 3, 4])

    for modo in modos:
        try:
            inst.control_ren(modo)
            return True
        except Exception:
            pass
    return False


def liberar_control_manual_keithley(recurso_visa: str, timeout_ms: int = 5000):
    """Libera el Keithley 2450 permitiendo la operación manual en su pantalla táctil."""
    inst = None
    try:
        inst = conectar_y_verificar(recurso_visa or "AUTO", timeout_ms=timeout_ms)
        inst.timeout = int(timeout_ms)
        inst.write_termination = "\n"
        inst.read_termination = "\n"

        try:
            inst.write(":ABOR")
            time.sleep(0.05)
        except Exception:
            pass

        try:
            inst.write(":SYST:ACC FULL")
        except Exception:
            pass

        try:
            inst.write(":DISP:CLE")
        except Exception:
            pass

        try:
            enviar_go_to_local_visa(inst)
        except Exception:
            pass
    finally:
        if inst is not None:
            try:
                inst.close()
            except Exception:
                pass


def recuperar_control_automatico_keithley(recurso_visa: str, timeout_ms: int = 5000):
    """Recupera el control remoto VISA después del modo manual."""
    inst = None
    try:
        inst = conectar_y_verificar(recurso_visa or "AUTO", timeout_ms=timeout_ms)
        inst.timeout = int(timeout_ms)
        inst.write_termination = "\n"
        inst.read_termination = "\n"
        if not enviar_go_to_remote_visa(inst):
            raise ErrorSMU("No se pudo recuperar el control remoto del Keithley 2450.")
    finally:
        if inst is not None:
            try:
                inst.close()
            except Exception:
                pass

