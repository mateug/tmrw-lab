"""Bloques de configuración reutilizables entre modos — TMRW Lab.

Cada modo compone su DEFAULT_CONFIG importando y mezclando estos bloques.
Solo se definen aquí los parámetros que aparecen en 2 o más modos.
"""
from copy import deepcopy
from datetime import datetime
from core.utils import resolver_carpeta_salida_portatil


# ---------------------------------------------------------------------------
# Bloque: barrido IV (Studio + Lite + Stress)
# ---------------------------------------------------------------------------

BLOQUE_BARRIDO_IV = {
    "modo_medida": "completa",           # "directa" | "inversa" | "completa"
    "i_max_A": 1e-5,
    "i_max_uA": 10,
    "i_max_unit": "uA",
    "superficie_um2": None,
    "irradiancia_mW_cm2": None,
    "rango_corriente_A": None,
    "nplc": 1,
    "delay_estabilizacion_s": 0.0001,
    "abortar_si_limite_corriente": True,
    "fraccion_limite_warning": 0.98,
    "timeout_lectura_segura_ms": 10000,
    "guardar_parcial_si_aborta": True,
    "medir_tension_real": False,
    "invertir_eje_y_graficas": True,
    "directa": {
        "v_inicial_mV": 0,
        "v_final_mV": 550,
        "paso_mV": 10,
    },
    "inversa": {
        "v_inicial_mV": None,
        "v_final_V": -11,
        "paso_mV": 100,
    },
}

# ---------------------------------------------------------------------------
# Bloque: motor (Studio + Lite)
# ---------------------------------------------------------------------------

BLOQUE_MOTOR = {
    "barrido_motor_activo": False,
    "motor": {
        "puerto_serie": "COM4",
        "baudrate": 115200,
        "timeout_s": 120.0,
        "pasos_por_segundo_motor": 50.0,
        "margen_timeout_movimiento_s": 8.0,
        "step_pasos": -625,
        "stop_pasos": -62500,
        "resolucion_mm_paso": 0.00128,
        "espera_estabilizacion_s": 0.0,
        "espera_luz_encendida_s": 0.0,
        "pasos_centrado_pulsacion": 1,
        "poner_cero_al_conectar": True,
        "volver_cero_al_final": False,
        "inclinacion": {
            "puerto_serie": "COM5",
            "baudrate": 115200,
            "step_pasos": -625,
            "stop_pasos": -62500,
            "resolucion_deg_paso": 0.00128,
            "espera_estabilizacion_s": 0.0,
            "poner_cero_al_conectar": True,
            "volver_cero_al_final": False,
            "pasos_centrado_pulsacion": 1,
        },
        "rotacion": {
            "puerto_serie": "COM6",
            "baudrate": 115200,
            "step_pasos": -625,
            "stop_pasos": -62500,
            "resolucion_deg_paso": 0.00128,
            "espera_estabilizacion_s": 0.0,
            "poner_cero_al_conectar": True,
            "volver_cero_al_final": False,
            "pasos_centrado_pulsacion": 1,
        },
    },
    "posicion_motor_pasos": None,
    "posicion_motor_mm": None,
}

# ---------------------------------------------------------------------------
# Bloque: simulador solar / LEDs (Studio + Lite)
# ---------------------------------------------------------------------------

BLOQUE_SIMULADOR_SOLAR = {
    "simulador_solar_activo": False,
    "simulador_solar": {
        "puerto_serie": "COM3",
        "baudrate": 9600,
        "timeout_lectura_s": 0.20,
        "timeout_comando_s": 5.0,
        "reintentos": 3,
        "tiempo_confirmacion_encendido_s": 2.5,
        "intervalo_confirmacion_s": 0.25,
        "confirmaciones_requeridas": 2,
        "tolerancia_potencia_mW_cm2": 0.5,
        "separador_comando": "auto",
        "apagar_al_conectar": True,
        "potencia_objetivo_mW_cm2": None,
    },
    "irradiancia_modo": "potencia",
    "irradiancia_potencia": {
        "p_inicial_mW_cm2": 0.0,
        "p_final_mW_cm2": 100.0,
        "paso_mW_cm2": 10.0,
        "lista_potencias_custom": None,
        "espera_estabilizacion_s": 3.0,
        "espera_encendido_medida_s": 3.0,
        "apagar_al_final": True,
    },
    "irradiancia_longitud_onda": {
        "plantilla_comando": "<ch{channel}:{intensity}>",
        "canales_seleccionados": "390",
        "i_inicial_pct": 0,
        "i_final_pct": 100,
        "paso_pct": 10,
        "lista_intensidades_custom": None,
        "espera_estabilizacion_s": 3.0,
        "espera_encendido_medida_s": 3.0,
        "apagar_al_final": True,
    },
    "irradiancia_combinacion": {
        "plantilla_comando": "<ch{channel}:{intensity}>",
        "canales_combinacion": [
            {"canal": "950", "intensidades": "100"},
            {"canal": "660", "intensidades": "0, 50, 100"},
        ],
        "espera_estabilizacion_s": 3.0,
        "espera_encendido_medida_s": 3.0,
        "cada_n_medidas_estructura": 0,
        "tiempo_enfriado_s": 0.0,
        "tiempo_espera_cada_n_s": 0.0,
        "apagar_al_final": True,
    },
    "irradiancia_multiples_combinaciones": {
        "plantilla_comando": "<ch{channel}:{intensity}>",
        "combinaciones": [],
        "espera_estabilizacion_s": 3.0,
        "espera_encendido_medida_s": 3.0,
        "cada_n_medidas_estructura": 0,
        "tiempo_enfriado_s": 0.0,
        "tiempo_espera_cada_n_s": 0.0,
        "apagar_al_final": True,
    },
}

# ---------------------------------------------------------------------------
# Bloque: salida de archivos (Studio + Lite + Stress)
# ---------------------------------------------------------------------------

BLOQUE_SALIDA = {
    "carpeta_salida": resolver_carpeta_salida_portatil(),
    "nombre_carpeta_medida": datetime.now().strftime("%Y-%m-%d"),
    "carpeta_salida_medida": None,
    "nombre_medida": "medida_",
    "fecha_hora_inicio_medida": None,
    "guardar_archivos": True,
}

# ---------------------------------------------------------------------------
# Bloque: UI
# ---------------------------------------------------------------------------

BLOQUE_UI = {
    "tema_ui": "tmrw_silicon",
    "mostrar_graficas": True,
}

# ---------------------------------------------------------------------------
# Bloque: estructura / relé de muestra (Studio + Lite)
# ---------------------------------------------------------------------------

BLOQUE_ESTRUCTURA = {
    "eje_estructura_activo": False,
    "estructura": {
        "puerto_serie": "COM4",
        "baudrate": 115200,
        "estructuras": ["A", "B"],
        "espera_conmutacion_s": 0.5,
    },
}

# ---------------------------------------------------------------------------
# Bloque: runtime (callbacks, aborto — no se serializa)
# ---------------------------------------------------------------------------

BLOQUE_RUNTIME = {
    "evento_aborto": None,
    "log_callback": None,
    "grafica_callback": None,
}


def combinar(*bloques) -> dict:
    """Combina múltiples bloques de configuración en un único dict."""
    resultado = {}
    for bloque in bloques:
        resultado.update(deepcopy(bloque))
    return resultado
