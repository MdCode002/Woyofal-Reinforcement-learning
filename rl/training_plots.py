"""Courbes d'entraînement à partir des fichiers Monitor de SB3."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def tracer_monitor(chemin_monitor: str | Path, chemin_figure: str | Path) -> Path:
    """Trace récompense, longueur, énergie et inconfort par épisode."""

    table = pd.read_csv(chemin_monitor, comment="#")
    if table.empty:
        raise ValueError("Le fichier Monitor ne contient aucun épisode terminé")
    chemin_figure = Path(chemin_figure)
    chemin_figure.parent.mkdir(parents=True, exist_ok=True)
    colonnes = [
        ("r", "Récompense"),
        ("l", "Durée (pas)"),
        ("energie_servie_cumulee_kwh", "Énergie servie (kWh)"),
        ("inconfort_cumule_degre_heures", "Inconfort (°C·h)"),
    ]
    figure, axes = plt.subplots(len(colonnes), 1, figsize=(10, 10), sharex=True)
    for axe, (colonne, titre) in zip(axes, colonnes, strict=True):
        if colonne in table:
            axe.plot(table.index, table[colonne])
        axe.set_ylabel(titre)
    axes[-1].set_xlabel("Épisode")
    figure.tight_layout()
    figure.savefig(chemin_figure, dpi=160)
    plt.close(figure)
    return chemin_figure
