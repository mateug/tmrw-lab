import pandas as pd
import pytest

from apps.lite.plan_engine import build_lite_plan


def test_build_lite_plan_expands_only_structures_and_preserves_order():
    df = pd.DataFrame([
        {
            "motor_lineal_step": 10,
            "motor_lineal_stop": 20,
            "motor_inclinacion_step": 0,
            "motor_inclinacion_stop": 0,
            "motor_rotacion_step": 0,
            "motor_rotacion_stop": 0,
            "650 nm": 0.5,
            "Warm white": 0,
            "Estructuras": "1, 2, 3",
        },
        {
            "motor_lineal_step": 30,
            "motor_lineal_stop": 40,
            "motor_inclinacion_step": 0,
            "motor_inclinacion_stop": 0,
            "motor_rotacion_step": 0,
            "motor_rotacion_stop": 0,
            "650 nm": 1.0,
            "Warm white": 0.25,
            "Estructuras": "3,6",
        },
    ])

    plan = build_lite_plan(df)

    assert plan.measure_count == 5
    assert [step["estructura"] for step in plan.steps] == [
        "Estructura 1", "Estructura 2", "Estructura 3", "Estructura 3", "Estructura 6"
    ]
    assert plan.active_axes == frozenset({"motor_lineal", "led", "estructura"})
    assert plan.steps[0]["motores"]["motor_lineal"] == {"step": 10.0, "stop": 20.0}
    assert plan.steps[0]["leds"] == {"650": 50.0}
    assert plan.steps[-1]["leds"] == {"650": 100.0, "warm_white": 25.0}


def test_build_lite_plan_allows_no_structure_axis():
    df = pd.DataFrame([{"650 nm": 50}])

    plan = build_lite_plan(df, valores_en_tanto_por_uno=False)

    assert plan.measure_count == 1
    assert plan.steps[0]["estructura"] is None
    assert plan.active_axes == frozenset({"led"})


def test_build_lite_plan_ignores_zero_structure_ids():
    plan = build_lite_plan(pd.DataFrame([{"Estructura": "0, 2.0"}]))

    assert [step["estructura"] for step in plan.steps] == ["Estructura 2"]
    assert plan.active_axes == frozenset({"estructura"})


@pytest.mark.parametrize("value", ["x", 1.1, -0.1])
def test_build_lite_plan_rejects_invalid_unit_interval_led(value):
    with pytest.raises(ValueError, match="650 nm"):
        build_lite_plan(pd.DataFrame([{"650 nm": value}]))


def test_build_lite_plan_rejects_partial_motor_pair():
    df = pd.DataFrame([{"motor_lineal_step": 10, "motor_lineal_stop": 0}])

    with pytest.raises(ValueError, match="motor_lineal"):
        build_lite_plan(df)


def test_build_lite_plan_rejects_structure_outside_relay_range():
    with pytest.raises(ValueError, match="entre 1 y 7"):
        build_lite_plan(pd.DataFrame([{"Estructura": "1,8"}]))