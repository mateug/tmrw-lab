"""Construccion de configuraciones Keithley por iteracion."""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Callable


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
    cfg["i_max_uA"] = float(overrides.get("i_max_uA", cfg.get("i_max_uA", 10.0)))
    cfg["i_max_A"] = cfg["i_max_uA"] * 1e-6
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
