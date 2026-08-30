"""Excepciones de dominio unificadas de TMRW Lab."""


class MedidaAbortadaPorUsuario(RuntimeError):
    """El usuario solicitó terminar la ejecución de manera cooperativa."""

    def __init__(self, mensaje="Medida abortada por el usuario.", df_parcial=None):
        super().__init__(mensaje)
        self.df_parcial = df_parcial


class LimiteCorrienteAlcanzado(RuntimeError):
    """La protección de corriente del SMU detuvo el barrido."""

    def __init__(self, mensaje="Límite de corriente alcanzado.", df_parcial=None):
        super().__init__(mensaje)
        self.df_parcial = df_parcial


class ErrorSMU(RuntimeError):
    """Error de comunicación o configuración del SMU."""


class ErrorRele(RuntimeError):
    """Error de comunicación o conmutación del relé."""


class ErrorMotor(RuntimeError):
    """Error de comunicación o movimiento del motor."""


class ErrorSimuladorSolar(RuntimeError):
    """Error de comunicación o configuración del simulador solar."""
