"""Entraînement et rechargement reproductibles de DQN."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stable_baselines3 import DQN
from stable_baselines3.common.monitor import Monitor

from env import creer_environnement, creer_environnement_multi

from .config import charger_configuration, configuration_recompense
from .reproducibility import creer_metadonnees, sauvegarder_json

RACINE_PROJET = Path(__file__).resolve().parents[1]
RESULTATS_MODELES = RACINE_PROJET / "results" / "models"


def construire_environnement(configuration: dict[str, Any], *, seed: int):
    dossier_scenarios = Path(configuration["environnement"].get("jeu_scenarios", ""))
    if dossier_scenarios.exists() and any(dossier_scenarios.glob("scenario_*.json")):
        environnement = creer_environnement_multi(
            dossier_scenarios,
            configuration_recompense=configuration_recompense(configuration),
        )
    else:
        environnement = creer_environnement(
            seed=seed,
            configuration_recompense=configuration_recompense(configuration),
        )
    environnement.reset(seed=seed)
    return environnement


def _parametres_modele(algorithme: str, configuration: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    parametres = dict(configuration.get(algorithme, configuration.get("dqn", {})))
    total = int(parametres.pop("total_timesteps", 500000))
    parametres.pop("seeds_finales", None)
    architecture = parametres.pop("net_arch", [256, 256])
    parametres["policy_kwargs"] = {"net_arch": architecture}
    return total, parametres


def entrainer(
    *,
    algorithme: str = "dqn",
    configuration: dict[str, Any] | None = None,
    seed: int = 17,
    total_timesteps: int | None = None,
    dossier_sortie: str | Path | None = None,
    modele_initial: str | Path | None = None,
    verbose: int = 1,
) -> Path:
    algorithme = algorithme.lower()
    if algorithme != "dqn":
        raise ValueError("L'algorithme de ce projet est 'dqn'")
    configuration = configuration or charger_configuration()
    total_config, parametres = _parametres_modele(algorithme, configuration)
    nombre_pas = int(total_timesteps or total_config)
    if nombre_pas <= 0:
        raise ValueError("total_timesteps doit être strictement positif")
    dossier = Path(dossier_sortie or RESULTATS_MODELES / f"{algorithme}_seed_{seed}")
    dossier.mkdir(parents=True, exist_ok=True)
    environnement = Monitor(
        construire_environnement(configuration, seed=seed),
        filename=str(dossier / "monitor.csv"),
        info_keywords=(
            "energie_servie_cumulee_kwh", "inconfort_cumule_degre_heures",
            "date_cible_atteinte", "raison_fin",
        ),
    )
    if modele_initial is None:
        modele = DQN("MlpPolicy", environnement, seed=seed, verbose=verbose, **parametres)
        remise_a_zero = True
    else:
        modele = DQN.load(str(modele_initial), env=environnement)
        remise_a_zero = False
    modele.learn(
        total_timesteps=nombre_pas, progress_bar=False,
        reset_num_timesteps=remise_a_zero,
    )
    chemin = dossier / "modele"
    modele.save(chemin)
    sauvegarder_json(
        creer_metadonnees(
            algorithme=algorithme, seed=seed,
            configuration={
                **configuration,
                "execution": {
                    "total_timesteps": nombre_pas,
                    "modele_initial": str(modele_initial) if modele_initial else None,
                },
            },
        ),
        dossier / "metadata.json",
    )
    environnement.close()
    return chemin.with_suffix(".zip")


def charger_modele(algorithme: str = "dqn", chemin: str | Path = "", environnement=None):
    if algorithme.lower() != "dqn":
        raise ValueError("L'algorithme de ce projet est 'dqn'")
    return DQN.load(str(chemin), env=environnement)
