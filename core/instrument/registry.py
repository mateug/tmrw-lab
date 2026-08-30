"""Registro thread-safe de instrumentos activos — versión unificada de TMRW Lab.

Soporta claves dinámicas: 'keithley', 'motor', 'simulador_solar', 'smu', 'rele'.
"""
from threading import Lock

_lock = Lock()
_activos: dict[str, object | None] = {
    "keithley": None,
    "motor": None,
    "simulador_solar": None,
    "smu": None,
    "rele": None,
}


def registrar(nombre: str, instrumento: object) -> None:
    if nombre not in _activos:
        raise KeyError(f"Instrumento desconocido: {nombre!r}")
    with _lock:
        _activos[nombre] = instrumento


def limpiar(nombre: str, instrumento: object | None = None) -> None:
    if nombre not in _activos:
        raise KeyError(f"Instrumento desconocido: {nombre!r}")
    with _lock:
        if instrumento is None or _activos[nombre] is instrumento:
            _activos[nombre] = None


def obtener(nombre: str) -> object | None:
    with _lock:
        return _activos.get(nombre)


def abortar_instrumento_activo() -> bool:
    """Detiene todos los instrumentos registrados. Devuelve True si había alguno."""
    with _lock:
        activos = [inst for inst in _activos.values() if inst is not None]

    if not activos:
        return False

    for inst in activos:
        try:
            stop = getattr(inst, "stop", None)
            if callable(stop):
                stop()
            else:
                output_off = getattr(inst, "output_off", None)
                if callable(output_off):
                    output_off()
                else:
                    # Keithley: enviar abort directo
                    write = getattr(inst, "write", None)
                    if callable(write):
                        write(":ABOR")
                        write(":SOUR:VOLT 0")
                        write(":OUTP OFF")
        except Exception:
            pass
        try:
            inst.close()
        except Exception:
            pass

    with _lock:
        for nombre in list(_activos):
            if _activos[nombre] in activos:
                _activos[nombre] = None

    return True


# ---- Aliases de compatibilidad con iv-maker (registro por función dedicada) ----

def registrar_instrumento_activo(inst) -> None:
    registrar("keithley", inst)


def limpiar_instrumento_activo(inst=None) -> None:
    limpiar("keithley", inst)


def registrar_motor_activo(motor) -> None:
    registrar("motor", motor)


def limpiar_motor_activo(motor=None) -> None:
    limpiar("motor", motor)


def registrar_simulador_solar_activo(simulador) -> None:
    registrar("simulador_solar", simulador)


def limpiar_simulador_solar_activo(simulador=None) -> None:
    limpiar("simulador_solar", simulador)


def abortar_motor_activo() -> bool:
    motor = obtener("motor")
    if motor is None:
        return False
    try:
        motor.stop()
    except Exception:
        pass
    try:
        motor.close()
    except Exception:
        pass
    limpiar("motor")
    return True


def abortar_simulador_solar_activo() -> bool:
    sim = obtener("simulador_solar")
    if sim is None:
        return False
    try:
        sim.apagar_sin_error()
    except Exception:
        pass
    try:
        sim.close()
    except Exception:
        pass
    limpiar("simulador_solar")
    return True
