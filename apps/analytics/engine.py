"""Motor de datos de Analytics — portado de IV-Curves-Generator.

Responsabilidades:
- Escanear carpeta en busca de archivos Excel con curvas IV.
- Leer y combinar los DataFrames IV.
- Detectar y validar unidades.
- Calcular resúmenes (Isc, Voc, Pmax, FF).
No toca Tkinter: es puro Python/pandas.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Factores de unidad
# ---------------------------------------------------------------------------

UNIT_FACTORS = {
    "I": {"A": 1.0, "mA": 1e3, "uA": 1e6, "nA": 1e9},
    "V": {"V": 1.0, "mV": 1e3},
}

COL_CORRIENTE_CANDIDATAS = [
    "corriente_medida_A", "corriente_A", "I", "i",
    "Corriente (A)", "Current (A)", "I (A)",
]
COL_VOLTAJE_CANDIDATAS = [
    "voltaje_V", "voltaje_medido_V", "V", "v",
    "Voltaje (V)", "Voltage (V)", "V (V)",
]
COL_ARCHIVO = "Archivo"
COL_DATETIME = "Fecha y hora inicio"


def _detectar_columna(cols, candidatas) -> str | None:
    cols_lower = {c.lower(): c for c in cols}
    for cand in candidatas:
        if cand in cols:
            return cand
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None


def _detectar_unidad_corriente(df, col_i: str) -> str:
    i_max = df[col_i].abs().max()
    if not np.isfinite(i_max) or i_max == 0:
        return "A"
    if i_max >= 1e-3:
        return "mA" if i_max < 1.0 else "A"
    if i_max >= 1e-6:
        return "uA"
    return "nA"


def _detectar_unidad_voltaje(df, col_v: str) -> str:
    v_max = df[col_v].abs().max()
    if not np.isfinite(v_max) or v_max == 0:
        return "V"
    return "mV" if v_max < 0.5 else "V"


def leer_excel_iv(ruta: Path) -> tuple[pd.DataFrame | None, str, str, str]:
    """Lee un Excel de medidas IV.

    Returns:
        (df, col_i, col_v, mensaje_error) — df es None si falla.
    """
    try:
        df = pd.read_excel(str(ruta), engine="openpyxl")
    except Exception as exc:
        return None, "", "", f"Error al leer {ruta.name}: {exc}"

    col_i = _detectar_columna(df.columns.tolist(), COL_CORRIENTE_CANDIDATAS)
    col_v = _detectar_columna(df.columns.tolist(), COL_VOLTAJE_CANDIDATAS)

    if col_i is None or col_v is None:
        return None, "", "", (
            f"{ruta.name}: no se reconocen columnas I/V. "
            f"Columnas encontradas: {list(df.columns)}"
        )

    df[col_i] = pd.to_numeric(df[col_i], errors="coerce")
    df[col_v] = pd.to_numeric(df[col_v], errors="coerce")
    df = df.dropna(subset=[col_i, col_v])

    if df.empty:
        return None, col_i, col_v, f"{ruta.name}: sin datos numéricos válidos."

    return df, col_i, col_v, ""


def escanear_carpeta(carpeta: str | Path) -> list[dict]:
    """Devuelve una lista de dicts con info de cada Excel encontrado.

    Cada dict: {ruta, nombre, col_i, col_v, unidad_i, unidad_v, error, df}
    """
    carpeta = Path(carpeta)
    resultados = []

    if not carpeta.exists():
        return resultados

    for ruta in sorted(carpeta.rglob("*.xlsx")):
        df, col_i, col_v, error = leer_excel_iv(ruta)
        entry = {
            "ruta": ruta,
            "nombre": ruta.name,
            "col_i": col_i,
            "col_v": col_v,
            "unidad_i": _detectar_unidad_corriente(df, col_i) if df is not None else "",
            "unidad_v": _detectar_unidad_voltaje(df, col_v) if df is not None else "",
            "error": error,
            "df": df,
        }
        resultados.append(entry)

    return resultados


def combinar_iv(
    entradas: list[dict],
    unidad_i: str = "mA",
    unidad_v: str = "V",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combina múltiples DataFrames IV normalizando a las unidades indicadas.

    Returns:
        (combined_iv, combined_summary)
        combined_iv: MultiIndex columns (archivo, variable)
        combined_summary: fila por medida con Isc, Voc, Pmax, FF
    """
    factor_i = UNIT_FACTORS["I"].get(unidad_i, 1.0)
    factor_v = UNIT_FACTORS["V"].get(unidad_v, 1.0)

    iv_frames = {}
    summary_rows = []

    for entrada in entradas:
        if entrada.get("error") or entrada.get("df") is None:
            continue

        df = entrada["df"].copy()
        col_i = entrada["col_i"]
        col_v = entrada["col_v"]
        nombre = entrada["nombre"]

        factor_i_src = UNIT_FACTORS["I"].get(entrada["unidad_i"], 1.0)
        factor_v_src = UNIT_FACTORS["V"].get(entrada["unidad_v"], 1.0)

        # Normalizar a unidades base (A, V) y luego a unidades destino
        i_vals = df[col_i].to_numpy(dtype=float) / factor_i_src * factor_i
        v_vals = df[col_v].to_numpy(dtype=float) / factor_v_src * factor_v

        iv_frames[nombre] = pd.DataFrame(
            {f"I ({unidad_i})": i_vals, f"V ({unidad_v})": v_vals}
        )

        # Resumen por archivo (Isc, Voc, Pmax, FF)
        try:
            row = _calcular_resumen(i_vals / factor_i, v_vals / factor_v, nombre, df)
            summary_rows.append(row)
        except Exception:
            pass

    if not iv_frames:
        return pd.DataFrame(), pd.DataFrame()

    combined_iv = pd.concat(iv_frames, axis=1)
    combined_iv.columns = pd.MultiIndex.from_tuples(
        [(a, b) for a, b in combined_iv.columns]
    )

    combined_summary = pd.DataFrame(summary_rows) if summary_rows else pd.DataFrame()
    return combined_iv, combined_summary


def _calcular_resumen(i_A, v_V, nombre, df_orig) -> dict:
    """Calcula métricas PV básicas para el resumen."""
    from core.postprocess.analysis import calcular_voc_isc, calcular_mpp_y_ff

    df_local = pd.DataFrame({"voltaje_V": v_V, "corriente_medida_A": i_A})

    # Añadir segmento si no existe
    if "segmento" not in df_local.columns:
        df_local["segmento"] = "directa"

    try:
        Voc, Isc = calcular_voc_isc(df_local)
        Pmax, Vmp, Imp, FF = calcular_mpp_y_ff(df_local, Voc, Isc)
    except Exception:
        Voc = Isc = Pmax = Vmp = Imp = FF = float("nan")

    row = {COL_ARCHIVO: nombre, "Voc (V)": Voc, "Isc (A)": Isc,
           "Pmax (W)": Pmax, "Vmp (V)": Vmp, "Imp (A)": Imp, "FF": FF}

    # Añadir datetime si existe en el Excel original
    if COL_DATETIME in df_orig.columns:
        row[COL_DATETIME] = df_orig[COL_DATETIME].iloc[0]
    if "Isc" in df_orig.columns:
        row["Isc"] = pd.to_numeric(df_orig["Isc"].iloc[0], errors="coerce")

    return row
