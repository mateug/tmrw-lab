"""Orquestación de ciclos comparativos de degradación A -> B."""
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from apps.stress.relay_degradation import RelayArduinoSerial
from apps.stress.scheduler import (
    IntervalDecision,
    VocObservation,
    interval_for_elapsed_time,
    interval_for_voc_slopes,
    slope_voc_v_per_min,
    validate_slope_rules,
    validate_time_rules,
)
from core.instrument.ngu401 import NGU401
from core.measure.run_ngu401 import run_atomic
from core.postprocess.data import carpeta_experimento, guardar_resumen_ciclo, nombre_seguro
from core.utils import escribir_log

Config = dict[str, Any]
Clock = Callable[[], float]


def run_comparison_cycle(cfg: dict, ciclo: int = 1, guardar_archivos: bool = True) -> dict:
    """Ejecuta un ciclo comparativo A -> B con conmutación física por relé."""
    escribir_log(cfg, "\n################################################################")
    escribir_log(cfg, f"                 INICIO CICLO COMPARATIVO {ciclo:03d}")
    escribir_log(cfg, "################################################################")

    relay = RelayArduinoSerial(cfg["rele"], cfg.get("evento_aborto"))
    smu = None
    resultados = []

    try:
        relay.connect()
        smu = NGU401(cfg).connect()

        for dispositivo in ("A", "B"):
            escribir_log(cfg, f"\n--- Conmutando a la estructura {dispositivo} ---")
            relay.select(dispositivo)
            resultado = run_atomic(cfg, dispositivo, ciclo, smu, guardar_archivos)
            resultados.append(resultado)
    finally:
        if smu:
            smu.close()
        relay.close()

    filas = [r["resumen"] for r in resultados]
    ruta = None
    if guardar_archivos and filas:
        ruta = carpeta_experimento(cfg) / f"{nombre_seguro(cfg['nombre_experimento'])}_resumen_comparativo.xlsx"
        guardar_resumen_ciclo(ruta, filas)
        escribir_log(cfg, f"\nResumen conjunto guardado en: {Path(ruta).name}")

    escribir_log(cfg, "\nCICLO COMPARATIVO FINALIZADO DE FORMA SEGURA")
    return {"medidas": resultados, "ruta_resumen": str(ruta) if ruta else None}


def _wait_cancelable(
    seconds: float,
    event: Any,
    clock: Clock,
    sleep: Callable[[float], None],
) -> bool:
    deadline = clock() + max(0.0, float(seconds))
    while True:
        remaining = deadline - clock()
        if remaining <= 1e-9:
            break
        if event is not None and event.is_set():
            return False
        sleep(min(0.25, remaining))
    return event is None or not event.is_set()


