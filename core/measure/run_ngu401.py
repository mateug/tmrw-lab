"""Una medida I-V atómica: barrido, análisis, Excel y curvas."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import time
import numpy as np
import pandas as pd
from core.instrument.ngu401 import NGU401
from core.postprocess.analysis import calcular_fv
from core.postprocess.data import carpeta_experimento, guardar_medida, nombre_seguro
from core.plot.plotter import guardar_curvas
from core.utils import escribir_log


RANGOS_TENSION_NGU401 = np.array([6.0, 20.0])
RANGOS_CORRIENTE_NGU401 = np.array([10e-6, 1e-3, 10e-3, 100e-3, 3.0, 10.0])
MIN_LIMITE_CORRIENTE_NGU401_A = 20e-6


def construir_barrido(v_inicial_V: float, v_final_V: float, paso_V: float) -> np.ndarray:
    if paso_V <= 0:
        raise ValueError("El paso de tensión debe ser positivo.")
    inicio = float(v_inicial_V)
    final = float(v_final_V)
    paso = float(paso_V)
    signo = 1.0 if final >= inicio else -1.0
    distancia = abs(final - inicio)
    n_intervalos = int(np.floor(distancia / paso + 1e-10))
    tensiones = inicio + signo * paso * np.arange(n_intervalos + 1, dtype=float)
    if np.isclose(tensiones[-1], final, rtol=0.0, atol=1e-12):
        tensiones[-1] = final
    return tensiones


def construir_plan_medida(cfg: dict) -> list[dict]:
    modo = str(cfg["modo_medida"]).lower().strip()
    directa, inversa = cfg["directa"], cfg["inversa"]
    if modo not in {"directa", "inversa", "completa"}:
        raise ValueError("modo_medida debe ser directa, inversa o completa.")
    def segmento(nombre: str, inicio: float, final: float, paso: float) -> dict:
        return {"segmento": nombre, "tensiones_V": construir_barrido(inicio, final, paso)}
    v0 = float(directa["v_inicial_mV"]) * 1e-3
    directa_seg = segmento("directa", v0, float(directa["v_final_mV"]) * 1e-3, float(directa["paso_mV"]) * 1e-3)
    vi = v0 if inversa["v_inicial_mV"] is None else float(inversa["v_inicial_mV"]) * 1e-3
    inversa_seg = segmento("inversa", vi, float(inversa["v_final_V"]), float(inversa["paso_mV"]) * 1e-3)
    if modo == "directa":
        return [directa_seg]
    if modo == "inversa":
        return [inversa_seg]
    return [directa_seg, inversa_seg]


def validar_plan_ngu401(cfg: dict, segmentos: list[dict]) -> list[dict]:
    i_max = abs(float(cfg.get("compliance_hardware_A", cfg["i_max_A"])))
    if not 0 < i_max <= 8.0:
        raise ValueError("El límite de corriente debe estar entre 0 y 8 A.")
    if i_max < MIN_LIMITE_CORRIENTE_NGU401_A:
        raise ValueError("La compliance del NGU401 debe ser al menos 20 µA.")
    for segmento in segmentos:
        vmax = float(np.max(np.abs(segmento["tensiones_V"])))
        if vmax > 20.0 or vmax * i_max > 60.0:
            raise ValueError("El plan excede los límites de tensión o potencia del NGU401.")
        if vmax > 6.0 and i_max > 3.0:
            raise ValueError("Por encima de 6 V el NGU401 admite como máximo 3 A.")
    return segmentos


RUNTIME_CONFIG_KEYS = {
    "evento_aborto",
    "log_callback",
    "grafica_callback",
    "t0_experimento",
}


def copiar_configuracion_medida(cfg: dict) -> dict:
    """Copia solo la configuración de datos, excluyendo el estado runtime."""
    return deepcopy({
        clave: valor
        for clave, valor in cfg.items()
        if clave not in RUNTIME_CONFIG_KEYS
    })

def configuracion_dispositivo(cfg: dict, dispositivo: str, ciclo: int) -> dict:
    local = copiar_configuracion_medida(cfg)
    for clave in RUNTIME_CONFIG_KEYS:
        if clave in cfg:
            local[clave] = cfg[clave]

    curva = cfg["curva_iv"][dispositivo]
    local["directa"] = {"v_inicial_mV": float(curva["v_ini_dir_mV"]), "v_final_mV": float(curva["v_fin_dir_mV"]), "paso_mV": float(curva["paso_dir_mV"])}
    local["inversa"] = {"v_inicial_mV": float(curva["v_ini_inv_mV"]) if str(curva["v_ini_inv_mV"]).strip() else None, "v_final_V": float(curva["v_fin_inv_V"]), "paso_mV": float(curva["paso_inv_mV"])}
    limite_solicitado = abs(float(curva["i_max_uA"])) * 1e-6
    local["i_proteccion_solicitada_A"] = limite_solicitado
    local["i_max_A"] = max(limite_solicitado, MIN_LIMITE_CORRIENTE_NGU401_A)
    nombre_dispositivo = local["dispositivos"][dispositivo]["nombre"]
    local["nombre_medida"] = f"{nombre_seguro(nombre_dispositivo)}_ciclo_{ciclo:03d}"
    return local

def run_atomic(cfg: dict, dispositivo: str, ciclo: int, smu: NGU401 | None = None, guardar_archivos: bool = True) -> dict:
    local = configuracion_dispositivo(cfg, dispositivo, ciclo)
    nombre = local["dispositivos"][dispositivo]["nombre"]; inicio = datetime.now(); t0 = time.perf_counter()
    t0_exp = local.get("t0_experimento", t0)
    tiempo_transcurrido_s = max(0.0, t0 - t0_exp)
    escribir_log(cfg, "\n============================================================")
    escribir_log(cfg, f"        INICIO MEDIDA IV — {dispositivo}: {nombre}")
    escribir_log(cfg, "============================================================")
    segmentos = validar_plan_ngu401(local, construir_plan_medida(local))
    propio = smu is None; smu = smu or NGU401(local).connect()
    filas = []
    try:
        smu.initialize(local["i_max_A"], local["rango_corriente_A"])
        compliance_hw = local.get("compliance_hardware_A", local.get("i_max_A", 20e-6))
        escribir_log(
            cfg,
            f"Protección solicitada: {local['i_proteccion_solicitada_A'] * 1e6:g} uA; "
            f"compliance hardware: {compliance_hw * 1e6:g} uA.",
        )
        for segmento in segmentos:
            lecturas = smu.measure_segment(segmento["tensiones_V"], local.get("evento_aborto"))
            for indice, lectura in enumerate(lecturas, 1):
                corriente = -lectura.corriente_A if local["invertir_eje_y_graficas"] else lectura.corriente_A
                filas.append({"segmento": segmento["segmento"], "indice_segmento": indice, "tiempo_relativo_s": time.perf_counter()-t0, "voltaje_V": lectura.voltaje_V, "corriente_A": corriente, "potencia_W": lectura.voltaje_V*corriente})
    finally:
        smu.output_off()
        if propio: smu.close()
    datos = pd.DataFrame(filas); datos.insert(0, "indice_global", range(1, len(datos)+1))
    fv = calcular_fv(datos)
    resumen = {
        "Fecha y hora inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"),
        "Tiempo transcurrido (s)": round(tiempo_transcurrido_s, 2),
        "Estructura": dispositivo,
        "Nombre estructura": nombre,
        "Ciclo": ciclo,
        "Medida": local["modo_medida"],
        "Puntos": len(datos),
        f"Voc ({fv['Voc_unidad']})": fv["Voc_adapt"],
        f"Isc ({fv['Isc_unidad']})": fv["Isc_adapt"],
        f"Pmax ({fv['Pmax_unidad']})": fv["Pmax_adapt"],
        f"Vmp ({fv['Vmp_unidad']})": fv["Vmp_adapt"],
        f"Imp ({fv['Imp_unidad']})": fv["Imp_adapt"],
        "FF (%)": fv["FF"] * 100.0,
    }
    grafica_callback = cfg.get("grafica_callback")
    if callable(grafica_callback) and not datos.empty:
        grafica_callback(datos, local)
    ruta_excel = None; figuras = {}
    if guardar_archivos:
        base = carpeta_experimento(cfg) / local["nombre_medida"]; ruta_excel = base.with_suffix(".xlsx")
        guardar_medida(ruta_excel, datos, resumen); figuras = guardar_curvas(datos, base, f"{dispositivo} — {nombre}")
    escribir_log(cfg, "\nMEDIDA FINALIZADA - SMU DETENIDO")
    escribir_log(cfg, f"Puntos medidos        : {len(datos)}")
    escribir_log(cfg, f"Tiempo de iteración   : {time.perf_counter()-t0:.3f} s")
    escribir_log(
        cfg,
        f"Voc = {fv['Voc_adapt']:.6g} {fv['Voc_unidad']} | "
        f"Isc = {fv['Isc_adapt']:.6g} {fv['Isc_unidad']} | "
        f"Pmax = {fv['Pmax_adapt']:.6g} {fv['Pmax_unidad']} | "
        f"Vmp = {fv['Vmp_adapt']:.6g} {fv['Vmp_unidad']} | "
        f"Imp = {fv['Imp_adapt']:.6g} {fv['Imp_unidad']} | "
        f"FF = {fv['FF']:.4g}",
    )
    if ruta_excel: escribir_log(cfg, f"Resultados guardados en: {ruta_excel.name}")
    return {"datos": datos, "resumen": resumen, "ruta_excel": str(ruta_excel) if ruta_excel else None, "rutas_figuras": figuras}
