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


def _expandir_combinacion_canales(canales: list, relaciones: list) -> list:
    """Expande una lista de canales con sus intensidades en las combinaciones finales.

    Respeta la relación 1-1 (emparejamiento por posición) o 1-N (producto
    cartesiano) definida entre cada par de canales consecutivos, replicando
    exactamente el comportamiento que tenían las pestañas "Combinación
    Multi-Canal" y "Múltiples Combinaciones Multi-Canal" del antiguo Modo 3
    de Irradiancia LED.

    Devuelve una lista de tuplas (nombres_canales, intensidades).
    """
    nombres_canales = [normalizar_canal_ossila(ch.get("canal", "")) for ch in canales]
    listas_intensidades = []
    for ch in canales:
        raw = str(ch.get("intensidades", "0")).strip()
        vals = [float(x.strip()) for x in raw.split(",") if x.strip()] or [0.0]
        listas_intensidades.append(vals)

    if not listas_intensidades:
        return []

    # Combinaciones parciales construidas incrementalmente, canal a canal.
    combos_parciales = [[v] for v in listas_intensidades[0]]

    for idx in range(1, len(listas_intensidades)):
        actual = listas_intensidades[idx]
        relacion = relaciones[idx - 1] if idx - 1 < len(relaciones) else "1-1"
        anterior_len = len(listas_intensidades[idx - 1])

        nuevas = []
        if relacion == "1-N":
            for parcial in combos_parciales:
                for val in actual:
                    nuevas.append(parcial + [val])
        else:
            # 1-1: emparejamiento por posición, salvo que uno de los dos sea un valor fijo.
            if anterior_len == 1:
                for parcial in combos_parciales:
                    for val in actual:
                        nuevas.append(parcial + [val])
            elif len(actual) == 1:
                for parcial in combos_parciales:
                    nuevas.append(parcial + [actual[0]])
            elif anterior_len == len(actual):
                for parcial, val in zip(combos_parciales, actual):
                    nuevas.append(parcial + [val])
            else:
                raise ValueError(
                    "La relación 1-1 entre dos canales consecutivos requiere el mismo número "
                    "de intensidades, salvo que uno de ellos tenga una única intensidad fija. "
                    f"Se han encontrado {anterior_len} y {len(actual)}."
                )
        combos_parciales = nuevas

    return [(nombres_canales, intensidades) for intensidades in combos_parciales]


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
        # Submodo C: Combinación Multi-Canal (una sola combinación con relaciones 1-1 / 1-N
        # entre canales consecutivos), tal como en la pestaña homónima del antiguo Modo 3.
        c_cfg = cfg["irradiancia_combinacion"]
        canales = c_cfg.get("canales_combinacion", [])
        if not canales:
            raise ValueError("No se han configurado canales para la combinación LED.")

        relaciones = c_cfg.get("relaciones", [])
        combos = _expandir_combinacion_canales(canales, relaciones)
        return [
            {
                "solar_modo": "combinacion",
                "solar_params": {
                    "canales": nombres_canales,
                    "intensidades": list(intensidades),
                    "espera_estabilizacion_s": float(c_cfg.get("espera_estabilizacion_s", 3.0)),
                    "espera_encendido_medida_s": float(c_cfg.get("espera_encendido_medida_s", 3.0)),
                },
            }
            for nombres_canales, intensidades in combos
        ]

    elif modo == "multiples_combinaciones":
        # Submodo D: Múltiples Combinaciones Multi-Canal. Cada combinación se expande igual
        # que en el submodo C (con sus propias relaciones 1-1 / 1-N) y todas se concatenan
        # en el orden en que fueron definidas.
        m_cfg = cfg["irradiancia_multiples_combinaciones"]
        combinaciones = m_cfg.get("combinaciones", [])
        if not combinaciones:
            raise ValueError("No se han configurado combinaciones en múltiples combinaciones.")

        pasos = []
        for combo in combinaciones:
            canales = combo.get("canales", [])
            if not canales:
                continue
            relaciones = combo.get("relaciones", [])
            for nombres_canales, intensidades in _expandir_combinacion_canales(canales, relaciones):
                pasos.append({
                    "solar_modo": "combinacion",
                    "solar_params": {
                        "canales": nombres_canales,
                        "intensidades": list(intensidades),
                        "nombre_combinacion": combo.get("nombre", ""),
                        "espera_estabilizacion_s": float(m_cfg.get("espera_estabilizacion_s", 3.0)),
                        "espera_encendido_medida_s": float(m_cfg.get("espera_encendido_medida_s", 3.0)),
                    },
                })
        if not pasos:
            raise ValueError("No se han configurado combinaciones en múltiples combinaciones.")
        return pasos

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


