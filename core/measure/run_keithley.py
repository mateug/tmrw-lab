import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyvisa

from core.instrument import keithley
from core.instrument.registry import registrar_instrumento_activo, limpiar_instrumento_activo, abortar_instrumento_activo
from core.postprocess.data import construir_rutas_salida, preparar_datos_excel, eliminar_archivo_previo
from core.postprocess.analysis import calcular_voc_isc, calcular_mpp_y_ff, calcular_resultados_fotovoltaicos, crear_resumen_excel
from core.plot.plotter import representar_curvas_iv_pv
from core.utils import emitir_log, formatear_resultados_fotovoltaicos
from core.exceptions import LimiteCorrienteAlcanzado, MedidaAbortadaPorUsuario


RANGOS_TENSION_2450 = np.array([0.02, 0.2, 2.0, 20.0, 200.0])
RANGOS_CORRIENTE_2450 = np.array([
    10e-9, 100e-9, 1e-6, 10e-6, 100e-6,
    1e-3, 10e-3, 100e-3, 1.0
])


def elegir_rango(valor_maximo, rangos_disponibles, nombre):
    valor_maximo = abs(float(valor_maximo))
    candidatos = rangos_disponibles[rangos_disponibles >= valor_maximo]
    if candidatos.size == 0:
        raise ValueError(
            f"No hay rango disponible para {nombre}={valor_maximo:g}. "
            f"Rango máximo permitido: {rangos_disponibles[-1]:g}."
        )
    return float(candidatos[0])


def construir_barrido(v_ini, v_fin, paso):
    if paso <= 0:
        raise ValueError("El paso de tensión debe ser positivo.")
    signo = 1 if v_fin >= v_ini else -1
    return np.arange(v_ini, v_fin + signo * paso / 2, signo * paso)


def construir_segmento_desde_tensiones(nombre, tensiones, paso):
    tensiones = np.asarray(tensiones, dtype=float)
    if tensiones.size == 0:
        return None
    return {
        "segmento": nombre,
        "v_inicial_V": float(tensiones[0]),
        "v_final_V": float(tensiones[-1]),
        "paso_V": float(abs(paso)),
        "n_puntos": int(len(tensiones)),
        "tensiones_V": tensiones,
    }


def normalizar_segmento(nombre, cfg_segmento, modo_medida, cfg_directa=None):
    if nombre == "directa":
        v_ini = cfg_segmento["v_inicial_mV"] * 1e-3
        v_fin = cfg_segmento["v_final_mV"] * 1e-3
        paso = cfg_segmento["paso_mV"] * 1e-3
    elif nombre == "inversa":
        if cfg_segmento.get("v_inicial_mV") is None:
            if modo_medida != "completa" or cfg_directa is None:
                raise ValueError("En modo inversa independiente debes especificar V_i (mV).")
            v_inicial_mV = cfg_directa["v_inicial_mV"]
        else:
            v_inicial_mV = cfg_segmento["v_inicial_mV"]
        v_ini = v_inicial_mV * 1e-3
        v_fin = cfg_segmento["v_final_V"]
        paso = cfg_segmento["paso_mV"] * 1e-3
    else:
        raise ValueError(f"Segmento desconocido: {nombre}")

    tensiones = construir_barrido(v_ini, v_fin, paso)
    return {
        "segmento": nombre,
        "v_inicial_V": float(v_ini),
        "v_final_V": float(v_fin),
        "paso_V": float(paso),
        "n_puntos": int(len(tensiones)),
        "tensiones_V": tensiones,
    }


