"""Contrats de données uniques du projet Woyofal.

Les modules RAMP, thermique, compteur, Gymnasium, RL et API échangent
exclusivement ces structures. Les unités sont explicites dans les noms.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, time
from enum import Enum
import json
from pathlib import Path
from typing import Any

from .units import PAS_DECISION_MINUTES, SOUS_PAS_THERMIQUE_MINUTES


class ModeConfort(str, Enum):
    """Modes simples présentés au foyer et utilisables par les deux agents RL."""

    ARRET = "arret"
    VENTILATEUR = "ventilateur"
    CLIM_ECO = "clim_eco_27"
    CLIM_CONFORT = "clim_confort_25"
    CLIM_BOOST = "clim_boost_23"

    @property
    def consigne_c(self) -> float | None:
        return {
            ModeConfort.CLIM_ECO: 27.0,
            ModeConfort.CLIM_CONFORT: 25.0,
            ModeConfort.CLIM_BOOST: 23.0,
        }.get(self)


class ProfilOccupation(str, Enum):
    """Profil simple choisi par le foyer, sans demander un agenda détaillé."""

    NUIT = "nuit"
    SOIREE = "soiree"
    JOURNEE = "journee"
    VARIABLE = "variable"
    TOUJOURS = "toujours"


@dataclass(frozen=True, slots=True)
class Piece:
    """Description volontairement courte d'une zone de confort du foyer.

    La puissance est facultative : lorsqu'elle est inconnue, une estimation
    prudente est déduite de la taille déclarée. L'utilisateur n'a donc pas à
    lire obligatoirement la plaque signalétique de ses appareils.
    """

    nom: str
    type_piece: str = "chambre"
    taille: str = "moyenne"
    climatisation: bool = False
    ventilateur: bool = False
    nombre_climatiseurs: int | None = None
    nombre_ventilateurs: int | None = None
    puissance_climatisation_w: float | None = None
    puissance_ventilateur_w: float | None = None
    profil_occupation: ProfilOccupation | str | None = None
    occupation_actuelle: bool | None = None
    occupation_actuelle_jusqua: datetime | None = None

    def __post_init__(self) -> None:
        if not self.nom.strip():
            raise ValueError("Le nom de la pièce est obligatoire")
        if self.type_piece not in {"chambre", "salon", "autre"}:
            raise ValueError("type_piece doit valoir chambre, salon ou autre")
        if self.taille not in {"petite", "moyenne", "grande"}:
            raise ValueError("taille doit valoir petite, moyenne ou grande")
        for nom, valeur in (
            ("puissance_climatisation_w", self.puissance_climatisation_w),
            ("puissance_ventilateur_w", self.puissance_ventilateur_w),
        ):
            if valeur is not None and valeur <= 0:
                raise ValueError(f"{nom} doit être strictement positive")
        nombre_climatiseurs = (
            int(self.climatisation)
            if self.nombre_climatiseurs is None else self.nombre_climatiseurs
        )
        nombre_ventilateurs = (
            int(self.ventilateur)
            if self.nombre_ventilateurs is None else self.nombre_ventilateurs
        )
        if nombre_climatiseurs < 0 or nombre_ventilateurs < 0:
            raise ValueError("Les quantités de climatiseurs et ventilateurs doivent être positives")
        if nombre_climatiseurs > 4 or nombre_ventilateurs > 8:
            raise ValueError("Une pièce accepte au plus 4 climatiseurs et 8 ventilateurs")
        if self.occupation_actuelle_jusqua is not None:
            if self.occupation_actuelle is None:
                raise ValueError("occupation_actuelle doit accompagner sa durée de validité")
            if self.occupation_actuelle_jusqua.tzinfo is None:
                raise ValueError("occupation_actuelle_jusqua doit contenir un fuseau horaire")
        object.__setattr__(self, "nombre_climatiseurs", nombre_climatiseurs)
        object.__setattr__(self, "nombre_ventilateurs", nombre_ventilateurs)
        object.__setattr__(self, "climatisation", nombre_climatiseurs > 0)
        object.__setattr__(self, "ventilateur", nombre_ventilateurs > 0)
        profil = self.profil_occupation
        if profil is None:
            profil = {
                "chambre": ProfilOccupation.NUIT,
                "salon": ProfilOccupation.SOIREE,
                "autre": ProfilOccupation.VARIABLE,
            }[self.type_piece]
        object.__setattr__(self, "profil_occupation", ProfilOccupation(profil))

    @property
    def puissance_climatisation_unitaire_effective_w(self) -> float:
        if not self.climatisation:
            return 0.0
        return float(self.puissance_climatisation_w or {
            "petite": 900.0, "moyenne": 1_200.0, "grande": 1_800.0,
        }[self.taille])

    @property
    def puissance_climatisation_effective_w(self) -> float:
        """Puissance électrique totale des climatiseurs de la pièce."""

        return self.puissance_climatisation_unitaire_effective_w * int(
            self.nombre_climatiseurs or 0
        )

    @property
    def puissance_ventilateur_unitaire_effective_w(self) -> float:
        if not self.ventilateur:
            return 0.0
        return float(self.puissance_ventilateur_w or 55.0)

    @property
    def puissance_ventilateur_effective_w(self) -> float:
        """Puissance électrique totale des ventilateurs de la pièce."""

        return self.puissance_ventilateur_unitaire_effective_w * int(
            self.nombre_ventilateurs or 0
        )


@dataclass(frozen=True, slots=True)
class FenetreUsage:
    """Fenêtre probable d'utilisation, et non horaire certain d'allumage."""

    heure_debut: time
    heure_fin: time
    probabilite_utilisation: float
    duree_moyenne_minutes: int
    variabilite_minutes: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.probabilite_utilisation <= 1.0:
            raise ValueError("probabilite_utilisation doit être comprise entre 0 et 1")
        if self.duree_moyenne_minutes <= 0:
            raise ValueError("duree_moyenne_minutes doit être strictement positive")
        if self.variabilite_minutes < 0:
            raise ValueError("variabilite_minutes doit être positive ou nulle")


@dataclass(frozen=True, slots=True)
class Appareil:
    """Appareil déclaré par le foyer ou tiré dans un scénario synthétique."""

    nom: str
    categorie: str
    puissance_w: float
    quantite: int
    flexible: bool
    decalage_autorise: bool
    essentiel: bool
    controle_par_environnement: bool
    fenetres_usage: tuple[FenetreUsage, ...]
    variabilite_puissance_pourcent: float = 0.10

    def __post_init__(self) -> None:
        if not self.nom.strip() or not self.categorie.strip():
            raise ValueError("Le nom et la catégorie de l'appareil sont obligatoires")
        if self.puissance_w < 0 or self.quantite <= 0:
            raise ValueError("La puissance doit être positive et la quantité non nulle")
        if self.decalage_autorise and not self.flexible:
            raise ValueError("Un appareil décalable doit aussi être flexible")
        if not self.fenetres_usage:
            raise ValueError("Au moins une fenêtre d'usage est obligatoire")
        if not 0.0 <= self.variabilite_puissance_pourcent <= 1.0:
            raise ValueError("La variabilité de puissance doit être comprise entre 0 et 1")


@dataclass(frozen=True, slots=True)
class HistoriqueCompteur:
    """Lectures Woyofal facultatives saisies manuellement par l'utilisateur."""

    consommation_mois_precedent_kwh: float | None = None
    consommation_mois_courant_kwh: float | None = None
    consommation_veille_kwh: float | None = None
    puissance_instantanee_w: float | None = None

    def __post_init__(self) -> None:
        for nom, valeur in asdict(self).items():
            if valeur is not None and valeur < 0:
                raise ValueError(f"{nom} doit être positif ou nul")


