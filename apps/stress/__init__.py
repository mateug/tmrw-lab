"""Manifest de apps/stress — modo Stress."""


def _crear_frame(parent, callback_volver):
    from apps.stress.ui.panel import StressFrame
    return StressFrame(parent, callback_volver=callback_volver)


MANIFEST = {
    "id": "stress",
    "nombre": "Stress",
    "descripcion": (
        "Ensayo de degradación comparativa\n"
        "A/B con R&S NGU401.\n"
        "Ciclos programados por tiempo o Voc."
    ),
    "icono": "⚡",
    "icono_archivo": "stress",
    "crear_frame": _crear_frame,
}
