"""Adaptateur local autour de la bibliothèque officielle :mod:`ramp`.

Le nom du paquet est volontairement ``ramp_adapter`` : créer un paquet local
``ramp`` masquerait la dépendance ``rampdemand`` installée.
"""

from .catalogue import charger_catalogue, construire_appareil
from .generator import generer_profils_ramp
from .scenarios import (
    generer_jeux_scenarios,
    generer_partition_scenarios,
    generer_profils_lisibles,
)
from .weather import (
    CACHE_METEO_DEFAUT,
    generer_meteo_fixture,
    lire_meteo_csv,
    meteo_avec_source_pour_scenario,
    meteo_pour_scenario,
    telecharger_meteo_dakar,
)

__all__ = [
    "charger_catalogue",
    "construire_appareil",
    "generer_profils_ramp",
    "generer_jeux_scenarios",
    "generer_partition_scenarios",
    "generer_profils_lisibles",
    "generer_meteo_fixture",
    "lire_meteo_csv",
    "meteo_avec_source_pour_scenario",
    "meteo_pour_scenario",
    "telecharger_meteo_dakar",
    "CACHE_METEO_DEFAUT",
]
