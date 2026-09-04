"""Utilidades de estimacion de duracion para secuencias de medida."""
from __future__ import annotations

from statistics import median


def formatear_duracion(segundos: float) -> str:
    segundos = max(0, int(round(float(segundos))))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas} h {minutos:02d} min"
    if minutos:
        return f"{minutos} min {segundos:02d} s"
    return f"{segundos} s"


def estimar_secuencia(
    duraciones: list[float],
    medidas_restantes: int,
    pausas_totales: float,
    pausas_restantes: float,
) -> tuple[float, float] | None:
    if not duraciones:
        return None
    media_robusta = median(duraciones)
    medidas_restantes = max(0, int(medidas_restantes))
    restante = media_robusta * medidas_restantes + max(0.0, float(pausas_restantes))
    total = media_robusta * (len(duraciones) + medidas_restantes) + max(0.0, float(pausas_totales))
    return total, restante