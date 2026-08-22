"""
SPRINT M2+M3 - Domain randomization
Module de tirage aléatoire des scénarios de foyer.

Paramètres randomisés par scénario :
  - appareils possédés (tirage Bernoulli par appareil selon probabilité de possession)
  - puissances (jitter multiplicatif autour de la puissance nominale)
  - horaires (décalage aléatoire des fenêtres d'usage)
  - occupation (taille du foyer -> intensité d'usage éclairage/TV/ventilateur)
  - météo (température moyenne/amplitude, humidité moyenne/amplitude, avec
    décalage saisonnier dépendant de la date cible)
  - R, C (modèle thermique simplifié RC du logement)
  - COP (coefficient de performance du froid : frigo/climatiseur)
  - crédit initial (FCFA)
  - date cible (jour de l'année simulé -> détermine la saison)

IMPORTANT - séparation train/val vs test :
  Le jeu train/validation est tiré avec un générateur (np.random.default_rng)
  initialisé avec SEED_TRAIINVAL. Le jeu de test est tiré avec un générateur
  totalement distinct, initialisé avec SEED_TEST, jamais utilisé ailleurs
  dans le code. Les deux flux ne partagent aucun état -> le test est
  garanti "jamais vu" au sens de la génération aléatoire.
"""

import numpy as np
import pandas as pd

SEED_TRAINVAL = 12345
SEED_TEST = 987654321  # flux totalement disjoint, réservé au test

# --------------------------------------------------------------------
# POOL D'APPAREILS - superset dans lequel chaque foyer tire un sous-ensemble
# --------------------------------------------------------------------
POOL_APPAREILS = [
    # name, power_W, base_quantity, window_start, window_end, func_time,
    # prob_possession, occupancy_sensitive, thermal_duration (durée sensible
    # à la chaleur), cop_sensitive (puissance électrique liée au COP -
    # uniquement les machines à compression : frigo/clim), flexible
    dict(name="TV", power_W=100.0, quantity=1, window_start_min=1080, window_end_min=1380,
         func_time_min=240, prob_possession=0.90, occupancy_sensitive=True,
         thermal_duration=False, cop_sensitive=False, flexible=False),
    dict(name="Eclairage_LED", power_W=12.0, quantity=5, window_start_min=1080, window_end_min=1380,
         func_time_min=300, prob_possession=0.99, occupancy_sensitive=True,
         thermal_duration=False, cop_sensitive=False, flexible=False),
    dict(name="Ventilateur", power_W=50.0, quantity=2, window_start_min=720, window_end_min=1200,
         func_time_min=480, prob_possession=0.80, occupancy_sensitive=True,
         thermal_duration=True, cop_sensitive=False, flexible=True),
    dict(name="Refrigerateur", power_W=150.0, quantity=1, window_start_min=0, window_end_min=1440,
         func_time_min=600, prob_possession=0.85, occupancy_sensitive=False,
         thermal_duration=True, cop_sensitive=True, flexible=False),
    dict(name="Fer_Repasser", power_W=1200.0, quantity=1, window_start_min=480, window_end_min=600,
         func_time_min=30, prob_possession=0.70, occupancy_sensitive=False,
         thermal_duration=False, cop_sensitive=False, flexible=True),
    dict(name="Pompe_Eau", power_W=750.0, quantity=1, window_start_min=600, window_end_min=780,
         func_time_min=45, prob_possession=0.40, occupancy_sensitive=False,
         thermal_duration=False, cop_sensitive=False, flexible=True),
    dict(name="Chauffe_Eau", power_W=1500.0, quantity=1, window_start_min=330, window_end_min=450,
         func_time_min=60, prob_possession=0.55, occupancy_sensitive=False,
         thermal_duration=False, cop_sensitive=False, flexible=False),
    dict(name="Climatiseur", power_W=1000.0, quantity=1, window_start_min=1260, window_end_min=1440,
         func_time_min=180, prob_possession=0.25, occupancy_sensitive=False,
         thermal_duration=True, cop_sensitive=True, flexible=False),
    dict(name="Veille_Divers", power_W=15.0, quantity=1, window_start_min=0, window_end_min=1440,
         func_time_min=1440, prob_possession=0.95, occupancy_sensitive=False,
         thermal_duration=False, cop_sensitive=False, flexible=False),
]

# Constantes du modèle thermique simplifié (illustratif, pas une simulation
# de physique du bâtiment complète)
T_CONFORT_C = 26.0
COP_REFERENCE = 3.0


def _jitter(rng, base, pct):
    """Applique un facteur multiplicatif aléatoire dans [1-pct, 1+pct]."""
    return base * (1.0 + rng.uniform(-pct, pct))


def _sample_date_cible(rng, year=2026):
    """Tire une date cible dans l'année -> détermine la saison simulée."""
    day_of_year = rng.integers(1, 366)
    date = pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=int(day_of_year) - 1)
    return date


def _saison_depuis_date(date):
    """Saison chaude à Dakar : environ mars à juin (simplification)."""
    return "Chaude" if date.month in (3, 4, 5, 6) else "Fraiche"


