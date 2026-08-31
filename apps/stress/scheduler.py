"""Polí­ticas de intervalo para secuencias de degradación."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

import numpy as np


@dataclass(frozen=True)
class TimeRule:
    """Intervalo aplicable hasta un lí­mite de tiempo, en minutos."""

    until_min: float
    interval_s: float


@dataclass(frozen=True)
class SlopeRule:
    """Intervalo aplicable cuando ambos dispositivos superan un umbral."""

    threshold_v_per_min: float
    interval_s: float


@dataclass(frozen=True)
class VocObservation:
    """Valor de Voc asociado al instante monotónico de una medida."""

    elapsed_s: float
    voc_v: float


@dataclass(frozen=True)
class IntervalDecision:
    interval_s: float
    reason: str
    slope_a_v_per_min: float | None = None
    slope_b_v_per_min: float | None = None
    matched_threshold_v_per_min: float | None = None
    finished: bool = False


def validate_time_rules(rules: Iterable[Mapping[str, float]]) -> list[TimeRule]:
    """Valida y ordena reglas por tiempo ascendente."""
    parsed = [
        TimeRule(float(rule["hasta_min"]), float(rule["intervalo_s"]))
        for rule in rules
    ]
    if not parsed:
        raise ValueError("Debe existir al menos un tramo temporal.")
    if any(
        not isfinite(rule.until_min)
        or not isfinite(rule.interval_s)
        or rule.until_min <= 0
        or rule.interval_s <= 0
        for rule in parsed
    ):
        raise ValueError("Los lí­mites e intervalos temporales deben ser positivos.")
    parsed.sort(key=lambda rule: rule.until_min)
    if any(left.until_min == right.until_min for left, right in zip(parsed, parsed[1:])):
        raise ValueError("No puede haber lí­mites temporales duplicados.")
    return parsed


def _slope_rule_mapping(rule: SlopeRule | Mapping[str, float]) -> Mapping[str, float]:
    if isinstance(rule, SlopeRule):
        return {
            "umbral_V_por_min": rule.threshold_v_per_min,
            "intervalo_s": rule.interval_s,
        }
    return rule


def validate_slope_rules(rules: Iterable[Mapping[str, float]]) -> list[SlopeRule]:
    """Valida y ordena umbrales de pendiente de mayor a menor."""
    parsed = [
        SlopeRule(
            float(rule["umbral_V_por_min"]),
            float(rule["intervalo_s"]),
        )
        for rule in rules
    ]
    if not parsed:
        raise ValueError("Debe existir al menos una regla de pendiente.")
    if any(
        not isfinite(rule.threshold_v_per_min)
        or not isfinite(rule.interval_s)
        or rule.threshold_v_per_min < 0
        or rule.interval_s <= 0
        for rule in parsed
    ):
        raise ValueError("Los umbrales no pueden ser negativos y los intervalos deben ser positivos.")
    parsed.sort(key=lambda rule: rule.threshold_v_per_min, reverse=True)
    if any(
        left.threshold_v_per_min == right.threshold_v_per_min
        for left, right in zip(parsed, parsed[1:])
    ):
        raise ValueError("No puede haber umbrales de pendiente duplicados.")
    return parsed

def interval_for_elapsed_time(
    elapsed_s: float,
    rules: Iterable[TimeRule],
) -> IntervalDecision:
    """Devuelve el intervalo del primer lí­mite temporal que aún no se supera."""
    elapsed_min = max(0.0, float(elapsed_s)) / 60.0
    parsed = validate_time_rules(
        {
            "hasta_min": rule.until_min,
            "intervalo_s": rule.interval_s,
        }
        for rule in rules
    )

    for index, rule in enumerate(parsed):
        if elapsed_min <= rule.until_min:
            return IntervalDecision(
                rule.interval_s,
                f"tiempo transcurrido <= {rule.until_min:g} min",
                finished=(index == len(parsed) - 1 and elapsed_min >= rule.until_min),
            )

    last = parsed[-1]
    return IntervalDecision(
        last.interval_s,
        f"tiempo transcurrido > {last.until_min:g} min",
        finished=True,
    )


def slope_voc_v_per_min(
    observations: Iterable[VocObservation],
    window_size: int,
) -> float | None:
    """Calcula |dVoc/dt| mediante regresión lineal sobre las últimas muestras."""
    window = list(observations)[-max(2, int(window_size)) :]
    if len(window) < 2:
        return None
    times = np.asarray([item.elapsed_s for item in window], dtype=float)
    voc = np.asarray([item.voc_v for item in window], dtype=float)
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(voc)):
        return None
    if np.unique(times).size < 2:
        return None
    slope_v_per_s = float(np.polyfit(times, voc, 1)[0])
    return abs(slope_v_per_s) * 60.0


def interval_for_voc_slopes(
    slope_a_v_per_min: float | None,
    slope_b_v_per_min: float | None,
    rules: Iterable[SlopeRule | Mapping[str, float]],
    fallback_interval_s: float,
) -> IntervalDecision:
    """Elige la regla más rápida que cumplen simultáneamente A y B.

    La regla de mayor umbral representa la evolución más rápida y, por tanto,
    el intervalo más frecuente. Si falta una pendiente o ningún umbral se
    cumple en ambos dispositivos, se usa el intervalo de fallback.
    """
    fallback = float(fallback_interval_s)
    if not isfinite(fallback) or fallback <= 0:
        raise ValueError("El intervalo de fallback debe ser positivo.")
    if slope_a_v_per_min is None or slope_b_v_per_min is None:
        return IntervalDecision(fallback, "pendiente insuficiente para ambos dispositivos")
    if not isfinite(slope_a_v_per_min) or not isfinite(slope_b_v_per_min):
        return IntervalDecision(fallback, "pendiente no válida para ambos dispositivos")

    parsed = validate_slope_rules(
        _slope_rule_mapping(rule)
        for rule in rules
    )
    for rule in parsed:
        if (
            slope_a_v_per_min >= rule.threshold_v_per_min
            and slope_b_v_per_min >= rule.threshold_v_per_min
        ):
            return IntervalDecision(
                rule.interval_s,
                f"A y B superan {rule.threshold_v_per_min:g} V/min",
                slope_a_v_per_min,
                slope_b_v_per_min,
                rule.threshold_v_per_min,
            )
    return IntervalDecision(
        fallback,
        "ningún umbral se cumple simultáneamente en A y B",
        slope_a_v_per_min,
        slope_b_v_per_min,
    )

