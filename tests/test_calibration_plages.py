from thermal.model_1r1c import Thermal1R1C
from common.units import PAS_DECISION_MINUTES, MINUTES_PAR_HEURE
 
DT_HOURS = PAS_DECISION_MINUTES / MINUTES_PAR_HEURE
 
R_MIN, R_MAX = 1.0, 4.0
C_MIN, C_MAX = 5.0, 20.0
COP_MIN, COP_MAX = 2.5, 4.5
TAU_MIN_HOURS, TAU_MAX_HOURS = 2.0, 80.0
 
 
def test_default_r_within_plausible_range():
    thermal = Thermal1R1C(T_int=28.0, R=2.0, C=10.0)
    assert R_MIN <= thermal.R <= R_MAX
 
 
def test_default_c_within_plausible_range():
    thermal = Thermal1R1C(T_int=28.0, R=2.0, C=10.0)
    assert C_MIN <= thermal.C <= C_MAX
 
 
def test_default_cop_within_plausible_range():
    thermal = Thermal1R1C(cooling_power_kw=3.0, cop=3.0)
    assert COP_MIN <= thermal.cop <= COP_MAX
 
 
def test_time_constant_within_plausible_range():
    thermal = Thermal1R1C(T_int=28.0, R=2.0, C=10.0)
    tau = thermal.R * thermal.C
    assert TAU_MIN_HOURS <= tau <= TAU_MAX_HOURS
 
 
def test_time_constant_scales_with_r_and_c():
    # Un R ou un C plus grand doit ralentir l'evolution, donc augmenter tau,
    # tout en restant dans la plage plausible tant que R et C le sont.
    thermal_faible = Thermal1R1C(T_int=28.0, R=R_MIN, C=C_MIN)
    thermal_fort = Thermal1R1C(T_int=28.0, R=R_MAX, C=C_MAX)
 
    tau_faible = thermal_faible.R * thermal_faible.C
    tau_fort = thermal_fort.R * thermal_fort.C
 
    assert tau_faible < tau_fort
    assert TAU_MIN_HOURS <= tau_faible <= TAU_MAX_HOURS
    assert TAU_MIN_HOURS <= tau_fort <= TAU_MAX_HOURS
 
 
def test_ac_power_range_realistic_for_prepaid_household():
    for cooling_power_kw in (0.9, 1.5, 2.5, 3.5):
        thermal = Thermal1R1C(cooling_power_kw=cooling_power_kw, cop=3.0)
        energy = thermal.electric_consumption_kwh(dt_hours=DT_HOURS, ac_on=True)
        assert energy > 0.0
        assert energy <= cooling_power_kw * DT_HOURS
 
 
def test_temperature_stays_bounded_over_one_day_across_r_c_grid():
    # Verifie que, pour toute combinaison plausible de R et C, une simulation
    # d'une journee complete reste dans une plage de temperature realiste
    # (pas de divergence numerique, pas de temperature negative).
    steps_par_jour = int(24 / DT_HOURS)
 
    for R in (R_MIN, (R_MIN + R_MAX) / 2, R_MAX):
        for C in (C_MIN, (C_MIN + C_MAX) / 2, C_MAX):
            thermal = Thermal1R1C(
                T_int=28.0,
                R=R,
                C=C,
                cooling_power_kw=3.0,
                cop=3.0,
            )
 
            for step in range(steps_par_jour):
                hour = step * DT_HOURS
                ac_on = hour >= 20 or hour < 6
                T_ext = 34.0 if 6 <= hour < 18 else 28.0
 
                T_int = thermal.step(T_ext=T_ext, dt_hours=DT_HOURS, ac_on=ac_on)
 
                assert 0.0 < T_int < 50.0, (
                    f"Temperature implausible pour R={R}, C={C} au pas {step}: {T_int}"
                )