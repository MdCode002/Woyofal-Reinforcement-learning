"""Unités et conversions communes fixées par M1."""

PAS_DECISION_MINUTES = 30
MINUTES_PAR_HEURE = 60
WATTS_PAR_KILOWATT = 1_000


def convertir_en_kwh(puissance_w: float, duree_minutes: int) -> float:
    """Convertit une puissance constante en énergie selon la convention commune."""

    if puissance_w < 0:
        raise ValueError("puissance_w doit être positive ou nulle")
    if duree_minutes <= 0:
        raise ValueError("duree_minutes doit être strictement positive")
    return puissance_w * duree_minutes / MINUTES_PAR_HEURE / WATTS_PAR_KILOWATT

