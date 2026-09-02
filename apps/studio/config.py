"""Configuración por defecto para el modo Studio."""
from core.config.schemas import (
    BLOQUE_BARRIDO_IV,
    BLOQUE_MOTOR,
    BLOQUE_SIMULADOR_SOLAR,
    BLOQUE_SALIDA,
    BLOQUE_UI,
    BLOQUE_ESTRUCTURA,
    BLOQUE_RUNTIME,
    combinar,
)


def get_default_config() -> dict:
    """Devuelve la configuración completa por defecto para Studio."""
    cfg = combinar(
        BLOQUE_BARRIDO_IV,
        BLOQUE_MOTOR,
        BLOQUE_SIMULADOR_SOLAR,
        BLOQUE_SALIDA,
        BLOQUE_UI,
        BLOQUE_ESTRUCTURA,
        BLOQUE_RUNTIME,
    )
    # Ajustes específicos de Studio
    cfg["titulo_aplicacion"] = "TMRW Lab — Studio"
    cfg["recurso_visa"] = "AUTO"
    cfg["smu_modelo_esperado"] = "2450"

    # Ejes combinables de Studio
    cfg["eje_estructura_activo"] = False
    cfg["estructura_seleccionada"] = "Estructura 1"
    cfg["estructuras_disponibles"] = ["Estructura 1", "Estructura 2"]

    cfg["relacion_ejes"] = "1-N"  # "1-1" o "1-N" (producto cartesiano)
    return cfg
