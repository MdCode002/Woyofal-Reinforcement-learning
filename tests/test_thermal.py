from thermal.model_1r1c import Thermal1R1C


def test_temperature_increases_when_outside_is_hotter():
    thermal = Thermal1R1C(
        T_int=25.0,
        R=2.0,
        C=10.0
    )

    new_temperature = thermal.step(
        T_ext=35.0,
        dt=1.0
    )

    assert new_temperature > 25.0


def test_temperature_decreases_when_outside_is_cooler():
    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0
    )

    new_temperature = thermal.step(
        T_ext=20.0,
        dt=1.0
    )

    assert new_temperature < 30.0


def test_temperature_remains_unchanged_when_inside_equals_outside():
    thermal = Thermal1R1C(
        T_int=25.0,
        R=2.0,
        C=10.0
    )

    new_temperature = thermal.step(
        T_ext=25.0,
        dt=1.0
    )

    assert new_temperature == 25.0