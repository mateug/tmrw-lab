from pathlib import Path
import numpy as np
import pandas as pd

from core.utils import preparar_carpeta_medida, sanitizar_nombre_archivo


# ---------------------------------------------------------------------------
# Normalización de unidades adaptativas en resúmenes combinados
# ---------------------------------------------------------------------------

_FACTORES_UNIDADES = {
    "pA": 1e-12,
    "nA": 1e-9,
    "uA": 1e-6,
    "mA": 1e-3,
    "A": 1.0,
    "uV": 1e-6,
    "mV": 1e-3,
    "V": 1.0,
    "kV": 1e3,
    "pW": 1e-12,
    "nW": 1e-9,
    "uW": 1e-6,
    "mW": 1e-3,
    "W": 1.0,
    "uA/cm^2": 1e-6,
    "mA/cm^2": 1e-3,
    "A/cm^2": 1.0,
    "uW/cm^2": 1e-6,
    "mW/cm^2": 1e-3,
    "W/cm^2": 1.0,
    "nm^2": 1e-6,
    "um^2": 1.0,
    "mm^2": 1e6,
    "%": 1.0,
}


def _extraer_unidad(clave, prefijo):
    """Extrae la unidad de una columna con formato 'prefijo (unidad)'."""
    texto = str(clave)
    marcador = f"{prefijo} ("
    if not texto.startswith(marcador) or not texto.endswith(")"):
        return None
    return texto[len(marcador):-1]


def _valor_numerico_valido(valor):
    try:
        return np.isfinite(float(valor))
    except (TypeError, ValueError):
        return False


def _extraer_magnitud_unidad(clave, prefijos):
    """Devuelve (magnitud, unidad) si la columna representa una magnitud conocida."""
    texto = str(clave)

    for prefijo in prefijos:
        marcador = f"{prefijo} ("
        if texto.startswith(marcador) and texto.endswith(")"):
            unidad = texto[len(marcador):-1]
            if unidad in _FACTORES_UNIDADES:
                return prefijo, unidad

    return None, None


def _unidad_adaptativa_valor(valor_base, grupo):
    """Elige una unidad legible a partir de un valor expresado en unidades base."""
    if not _valor_numerico_valido(valor_base):
        return None

    valor = abs(float(valor_base))

    if grupo in {"corriente", "limite_corriente"}:
        opciones = [
            (1.0, "A"),
            (1e3, "mA"),
            (1e6, "uA"),
            (1e9, "nA"),
            (1e12, "pA"),
        ]

    elif grupo == "tension":
        opciones = [
            (1.0, "V"),
            (1e3, "mV"),
            (1e6, "uV"),
        ]

    elif grupo == "potencia":
        opciones = [
            (1.0, "W"),
            (1e3, "mW"),
            (1e6, "uW"),
            (1e9, "nW"),
            (1e12, "pW"),
        ]

    elif grupo == "densidad_corriente":
        opciones = [
            (1.0, "A/cm^2"),
            (1e3, "mA/cm^2"),
            (1e6, "uA/cm^2"),
        ]

    elif grupo == "densidad_potencia":
        opciones = [
            (1.0, "W/cm^2"),
            (1e3, "mW/cm^2"),
            (1e6, "uW/cm^2"),
        ]

    elif grupo == "superficie":
        opciones = [
            (1.0, "um^2"),
            (1e-6, "mm^2"),
            (1e6, "nm^2"),
        ]

    elif grupo == "porcentaje":
        return "%"

    else:
        return None

    for factor, unidad in opciones:
        if valor * factor >= 1.0:
            return unidad

    return opciones[-1][1]


