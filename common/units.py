"""Unités et conversions communes à tous les modules."""

PAS_DECISION_MINUTES = 30
SOUS_PAS_THERMIQUE_MINUTES = 5
MINUTES_PAR_HEURE = 60
HEURES_PAR_JOUR = 24
WATTS_PAR_KILOWATT = 1_000


def convertir_en_kwh(puissance_w: float, duree_minutes: float) -> float:
    if puissance_w < 0:
        raise ValueError("puissance_w doit être positive ou nulle")
    if duree_minutes <= 0:
        raise ValueError("duree_minutes doit être strictement positive")
    return puissance_w * duree_minutes / MINUTES_PAR_HEURE / WATTS_PAR_KILOWATT


def convertir_en_watts(energie_kwh: float, duree_minutes: float) -> float:
    if energie_kwh < 0 or duree_minutes <= 0:
        raise ValueError("L'énergie et la durée sont invalides")
    return energie_kwh * WATTS_PAR_KILOWATT * MINUTES_PAR_HEURE / duree_minutes

