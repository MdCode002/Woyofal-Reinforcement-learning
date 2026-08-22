from thermal.model_1r1c import Thermal1R1C


def test_temperature_increases_when_ac_is_off():
    thermal = Thermal1R1C(
        T_int=25.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0
    )

    new_temperature = thermal.step(
        T_ext=35.0,
        dt_hours=0.5,
        ac_on=False
    )

    assert new_temperature > 25.0


def test_temperature_decreases_when_ac_is_on():
    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0
    )

    new_temperature = thermal.step(
        T_ext=35.0,
        dt_hours=0.5,
        ac_on=True
    )

    assert new_temperature < 30.0


def test_temperature_unchanged_when_inside_equals_outside_and_ac_off():
    thermal = Thermal1R1C(
        T_int=25.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0
    )

    new_temperature = thermal.step(
        T_ext=25.0,
        dt_hours=0.5,
        ac_on=False
    )

    assert new_temperature == 25.0


def test_ac_electric_consumption():
    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0
    )

    energy = thermal.electric_consumption_kwh(
        dt_hours=0.5,
        ac_on=True
    )

    assert energy == 0.5


def test_ac_consumes_nothing_when_off():
    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0
    )

    energy = thermal.electric_consumption_kwh(
        dt_hours=0.5,
        ac_on=False
    )

    assert energy == 0.0