def normalizar_unidades_filas_resumen(filas_resumen):
    """
    Normaliza un resumen completo sin perder valores cuando cambian las unidades.

    Acepta:
      - columnas en unidades base, por ejemplo ``Voc (V)``
      - columnas ya adaptativas, por ejemplo ``Voc (mV)``

    Primero convierte todas las magnitudes a unidades base.
    Después elige UNA única escala de salida para TODO el histórico.
    """

    if not filas_resumen:
        return []

    grupos = {
        "corriente": ["Isc", "Imp"],
        "limite_corriente": ["Imax"],
        "tension": ["Voc", "Vmp"],
        "potencia": ["Pmax"],
        "densidad_corriente": ["Jsc"],
        "densidad_potencia": ["Irradiancia", "Densidad de potencia"],
        "superficie": ["Superficie activa"],
        "porcentaje": ["FF", "Eff"],
    }

    grupo_por_magnitud = {
        magnitud: grupo
        for grupo, prefijos in grupos.items()
        for magnitud in prefijos
    }

    todos_prefijos = list(grupo_por_magnitud.keys())

    # ------------------------------------------------------------------
    # 1. Convertir todo el histórico a unidades base.
    # ------------------------------------------------------------------
    filas_base = []
    maximos = {grupo: 0.0 for grupo in grupos}

    for fila in filas_resumen:
        nueva = {}
        magnitudes_encontradas = set()

        for clave, valor in fila.items():
            magnitud, unidad = _extraer_magnitud_unidad(
                clave,
                todos_prefijos,
            )

            if magnitud is None:
                nueva[clave] = valor
                continue

            if not _valor_numerico_valido(valor):
                continue

            # Si la misma magnitud aparece varias veces con unidades distintas,
            # conservar únicamente la primera válida.
            if magnitud in magnitudes_encontradas:
                continue

            magnitudes_encontradas.add(magnitud)

            grupo = grupo_por_magnitud[magnitud]

            valor_base = float(valor) * _FACTORES_UNIDADES[unidad]

            nueva[f"__base__{magnitud}"] = valor_base

            maximos[grupo] = max(
                maximos[grupo],
                abs(valor_base),
            )

        filas_base.append(nueva)

    # ------------------------------------------------------------------
    # 2. Elegir una única unidad para todo el histórico.
    # ------------------------------------------------------------------
    unidades_destino = {}

    for grupo, maximo in maximos.items():
        if grupo == "porcentaje":
            unidades_destino[grupo] = "%"

        elif maximo > 0:
            unidades_destino[grupo] = _unidad_adaptativa_valor(
                maximo,
                grupo,
            )

        else:
            unidades_destino[grupo] = {
                "corriente": "uA",
                "limite_corriente": "uA",
                "tension": "mV",
                "potencia": "uW",
                "densidad_corriente": "mA/cm^2",
                "densidad_potencia": "mW/cm^2",
                "superficie": "um^2",
                "porcentaje": "%",
            }[grupo]

    # ------------------------------------------------------------------
    # 3. Reconstruir las filas con nombres de columnas estables.
    # ------------------------------------------------------------------
    resultado = []

    for fila_base in filas_base:
        fila = {
            clave: valor
            for clave, valor in fila_base.items()
            if not str(clave).startswith("__base__")
        }

        for magnitud, grupo in grupo_por_magnitud.items():
            clave_base = f"__base__{magnitud}"

            if clave_base not in fila_base:
                continue

            unidad = unidades_destino[grupo]
            valor_base = fila_base[clave_base]

            valor_salida = (
                valor_base /
                _FACTORES_UNIDADES[unidad]
            )

            fila[f"{magnitud} ({unidad})"] = valor_salida

        resultado.append(fila)

    return resultado


def construir_rutas_salida(cfg):
    carpeta = Path(
        cfg.get("carpeta_salida_medida")
        or preparar_carpeta_medida(cfg)
    )

    nombre = sanitizar_nombre_archivo(
        cfg["nombre_medida"]
    )

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
            f"No se pudo sobrescribir el archivo porque está abierto o bloqueado:\n"
            f"{ruta}\n\n"
            "Cierra Excel, el visor de imágenes o cualquier programa que lo esté "
            "usando y vuelve a lanzar la medida."
        ) from exc


def preparar_datos_excel(df):
    return pd.DataFrame({
        "t (seg)": df["tiempo_relativo_s"],
        "V (V)": df["voltaje_V"],
        "I (A)": df["corriente_medida_A"],
        "P (W)": df["potencia_W"],
    })


