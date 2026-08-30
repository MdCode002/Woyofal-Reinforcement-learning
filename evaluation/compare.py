"""Comparaison équitable des six politiques sur les mêmes épisodes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from env import EnvironnementMultiScenario, creer_environnement

from .baselines import creer_baselines
from .runner import evaluer_politique, resumer_evaluation


def comparer(
    *,
    seeds: list[int],
    modeles: dict[str, object] | None = None,
    dossier_sortie: str | Path = "results/evaluations/comparaison",
    taux_adoption: list[float] | None = None,
    ablation: str = "aucune",
    partition: str = "test",
    inclure_baselines: bool = True,
) -> pd.DataFrame:
    if partition not in {"validation", "test"}:
        raise ValueError("partition doit valoir validation ou test")
    politiques = creer_baselines() if inclure_baselines else {}
    politiques.update(modeles or {})
    if not politiques:
        raise ValueError("Aucune politique à évaluer")
    tables = []
    dossier = Path(dossier_sortie)
    dossier_scenarios = Path("data/generated_variable") / partition
    scenarios_test = (
        sorted(dossier_scenarios.glob("scenario_*.json"))
        if dossier_scenarios.exists() else []
    )
    for adoption in (taux_adoption or [1.0, 0.75, 0.5]):
        tables_par_strategie: dict[str, list[pd.DataFrame]] = {
            nom: [] for nom in politiques
        }
        chemins = scenarios_test or [None]
        # Scénario d'abord : toutes les politiques réutilisent immédiatement
        # les mêmes réalisations RAMP pour chaque seed, sans faux doublons.
        for chemin in chemins:
            for nom, politique in politiques.items():
                if chemin is not None:
                    fabrique = lambda chemin=chemin, adoption=adoption: EnvironnementMultiScenario(
                        [chemin], taux_adoption=adoption, ablation=ablation,
                    )
                    identifiant = chemin.stem
                else:
                    fabrique = creer_environnement
                    identifiant = "fixture-standard-dakar"
                table, _ = evaluer_politique(
                    politique=politique,
                    fabrique_environnement=fabrique,
                    nom_strategie=nom,
                    seeds=seeds,
                    contexte={
                        "partition": f"{partition}_gelee" if chemin is not None else "fixture",
                        "scenario": identifiant,
                        "taux_adoption": adoption,
                        "ablation": ablation,
                    },
                )
                tables_par_strategie[nom].append(table)
        for nom, tables_strategie in tables_par_strategie.items():
            table_complete = pd.concat(tables_strategie, ignore_index=True)
            sortie_strategie = dossier / f"adoption_{adoption:.2f}" / nom
            sortie_strategie.mkdir(parents=True, exist_ok=True)
            table_complete.to_csv(sortie_strategie / "episodes.csv", index=False)
            tables.append(table_complete)
    resultats = pd.concat(tables, ignore_index=True)
    dossier.mkdir(parents=True, exist_ok=True)
    resultats.to_csv(dossier / "tous_episodes.csv", index=False)
    resumer_evaluation(resultats).to_csv(dossier / "tableau_comparatif.csv", index=False)
    return resultats