@dataclass(frozen=True, slots=True)
class ParametresThermiques:
    """Paramètres physiques cohérents du modèle 1R1C."""

    resistance_c_par_kw: float = 6.0
    capacite_kwh_par_c: float = 0.35
    cop_climatisation: float = 3.2
    puissance_climatisation_electrique_kw: float = 1.2
    gains_internes_kw: float = 0.15
    coefficient_gains_solaires: float = 0.002
    temperature_confort_min_c: float = 22.0
    temperature_confort_max_c: float = 27.0
    gain_confort_ventilateur_c: float = 1.5

    def __post_init__(self) -> None:
        if self.resistance_c_par_kw <= 0 or self.capacite_kwh_par_c <= 0:
            raise ValueError("R et C doivent être strictement positifs")
        if not 2.0 <= self.cop_climatisation <= 5.0:
            raise ValueError("Le COP doit rester dans une plage physique plausible")
        if self.puissance_climatisation_electrique_kw < 0:
            raise ValueError("La puissance de climatisation doit être positive")
        if self.temperature_confort_min_c >= self.temperature_confort_max_c:
            raise ValueError("La borne basse de confort doit précéder la borne haute")

    @property
    def constante_temps_heures(self) -> float:
        return self.resistance_c_par_kw * self.capacite_kwh_par_c


