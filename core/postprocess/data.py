from pathlib import Path
import numpy as np
import pandas as pd

from core.utils import preparar_carpeta_medida, sanitizar_nombre_archivo


def construir_rutas_salida(cfg):
    carpeta = Path(cfg.get("carpeta_salida_medida") or preparar_carpeta_medida(cfg))
    nombre = sanitizar_nombre_archivo(cfg["nombre_medida"])

    ruta_excel = carpeta / f"{nombre}.xlsx"
    rutas_figuras = {
        "lineal": carpeta / f"{nombre}_lineal.png",
        "log_y": carpeta / f"{nombre}_log_y.png",
    }

    return ruta_excel, rutas_figuras


def eliminar_archivo_previo(ruta):
    ruta = Path(ruta)
    if not ruta.exists():
        return

    try:
        ruta.unlink()
    except PermissionError as exc:
        raise PermissionError(
            f"No se pudo sobrescribir el archivo porque está abierto o bloqueado:\n{ruta}\n\n"
            "Cierra Excel, el visor de imágenes o cualquier programa que lo esté usando "
            "y vuelve a lanzar la medida."
        ) from exc


def preparar_datos_excel(df):
    df_excel = pd.DataFrame({
        "t (seg)": df["tiempo_relativo_s"],
        "V (V)": df["voltaje_V"],
        "I (A)": df["corriente_medida_A"],
        "P (W)": df["potencia_W"],
    })
    return df_excel


def guardar_resumen_repetitividad_excel(cfg_base, filas_resumen):
    if not filas_resumen:
        return None

    ruta_base, _ = construir_rutas_salida(cfg_base)
    ruta = ruta_base.with_name(f"{ruta_base.stem}_medidas_repetitivas.xlsx")
    ruta.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(filas_resumen)
    eliminar_archivo_previo(ruta)
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="resumen_repetitividad", index=False)

    return str(ruta.resolve())


def guardar_resumen_barrido_motor_excel(cfg_base, filas_resumen):
    if not filas_resumen:
        return None

    ruta_base, _ = construir_rutas_salida(cfg_base)
    ruta = ruta_base.with_name(f"{ruta_base.stem}_barrido_motor.xlsx")
    ruta.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(filas_resumen)
    eliminar_archivo_previo(ruta)
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="resumen_barrido_motor", index=False)

    return str(ruta.resolve())


def guardar_resumen_irradiancia_excel(cfg_base, filas_resumen):
    if not filas_resumen:
        return None

    ruta_base, _ = construir_rutas_salida(cfg_base)
    submodo = cfg_base.get("irradiancia_modo", "potencia")
    if submodo == "potencia":
        sufijo = "resumen_potencias_sol"
    elif submodo in {"combinacion", "combinación", "multi_longitud_onda"}:
        sufijo = "resumen_combinacion_longitudes_onda"
    elif submodo in {"multiples_combinaciones", "multiples_multi_canal"}:
        sufijo = "resumen_multiples_combinaciones"
    elif submodo == "lectura_excel":
        sufijo = "resumen_lectura_excel"
    else:
        sufijo = "resumen_longitudes_onda"
    ruta = ruta_base.with_name(f"{ruta_base.stem}_{sufijo}.xlsx")
    ruta.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(filas_resumen)
    eliminar_archivo_previo(ruta)
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sufijo, index=False)

    return str(ruta.resolve())


