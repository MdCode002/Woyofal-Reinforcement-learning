from thermal.model_1r1c import Thermal1R1C
from woyofal.meter import WoyofalMeter


def test_ac_consumption_reduces_woyofal_balance():

    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0
    )

    meter = WoyofalMeter(initial_balance=20.0)

    energy = thermal.electric_consumption_kwh(
        dt_hours=0.5,
        ac_on=True
    )

    new_balance = meter.consume(energy)

    assert energy == 0.5
    assert new_balance == 19.5