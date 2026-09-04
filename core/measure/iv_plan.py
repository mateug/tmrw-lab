"""Planificacion y validacion comun de barridos IV para Keithley 2450."""
from __future__ import annotations

import numpy as np


RANGOS_TENSION_2450 = np.array([0.02, 0.2, 2.0, 20.0, 200.0])
RANGOS_CORRIENTE_2450 = np.array([
    10e-9, 100e-9, 1e-6, 10e-6, 100e-6,
    1e-3, 10e-3, 100e-3, 1.0,
])


def elegir_rango(valor_maximo, rangos_disponibles, nombre):
    valor_maximo = abs(float(valor_maximo))
    candidatos = rangos_disponibles[rangos_disponibles >= valor_maximo]
    if candidatos.size == 0:
        raise ValueError(
            f"No hay rango disponible para {nombre}={valor_maximo:g}. "
            f"Rango maximo permitido: {rangos_disponibles[-1]:g}."
        )
    return float(candidatos[0])


def construir_barrido(v_ini, v_fin, paso):
    if paso <= 0:
        raise ValueError("El paso de tension debe ser positivo.")
    signo = 1 if v_fin >= v_ini else -1
    return np.arange(v_ini, v_fin + signo * paso / 2, signo * paso)


def construir_barrido_decreciente(v_extremo_a, v_extremo_b, paso):
    """Construye un barrido desde la tension mayor hasta la menor."""
    return construir_barrido(
        max(float(v_extremo_a), float(v_extremo_b)),
        min(float(v_extremo_a), float(v_extremo_b)),
        paso,
    )


def construir_segmento_desde_tensiones(nombre, tensiones, paso):
    tensiones = np.asarray(tensiones, dtype=float)
    if tensiones.size == 0:
        return None
    return {
        "segmento": nombre,
        "v_inicial_V": float(tensiones[0]),
        "v_final_V": float(tensiones[-1]),
        "paso_V": float(abs(paso)),
        "n_puntos": int(len(tensiones)),
        "tensiones_V": tensiones,
    }


def normalizar_segmento(nombre, cfg_segmento, modo_medida, cfg_directa=None):
    if nombre == "directa":
        v_ini = cfg_segmento["v_inicial_mV"] * 1e-3
        v_fin = cfg_segmento["v_final_mV"] * 1e-3
        paso = cfg_segmento["paso_mV"] * 1e-3
    elif nombre == "inversa":
        if cfg_segmento.get("v_inicial_mV") is None:
            if modo_medida != "completa" or cfg_directa is None:
                raise ValueError("En modo inversa independiente debes especificar V_i (mV).")
            v_inicial_mV = cfg_directa["v_inicial_mV"]
        else:
            v_inicial_mV = cfg_segmento["v_inicial_mV"]
        v_ini = v_inicial_mV * 1e-3
        v_fin = cfg_segmento["v_final_V"]
        paso = cfg_segmento["paso_mV"] * 1e-3
    else:
        raise ValueError(f"Segmento desconocido: {nombre}")

    tensiones = construir_barrido_decreciente(v_ini, v_fin, paso)
    return {
        "segmento": nombre,
        "v_inicial_V": float(v_ini),
        "v_final_V": float(v_fin),
        "paso_V": float(paso),
        "n_puntos": int(len(tensiones)),
        "tensiones_V": tensiones,
    }


def construir_plan_medida(cfg):
    modo = cfg["modo_medida"].strip().lower()
    if modo not in {"directa", "inversa", "completa"}:
        raise ValueError("modo_medida debe ser 'directa', 'inversa' o 'completa'.")

    if modo == "directa":
        segmentos = [normalizar_segmento("directa", cfg["directa"], modo)]
    elif modo == "inversa":
        segmentos = [normalizar_segmento("inversa", cfg["inversa"], modo)]
    else:
        v_union = float(cfg["directa"]["v_inicial_mV"]) * 1e-3
        v_directa_final = float(cfg["directa"]["v_final_mV"]) * 1e-3
        paso_directa = float(cfg["directa"]["paso_mV"]) * 1e-3
        v_inversa_final = float(cfg["inversa"]["v_final_V"])
        paso_inversa = float(cfg["inversa"]["paso_mV"]) * 1e-3
        if paso_directa <= 0 or paso_inversa <= 0:
            raise ValueError("Los pasos de tension deben ser positivos.")

        segmentos = []
        directa = construir_segmento_desde_tensiones(
            "directa",
            construir_barrido_decreciente(v_directa_final, v_union, paso_directa),
            paso_directa,
        )
        inversa = construir_segmento_desde_tensiones(
            "inversa",
            construir_barrido_decreciente(v_union, v_inversa_final, paso_inversa),
            paso_inversa,
        )
        if directa is not None:
            segmentos.append(directa)
        if inversa is not None:
            segmentos.append(inversa)
    return segmentos


def validar_segmentos_y_configuracion(cfg, segmentos):
    i_max = abs(float(cfg["i_max_A"]))
    if i_max <= 0:
        raise ValueError("i_max_A debe ser positivo.")
    if i_max > 1:
        raise ValueError("El Keithley 2450 no debe superar +/-1 A.")

    rango_i = cfg.get("rango_corriente_A")
    if rango_i is None:
        rango_i = elegir_rango(i_max, RANGOS_CORRIENTE_2450, "corriente")
    else:
        rango_i = abs(float(rango_i))
        if rango_i < i_max:
            raise ValueError("El rango de corriente debe ser mayor o igual que i_max_A.")
        rango_i = elegir_rango(rango_i, RANGOS_CORRIENTE_2450, "corriente")

    for seg in segmentos:
        vmax = max(abs(seg["v_inicial_V"]), abs(seg["v_final_V"]))
        if vmax > 200:
            raise ValueError("El Keithley 2450 no debe superar +/-200 V.")
        if vmax * i_max > 20:
            raise ValueError(
                f"El segmento {seg['segmento']} supera el limite de potencia de 20 W. "
                f"Vmax*Imax = {vmax * i_max:g} W."
            )
        seg["rango_tension_V"] = elegir_rango(vmax, RANGOS_TENSION_2450, "tension")
        seg["limite_corriente_A"] = i_max
        seg["rango_corriente_A"] = rango_i
    return segmentos