def leer_combinaciones_excel(ruta, hoja=None, valores_en_tanto_por_uno=True):
    """
    Lee un excel de entrada con una fila de cabecera (nombres de canal/longitud de
    onda) y una fila por combinación de intensidades a medir.

    Acepta nombres de canal como "Cool White" y "Warm White" sin distinguir
    mayúsculas/minúsculas.

    Devuelve una tupla (df_original, canales, filas_combinaciones):
      - df_original: DataFrame tal cual se ha leí­do (columnas ya con espacios
        limpiados), usado luego para reconstruir el excel de salida.
      - canales: lista de nombres de columna/canal detectados.
      - filas_combinaciones: lista de dicts {canal: intensidad_pct} en el mismo
        orden que las filas del excel, con NaN filtrados.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encuentra el archivo Excel de combinaciones:\n{ruta}")

    if hoja:
        df_original = pd.read_excel(ruta, sheet_name=hoja, engine="openpyxl")
    else:
        df_original = pd.read_excel(ruta, sheet_name=0, engine="openpyxl")

    # Limpiamos nombres de columna.
    df_original.columns = [str(c).strip() for c in df_original.columns]

    # Descartamos columnas "Unnamed" completamente vací­as.
    df_original = df_original.dropna(axis=1, how="all")
    df_original = df_original.loc[:, ~df_original.columns.str.startswith("Unnamed")]

    if df_original.empty or len(df_original.columns) == 0:
        raise ValueError("El Excel de combinaciones no contiene columnas/canales validos.")

    # Normalización de nombres de canal:
    # permite Cool White / cool white / COOL WHITE / etc.
    mapa_canales = {}

    for canal in df_original.columns:
        canal_limpio = str(canal).strip()
        canal_normalizado = canal_limpio.casefold()

        if canal_normalizado == "cool white":
            mapa_canales[canal] = "Cool White"
        elif canal_normalizado == "warm white":
            mapa_canales[canal] = "Warm White"
        else:
            mapa_canales[canal] = canal_limpio

    canales = list(mapa_canales.values())

    filas_combinaciones = []

    for _, fila in df_original.iterrows():
        combinacion = {}

        for canal_original in df_original.columns:
            valor = fila[canal_original]

            if pd.isna(valor):
                continue

            valor_pct = (
                float(valor) * 100.0
                if valores_en_tanto_por_uno
                else float(valor)
            )

            canal = mapa_canales[canal_original]
            combinacion[canal] = valor_pct

        if combinacion:
            filas_combinaciones.append(combinacion)

    if not filas_combinaciones:
        raise ValueError(
            "No se ha encontrado ninguna combinacion (fila) valida en el Excel."
        )

    return df_original, canales, filas_combinaciones

def guardar_excel_combinaciones_resultados(ruta_salida, df_original, filas_resultado):
    """
    Crea una copia del excel de combinaciones de entrada anadiendo, a la derecha
    de las columnas originales, las columnas de resultados (Voc, Isc, Vmp, Imp,
    Pmax, FF, Eff, Estado, Archivo Excel, ...) de cada fila/combinacion medida.
    """
    if not filas_resultado:
        return None

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    df_resultados = pd.DataFrame(filas_resultado).reset_index(drop=True)
    # Estas columnas ya estan implicitas en las columnas originales del excel de
    # entrada (una por canal, con el mismo nombre + " (%)") o no aportan valor
    # en la vista combinada, asi que no se duplican en el excel de salida.
    columnas_a_excluir = {"Punto", "Combinacion", "Punto en combinacion"}
    columnas_a_excluir |= {f"{c} (%)" for c in df_original.columns}
    df_resultados = df_resultados.drop(columns=[c for c in columnas_a_excluir if c in df_resultados.columns])

    df_original_reset = df_original.reset_index(drop=True)
    n = min(len(df_original_reset), len(df_resultados))
    df_final = pd.concat(
        [df_original_reset.iloc[:n].reset_index(drop=True), df_resultados.iloc[:n].reset_index(drop=True)],
        axis=1,
    )

    # De la columna "Archivo Excel" quitamos la ruta y nos quedamos solo con el nombre del fichero
    df_final["Archivo Excel"] = df_final["Archivo Excel"].apply(lambda x: Path(x).name if pd.notna(x) else x)

    # Cambiamos el orden de las columnas "Estado" y "Archivo Excel" y las ponemos las últimas
    columnas =[col for col in df_final.columns if col != "Archivo Excel" and col != "Estado"] + ["Estado", "Archivo Excel"] 
    df_final = df_final[columnas]

    eliminar_archivo_previo(ruta_salida)
    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="combinaciones_resultados", index=False)

    return str(ruta_salida.resolve())

# ---------------------------------------------------------------------------
# Helpers para degradación y NGU401
# ---------------------------------------------------------------------------

def nombre_seguro(valor: str) -> str:
    import re
    return re.sub(r'[<>:\"/\\|?*]+', "_", str(valor)).strip(" ._") or "medida"

def carpeta_experimento(cfg: dict) -> Path:
    from pathlib import Path
    nombre = cfg.get("nombre_experimento") or cfg.get("nombre_carpeta_medida") or "experimento"
    ruta = Path(cfg["carpeta_salida"]) / nombre_seguro(nombre)
    ruta.mkdir(parents=True, exist_ok=True)
    cfg["carpeta_salida_experimento"] = str(ruta)
    return ruta

def guardar_medida(ruta: Path, datos: pd.DataFrame, resumen: dict) -> None:
    columnas_a_excluir = {"indice_global", "indice_segmento", "tiempo_relativo_s"}
    columnas_exportar = [col for col in datos.columns if col not in columnas_a_excluir]
    df_exportar = datos[columnas_exportar].rename(
        columns={"voltaje_V": "V (V)", "corriente_A": "I (A)", "potencia_W": "P (W)"}
    )
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        df_exportar.to_excel(writer, sheet_name="datos_IV", index=False)
        pd.DataFrame([resumen]).to_excel(writer, sheet_name="resumen", index=False)

def guardar_resumen_ciclo(ruta: Path, filas: list[dict]) -> None:
    if not filas:
        return
    nuevas_filas = pd.DataFrame(filas)
    ruta = Path(ruta)
    if ruta.exists():
        try:
            existente = pd.read_excel(ruta, sheet_name="resumen_comparativo")
            acumulado = pd.concat([existente, nuevas_filas], ignore_index=True)
        except Exception:
            acumulado = nuevas_filas
    else:
        acumulado = nuevas_filas

    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        acumulado.to_excel(writer, sheet_name="resumen_comparativo", index=False)
