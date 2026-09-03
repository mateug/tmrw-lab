"""Construcción y validación independiente de hardware de barridos I-V."""
import numpy as np

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

def construir_barrido_decreciente(v_extremo_a: float, v_extremo_b: float, paso_V: float) -> np.ndarray:
    """Construye un barrido desde la tensión mayor hasta la menor."""
    return construir_barrido(max(float(v_extremo_a), float(v_extremo_b)),
                             min(float(v_extremo_a), float(v_extremo_b)), paso_V)

def construir_plan_medida(cfg: dict) -> list[dict]:
    """Devuelve segmentos directos/inversos sin abrir una conexión VISA."""
    modo = str(cfg["modo_medida"]).lower().strip()
    directa, inversa = cfg["directa"], cfg["inversa"]
    if modo not in {"directa", "inversa", "completa"}:
        raise ValueError("modo_medida debe ser directa, inversa o completa.")
    def segmento(nombre: str, inicio: float, final: float, paso: float) -> dict:
        return {"segmento": nombre, "tensiones_V": construir_barrido_decreciente(inicio, final, paso)}
    v0 = float(directa["v_inicial_mV"]) * 1e-3
    directa_seg = segmento("directa", float(directa["v_final_mV"]) * 1e-3, v0, float(directa["paso_mV"]) * 1e-3)
    vi = v0 if inversa["v_inicial_mV"] is None else float(inversa["v_inicial_mV"]) * 1e-3
    inversa_seg = segmento("inversa", vi, float(inversa["v_final_V"]), float(inversa["paso_mV"]) * 1e-3)
    if modo == "directa":
        return [directa_seg]
    if modo == "inversa":
        return [inversa_seg]
    return [directa_seg, inversa_seg]

def validar_plan_ngu401(cfg: dict, segmentos: list[dict]) -> list[dict]:
    """Valida límites eléctricos nominales del NGU401 antes de medir."""
    i_max = abs(float(cfg.get("compliance_hardware_A", cfg.get("i_max_A", 20e-6))))
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
