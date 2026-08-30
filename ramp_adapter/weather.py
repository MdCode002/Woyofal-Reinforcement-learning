"""Cache météo Dakar : Open-Meteo/ERA5 en ligne, lecture locale hors ligne."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
from math import cos, pi, sin
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from common import MeteoPas, Scenario

COORDONNEES_DAKAR = {"latitude": 14.7167, "longitude": -17.4677}
RACINE_PROJET = Path(__file__).resolve().parents[1]
CACHE_METEO_DEFAUT = RACINE_PROJET / "data" / "weather" / "cache" / "dakar_2018_2025.csv"
URL_PREVISION = "https://api.open-meteo.com/v1/forecast"


def generer_meteo_fixture(debut: datetime, nombre_pas: int, pas_minutes: int = 30) -> list[MeteoPas]:
    """Météo déterministe plausible réservée aux tests et à la démo hors ligne."""

    if debut.tzinfo is None:
        raise ValueError("debut doit contenir un fuseau horaire")
    resultat = []
    for index in range(nombre_pas):
        horodatage = debut + timedelta(minutes=index * pas_minutes)
        heure = horodatage.hour + horodatage.minute / 60
        cycle = sin(2 * pi * (heure - 9) / 24)
        temperature = 28.5 + 3.2 * cycle
        humidite = 72.0 - 12.0 * cycle
        rayonnement = max(0.0, 760.0 * cos(pi * (heure - 12.5) / 12.0))
        resultat.append(MeteoPas(horodatage, temperature, humidite, rayonnement))
    return resultat


def telecharger_meteo_dakar(date_debut: str, date_fin: str, destination: str | Path) -> Path:
    """Télécharge les variables horaires officielles et écrit un cache traçable."""

    parametres = {
        **COORDONNEES_DAKAR,
        "start_date": date_debut,
        "end_date": date_fin,
        "hourly": "temperature_2m,relative_humidity_2m,shortwave_radiation",
        "timezone": "UTC",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(parametres)
    with urlopen(url, timeout=60) as reponse:  # noqa: S310 - domaine construit en dur
        contenu = json.load(reponse)
    horaire = contenu["hourly"]
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as fichier:
        champs = ["horodatage", "temperature_exterieure_c", "humidite_pourcent", "rayonnement_w_m2"]
        writer = csv.DictWriter(fichier, fieldnames=champs)
        writer.writeheader()
        for valeurs in zip(
            horaire["time"], horaire["temperature_2m"],
            horaire["relative_humidity_2m"], horaire["shortwave_radiation"], strict=True,
        ):
            writer.writerow(dict(zip(champs, valeurs, strict=True)))
    metadata = {
        "source": "Open-Meteo Historical Weather API / ERA5",
        "url": url,
        "coordonnees": COORDONNEES_DAKAR,
        "periode": [date_debut, date_fin],
        "date_telechargement_utc": datetime.now(timezone.utc).isoformat(),
    }
    destination.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def lire_meteo_csv(chemin: str | Path, pas_minutes: int = 30) -> list[MeteoPas]:
    """Lit le cache horaire et l'interpole au pas thermique/environnement voulu."""

    points: list[MeteoPas] = []
    with Path(chemin).open(encoding="utf-8", newline="") as fichier:
        for ligne in csv.DictReader(fichier):
            horodatage = datetime.fromisoformat(ligne["horodatage"])
            if horodatage.tzinfo is None:
                horodatage = horodatage.replace(tzinfo=timezone.utc)
            points.append(MeteoPas(
                horodatage,
                float(ligne["temperature_exterieure_c"]),
                float(ligne["humidite_pourcent"]),
                float(ligne["rayonnement_w_m2"]),
            ))
    if not points or pas_minutes == 60:
        return points
    resultat: list[MeteoPas] = []
    facteur = 60 // pas_minutes
    for index, actuel in enumerate(points):
        suivant = points[min(index + 1, len(points) - 1)]
        for sous_index in range(facteur):
            poids = sous_index / facteur
            resultat.append(MeteoPas(
                actuel.horodatage + timedelta(minutes=sous_index * pas_minutes),
                actuel.temperature_exterieure_c * (1 - poids) + suivant.temperature_exterieure_c * poids,
                actuel.humidite_pourcent * (1 - poids) + suivant.humidite_pourcent * poids,
                actuel.rayonnement_w_m2 * (1 - poids) + suivant.rayonnement_w_m2 * poids,
            ))
    return resultat


