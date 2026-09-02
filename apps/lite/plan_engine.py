"""Parser y plan de ejecución para recetas Excel del modo Lite."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


MOTOR_COLUMNS = {
    "motor_lineal": ("motor_lineal_step", "motor_lineal_stop"),
    "motor_inclinacion": ("motor_inclinacion_step", "motor_inclinacion_stop"),
    "motor_rotacion": ("motor_rotacion_step", "motor_rotacion_stop"),
}

LED_ALIASES = {
    "390 nm": "390",
    "450 nm": "450",
    "515 nm": "515",
    "600 nm": "600",
    "630 nm": "630",
    "650 nm": "650",
    "660 nm": "660",
    "730 nm": "730",
    "850 nm": "850",
    "950 nm": "950",
    "cool white": "cool_white",
    "warm white": "warm_white",
}


@dataclass(frozen=True)
class LitePlan:
    """Receta normalizada lista para ser consumida por el ejecutor."""

    steps: tuple[dict[str, Any], ...]
    active_axes: frozenset[str]
    structures: tuple[str, ...]
    columns: tuple[str, ...]

    @property
    def measure_count(self) -> int:
        return len(self.steps)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _number(value: Any, label: str) -> float:
    if _is_empty(value):
        raise ValueError(f"El valor de '{label}' no puede estar vacío.")
    try:
        result = float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"El valor de '{label}' debe ser numérico: {value!r}.") from exc
    if not math.isfinite(result):
        raise ValueError(f"El valor de '{label}' debe ser finito.")
    return result


def _canonical_header(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[áàäâ]", "a", text)
    text = re.sub(r"[éèëê]", "e", text)
    text = re.sub(r"[íìïî]", "i", text)
    text = re.sub(r"[óòöô]", "o", text)
    text = re.sub(r"[úùüû]", "u", text)
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _resolve_columns(df: pd.DataFrame) -> tuple[dict[str, str], list[str]]:
    resolved: dict[str, str] = {}
    led_columns: list[str] = []
    seen: dict[str, str] = {}
    for original in df.columns:
        header = _canonical_header(original)
        if header in seen:
            raise ValueError(f"Columnas duplicadas o ambiguas: '{seen[header]}' y '{original}'.")
        seen[header] = str(original)
        if header in {"estructura", "estructuras", "estructura_id", "estructura_ids"}:
            if "estructura" in resolved:
                raise ValueError("La receta solo puede tener una columna de estructuras.")
            resolved["estructura"] = str(original)
            continue
        if header in MOTOR_COLUMNS:
            raise ValueError(f"Encabezado incompleto de motor: '{original}'. Usa step o stop.")
        for motor, pair in MOTOR_COLUMNS.items():
            if header in pair:
                resolved[header] = str(original)
                break
        else:
            led = _led_channel_from_header(header)
            if led:
                led_columns.append(str(original))
    if not resolved and not led_columns:
        raise ValueError("El Excel no contiene columnas reconocibles de motores, LEDs o estructuras.")
    return resolved, led_columns


def _led_channel_from_header(header: str) -> str | None:
    normalized = header.replace("_", " ").strip()
    if normalized in LED_ALIASES:
        return LED_ALIASES[normalized]
    match = re.fullmatch(r"(\d{3})", normalized)
    if match and f"{match.group(1)} nm" in LED_ALIASES:
        return match.group(1)
    if normalized in {"cool", "cool led"}:
        return "cool_white"
    if normalized in {"warm", "warm led"}:
        return "warm_white"
    return None


def _parse_structures(value: Any, row_number: int) -> list[str]:
    if _is_empty(value):
        return []
    result = []
    for raw in str(value).split(","):
        token = raw.strip()
        if not token:
            continue
        try:
            numeric = float(token)
            number = int(numeric)
        except ValueError as exc:
            raise ValueError(f"Fila {row_number}: estructura inválida '{token}'.") from exc
        if number == 0:
            continue
        if number < 1 or number > 7 or numeric != number:
            raise ValueError(f"Fila {row_number}: la estructura '{token}' debe ser un ID entero entre 1 y 7.")
        name = f"Estructura {number}"
        if name not in result:
            result.append(name)
    return result


def build_lite_plan(df: pd.DataFrame, valores_en_tanto_por_uno: bool = True) -> LitePlan:
    """Valida ``df`` y devuelve una medida por estructura de cada fila."""
    if df.empty:
        raise ValueError("La receta Excel no contiene filas de datos.")
    resolved, led_columns = _resolve_columns(df)
    active_axes: set[str] = set()
    motor_values: dict[int, dict[str, dict[str, float]]] = {}
    led_values: dict[int, dict[str, float]] = {}

    for row_index, row in df.iterrows():
        motor_values[row_index] = {}
        for motor, (step_header, stop_header) in MOTOR_COLUMNS.items():
            step_col = resolved.get(step_header)
            stop_col = resolved.get(stop_header)
            if not step_col and not stop_col:
                continue
            step_raw = row.get(step_col) if step_col else None
            stop_raw = row.get(stop_col) if stop_col else None
            if _is_empty(step_raw) and _is_empty(stop_raw):
                continue
            step = _number(step_raw, step_header)
            stop = _number(stop_raw, stop_header)
            if step == 0 and stop == 0:
                continue
            if step == 0 or stop == 0:
                raise ValueError(f"Fila {row_index + 2}: '{motor}' requiere step y stop, o ambos a cero.")
            active_axes.add(motor)
            motor_values[row_index][motor] = {"step": step, "stop": stop}

        led_values[row_index] = {}
        for column in led_columns:
            value = row[column]
            if _is_empty(value):
                continue
            intensity = _number(value, column)
            if valores_en_tanto_por_uno:
                if intensity < 0 or intensity > 1:
                    raise ValueError(f"Fila {row_index + 2}: '{column}' debe estar entre 0 y 1.")
                intensity *= 100
            elif intensity < 0 or intensity > 100:
                raise ValueError(f"Fila {row_index + 2}: '{column}' debe estar entre 0 y 100.")
            if intensity:
                active_axes.add("led")
                led_values[row_index][_led_channel_from_header(_canonical_header(column))] = intensity

    steps: list[dict[str, Any]] = []
    structures_seen: list[str] = []
    structure_column = resolved.get("estructura")
    for row_index, row in df.iterrows():
        structures = _parse_structures(row.get(structure_column) if structure_column else None, row_index + 2)
        if structures:
            active_axes.add("estructura")
        for structure in structures or [None]:
            if structure and structure not in structures_seen:
                structures_seen.append(structure)
            steps.append({
                "fila_excel": row_index + 2,
                "estructura": structure,
                "motores": motor_values[row_index],
                "leds": led_values[row_index],
                "valores_originales": row.to_dict(),
            })
    if not steps:
        raise ValueError("La receta no contiene ninguna medida válida.")
    return LitePlan(tuple(steps), frozenset(active_axes), tuple(structures_seen), tuple(map(str, df.columns)))