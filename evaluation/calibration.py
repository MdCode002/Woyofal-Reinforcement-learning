"""Contrôle des agrégats RAMP générés par le pipeline final."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from common import charger_scenario
from ramp_adapter import generer_profils_ramp


def analyser_scenarios(
    dossier_scenarios: str | Path = "data/generated/train",
    *,
    limite: int | None = 30,
    dossier_sortie: str | Path = "results/evaluations/calibration",
) -> pd.DataFrame:
    chemins = sorted(Path(dossier_scenarios).glob("scenario_*.json"))
    if limite is not None:
        chemins = chemins[:limite]
    lignes = []
    for chemin in chemins:
        scenario = charger_scenario(chemin)
        profils = generer_profils_ramp(scenario, nombre_jours=1)
        energie = sum(
            p.energie_non_pilotable_kwh + sum(p.charges_decalables_kwh.values())
            for p in profils
        )
        soir = profils[36:46]
        pointe = max(
            sum(p.energie_demandee_par_appareil_kwh.values()) * 2
            for p in soir
        )
        lignes.append({
            "scenario": scenario.identifiant_foyer,
            "energie_non_thermique_kwh_jour": energie,
            "projection_kwh_mois": energie * 30,
            "pointe_soir_kw": pointe,
            "climatisation_presente": any(piece.climatisation for piece in scenario.pieces),
            "nombre_pieces": len(scenario.pieces),
            "nombre_climatiseurs": sum(piece.climatisation for piece in scenario.pieces),
            "nombre_ventilateurs": sum(piece.ventilateur for piece in scenario.pieces),
        })
    table = pd.DataFrame(lignes)
    destination = Path(dossier_sortie)
    destination.mkdir(parents=True, exist_ok=True)
    table.to_csv(destination / "calibration.csv", index=False)
    return table