def sample_meteo(rng, date):
    """Randomise la météo journalière, avec décalage selon la saison de la date cible."""
    saison = _saison_depuis_date(date)
    decalage_T = rng.uniform(2.0, 5.0) if saison == "Chaude" else rng.uniform(-1.5, 1.0)
    T_mean = 27.5 + decalage_T + rng.normal(0, 0.8)
    T_amp = max(1.0, 3.5 + rng.normal(0, 0.7))
    H_mean = np.clip(72.5 - decalage_T * 2 + rng.normal(0, 3), 30, 95)
    H_amp = max(2.0, 12.5 + rng.normal(0, 2))
    return {"T_mean": T_mean, "T_amp": T_amp, "H_mean": H_mean, "H_amp": H_amp, "saison": saison}


def sample_rc_cop(rng):
    """Randomise les paramètres du modèle thermique simplifié du logement."""
    R = rng.uniform(15.0, 40.0)     # résistance thermique (indice arbitraire, + grand = mieux isolé)
    C = rng.uniform(500.0, 2500.0)  # capacité thermique (indice arbitraire, + grand = + d'inertie)
    COP = rng.uniform(2.0, 4.5)     # coefficient de performance frigo/clim
    return {"R": R, "C": C, "COP": COP}


def facteurs_thermiques(meteo, rc_cop):
    """Traduit meteo + R/C/COP en 2 facteurs appliqués aux appareils 'cooling_appliance' :
    - facteur_duree : agit sur func_time (durée de fonctionnement/duty cycle)
    - facteur_puissance : agit sur power_W (COP plus faible -> plus de puissance électrique
      nécessaire pour la même charge thermique à évacuer)
    Modèle volontairement simplifié (illustratif) : Q ~ deltaT / R ; P_elec = Q / COP ;
    l'inertie thermique C amortit l'amplitude journalière effective.
    """
    tau_h = (rc_cop["R"] * rc_cop["C"]) / 5000.0  # constante de temps (h), échelle arbitraire
    amplitude_effective = meteo["T_amp"] / (1.0 + tau_h / 12.0)
    T_ressentie = meteo["T_mean"] + 0.5 * amplitude_effective

    charge_thermique = max(0.0, T_ressentie - T_CONFORT_C) / rc_cop["R"]
    facteur_duree = 1.0 + np.clip(charge_thermique * 8.0, 0.0, 1.6)
    facteur_puissance = np.clip(COP_REFERENCE / rc_cop["COP"], 0.6, 2.0)

    return {"facteur_duree": facteur_duree, "facteur_puissance": facteur_puissance, "tau_h": tau_h}


def sample_household(rng, scenario_id, year=2026):
    """Tire un scénario de foyer complet (appareils, horaires, occupation,
    météo, thermique, crédit, date cible)."""
    date_cible = _sample_date_cible(rng, year=year)
    meteo = sample_meteo(rng, date_cible)
    rc_cop = sample_rc_cop(rng)
    therm = facteurs_thermiques(meteo, rc_cop)

    occupation = int(rng.integers(1, 9))  # 1 à 8 personnes
    intensite_occupation = np.clip(0.6 + 0.12 * occupation, 0.6, 1.8)

    credit_initial = float(rng.uniform(1000, 40000))

    appareils = []
    for base in POOL_APPAREILS:
        possede = rng.random() < base["prob_possession"]
        if not possede:
            continue

        entry = dict(base)
        entry["power_W"] = round(_jitter(rng, base["power_W"], 0.15), 1)
        entry["quantity"] = max(1, int(round(_jitter(rng, base["quantity"], 0.3))))

        decalage = rng.integers(-45, 46)
        entry["window_start_min"] = int(np.clip(base["window_start_min"] + decalage, 0, 1439))
        entry["window_end_min"] = int(np.clip(base["window_end_min"] + decalage, entry["window_start_min"] + 5, 1440))

        func_time = base["func_time_min"]
        if entry["occupancy_sensitive"]:
            func_time *= intensite_occupation
        if entry["thermal_duration"]:
            func_time *= therm["facteur_duree"]
        if entry["cop_sensitive"]:
            entry["power_W"] *= therm["facteur_puissance"]
        entry["func_time_min"] = int(np.clip(func_time, 5, entry["window_end_min"] - entry["window_start_min"]))

        entry["random_var"] = round(float(rng.uniform(0.08, 0.22)), 3)
        entry["time_var"] = round(float(rng.uniform(0.08, 0.22)), 3)
        entry["power_var"] = round(float(rng.uniform(0.02, 0.15)), 3)

        appareils.append(entry)

    return {
        "scenario_id": scenario_id,
        "date_cible": date_cible.strftime("%Y-%m-%d"),
        "saison": meteo["saison"],
        "occupation": occupation,
        "credit_initial_FCFA": round(credit_initial, 0),
        "T_mean": round(meteo["T_mean"], 2),
        "T_amp": round(meteo["T_amp"], 2),
        "H_mean": round(meteo["H_mean"], 1),
        "H_amp": round(meteo["H_amp"], 1),
        "R": round(rc_cop["R"], 2),
        "C": round(rc_cop["C"], 1),
        "COP": round(rc_cop["COP"], 2),
        "facteur_duree_thermique": round(therm["facteur_duree"], 3),
        "facteur_puissance_thermique": round(therm["facteur_puissance"], 3),
        "appareils": appareils,
        "nb_appareils": len(appareils),
    }


def generer_jeu_scenarios(n_scenarios, rng, prefix, year=2026):
    return [sample_household(rng, f"{prefix}_{i:04d}", year=year) for i in range(n_scenarios)]
