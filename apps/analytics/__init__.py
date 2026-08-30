"""Manifest de apps/analytics — modo Analytics."""


def _crear_frame(parent, callback_volver):
    from apps.analytics.ui.panel import AnalyticsFrame
    return AnalyticsFrame(parent, callback_volver=callback_volver)


MANIFEST = {
    "id": "analytics",
    "nombre": "Analytics",
    "descripcion": (
        "Visualiza y analiza curvas IV\n"
        "guardadas en Excel.\n"
        "Comparativas e Isc vs tiempo."
    ),
    "icono": "📊",
    "crear_frame": _crear_frame,
}
