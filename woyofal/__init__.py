"""Compteur Woyofal, simulation, CLI et API locale."""

from .meter import (
    CompteurWoyofal,
    ResultatCompteur,
    WoyofalMeter,
    convertir_fcfa_en_kwh,
    convertir_kwh_en_fcfa,
)

__version__ = "1.1.0"

__all__ = [
    "CompteurWoyofal",
    "ResultatCompteur",
    "WoyofalMeter",
    "convertir_fcfa_en_kwh",
    "convertir_kwh_en_fcfa",
    "__version__",
]
