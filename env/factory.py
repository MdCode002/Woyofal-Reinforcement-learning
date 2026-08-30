"""Construction unique de l'environnement complet."""

from __future__ import annotations

from pathlib import Path

from common import Scenario, charger_scenario
from ramp_adapter import generer_profils_ramp, meteo_pour_scenario
from rl.config import ConfigurationRecompense

from .woyofal_env import EnvironnementWoyofal
from .multi_scenario import EnvironnementMultiScenario

SCENARIO_FIXTURE = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "foyer_fictif.json"


def creer_environnement(
    scenario: Scenario | None = None,
    *,
    seed: int | None = None,
    configuration_recompense: ConfigurationRecompense | None = None,
) -> EnvironnementWoyofal:
    scenario = scenario or charger_scenario(SCENARIO_FIXTURE)
    profils = generer_profils_ramp(scenario, seed=scenario.seed if seed is None else seed)
    meteo = meteo_pour_scenario(scenario)
    return EnvironnementWoyofal(scenario, profils, meteo, configuration_recompense)


def creer_environnement_multi(
    dossier: str | Path,
    *,
    configuration_recompense: ConfigurationRecompense | None = None,
    taux_adoption: float | None = None,
    ablation: str = "aucune",
) -> EnvironnementMultiScenario:
    chemins = sorted(Path(dossier).glob("scenario_*.json"))
    return EnvironnementMultiScenario(
        chemins,
        configuration_recompense=configuration_recompense,
        taux_adoption=taux_adoption,
        ablation=ablation,
    )


def verifier_gymnasium() -> None:
    from gymnasium.utils.env_checker import check_env

    env = creer_environnement()
    check_env(env, skip_render_check=True)
    if env._environnements_pieces:
        check_env(env._environnements_pieces[0], skip_render_check=True)