def _interpoler_points_horaires(
    points: list[MeteoPas], pas_minutes: int = 30,
) -> list[MeteoPas]:
    if not points or pas_minutes == 60:
        return points
    resultat: list[MeteoPas] = []
    facteur = 60 // pas_minutes
    for index, actuel in enumerate(points):
        suivant = points[min(index + 1, len(points) - 1)]
        for sous_index in range(facteur):
            poids = sous_index / facteur
            resultat.append(MeteoPas(
                actuel.horodatage + timedelta(minutes=sous_index * pas_minutes),
                actuel.temperature_exterieure_c * (1 - poids)
                + suivant.temperature_exterieure_c * poids,
                actuel.humidite_pourcent * (1 - poids)
                + suivant.humidite_pourcent * poids,
                actuel.rayonnement_w_m2 * (1 - poids) + suivant.rayonnement_w_m2 * poids,
            ))
    return resultat


@lru_cache(maxsize=2)
def lire_prevision_dakar(pas_minutes: int = 30) -> list[MeteoPas]:
    """Lit la prévision courante de Dakar sans l'écrire dans le dépôt."""

    parametres = {
        **COORDONNEES_DAKAR,
        "hourly": "temperature_2m,relative_humidity_2m,shortwave_radiation",
        "timezone": "UTC",
        "forecast_days": 16,
        "past_days": 2,
    }
    with urlopen(URL_PREVISION + "?" + urlencode(parametres), timeout=8) as reponse:
        contenu = json.load(reponse)
    horaire = contenu["hourly"]
    points = [
        MeteoPas(
            datetime.fromisoformat(horodatage).replace(tzinfo=timezone.utc),
            float(temperature),
            float(humidite),
            max(0.0, float(rayonnement or 0.0)),
        )
        for horodatage, temperature, humidite, rayonnement in zip(
            horaire["time"], horaire["temperature_2m"],
            horaire["relative_humidity_2m"], horaire["shortwave_radiation"],
            strict=True,
        )
    ]
    return _interpoler_points_horaires(points, pas_minutes)


@lru_cache(maxsize=2)
def _climatologie_cache(
    chemin_resolu: str, pas_minutes: int,
) -> tuple[dict[tuple[int, int, int, int], tuple[float, float, float]], dict[tuple[int, int, int], tuple[float, float, float]]]:
    points = lire_meteo_csv(chemin_resolu, pas_minutes)
    detail: dict[tuple[int, int, int, int], list[tuple[float, float, float]]] = {}
    repli: dict[tuple[int, int, int], list[tuple[float, float, float]]] = {}
    for point in points:
        valeur = (
            point.temperature_exterieure_c,
            point.humidite_pourcent,
            point.rayonnement_w_m2,
        )
        detail.setdefault((
            point.horodatage.month, point.horodatage.day,
            point.horodatage.hour, point.horodatage.minute,
        ), []).append(valeur)
        repli.setdefault((
            point.horodatage.month, point.horodatage.hour, point.horodatage.minute,
        ), []).append(valeur)

    def moyenne(valeurs: list[tuple[float, float, float]]) -> tuple[float, float, float]:
        return tuple(sum(v[index] for v in valeurs) / len(valeurs) for index in range(3))

    return (
        {cle: moyenne(valeurs) for cle, valeurs in detail.items()},
        {cle: moyenne(valeurs) for cle, valeurs in repli.items()},
    )


