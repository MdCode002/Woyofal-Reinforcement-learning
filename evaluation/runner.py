"""Boucle d'évaluation strictement commune aux baselines, DQN et PPO."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import gymnasium as gym
import numpy as np
import pandas as pd


def _action_scalaire(prediction: Any) -> int:
    action = prediction[0] if isinstance(prediction, tuple) else prediction
    return int(np.asarray(action).reshape(-1)[0])


def evaluer_politique(
    *,
    politique: Any,
    fabrique_environnement: Callable[[], gym.Env],
    nom_strategie: str,
    seeds: list[int],
    dossier_sortie: str | Path | None = None,
    contexte: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    contexte = dict(contexte or {})
    episodes: list[dict[str, Any]] = []
    trajectoires: list[dict[str, Any]] = []
    environnement = fabrique_environnement()
    for seed in seeds:
        observation, _ = environnement.reset(seed=seed)
        termine = tronque = False
        recompense_totale = 0.0
        pas_agent = 0
        pas_physiques = 0
        latences = []
        info: dict[str, Any] = {}
        while not (termine or tronque):
            debut = perf_counter()
            action = _action_scalaire(politique.predict(observation, deterministic=True))
            latences.append((perf_counter() - debut) * 1000)
            observation, recompense, termine, tronque, info = environnement.step(action)
            recompense_totale += float(recompense)
            if info.get("decision_physique_appliquee", True):
                trajectoires.append({
                    **contexte,
                    "strategie": nom_strategie, "seed": seed, "pas": pas_physiques,
                    "action": action, "recompense": float(recompense),
                    "credit_restant_kwh": info["credit_restant_kwh"],
                    "temperature_interieure_c": info["temperature_interieure_c"],
                    "energie_servie_pas_kwh": info["energie_servie_pas_kwh"],
                    "inconfort_pas_degre_heures": info["inconfort_pas_degre_heures"],
                })
                pas_physiques += 1
            pas_agent += 1
        episodes.append({
            **contexte,
            "strategie": nom_strategie,
            "seed": seed,
            "scenario_id": info.get("scenario", contexte.get("scenario", "fixture")),
            "recompense_totale": recompense_totale,
            "nombre_pas": pas_physiques,
            "nombre_decisions_agent": pas_agent,
            "duree_survie_heures": pas_physiques * 0.5,
            "energie_demandee_kwh": info.get("energie_demandee_cumulee_kwh", np.nan),
            "energie_servie_kwh": info.get("energie_servie_cumulee_kwh", np.nan),
            "energie_non_servie_kwh": info.get("energie_non_servie_cumulee_kwh", np.nan),
            "credit_restant_kwh": info.get("credit_restant_kwh", np.nan),
            "inconfort_degre_heures": info.get("inconfort_cumule_degre_heures", np.nan),
            "coupure": info.get("raison_fin") == "credit_epuise",
            "date_cible_atteinte": bool(info.get("date_cible_atteinte", False)),
            "date_cible_fournie": bool(info.get("date_cible_fournie", True)),
            "reports_reussis": info.get("reports_reussis", 0),
            "nombre_changements": info.get("nombre_changements", 0),
            "taux_adoption_observe": info.get("taux_adoption_observe", np.nan),
            "latence_inference_ms": float(np.mean(latences)),
            "raison_fin": info.get("raison_fin", "inconnue"),
        })
    environnement.close()
    table_episodes = pd.DataFrame(episodes)
    table_trajectoires = pd.DataFrame(trajectoires)
    if dossier_sortie is not None:
        dossier = Path(dossier_sortie)
        dossier.mkdir(parents=True, exist_ok=True)
        table_episodes.to_csv(dossier / "episodes.csv", index=False)
        table_trajectoires.to_csv(dossier / "trajectoires.csv", index=False)
        (dossier / "resume.json").write_text(
            json.dumps(resumer_evaluation(table_episodes).to_dict(orient="records"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return table_episodes, table_trajectoires


def resumer_evaluation(table: pd.DataFrame) -> pd.DataFrame:
    """Moyenne, écart-type et IC95 normal, groupés par stratégie."""

    metriques = [
        "date_cible_atteinte", "coupure", "duree_survie_heures",
        "energie_demandee_kwh", "energie_servie_kwh", "energie_non_servie_kwh",
        "credit_restant_kwh", "inconfort_degre_heures", "reports_reussis",
        "nombre_changements", "taux_adoption_observe", "latence_inference_ms",
    ]
    lignes = []
    regroupement = ["strategie"] + [
        colonne for colonne in ("taux_adoption", "ablation") if colonne in table.columns
    ]
    for cles, groupe in table.groupby(regroupement):
        if not isinstance(cles, tuple):
            cles = (cles,)
        ligne: dict[str, Any] = dict(zip(regroupement, cles, strict=True))
        ligne["n"] = len(groupe)
        if "date_cible_fournie" in groupe:
            ligne["n_dates_cibles"] = int(groupe["date_cible_fournie"].astype(bool).sum())
        for metrique in metriques:
            donnees_metrique = groupe
            if metrique == "date_cible_atteinte" and "date_cible_fournie" in groupe:
                donnees_metrique = groupe[groupe["date_cible_fournie"].astype(bool)]
            valeurs = donnees_metrique[metrique].astype(float)
            moyenne = float(valeurs.mean())
            ecart = float(valeurs.std(ddof=1)) if len(valeurs) > 1 else 0.0
            demi_ic = 1.96 * ecart / np.sqrt(max(len(valeurs), 1))
            ligne.update({
                f"{metrique}_moyenne": moyenne,
                f"{metrique}_ecart_type": ecart,
                f"{metrique}_ic95_bas": moyenne - demi_ic,
                f"{metrique}_ic95_haut": moyenne + demi_ic,
            })
        lignes.append(ligne)
    return pd.DataFrame(lignes)
