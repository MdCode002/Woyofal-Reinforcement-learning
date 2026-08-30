"""Génération reproductible des scénarios train/validation/test."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random
from typing import Iterable

from common import (
    HistoriqueCompteur, ParametresThermiques, Piece, ProfilOccupation, Scenario,
)

from .catalogue import charger_catalogue, construire_appareil
from .generator import generer_profils_ramp

PROFILS_LISIBLES: dict[str, tuple[str, ...]] = {
    "modeste": ("eclairage_led", "television", "petits_appareils", "ventilateur"),
    "standard": ("eclairage_led", "television", "refrigerateur", "petits_appareils", "ventilateur", "fer", "pompe_eau"),
    "confort_climatise": ("eclairage_led", "television", "refrigerateur", "congelateur", "petits_appareils", "ventilateur", "fer", "lave_linge", "climatiseur"),
}

SPECIFICATIONS_PARTITIONS = {
    "train": (200, tuple(range(2018, 2024)), True, 10_000),
    "validation": (40, (2024,), False, 20_000),
    "test": (60, (2025,), False, 30_000),
}


def _thermique(rng: random.Random) -> ParametresThermiques:
    for _ in range(100):
        resistance = rng.uniform(3.0, 10.0)
        capacite = rng.uniform(0.2, 0.4)
        if 1.0 <= resistance * capacite <= 4.0:
            return ParametresThermiques(
                resistance_c_par_kw=round(resistance, 4),
                capacite_kwh_par_c=round(capacite, 4),
                cop_climatisation=round(rng.uniform(2.6, 3.8), 3),
                gains_internes_kw=round(rng.uniform(0.08, 0.25), 3),
                coefficient_gains_solaires=round(rng.uniform(0.0003, 0.0012), 6),
            )
    raise RuntimeError("Impossible de tirer des paramètres thermiques plausibles")


def _inventaire(rng: random.Random, *, entrainement: bool, index: int):
    catalogue = charger_catalogue()
    obligatoires = {"eclairage_led", "petits_appareils"}
    choisis = set(obligatoires)
    for cle, donnees in catalogue.items():
        if cle in obligatoires:
            continue
        probabilite = float(donnees.get("taux_possession", 0.0))
        if cle == "climatiseur" and entrainement:
            probabilite = 0.45
        if rng.random() < probabilite:
            choisis.add(cle)
    # Les stress tests garantissent l'exposition à certaines situations rares.
    if index % 20 == 0:
        choisis.update({"climatiseur", "lave_linge"})
    return tuple(construire_appareil(cle) for cle in sorted(choisis))


def _pieces(
    rng: random.Random,
    inventaire,
    *,
    entrainement: bool,
    index: int,
) -> tuple[Piece, ...]:
    """Génère une à huit zones, sans chambre principale ni priorité implicite."""

    clim_disponible = any("clim" in appareil.nom.casefold() for appareil in inventaire)
    ventilateur_disponible = any("ventil" in appareil.nom.casefold() for appareil in inventaire)
    poids_nombre = (
        (0.08, 0.16, 0.22, 0.20, 0.14, 0.10, 0.06, 0.04)
        if entrainement
        else (0.10, 0.20, 0.25, 0.20, 0.12, 0.07, 0.04, 0.02)
    )
    nombre = rng.choices(tuple(range(1, 9)), weights=poids_nombre, k=1)[0]
    nombre_clims = 0
    if clim_disponible:
        maximum = nombre if entrainement and index % 20 == 0 else max(1, round(nombre * 0.6))
        nombre_clims = rng.randint(1, maximum)
    nombre_ventilateurs = 0
    if ventilateur_disponible:
        nombre_ventilateurs = rng.randint(1, nombre)
    types = ["chambre"] * nombre
    if nombre == 1:
        types[0] = rng.choices(("chambre", "salon"), weights=(0.75, 0.25), k=1)[0]
    elif rng.random() < 0.85:
        types[rng.randrange(nombre)] = "salon"
    if nombre >= 4 and rng.random() < 0.35:
        candidats = [i for i, type_piece in enumerate(types) if type_piece == "chambre"]
        types[rng.choice(candidats)] = "autre"
    indices_climatisation = set(rng.sample(range(nombre), k=nombre_clims))
    indices_ventilateur = set(rng.sample(range(nombre), k=nombre_ventilateurs))
    numero_chambre = 0
    numero_autre = 0
    pieces = []
    for numero, type_piece in enumerate(types):
        if type_piece == "salon":
            nom = "Salon"
            taille = "grande"
            profil = rng.choices(
                (ProfilOccupation.SOIREE, ProfilOccupation.VARIABLE, ProfilOccupation.JOURNEE),
                weights=(0.60, 0.30, 0.10), k=1,
            )[0]
        elif type_piece == "autre":
            numero_autre += 1
            nom = f"Pièce polyvalente {numero_autre}"
            taille = rng.choice(("petite", "moyenne"))
            profil = rng.choice((ProfilOccupation.VARIABLE, ProfilOccupation.JOURNEE))
        else:
            numero_chambre += 1
            nom = f"Chambre {numero_chambre}"
            taille = rng.choice(("petite", "moyenne", "moyenne", "grande"))
            profil = rng.choices(
                (
                    ProfilOccupation.NUIT, ProfilOccupation.VARIABLE,
                    ProfilOccupation.TOUJOURS, ProfilOccupation.JOURNEE,
                ),
                weights=(0.75, 0.15, 0.05, 0.05), k=1,
            )[0]
        climatisation = numero in indices_climatisation
        ventilateur = numero in indices_ventilateur
        pieces.append(Piece(
            nom=nom,
            type_piece=type_piece,
            taille=taille,
            climatisation=climatisation,
            ventilateur=ventilateur,
            # Une partie des foyers connaît la puissance, les autres utilisent
            # automatiquement la valeur déduite de la taille de la pièce.
            puissance_climatisation_w=(
                float(rng.choice((900, 1_200, 1_500, 1_800)))
                if climatisation and rng.random() < 0.55 else None
            ),
            puissance_ventilateur_w=(
                float(rng.choice((45, 55, 65, 75)))
                if ventilateur and rng.random() < 0.55 else None
            ),
            profil_occupation=profil,
        ))
    return tuple(pieces)


def _charge_journaliere_calibree(scenario: Scenario) -> float:
    """Estime la demande journalière à partir du vrai adaptateur RAMP.

    Le crédit n'est ainsi plus tiré indépendamment des appareils. Une petite
    enveloppe de confort est ajoutée pour que les décisions clim/ventilateur
    aient un effet réel sans rendre tous les scénarios trivialement faciles.
    """

    jours = 7
    profils = generer_profils_ramp(
        scenario,
        nombre_jours=jours,
        seed=(scenario.seed + 7_919) % (2**32 - 1),
    )
    energie_ramp = sum(
        pas.energie_non_pilotable_kwh + sum(pas.charges_decalables_kwh.values())
        for pas in profils
    ) / jours
    enveloppe_ventilateur = sum(
        piece.puissance_ventilateur_effective_w / 1000.0 * 6.0
        for piece in scenario.pieces
    )
    enveloppe_climatisation = sum(
        piece.puissance_climatisation_effective_w / 1000.0 * 2.0
        for piece in scenario.pieces
    )
    return max(0.1, energie_ramp + enveloppe_ventilateur + enveloppe_climatisation)


def _facteur_credit(rng: random.Random, index: int) -> float:
    """Mélange documenté de cas impossibles, serrés et confortables."""

    if index % 15 == 0:
        return rng.uniform(0.45, 0.65)
    tirage = rng.random()
    if tirage < 0.10:
        return rng.uniform(0.82, 0.95)
    if tirage < 0.75:
        return rng.uniform(1.05, 1.25)
    return rng.uniform(1.30, 1.55)


def generer_scenario(
    *,
    partition: str,
    index: int,
    seed: int,
    annee: int,
    entrainement: bool,
) -> Scenario:
    rng = random.Random(seed)
    debut_annee = datetime(annee, 1, 1, tzinfo=timezone.utc)
    date_debut = debut_annee + timedelta(days=rng.randrange(0, 330))
    a_date_cible = rng.random() < 0.80
    jours_cible = rng.randint(7, 21)
    date_cible = date_debut + timedelta(days=jours_cible) if a_date_cible else None
    inventaire = _inventaire(rng, entrainement=entrainement, index=index)
    pieces = _pieces(rng, inventaire, entrainement=entrainement, index=index)
    appareils = tuple(a for a in inventaire if not a.controle_par_environnement)
    thermique = _thermique(rng)
    if not any(piece.climatisation for piece in pieces):
        thermique = replace(thermique, puissance_climatisation_electrique_kw=0.0)
    taux_adoption = round(rng.uniform(0.65, 1.0), 2) if entrainement else 1.0
    scenario_provisoire = Scenario(
        identifiant_foyer=f"{partition}-{index:03d}",
        nombre_occupants=rng.randint(1, 9),
        credit_initial_kwh=1.0,
        date_debut=date_debut,
        date_cible=date_cible,
        horizon_max_minutes=30 * 24 * 60,
        appareils=appareils,
        pieces=pieces,
        parametres_thermiques=thermique,
        taux_adoption=taux_adoption,
        seed=seed,
    )
    charge_journaliere = _charge_journaliere_calibree(scenario_provisoire)
    if date_cible is not None:
        jours_budget = jours_cible
        facteur_credit = _facteur_credit(rng, index)
    else:
        jours_budget = rng.uniform(4.0, 25.0)
        facteur_credit = rng.uniform(0.95, 1.25)
    historique = HistoriqueCompteur(
        consommation_mois_precedent_kwh=round(
            charge_journaliere * 30 * rng.uniform(0.85, 1.15), 2
        ),
        consommation_mois_courant_kwh=round(
            charge_journaliere * rng.uniform(1, 20), 2
        ),
        consommation_veille_kwh=round(
            charge_journaliere * rng.uniform(0.75, 1.25), 2
        ),
    )
    return replace(
        scenario_provisoire,
        credit_initial_kwh=round(charge_journaliere * jours_budget * facteur_credit, 3),
        historique_compteur=historique,
    )


def _serialiser(objet):
    if isinstance(objet, (datetime,)):
        return objet.isoformat()
    if hasattr(objet, "isoformat"):
        return objet.isoformat()
    if isinstance(objet, tuple):
        return list(objet)
    raise TypeError(type(objet).__name__)


def ecrire_scenario(scenario: Scenario, chemin: str | Path) -> Path:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(asdict(scenario), default=_serialiser, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return chemin


def _manifeste_sha256(fichiers: Iterable[Path], destination: Path) -> None:
    lignes = []
    for fichier in sorted(fichiers):
        empreinte = hashlib.sha256(fichier.read_bytes()).hexdigest()
        lignes.append(f"{empreinte}  {fichier.name}")
    destination.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def generer_partition_scenarios(
    destination: str | Path,
    partition: str,
    seed_maitre: int = 20260823,
) -> int:
    """Régénère une partition sans toucher aux deux autres."""

    if partition not in SPECIFICATIONS_PARTITIONS:
        raise ValueError(f"Partition inconnue : {partition}")
    destination = Path(destination)
    nombre, annees, entrainement, offset = SPECIFICATIONS_PARTITIONS[partition]
    dossier = destination / partition
    dossier.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for index in range(nombre):
        seed = seed_maitre + offset + index
        scenario = generer_scenario(
            partition=partition,
            index=index,
            seed=seed,
            annee=annees[index % len(annees)],
            entrainement=entrainement,
        )
        fichiers.append(ecrire_scenario(scenario, dossier / f"scenario_{index:03d}.json"))
    if partition == "test":
        _manifeste_sha256(fichiers, dossier / "manifest.sha256")
    return nombre


def generer_jeux_scenarios(destination: str | Path, seed_maitre: int = 20260823) -> dict[str, int]:
    """Écrit 200/40/60 scénarios, avec années et seeds strictement séparées."""

    compteurs: dict[str, int] = {}
    for partition in SPECIFICATIONS_PARTITIONS:
        compteurs[partition] = generer_partition_scenarios(
            destination, partition, seed_maitre,
        )
    return compteurs


def generer_profils_lisibles(destination: str | Path) -> list[Path]:
    destination = Path(destination)
    fichiers = []
    for index, (nom, inventaire) in enumerate(PROFILS_LISIBLES.items()):
        scenario = generer_scenario(
            partition=nom, index=index + 1, seed=9000 + index,
            annee=2025, entrainement=False,
        )
        inventaire_complet = tuple(construire_appareil(cle) for cle in inventaire)
        appareils = tuple(a for a in inventaire_complet if not a.controle_par_environnement)
        pieces = _pieces(
            random.Random(12_000 + index), inventaire_complet,
            entrainement=False, index=index,
        )
        thermique = scenario.parametres_thermiques
        if "climatiseur" not in inventaire:
            thermique = replace(thermique, puissance_climatisation_electrique_kw=0.0)
        scenario = replace(
            scenario, appareils=appareils, pieces=pieces,
            parametres_thermiques=thermique,
        )
        fichiers.append(ecrire_scenario(scenario, destination / f"{nom}.json"))
    return fichiers