@dataclass(frozen=True, slots=True)
class Scenario:
    """Configuration complète d'un épisode de simulation."""

    identifiant_foyer: str
    nombre_occupants: int
    credit_initial_kwh: float
    date_debut: datetime
    date_cible: datetime | None
    horizon_max_minutes: int
    appareils: tuple[Appareil, ...]
    pieces: tuple[Piece, ...] = field(default_factory=tuple)
    parametres_thermiques: ParametresThermiques = field(default_factory=ParametresThermiques)
    historique_compteur: HistoriqueCompteur = field(default_factory=HistoriqueCompteur)
    pas_minutes: int = PAS_DECISION_MINUTES
    sous_pas_thermique_minutes: int = SOUS_PAS_THERMIQUE_MINUTES
    source_meteo: str = "cache_open_meteo_era5"
    occupation_initiale: bool = True
    taux_adoption: float = 1.0
    seed: int = 42

    def __post_init__(self) -> None:
        if not self.identifiant_foyer.strip():
            raise ValueError("identifiant_foyer est obligatoire")
        if self.nombre_occupants <= 0 or self.credit_initial_kwh < 0:
            raise ValueError("Le foyer et le crédit initial sont invalides")
        if self.date_debut.tzinfo is None:
            raise ValueError("date_debut doit contenir un fuseau horaire")
        if self.date_cible is not None:
            if self.date_cible.tzinfo is None or self.date_cible <= self.date_debut:
                raise ValueError("date_cible doit être postérieure et contenir un fuseau")
        if self.horizon_max_minutes <= 0:
            raise ValueError("horizon_max_minutes doit être strictement positif")
        if self.pas_minutes != PAS_DECISION_MINUTES:
            raise ValueError(f"Le pas commun doit être {PAS_DECISION_MINUTES} minutes")
        if self.pas_minutes % self.sous_pas_thermique_minutes != 0:
            raise ValueError("Le sous-pas thermique doit diviser exactement le pas principal")
        if not self.appareils:
            raise ValueError("Le scénario doit contenir au moins un appareil")
        if not self.pieces:
            object.__setattr__(self, "pieces", _deduire_pieces(self.appareils))
        noms_pieces = [piece.nom.casefold() for piece in self.pieces]
        if len(noms_pieces) != len(set(noms_pieces)):
            raise ValueError("Les noms des pièces doivent être uniques")
        if not 0.0 <= self.taux_adoption <= 1.0:
            raise ValueError("taux_adoption doit être compris entre 0 et 1")

    @property
    def nombre_pas_max(self) -> int:
        return self.horizon_max_minutes // self.pas_minutes


@dataclass(frozen=True, slots=True)
class MeteoPas:
    horodatage: datetime
    temperature_exterieure_c: float
    humidite_pourcent: float
    rayonnement_w_m2: float = 0.0

    def __post_init__(self) -> None:
        if self.horodatage.tzinfo is None:
            raise ValueError("L'horodatage météo doit contenir un fuseau")
        if not 0.0 <= self.humidite_pourcent <= 100.0:
            raise ValueError("L'humidité doit être comprise entre 0 et 100 %")
        if self.rayonnement_w_m2 < 0:
            raise ValueError("Le rayonnement ne peut pas être négatif")


@dataclass(frozen=True, slots=True)
class ProfilChargePas:
    """Demande RAMP agrégée sur un pas de 30 minutes."""

    horodatage: datetime
    pas_minutes: int
    puissance_demandee_par_appareil_w: dict[str, float]
    energie_demandee_par_appareil_kwh: dict[str, float]
    energie_non_pilotable_kwh: float
    charges_decalables_kwh: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.pas_minutes != PAS_DECISION_MINUTES:
            raise ValueError("Le profil RAMP doit être agrégé à 30 minutes")
        valeurs = [
            *self.puissance_demandee_par_appareil_w.values(),
            *self.energie_demandee_par_appareil_kwh.values(),
            *self.charges_decalables_kwh.values(),
            self.energie_non_pilotable_kwh,
        ]
        if any(valeur < -1e-12 for valeur in valeurs):
            raise ValueError("Un profil de charge ne peut pas contenir de valeur négative")


@dataclass(frozen=True, slots=True)
class ReportCharge:
    appareil: str
    report_minutes: int

    def __post_init__(self) -> None:
        if not self.appareil or self.report_minutes <= 0:
            raise ValueError("Le report doit préciser un appareil et une durée positive")
        if self.report_minutes % PAS_DECISION_MINUTES != 0:
            raise ValueError("Le report doit être un multiple de 30 minutes")


@dataclass(frozen=True, slots=True)
class Action:
    piece_cible: str | None
    mode_confort: ModeConfort | None
    report_charge: ReportCharge | None = None

    @property
    def temperature_consigne_c(self) -> float | None:
        return None if self.mode_confort is None else self.mode_confort.consigne_c


