"""Contrato de configuración compartido por toda la aplicación."""
from copy import deepcopy
from core.utils import resolver_carpeta_salida_portatil

DEFAULT_CONFIG = {
    "tema_ui": "tmrw_silicon",
    "titulo_aplicacion": "Degradación comparativa I-V",
    # SMU R&S NGU401; el driver VISA se incorpora en la etapa 2.
    "smu": {
        "modelo": "R&S NGU401", 
        "recurso_visa": "AUTO", 
        "canal": 1,
        "verificar_modelo": True, 
        "timeout_ms": 60_000,
        "comprobar_errores_scpi_por_punto": True, 
        "comprobar_estado_cc": False,
    },
    "modo_medida": "completa",
    "i_proteccion_solicitada_A": 10e-6, 
    "i_max_A": 20e-6,
    "rango_corriente_A": 10e-6, 
    "nplc": 1.0,
    "delay_estabilizacion_s": 0.0001, 
    "lecturas_descartables_por_punto": 1,
    "espera_entre_lecturas_s": 0.020,
    "frecuencia_red_Hz": 50.0,
    "margen_lectura_s": 0.010, 
    "delay_primer_punto_s": 1.0,
    "espera_tras_activar_s": 0.100,
    "timeout_lectura_valida_s": 2.0, 
    "intervalo_reintento_lectura_s": 0.020,
    "abortar_si_limite_corriente": True, 
    "fraccion_limite_warning": 0.98,
    "guardar_parcial_si_aborta": True, 
    "medir_tension_real": False,
    "invertir_eje_y_graficas": True,
    "directa": {
        "v_inicial_mV": 0.0, 
        "v_final_mV": 550.0,
        "paso_mV": 10.0
        },
    "inversa": {
        "v_inicial_mV": None, 
        "v_final_V": -11.0,
        "paso_mV": 100.0
        },
    "irradiancia_mW_cm2": None,
    "curva_iv": {
        "A": {"v_ini_dir_mV": 0.0, "v_fin_dir_mV": 550.0, "paso_dir_mV": 10.0, "v_ini_inv_mV": "", "v_fin_inv_V": -11.0, "paso_inv_mV": 100.0, "i_max_uA": 10.0, "i_max_unit": "uA"},
        "B": {"v_ini_dir_mV": 0.0, "v_fin_dir_mV": 550.0, "paso_dir_mV": 10.0, "v_ini_inv_mV": "", "v_fin_inv_V": -11.0, "paso_inv_mV": 100.0, "i_max_uA": 10.0, "i_max_unit": "uA"},
    },
    "dispositivos": {
        "A": {"nombre": "Estructura A", "superficie_um2": None},
        "B": {"nombre": "Estructura B", "superficie_um2": None},
    },
    # A usa los contactos NC; B usa los contactos NO de ambos relés.
    "rele": {
        "driver": "arduino_serial", 
        "puerto_serie": "COM3",
        "baudrate": 115200,
        "timeout_s": 3.0, 
        "espera_tras_conmutacion_s": 0.5,
        "estado_seguro_al_inicio": "todos_desconectados",
        "estado_seguro_al_final": "todos_desconectados", 
        "duracion_prueba_rele_s": 0.35, 
        "prueba_deteccion": {
            "tension_V": 0.10, 
            "limite_corriente_A": 100e-6, 
            "rango_corriente_A": 1e-3, 
            "umbral_corriente_A": 10e-9
            },
    },
    "programacion": {
        "modo": "por_tiempo", #  por_tiempo | por_pendiente_voc
        "inicio_inmediato": True,
        "tramos_tiempo": [
            {"hasta_min": 5.0, "intervalo_s": 30.0},
            {"hasta_min": 15.0, "intervalo_s": 60.0},
            {"hasta_min": 20.0, "intervalo_s": 150.0},
        ],
        "intervalo_final_s": 150.0,
        "tramos_pendiente_voc": [
            {"umbral_V_por_min": 0.005, "intervalo_s": 60.0},
            {"umbral_V_por_min": 0.002, "intervalo_s": 150.0},
        ],
        "ventana_pendiente_muestras": 4,
        "confirmaciones_pendiente": 2,
        "intervalo_minimo_s": 10.0,
    },
    "carpeta_salida": resolver_carpeta_salida_portatil(),
    "nombre_experimento": "test_mateu",
    "carpeta_salida_experimento": None,
    "fecha_hora_inicio_experimento": None,
    "evento_aborto": None, 
    "log_callback": None, 
    "grafica_callback": None,
}

def get_default_config() -> dict:
    """Devuelve una copia profunda para evitar estado compartido entre medidas."""
    return deepcopy(DEFAULT_CONFIG)
