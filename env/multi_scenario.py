"""Environnement d'entraînement qui change de foyer à chaque épisode."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from common import ParametresThermiques, charger_scenario
from ramp_adapter import generer_profils_ramp, meteo_pour_scenario
from rl.config import ConfigurationRecompense

from .woyofal_env import DIMENSION_OBSERVATION, NOMBRE_ACTIONS, EnvironnementWoyofal


@lru_cache(maxsize=96)
def _donnees_partagees(chemin_resolu: str, realisation_seed: int):
    """Cache une réalisation RAMP commune aux politiques comparées."""

    scenario = charger_scenario(chemin_resolu)
    graine_ramp = (scenario.seed * 1_000_003 + realisation_seed) % (2**32 - 1)
    profils = tuple(generer_profils_ramp(scenario, seed=graine_ramp))
    meteo = tuple(meteo_pour_scenario(scenario))
    return scenario, profils, meteo


class EnvironnementMultiScenario(gym.Env[np.ndarray, int]):
    """Sélection déterministe d'un scénario, avec un petit cache mémoire LRU."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        chemins_scenarios: Sequence[str | Path],
        *,
        configuration_recompense: ConfigurationRecompense | None = None,
        taux_adoption: float | None = None,
        ablation: str = "aucune",
        taille_cache: int = 4,
    ) -> None:
        super().__init__()
        self.chemins = tuple(Path(p) for p in chemins_scenarios)
        if not self.chemins:
            raise ValueError("Aucun scénario fourni")
        self.configuration_recompense = configuration_recompense
        self.taux_adoption = taux_adoption
        self.ablation = ablation
        self.taille_cache = max(1, taille_cache)
        self.action_space = spaces.Discrete(NOMBRE_ACTIONS)
        self.observation_space = spaces.Box(
            -1.0, 1.0, shape=(DIMENSION_OBSERVATION,), dtype=np.float32,
        )
        self._cache: OrderedDict[tuple[Path, int], tuple] = OrderedDict()
        self._courant: EnvironnementWoyofal | None = None
        self.scenario_courant = ""

    def _donnees(self, chemin: Path, realisation_seed: int):
        cle = (chemin, realisation_seed)
        if cle in self._cache:
            self._cache.move_to_end(cle)
            return self._cache[cle]
        scenario, profils, meteo = _donnees_partagees(
            str(chemin.resolve()), realisation_seed
        )
        if self.taux_adoption is not None:
            scenario = replace(scenario, taux_adoption=self.taux_adoption)
        if self.ablation == "sans_randomisation":
            parametres = ParametresThermiques()
            scenario = replace(
                scenario,
                parametres_thermiques=parametres,
                taux_adoption=1.0,
            )
        donnees = scenario, profils, meteo
        self._cache[cle] = donnees
        if len(self._cache) > self.taille_cache:
            self._cache.popitem(last=False)
        return donnees

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        index = 0 if self.ablation == "sans_randomisation" else int(
            self.np_random.integers(0, len(self.chemins))
        )
        chemin = self.chemins[index]
        if self.ablation == "sans_randomisation":
            realisation_seed = 0
        elif seed is not None:
            realisation_seed = int(seed)
        else:
            realisation_seed = int(self.np_random.integers(1, 2**31 - 1))
        scenario, profils, meteo = self._donnees(chemin, realisation_seed)
        self._courant = EnvironnementWoyofal(
            scenario, profils, meteo,
            configuration_recompense=self.configuration_recompense,
            ablation=self.ablation,
        )
        self.scenario_courant = scenario.identifiant_foyer
        observation, info = self._courant.reset(seed=realisation_seed)
        info["scenario"] = self.scenario_courant
        return observation, info

    def step(self, action: int):
        if self._courant is None:
            raise RuntimeError("Appelez reset() avant step()")
        observation, recompense, termine, tronque, info = self._courant.step(action)
        info["scenario"] = self.scenario_courant
        return observation, recompense, termine, tronque, info

    def close(self) -> None:
        if self._courant is not None:
            self._courant.close()
        self._cache.clear()
