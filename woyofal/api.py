"""API FastAPI locale : aucune opération d'entraînement."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from common import charger_scenario
from ramp_adapter.catalogue import charger_catalogue

from . import __version__
from .intake import scenario_depuis_saisie
from .service import SCENARIO_DEFAUT, prevoir, recommander

app = FastAPI(title="Woyofal", version=__version__)
origines = [
    origine.strip()
    for origine in os.getenv(
        "WOYOFAL_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origine.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origines,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ModeleAPI(BaseModel):
    """Refuse les champs inconnus pour éviter un fallback silencieux."""

    model_config = ConfigDict(extra="forbid")


class PieceSaisie(ModeleAPI):
    nom: str
    type_piece: str = Field(default="chambre", pattern="^(chambre|salon|autre)$")
    taille: str = Field(default="moyenne", pattern="^(petite|moyenne|grande)$")
    climatisation: bool = False
    ventilateur: bool = False
    nombre_climatiseurs: int | None = Field(default=None, ge=0, le=4)
    nombre_ventilateurs: int | None = Field(default=None, ge=0, le=8)
    puissance_climatisation_w: float | None = Field(default=None, gt=0)
    puissance_ventilateur_w: float | None = Field(default=None, gt=0)
    profil_occupation: str | None = Field(
        default=None,
        pattern="^(nuit|soiree|journee|variable|toujours)$",
    )
    occupation_actuelle: bool | None = None


class AppareilSaisie(ModeleAPI):
    type_appareil: str
    quantite: int = Field(default=1, ge=1, le=30)
    puissance_w: float | None = Field(default=None, gt=0, le=20_000)


class FoyerSaisie(ModeleAPI):
    identifiant_foyer: str = "foyer-utilisateur"
    nombre_occupants: int = Field(ge=1, le=20)
    credit_initial_kwh: float = Field(ge=0)
    date_debut: datetime | None = None
    date_cible: datetime | None = None
    pieces: list[PieceSaisie] = Field(min_length=1, max_length=50)
    appareils: list[str | AppareilSaisie] = Field(default_factory=list, max_length=30)
    historique_compteur: dict[str, float | None] = Field(default_factory=dict)
    source_meteo: str = Field(
        default="auto_dakar",
        pattern="^(auto_dakar|cache_open_meteo_era5|fixture_deterministe)$",
    )
    taux_adoption: float = Field(default=1.0, ge=0, le=1)
    seed: int = 42


class RequeteScenario(ModeleAPI):
    scenario: str | None = str(SCENARIO_DEFAUT)
    foyer: FoyerSaisie | None = None
    modele: str | None = None
    algorithme: str | None = Field(default="dqn", pattern="^dqn$")


class RequetePrevision(RequeteScenario):
    simulations: int = Field(default=20, ge=3, le=200)


class RequeteRecommandation(RequeteScenario):
    horizon_heures: int = Field(default=4, ge=1, le=12)


@app.get("/health")
def health() -> dict[str, str]:
    return {"statut": "ok", "version": __version__}


@app.get("/v1/catalogue")
def catalogue() -> dict[str, Any]:
    """Expose les choix du formulaire sans dupliquer les hypothèses côté front."""

    appareils = []
    for cle, donnees in charger_catalogue().items():
        if donnees.get("controle_par_environnement"):
            continue
        appareils.append({
            "type_appareil": cle,
            "nom": donnees["nom"],
            "categorie": donnees["categorie"],
            "puissance_w_par_defaut": donnees["puissance_w"],
            "quantite_par_defaut": donnees["quantite"],
            "decalable": donnees["decalage_autorise"],
            "essentiel": donnees["essentiel"],
        })
    return {"appareils": appareils}


def _scenario(chemin: str | None, foyer: FoyerSaisie | None):
    if foyer is not None:
        try:
            return scenario_depuis_saisie(foyer.model_dump())
        except (ValueError, TypeError, KeyError) as erreur:
            raise HTTPException(status_code=422, detail=str(erreur)) from erreur
    if chemin is None:
        raise HTTPException(status_code=422, detail="Fournissez scenario ou foyer")
    path = Path(chemin)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    try:
        return charger_scenario(path)
    except (ValueError, TypeError, KeyError) as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur


def _service_rl(fonction, **arguments):
    try:
        return fonction(**arguments)
    except (FileNotFoundError, RuntimeError) as erreur:
        raise HTTPException(status_code=503, detail=str(erreur)) from erreur
    except ValueError as erreur:
        raise HTTPException(status_code=422, detail=str(erreur)) from erreur


@app.post("/v1/prevision")
def endpoint_prevision(requete: RequetePrevision):
    return _service_rl(
        prevoir,
        scenario=_scenario(requete.scenario, requete.foyer), simulations=requete.simulations,
        modele=requete.modele, algorithme=requete.algorithme,
    )


@app.post("/v1/recommandation")
def endpoint_recommandation(requete: RequeteRecommandation):
    return _service_rl(
        recommander,
        scenario=_scenario(requete.scenario, requete.foyer),
        modele=requete.modele, algorithme=requete.algorithme,
        horizon_heures=requete.horizon_heures,
    )
