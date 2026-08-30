"""Lecture du catalogue d'appareils et conversion vers les contrats communs."""

from __future__ import annotations

from datetime import time
import json
from pathlib import Path
from typing import Any

from common import Appareil, FenetreUsage

CATALOGUE_DEFAUT = Path(__file__).resolve().parents[1] / "config" / "catalogue_appareils.json"


def charger_catalogue(chemin: str | Path = CATALOGUE_DEFAUT) -> dict[str, dict[str, Any]]:
    """Retourne les entrées brutes du catalogue versionné."""

    contenu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if "appareils" not in contenu:
        raise ValueError("Le catalogue doit contenir la clé 'appareils'")
    return contenu["appareils"]


def construire_appareil(
    cle: str,
    *,
    quantite: int | None = None,
    puissance_w: float | None = None,
) -> Appareil:
    """Construit un :class:`Appareil` validé à partir d'une clé du catalogue."""

    catalogue = charger_catalogue()
    if cle not in catalogue:
        raise KeyError(f"Appareil inconnu : {cle}")
    source = dict(catalogue[cle])
    source.pop("taux_possession", None)
    fenetres = tuple(
        FenetreUsage(
            heure_debut=time.fromisoformat(item["heure_debut"]),
            heure_fin=time.fromisoformat(item["heure_fin"]),
            probabilite_utilisation=float(item["probabilite_utilisation"]),
            duree_moyenne_minutes=int(item["duree_moyenne_minutes"]),
            variabilite_minutes=int(item.get("variabilite_minutes", 0)),
        )
        for item in source.pop("fenetres_usage")
    )
    if quantite is not None:
        source["quantite"] = quantite
    if puissance_w is not None:
        source["puissance_w"] = puissance_w
    return Appareil(**source, fenetres_usage=fenetres)