@dataclass(frozen=True, slots=True)
class Observation:
    credit_restant_kwh: float
    heure: float
    jour_semaine: int
    temps_avant_cible_minutes: int
    temperatures_interieures_c: dict[str, float]
    temperature_exterieure_c: float
    humidite_pourcent: float
    occupations: dict[str, bool]
    consommation_cumulee_kwh: float
    rythme_kwh_par_jour: float
    demande_decalable_kwh: float
    historique_moyen_kwh_par_jour: float
    modes_confort: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StepResult:
    nouvelle_observation: Observation
    action_recommandee: Action
    action_appliquee: Action
    energie_demandee_kwh: float
    energie_servie_kwh: float
    energie_non_servie_kwh: float
    recompense: float
    termine: bool
    tronque: bool
    informations: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MetriquesEpisode:
    consommation_demandee_kwh: float
    consommation_servie_kwh: float
    energie_non_servie_kwh: float
    credit_restant_kwh: float
    inconfort_degre_heures: float
    nombre_coupures: int
    nombre_changements: int
    reports_reussis: int
    duree_survie_heures: float
    date_cible_atteinte: bool
    taux_adoption_observe: float
    raison_fin: str


def _lire_date(valeur: str | None) -> datetime | None:
    if valeur is None:
        return None
    date = datetime.fromisoformat(valeur)
    if date.tzinfo is None:
        raise ValueError("Les dates ISO 8601 doivent contenir un fuseau horaire")
    return date


def _lire_heure(valeur: str) -> time:
    return time.fromisoformat(valeur)


def _deduire_pieces(appareils: tuple[Appareil, ...]) -> tuple[Piece, ...]:
    """Compatibilité avec les anciens scénarios sans section ``pieces``."""

    climatiseurs = [a for a in appareils if a.controle_par_environnement and "clim" in a.nom.casefold()]
    ventilateurs = [a for a in appareils if a.controle_par_environnement and "ventil" in a.nom.casefold()]
    nombre_clims = sum(a.quantite for a in climatiseurs)
    nombre_ventilos = sum(a.quantite for a in ventilateurs)
    nombre = max(1, nombre_clims, nombre_ventilos)
    puissance_clim = climatiseurs[0].puissance_w if climatiseurs else None
    puissance_ventilo = ventilateurs[0].puissance_w if ventilateurs else None
    return tuple(
        Piece(
            nom=("Salon" if index == 0 else f"Chambre {index}"),
            type_piece=("salon" if index == 0 else "chambre"),
            taille="moyenne",
            climatisation=index < nombre_clims,
            ventilateur=index < nombre_ventilos,
            puissance_climatisation_w=puissance_clim if index < nombre_clims else None,
            puissance_ventilateur_w=puissance_ventilo if index < nombre_ventilos else None,
        )
        for index in range(nombre)
    )


def charger_scenario(chemin: str | Path) -> Scenario:
    """Charge et valide un scénario JSON au format final."""

    contenu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    appareils: list[Appareil] = []
    for donnees_source in contenu.pop("appareils"):
        donnees = dict(donnees_source)
        fenetres = []
        for fenetre_source in donnees.pop("fenetres_usage"):
            fenetre = dict(fenetre_source)
            fenetre["heure_debut"] = _lire_heure(fenetre["heure_debut"])
            fenetre["heure_fin"] = _lire_heure(fenetre["heure_fin"])
            fenetres.append(FenetreUsage(**fenetre))
        appareils.append(Appareil(**donnees, fenetres_usage=tuple(fenetres)))

    donnees_pieces = []
    for source_piece in contenu.pop("pieces", []):
        donnees_piece = dict(source_piece)
        occupation_jusqua = donnees_piece.get("occupation_actuelle_jusqua")
        if isinstance(occupation_jusqua, str):
            donnees_piece["occupation_actuelle_jusqua"] = _lire_date(occupation_jusqua)
        donnees_pieces.append(donnees_piece)
    pieces = tuple(Piece(**donnees) for donnees in donnees_pieces)
    thermique = ParametresThermiques(**contenu.pop("parametres_thermiques", {}))
    historique = HistoriqueCompteur(**contenu.pop("historique_compteur", {}))
    date_debut = _lire_date(contenu.pop("date_debut"))
    date_cible = _lire_date(contenu.pop("date_cible", None))
    assert date_debut is not None
    return Scenario(
        **contenu,
        date_debut=date_debut,
        date_cible=date_cible,
        appareils=tuple(appareils),
        pieces=pieces,
        parametres_thermiques=thermique,
        historique_compteur=historique,
    )
