"""Configuración por defecto para el Modo Lite."""
from copy import deepcopy
from core.config.schemas import (
    BLOQUE_BARRIDO_IV,
    BLOQUE_SALIDA,
    BLOQUE_UI,
    BLOQUE_MOTOR,
    BLOQUE_SIMULADOR_SOLAR,
    BLOQUE_ESTRUCTURA,
)

CONFIG_LITE_DEFAULT = {
    **deepcopy(BLOQUE_BARRIDO_IV),
    **deepcopy(BLOQUE_SALIDA),
    **deepcopy(BLOQUE_UI),
    **deepcopy(BLOQUE_MOTOR),
    **deepcopy(BLOQUE_SIMULADOR_SOLAR),
    **deepcopy(BLOQUE_ESTRUCTURA),
    # Parámetros específicos de receta Excel (Submodo E de iv-maker)
    "ruta_excel_receta": "",
    "hoja_excel": "",
    "excel_valores_0_1": True,
    "plantilla_comando_excel": "<ch{channel}:{intensity}>",
    "espera_estabilizacion_s": 1.0,
    "espera_luz_encendida_s": 0.0,
    "espera_motor_s": 0.0,
    "tiempo_enfriado_s": 0.0,
    "apagar_al_final": True,
}


def get_default_config() -> dict:
    return deepcopy(CONFIG_LITE_DEFAULT)
