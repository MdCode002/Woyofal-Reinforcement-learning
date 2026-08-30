"""Environnement global à politique partagée et nombre de pièces variable."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from math import cos, log1p, pi, sin
from typing import Any, Sequence

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from common import Action, Appareil, MeteoPas, ModeConfort, ProfilChargePas, ReportCharge, Scenario
from rl.config import ConfigurationRecompense
from rl.reward import calculer_recompense
from woyofal import CompteurWoyofal

from .room_env import (
    EnvironnementPiece,
    MODES_CONFORT,
    extinction_inoccupation_requise,
    extinction_nocturne_requise,
    occupation_piece,
)


# Une même politique décide successivement pour chaque pièce. La taille de
# l'espace RL ne dépend donc plus du nombre de chambres du foyer.
NOMBRE_ACTIONS = len(MODES_CONFORT) * 2
DIMENSION_OBSERVATION_GLOBALE = 16
DIMENSION_OBSERVATION_PIECE = 9
DIMENSION_OBSERVATION_AGREGEE = 8
DIMENSION_OBSERVATION = (
    DIMENSION_OBSERVATION_GLOBALE
    + DIMENSION_OBSERVATION_PIECE
    + DIMENSION_OBSERVATION_AGREGEE
)


@dataclass(slots=True)
class _TacheFlexible:
    appareil: str
    energie_kwh: float
    echeance_index: int


def decoder_action(action: int) -> tuple[ModeConfort, bool]:
    """Décode un mode pour la pièce courante et une demande de report."""

    if action not in range(NOMBRE_ACTIONS):
        raise ValueError(f"L'action doit être un entier de 0 à {NOMBRE_ACTIONS - 1}")
    mode_index, report = divmod(int(action), 2)
    return MODES_CONFORT[mode_index], bool(report)


def encoder_action(
    mode: ModeConfort | str = ModeConfort.ARRET,
    report: bool = False,
) -> int:
    mode = ModeConfort(mode)
    return 2 * MODES_CONFORT.index(mode) + int(report)


class EnvironnementWoyofal(gym.Env[np.ndarray, int]):
    """Coordonne des pièces sans priorité et un unique crédit prépayé.

    Un appel ``step`` décide pour la pièce courante. Lorsque toutes les pièces
    ont reçu une décision, le temps physique avance de 30 minutes. L'ordre des
    pièces est remélangé à chaque pas avec la graine de l'épisode : aucune
    chambre, aucun nom et aucun indice ne reçoivent un avantage structurel.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        scenario: Scenario,
        profils: Sequence[ProfilChargePas],
        meteo: Sequence[MeteoPas],
        configuration_recompense: ConfigurationRecompense | None = None,
        ablation: str = "aucune",
    ) -> None:
        super().__init__()
        if not profils or not meteo:
            raise ValueError("Profils RAMP et météo sont obligatoires")
        self.scenario = scenario
        self.profils = list(profils[: scenario.nombre_pas_max])
        self.meteo = list(meteo[: scenario.nombre_pas_max])
        self.configuration_recompense = configuration_recompense or ConfigurationRecompense()
        ablations = {
            "aucune", "sans_historique", "sans_credit_observable",
            "sans_inertie", "sans_randomisation",
        }
        if ablation not in ablations:
            raise ValueError(f"Ablation inconnue : {ablation}")
        self.ablation = ablation
        self.nombre_pas_disponibles = min(
            len(self.profils), len(self.meteo), scenario.nombre_pas_max,
        )
        self.action_space = spaces.Discrete(NOMBRE_ACTIONS)
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(DIMENSION_OBSERVATION,), dtype=np.float32,
        )
        self._appareils = {a.nom: a for a in scenario.appareils}
        self._seed_initiale = scenario.seed
        self._pieces = tuple(scenario.pieces)

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        graine = self._seed_initiale if seed is None else seed
        super().reset(seed=graine)
        self._index = 0
        self._compteur = CompteurWoyofal(self.scenario.credit_initial_kwh)
        self._environnements_pieces = [
            EnvironnementPiece(
                piece,
                self.meteo[:self.nombre_pas_disponibles],
                self.scenario.parametres_thermiques,
                pas_minutes=self.scenario.pas_minutes,
                sous_pas_minutes=self.scenario.sous_pas_thermique_minutes,
            )
            for piece in self._pieces
        ]
        for index, environnement in enumerate(self._environnements_pieces):
            environnement.reset(seed=graine + index)
        self._taches: list[_TacheFlexible] = []
        self._action_precedente = Action(None, None, None)
        self._energie_demandee = 0.0
        self._energie_servie = 0.0
        self._energie_non_servie = 0.0
        self._inconfort = 0.0
        self._inconfort_pilotable = 0.0
        self._changements = 0
        self._reports_reussis = 0
        self._recommandations = 0
        self._adoptions = 0
        self._raison_fin = "en_cours"
        self._termine = False
        self._tronque = False
        self._preparer_cycle_decisions()
        return self._observation(), self._info()

    def _preparer_cycle_decisions(self) -> None:
        self._ordre_decision = self.np_random.permutation(len(self._pieces)).tolist()
        self._position_decision = 0
        self._actions_recommandees: dict[str, str] = {}
        self._actions_appliquees: dict[str, str] = {}
        self._report_demande = False
        self._action_invalide_cycle = False
        self._extinctions_inoccupation: list[str] = []
        self._extinctions_nuit: list[str] = []
        self._modes_avant_cycle = tuple(
            environnement.mode for environnement in self._environnements_pieces
        )

    @property
    def _index_piece_courante(self) -> int:
        return int(self._ordre_decision[self._position_decision])

    def _ratio_temps_restant(self, index: int) -> float:
        if self.scenario.date_cible is None:
            return float(np.clip(1.0 - index / max(self.nombre_pas_disponibles, 1), 0.0, 1.0))
        instant = self.scenario.date_debut + timedelta(minutes=index * self.scenario.pas_minutes)
        minutes = max(0.0, (self.scenario.date_cible - instant).total_seconds() / 60.0)
        total = max((self.scenario.date_cible - self.scenario.date_debut).total_seconds() / 60.0, 1.0)
        return float(np.clip(minutes / total, 0.0, 1.0))

    def _budget_journalier_restant(self, index: int) -> float:
        if self.scenario.date_cible is not None:
            instant = self.scenario.date_debut + timedelta(minutes=index * self.scenario.pas_minutes)
            jours_restants = max(
                (self.scenario.date_cible - instant).total_seconds() / 86_400.0,
                self.scenario.pas_minutes / 1_440.0,
            )
        else:
            jours_restants = max(
                (self.nombre_pas_disponibles - index) * self.scenario.pas_minutes / 1_440.0,
                self.scenario.pas_minutes / 1_440.0,
            )
        return self._compteur.credit_restant_kwh / jours_restants

    def _echeance(self, appareil: Appareil, horodatage) -> int:
        minute = horodatage.hour * 60 + horodatage.minute
        candidats: list[int] = []
        for fenetre in appareil.fenetres_usage:
            debut = fenetre.heure_debut.hour * 60 + fenetre.heure_debut.minute
            fin = fenetre.heure_fin.hour * 60 + fenetre.heure_fin.minute
            if debut <= fin and debut <= minute <= fin:
                candidats.append(fin)
            elif debut > fin and (minute >= debut or minute <= fin):
                candidats.append(fin + (1440 if minute >= debut else 0))
        if not candidats:
            return self._index
        pas_restants = max(0, (min(candidats) - minute) // self.scenario.pas_minutes)
        return min(self.nombre_pas_disponibles - 1, self._index + pas_restants)

    def _ajouter_taches(self, profil: ProfilChargePas) -> None:
        for nom, energie in profil.charges_decalables_kwh.items():
            if energie <= 1e-12:
                continue
            appareil = self._appareils.get(nom)
            echeance = self._index if appareil is None else self._echeance(appareil, profil.horodatage)
            self._taches.append(_TacheFlexible(nom, energie, echeance))

    def _action_reference(self, index_piece: int, horodatage) -> Action:
        piece = self._pieces[index_piece]
        temperature = self._environnements_pieces[index_piece]._thermique.temperature_interieure_c
        occupee = occupation_piece(piece, horodatage)
        if occupee and temperature > 29.0 and piece.climatisation:
            mode = ModeConfort.CLIM_ECO
        elif occupee and temperature > 27.0 and piece.ventilateur:
            mode = ModeConfort.VENTILATEUR
        else:
            mode = ModeConfort.ARRET
        return Action(piece.nom, mode, None)

    def _appliquer_adoption(self, recommandee: Action, index_piece: int, horodatage) -> Action:
        self._recommandations += 1
        if self.np_random.random() <= self.scenario.taux_adoption:
            self._adoptions += 1
            return recommandee
        return self._action_reference(index_piece, horodatage)

    def _traiter_taches(self, report: ReportCharge | None) -> tuple[float, str | None]:
        energie_flexible = 0.0
        restantes: list[_TacheFlexible] = []
        appareil_reporte = None
        for tache in self._taches:
            peut_reporter = (
                report is not None
                and tache.appareil == report.appareil
                and tache.echeance_index > self._index
            )
            if peut_reporter:
                restantes.append(tache)
                appareil_reporte = tache.appareil
            else:
                energie_flexible += tache.energie_kwh
        if appareil_reporte is not None:
            self._reports_reussis += 1
        self._taches = restantes
        return energie_flexible, appareil_reporte

    def _eteindre_pieces_inoccupees(self, horodatage) -> None:
        for environnement in self._environnements_pieces:
            if (
                extinction_inoccupation_requise(environnement.piece, horodatage)
                and environnement.mode != ModeConfort.ARRET
            ):
                environnement.mode = ModeConfort.ARRET
                self._extinctions_inoccupation.append(environnement.piece.nom)
                if extinction_nocturne_requise(environnement.piece, horodatage):
                    self._extinctions_nuit.append(environnement.piece.nom)

    def _info_decision_intermediaire(
        self, recommandee: Action, appliquee: Action, action_invalide: bool,
    ) -> dict[str, Any]:
        info = self._info()
        info.update({
            "decision_physique_appliquee": False,
            "action_recommandee": asdict(recommandee),
            "action_appliquee": asdict(appliquee),
            "actions_recommandees_pieces": dict(self._actions_recommandees),
            "actions_appliquees_pieces": dict(self._actions_appliquees),
            "action_invalide_normalisee": action_invalide,
            "energie_demandee_pas_kwh": 0.0,
            "energie_servie_pas_kwh": 0.0,
            "energie_non_servie_pas_kwh": 0.0,
            "inconfort_pas_degre_heures": 0.0,
        })
        return info

    def step(self, action: int):
        if self._termine or self._tronque:
            raise RuntimeError("L'épisode est fini; appelez reset()")
        mode, veut_reporter = decoder_action(int(action))
        profil, meteo = self.profils[self._index], self.meteo[self._index]
        if self._position_decision == 0:
            self._eteindre_pieces_inoccupees(profil.horodatage)
            self._ajouter_taches(profil)
            self._taches.sort(key=lambda t: (t.echeance_index, t.appareil))

        index_piece = self._index_piece_courante
        environnement_piece = self._environnements_pieces[index_piece]
        mode_effectif = environnement_piece._mode_autorise(mode, profil.horodatage)
        action_invalide = mode_effectif != mode
        self._action_invalide_cycle = self._action_invalide_cycle or action_invalide
        if (
            mode != ModeConfort.ARRET
            and mode_effectif == ModeConfort.ARRET
            and extinction_inoccupation_requise(environnement_piece.piece, profil.horodatage)
        ):
            if environnement_piece.piece.nom not in self._extinctions_inoccupation:
                self._extinctions_inoccupation.append(environnement_piece.piece.nom)
            if (
                extinction_nocturne_requise(environnement_piece.piece, profil.horodatage)
                and environnement_piece.piece.nom not in self._extinctions_nuit
            ):
                self._extinctions_nuit.append(environnement_piece.piece.nom)

        report = None
        if veut_reporter and self._taches and self._taches[0].echeance_index > self._index:
            cible = self._taches[0]
            report = ReportCharge(cible.appareil, self.scenario.pas_minutes)
        recommandee = Action(environnement_piece.piece.nom, mode_effectif, report)
        appliquee = self._appliquer_adoption(recommandee, index_piece, profil.horodatage)
        environnement_piece.mode = environnement_piece._mode_autorise(
            appliquee.mode_confort or ModeConfort.ARRET, profil.horodatage,
        )
        self._actions_recommandees[environnement_piece.piece.nom] = mode_effectif.value
        self._actions_appliquees[environnement_piece.piece.nom] = environnement_piece.mode.value
        self._report_demande = self._report_demande or appliquee.report_charge is not None
        self._action_precedente = appliquee

        derniere_piece = self._position_decision == len(self._pieces) - 1
        if not derniere_piece:
            self._position_decision += 1
            return (
                self._observation(), 0.0, False, False,
                self._info_decision_intermediaire(recommandee, appliquee, action_invalide),
            )

        report_effectif = None
        if self._report_demande and self._taches and self._taches[0].echeance_index > self._index:
            cible = self._taches[0]
            report_effectif = ReportCharge(cible.appareil, self.scenario.pas_minutes)
        energie_flexible, appareil_reporte = self._traiter_taches(report_effectif)

        resultats_pieces = []
        for environnement in self._environnements_pieces:
            _, _, _, _, info_piece = environnement.step(MODES_CONFORT.index(environnement.mode))
            resultats_pieces.append(info_piece)
        energie_climatisation = sum(i["energie_climatisation_kwh"] for i in resultats_pieces)
        energie_ventilateur = sum(i["energie_ventilateur_kwh"] for i in resultats_pieces)
        inconfort_pas = sum(i["inconfort_degre_heures"] for i in resultats_pieces)
        inconfort_pilotable_pas = sum(
            i["inconfort_pilotable_degre_heures"] for i in resultats_pieces
        )

        credit_initial = max(self.scenario.credit_initial_kwh, 1e-6)
        marge_avant = (
            self._compteur.credit_restant_kwh / credit_initial
            - self._ratio_temps_restant(self._index)
        )
        demande = (
            profil.energie_non_pilotable_kwh + energie_flexible
            + energie_ventilateur + energie_climatisation
        )
        resultat_compteur = self._compteur.servir(demande)
        if self.ablation == "sans_inertie":
            for environnement in self._environnements_pieces:
                environnement._thermique.temperature_interieure_c = meteo.temperature_exterieure_c

        modes_apres = tuple(e.mode for e in self._environnements_pieces)
        changee = modes_apres != self._modes_avant_cycle
        if changee:
            self._changements += 1
        self._energie_demandee += demande
        self._energie_servie += resultat_compteur.energie_servie_kwh
        self._energie_non_servie += resultat_compteur.energie_non_servie_kwh
        self._inconfort += inconfort_pas
        self._inconfort_pilotable += inconfort_pilotable_pas
        self._index += 1
        marge_apres = (
            self._compteur.credit_restant_kwh / credit_initial
            - self._ratio_temps_restant(self._index)
        )

        coupure = resultat_compteur.coupure or self._compteur.credit_restant_kwh <= 1e-12
        instant_suivant = profil.horodatage + timedelta(minutes=self.scenario.pas_minutes)
        succes = (
            self.scenario.date_cible is not None
            and instant_suivant >= self.scenario.date_cible
            and not coupure
        )
        self._termine = coupure or succes
        if not self._termine and self._index >= self.nombre_pas_disponibles:
            self._tronque = True
        if coupure:
            self._raison_fin = "credit_epuise"
        elif succes:
            self._raison_fin = "date_cible_atteinte"
        elif self._tronque:
            self._raison_fin = "horizon_ou_donnees_epuisees"

        taches_inachevees = (
            sum(t.energie_kwh for t in self._taches)
            if (self._termine or self._tronque) else 0.0
        )
        detail = calculer_recompense(
            energie_pilotable_kwh=energie_climatisation + energie_ventilateur,
            facteur_energie_pilotable=float(np.clip(1.0 - 1.5 * marge_avant, 0.4, 3.0)),
            energie_non_servie_kwh=resultat_compteur.energie_non_servie_kwh,
            inconfort_degre_heures=inconfort_pilotable_pas,
            energie_taches_inachevees_kwh=taches_inachevees,
            coupure=coupure,
            action_changee=changee,
            action_invalide=self._action_invalide_cycle,
            date_cible_atteinte=succes,
            progression_budget=marge_apres - marge_avant,
            configuration=self.configuration_recompense,
        )
        actions_recommandees = dict(self._actions_recommandees)
        actions_appliquees = dict(self._actions_appliquees)
        extinctions_inoccupation = list(self._extinctions_inoccupation)
        extinctions_nuit = list(self._extinctions_nuit)
        action_invalide_cycle = self._action_invalide_cycle
        if not (self._termine or self._tronque):
            self._preparer_cycle_decisions()
        info = self._info()
        info.update({
            "decision_physique_appliquee": True,
            "horodatage": profil.horodatage.isoformat(),
            "temperature_exterieure_c": meteo.temperature_exterieure_c,
            "humidite_exterieure_pourcent": meteo.humidite_pourcent,
            "occupations_estimees": {
                piece.nom: occupation_piece(piece, profil.horodatage) for piece in self._pieces
            },
            "action_recommandee": asdict(recommandee),
            "action_appliquee": asdict(appliquee),
            "actions_recommandees_pieces": actions_recommandees,
            "actions_appliquees_pieces": actions_appliquees,
            "appareil_flexible_reporte": appareil_reporte,
            "action_invalide_normalisee": action_invalide_cycle,
            "extinctions_automatiques_inoccupation": extinctions_inoccupation,
            "extinctions_automatiques_nuit": extinctions_nuit,
            "recommandation_charge": (
                f"Ne pas démarrer {appareil_reporte} maintenant; réévaluer dans 30 minutes."
                if appareil_reporte else None
            ),
            "energie_demandee_pas_kwh": demande,
            "energie_servie_pas_kwh": resultat_compteur.energie_servie_kwh,
            "energie_non_servie_pas_kwh": resultat_compteur.energie_non_servie_kwh,
            "energie_non_pilotable_pas_kwh": profil.energie_non_pilotable_kwh,
            "energie_flexible_pas_kwh": energie_flexible,
            "energie_climatisation_pas_kwh": energie_climatisation,
            "energie_ventilateur_pas_kwh": energie_ventilateur,
            "inconfort_pas_degre_heures": inconfort_pas,
            "inconfort_pilotable_pas_degre_heures": inconfort_pilotable_pas,
            "pieces": resultats_pieces,
            "detail_recompense": asdict(detail),
        })
        return self._observation(), float(detail.total), self._termine, self._tronque, info

    def _historique_journalier(self) -> float:
        h = self.scenario.historique_compteur
        if h.consommation_veille_kwh is not None:
            return h.consommation_veille_kwh
        if h.consommation_mois_precedent_kwh is not None:
            return h.consommation_mois_precedent_kwh / 30.0
        return 0.0

    def _observation(self) -> np.ndarray:
        index = min(self._index, self.nombre_pas_disponibles - 1)
        profil, meteo = self.profils[index], self.meteo[index]
        heure = profil.horodatage.hour + profil.horodatage.minute / 60.0
        jour = profil.horodatage.weekday()
        credit_initial = max(self.scenario.credit_initial_kwh, 1e-6)
        jours_ecoules = max(self._index * self.scenario.pas_minutes / 1440.0, 1 / 48)
        rythme = self._energie_servie / jours_ecoules
        ratio_temps = self._ratio_temps_restant(self._index)
        demande_flexible = (
            sum(t.energie_kwh for t in self._taches)
            + sum(profil.charges_decalables_kwh.values())
        )
        ratio_credit = np.clip(self._compteur.credit_restant_kwh / credit_initial, 0, 1)
        credit_normalise = 2 * ratio_credit - 1
        historique_normalise = 2 * np.clip(self._historique_journalier() / 20.0, 0, 1) - 1
        if self.ablation == "sans_credit_observable":
            credit_normalise = 0.0
        if self.ablation == "sans_historique":
            historique_normalise = 0.0
        valeurs_globales = [
            credit_normalise,
            2 * np.clip(ratio_temps, 0, 1) - 1,
            sin(2 * pi * heure / 24), cos(2 * pi * heure / 24),
            sin(2 * pi * jour / 7), cos(2 * pi * jour / 7),
            np.clip((meteo.temperature_exterieure_c - 30) / 20, -1, 1),
            2 * np.clip(meteo.humidite_pourcent / 100, 0, 1) - 1,
            2 * np.clip(self._budget_journalier_restant(self._index) / 10.0, 0, 1) - 1,
            2 * np.clip(self._energie_servie / credit_initial, 0, 1) - 1,
            2 * np.clip(rythme / 20.0, 0, 1) - 1,
            historique_normalise,
            2 * np.clip(demande_flexible / 5.0, 0, 1) - 1,
            2 * self.scenario.taux_adoption - 1,
            np.clip(ratio_credit - ratio_temps, -1, 1),
            2 * np.clip(profil.energie_non_pilotable_kwh / 2.5, 0, 1) - 1,
        ]
        piece_courante = self._environnements_pieces[self._index_piece_courante]
        valeurs_piece = piece_courante._observation().tolist()
        n = len(self._pieces)
        occupations = [occupation_piece(p, profil.horodatage) for p in self._pieces]
        temperatures = [e._thermique.temperature_interieure_c for e in self._environnements_pieces]
        valeurs_agregees = [
            2 * sum(occupations) / n - 1,
            2 * sum(p.climatisation for p in self._pieces) / n - 1,
            2 * sum(p.ventilateur for p in self._pieces) / n - 1,
            np.clip((float(np.mean(temperatures)) - 27.0) / 15.0, -1, 1),
            np.clip((float(np.max(temperatures)) - 27.0) / 15.0, -1, 1),
            2 * sum(e.mode != ModeConfort.ARRET for e in self._environnements_pieces) / n - 1,
            2 * (n - self._position_decision) / n - 1,
            2 * min(log1p(n) / log1p(20), 1.0) - 1,
        ]
        return np.asarray(
            [*valeurs_globales, *valeurs_piece, *valeurs_agregees], dtype=np.float32,
        )

    def _info(self) -> dict[str, Any]:
        temperatures = {
            e.piece.nom: e._thermique.temperature_interieure_c
            for e in self._environnements_pieces
        }
        modes = {e.piece.nom: e.mode.value for e in self._environnements_pieces}
        index = min(self._index, self.nombre_pas_disponibles - 1)
        occupations = {
            piece.nom: occupation_piece(piece, self.meteo[index].horodatage)
            for piece in self._pieces
        }
        piece_courante = self._pieces[self._index_piece_courante]
        return {
            "index_pas": self._index,
            "nombre_pieces": len(self._pieces),
            "piece_decision_courante": piece_courante.nom,
            "position_decision": self._position_decision,
            "horodatage": self.meteo[index].horodatage.isoformat(),
            "credit_restant_kwh": self._compteur.credit_restant_kwh,
            "temperature_interieure_c": float(np.mean(list(temperatures.values()))),
            "temperatures_pieces_c": temperatures,
            "modes_pieces": modes,
            "occupations_estimees": occupations,
            "source_temperature_interieure": "estimations_1r1c_par_piece_sans_thermometre",
            "energie_demandee_cumulee_kwh": self._energie_demandee,
            "energie_servie_cumulee_kwh": self._energie_servie,
            "energie_non_servie_cumulee_kwh": self._energie_non_servie,
            "inconfort_cumule_degre_heures": self._inconfort,
            "inconfort_pilotable_cumule_degre_heures": self._inconfort_pilotable,
            "nombre_changements": self._changements,
            "reports_reussis": self._reports_reussis,
            "energie_taches_en_attente_kwh": sum(t.energie_kwh for t in self._taches),
            "taux_adoption_observe": self._adoptions / max(self._recommandations, 1),
            "date_cible_atteinte": self._raison_fin == "date_cible_atteinte",
            "date_cible_fournie": self.scenario.date_cible is not None,
            "raison_fin": self._raison_fin,
        }
