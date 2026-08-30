"""Sélection lexicographique et différences appariées entre politiques."""

from __future__ import annotations

import numpy as np
import pandas as pd


def classement_lexicographique(episodes: pd.DataFrame) -> pd.DataFrame:
    """Classe sans utiliser la récompense d'entraînement comme conclusion."""

    lignes = []
    for strategie, donnees in episodes.groupby("strategie"):
        avec_cible = donnees
        if "date_cible_fournie" in donnees:
            avec_cible = donnees[donnees["date_cible_fournie"].astype(bool)]
        lignes.append({
            "strategie": strategie,
            "taux_reussite": float(avec_cible["date_cible_atteinte"].mean()),
            "taux_coupure": float(donnees["coupure"].mean()),
            "inconfort": float(donnees["inconfort_degre_heures"].mean()),
            "energie": float(donnees["energie_servie_kwh"].mean()),
            "changements": float(donnees["nombre_changements"].mean()),
        })
    groupe = pd.DataFrame(lignes)
    return groupe.sort_values(
        ["taux_reussite", "taux_coupure", "inconfort", "energie", "changements"],
        ascending=[False, True, True, True, True],
        kind="stable",
    ).reset_index(drop=True)


def differences_appariees(
    episodes: pd.DataFrame,
    *,
    reference: str = "economie_maximale",
    metrique: str = "date_cible_atteinte",
) -> pd.DataFrame:
    """IC95 des différences sur les mêmes scénario/seed/adoption."""

    if metrique == "date_cible_atteinte" and "date_cible_fournie" in episodes:
        episodes = episodes[episodes["date_cible_fournie"].astype(bool)]
    index = [
        col for col in ("scenario_id", "seed", "taux_adoption", "ablation")
        if col in episodes.columns
    ]
    pivot = episodes.pivot_table(index=index, columns="strategie", values=metrique, aggfunc="mean")
    if reference not in pivot:
        raise ValueError(f"Référence absente : {reference}")
    lignes = []
    for strategie in pivot.columns:
        if strategie == reference:
            continue
        differences = (pivot[strategie] - pivot[reference]).dropna().astype(float)
        moyenne = float(differences.mean())
        ecart = float(differences.std(ddof=1)) if len(differences) > 1 else 0.0
        demi = 1.96 * ecart / np.sqrt(max(len(differences), 1))
        lignes.append({
            "strategie": strategie, "reference": reference, "metrique": metrique,
            "n_paires": len(differences), "difference_moyenne": moyenne,
            "ic95_bas": moyenne - demi, "ic95_haut": moyenne + demi,
        })
    return pd.DataFrame(lignes)