def construir_plan_medida(cfg):
    modo = cfg["modo_medida"].strip().lower()
    if modo not in {"directa", "inversa", "completa"}:
        raise ValueError("modo_medida debe ser 'directa', 'inversa' o 'completa'.")

    if modo == "directa":
        segmentos = [normalizar_segmento("directa", cfg["directa"], modo)]
    elif modo == "inversa":
        segmentos = [normalizar_segmento("inversa", cfg["inversa"], modo)]
    else:
        v_union = float(cfg["directa"]["v_inicial_mV"]) * 1e-3
        v_directa_final = float(cfg["directa"]["v_final_mV"]) * 1e-3
        paso_directa = float(cfg["directa"]["paso_mV"]) * 1e-3

        v_inversa_final = float(cfg["inversa"]["v_final_V"])
        paso_inversa = float(cfg["inversa"]["paso_mV"]) * 1e-3

        if paso_directa <= 0 or paso_inversa <= 0:
            raise ValueError("Los pasos de tensión deben ser positivos.")

        tensiones_directa = construir_barrido(v_directa_final, v_union, paso_directa)
        tensiones_inversa = construir_barrido(v_union, v_inversa_final, paso_inversa)

        segmentos = []
        directa = construir_segmento_desde_tensiones("directa", tensiones_directa, paso_directa)
        inversa = construir_segmento_desde_tensiones("inversa", tensiones_inversa, paso_inversa)
        if directa is not None:
            segmentos.append(directa)
        if inversa is not None:
            segmentos.append(inversa)

    return segmentos


def validar_segmentos_y_configuracion(cfg, segmentos):
    i_max = abs(float(cfg["i_max_A"]))
    if i_max <= 0:
        raise ValueError("i_max_A debe ser positivo.")
    if i_max > 1:
        raise ValueError("El Keithley 2450 no debe superar ±1 A.")

    rango_i = cfg.get("rango_corriente_A")
    if rango_i is None:
        rango_i = elegir_rango(i_max, RANGOS_CORRIENTE_2450, "corriente")
    else:
        rango_i = abs(float(rango_i))
        if rango_i < i_max:
            raise ValueError("El rango de corriente debe ser mayor o igual que i_max_A.")
        rango_i = elegir_rango(rango_i, RANGOS_CORRIENTE_2450, "corriente")

    for seg in segmentos:
        vmax = max(abs(seg["v_inicial_V"]), abs(seg["v_final_V"]))
        if vmax > 200:
            raise ValueError("El Keithley 2450 no debe superar ±200 V.")
        if vmax * i_max > 20:
            raise ValueError(
                f"El segmento {seg['segmento']} supera el límite de potencia de 20 W. "
                f"Vmax*Imax = {vmax * i_max:g} W."
            )
        seg["rango_tension_V"] = elegir_rango(vmax, RANGOS_TENSION_2450, "tensión")
        seg["limite_corriente_A"] = i_max
        seg["rango_corriente_A"] = rango_i

    return segmentos


def aplicar_inversion_datos(df, invertir_eje_y=False):
    df = df.copy()

    factor = -1 if invertir_eje_y else 1

    df["corriente_medida_A"] = factor * df["corriente_medida_A"]
    df["potencia_W"] = df["voltaje_V"] * df["corriente_medida_A"]

    return df


