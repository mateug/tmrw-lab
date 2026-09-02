"""Manifest de apps/lite — modo Lite."""


def _crear_frame(parent, callback_volver):
    from apps.lite.ui.panel import LiteFrame
    return LiteFrame(parent, callback_volver=callback_volver)


MANIFEST = {
    "id": "lite",
    "nombre": "Lite",
    "descripcion": (
        "Carga las combinaciones desde un Excel.\n\n"
        "Vista previa antes de medir.\n\n"
    ),
    "icono": "📋",
    "icono_archivo": "lite",
    "crear_frame": _crear_frame,
}
