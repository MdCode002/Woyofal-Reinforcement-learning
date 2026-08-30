"""Configuration versionnée de l'environnement, de la récompense et du RL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

RACINE_PROJET = Path(__file__).resolve().parents[1]
CONFIG_ENTRAINEMENT = RACINE_PROJET / "config" / "entrainement.json"


@dataclass(frozen=True, slots=True)
class ConfigurationRecompense:
    poids_energie_pilotable: float = 2.0
    poids_inconfort: float = 0.25
    poids_progression_budget: float = 20.0
    bonus_survie_pas: float = 0.02
    penalite_non_servie: float = 50.0
    penalite_tache_inachevee: float = 10.0
    penalite_coupure: float = 150.0
    penalite_changement: float = 0.05
    penalite_action_invalide: float = 0.05
    bonus_date_cible: float = 150.0

    def __post_init__(self) -> None:
        if any(valeur < 0 for valeur in asdict(self).values()):
            raise ValueError("Les poids de récompense doivent être positifs ou nuls")


def charger_configuration(chemin: str | Path = CONFIG_ENTRAINEMENT) -> dict[str, Any]:
    contenu = json.loads(Path(chemin).read_text(encoding="utf-8"))
    sections = {"environnement", "recompense", "recherche", "dqn"}
    manquantes = sections.difference(contenu)
    if manquantes:
        raise ValueError(f"Sections de configuration manquantes : {sorted(manquantes)}")
    return contenu


def configuration_recompense(contenu: dict[str, Any]) -> ConfigurationRecompense:
    return ConfigurationRecompense(**contenu["recompense"])
