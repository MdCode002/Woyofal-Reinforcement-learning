"""Tables finales publiables à partir des épisodes gelés."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .plots import tracer_comparaison
from .runner import resumer_evaluation
from .selection import classement_lexicographique, differences_appariees


def produire_rapport_resultats(
    episodes: str | Path = "results/evaluations/test_final/tous_episodes.csv",
    dossier_sortie: str | Path = "results/evaluations/test_final",
) -> dict[str, Path]:
    table = pd.read_csv(episodes)
    dossier = Path(dossier_sortie)
    dossier.mkdir(parents=True, exist_ok=True)
    chemins = {
        "resume": dossier / "resume_par_adoption.csv",
        "classement": dossier / "classement_global.csv",
        "paires_reussite": dossier / "differences_appariees_reussite.csv",
        "paires_coupure": dossier / "differences_appariees_coupure.csv",
        "figure": dossier / "comparaison.png",
    }
    resumer_evaluation(table).to_csv(chemins["resume"], index=False)
    classement_lexicographique(table).to_csv(chemins["classement"], index=False)
    differences_appariees(table, reference="economie_maximale", metrique="date_cible_atteinte").to_csv(
        chemins["paires_reussite"], index=False
    )
    differences_appariees(table, reference="economie_maximale", metrique="coupure").to_csv(
        chemins["paires_coupure"], index=False
    )
    tracer_comparaison(table, chemins["figure"])
    return chemins