def _voc_by_device(cycle_result: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    for measurement in cycle_result.get("medidas", []):
        summary = measurement.get("resumen", {})
        device = str(summary.get("Estructura", summary.get("Dispositivo", "")))
        voc = summary.get("Voc (V)")
        if voc is None:
            for key, raw in summary.items():
                if str(key).startswith("Voc (") and str(key).endswith(")"):
                    unit = str(key)[5:-1]
                    factor = {"V": 1.0, "mV": 1e-3, "uV": 1e-6}.get(unit)
                    if factor is not None:
                        try:
                            voc = float(raw) * factor
                        except (TypeError, ValueError):
                            voc = None
                    break
        if device in {"A", "B"} and voc is not None:
            try:
                value = float(voc)
            except (TypeError, ValueError):
                continue
            if value == value and abs(value) != float("inf"):
                values[device] = value
    return values


def _decision(
    cfg: Config,
    elapsed_s: float,
    histories: dict[str, list[VocObservation]],
) -> IntervalDecision:
    programming = cfg.get("programacion", {})
    mode = str(programming.get("modo", "por_tiempo")).strip().lower()
    if mode == "por_tiempo":
        rules = validate_time_rules(programming.get("tramos_tiempo", []))
        return interval_for_elapsed_time(elapsed_s, rules)
    if mode != "por_pendiente_voc":
        raise ValueError("programacion.modo debe ser 'por_tiempo' o 'por_pendiente_voc'.")

    window_size = int(programming.get("ventana_pendiente_muestras", 4))
    slope_a = slope_voc_v_per_min(histories["A"], window_size)
    slope_b = slope_voc_v_per_min(histories["B"], window_size)
    rules = validate_slope_rules(programming.get("tramos_pendiente_voc", []))
    return interval_for_voc_slopes(
        slope_a,
        slope_b,
        rules,
        float(programming.get("intervalo_final_s", 150.0)),
    )


def run_degradation_sequence(
    cfg: Config,
    guardar_archivos: bool = True,
    clock: Clock = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Ejecuta ciclos A -> B hasta aborto o duración máxima."""
    programming = cfg.get("programacion", {})
    mode = str(programming.get("modo", "por_tiempo")).strip().lower()
    event = cfg.get("evento_aborto")

    started_at = cfg.get("t0_experimento")
    if started_at is None:
        started_at = clock()
        cfg["t0_experimento"] = started_at

    max_duration_s = None
    if mode == "por_tiempo":
        time_rules = validate_time_rules(programming.get("tramos_tiempo", []))
        if time_rules:
            max_duration_s = time_rules[-1].until_min * 60.0
    else:
        max_duration_min = programming.get("duracion_maxima_min")
        if max_duration_min not in (None, ""):
            max_duration_s = max(0.0, float(max_duration_min) * 60.0)

    histories: dict[str, list[VocObservation]] = {"A": [], "B": []}
    cycles: list[dict[str, Any]] = []
    decision: IntervalDecision | None = None
    cycle_number = 1

    while True:
        if event is not None and event.is_set():
            break
        if max_duration_s is not None and clock() - started_at >= max_duration_s:
            break

        escribir_log(cfg, f"Iniciando ciclo comparativo {cycle_number:03d}.")
        result = run_comparison_cycle(
            cfg,
            ciclo=cycle_number,
            guardar_archivos=guardar_archivos,
        )
        cycles.append(result)

        elapsed_after_cycle = clock() - started_at
        for device, voc in _voc_by_device(result).items():
            histories[device].append(
                VocObservation(elapsed_s=elapsed_after_cycle, voc_v=voc)
            )

        if max_duration_s is not None:
            escribir_log(
                cfg,
                f"Tiempo total transcurrido: {elapsed_after_cycle:.1f} s "
                f"({elapsed_after_cycle / 60.0:.2f} min). "
                f"Límite temporal máximo actual: {max_duration_s / 60.0:.2f} min."
            )

        if max_duration_s is not None and elapsed_after_cycle >= max_duration_s:
            break

        decision = _decision(cfg, elapsed_after_cycle, histories)
        programming_interval = max(
            float(programming.get("intervalo_minimo_s", 0.0)),
            decision.interval_s,
        )

        escribir_log(
            cfg,
            f"Próximo ciclo en {programming_interval:g} s ({decision.reason}).",
        )
        if not _wait_cancelable(programming_interval, event, clock, sleep):
            break

        cycle_number += 1

    elapsed_final_s = clock() - started_at
    status = "abortada" if event is not None and event.is_set() else "finalizada"
    escribir_log(
        cfg,
        f"Secuencia de degradación {status}: "
        f"{len(cycles)} ciclo(s), {elapsed_final_s:.1f} s.",
    )
    return {
        "ciclos": cycles,
        "historial_voc": {
            device: [observation.__dict__ for observation in observations]
            for device, observations in histories.items()
        },
        "ultima_decision": decision,
        "duracion_s": elapsed_final_s,
        "estado": status,
    }


run_cycle = run_comparison_cycle
run_sequence = run_degradation_sequence

