"""Manifest de apps/analytics — modo Analytics."""


def _crear_frame(parent, callback_volver):
    from apps.analytics.ui.panel import AnalyticsFrame
    return AnalyticsFrame(parent, callback_volver=callback_volver)


MANIFEST = {
    "id": "analytics",
    "nombre": "Analytics",
    "descripcion": (
        "Visualiza las curvas IV de varios excels.\n\n"
        "Genera un excel combinado.\n\n"
    ),
    "icono": "📈",
    "icono_archivo": "analytics",
    "crear_frame": _crear_frame,
}
