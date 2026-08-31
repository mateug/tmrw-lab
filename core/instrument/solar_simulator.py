import re
import time
import numpy as np

from core.exceptions import MedidaAbortadaPorUsuario, ErrorSimuladorSolar


ossila_CANALES_LED = {
    "390": "1",
    "390 nm": "1",
    "450": "2",
    "450 nm": "2",
    "515": "3",
    "515 nm": "3",
    "cool_white": "4",
    "cool white": "4",
    "warm_white": "5",
    "warm white": "5",
    "600": "6",
    "600 nm": "6",
    "630": "7",
    "630 nm": "7",
    "660": "8",
    "660 nm": "8",
    "730": "9",
    "730 nm": "9",
    "850": "10",
    "850 nm": "10",
    "950": "11",
    "950 nm": "11",
}


def normalizar_canal_ossila(canal):
    """Convierte longitudes de onda conocidas al numero de canal ossila/Ossila."""
    texto = str(canal).strip()
    if not texto:
        return texto
    texto_lower = texto.lower()
    if texto_lower.startswith("ch") and texto_lower[2:].strip().isdigit():
        return texto_lower[2:].strip()
    return ossila_CANALES_LED.get(texto_lower, texto)


class ControladorSimuladorSolarOssila:
    def __init__(self, cfg_simulador, evento_aborto=None):
        self.cfg = cfg_simulador
        self.evento_aborto = evento_aborto
        self.serial = None
        self.conectado = False
        self.encendido = False
        self.potencia_confirmada = None
        self._separador_set = None

    def _comprobar_aborto(self):
        if self.evento_aborto is not None and self.evento_aborto.is_set():
            raise MedidaAbortadaPorUsuario(
                "Secuencia abortada mientras se controlaba el simulador solar."
            )

    def connect(self):
        try:
            import serial
        except ImportError as exc:
            raise ErrorSimuladorSolar(
                "Falta la librerí­a pyserial. Instálala con: pip install pyserial"
            ) from exc

        puerto_raw = str(self.cfg.get("puerto_serie", ""))
        puerto = re.sub(r"\s+", "", puerto_raw)
        if not puerto:
            raise ErrorSimuladorSolar(
                "Introduce el puerto COM del simulador solar."
            )

        baudrate = int(self.cfg.get("baudrate", 9600))
        timeout_lectura = max(0.05, float(self.cfg.get("timeout_lectura_s", 0.20)))

        self.serial = serial.Serial(
            port=puerto,
            baudrate=baudrate,
            timeout=timeout_lectura,
            write_timeout=2.0,
        )
        time.sleep(0.40)
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

        try:
            self.dispositivo = self.consultar_texto("device")
            self.numero_serie = self.consultar_texto("serial")
            self.firmware = self.consultar_texto("firmware")
            potencia = self.consultar_potencia()
            codigo_error = self.consultar_error()
            if codigo_error != 0:
                raise ErrorSimuladorSolar(self._texto_error(codigo_error))

            self.conectado = True
            self.encendido = potencia > float(self.cfg.get("tolerancia_potencia_mW_cm2", 0.5))
            self.potencia_confirmada = potencia
            if self.cfg.get("apagar_al_conectar", True):
                self.apagar()
        except Exception:
            self.close(apagar=False)
            raise

    def _texto_error(self, codigo):
        errores = {
            0: "sin error",
            1: "tensión de alimentación baja",
            2: "temperatura excesiva",
            3: "fallo de LED",
        }
        codigo = int(codigo)
        detalle = errores.get(codigo, "código no reconocido")
        return f"El simulador solar devuelve error {codigo}: {detalle}."

    def _leer_trama(self, timeout_s=None):
        if self.serial is None or not self.serial.is_open:
            raise ErrorSimuladorSolar("El puerto serie del simulador solar no está abierto.")

        limite = time.monotonic() + float(self.cfg.get("timeout_comando_s", 5.0) if timeout_s is None else timeout_s)
        datos = bytearray()
        dentro = False

        while time.monotonic() < limite:
            self._comprobar_aborto()
            byte = self.serial.read(1)
            if not byte:
                continue
            if byte == b"<":
                datos = bytearray(byte)
                dentro = True
                continue
            if not dentro:
                continue
            datos.extend(byte)
            if byte == b">":
                return datos.decode("ascii", errors="replace").strip()

        raise ErrorSimuladorSolar("Timeout esperando una respuesta del simulador solar.")

    def _intercambiar(self, comando, timeout_s=None):
        if self.serial is None or not self.serial.is_open:
            raise ErrorSimuladorSolar("El puerto serie del simulador solar no está abierto.")

        self._comprobar_aborto()
        self.serial.reset_input_buffer()
        self.serial.write(comando.encode("ascii"))
        self.serial.flush()
        respuesta = self._leer_trama(timeout_s=timeout_s)

        if respuesta.strip().lower() == "<invalid command>":
            raise ErrorSimuladorSolar(f"Comando no aceptado por el simulador: {comando}")

        return respuesta

    @staticmethod
    def _separar_respuesta(respuesta):
        texto = str(respuesta).strip()
        if not (texto.startswith("<") and texto.endswith(">")):
            raise ErrorSimuladorSolar(f"Respuesta no válida del simulador solar: {respuesta!r}")

        interior = texto[1:-1].strip()
        if not interior:
            raise ErrorSimuladorSolar("La respuesta del simulador solar devolvió una respuesta vací­a.")

        if ":" in interior:
            clave, valor = interior.split(":", 1)
        elif " " in interior:
            clave, valor = interior.split(None, 1)
        else:
            clave, valor = interior, ""

        return clave.strip().lower(), valor.strip()

    def _consultar(self, nombre):
        nombre = str(nombre).strip().lower()
        respuesta = self._intercambiar(f"<{nombre}?>")
        clave, valor = self._separar_respuesta(respuesta)
        if clave != nombre:
            raise ErrorSimuladorSolar(f"Se esperaba una respuesta '{nombre}', pero se recibió {respuesta!r}.")
        return valor

    def consultar_texto(self, nombre):
        valor = self._consultar(nombre)
        if valor == "":
            raise ErrorSimuladorSolar(f"La consulta <{nombre}?> no devolvió ningún valor.")
        return valor

    def consultar_potencia(self):
        valor = self._consultar("power")
        if str(valor).strip().lower() == "undef":
            self.potencia_confirmada = np.nan
            return np.nan
        try:
            potencia = float(valor)
        except ValueError as exc:
            raise ErrorSimuladorSolar(f"Potencia no válida devuelta por el simulador: {valor!r}") from exc
        self.potencia_confirmada = potencia
        return potencia

    def consultar_error(self):
        valor = self._consultar("error")
        try:
            return int(float(valor))
        except ValueError as exc:
            raise ErrorSimuladorSolar(f"Código de error no válido: {valor!r}") from exc

    def _separadores_candidatos(self):
        configurado = str(self.cfg.get("separador_comando", "auto")).strip().lower()
        if configurado in {"espacio", "space", " "}:
            return [" "]
        if configurado in {"dos_puntos", "colon", ":"}:
            return [":"]
        if self._separador_set in {" ", ":"}:
            otro = ":" if self._separador_set == " " else " "
            return [self._separador_set, otro]
        return [" ", ":"]

    def fijar_potencia(self, potencia_mW_cm2):
        potencia = int(potencia_mW_cm2)
        ultimo_error = None

        for separador in self._separadores_candidatos():
            comando = f"<power{separador}{potencia}>"
            try:
                respuesta = self._intercambiar(comando)
                clave, valor = self._separar_respuesta(respuesta)
                if clave != "power":
                    raise ErrorSimuladorSolar(f"Eco inesperado al fijar potencia: {respuesta!r}")
                valor_eco = float(valor)
                if abs(valor_eco - potencia) > 0.5:
                    raise ErrorSimuladorSolar(f"El eco de potencia no coincide: {respuesta!r}")
                self._separador_set = separador
                return
            except MedidaAbortadaPorUsuario:
                raise
            except Exception as exc:
                ultimo_error = exc

        raise ErrorSimuladorSolar("El simulador no aceptó el comando de potencia con ninguna de las sintaxis compatibles.") from ultimo_error

    def enviar_comando_personalizado(self, plantilla, **kwargs):
        """Envia un comando formateado personalizable según plantilla a ossila."""
        kwargs_formato = dict(kwargs)
        canal_original = kwargs_formato.get("channel", kwargs_formato.get("canal", ""))
        canal_normalizado = normalizar_canal_ossila(canal_original)
        if canal_normalizado:
            kwargs_formato["channel"] = canal_normalizado
            kwargs_formato["canal"] = canal_normalizado
            kwargs_formato["channel_raw"] = canal_original
            kwargs_formato["canal_raw"] = canal_original

        if "intensity" in kwargs_formato:
            try:
                intensidad = float(kwargs_formato["intensity"])
                intensidad_int = int(max(0.0, min(100.0, intensidad)))
                kwargs_formato["intensity"] = intensidad_int
                kwargs_formato["intensidad"] = intensidad_int
                kwargs_formato["intensity_raw"] = kwargs.get("intensity")
                kwargs_formato["intensidad_raw"] = kwargs.get("intensidad", kwargs.get("intensity"))
            except (TypeError, ValueError):
                pass

        try:
            comando = plantilla.format(**kwargs_formato)
        except KeyError as exc:
            raise ErrorSimuladorSolar(f"Falta el parámetro {exc} en la plantilla de comando '{plantilla}'") from exc

        if not comando.startswith("<"):
            comando = "<" + comando
        if not comando.endswith(">"):
            comando = comando + ">"

        try:
            respuesta = self._intercambiar(comando)
        except MedidaAbortadaPorUsuario:
            raise
        except Exception as exc:
            diagnostico = self.diagnosticar_plantilla_led(canal_normalizado)
            raise ErrorSimuladorSolar(
                "Falló el comando de longitud de onda enviado al ossila.\n"
                f"Comando enviado: {comando}\n"
                f"Plantilla configurada: {plantilla}\n"
                f"{diagnostico}\n"
                f"Error original: {exc}"
            ) from exc
        return respuesta

    def diagnosticar_plantilla_led(self, canal=None):
        canal_normalizado = normalizar_canal_ossila(canal or "1") or "1"
        consultas = [f"ch{canal_normalizado}", "ch1", "device", "firmware", "error"]
        respuestas = []
        for consulta in dict.fromkeys(consultas):
            try:
                valor = self._consultar(consulta)
                respuestas.append(f"<{consulta}?> -> <{consulta}:{valor}>")
            except Exception as exc:
                respuestas.append(f"<{consulta}?> -> sin respuesta válida ({exc})")

        return (
            "Consulta de diagnóstico enviada al ossila: "
            + "; ".join(respuestas)
            + "\nPlantilla que pide ossila/Ossila para LEDs individuales: "
            "<ch{channel}:{intensity}>. "
            "El campo {channel} debe ser el número de canal LED (1-11) y "
            "{intensity} un entero de 0 a 100 %. "
            "Ejemplo manual: <ch1:50> para 390 nm al 50 %."
        )

    def _esperar_abortable(self, segundos):
        fin = time.monotonic() + max(0.0, float(segundos))
        while time.monotonic() < fin:
            self._comprobar_aborto()
            time.sleep(min(0.05, max(0.0, fin - time.monotonic())))

    def _confirmar_potencia_y_error(self, objetivo):
        tolerancia = max(0.0, float(self.cfg.get("tolerancia_potencia_mW_cm2", 0.5)))
        potencia = self.consultar_potencia()
        codigo_error = self.consultar_error()
        if codigo_error != 0:
            raise ErrorSimuladorSolar(self._texto_error(codigo_error))
        if not np.isfinite(potencia):
            raise ErrorSimuladorSolar(
                "El simulador solar devuelve <power:undef>; está en modo de potencia personalizada por canales LED."
            )
        if abs(float(potencia) - float(objetivo)) > tolerancia:
            raise ErrorSimuladorSolar(
                f"El simulador solar no confirma la potencia solicitada: objetivo={objetivo:g} mW/cmÂ², respuesta={potencia:g} mW/cmÂ²."
            )
        return potencia

    def encender_y_verificar(self, potencia_mW_cm2):
        if not self.conectado:
            raise ErrorSimuladorSolar("El simulador solar no está conectado.")

        potencia = float(potencia_mW_cm2)
        if not np.isfinite(potencia) or potencia < 0 or potencia > 200:
            raise ErrorSimuladorSolar("La potencia de encendido debe estar entre 0 y 200 mW/cmÂ².")

        objetivo = int(potencia)
        self.fijar_potencia(objetivo)
        self._esperar_abortable(self.cfg.get("tiempo_confirmacion_encendido_s", 1.0))

        if objetivo > 0:
            necesarias = max(1, int(self.cfg.get("confirmaciones_requeridas", 2)))
            intervalo = max(0.0, float(self.cfg.get("intervalo_confirmacion_s", 0.25)))
            correctas = 0
            intentos = max(necesarias, int(self.cfg.get("reintentos", 3))) + necesarias
            ultimo_error = None

            for _ in range(intentos):
                self._comprobar_aborto()
                try:
                    confirmada = self._confirmar_potencia_y_error(objetivo)
                    correctas += 1
                    if correctas >= necesarias:
                        self.encendido = True
                        self.potencia_confirmada = confirmada
                        return confirmada
                except Exception as exc:
                    ultimo_error = exc
                    correctas = 0
                self._esperar_abortable(intervalo)

            raise ErrorSimuladorSolar("No se pudo verificar el encendido del simulador solar.") from ultimo_error
        else:
            self.encendido = False
            self.potencia_confirmada = 0.0
            return 0.0

    def apagar(self):
        if self.serial is None or not self.serial.is_open:
            self.encendido = False
            self.potencia_confirmada = 0.0
            return 0.0

        evento_original = self.evento_aborto
        self.evento_aborto = None
        try:
            self.fijar_potencia(0)
            self.encendido = False
            self.potencia_confirmada = 0.0
            return 0.0
        finally:
            self.evento_aborto = evento_original

    def apagar_sin_error(self):
        try:
            return self.apagar()
        except Exception:
            return None

    def close(self, apagar=True):
        try:
            if apagar:
                self.apagar_sin_error()
        finally:
            if self.serial is not None:
                try:
                    self.serial.close()
                except Exception:
                    pass
            self.serial = None
            self.conectado = False
            self.encendido = False


def crear_controlador_simulador_solar(cfg, evento_aborto=None):
    if not cfg.get("simulador_solar_activo", False):
        return None
    return ControladorSimuladorSolarOssila(cfg["simulador_solar"], evento_aborto=evento_aborto)

