"""Graphiques issus uniquement des métriques finales."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def tracer_trajectoire(table: pd.DataFrame, chemin: str | Path) -> Path:
    if table.empty:
        raise ValueError("La trajectoire est vide")
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(table["pas"], table["energie_servie_pas_kwh"])
    axes[0].set_ylabel("kWh servis / pas")
    axes[1].plot(table["pas"], table["credit_restant_kwh"])
    axes[1].set_ylabel("Crédit (kWh)")
    axes[2].plot(table["pas"], table["temperature_interieure_c"])
    axes[2].set_ylabel("T intérieure (°C)")
    axes[2].set_xlabel("Pas de 30 minutes")
    figure.tight_layout()
    figure.savefig(chemin, dpi=160)
    plt.close(figure)
    return chemin


def tracer_comparaison(table: pd.DataFrame, chemin: str | Path) -> Path:
    resume = table.groupby("strategie").agg(
        energie=("energie_servie_kwh", "mean"),
        inconfort=("inconfort_degre_heures", "mean"),
        coupure=("coupure", "mean"),
    )
    avec_cible = table
    if "date_cible_fournie" in table:
        avec_cible = table[table["date_cible_fournie"].astype(bool)]
    resume["reussite"] = avec_cible.groupby("strategie")["date_cible_atteinte"].mean()
    resume = resume.rename(index={
        "gloutonne_ventilateur_avant_clim": "gloutonne",
        "horaires_fixes": "horaires",
        "tout_allume": "tout allumé",
    })
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    axes = resume.plot(kind="bar", subplots=True, figsize=(11, 9), legend=False)
    axes[-1].set_xlabel("Stratégie")
    plt.tight_layout()
    plt.savefig(chemin, dpi=160)
    plt.close()
    return chemin
