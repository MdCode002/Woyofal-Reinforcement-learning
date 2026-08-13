"""Contrats de données communs définis par M1 pour le Sprint 0."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
import json
from pathlib import Path
from typing import Any

from .units import PAS_DECISION_MINUTES


@dataclass(frozen=True)
class FenetreUsage:
    """Période probable d'utilisation, et non horaire certain d'allumage."""

    heure_debut: time
    heure_fin: time
    probabilite_utilisation: float
    duree_moyenne_minutes: int
    variabilite_minutes: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.probabilite_utilisation <= 1:
            raise ValueError("probabilite_utilisation doit être comprise entre 0 et 1")
        if self.duree_moyenne_minutes <= 0:
            raise ValueError("duree_moyenne_minutes doit être strictement positive")
        if self.variabilite_minutes < 0:
            raise ValueError("variabilite_minutes doit être positive ou nulle")


@dataclass(frozen=True)
class Appareil:
    """Description minimale d'un appareil déclaré dans un scénario."""

    nom: str
    puissance_w: float
    flexible: bool
    decalage_autorise: bool
    essentiel: bool
    fenetres_usage: tuple[FenetreUsage, ...]

    def __post_init__(self) -> None:
        if not self.nom:
            raise ValueError("Le nom de l'appareil est obligatoire")
        if self.puissance_w < 0:
            raise ValueError("puissance_w doit être positive ou nulle")
        if self.decalage_autorise and not self.flexible:
            raise ValueError("Un appareil décalable doit aussi être flexible")
        if not self.fenetres_usage:
            raise ValueError("Au moins une fenêtre d'usage probable est obligatoire")


@dataclass(frozen=True)
class Scenario:
    """Configuration commune fournie au simulateur au début d'un épisode."""

    identifiant_foyer: str
    nombre_occupants: int
    credit_initial_kwh: float
    date_debut: datetime
    date_cible: datetime
    pas_minutes: int
    appareils: tuple[Appareil, ...]
    temperature_interieure_initiale_c: float | None
    source_temperature_interieure: str
    temperature_exterieure_initiale_c: float
    humidite_initiale_pourcent: float
    source_meteo: str
    occupation_initiale: bool

    def __post_init__(self) -> None:
        if not self.identifiant_foyer:
            raise ValueError("identifiant_foyer est obligatoire")
        if self.nombre_occupants <= 0:
            raise ValueError("nombre_occupants doit être strictement positif")
        if self.credit_initial_kwh < 0:
            raise ValueError("credit_initial_kwh doit être positif ou nul")
        if self.date_cible <= self.date_debut:
            raise ValueError("date_cible doit être postérieure à date_debut")
        if self.pas_minutes != PAS_DECISION_MINUTES:
            raise ValueError(
                f"Le pas commun doit rester fixé à {PAS_DECISION_MINUTES} minutes"
            )
        sources_temperature = {"mesuree", "estimee", "non_disponible"}
        if self.source_temperature_interieure not in sources_temperature:
            raise ValueError(
                "source_temperature_interieure doit valoir 'mesuree', "
                "'estimee' ou 'non_disponible'"
            )
        if (
            self.temperature_interieure_initiale_c is None
            and self.source_temperature_interieure != "non_disponible"
        ):
            raise ValueError("Une température absente doit être marquée non_disponible")
        if (
            self.temperature_interieure_initiale_c is not None
            and self.source_temperature_interieure == "non_disponible"
        ):
            raise ValueError("Une température fournie doit être mesurée ou estimée")
        if not 0 <= self.humidite_initiale_pourcent <= 100:
            raise ValueError("humidite_initiale_pourcent doit être compris entre 0 et 100")
        if not self.source_meteo:
            raise ValueError("La source de la météo doit être documentée")
        if not self.appareils:
            raise ValueError("Le scénario doit contenir au moins un appareil")


@dataclass(frozen=True)
class Observation:
    """Informations que l'environnement rend visibles à l'agent RL."""

    credit_restant_kwh: float
    heure: float
    jour_semaine: int
    temps_avant_date_cible_minutes: int
    temperature_interieure_c: float
    temperature_exterieure_c: float
    humidite_pourcent: float
    occupation: bool
    consommation_cumulee_kwh: float
    rythme_actuel_kwh_par_jour: float
    historique_consommation_kwh: tuple[float, ...] = ()
    etat_appareils: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportCharge:
    """Description précise d'une recommandation de report."""

    appareil: str
    report_minutes: int

    def __post_init__(self) -> None:
        if not self.appareil:
            raise ValueError("L'appareil à reporter est obligatoire")
        if self.report_minutes <= 0:
            raise ValueError("report_minutes doit être strictement positif")
        if self.report_minutes % PAS_DECISION_MINUTES != 0:
            raise ValueError("Le report doit être un multiple du pas de 30 minutes")


@dataclass(frozen=True)
class Action:
    """Recommandation MVP envoyée par l'agent à l'environnement."""

    climatisation_active: bool
    ventilateur_actif: bool
    report_charge: ReportCharge | None = None


@dataclass(frozen=True)
class StepResult:
    """Résultat commun retourné après une décision de l'agent."""

    nouvelle_observation: Observation
    consommation_kwh: float
    recompense: float
    termine: bool
    tronque: bool
    informations: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfilChargePas:
    """Format imposé à la future sortie RAMP de M2, agrégée à 30 minutes."""

    horodatage: datetime
    pas_minutes: int
    puissance_par_appareil_w: dict[str, float]
    energie_par_appareil_kwh: dict[str, float]
    energie_non_thermique_totale_kwh: float


@dataclass(frozen=True)
class Metriques:
    """Métriques identiques pour les baselines, DQN et PPO."""

    consommation_kwh: float
    credit_restant_kwh: float
    temperature_interieure_c: float
    inconfort: float
    nombre_coupures: int
    duree_restante_minutes: int
    date_cible_atteinte: bool


def _lire_date(value: str) -> datetime:
    date = datetime.fromisoformat(value)
    if date.tzinfo is None:
        raise ValueError("Les dates ISO 8601 doivent contenir un fuseau horaire")
    return date


def _lire_heure(value: str) -> time:
    return time.fromisoformat(value)


def charger_scenario(chemin: str | Path) -> Scenario:
    """Charge le scénario JSON commun et valide uniquement son contrat."""

    contenu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    appareils = []
    for donnees_appareil in contenu.pop("appareils"):
        fenetres = []
        for donnees_fenetre in donnees_appareil.pop("fenetres_usage"):
            heure_debut = _lire_heure(donnees_fenetre.pop("heure_debut"))
            heure_fin = _lire_heure(donnees_fenetre.pop("heure_fin"))
            fenetres.append(
                FenetreUsage(
                    **donnees_fenetre,
                    heure_debut=heure_debut,
                    heure_fin=heure_fin,
                )
            )
        appareils.append(Appareil(**donnees_appareil, fenetres_usage=tuple(fenetres)))

    date_debut = _lire_date(contenu.pop("date_debut"))
    date_cible = _lire_date(contenu.pop("date_cible"))
    return Scenario(
        **contenu,
        appareils=tuple(appareils),
        date_debut=date_debut,
        date_cible=date_cible,
    )
