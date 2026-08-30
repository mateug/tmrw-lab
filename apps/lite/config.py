"""Configuración por defecto para el modo Lite."""
from core.config.schemas import (
    BLOQUE_BARRIDO_IV,
    BLOQUE_MOTOR,
    BLOQUE_SIMULADOR_SOLAR,
    BLOQUE_SALIDA,
    BLOQUE_UI,
    BLOQUE_RUNTIME,
    combinar,
)


def get_default_config() -> dict:
    """Devuelve la configuración completa por defecto para Lite."""
    cfg = combinar(
        BLOQUE_BARRIDO_IV,
        BLOQUE_MOTOR,
        BLOQUE_SIMULADOR_SOLAR,
        BLOQUE_SALIDA,
        BLOQUE_UI,
        BLOQUE_RUNTIME,
    )
    cfg["titulo_aplicacion"] = "TMRW Lab — Lite"
    cfg["recurso_visa"] = "AUTO"
    cfg["smu_modelo_esperado"] = "2450"
    cfg["ruta_excel_receta"] = ""
    return cfg
