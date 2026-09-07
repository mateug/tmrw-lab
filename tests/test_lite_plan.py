import pandas as pd
import pytest

from apps.lite.config import get_default_config
from apps.lite.plan_engine import build_lite_plan, construir_nombre_iteracion_lite, insertar_enfriamientos_lite


def test_default_lite_config_includes_nested_motor_axes():
    cfg = get_default_config()

    assert cfg["motor"]["inclinacion"]["puerto_serie"] == "COM5"
    assert cfg["motor"]["rotacion"]["puerto_serie"] == "COM6"


def test_build_lite_plan_expands_only_structures_and_preserves_order():
    df = pd.DataFrame([
        {
            "lineal step": 10,
            "lineal stop": 20,
            "rotacion step": 45,
            "rotacion stop": 90,
            "inclinacion step": 30,
            "inclinacion stop": 60,
            "650 nm": 0.5,
            "Warm white": 0,
            "Estructuras": "1, 2, 3",
        },
        {
            "lineal step": 0,
            "lineal stop": 0,
            "rotacion step": 0,
            "rotacion stop": 0,
            "inclinacion step": 0,
            "inclinacion stop": 0,
            "650 nm": 1.0,
            "Warm white": 0.25,
            "Estructuras": "3,6",
        },
    ])

    plan = build_lite_plan(df)

    assert plan.measure_count == 83
    assert [step["estructura"] for step in plan.steps] == [
        *(["Estructura 1", "Estructura 2", "Estructura 3"] * 27),
        "Estructura 3", "Estructura 6",
    ]
    assert plan.active_axes == frozenset({"motor_lineal", "motor_inclinacion", "motor_rotacion", "led", "estructura"})
    assert plan.steps[0]["motores"]["motor_lineal"]["pasos"] == 0
    assert plan.steps[1]["motores"]["motor_lineal"]["pasos"] == 0
    assert plan.steps[0]["leds"] == {"650": 50.0, "warm_white": 0.0}
    assert plan.steps[-1]["leds"] == {"650": 100.0, "warm_white": 25.0}


def test_build_lite_plan_allows_no_structure_axis():
    df = pd.DataFrame([{"650 nm": 50}])

    plan = build_lite_plan(df, valores_en_tanto_por_uno=False)

    assert plan.measure_count == 1
    assert plan.steps[0]["estructura"] is None
    assert plan.active_axes == frozenset({"led"})


def test_construir_nombre_iteracion_lite_usa_longitud_de_onda():
    nombre = construir_nombre_iteracion_lite(
        "medida_lite",
        {"leds": {"11": 50, "8": 25, "cool_white": 100}, "motores": {}},
    )

    assert nombre == "medida_lite__950nm_050pct-660nm_025pct-cool_white_100pct"


def test_build_lite_plan_ignores_zero_structure_ids():
    plan = build_lite_plan(pd.DataFrame([{"Estructura": "0, 2.0"}]))

    assert [step["estructura"] for step in plan.steps] == ["Estructura 2"]
    assert plan.active_axes == frozenset({"estructura"})


def test_insertar_enfriamientos_lite_usa_medidas_de_estructuras():
    plan = build_lite_plan(pd.DataFrame([{"Estructura": "1, 2, 3"}]))

    plan = insertar_enfriamientos_lite(plan, cada_n_medidas=2, tiempo_s=30)

    assert plan.measure_count == 3
    assert [step.get("tipo", "medida") for step in plan.steps] == ["medida", "medida", "enfriar", "medida"]
    assert plan.steps[2]["duracion_s"] == 30


@pytest.mark.parametrize("value", ["x", 1.1, -0.1])
def test_build_lite_plan_rejects_invalid_unit_interval_led(value):
    with pytest.raises(ValueError, match="650 nm"):
        build_lite_plan(pd.DataFrame([{"650 nm": value}]))


def test_build_lite_plan_rejects_partial_motor_pair():
    df = pd.DataFrame([{"lineal step": 10, "lineal stop": 0}])

    with pytest.raises(ValueError, match="motor_lineal"):
        build_lite_plan(df)


def test_build_lite_plan_reads_reference_headers():
    df = pd.read_excel("referencia.xlsx", sheet_name="Tabla")

    plan = build_lite_plan(df, valores_en_tanto_por_uno=False)

    assert plan.measure_count == 11 * 5 * 11 * 7
    assert plan.steps[0]["estructura"] == "Estructura 1"
    assert plan.steps[0]["leds"] == {"660": 50.0, "730": 50.0}
    assert plan.steps[-1]["motores"]["motor_lineal"]["valor"] == 6500.0
    assert plan.steps[-1]["motores"]["motor_inclinacion"]["valor"] == 180.0
    assert plan.steps[-1]["motores"]["motor_rotacion"]["valor"] == 5.0


def test_build_lite_plan_rejects_structure_outside_relay_range():
    with pytest.raises(ValueError, match="entre 1 y 7"):
        build_lite_plan(pd.DataFrame([{"Estructura": "1,8"}]))