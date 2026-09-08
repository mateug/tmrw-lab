"""Construccion de configuraciones Keithley por iteracion."""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Callable


FACTORES_I_MAX_POR_UNIDAD = {
    "uA": 1e-6,
    "mA": 1e-3,
    "A": 1.0,
}


def convertir_i_max_a_amperios(valor, unidad="uA"):
    """Convierte el valor de compliance a amperios según su unidad."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        valor = 0.0
    return valor * FACTORES_I_MAX_POR_UNIDAD.get(str(unidad).strip() or "uA", 1e-6)


def construir_configuracion_keithley(
    cfg_base: dict,
    estructura: str | None = None,
    overrides: dict | None = None,
    callbacks: dict[str, Callable] | None = None,
) -> dict:
    """Devuelve una configuracion aislada para una medida Keithley."""
    cfg = deepcopy(cfg_base)
    overrides = overrides or {}
    estructura_cfg = cfg.get("estructura", {})
    estructuras = [estructura] if estructura else []
    cfg["estructura"] = dict(estructura_cfg, estructuras=estructuras)
    cfg["estructura"]["keithley_por_estructura"] = estructura_cfg.get(
        "keithley_por_estructura", {}
    )

    cfg["modo_medida"] = str(
        overrides.get("modo_medida", cfg.get("modo_medida", "completa"))
    ).strip() or "completa"

    unidad = str(overrides.get("i_max_unit", cfg.get("i_max_unit", "uA"))).strip() or "uA"
    valor_raw = overrides.get("i_max_value", overrides.get("i_max_uA", cfg.get("i_max_uA", 10.0)))
    valor = float(valor_raw)

    cfg["i_max_unit"] = unidad
    cfg["i_max_A"] = convertir_i_max_a_amperios(valor, unidad)
    cfg["i_max_uA"] = cfg["i_max_A"] * 1e6

    if "superficie_um2" in overrides:
        cfg["superficie_um2"] = (
            float(overrides["superficie_um2"])
            if overrides["superficie_um2"] not in (None, "")
            else None
        )
    if "irradiancia_mW_cm2" in overrides:
        cfg["irradiancia_mW_cm2"] = (
            float(overrides["irradiancia_mW_cm2"])
            if overrides["irradiancia_mW_cm2"] not in (None, "")
            else None
        )
    cfg["recurso_visa"] = str(cfg_base.get("recurso_visa", "AUTO")).strip() or "AUTO"
    cfg["invertir_eje_y_graficas"] = bool(
        overrides.get("invertir_eje_y", cfg.get("invertir_eje_y_graficas", True))
    )

    directa = dict(cfg.get("directa", {}))
    directa.update({
        "v_inicial_mV": float(overrides.get("v_inicial_mV", directa.get("v_inicial_mV", 0.0))),
        "v_final_mV": float(overrides.get("v_final_mV", directa.get("v_final_mV", 550.0))),
        "paso_mV": float(overrides.get("paso_mV", directa.get("paso_mV", 10.0))),
    })
    cfg["directa"] = directa

    inversa = dict(cfg.get("inversa", {}))
    inversa.update({
        "v_final_V": float(overrides.get("v_final_inversa_V", inversa.get("v_final_V", -11.0))),
        "paso_mV": float(overrides.get("paso_inversa_mV", inversa.get("paso_mV", 100.0))),
    })
    cfg["inversa"] = inversa

    if callbacks:
        cfg.update(callbacks)
    return cfg
