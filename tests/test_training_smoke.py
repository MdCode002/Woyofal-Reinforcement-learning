from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil

import numpy as np

from env import NOMBRE_ACTIONS, creer_environnement
from rl.config import charger_configuration
from rl.train import charger_modele, entrainer


def test_smoke_training_et_rechargement_dqn(tmp_path: Path):
    configuration = deepcopy(charger_configuration())
    configuration["dqn"].update({
        "buffer_size": 500, "learning_starts": 8, "batch_size": 16,
    })
    dossier = tmp_path / "smoke_dqn"
    chemin = entrainer(
        algorithme="dqn",
        configuration=configuration,
        seed=3,
        total_timesteps=64,
        dossier_sortie=str(dossier),
        verbose=0,
    )
    modele = charger_modele("dqn", chemin)
    observation, _ = creer_environnement(seed=3).reset(seed=3)
    action, _ = modele.predict(observation, deterministic=True)
    assert int(np.asarray(action).item()) in range(NOMBRE_ACTIONS)
