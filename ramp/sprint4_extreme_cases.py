"""
SPRINT M2+M3 - Cas extremes de domain randomization
Construit 4 scenarios explicitement forces aux limites du domaine :
  - Chaleur_Extreme     : T tres elevee, isolation mediocre, COP degrade
  - Credit_Faible       : credit initial quasi nul (risque de coupure)
  - Consommation_Forte  : gros foyer, tous les appareils, forte puissance
  - Historique_Perturbe : releves compteur corrompus (trous, pics, valeurs
                           aberrantes) - utile pour tester la robustesse
                           d'un modele de detection d'anomalies en aval
"""

from unittest.mock import patch
import random
import numpy as np
import pandas as pd
from ramp import Appliance, UseCase, User

from src.domain_randomization import POOL_APPAREILS, T_CONFORT_C, COP_REFERENCE

NUM_DAYS = 30
TARIF_FCFA_PAR_KWH = 100.0


def build_scenario_force(scenario_id, date_cible, appareils_forces, credit_initial,
                          T_mean, T_amp, H_mean, H_amp, R, C, COP, saison):
    return {
        "scenario_id": scenario_id,
        "date_cible": date_cible,
        "saison": saison,
        "credit_initial_FCFA": credit_initial,
        "T_mean": T_mean, "T_amp": T_amp, "H_mean": H_mean, "H_amp": H_amp,
        "R": R, "C": C, "COP": COP,
        "appareils": appareils_forces,
        "nb_appareils": len(appareils_forces),
    }


def appareils_from_pool(noms, power_scale=1.0, func_time_scale=1.0):
    """Sélectionne des appareils du pool par nom, avec mise à l'échelle
    optionnelle de la puissance et de la durée (pour forcer un cas extrême)."""
    out = []
    for base in POOL_APPAREILS:
        if base["name"] not in noms:
            continue
        entry = dict(base)
        entry["power_W"] = round(base["power_W"] * power_scale, 1)
        entry["func_time_min"] = int(min(
            base["func_time_min"] * func_time_scale,
            entry["window_end_min"] - entry["window_start_min"],
        ))
        entry["random_var"] = 0.15
        entry["time_var"] = 0.15
        entry["power_var"] = 0.08
        out.append(entry)
    return out


# ==========================================================
# CAS 1 - CHALEUR EXTREME
# ==========================================================
scenario_chaleur = build_scenario_force(
    "extreme_chaleur_extreme",
    date_cible="2026-05-15",         # coeur de la saison chaude à Dakar
    appareils_forces=appareils_from_pool(
        ["TV", "Eclairage_LED", "Ventilateur", "Refrigerateur", "Climatiseur", "Veille_Divers"],
        power_scale=1.05,
        func_time_scale=1.4,          # usage prolongé du fait de la chaleur
    ),
    credit_initial=25000.0,
    T_mean=38.0, T_amp=5.0, H_mean=55.0, H_amp=10.0,  # canicule, air sec
    R=14.0,    # logement mal isolé (faible R -> forte déperdition/gain thermique)
    C=500.0,   # faible inertie thermique -> réagit vite à la chaleur extérieure
    COP=2.0,   # climatiseur vieillissant/peu performant
    saison="Chaude",
)

# ==========================================================
# CAS 2 - CREDIT FAIBLE
# ==========================================================
scenario_credit = build_scenario_force(
    "extreme_credit_faible",
    date_cible="2026-02-10",
    appareils_forces=appareils_from_pool(
        ["TV", "Eclairage_LED", "Refrigerateur", "Veille_Divers"],
        power_scale=1.0,
        func_time_scale=1.0,
    ),
    credit_initial=350.0,   # quasi épuisé dès le départ (~3.5 kWh à 100 FCFA/kWh)
    T_mean=26.5, T_amp=3.0, H_mean=73.0, H_amp=10.0,
    R=25.0, C=1200.0, COP=3.0,
    saison="Fraiche",
)

# ==========================================================
# CAS 3 - CONSOMMATION FORTE
# ==========================================================
scenario_forte = build_scenario_force(
    "extreme_consommation_forte",
    date_cible="2026-05-01",
    appareils_forces=appareils_from_pool(
        ["TV", "Eclairage_LED", "Ventilateur", "Refrigerateur", "Fer_Repasser",
         "Pompe_Eau", "Chauffe_Eau", "Climatiseur", "Veille_Divers"],
        power_scale=1.25,     # gros équipements, forte puissance
        func_time_scale=1.3,  # grand foyer, usage intensif
    ),
    credit_initial=60000.0,
    T_mean=31.0, T_amp=4.0, H_mean=65.0, H_amp=10.0,
    R=18.0, C=900.0, COP=2.5,
    saison="Chaude",
)


def simuler(scenario, num_days=NUM_DAYS, seed=0):
    random.seed(seed)     # RAMP utilise le module 'random' stdlib en interne
    np.random.seed(seed)  # gardé par précaution / compatibilité numpy
    user = User(scenario["scenario_id"], 1)
    for entry in scenario["appareils"]:
        app = Appliance(
            user, number=entry["quantity"], power=entry["power_W"], num_windows=1,
            func_time=entry["func_time_min"],
            time_fraction_random_variability=entry["time_var"],
            thermal_p_var=entry["power_var"], name=entry["name"],
        )
        app.windows(
            window_1=[entry["window_start_min"], entry["window_end_min"]],
            random_var_w=entry["random_var"],
        )
    use_case = UseCase(users=[user], date_start=scenario["date_cible"])
    with patch("builtins.input", return_value="1"):
        use_case.initialize(num_days=num_days)
    profiles = use_case.generate_daily_load_profiles(flat=False)
    return np.array(profiles).reshape(num_days, 1440)


