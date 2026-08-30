"""Manifest de apps/lite — modo Lite."""


def _crear_frame(parent, callback_volver):
    from apps.lite.ui.panel import LiteFrame
    return LiteFrame(parent, callback_volver=callback_volver)


MANIFEST = {
    "id": "lite",
    "nombre": "Lite",
    "descripcion": (
        "Carga combinaciones desde Excel.\n"
        "Vista previa antes de medir.\n"
        "Ejecución desatendida de la lista."
    ),
    "icono": "📋",
    "icono_archivo": "lite",
    "crear_frame": _crear_frame,
}