def guardar_resumen_repetitividad_excel(cfg_base, filas_resumen):
    if not filas_resumen:
        return None

    ruta_base, _ = construir_rutas_salida(cfg_base)

    ruta = ruta_base.with_name(
        f"{ruta_base.stem}_medidas_repetitivas.xlsx"
    )

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.DataFrame(
        normalizar_unidades_filas_resumen(
            filas_resumen
        )
    )

    eliminar_archivo_previo(ruta)

    with pd.ExcelWriter(
        ruta,
        engine="openpyxl",
    ) as writer:
        df.to_excel(
            writer,
            sheet_name="resumen_repetitividad",
            index=False,
        )

    return str(ruta.resolve())


def guardar_resumen_barrido_motor_excel(cfg_base, filas_resumen):
    if not filas_resumen:
        return None

    ruta_base, _ = construir_rutas_salida(cfg_base)

    ruta = ruta_base.with_name(
        f"{ruta_base.stem}_barrido_motor.xlsx"
    )

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.DataFrame(
        normalizar_unidades_filas_resumen(
            filas_resumen
        )
    )

    eliminar_archivo_previo(ruta)

    with pd.ExcelWriter(
        ruta,
        engine="openpyxl",
    ) as writer:
        df.to_excel(
            writer,
            sheet_name="resumen_barrido_motor",
            index=False,
        )

    return str(ruta.resolve())


def guardar_resumen_studio_excel(cfg_base, filas_resumen):
    """Guarda el resumen multieje de Studio en una única hoja sin rutas."""
    if not filas_resumen:
        return None

    ruta_base, _ = construir_rutas_salida(cfg_base)
    ruta = ruta_base.with_name(f"{ruta_base.stem}__resumen_combinado.xlsx")
    ruta.parent.mkdir(parents=True, exist_ok=True)

    filas_limpias = [
        fila for fila in filas_resumen
        if any(valor is not None and not (isinstance(valor, float) and np.isnan(valor))
               for valor in fila.values())
    ]
    filas_normalizadas = normalizar_unidades_filas_resumen(filas_limpias)

    columnas_base = [
        "Iteración", "Nombre iteración", "Estructura", "Motor lineal (mm)",
        "Inclinación (deg)", "Rotación (deg)", "Irradiancia (mW/cm^2)",
        "Estado", "Puntos",
    ]
    columnas_led = sorted({
        clave for fila in filas_normalizadas for clave in fila
        if str(clave).startswith("LED ") and str(clave).endswith(" (%)")
    })
    columnas_fv = [
        clave for fila in filas_normalizadas for clave in fila
        if clave not in columnas_base
        and clave not in columnas_led
        and clave not in {"Archivo Excel", "Archivo PNG", "ruta_excel", "rutas_figuras"}
        and "ruta" not in str(clave).lower()
        and "archivo" not in str(clave).lower()
    ]
    columnas_fv = list(dict.fromkeys(columnas_fv))
    columnas = columnas_base[:3] + columnas_led + columnas_base[3:] + columnas_fv
    filas = [{columna: fila.get(columna) for columna in columnas} for fila in filas_normalizadas]
    filas = [
        fila for fila in filas
        if any(valor is not None and not (isinstance(valor, float) and np.isnan(valor))
               for valor in fila.values())
    ]

    eliminar_archivo_previo(ruta)
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        pd.DataFrame(filas, columns=columnas).to_excel(
            writer, sheet_name="resumen_studio", index=False
        )

    return str(ruta.resolve())


def guardar_resumen_irradiancia_excel(cfg_base, filas_resumen):
    if not filas_resumen:
        return None

    ruta_base, _ = construir_rutas_salida(cfg_base)

    submodo = cfg_base.get(
        "irradiancia_modo",
        "potencia",
    )

    if submodo == "potencia":
        sufijo = "resumen_potencias_sol"

    elif submodo in {
        "combinacion",
        "combinación",
        "multi_longitud_onda",
    }:
        sufijo = "resumen_combinacion_longitudes_onda"

    elif submodo in {
        "multiples_combinaciones",
        "multiples_multi_canal",
    }:
        sufijo = "resumen_multiples_combinaciones"

    elif submodo == "lectura_excel":
        sufijo = "resumen_lectura_excel"

    else:
        sufijo = "resumen_longitudes_onda"

    ruta = ruta_base.with_name(
        f"{ruta_base.stem}_{sufijo}.xlsx"
    )

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.DataFrame(
        normalizar_unidades_filas_resumen(
            filas_resumen
        )
    )

    eliminar_archivo_previo(ruta)

    with pd.ExcelWriter(
        ruta,
        engine="openpyxl",
    ) as writer:
        df.to_excel(
            writer,
            sheet_name=sufijo,
            index=False,
        )

    return str(ruta.resolve())