print("=== CAS EXTREMES 1-3 : SIMULATION ET CONTROLE ===")
resultats_extremes = []
profils_extremes = {}

for scenario, seed in ((scenario_chaleur, 500001), (scenario_credit, 500002), (scenario_forte, 500003)):
    profils = simuler(scenario, seed=seed)
    profils_extremes[scenario["scenario_id"]] = profils
    kwh_jour = profils.sum(axis=1) / 60000.0
    kwh_mois = kwh_jour.sum()
    cout_mois_fcfa = kwh_mois * TARIF_FCFA_PAR_KWH
    jour_epuisement = None
    solde = scenario["credit_initial_FCFA"]
    cumul = 0.0
    for j, kwh in enumerate(kwh_jour, start=1):
        cumul += kwh * TARIF_FCFA_PAR_KWH
        if cumul >= solde and jour_epuisement is None:
            jour_epuisement = j

    resultats_extremes.append(
        {
            "scenario_id": scenario["scenario_id"],
            "kWh_mois": round(kwh_mois, 2),
            "Pmax_W": round(profils.max(), 1),
            "credit_initial_FCFA": scenario["credit_initial_FCFA"],
            "cout_mois_estime_FCFA": round(cout_mois_fcfa, 0),
            "jour_epuisement_credit": jour_epuisement if jour_epuisement else "non atteint sur le mois",
        }
    )

df_extremes = pd.DataFrame(resultats_extremes)
print(df_extremes.to_string(index=False))

print(
    "\nLecture attendue :\n"
    "  - Chaleur_Extreme    : forte conso, tirée par le climatiseur (isolation faible, COP dégradé)\n"
    "  - Credit_Faible      : crédit épuisé très tôt dans le mois (coupure simulée)\n"
    "  - Consommation_Forte : conso mensuelle la plus élevée du lot, gros Pmax\n"
)

# ==========================================================
# CAS 4 - HISTORIQUE COMPTEUR PERTURBE
# ==========================================================
print("=== CAS EXTREME 4 : HISTORIQUE COMPTEUR PERTURBE ===")

# On part d'un historique "propre" (Foyer_Standard-like) simulé sur 30 jours,
# puis on injecte des anomalies representatives de ce qu'un systeme de
# detection devra reperer (releves manquants, pics improbables, valeurs
# negatives, journee a zero suspecte).
scenario_propre = build_scenario_force(
    "extreme_historique_base",
    date_cible="2026-03-01",
    appareils_forces=appareils_from_pool(
        ["TV", "Eclairage_LED", "Ventilateur", "Refrigerateur", "Fer_Repasser", "Chauffe_Eau", "Veille_Divers"]
    ),
    credit_initial=20000.0,
    T_mean=28.0, T_amp=3.5, H_mean=70.0, H_amp=10.0,
    R=25.0, C=1200.0, COP=3.0,
    saison="Chaude",
)
profils_propre = simuler(scenario_propre, seed=500004)
kwh_jour_propre = profils_propre.sum(axis=1) / 60000.0

rng_perturb = np.random.default_rng(777)
kwh_jour_perturbe = kwh_jour_propre.copy()
anomalies = []

# (a) 2 relevés manquants (NaN) - panne de télérelevé
jours_manquants = rng_perturb.choice(NUM_DAYS, size=2, replace=False)
for j in jours_manquants:
    kwh_jour_perturbe[j] = np.nan
    anomalies.append({"jour": int(j) + 1, "type": "releve_manquant", "valeur_kWh": None})

# (b) 1 pic improbable (x5 à x8 la conso habituelle - fraude/dérivation possible)
jour_pic = rng_perturb.choice([j for j in range(NUM_DAYS) if j not in jours_manquants])
facteur_pic = rng_perturb.uniform(5, 8)
kwh_jour_perturbe[jour_pic] = kwh_jour_propre[jour_pic] * facteur_pic
anomalies.append({"jour": int(jour_pic) + 1, "type": "pic_improbable", "valeur_kWh": round(kwh_jour_perturbe[jour_pic], 2)})

# (c) 1 journée à zéro suspecte (compteur figé / manipulation)
candidats = [j for j in range(NUM_DAYS) if j not in jours_manquants and j != jour_pic]
jour_zero = rng_perturb.choice(candidats)
kwh_jour_perturbe[jour_zero] = 0.0
anomalies.append({"jour": int(jour_zero) + 1, "type": "conso_zero_suspecte", "valeur_kWh": 0.0})

# (d) 1 valeur négative (incohérence de relevé, delta mal calculé)
candidats = [j for j in candidats if j != jour_zero]
jour_negatif = rng_perturb.choice(candidats)
kwh_jour_perturbe[jour_negatif] = -abs(rng_perturb.uniform(0.5, 2.0))
anomalies.append({"jour": int(jour_negatif) + 1, "type": "valeur_negative", "valeur_kWh": round(kwh_jour_perturbe[jour_negatif], 2)})

df_historique = pd.DataFrame(
    {
        "jour": np.arange(1, NUM_DAYS + 1),
        "kWh_jour_propre": kwh_jour_propre.round(3),
        "kWh_jour_perturbe": kwh_jour_perturbe.round(3),
    }
)
df_anomalies = pd.DataFrame(anomalies).sort_values("jour")

print(df_historique.to_string(index=False))
print("\nAnomalies injectées :")
print(df_anomalies.to_string(index=False))

df_historique.to_csv("extreme_historique_perturbe.csv", index=False)
df_anomalies.to_csv("extreme_historique_anomalies.csv", index=False)
df_extremes.to_csv("extreme_cas_resume.csv", index=False)

print("\nExports : extreme_historique_perturbe.csv, extreme_historique_anomalies.csv, extreme_cas_resume.csv")
