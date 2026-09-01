"""Motor de combinatoria de ejes y planes de medida para Studio.

Combina los ejes seleccionados (Estructura, Motores, LEDs) mediante relaciones
1-1 (emparejamiento directo) o 1-N (producto cartesiano). Si ningún eje está
activo, genera un plan de 1 fila (medida estática única).
"""
from __future__ import annotations

import itertools
import numpy as np

from core.instrument.motors.motor_lineal import (
    construir_barrido_pasos,
    validar_configuracion_motor,
)
from core.instrument.solar_simulator import normalizar_canal_ossila


RANGOS_TENSION_2450 = np.array([0.02, 0.2, 2.0, 20.0, 200.0])
RANGOS_CORRIENTE_2450 = np.array([
    10e-9, 100e-9, 1e-6, 10e-6, 100e-6,
    1e-3, 10e-3, 100e-3, 1.0
])


# ---------------------------------------------------------------------------
# Funciones de barrido IV (Keithley 2450)
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


def construir_barrido(v_ini, v_fin, paso):
    if paso <= 0:
        raise ValueError("El paso de tensión debe ser positivo.")
    signo = 1 if v_fin >= v_ini else -1
    return np.arange(v_ini, v_fin + signo * paso / 2, signo * paso)


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

    tensiones = construir_barrido(v_ini, v_fin, paso)
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
            raise ValueError("Los pasos de tensión deben ser positivos.")

        tensiones_directa = construir_barrido(v_directa_final, v_union, paso_directa)
        tensiones_inversa = construir_barrido(v_union, v_inversa_final, paso_inversa)

        segmentos = []
        directa = construir_segmento_desde_tensiones("directa", tensiones_directa, paso_directa)
        inversa = construir_segmento_desde_tensiones("inversa", tensiones_inversa, paso_inversa)
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
        raise ValueError("El Keithley 2450 no debe superar ±1 A.")

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
            raise ValueError("El Keithley 2450 no debe superar ±200 V.")
        if vmax * i_max > 20:
            raise ValueError(
                f"El segmento {seg['segmento']} supera el límite de potencia de 20 W. "
                f"Vmax*Imax = {vmax * i_max:g} W."
            )
        seg["rango_tension_V"] = elegir_rango(vmax, RANGOS_TENSION_2450, "tensión")
        seg["limite_corriente_A"] = i_max
        seg["rango_corriente_A"] = rango_i

    return segmentos


# ---------------------------------------------------------------------------
# Motor de combinatoria de ejes para Studio
# ---------------------------------------------------------------------------

def construir_eje_leds(cfg: dict) -> list[dict]:
    """Construye la lista de configuraciones para el eje de LEDs."""
    if not cfg.get("simulador_solar_activo", False):
        return [{"solar_modo": "off", "solar_params": {}}]

    modo = cfg.get("irradiancia_modo", "potencia")

    if modo == "potencia":
        p_cfg = cfg["irradiancia_potencia"]
        if p_cfg.get("lista_potencias_custom"):
            potencias = [float(x.strip()) for x in str(p_cfg["lista_potencias_custom"]).split(",") if x.strip()]
        else:
            p_ini = float(p_cfg["p_inicial_mW_cm2"])
            p_fin = float(p_cfg["p_final_mW_cm2"])
            paso = float(p_cfg["paso_mW_cm2"])
            if paso <= 0:
                raise ValueError("El paso de potencia debe ser mayor que 0.")
            potencias = list(np.arange(p_ini, p_fin + paso / 2, paso))

        return [
            {
                "solar_modo": "potencia",
                "solar_params": {
                    "potencia_mW_cm2": p,
                    "espera_estabilizacion_s": float(p_cfg.get("espera_estabilizacion_s", 3.0)),
                    "espera_encendido_medida_s": float(p_cfg.get("espera_encendido_medida_s", 3.0)),
                },
            }
            for p in potencias
        ]

    elif modo == "longitud_onda":
        l_cfg = cfg["irradiancia_longitud_onda"]
        canal = normalizar_canal_ossila(l_cfg.get("canales_seleccionados", "390"))
        if l_cfg.get("lista_intensidades_custom"):
            intensidades = [float(x.strip()) for x in str(l_cfg["lista_intensidades_custom"]).split(",") if x.strip()]
        else:
            i_ini = float(l_cfg["i_inicial_pct"])
            i_fin = float(l_cfg["i_final_pct"])
            paso = float(l_cfg["paso_pct"])
            if paso <= 0:
                raise ValueError("El paso de intensidad debe ser mayor que 0.")
            intensidades = list(np.arange(i_ini, i_fin + paso / 2, paso))

        return [
            {
                "solar_modo": "longitud_onda",
                "solar_params": {
                    "canal": canal,
                    "intensidad_pct": i,
                    "espera_estabilizacion_s": float(l_cfg.get("espera_estabilizacion_s", 3.0)),
                    "espera_encendido_medida_s": float(l_cfg.get("espera_encendido_medida_s", 3.0)),
                },
            }
            for i in intensidades
        ]

    elif modo == "combinacion":
        c_cfg = cfg["irradiancia_combinacion"]
        canales = c_cfg.get("canales_combinacion", [])
        if not canales:
            raise ValueError("No se han configurado canales para la combinación LED.")

        # Obtener listas de intensidades por canal
        listas_intensidades = []
        nombres_canales = []
        for ch_info in canales:
            canal = normalizar_canal_ossila(ch_info.get("canal", ""))
            raw_ints = str(ch_info.get("intensidades", "0")).strip()
            vals = [float(x.strip()) for x in raw_ints.split(",") if x.strip()] or [0.0]
            nombres_canales.append(canal)
            listas_intensidades.append(vals)

        # Producto cartesiano de los canales configurados
        combos = list(itertools.product(*listas_intensidades))
        return [
            {
                "solar_modo": "combinacion",
                "solar_params": {
                    "canales": nombres_canales,
                    "intensidades": list(c),
                    "espera_estabilizacion_s": float(c_cfg.get("espera_estabilizacion_s", 3.0)),
                    "espera_encendido_medida_s": float(c_cfg.get("espera_encendido_medida_s", 3.0)),
                },
            }
            for c in combos
        ]

    elif modo == "multiples_combinaciones":
        m_cfg = cfg["irradiancia_multiples_combinaciones"]
        recetas = m_cfg.get("combinaciones", [])
        if not recetas:
            raise ValueError("No se han configurado recetas en múltiples combinaciones.")
        return [
            {
                "solar_modo": "combinacion",
                "solar_params": {
                    "canales": [normalizar_canal_ossila(item.get("canal", "")) for item in r.get("canales", [])],
                    "intensidades": [float(item.get("intensidad", 0)) for item in r.get("canales", [])],
                    "espera_estabilizacion_s": float(m_cfg.get("espera_estabilizacion_s", 3.0)),
                    "espera_encendido_medida_s": float(m_cfg.get("espera_encendido_medida_s", 3.0)),
                },
            }
            for r in recetas
        ]

    return [{"solar_modo": "off", "solar_params": {}}]