def leer_combinaciones_excel(
    ruta,
    hoja=None,
    valores_en_tanto_por_uno=True,
):
    """
    Lee un Excel de entrada con una fila de cabecera
    y una fila por combinación de intensidades.
    """

    ruta = Path(ruta)

    if hoja is None:
        df = pd.read_excel(ruta)

    else:
        df = pd.read_excel(
            ruta,
            sheet_name=hoja,
        )

    if df.empty:
        return []

    columnas = [
        str(columna).strip()
        for columna in df.columns
    ]

    df.columns = columnas

    combinaciones = []

    for _, fila in df.iterrows():
        combinacion = {}

        for columna in columnas:
            valor = fila[columna]

            if pd.isna(valor):
                continue

            valor = float(valor)

            if valores_en_tanto_por_uno:
                valor = max(
                    0.0,
                    min(1.0, valor),
                )

            combinacion[columna] = valor

        combinaciones.append(combinacion)

    return combinaciones


def nombre_seguro(nombre):
    return sanitizar_nombre_archivo(
        str(nombre)
    )


def carpeta_experimento(cfg):
    nombre = (
        cfg.get("nombre_experimento")
        or cfg.get("nombre_carpeta_medida")
        or "experimento"
    )

    ruta = (
        Path(cfg["carpeta_salida"])
        / nombre_seguro(nombre)
    )

    ruta.mkdir(
        parents=True,
        exist_ok=True,
    )

    cfg["carpeta_salida_experimento"] = str(ruta)

    return ruta


def guardar_medida(
    ruta: Path,
    datos: pd.DataFrame,
    resumen: dict,
) -> None:

    columnas_a_excluir = {
        "indice_global",
        "indice_segmento",
        "tiempo_relativo_s",
    }

    columnas_exportar = [
        columna
        for columna in datos.columns
        if columna not in columnas_a_excluir
    ]

    df_exportar = datos[
        columnas_exportar
    ].rename(
        columns={
            "voltaje_V": "V (V)",
            "corriente_A": "I (A)",
            "potencia_W": "P (W)",
        }
    )

    with pd.ExcelWriter(
        ruta,
        engine="openpyxl",
    ) as writer:

        df_exportar.to_excel(
            writer,
            sheet_name="datos_IV",
            index=False,
        )

        pd.DataFrame(
            [resumen]
        ).to_excel(
            writer,
            sheet_name="resumen",
            index=False,
        )


def guardar_resumen_ciclo(
    ruta: Path,
    filas: list[dict],
) -> None:
    """
    Añade los nuevos ciclos al Excel combinado y normaliza
    las unidades sobre TODO el histórico.

    Importante:
    no se normalizan por separado los ciclos nuevos y los
    existentes. Primero se juntan y después se escoge una
    unidad única para cada magnitud.
    """

    if not filas:
        return

    nuevas_filas = pd.DataFrame(filas)

    ruta = Path(ruta)

    if ruta.exists():
        try:
            existente = pd.read_excel(
                ruta,
                sheet_name="resumen_comparativo",
            )

            acumulado_raw = pd.concat(
                [
                    existente,
                    nuevas_filas,
                ],
                ignore_index=True,
            )

        except Exception:
            acumulado_raw = nuevas_filas

    else:
        acumulado_raw = nuevas_filas

    acumulado = pd.DataFrame(
        normalizar_unidades_filas_resumen(
            acumulado_raw.to_dict(
                "records"
            )
        )
    )

    with pd.ExcelWriter(
        ruta,
        engine="openpyxl",
    ) as writer:

        acumulado.to_excel(
            writer,
            sheet_name="resumen_comparativo",
            index=False,
        )