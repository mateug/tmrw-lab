from apps.studio.config import get_default_config
from apps.studio.plan_engine import generar_plan_estudio


def _build_cfg():
    cfg = get_default_config()
    cfg["simulador_solar_activo"] = True
    cfg["eje_estructura_activo"] = True
    cfg["barrido_motor_activo"] = False
    cfg["irradiancia_modo"] = "potencia"
    cfg["irradiancia_potencia"] = {
        "p_inicial_mW_cm2": 10.0,
        "p_final_mW_cm2": 20.0,
        "paso_mW_cm2": 10.0,
        "espera_estabilizacion_s": 1.0,
        "espera_encendido_medida_s": 1.0,
    }
    cfg["estructura"] = {
        "estructuras": ["Estructura 1", "Estructura 2"],
        "espera_estabilizacion_s": 0.5,
        "keithley_por_estructura": {
            "Estructura 1": {"recurso_visa": "AUTO", "modo_medida": "completa"},
            "Estructura 2": {"recurso_visa": "AUTO", "modo_medida": "completa"},
        },
    }
    cfg["irradiancia_combinacion"] = {
        "canales_combinacion": [{"canal": "950", "intensidades": "100"}],
        "relaciones": [],
        "espera_estabilizacion_s": 1.0,
        "espera_encendido_medida_s": 1.0,
        "cada_n_medidas_estructura": 1,
        "tiempo_enfriado_s": 30.0,
    }
    cfg["irradiancia_multiples_combinaciones"] = {
        "combinaciones": [],
        "espera_estabilizacion_s": 1.0,
        "espera_encendido_medida_s": 1.0,
        "cada_n_medidas_estructura": 1,
        "tiempo_enfriado_s": 30.0,
    }
    return cfg


def test_generar_plan_estudio_ordena_medidas_por_estructura_y_cooldown():
    cfg = _build_cfg()

    plan = generar_plan_estudio(cfg)

    assert plan[0]["tipo"] == "medida"
    assert plan[0]["estructura"] == "Estructura 1"
    assert plan[1]["tipo"] == "enfriar"
    assert plan[1]["duracion_s"] == 30.0
    assert plan[2]["tipo"] == "medida"
    assert plan[2]["estructura"] == "Estructura 2"