def construir_eje_motor(cfg: dict) -> list[dict]:
    """Construye la lista de posiciones para los ejes de motor activos."""
    motores_activados = []
    if cfg.get("motor_lineal_activo", cfg.get("barrido_motor_activo", False)):
        motores_activados.append({"eje": "lineal", "config": cfg["motor"]})
    if cfg.get("motor_inclinacion_activo", False):
        motores_activados.append({"eje": "inclinacion", "config": cfg["motor"].get("inclinacion", cfg["motor"])})
    if cfg.get("motor_rotacion_activo", False):
        motores_activados.append({"eje": "rotacion", "config": cfg["motor"].get("rotacion", cfg["motor"])})

    if not motores_activados:
        return [{"motor_activo": False, "eje": None, "posicion_pasos": 0, "posicion_mm": 0.0}]

    posiciones = []
    for motor in motores_activados:
        eje_cfg = motor["config"]
        posiciones_pasos = validar_configuracion_motor({**cfg, "motor": eje_cfg})
        if posiciones_pasos.size == 0:
            continue
        resolucion = float(eje_cfg.get("resolucion_mm_paso", cfg["motor"].get("resolucion_mm_paso", 0.00128)))
        for p in posiciones_pasos:
            posiciones.append({
                "motor_activo": True,
                "eje": motor["eje"],
                "posicion_pasos": int(p),
                "posicion_mm": float(p * resolucion),
            })

    if not posiciones:
        return [{"motor_activo": False, "eje": None, "posicion_pasos": 0, "posicion_mm": 0.0}]

    return posiciones


def construir_eje_estructura(cfg: dict) -> list[dict]:
    """Construye la lista de selecciones para el eje de estructura."""
    if not cfg.get("eje_estructura_activo", False):
        return [{"estructura_activa": False, "estructura": None, "keithley": {}}]

    estructura_cfg = cfg.get("estructura", {})
    estructuras = estructura_cfg.get("estructuras") or cfg.get("estructuras_disponibles", ["Estructura 1"])
    keithley_por_estructura = estructura_cfg.get("keithley_por_estructura", {})
    return [
        {
            "estructura_activa": True,
            "estructura": str(est),
            "keithley": keithley_por_estructura.get(str(est), {}),
        }
        for est in estructuras
    ]


def generar_plan_estudio(cfg: dict) -> list[dict]:
    """Genera el plan de medidas multidimensional combinando los ejes activos.

    La relación entre ejes activos es siempre producto cartesiano 1-N en Studio.
    Se mantiene compatibilidad con configuraciones antiguas en las que se hubiese
    especificado "1-1", pero en la práctica se normaliza a "1-N" para evitar
    comportamiento inesperado en la secuencia de medidas.
    """
    eje_est = construir_eje_estructura(cfg)
    eje_mot = construir_eje_motor(cfg)
    eje_led = construir_eje_leds(cfg)

    # Compatibilidad legacy: si existía una configuración antigua con 1-1,
    # se ignora y se utiliza siempre el producto cartesiano.
    _ = cfg.get("relacion_ejes", "1-N")
    combinaciones = list(itertools.product(eje_est, eje_mot, eje_led))

    plan = []
    for idx, (est_info, mot_info, led_info) in enumerate(combinaciones, start=1):
        paso = {
            "indice": idx,
            "total_pasos": len(combinaciones),
            # Estructura
            "estructura_activa": est_info["estructura_activa"],
            "estructura": est_info["estructura"],
            # Motor
            "motor_activo": mot_info["motor_activo"],
            "posicion_motor_pasos": mot_info["posicion_pasos"],
            "posicion_motor_mm": mot_info["posicion_mm"],
            # LED / Simulador Solar
            "solar_modo": led_info["solar_modo"],
            "solar_params": led_info["solar_params"],
        }
        plan.append(paso)

    return plan
