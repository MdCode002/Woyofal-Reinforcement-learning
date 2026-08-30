"""Conversion d'un formulaire court en scénario complet et validé."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from common import HistoriqueCompteur, Piece, Scenario
from ramp_adapter.catalogue import construire_appareil


APPAREILS_PAR_DEFAUT = (
    "eclairage_led", "television", "refrigerateur", "petits_appareils",
)


def _date(value: datetime | str | None, *, defaut: datetime | None = None) -> datetime | None:
    if value is None:
        return defaut
    resultat = datetime.fromisoformat(value) if isinstance(value, str) else value
    if resultat.tzinfo is None:
        raise ValueError("Les dates doivent contenir un fuseau horaire")
    return resultat


def _aligner_sur_demi_heure(date: datetime) -> datetime:
    """Ramène une lecture réelle au dernier pas de décision entièrement connu."""

    return date.replace(minute=30 if date.minute >= 30 else 0, second=0, microsecond=0)


def _construire_inventaire(donnees: list[Any]) -> tuple:
    inventaire = []
    for entree in donnees:
        if isinstance(entree, str):
            inventaire.append(construire_appareil(entree))
            continue
        if not isinstance(entree, dict):
            raise TypeError("Chaque appareil doit être un nom ou un objet détaillé")
        cle = entree.get("type_appareil") or entree.get("cle")
        if not cle:
            raise ValueError("Le type de chaque appareil est obligatoire")
        inventaire.append(construire_appareil(
            str(cle),
            quantite=int(entree.get("quantite", 1)),
            puissance_w=(
                float(entree["puissance_w"])
                if entree.get("puissance_w") is not None else None
            ),
        ))
    return tuple(inventaire)


def scenario_depuis_saisie(donnees: dict[str, Any]) -> Scenario:
    """Crée le contrat détaillé à partir des quelques champs visibles du formulaire."""

    debut_defaut = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    date_debut = _date(donnees.get("date_debut"), defaut=debut_defaut)
    date_cible = _date(donnees.get("date_cible"))
    assert date_debut is not None
    date_debut = _aligner_sur_demi_heure(date_debut)
    if date_cible is not None:
        horizon = int((date_cible - date_debut).total_seconds() / 60)
    else:
        horizon = 30 * 24 * 60
    horizon = max(30, min(horizon, 30 * 24 * 60))

    donnees_pieces = donnees.get("pieces") or [
        {"nom": "Pièce principale", "type_piece": "salon", "taille": "moyenne"}
    ]
    pieces_preparees = []
    for source_piece in donnees_pieces:
        piece = dict(source_piece)
        if piece.get("occupation_actuelle") is not None:
            piece["occupation_actuelle_jusqua"] = date_debut + timedelta(minutes=30)
        pieces_preparees.append(piece)
    pieces = tuple(Piece(**piece) for piece in pieces_preparees)
    cles_appareils = donnees.get("appareils") or list(APPAREILS_PAR_DEFAUT)
    inventaire = _construire_inventaire(cles_appareils)
    appareils = tuple(appareil for appareil in inventaire if not appareil.controle_par_environnement)
    if not appareils:
        raise ValueError("Ajoutez au moins un appareil domestique hors climatisation/ventilateur")
    historique = HistoriqueCompteur(**(donnees.get("historique_compteur") or {}))
    return Scenario(
        identifiant_foyer=str(donnees.get("identifiant_foyer", "foyer-utilisateur")),
        nombre_occupants=int(donnees["nombre_occupants"]),
        credit_initial_kwh=float(donnees["credit_initial_kwh"]),
        date_debut=date_debut,
        date_cible=date_cible,
        horizon_max_minutes=horizon,
        appareils=appareils,
        pieces=pieces,
        historique_compteur=historique,
        source_meteo=str(donnees.get("source_meteo", "fixture_deterministe")),
        taux_adoption=float(donnees.get("taux_adoption", 1.0)),
        seed=int(donnees.get("seed", 42)),
    )
