"""Sous-environnement Gymnasium d'une pièce climatisée ou ventilée."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any, Sequence

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from common import MeteoPas, ModeConfort, ParametresThermiques, Piece, ProfilOccupation
from common.units import convertir_en_kwh
from thermal import ModeleThermique1R1C, estimer_temperature_interieure_initiale


MODES_CONFORT = tuple(ModeConfort)
HEURE_DEBUT_EXTINCTION_COMMUNS = 23.0
HEURE_FIN_EXTINCTION_COMMUNS = 6.0


def extinction_nocturne_requise(piece: Piece, horodatage: datetime) -> bool:
    """Impose l'arrêt du confort dans les espaces non dédiés au sommeil."""

    heure = horodatage.hour + horodatage.minute / 60.0
    nuit = heure >= HEURE_DEBUT_EXTINCTION_COMMUNS or heure < HEURE_FIN_EXTINCTION_COMMUNS
    return piece.type_piece != "chambre" and nuit


def occupation_piece(piece: Piece, horodatage: datetime) -> bool:
    """Estime l'occupation depuis le profil déclaré, pas depuis le nom de la pièce."""

    if (
        piece.occupation_actuelle is not None
        and piece.occupation_actuelle_jusqua is not None
        and horodatage < piece.occupation_actuelle_jusqua
    ):
        return piece.occupation_actuelle
    heure = horodatage.hour + horodatage.minute / 60.0
    weekend = horodatage.weekday() >= 5
    profil = ProfilOccupation(piece.profil_occupation)
    if profil == ProfilOccupation.TOUJOURS:
        return True
    if profil == ProfilOccupation.NUIT:
        return heure < (9.0 if weekend else 8.0) or heure >= 21.0
    if profil == ProfilOccupation.SOIREE:
        return (10.0 <= heure < 23.0) if weekend else (17.0 <= heure < 23.0)
    if profil == ProfilOccupation.JOURNEE:
        return 8.0 <= heure < 18.0
    return (
        6.0 <= heure < 8.0
        or 12.0 <= heure < 15.0
        or 18.0 <= heure < 23.0
    )


def extinction_inoccupation_requise(piece: Piece, horodatage: datetime) -> bool:
    """Interdit de dépenser du confort dans une pièce estimée vide."""

    return not occupation_piece(piece, horodatage)


class EnvironnementPiece(gym.Env[np.ndarray, int]):
    """État thermique autonome d'une pièce, synchronisé par le foyer global."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        piece: Piece,
        meteo: Sequence[MeteoPas],
        parametres: ParametresThermiques,
        *,
        pas_minutes: int = 30,
        sous_pas_minutes: int = 5,
    ) -> None:
        super().__init__()
        if not meteo:
            raise ValueError("La météo est obligatoire pour une pièce")
        self.piece = piece
        self.meteo = tuple(meteo)
        self.pas_minutes = pas_minutes
        self.sous_pas_minutes = sous_pas_minutes
        self.parametres = replace(
            parametres,
            puissance_climatisation_electrique_kw=piece.puissance_climatisation_effective_w / 1000.0,
            gains_internes_kw=parametres.gains_internes_kw * {
                "petite": 0.75, "moyenne": 1.0, "grande": 1.3,
            }[piece.taille],
        )
        self.action_space = spaces.Discrete(len(MODES_CONFORT))
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(9,), dtype=np.float32)
        self._index = 0
        self.mode = ModeConfort.ARRET

    def _mode_valide(self, mode: ModeConfort) -> ModeConfort:
        if mode == ModeConfort.VENTILATEUR and not self.piece.ventilateur:
            return ModeConfort.ARRET
        if mode.consigne_c is not None and not self.piece.climatisation:
            return ModeConfort.VENTILATEUR if self.piece.ventilateur else ModeConfort.ARRET
        return mode

    def _mode_autorise(self, mode: ModeConfort, horodatage: datetime) -> ModeConfort:
        """Normalise le matériel absent puis applique la règle d'occupation."""

        mode = self._mode_valide(mode)
        if extinction_inoccupation_requise(self.piece, horodatage):
            return ModeConfort.ARRET
        return mode

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        self._index = 0
        self.mode = ModeConfort.ARRET
        temperature = estimer_temperature_interieure_initiale(
            self.meteo,
            self.parametres,
            pas_minutes=self.pas_minutes,
            sous_pas_minutes=self.sous_pas_minutes,
        )
        self._thermique = ModeleThermique1R1C(temperature, self.parametres)
        return self._observation(), self._info(0.0, 0.0, 0.0)

    def step(self, action: int):
        if self._index >= len(self.meteo):
            raise RuntimeError("La météo de la pièce est épuisée; appelez reset()")
        point_meteo = self.meteo[self._index]
        self.mode = self._mode_autorise(MODES_CONFORT[int(action)], point_meteo.horodatage)
        occupee = occupation_piece(self.piece, point_meteo.horodatage)
        ventilateur = self.mode == ModeConfort.VENTILATEUR
        climatisation = self.mode.consigne_c is not None
        resultat = self._thermique.step(
            point_meteo,
            climatisation_active=climatisation,
            ventilateur_actif=ventilateur,
            occupation=occupee,
            temperature_consigne_c=self.mode.consigne_c,
            duree_minutes=self.pas_minutes,
            sous_pas_minutes=self.sous_pas_minutes,
        )
        energie_ventilateur = convertir_en_kwh(
            self.piece.puissance_ventilateur_effective_w if ventilateur else 0.0,
            self.pas_minutes,
        )
        energie_clim = resultat.energie_climatisation_kwh
        inconfort = resultat.inconfort_degre_heures
        self._index += 1
        tronque = self._index >= len(self.meteo)
        info = self._info(energie_clim, energie_ventilateur, inconfort)
        return self._observation(), -(energie_clim + energie_ventilateur + inconfort), False, tronque, info

    def _observation(self) -> np.ndarray:
        index = min(self._index, len(self.meteo) - 1)
        point = self.meteo[index]
        mode_one_hot = [1.0 if self.mode == mode else -1.0 for mode in MODES_CONFORT]
        return np.asarray([
            np.clip((self._thermique.temperature_interieure_c - 27.0) / 15.0, -1, 1),
            1.0 if occupation_piece(self.piece, point.horodatage) else -1.0,
            1.0 if self.piece.climatisation else -1.0,
            1.0 if self.piece.ventilateur else -1.0,
            *mode_one_hot,
        ], dtype=np.float32)

    def _info(self, energie_clim: float, energie_ventilateur: float, inconfort: float) -> dict[str, Any]:
        index = min(self._index, len(self.meteo) - 1)
        return {
            "piece": self.piece.nom,
            "mode": self.mode.value,
            "consigne_c": self.mode.consigne_c,
            "temperature_interieure_estimee_c": self._thermique.temperature_interieure_c,
            "occupation_estimee": occupation_piece(self.piece, self.meteo[index].horodatage),
            "energie_climatisation_kwh": energie_clim,
            "energie_ventilateur_kwh": energie_ventilateur,
            "inconfort_degre_heures": inconfort,
            "inconfort_pilotable_degre_heures": (
                inconfort if (self.piece.climatisation or self.piece.ventilateur) else 0.0
            ),
        }
