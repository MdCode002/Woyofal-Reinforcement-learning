"""Publication honnête de la politique à servir après le test gelé."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .selection import classement_lexicographique


def publier_decision(
    episodes: str | Path = "results/evaluations/test_final/tous_episodes.csv",
    destination: str | Path = "results/models/selection.json",
) -> Path:
    table = pd.read_csv(episodes)
    classement = classement_lexicographique(table)
    gagnant_global = str(classement.iloc[0]["strategie"])
    destination = Path(destination)
    if not destination.exists():
        raise FileNotFoundError(
            "La sélection sur validation doit être publiée avant l'ouverture du test"
        )
    contenu = json.loads(destination.read_text(encoding="utf-8"))
    algorithme = str(contenu["algorithme"])
    ligne_rl = classement[classement["strategie"] == algorithme]
    if ligne_rl.empty:
        raise ValueError(f"Le modèle sélectionné {algorithme} est absent du test")
    taux_reussite_rl = float(ligne_rl.iloc[0]["taux_reussite"])
    contenu.pop("rl_superieur", None)
    contenu.update({
        "source_politique": algorithme,
        "test": str(episodes),
        "rl_premier_classement_global": gagnant_global == algorithme,
        "taux_reussite_test": taux_reussite_rl,
        "seuil_reussite_vise": 0.70,
        "seuil_reussite_atteint": taux_reussite_rl >= 0.70,
        "meilleure_strategie_globale": gagnant_global,
    })
    if gagnant_global != algorithme:
        contenu["avertissement_test"] = (
            "Le modèle RL est publié car le produit est expérimental, mais une baseline "
            "obtient un meilleur classement global."
        )
    else:
        contenu.pop("avertissement_test", None)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
