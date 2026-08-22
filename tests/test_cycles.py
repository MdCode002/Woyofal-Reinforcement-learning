from thermal.model_1r1c import Thermal1R1C
from woyofal.meter import WoyofalMeter
from common.units import PAS_DECISION_MINUTES, MINUTES_PAR_HEURE

DT_HOURS = PAS_DECISION_MINUTES / MINUTES_PAR_HEURE

# Cycles du compteur Woyofal


def test_repeated_small_consumptions_equal_one_large_consumption():
    # Consommer 0.5 kWh dix fois de suite doit donner le meme solde final
    # que consommer 5.0 kWh en une seule fois (pas d'effet de bord entre pas).
    meter_par_petits_pas = WoyofalMeter(initial_balance=20.0)
    for _ in range(10):
        meter_par_petits_pas.consume(0.5)

    meter_en_un_coup = WoyofalMeter(initial_balance=20.0)
    meter_en_un_coup.consume(5.0)

    assert meter_par_petits_pas.balance == meter_en_un_coup.balance


def test_meter_stays_cutoff_after_reaching_zero():
    meter = WoyofalMeter(initial_balance=1.0)

    meter.consume(1.0)
    assert meter.balance == 0.0
    assert meter.is_cutoff is True

    # Un pas supplementaire apres coupure ne doit pas faire "repartir" le
    # solde en negatif ni retirer l'etat de coupure.
    meter.consume(2.0)
    assert meter.balance == 0.0
    assert meter.is_cutoff is True


def test_meter_rejects_negative_consumption():
    meter = WoyofalMeter(initial_balance=5.0)

    try:
        meter.consume(-1.0)
        assert False, "consume() aurait du lever une ValueError"
    except ValueError:
        pass


def test_meter_zero_consumption_does_not_change_balance():
    meter = WoyofalMeter(initial_balance=5.0)

    new_balance = meter.consume(0.0)

    assert new_balance == 5.0
    assert meter.is_cutoff is False


# Cycles thermiques sur plusieurs jours

def test_temperature_remains_bounded_over_three_repeated_days():
    # Rejoue le meme cycle jour/nuit sur 3 jours consecutifs et verifie que
    # la temperature ne derive pas (pas de divergence numerique cumulative).
    thermal = Thermal1R1C(
        T_int=28.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0,
    )

    steps_par_jour = int(24 / DT_HOURS)
    temperatures_fin_de_journee = []

    for _ in range(3):
        for step in range(steps_par_jour):
            hour = step * DT_HOURS
            ac_on = hour >= 20 or hour < 6
            T_ext = 34.0 if 6 <= hour < 18 else 28.0

            thermal.step(T_ext=T_ext, dt_hours=DT_HOURS, ac_on=ac_on)

        temperatures_fin_de_journee.append(thermal.T_int)
        assert 0.0 < thermal.T_int < 50.0

    # L'ecart de temperature entre le 1er et le 3eme jour (meme cycle rejoue)
    # doit rester faible : le systeme converge vers un regime quasi-periodique
    # plutot que de deriver indefiniment.
    ecart_jour1_jour3 = abs(temperatures_fin_de_journee[2] - temperatures_fin_de_journee[0])
    assert ecart_jour1_jour3 < 2.0


def test_ac_on_off_cycle_alternates_temperature_direction():
    # Une clim qu'on alterne ON/OFF pendant du chaud exterieur doit faire
    # alterner la direction d'evolution de la temperature (baisse quand ON,
    # hausse ou stagnation quand OFF), et non toujours dans le meme sens.
    thermal = Thermal1R1C(
        T_int=30.0,
        R=2.0,
        C=10.0,
        cooling_power_kw=3.0,
        cop=3.0,
    )

    directions = []
    for cycle_step in range(6):
        ac_on = cycle_step % 2 == 0
        before = thermal.T_int
        after = thermal.step(T_ext=35.0, dt_hours=DT_HOURS, ac_on=ac_on)
        directions.append("baisse" if after < before else "hausse_ou_stable")

    assert "baisse" in directions
    assert "hausse_ou_stable" in directions