"""Recherche limitée, entraînement final et sélection sur validation."""

from __future__ import annotations

from copy import deepcopy
import itertools
import json
from pathlib import Path
import shutil

import pandas as pd

from env import EnvironnementMultiScenario
from evaluation.runner import evaluer_politique
from evaluation.selection import classement_lexicographique

from .config import charger_configuration
from .train import charger_modele, entrainer


def _evaluer_validation(politique, nom: str, contexte: dict) -> pd.DataFrame:
    tables = []
    for chemin in sorted(Path("data/generated_variable/validation").glob("scenario_*.json")):
        table, _ = evaluer_politique(
            politique=politique,
            fabrique_environnement=lambda chemin=chemin: EnvironnementMultiScenario(
                [chemin], taux_adoption=1.0,
            ),
            nom_strategie=nom,
            seeds=[1101, 1102, 1103, 1104, 1105],
            contexte={**contexte, "scenario": chemin.stem},
        )
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def rechercher(
    *,
    algorithme: str,
    dossier_sortie: str | Path = "results/models/search",
    timesteps_override: int | None = None,
) -> Path:
    """Exécute exactement 2 learning rates × 2 gamma × 2 seeds."""

    configuration = charger_configuration()
    recherche = configuration["recherche"]
    dossier = Path(dossier_sortie) / algorithme
    tables = []
    for numero, (lr, gamma) in enumerate(itertools.product(
        recherche["learning_rate"], recherche["gamma"]
    )):
        for seed in recherche["seeds"]:
            variante = deepcopy(configuration)
            variante[algorithme]["learning_rate"] = lr
            variante[algorithme]["gamma"] = gamma
            chemin = entrainer(
                algorithme=algorithme, configuration=variante, seed=seed,
                total_timesteps=timesteps_override or recherche["pas_par_configuration"],
                dossier_sortie=dossier / f"config_{numero}_seed_{seed}", verbose=0,
            )
            modele = charger_modele(algorithme, chemin)
            table = _evaluer_validation(
                modele,
                f"config_{numero}_seed_{seed}",
                {"learning_rate": lr, "gamma": gamma, "modele": str(chemin)},
            )
            tables.append(table)
    episodes = pd.concat(tables, ignore_index=True)
    classement = classement_lexicographique(episodes)
    dossier.mkdir(parents=True, exist_ok=True)
    episodes.to_csv(dossier / "episodes_validation.csv", index=False)
    classement.to_csv(dossier / "classement.csv", index=False)
    gagnant = classement.iloc[0]["strategie"]
    ligne = episodes.loc[episodes["strategie"] == gagnant].iloc[0]
    selection = {
        "algorithme": algorithme,
        "strategie_validation": gagnant,
        "learning_rate": float(ligne["learning_rate"]),
        "gamma": float(ligne["gamma"]),
        "chemin": ligne["modele"],
        "critere": "lexicographique_reussite_coupure_inconfort_energie_changements",
    }
    chemin_selection = dossier / "selection.json"
    chemin_selection.write_text(json.dumps(selection, indent=2), encoding="utf-8")
    return chemin_selection


def entrainer_final(
    *,
    algorithme: str,
    selection_recherche: str | Path,
    timesteps_override: int | None = None,
) -> Path:
    """Entraîne trois seeds puis publie le meilleur modèle de validation."""

    configuration = charger_configuration()
    selection = json.loads(Path(selection_recherche).read_text(encoding="utf-8"))
    configuration[algorithme]["learning_rate"] = selection["learning_rate"]
    configuration[algorithme]["gamma"] = selection["gamma"]
    tables = []
    for seed in configuration[algorithme]["seeds_finales"]:
        chemin = entrainer(
            algorithme=algorithme, configuration=configuration, seed=int(seed),
            total_timesteps=timesteps_override,
            dossier_sortie=Path("results/models/final") / f"{algorithme}_seed_{seed}",
            verbose=0,
        )
        modele = charger_modele(algorithme, chemin)
        tables.append(_evaluer_validation(
            modele, f"{algorithme}_seed_{seed}", {"modele": str(chemin)},
        ))
    episodes = pd.concat(tables, ignore_index=True)
    classement = classement_lexicographique(episodes)
    gagnant = classement.iloc[0]["strategie"]
    ligne = episodes.loc[episodes["strategie"] == gagnant].iloc[0]
    publication = {
        "algorithme": algorithme,
        "chemin": ligne["modele"],
        "strategie_validation": gagnant,
        "critere": "lexicographique_reussite_coupure_inconfort_energie_changements",
    }
    destination = Path(f"results/models/selection_{algorithme}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(publication, indent=2), encoding="utf-8")
    episodes.to_csv(destination.parent / f"validation_finale_{algorithme}.csv", index=False)
    return destination


def selectionner_modele_final() -> Path:
    """Sélectionne le meilleur DQN sur validation et publie le modèle de production."""

    chemin = Path("results/models/validation_finale_dqn.csv")
    if not chemin.exists():
        raise FileNotFoundError("Aucune évaluation finale DQN disponible")
    episodes = pd.read_csv(chemin)
    classement = classement_lexicographique(episodes)
    strategie = classement.iloc[0]["strategie"]
    ligne = episodes.loc[episodes["strategie"] == strategie].iloc[0]
    source_modele = Path(str(ligne["modele"]))
    dossier_production = Path("results/models/production")
    dossier_production.mkdir(parents=True, exist_ok=True)
    modele_production = dossier_production / "modele.zip"
    shutil.copy2(source_modele, modele_production)
    source_metadata = source_modele.parent / "metadata.json"
    if source_metadata.exists():
        shutil.copy2(source_metadata, dossier_production / "metadata.json")
    publication = {
        "algorithme": "dqn",
        "chemin": modele_production.as_posix(),
        "strategie_validation": strategie,
        "critere": "lexicographique_reussite_coupure_inconfort_energie_changements",
        "selection_effectuee_uniquement_sur": "validation_2024",
    }
    destination = Path("results/models/selection.json")
    destination.write_text(json.dumps(publication, indent=2), encoding="utf-8")
    return destination
