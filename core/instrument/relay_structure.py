"""Relé de selección de estructura para Studio/Lite — STUB.

Este script es el punto de extensión para conectar el relé que selecciona
qué estructura medir dentro de Studio y Lite. Intencionadamente separado
de apps/stress/relay_degradation.py (conmutación A/B del ensayo de degradación).

TODO: implementar la clase RelayEstructuraArduinoSerial cuando el hardware esté disponible.
      Usar el mismo protocolo Arduino Serial que relay_degradation.py (HELLO, SELECT A/B,
      OFF ALL, STATUS?) adaptado a las necesidades de Studio/Lite.
"""
from core.exceptions import ErrorRele


class RelayEstructura:
    """Stub de relé de selección de estructura.

    Interfaz mínima que Studio/Lite esperan:
        connect()        → abre la conexión con el Arduino
        select(nombre)   → activa el contacto de la estructura indicada
        off()            → desactiva todos los contactos
        close()          → cierra la conexión

    La implementación real deberá sustituir este stub.
    """

    def __init__(self, cfg, event=None):
        self.cfg = cfg
        self.event = event
        self._conectado = False

    def connect(self):
        # TODO: abrir puerto serie y verificar firmware
        raise ErrorRele(
            "relay_structure.py es un stub. "
            "Implementa la conexión real cuando el hardware esté disponible."
        )

    def select(self, nombre: str):
        if not self._conectado:
            raise ErrorRele("El relé de estructura no está conectado.")
        # TODO: enviar comando SELECT al Arduino

    def off(self):
        if not self._conectado:
            return
        # TODO: enviar comando OFF ALL al Arduino

    def close(self):
        self.off()
        self._conectado = False
        # TODO: cerrar puerto serie

    def stop(self):
        self.off()


def crear_rele_estructura(cfg, event=None) -> RelayEstructura:
    """Factoría: devuelve el controlador de relé de estructura."""
    return RelayEstructura(cfg.get("rele_estructura", {}), event=event)
