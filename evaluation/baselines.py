"""Quatre règles simples pour la même politique partagée que DQN et PPO."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, pi

import numpy as np

from common import ModeConfort
from env.room_env import MODES_CONFORT
from env.woyofal_env import DIMENSION_OBSERVATION_GLOBALE, encoder_action


def _etat(observation: np.ndarray) -> dict:
    obs = np.asarray(observation, dtype=float).reshape(-1)
    heure = (atan2(obs[2], obs[3]) % (2 * pi)) * 24 / (2 * pi)
    bloc = obs[DIMENSION_OBSERVATION_GLOBALE:DIMENSION_OBSERVATION_GLOBALE + 9]
    return {
        "credit_relatif": (obs[0] + 1) / 2,
        "temps_relatif": (obs[1] + 1) / 2,
        "heure": heure,
        "demande_flexible": (obs[12] + 1) * 2.5,
        "piece": {
            "temperature": 27 + 15 * bloc[0],
            "occupee": bloc[1] > 0,
            "climatisation": bloc[2] > 0,
            "ventilateur": bloc[3] > 0,
            "mode": MODES_CONFORT[int(np.argmax(bloc[4:9]))],
        },
    }


class PolitiqueToutAllume:
    nom = "tout_allume"

    def predict(self, observation: np.ndarray, deterministic: bool = True):
        del deterministic
        piece = _etat(observation)["piece"]
        if piece["climatisation"]:
            mode = ModeConfort.CLIM_BOOST
        elif piece["ventilateur"]:
            mode = ModeConfort.VENTILATEUR
        else:
            mode = ModeConfort.ARRET
        return np.array(encoder_action(mode), dtype=np.int64), None


@dataclass(slots=True)
class PolitiqueHorairesFixes:
    debut_clim_h: float = 21.0
    fin_clim_h: float = 6.0
    nom: str = "horaires_fixes"

    def predict(self, observation: np.ndarray, deterministic: bool = True):
        del deterministic
        etat = _etat(observation)
        piece = etat["piece"]
        horaire_nuit = etat["heure"] >= self.debut_clim_h or etat["heure"] < self.fin_clim_h
        if not piece["occupee"]:
            mode = ModeConfort.ARRET
        elif horaire_nuit and piece["climatisation"]:
            mode = ModeConfort.CLIM_ECO
        elif piece["temperature"] > 27.0 and piece["ventilateur"]:
            mode = ModeConfort.VENTILATEUR
        else:
            mode = ModeConfort.ARRET
        return np.array(encoder_action(mode), dtype=np.int64), None


class PolitiqueEconomieMaximale:
    """Borne comparative : confort piloté coupé, reports systématiques."""

    nom = "economie_maximale"

    def predict(self, observation: np.ndarray, deterministic: bool = True):
        del observation, deterministic
        return np.array(encoder_action(ModeConfort.ARRET, True), dtype=np.int64), None


@dataclass(slots=True)
class PolitiqueGloutonne:
    nom: str = "gloutonne_ventilateur_avant_clim"

    def predict(self, observation: np.ndarray, deterministic: bool = True):
        del deterministic
        etat = _etat(observation)
        piece = etat["piece"]
        report = etat["demande_flexible"] > 0 and etat["credit_relatif"] < etat["temps_relatif"]
        if not piece["occupee"]:
            mode = ModeConfort.ARRET
        elif piece["temperature"] > 29.5 and piece["climatisation"] and etat["credit_relatif"] > 0.15:
            mode = ModeConfort.CLIM_ECO
        elif piece["temperature"] > 27.0 and piece["ventilateur"]:
            mode = ModeConfort.VENTILATEUR
        else:
            mode = ModeConfort.ARRET
        return np.array(encoder_action(mode, report), dtype=np.int64), None


def creer_baselines() -> dict[str, object]:
    politiques = (
        PolitiqueToutAllume(), PolitiqueHorairesFixes(),
        PolitiqueEconomieMaximale(), PolitiqueGloutonne(),
    )
    return {politique.nom: politique for politique in politiques}
