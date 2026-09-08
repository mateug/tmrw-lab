"""Pruebas compartidas de hardware para Studio y Lite."""
from __future__ import annotations

import time
from collections.abc import Callable

from core.instrument.relay_structure import crear_rele_estructura
from core.instrument.registry import (
    limpiar_simulador_solar_activo,
    registrar_simulador_solar_activo,
)
from core.instrument.solar_simulator import crear_controlador_simulador_solar


def _esperar_abortable(segundos: float, evento_aborto) -> None:
    limite = time.monotonic() + max(0.0, float(segundos))
    while time.monotonic() < limite:
        if evento_aborto is not None and evento_aborto.is_set():
            raise RuntimeError("Prueba abortada por el usuario.")
        time.sleep(min(0.05, limite - time.monotonic()))


def probar_simulador_solar(
    cfg: dict,
    evento_aborto,
    log_callback: Callable[[str], None],
    plantilla_comando: str = "<ch{channel}:{intensity}>",
) -> None:
    """Prueba el simulador solar con un único encendido a 50 mW/cm2."""
    simulador = None
    try:
        simulador = crear_controlador_simulador_solar(
            {**cfg, "simulador_solar_activo": True}, evento_aborto
        )
        simulador.connect()
        registrar_simulador_solar_activo(simulador)
        log_callback("[TEST] Encendiendo potencia: 50 mW/cm2\n")
        simulador.encender_y_verificar(50.0)
        _esperar_abortable(1.0, evento_aborto)
        simulador.apagar()
        log_callback("[OK] Prueba del simulador solar completada.\n")
    finally:
        if simulador is not None:
            limpiar_simulador_solar_activo(simulador)
            try:
                simulador.close()
            except Exception:
                pass


def probar_reles_estructura(
    cfg: dict,
    evento_aborto,
    log_callback: Callable[[str], None],
    pausa_s: float = 0.0,
) -> None:
    """Selecciona las estructuras configuradas y comprueba el relé."""
    rele = None
    try:
        estructuras = cfg.get("estructura", {}).get("estructuras") or [
            "Estructura 1", "Estructura 2"
        ]
        rele = crear_rele_estructura(cfg, evento_aborto)
        rele.connect()
        for index, estructura in enumerate(estructuras, 1):
            if evento_aborto is not None and evento_aborto.is_set():
                raise RuntimeError("Prueba abortada por el usuario.")
            letra = rele.select(estructura)
            log_callback(
                f"[TEST] Estructura {index}/{len(estructuras)}: "
                f"{estructura} ({letra})\n"
            )
            _esperar_abortable(pausa_s, evento_aborto)
        log_callback("[OK] Prueba de relés completada.\n")
    finally:
        if rele is not None:
            try:
                rele.close()
            except Exception:
                pass
