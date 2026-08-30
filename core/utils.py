"""Utilidades comunes sin dependencias de interfaz ni hardware."""
from datetime import datetime
from pathlib import Path
import re
import uuid

import numpy as np


# ---------------------------------------------------------------------------
# Salida de texto
# ---------------------------------------------------------------------------

def imprimir(*args, **kwargs):
    kwargs.setdefault("flush", True)
    print(*args, **kwargs)


def escribir_log(cfg, mensaje: str) -> None:
    """Envía un mensaje al callback de UI si existe; si no, escribe en terminal."""
    callback = cfg.get("log_callback") if isinstance(cfg, dict) else None
    if callback is not None:
        callback(str(mensaje))
    else:
        imprimir(mensaje)


# Alias para compatibilidad con iv-maker
def emitir_log(cfg, *args, **kwargs):
    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    mensaje = sep.join(str(arg) for arg in args)
    escribir_log(cfg, mensaje + end)


# ---------------------------------------------------------------------------
# Nombres de archivo
# ---------------------------------------------------------------------------

def sanitizar_nombre_archivo(nombre: str) -> str:
    nombre = str(nombre).strip()
    if not nombre:
        raise ValueError("nombre_medida no puede estar vacío.")
    nombre = re.sub(r'[\\/:*?"<>|]+', "_", nombre)
    nombre = re.sub(r"\s+", "_", nombre)
    return nombre


# Alias con nombre más corto (devices-degradation)
def nombre_seguro(nombre: str) -> str:
    limpio = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(nombre)).strip(" ._")
    return limpio or "medida"


def crear_nombre_temporal(ruta) -> Path:
    ruta = Path(ruta)
    return ruta.with_name(f".{ruta.stem}_{uuid.uuid4().hex}.tmp{ruta.suffix}")


# ---------------------------------------------------------------------------
# Carpetas de salida
# ---------------------------------------------------------------------------

def resolver_carpeta_salida_portatil() -> str:
    home = Path.home()
    candidatos = (home / "Desktop", home / "Escritorio", home / "Documents", home)
    base = next((ruta for ruta in candidatos if ruta.exists()), home)
    return str(base / "automatic-measurements-lab" / "Medidas SMU")


def obtener_nombre_carpeta_medida(cfg) -> str:
    nombre = str(cfg.get("nombre_carpeta_medida", "")).strip()
    if not nombre:
        nombre = datetime.now().strftime("%Y-%m-%d")
    return sanitizar_nombre_archivo(nombre)


def preparar_carpeta_medida(cfg) -> Path:
    carpeta_base = Path(cfg["carpeta_salida"])
    nombre_carpeta = obtener_nombre_carpeta_medida(cfg)
    carpeta_medida = carpeta_base / nombre_carpeta
    carpeta_medida.mkdir(parents=True, exist_ok=True)
    cfg["carpeta_salida_medida"] = str(carpeta_medida)
    return carpeta_medida


# ---------------------------------------------------------------------------
# Formateo de resultados FV
# ---------------------------------------------------------------------------

def formatear_resultados_fotovoltaicos(resultados) -> str:
    if not resultados:
        return "Resultados FV: no disponibles."

    def valor(nombre, fmt=".3f", unidad=""):
        dato = resultados.get(nombre)
        try:
            dato = float(dato)
            if not np.isfinite(dato):
                return "N/A"
            return f"{dato:{fmt}}{unidad}"
        except (TypeError, ValueError):
            return "N/A"

    u_isc = " " + str(resultados.get("Isc_unidad", ""))
    u_imp = " " + str(resultados.get("Imp_unidad", ""))
    u_pmax = " " + str(resultados.get("Pmax_unidad", ""))

    lineas = [
        "RESULTADOS FOTOVOLTAICOS",
        f"  Voc  : {valor('Voc_mV', '.2f', ' mV')}",
        f"  Isc  : {valor('Isc_adapt', '.3f', u_isc)}",
        f"  Vmp  : {valor('Vmp_mV', '.2f', ' mV')}",
        f"  Imp  : {valor('Imp_adapt', '.3f', u_imp)}",
        f"  Pmax : {valor('Pmax_adapt', '.3f', u_pmax)}",
        f"  FF   : {valor('FF', '.2%')}",
    ]

    for clave, etiqueta, fmt, unidad in (
        ("Jsc_mA_cm2", "Jsc", ".3f", " mA/cm²"),
        ("Eff", "Eff", ".2f", " %"),
    ):
        try:
            disponible = resultados.get(clave) is not None and np.isfinite(
                float(resultados.get(clave))
            )
        except (TypeError, ValueError):
            disponible = False
        if disponible:
            lineas.append(f"  {etiqueta:<4}: {valor(clave, fmt, unidad)}")

    return "\n".join(lineas)
