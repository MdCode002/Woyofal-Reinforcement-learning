from thermal.model_1r1c import Thermal1R1C
from common.units import PAS_DECISION_MINUTES, MINUTES_PAR_HEURE

# Pas de décision commun (30 minutes), dérivé du contrat de M1 plutôt que codé en dur.
DT_HOURS = PAS_DECISION_MINUTES / MINUTES_PAR_HEURE
STEPS_PAR_JOUR = int(24 / DT_HOURS)


def test_hot_weather_increases_temperature():
    thermal = Thermal1R1C(
        T_int=28.0,
        R=2.0,
        C=10.0
    )

    initial_temperature = thermal.T_int

    thermal.step(
        T_ext=40.0,
        dt_hours=DT_HOURS,
        ac_on=False
    )

    assert thermal.T_int > initial_temperature


def test_cool_weather_decreases_temperature():
    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0
    )

    initial_temperature = thermal.T_int

    thermal.step(
        T_ext=20.0,
        dt_hours=DT_HOURS,
        ac_on=False
    )

    assert thermal.T_int < initial_temperature


def test_stronger_ac_cools_more():
    thermal_weak = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=2.0
    )

    thermal_strong = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=4.0
    )

    temp_weak = thermal_weak.step(
        T_ext=35.0,
        dt_hours=DT_HOURS,
        ac_on=True
    )

    temp_strong = thermal_strong.step(
        T_ext=35.0,
        dt_hours=DT_HOURS,
        ac_on=True
    )

    assert temp_strong < temp_weak


def test_higher_thermal_resistance_slows_temperature_change():
    thermal_low_R = Thermal1R1C(
        T_int=25.0,
        R=1.0,
        C=10.0
    )

    thermal_high_R = Thermal1R1C(
        T_int=25.0,
        R=4.0,
        C=10.0
    )

    temp_low_R = thermal_low_R.step(
        T_ext=35.0,
        dt_hours=DT_HOURS,
        ac_on=False
    )

    temp_high_R = thermal_high_R.step(
        T_ext=35.0,
        dt_hours=DT_HOURS,
        ac_on=False
    )

    assert temp_high_R < temp_low_R


def test_higher_thermal_capacity_slows_temperature_change():
    thermal_low_C = Thermal1R1C(
        T_int=25.0,
        R=2.0,
        C=5.0
    )

    thermal_high_C = Thermal1R1C(
        T_int=25.0,
        R=2.0,
        C=20.0
    )

    temp_low_C = thermal_low_C.step(
        T_ext=35.0,
        dt_hours=DT_HOURS,
        ac_on=False
    )

    temp_high_C = thermal_high_C.step(
        T_ext=35.0,
        dt_hours=DT_HOURS,
        ac_on=False
    )

    assert temp_high_C < temp_low_C


def test_thermal_time_constant():
    thermal = Thermal1R1C(
        T_int=28.0,
        R=2.0,
        C=10.0
    )

    tau = thermal.R * thermal.C

    assert tau == 20.0


def test_higher_cop_reduces_electric_consumption():
    thermal_low_cop = Thermal1R1C(
        cooling_power_kw=3.0,
        cop=2.0
    )

    thermal_high_cop = Thermal1R1C(
        cooling_power_kw=3.0,
        cop=4.0
    )

    energy_low_cop = thermal_low_cop.electric_consumption_kwh(
        dt_hours=1.0,
        ac_on=True
    )

    energy_high_cop = thermal_high_cop.electric_consumption_kwh(
        dt_hours=1.0,
        ac_on=True
    )

    assert energy_high_cop < energy_low_cop


def test_one_day_temperature_simulation():
    thermal = Thermal1R1C(
        T_int=28.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0
    )

    temperatures = []

    for step in range(STEPS_PAR_JOUR):

        hour = step * DT_HOURS

        if 20 <= hour or hour < 6:
            ac_on = True
        else:
            ac_on = False

        if 6 <= hour < 18:
            T_ext = 34.0
        else:
            T_ext = 28.0

        temperature = thermal.step(
            T_ext=T_ext,
            dt_hours=DT_HOURS,
            ac_on=ac_on
        )

        temperatures.append(temperature)

    assert len(temperatures) == STEPS_PAR_JOUR
    assert all(temp > 0 for temp in temperatures)