def _extraer_cooldown_led(cfg: dict) -> tuple[int, float]:
    """Devuelve la regla de enfriamiento por estructura aplicada dentro de cada combinación LED."""
    irradiancia_cfg = cfg.get("irradiancia_combinacion", {})
    if not irradiancia_cfg and cfg.get("irradiancia_modo") == "multiples_combinaciones":
        irradiancia_cfg = cfg.get("irradiancia_multiples_combinaciones", {})

    cada_n = int(irradiancia_cfg.get("cada_n_medidas_estructura", 0) or 0)
    if cada_n < 0:
        cada_n = 0
    tiempo_s = float(
        irradiancia_cfg.get("tiempo_espera_cada_n_s",
                            irradiancia_cfg.get("tiempo_enfriado_s", 0.0))
        or 0.0
    )
    if tiempo_s < 0:
        tiempo_s = 0.0
    return cada_n, tiempo_s


def generar_plan_estudio(cfg: dict) -> list[dict]:
    """Genera el plan de medidas multidimensional combinando ejes activos.

    El orden real del estudio es: motor → LED → estructura(s) → medida. Dentro de cada
    combinación motor+LED, se recorren las estructuras seleccionadas y se insertan pasos de
    enfriamiento cuando se alcanza el umbral configurado por combinación.
    """
    eje_mot = construir_eje_motor(cfg)
    eje_led = construir_eje_leds(cfg)
    config_estructura = cfg.get("estructura", {})
    estructuras_seleccionadas = []
    if cfg.get("eje_estructura_activo", False):
        estructuras_seleccionadas = [
            str(est) for est in (config_estructura.get("estructuras") or [])
        ]
    if not estructuras_seleccionadas:
        estructuras_seleccionadas = [None]

    plan = []
    cd_medidas, cd_tiempo = _extraer_cooldown_led(cfg)

    combo_idx = 0
    for mot_info in eje_mot:
        for led_info in eje_led:
            combo_idx += 1
            for medida_idx, estructura in enumerate(estructuras_seleccionadas, start=1):
                keithley_cfg = {}
                if estructura is not None:
                    keithley_cfg = config_estructura.get("keithley_por_estructura", {}).get(str(estructura), {})

                plan.append({
                    "indice": len(plan) + 1,
                    "total_pasos": None,
                    "tipo": "medida",
                    "combo_idx": combo_idx,
                    "estructura_activa": estructura is not None,
                    "estructura": estructura,
                    "motor_activo": mot_info["motor_activo"],
                    "posicion_motor_pasos": mot_info["posicion_pasos"],
                    "posicion_motor_mm": mot_info["posicion_mm"],
                    "solar_modo": led_info["solar_modo"],
                    "solar_params": led_info["solar_params"],
                    "keithley": keithley_cfg,
                    "orden_estructura": medida_idx,
                })

                if cd_medidas and cd_tiempo and medida_idx % cd_medidas == 0 and medida_idx < len(estructuras_seleccionadas):
                    plan.append({
                        "indice": len(plan) + 1,
                        "total_pasos": None,
                        "tipo": "enfriar",
                        "combo_idx": combo_idx,
                        "estructura": estructura,
                        "duracion_s": cd_tiempo,
                        "accion": "apagar_luz",
                    })

    for idx, paso in enumerate(plan, start=1):
        paso["total_pasos"] = len(plan)
        paso["indice"] = idx

    return plan