def run(cfg=None, callback_fin_medida=None):
    t_programa_ini = time.perf_counter()

    if cfg is None:
        from core.config.schemas import get_default_config

        cfg = get_default_config()

    def log(*args, **kwargs):
        emitir_log(cfg, *args, **kwargs)

    segmentos = construir_plan_medida(cfg)
    segmentos = validar_segmentos_y_configuracion(cfg, segmentos)

    n_puntos_total = sum(seg["n_puntos"] for seg in segmentos)

    inst = keithley.conectar_y_verificar(cfg["recurso_visa"])
    registrar_instrumento_activo(inst)

    inst.timeout = 60000
    inst.write_termination = "\n"
    inst.read_termination = "\n"

    dfs = []
    tiempos_segmentos = []
    estado_medida = "correcta"
    mensaje_limite_corriente = None

    try:
        idn = inst.query("*IDN?").strip()

        es_rapida = cfg.get("es_medida_rapida", False)

        log("============================================================")
        if es_rapida:
            log("        INICIO DE MEDIDA RAPIDA (TEST / CALIBRACION)")
        else:
            log("                INICIO DE NUEVA MEDIDA")
        log("============================================================")
        # Temporalmente omitidos del log de usuario.
        # log(f"Instrumento detectado: {idn}")
        # log(f"Modo de medida       : {cfg['modo_medida']}")
        # log(f"Puntos totales       : {n_puntos_total}")

        keithley.inicializar_instrumento(inst, cfg)

        if cfg.get("fecha_hora_inicio_medida") is None:
            cfg["fecha_hora_inicio_medida"] = datetime.now()

        for i, seg in enumerate(segmentos, start=1):
            # log(f"\n--- SEGMENTO {i}/{len(segmentos)}: {seg['segmento']} ---")
            # log(
            # f"Configurando segmento: {seg['v_inicial_V']:.6g} V -> {seg['v_final_V']:.6g} V, "
            # f"({seg['v_inicial_V']:.6g} V -> {seg['v_final_V']:.6g} V, "
            # f"paso {seg['paso_V']:.6g} V, {seg['n_puntos']} puntos)"
            # )
            # log(
            # f"Paso: {seg['paso_V']:.6g} V | {seg['n_puntos']} puntos | "
            # f"Rango V: {seg['rango_tension_V']} V | "
            # f"I_limit: {seg['limite_corriente_A']} A | "
            # f"Rango I: {seg['rango_corriente_A']} A"
            # )

            keithley.configurar_sweep_interno(inst, seg, cfg)

            # log("Iniciando medida...")

            if cfg.get("abortar_si_limite_corriente", True):
                tiempo_medida, df_seg = keithley.ejecutar_sweep_seguro_punto_a_punto(inst, seg, cfg)
                dfs.append(df_seg)
            else:
                tiempo_medida = keithley.ejecutar_sweep(inst, cfg)
                # log("Leyendo buffer...")
                df_seg = keithley.leer_buffer(inst, seg["n_puntos"], seg["segmento"])
                dfs.append(df_seg)

            tiempos_segmentos.append({
                "segmento": seg["segmento"],
                "tiempo_medida_s": tiempo_medida,
            })

    except MedidaAbortadaPorUsuario as exc:
        estado_medida = "abortada_usuario"
        log("\n" + "!" * 70)
        log(str(exc))
        log("!" * 70 + "\n")

        if exc.df_parcial is not None and not exc.df_parcial.empty:
            dfs.append(exc.df_parcial)

        if not cfg.get("guardar_parcial_si_aborta", True):
            dfs = []

    except LimiteCorrienteAlcanzado as exc:
        estado_medida = "warning_limite_corriente"
        mensaje_limite_corriente = str(exc)
        log("\n" + "!" * 70)
        log(str(exc))
        log("!" * 70 + "\n")

        if exc.df_parcial is not None and not exc.df_parcial.empty:
            dfs.append(exc.df_parcial)

        if not cfg.get("guardar_parcial_si_aborta", True):
            dfs = []

    finally:
        keithley.apagar_seguro(inst)
        limpiar_instrumento_activo(inst)
        try:
            inst.close()
        except Exception:
            pass

    if not dfs:
        estado_medida = "abortada_sin_datos"

    if callback_fin_medida is not None:
        if estado_medida == "correcta":
            mensaje_usuario = (
                "El SMU ha terminado de medir correctamente. Aparta la muestra de la fuente.\n\n"
            )
        elif estado_medida == "warning_limite_corriente":
            mensaje_usuario = (
                "WARNING: la medida se ha detenido al alcanzar el lí­mite de corriente.\n"
            )
        elif estado_medida == "abortada_usuario":
            mensaje_usuario = "La medida ha sido abortada por el usuario.\n"
        else:
            mensaje_usuario = (
                "WARNING: la medida se ha detenido al alcanzar el lí­mite de corriente.\n"
            )

        callback_fin_medida(estado_medida, mensaje_usuario, mensaje_limite_corriente)

    if not dfs:
        log("\n============================================================")
        log("MEDIDA ABORTADA - SMU DETENIDO")
        log("No hay datos parciales que guardar.")
        log("============================================================\n")
        return {"estado_medida": estado_medida, "puntos_medidos": 0, "df": None}

    log("\nMEDIDA FINALIZADA - SMU DETENIDO")

    df_original = pd.concat(dfs, ignore_index=True)
    df_original.insert(0, "indice_global", np.arange(1, len(df_original) + 1))

    df = aplicar_inversion_datos(
        df_original,
        invertir_eje_y=cfg.get("invertir_eje_y_graficas", False),
    )

    calcular_magnitudes_fv = cfg["modo_medida"].strip().lower() != "inversa"
    resultados_fv = None

    if calcular_magnitudes_fv:
        df_directa = df[df["segmento"] == "directa"].copy()
        if df_directa.empty:
            df_directa = df.copy()

        Voc, Isc = calcular_voc_isc(df_directa)
        Pmax, Vmp, Imp, FF = calcular_mpp_y_ff(
            df_directa,
            Voc,
            Isc,
            invertir_eje_y=cfg.get("invertir_eje_y_graficas", False),
        )

        resultados_fv = calcular_resultados_fotovoltaicos(cfg, Voc, Isc, Pmax, Vmp, Imp)

    ruta = None
    rutas_figuras_generadas = {}

    if not es_rapida and cfg.get("guardar_archivos", True):
        ruta, rutas_figuras = construir_rutas_salida(cfg)
        ruta.parent.mkdir(parents=True, exist_ok=True)

        df_datos_excel = preparar_datos_excel(df)

        if resultados_fv is not None:
            df_resumen = crear_resumen_excel(cfg, resultados_fv)
        else:
            fecha_hora = cfg.get("fecha_hora_inicio_medida")
            if isinstance(fecha_hora, datetime):
                fecha_hora = fecha_hora.strftime("%Y-%m-%d %H:%M:%S")
            df_resumen = pd.DataFrame([{
                "Fecha y hora inicio": fecha_hora,
                "Medida": cfg["modo_medida"],
                "Imax (uA)": np.nan,
            }])

        eliminar_archivo_previo(ruta)
        with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
            df_datos_excel.to_excel(writer, sheet_name="datos_IV", index=False)
            df_resumen.to_excel(writer, sheet_name="resumen", index=False)

        rutas_figuras_generadas = representar_curvas_iv_pv(
            df,
            rutas_figuras,
            cfg,
        )

    tiempo_medida_total = sum(t["tiempo_medida_s"] for t in tiempos_segmentos)
    tiempo_iteracion = time.perf_counter() - t_programa_ini
    tiempo_acumulado = time.perf_counter() - float(cfg.get("_tiempo_inicio_proceso_s", t_programa_ini))

    log("\n")
    if es_rapida:
        log("RESUMEN DE MEDIDA RAPIDA (TEST / CALIBRACION)")
    else:
        log("RESUMEN DE MEDIDA")
    log(f"Puntos medidos        : {len(df)}")
    log(f"Tiempo de iteración   : {tiempo_iteracion:.3f} s")
    log(f"Tiempo de barrido     : {tiempo_medida_total:.3f} s")
    log(f"Tiempo total acumulado: {tiempo_acumulado:.3f} s")
    log(formatear_resultados_fotovoltaicos(resultados_fv))
    if not es_rapida and ruta is not None:
        log(f"Resultados guardados en: {ruta.name}")
    else:
        log("Medida rápida de test finalizada (no se guardan archivos en disco).")

    # Invocar callback de gráfica para actualizar la UI en tiempo real
    cb_grafica = cfg.get("grafica_callback")
    if callable(cb_grafica):
        try:
            cb_grafica(df, cfg)
        except Exception:
            pass

    salida = {
        "estado_medida": estado_medida,
        "ruta_excel": str(ruta.resolve()) if (not es_rapida and ruta is not None) else None,
        "rutas_figuras": {k: str(v.resolve()) for k, v in rutas_figuras_generadas.items()},
        "puntos_medidos": int(len(df)),
        "tiempo_iteracion_s": float(tiempo_iteracion),
        "tiempo_acumulado_s": float(tiempo_acumulado),
        "df": df,
    }

    if resultados_fv is not None:
        salida["resultados_fv"] = resultados_fv

    return salida
