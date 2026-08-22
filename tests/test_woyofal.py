from thermal.model_1r1c import Thermal1R1C
from woyofal.meter import WoyofalMeter


def test_balance_decreases_after_consumption():
    meter = WoyofalMeter(initial_balance=10.0)

    new_balance = meter.consume(2.5)

    assert new_balance == 7.5
    assert meter.is_cutoff is False


def test_balance_reaches_zero_and_cutoff():
    meter = WoyofalMeter(initial_balance=5.0)

    new_balance = meter.consume(5.0)

    assert new_balance == 0.0
    assert meter.is_cutoff is True


def test_balance_cannot_be_negative():
    meter = WoyofalMeter(initial_balance=5.0)

    new_balance = meter.consume(7.0)

    assert new_balance == 0.0
    assert meter.is_cutoff is True


def test_ac_consumption_decreases_woyofal_balance():
    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0
    )

    meter = WoyofalMeter(initial_balance=10.0)

    energy = thermal.electric_consumption_kwh(
        dt_hours=0.5,
        ac_on=True
    )

    new_balance = meter.consume(energy)

    assert energy == 0.5
    assert new_balance == 9.5