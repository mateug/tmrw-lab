import os
import subprocess
import sys
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from pathlib import Path
import uuid

from core.postprocess.analysis import seleccionar_escala_corriente, seleccionar_escala_potencia, valores_absolutos_para_log
from core.utils import imprimir


def guardar_figura_png_sobrescribiendo(fig, ruta, dpi=300, bbox_inches="tight"):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    ruta_temporal = ruta.with_name(
        f".{ruta.stem}_{uuid.uuid4().hex}.tmp{ruta.suffix}"
    )

    try:
        fig.savefig(ruta_temporal, dpi=dpi, bbox_inches=bbox_inches)
        ruta_temporal.replace(ruta)
    except PermissionError as exc:
        raise PermissionError(
            f"No se pudo sobrescribir la figura porque está abierta o bloqueada:\n{ruta}\n\n"
            "Cierra cualquier ventana de Matplotlib, visor de imágenes o explorador "
            "que esté usando esa PNG y vuelve a lanzar la medida."
        ) from exc
    finally:
        try:
            if ruta_temporal.exists():
                ruta_temporal.unlink()
        except Exception:
            pass

    try:
        fig.clear()
    except Exception:
        pass


def abrir_figuras_matplotlib_interactivo(rutas_figuras):
    rutas = [str(Path(r)) for r in rutas_figuras if Path(r).exists()]
    if not rutas:
        return

    def abrir_con_visorde_defecto(ruta):
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)
                return True
            if sys.platform == "darwin":
                subprocess.Popen(["open", ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        except Exception:
            return False
        return False

    abierto = False
    for ruta in rutas:
        if abrir_con_visorde_defecto(ruta):
            abierto = True

    if abierto:
        return

    try:
        codigo = "\n".join([
            "import sys",
            "import matplotlib.pyplot as plt",
            "import matplotlib.image as mpimg",
            "rutas = sys.argv[1:]",
            "for ruta in rutas:",
            "    try:",
            "        imagen = mpimg.imread(ruta)",
            "        fig, ax = plt.subplots(figsize=(8, 8))",
            "        ax.imshow(imagen)",
            "        ax.axis(\"off\")",
            "        fig.tight_layout()",
            "    except Exception as exc:",
            "        print(f\"No se pudo abrir la figura {ruta}: {exc}\", flush=True)",
            "plt.show()",
        ])

        kwargs = {}
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        subprocess.Popen(
            [sys.executable, "-c", codigo, *rutas],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except Exception as exc:
        imprimir(f"No se pudieron abrir las figuras con Matplotlib: {exc}")


def representar_curvas_iv_pv(df, rutas_figuras, cfg):
    rutas_generadas = {}

    i_max_medido = np.nanmax(np.abs(df["corriente_medida_A"].to_numpy(dtype=float)))
    if not np.isfinite(i_max_medido) or i_max_medido == 0:
        i_max_medido = 1.0
    factor_I, unidad_I = seleccionar_escala_corriente(i_max_medido)

    p_max = np.nanmax(np.abs(df["potencia_W"].to_numpy(dtype=float)))
    if not np.isfinite(p_max) or p_max == 0:
        p_max = 1.0

    factor_P, unidad_P = seleccionar_escala_potencia(p_max)
    nombre_medida = str(cfg.get("nombre_medida", "")).strip()

    def crear_figura():
        fig = Figure(figsize=(8, 8))
        FigureCanvasAgg(fig)
        ejes = fig.subplots(2, 1, sharex=True)
        return fig, ejes

    fig, ejes = crear_figura()

    for segmento, df_seg in df.groupby("segmento", sort=False):
        voltaje = df_seg["voltaje_V"]
        corriente = df_seg["corriente_medida_A"] * factor_I
        potencia = df_seg["potencia_W"] * factor_P

        ejes[0].plot(voltaje, corriente, marker="o", markersize=3, linewidth=1, label=segmento)
        ejes[1].plot(voltaje, potencia, marker="o", markersize=3, linewidth=1, label=segmento)

    ejes[0].set_ylabel(f"I ({unidad_I})")
    ejes[0].set_title(f"Curva IV {nombre_medida}")
    ejes[0].grid(True, alpha=0.3)
    ejes[0].legend()

    ejes[1].set_xlabel("V (V)")
    ejes[1].set_ylabel(f"P ({unidad_P})")
    ejes[1].set_title(f"Curva PV {nombre_medida}")
    ejes[1].grid(True, alpha=0.3)
    ejes[1].legend()

    fig.tight_layout()
    guardar_figura_png_sobrescribiendo(fig, rutas_figuras["lineal"], dpi=300, bbox_inches="tight")
    rutas_generadas["lineal"] = rutas_figuras["lineal"]

    fig, ejes = crear_figura()

    for segmento, df_seg in df.groupby("segmento", sort=False):
        voltaje = df_seg["voltaje_V"]
        corriente_log = valores_absolutos_para_log(df_seg["corriente_medida_A"] * factor_I)
        potencia_log = valores_absolutos_para_log(df_seg["potencia_W"] * factor_P)

        ejes[0].plot(voltaje, corriente_log, marker="o", markersize=3, linewidth=1, label=segmento)
        ejes[1].plot(voltaje, potencia_log, marker="o", markersize=3, linewidth=1, label=segmento)

    ejes[0].set_yscale("log")
    ejes[0].set_ylabel(f"I ({unidad_I})")
    ejes[0].set_title(f"Curva IV {nombre_medida} en escala logaritmica")
    ejes[0].grid(True, which="both", alpha=0.3)
    ejes[0].legend()

    ejes[1].set_yscale("log")
    ejes[1].set_xlabel("V (V)")
    ejes[1].set_ylabel(f"P ({unidad_P})")
    ejes[1].set_title(f"Curva PV {nombre_medida} en escala logaritmica")
    ejes[1].grid(True, which="both", alpha=0.3)
    ejes[1].legend()

    fig.tight_layout()
    guardar_figura_png_sobrescribiendo(fig, rutas_figuras["log_y"], dpi=300, bbox_inches="tight")
    rutas_generadas["log_y"] = rutas_figuras["log_y"]

    return rutas_generadas


def generar_imagen_tk_curvas_iv_pv(df, cfg=None, ancho_px=540, alto_px=250):
    """
    Genera un objeto ImageTk.PhotoImage con la curva IV para el log de la UI.

    Las gráficas IV/PV completas que se guardan en disco se generan mediante
    ``representar_curvas_iv_pv`` y no se modifican aquí­.
    """
    if df is None or df.empty:
        return None

    import io
    from PIL import Image, ImageTk

    if cfg is None:
        cfg = {}

    i_max_medido = np.nanmax(np.abs(df["corriente_medida_A"].to_numpy(dtype=float)))
    if not np.isfinite(i_max_medido) or i_max_medido == 0:
        i_max_medido = 1.0
    factor_I, unidad_I = seleccionar_escala_corriente(i_max_medido)

    fig = Figure(figsize=(ancho_px / 100.0, alto_px / 100.0), dpi=100)
    FigureCanvasAgg(fig)
    eje = fig.subplots()

    for segmento, df_seg in df.groupby("segmento", sort=False):
        voltaje = df_seg["voltaje_V"]
        corriente = df_seg["corriente_medida_A"] * factor_I

        eje.plot(voltaje, corriente, marker="o", markersize=2.5, linewidth=1, label=segmento)

    eje.set_xlabel("V (V)", fontsize=8)
    eje.set_ylabel(f"I ({unidad_I})", fontsize=8)
    eje.set_title("Curva IV", fontsize=9, fontweight="bold")
    eje.grid(True, alpha=0.3)
    eje.tick_params(labelsize=7)
    eje.legend(fontsize=7)

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    fig.clear()
    buf.seek(0)

    pil_img = Image.open(buf)
    tk_img = ImageTk.PhotoImage(pil_img.copy())
    return tk_img



def guardar_curvas(datos, base_path, titulo=""):
    """Alias para compatibilidad con devices-degradation: guarda curvas IV y PV."""
    from pathlib import Path
    base = Path(base_path)
    rutas = {"lineal": base.with_suffix("") .parent / (base.stem + "_lineal.png"),
             "log_y":  base.with_suffix("") .parent / (base.stem + "_log_y.png")}
    cfg = {"nombre_medida": titulo or base.stem}
    col_i = "corriente_medida_A" if "corriente_medida_A" in datos.columns else "corriente_A"
    datos_plot = datos.rename(columns={col_i: "corriente_medida_A"})
    return representar_curvas_iv_pv(datos_plot, rutas, cfg)
