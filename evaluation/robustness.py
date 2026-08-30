"""Ablations et taux d'adoption sur le pipeline d'évaluation commun."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from env import EnvironnementMultiScenario

from .baselines import PolitiqueEconomieMaximale
from .compare import comparer
from .runner import evaluer_politique


def evaluer_robustesse(
    *,
    modeles: dict[str, object] | None,
    seeds: list[int],
    dossier_sortie: str | Path = "results/evaluations/robustesse",
) -> pd.DataFrame:
    tables = []
    for ablation in (
        "aucune", "sans_historique", "sans_credit_observable",
        "sans_inertie", "sans_randomisation",
    ):
        tables.append(comparer(
            seeds=seeds,
            modeles=modeles,
            dossier_sortie=Path(dossier_sortie) / ablation,
            ablation=ablation,
        ))
    resultat = pd.concat(tables, ignore_index=True)
    Path(dossier_sortie).mkdir(parents=True, exist_ok=True)
    resultat.to_csv(Path(dossier_sortie) / "tous_episodes.csv", index=False)
    return resultat


def evaluer_ablations_ciblees(
    *,
    politique_rl,
    nom_rl: str,
    seeds: list[int],
    dossier_sortie: str | Path = "results/evaluations/ablations",
    ablations: tuple[str, ...] = (
        "aucune", "sans_historique", "sans_credit_observable",
        "sans_inertie", "sans_randomisation",
    ),
) -> pd.DataFrame:
    """Isole l'effet de chaque ablation à adoption 100 %, RL contre borne économe."""

    chemins = sorted(Path("data/generated_variable/test").glob("scenario_*.json"))
    politiques = {"economie_maximale": PolitiqueEconomieMaximale(), nom_rl: politique_rl}
    tables = []
    for ablation in ablations:
        for nom, politique in politiques.items():
            for chemin in chemins:
                table, _ = evaluer_politique(
                    politique=politique,
                    fabrique_environnement=lambda chemin=chemin, ablation=ablation: EnvironnementMultiScenario(
                        [chemin], taux_adoption=1.0, ablation=ablation,
                    ),
                    nom_strategie=nom,
                    seeds=seeds,
                    contexte={
                        "scenario": chemin.stem,
                        "taux_adoption": 1.0,
                        "ablation": ablation,
                        "partition": "test_gelee_analyse_sensibilite",
                    },
                )
                tables.append(table)
    resultat = pd.concat(tables, ignore_index=True)
    destination = Path(dossier_sortie)
    destination.mkdir(parents=True, exist_ok=True)
    resultat.to_csv(destination / "episodes.csv", index=False)
    return resultat
