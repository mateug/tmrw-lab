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
from core.instrument.solar_simulator import etiquetar_canal_ossila, normalizar_canal_ossila
from core.measure.iv_plan import (
    RANGOS_CORRIENTE_2450 as _RANGOS_CORRIENTE_2450,
    RANGOS_TENSION_2450 as _RANGOS_TENSION_2450,
    construir_barrido as _construir_barrido,
    construir_barrido_decreciente as _construir_barrido_decreciente,
    construir_plan_medida as _construir_plan_medida,
    construir_segmento_desde_tensiones as _construir_segmento_desde_tensiones,
    elegir_rango as _elegir_rango,
    normalizar_segmento as _normalizar_segmento,
    validar_segmentos_y_configuracion as _validar_segmentos_y_configuracion,
)
from core.utils import sanitizar_nombre_archivo


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


RANGOS_TENSION_2450 = _RANGOS_TENSION_2450
RANGOS_CORRIENTE_2450 = _RANGOS_CORRIENTE_2450


# ---------------------------------------------------------------------------
# Funciones de barrido IV (Keithley 2450)
# ---------------------------------------------------------------------------

def elegir_rango(valor_maximo, rangos_disponibles, nombre):
    return _elegir_rango(valor_maximo, rangos_disponibles, nombre)


def construir_barrido(v_ini, v_fin, paso):
    return _construir_barrido(v_ini, v_fin, paso)


def construir_barrido_decreciente(v_extremo_a, v_extremo_b, paso):
    """Construye un barrido desde la tensión mayor hasta la menor."""
    return _construir_barrido_decreciente(v_extremo_a, v_extremo_b, paso)


def construir_segmento_desde_tensiones(nombre, tensiones, paso):
    return _construir_segmento_desde_tensiones(nombre, tensiones, paso)


def normalizar_segmento(nombre, cfg_segmento, modo_medida, cfg_directa=None):
    return _normalizar_segmento(nombre, cfg_segmento, modo_medida, cfg_directa)


def construir_plan_medida(cfg):
    return _construir_plan_medida(cfg)


def validar_segmentos_y_configuracion(cfg, segmentos):
    return _validar_segmentos_y_configuracion(cfg, segmentos)


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
        canales_raw = l_cfg.get("canales_seleccionados", "390")
        if isinstance(canales_raw, str):
            canales_raw = [item.strip() for item in canales_raw.split(",") if item.strip()]
        canales = [normalizar_canal_ossila(canal) for canal in canales_raw if str(canal).strip()]
        if not canales:
            raise ValueError("Selecciona al menos un canal LED para el submodo de longitud de onda.")

        if l_cfg.get("lista_intensidades_custom"):
            intensidades = [float(x.strip()) for x in str(l_cfg["lista_intensidades_custom"]).split(",") if x.strip()]
        else:
            i_ini = float(l_cfg["i_inicial_pct"])
            i_fin = float(l_cfg["i_final_pct"])
            paso = float(l_cfg["paso_pct"])
            if paso <= 0:
                raise ValueError("El paso de intensidad debe ser mayor que 0.")
            intensidades = list(np.arange(i_ini, i_fin + paso / 2, paso))

        if not intensidades or any(not np.isfinite(valor) or valor < 0 or valor > 100 for valor in intensidades):
            raise ValueError("Las intensidades LED deben estar entre 0 y 100 %." )

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
            for canal in canales
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
        if motor["eje"] == "lineal":
            resolucion = float(eje_cfg.get("resolucion_mm_paso", cfg["motor"].get("resolucion_mm_paso", 0.00128)))
        else:
            resolucion = float(eje_cfg.get(
                "resolucion_deg_paso",
                eje_cfg.get("resolucion_mm_paso", 0.00128),
            ))
        for p in posiciones_pasos:
            posiciones.append({
                "motor_activo": True,
                "eje": motor["eje"],
                "posicion_pasos": int(p),
                "posicion_mm": float(p * resolucion),
                "posicion_fisica": float(p * resolucion),
                "unidad_fisica": "mm" if motor["eje"] == "lineal" else "deg",
            })

    if not posiciones:
        return [{"motor_activo": False, "eje": None, "posicion_pasos": 0, "posicion_mm": 0.0}]

    return posiciones


def _formatear_valor_nombre(valor: float) -> str:
    return f"{float(valor):.3f}"


def _etiqueta_canal_nombre(canal) -> str:
    etiqueta = etiquetar_canal_ossila(canal)
    return f"{etiqueta}nm" if etiqueta.isdigit() else etiqueta


def construir_nombre_iteracion(nombre_base: str, paso: dict) -> str:
    """Compone un nombre estable con únicamente los ejes activos del paso."""
    partes = [sanitizar_nombre_archivo(nombre_base)]

    estructura = paso.get("estructura")
    if estructura:
        partes.append(sanitizar_nombre_archivo(estructura))

    solar_modo = paso.get("solar_modo")
    solar = paso.get("solar_params") or {}
    if solar_modo == "potencia":
        partes.append(f"potencia_{_formatear_valor_nombre(solar.get('potencia_mW_cm2', 0))}mWcm2")
    elif solar_modo == "longitud_onda":
        partes.append(
            f"{sanitizar_nombre_archivo(_etiqueta_canal_nombre(solar.get('canal', 'led')))}_"
            f"{float(solar.get('intensidad_pct', 0)):03.0f}pct"
        )
    elif solar_modo == "combinacion":
        leds = [
            f"{sanitizar_nombre_archivo(_etiqueta_canal_nombre(canal))}_{float(intensidad):03.0f}pct"
            for canal, intensidad in zip(solar.get("canales", []), solar.get("intensidades", []))
        ]
        if leds:
            partes.append("-".join(leds))

    if paso.get("motor_activo"):
        eje = paso.get("eje")
        valor = paso.get("posicion_fisica", paso.get("posicion_mm", 0.0))
        unidad = paso.get("unidad_fisica", "mm")
        partes.append(f"{eje}_{_formatear_valor_nombre(valor)}{unidad}")

    return "__".join(partes)


def construir_eje_estructura(cfg: dict) -> list[dict]:
    """Construye la lista de selecciones para el eje de estructura."""
    relay_active = cfg.get("estructura_modo") == "relay" or cfg.get("eje_estructura_activo", False)
    if not relay_active:
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
    relay_active = cfg.get("estructura_modo") == "relay" or cfg.get("eje_estructura_activo", False)
    if relay_active:
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
                    "posicion_motor_fisica": mot_info.get("posicion_fisica", mot_info["posicion_mm"]),
                    "posicion_motor_unidad": mot_info.get("unidad_fisica"),
                    "eje_motor": mot_info.get("eje"),
                    "solar_modo": led_info["solar_modo"],
                    "solar_params": led_info["solar_params"],
                    "keithley": keithley_cfg,
                    "orden_estructura": medida_idx,
                })
                plan[-1]["nombre_iteracion"] = construir_nombre_iteracion(cfg["nombre_medida"], plan[-1])

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
