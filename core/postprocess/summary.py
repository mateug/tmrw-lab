"""Construccion compartida de filas de resumen de medidas."""
from __future__ import annotations


def añadir_resultados_fv(fila: dict, resultados_fv: dict | None) -> dict:
    """Añade resultados FV normalizados a una fila de resumen."""
    for clave, valor in (resultados_fv or {}).items():
        if clave in {"Isc_unidad", "Isc_adapt", "Imp_unidad", "Imp_adapt", "Pmax_unidad", "Pmax_adapt"}:
            continue
        if clave == "Jsc_mA_cm2":
            fila["Jsc (mA/cm^2)"] = valor
        elif clave == "Densidad_potencia_mW_cm2":
            fila["Densidad de potencia (mW/cm^2)"] = valor
        elif clave.endswith("_V"):
            fila[clave[:-2] + " (V)"] = valor
        elif clave.endswith("_A"):
            fila[clave[:-2] + " (A)"] = valor
        elif clave.endswith("_W"):
            fila[clave[:-2] + " (W)"] = valor
        elif clave == "FF":
            fila["FF (%)"] = float(valor) * 100.0
        elif clave == "Eff":
            fila["Eff (%)"] = valor
    return fila


def construir_fila_resumen_medida(
    resultado: dict,
    indice: int,
    nombre_iteracion: str,
    estructura=None,
) -> dict:
    """Crea los campos comunes de una fila de Studio/Lite."""
    fila = {
        "Iteración": indice,
        "Nombre iteración": nombre_iteracion,
        "Estructura": estructura,
        "Estado": resultado.get("estado_medida"),
        "Puntos": resultado.get("puntos_medidos"),
    }
    return añadir_resultados_fv(fila, resultado.get("resultados_fv"))


def añadir_ejes_a_fila(fila: dict, paso: dict) -> dict:
    """Añade motores y LEDs usando los formatos de cada plan."""
    for motor, posicion in (paso.get("motores") or {}).items():
        if motor == "motor_lineal":
            valor = posicion["valor"] * float(paso.get("resolucion_lineal_mm_paso", 0.00128))
            fila["Motor lineal (mm)"] = valor
        elif motor == "motor_inclinacion":
            fila["Inclinación (deg)"] = posicion["valor"]
        elif motor == "motor_rotacion":
            fila["Rotación (deg)"] = posicion["valor"]

    for canal, intensidad in (paso.get("leds") or {}).items():
        fila[f"LED {canal} (%)"] = intensidad
    return fila
