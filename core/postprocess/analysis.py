import datetime
import numpy as np
import pandas as pd


def interpolar_x_en_y_cero(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    mascara = np.isfinite(x) & np.isfinite(y)
    x = x[mascara]
    y = y[mascara]

    if x.size == 0:
        return np.nan

    idx_cero = np.where(y == 0)[0]
    if idx_cero.size > 0:
        return float(x[idx_cero[0]])

    cambios = np.where(y[:-1] * y[1:] < 0)[0]

    if cambios.size > 0:
        k = cambios[np.argmin(np.abs(y[cambios]) + np.abs(y[cambios + 1]))]
        x1, x2 = x[k], x[k + 1]
        y1, y2 = y[k], y[k + 1]
        return float(x1 + (0 - y1) * (x2 - x1) / (y2 - y1))

    if x.size < 2:
        return np.nan

    idx = np.argsort(np.abs(y))[:2]
    x1, x2 = x[idx[0]], x[idx[1]]
    y1, y2 = y[idx[0]], y[idx[1]]

    if y2 == y1:
        return float(x1)

    return float(x1 + (0 - y1) * (x2 - x1) / (y2 - y1))


def calcular_voc_isc(df):
    V = df["voltaje_V"].to_numpy(dtype=float)
    I = df["corriente_medida_A"].to_numpy(dtype=float)

    Voc = interpolar_x_en_y_cero(V, I)
    Isc = interpolar_x_en_y_cero(I, V)

    return Voc, Isc


def valores_absolutos_para_log(serie):
    valores = np.abs(np.asarray(serie, dtype=float))
    return np.where(valores > 0, valores, np.nan)


def seleccionar_escala_corriente(i_referencia_A):
    i_ref = abs(float(i_referencia_A))

    if i_ref >= 1.0:
        return 1.0, "A"
    if i_ref >= 1e-3:
        return 1e3, "mA"
    if i_ref >= 1e-6:
        return 1e6, "uA"
    if i_ref >= 1e-9:
        return 1e9, "nA"

    return 1e12, "pA"


def seleccionar_escala_potencia(p_referencia_W):
    p_ref = abs(float(p_referencia_W))

    if p_ref >= 1.0:
        return 1.0, "W"
    if p_ref >= 1e-3:
        return 1e3, "mW"
    if p_ref >= 1e-6:
        return 1e6, "uW"
    if p_ref >= 1e-9:
        return 1e9, "nW"

    return 1e12, "pW"


def calcular_mpp_y_ff(df_directa, Voc, Isc, invertir_eje_y=False):
    if df_directa.empty:
        return np.nan, np.nan, np.nan, np.nan

    P = df_directa["potencia_W"].to_numpy(dtype=float)
    V = df_directa["voltaje_V"].to_numpy(dtype=float)
    I = df_directa["corriente_medida_A"].to_numpy(dtype=float)

    mascara = np.isfinite(P) & np.isfinite(V) & np.isfinite(I)
    if not np.any(mascara):
        return np.nan, np.nan, np.nan, np.nan

    P_ok = P[mascara]
    V_ok = V[mascara]
    I_ok = I[mascara]

    # El sentido/signo usado para dibujar la curva no debe decidir el MPP.
    # El punto de máxima potencia fotovoltaica es el de mayor |V*I|.
    if invertir_eje_y:
        idx = int(np.nanargmax(P_ok))
    else:
        idx = int(np.nanargmin(P_ok))

    Pmax = float(abs(P_ok[idx]))
    V_Pmax = float(V_ok[idx])
    I_Pmax = float(I_ok[idx])

    denominador = abs(Voc * Isc)
    FF = Pmax / denominador if denominador > 0 else np.nan

    return Pmax, V_Pmax, I_Pmax, FF


def calcular_resultados_fotovoltaicos(cfg, Voc, Isc, Pmax, Vmp, Imp):
    superficie_um2 = cfg.get("superficie_um2", None)
    irradiancia_mW_cm2 = cfg.get("irradiancia_mW_cm2", None)

    Isc_uA = Isc * 1e6 if np.isfinite(Isc) else np.nan
    Imp_uA = Imp * 1e6 if np.isfinite(Imp) else np.nan
    Pmax_uW = Pmax * 1e6 if np.isfinite(Pmax) else np.nan

    Jsc_mA_cm2 = np.nan
    power_density_mW_cm2 = np.nan
    Eff = np.nan

    if superficie_um2 is not None and np.isfinite(superficie_um2) and superficie_um2 > 0:
        if np.isfinite(Isc_uA):
            Jsc_mA_cm2 = abs(Isc_uA) * 1e5 / superficie_um2
        if np.isfinite(Pmax_uW):
            power_density_mW_cm2 = abs(Pmax_uW) * 1e5 / superficie_um2

        if (
            irradiancia_mW_cm2 is not None
            and np.isfinite(irradiancia_mW_cm2)
            and irradiancia_mW_cm2 > 0
            and np.isfinite(power_density_mW_cm2)
        ):
            Eff = 100.0 * power_density_mW_cm2 / irradiancia_mW_cm2

    factor_I, unidad_I = seleccionar_escala_corriente(
        np.nanmax(np.abs([Isc, Imp])) if np.any(np.isfinite([Isc, Imp])) else 1.0
    )
    Isc_adapt = Isc * factor_I if np.isfinite(Isc) else np.nan
    Imp_adapt = Imp * factor_I if np.isfinite(Imp) else np.nan

    factor_P, unidad_P = seleccionar_escala_potencia(Pmax if np.isfinite(Pmax) else 1.0)
    Pmax_adapt = Pmax * factor_P if np.isfinite(Pmax) else np.nan

    return {
        "Voc_V": Voc,
        "Voc_mV": Voc * 1e3 if np.isfinite(Voc) else np.nan,
        "Isc_A": Isc,
        "Isc_adapt": Isc_adapt,
        "Isc_unidad": unidad_I,
        "Pmax_W": Pmax,
        "Pmax_adapt": Pmax_adapt,
        "Pmax_unidad": unidad_P,
        "Vmp_V": Vmp,
        "Vmp_mV": Vmp * 1e3 if np.isfinite(Vmp) else np.nan,
        "Imp_A": Imp,
        "Imp_adapt": Imp_adapt,
        "Imp_unidad": unidad_I,
        "FF": Pmax / abs(Voc * Isc) if np.isfinite(Pmax) and np.isfinite(Voc) and np.isfinite(Isc) and abs(Voc * Isc) > 0 else np.nan,
        "superficie_um2": superficie_um2,
        "irradiancia_mW_cm2": irradiancia_mW_cm2,
        "Jsc_mA_cm2": Jsc_mA_cm2,
        "Densidad_potencia_mW_cm2": power_density_mW_cm2,
        "Eff": Eff,
    }


def texto_numero(valor, precision=3):
    if valor is None:
        return "N/A"
    try:
        valor = float(valor)
    except Exception:
        return "N/A"
    if not np.isfinite(valor):
        return "N/A"
    return f"{valor:.{precision}f}"


def numero_resumen(valor, precision=3):
    if valor is None:
        return np.nan
    try:
        valor = float(valor)
    except Exception:
        return np.nan
    if not np.isfinite(valor):
        return np.nan
    return round(valor, precision)


def crear_resumen_excel(cfg, resultados):
    """
    Crea la hoja resumen sin duplicar magnitudes en unidades base y adaptativas.

    Criterios:
      - Las magnitudes numericas se redondean a 3 decimales.
      - Las unidades van siempre entre parentesis en el nombre de la columna.
      - Para corriente y potencia se conserva solo la escala adaptativa.
      - Las magnitudes derivadas de superficie/irradiancia solo aparecen si esos datos existen.
    """
    fecha_hora = cfg.get("fecha_hora_inicio_medida")
    if isinstance(fecha_hora, datetime.datetime):
        fecha_hora = fecha_hora.strftime("%Y-%m-%d %H:%M:%S")

    fila = {
        "Fecha y hora inicio": fecha_hora,
        "Medida": cfg["modo_medida"],
        "Imax (uA)": numero_resumen(cfg.get("i_max_uA", np.nan)),
        "Voc (mV)": numero_resumen(resultados["Voc_mV"]),
        f"Isc ({resultados['Isc_unidad']})": numero_resumen(resultados["Isc_adapt"]),
        "Vmp (mV)": numero_resumen(resultados["Vmp_mV"]),
        f"Imp ({resultados['Imp_unidad']})": numero_resumen(resultados["Imp_adapt"]),
        f"Pmax ({resultados['Pmax_unidad']})": numero_resumen(resultados["Pmax_adapt"]),
        "FF (%)": numero_resumen(resultados["FF"] * 100.0),
    }

    posicion_pasos = cfg.get("posicion_motor_pasos")
    if posicion_pasos is not None:
        fila["Posición eje (pasos)"] = int(posicion_pasos)

    posicion_motor = cfg.get("posicion_motor_mm")
    if posicion_motor is not None and np.isfinite(float(posicion_motor)):
        fila["Posición eje (mm)"] = numero_resumen(
            posicion_motor, precision=6
        )

    superficie = resultados.get("superficie_um2", None)
    irradiancia = resultados.get("irradiancia_mW_cm2", None)

    if superficie is not None and np.isfinite(superficie) and superficie > 0:
        fila["Superficie activa (um^2)"] = numero_resumen(superficie)
        fila["Jsc (mA/cm^2)"] = numero_resumen(resultados["Jsc_mA_cm2"])
        fila["Densidad de potencia (mW/cm^2)"] = numero_resumen(resultados["Densidad_potencia_mW_cm2"])

    if irradiancia is not None and np.isfinite(irradiancia) and irradiancia > 0:
        fila["Irradiancia (mW/cm^2)"] = numero_resumen(irradiancia)

    if (
        superficie is not None and np.isfinite(superficie) and superficie > 0
        and irradiancia is not None and np.isfinite(irradiancia) and irradiancia > 0
    ):
        fila["Eff (%)"] = numero_resumen(resultados["Eff"])

    return pd.DataFrame([fila])


# ---------------------------------------------------------------------------
# Alias unificado para compatibilidad con devices-degradation
# ---------------------------------------------------------------------------

def calcular_fv(df) -> dict:
    """Alias que envuelve las funciones PV para compatibilidad con run_ngu401."""
    import numpy as np
    import pandas as pd
    from .analysis import (
        calcular_voc_isc, calcular_mpp_y_ff,
        seleccionar_escala_corriente, seleccionar_escala_potencia,
    )
    V = df['voltaje_V'].to_numpy(dtype=float) if 'voltaje_V' in df.columns else df.iloc[:, 0].to_numpy()
    I_col = 'corriente_medida_A' if 'corriente_medida_A' in df.columns else 'corriente_A'

    df_dir = df[df['segmento'] == 'directa'].copy() if 'segmento' in df.columns else df.copy()
    if df_dir.empty:
        df_dir = df.copy()

    Voc, Isc = calcular_voc_isc(df_dir.rename(columns={'corriente_A': 'corriente_medida_A'}))
    Pmax, Vmp, Imp, FF = calcular_mpp_y_ff(df_dir.rename(columns={'corriente_A': 'corriente_medida_A'}), Voc, Isc)

    factor_I, unidad_I = seleccionar_escala_corriente(abs(Isc) if np.isfinite(Isc) else 1.0)
    factor_V, unidad_V = (1e3, 'mV') if abs(Voc) < 10 else (1.0, 'V')
    factor_P, unidad_P = seleccionar_escala_potencia(abs(Pmax) if np.isfinite(Pmax) else 1.0)

    return {
        'Voc_V': Voc, 'Voc_adapt': Voc * factor_V, 'Voc_unidad': unidad_V,
        'Isc_A': Isc, 'Isc_adapt': Isc * factor_I, 'Isc_unidad': unidad_I,
        'Pmax_W': Pmax, 'Pmax_adapt': Pmax * factor_P, 'Pmax_unidad': unidad_P,
        'Vmp_V': Vmp, 'Vmp_adapt': Vmp * factor_V, 'Vmp_unidad': unidad_V,
        'Imp_A': Imp, 'Imp_adapt': Imp * factor_I, 'Imp_unidad': unidad_I,
        'FF': FF,
    }
