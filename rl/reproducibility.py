"""Métadonnées nécessaires pour reproduire un entraînement."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
from typing import Any

import gymnasium
import numpy
import stable_baselines3


def _commande_git(*arguments: str) -> str:
    try:
        resultat = subprocess.run(
            ["git", *arguments], check=True, capture_output=True, text=True
        )
        return resultat.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "indisponible"


def creer_metadonnees(
    *, algorithme: str, seed: int, configuration: dict[str, Any]
) -> dict[str, Any]:
    """Capture code, dépendances, seed et paramètres au moment du run."""

    return {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "algorithme": algorithme,
        "seed": seed,
        "commit_git": _commande_git("rev-parse", "HEAD"),
        "branche_git": _commande_git("branch", "--show-current"),
        "etat_git": _commande_git("status", "--short"),
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "gymnasium": gymnasium.__version__,
        "stable_baselines3": stable_baselines3.__version__,
        "configuration": configuration,
    }


def sauvegarder_json(contenu: dict[str, Any], chemin: str | Path) -> Path:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chemin

