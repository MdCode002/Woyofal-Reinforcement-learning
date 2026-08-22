from datetime import datetime, time, timedelta, timezone

from stable_baselines3.common.env_checker import check_env

from env.energy_env import EnergyEnv
from common.models import Appareil, FenetreUsage, ProfilChargePas, Scenario
from common.units import PAS_DECISION_MINUTES



# Données de démo à remplacer par de vraies sorties m2


def _build_demo_scenario(
    credit_initial_kwh: float = 10.0,
    duree_heures: float = 2.0,
) -> Scenario:
    date_debut = datetime(2026, 8, 22, 0, 0, tzinfo=timezone.utc)
    date_cible = date_debut + timedelta(hours=duree_heures)

    fenetre = FenetreUsage(
        heure_debut=time(18, 0),
        heure_fin=time(20, 0),
        probabilite_utilisation=0.8,
        duree_moyenne_minutes=60,
    )

    fer_a_repasser = Appareil(
        nom="fer_a_repasser",
        puissance_w=1200.0,
        flexible=True,
        decalage_autorise=True,
        essentiel=False,
        fenetres_usage=(fenetre,),
    )

    frigo = Appareil(
        nom="frigo",
        puissance_w=150.0,
        flexible=False,
        decalage_autorise=False,
        essentiel=True,
        fenetres_usage=(fenetre,),
    )

    return Scenario(
        identifiant_foyer="foyer_test_001",
        nombre_occupants=3,
        credit_initial_kwh=credit_initial_kwh,
        date_debut=date_debut,
        date_cible=date_cible,
        pas_minutes=PAS_DECISION_MINUTES,
        appareils=(fer_a_repasser, frigo),
        temperature_interieure_initiale_c=28.0,
        source_temperature_interieure="estimee",
        temperature_exterieure_initiale_c=30.0,
        humidite_initiale_pourcent=60.0,
        source_meteo="demo",
        occupation_initiale=True,
    )


def _build_demo_load_profile(scenario: Scenario, n_steps: int) -> list[ProfilChargePas]:
    profile = []
    horodatage = scenario.date_debut

    for _ in range(n_steps):
        energie_par_appareil = {
            "fer_a_repasser": 0.6,
            "frigo": 0.075,
        }
        profile.append(
            ProfilChargePas(
                horodatage=horodatage,
                pas_minutes=PAS_DECISION_MINUTES,
                puissance_par_appareil_w={
                    "fer_a_repasser": 1200.0,
                    "frigo": 150.0,
                },
                energie_par_appareil_kwh=energie_par_appareil,
                energie_non_thermique_totale_kwh=sum(energie_par_appareil.values()),
            )
        )
        horodatage += timedelta(minutes=PAS_DECISION_MINUTES)

    return profile


def _build_demo_weather_profile(n_steps: int) -> list[dict]:
    return [
        {"temperature_ext": 30.0, "humidity": 60.0}
        for _ in range(n_steps)
    ]


def _build_demo_env(credit_initial_kwh: float = 10.0, n_steps: int = 4) -> EnergyEnv:
    scenario = _build_demo_scenario(credit_initial_kwh=credit_initial_kwh)
    load_profile = _build_demo_load_profile(scenario, n_steps)
    weather_profile = _build_demo_weather_profile(n_steps)

    return EnergyEnv(
        scenario=scenario,
        load_profile=load_profile,
        weather_profile=weather_profile,
    )



# Tests


def test_environment_reset():
    env = _build_demo_env()

    observation, info = env.reset()

    assert observation.shape == env.observation_space.shape
    assert env.observation_space.contains(observation)
    assert "observation" in info


def test_environment_step():
    env = _build_demo_env()
    env.reset()

    next_observation, reward, terminated, truncated, info = env.step(1)

    assert next_observation.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)


def test_ac_consumption_reduces_balance():
    env = _build_demo_env(credit_initial_kwh=10.0)
    env.reset()

    initial_balance = env.meter.balance

    _, _, _, _, info = env.step(1)

    assert info["energy_consumption"] > 0.0
    assert info["balance"] < initial_balance


def test_environment_uses_30_minute_steps():
    env = _build_demo_env()
    env.reset()

    env.step(0)

    assert env.hour == 0.5


def test_report_charge_defers_flexible_energy():
    env = _build_demo_env(n_steps=4)
    env.reset()

    # Action 4 = reporter la charge flexible decalable (fer_a_repasser)
    _, _, _, _, info = env.step(4)

    assert info["action"].report_charge is not None
    assert info["action"].report_charge.appareil == "fer_a_repasser"
    # L'energie du fer a repasser n'est pas consommee ce pas-ci, elle est mise
    # de cote pour le pas suivant...
    assert env.deferred_flexible_kwh == 0.6


    # baisser le solde et remet le compteur de report a zero.
    balance_after_defer = env.meter.balance
    env.step(0)
    assert env.meter.balance < balance_after_defer
    assert env.deferred_flexible_kwh == 0.0


def test_gymnasium_compliance():
    env = _build_demo_env()
    check_env(env)