def _meteo_climatologique(
    scenario: Scenario, chemin_cache: str | Path,
) -> list[MeteoPas]:
    chemin = Path(chemin_cache)
    if not chemin.exists():
        raise FileNotFoundError(
            f"Cache météo absent : {chemin}. Exécutez 'woyofal telecharger-meteo'."
        )
    detail, repli = _climatologie_cache(str(chemin.resolve()), scenario.pas_minutes)
    resultat = []
    for numero in range(scenario.nombre_pas_max):
        instant = (
            scenario.date_debut + timedelta(minutes=numero * scenario.pas_minutes)
        ).astimezone(timezone.utc)
        valeur = detail.get((instant.month, instant.day, instant.hour, instant.minute))
        valeur = valeur or repli[(instant.month, instant.hour, instant.minute)]
        resultat.append(MeteoPas(instant, *valeur))
    return resultat


@lru_cache(maxsize=2)
def _index_cache(chemin_resolu: str, pas_minutes: int) -> dict[datetime, MeteoPas]:
    points = lire_meteo_csv(chemin_resolu, pas_minutes)
    return {
        point.horodatage.astimezone(timezone.utc): point
        for point in points
    }


def meteo_avec_source_pour_scenario(
    scenario: Scenario,
    chemin_cache: str | Path = CACHE_METEO_DEFAUT,
) -> tuple[list[MeteoPas], str]:
    """Retourne la météo du scénario, réelle si elle est déclarée comme telle.

    La fixture synthétique reste réservée à la démonstration et aux tests. Un
    scénario d'entraînement ou d'évaluation ne bascule jamais silencieusement
    vers une fausse météo si le cache historique est absent.
    """

    if scenario.source_meteo == "fixture_deterministe":
        return (
            generer_meteo_fixture(
                scenario.date_debut, scenario.nombre_pas_max, scenario.pas_minutes
            ),
            "fixture_deterministe",
        )
    if scenario.source_meteo == "auto_dakar":
        climatologie = _meteo_climatologique(scenario, chemin_cache)
        try:
            prevision = {
                point.horodatage.astimezone(timezone.utc): point
                for point in lire_prevision_dakar(scenario.pas_minutes)
            }
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return climatologie, "climatologie_dakar_2018_2025_hors_ligne"
        resultat = [
            prevision.get(point.horodatage.astimezone(timezone.utc), point)
            for point in climatologie
        ]
        nombre_previsions = sum(
            point.horodatage.astimezone(timezone.utc) in prevision
            for point in climatologie
        )
        source = (
            "prevision_open_meteo_puis_climatologie"
            if nombre_previsions else "climatologie_dakar_2018_2025"
        )
        return resultat, source
    chemin = Path(chemin_cache)
    if not chemin.exists():
        raise FileNotFoundError(
            f"Cache météo absent : {chemin}. Exécutez 'woyofal telecharger-meteo'."
        )
    index = _index_cache(str(chemin.resolve()), scenario.pas_minutes)
    resultat: list[MeteoPas] = []
    for numero in range(scenario.nombre_pas_max):
        instant = (
            scenario.date_debut + timedelta(minutes=numero * scenario.pas_minutes)
        ).astimezone(timezone.utc)
        try:
            resultat.append(index[instant])
        except KeyError as erreur:
            raise ValueError(
                f"Le cache météo ne couvre pas {instant.isoformat()} pour {scenario.identifiant_foyer}"
            ) from erreur
    return resultat, "cache_open_meteo_era5"


def meteo_pour_scenario(
    scenario: Scenario,
    chemin_cache: str | Path = CACHE_METEO_DEFAUT,
) -> list[MeteoPas]:
    """Compatibilité : retourne uniquement les points météo résolus."""

    return meteo_avec_source_pour_scenario(scenario, chemin_cache)[0]
