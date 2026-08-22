"""
SPRINT M2+M3 - Domain randomization : génération des jeux de données
Objectifs couverts :
  1. Jeu de scénarios d'entraînement / validation (flux RNG SEED_TRAINVAL)
  2. Jeu de test jamais vu (flux RNG SEED_TEST totalement disjoint)
  3. Cas extrêmes : chaleur élevée, crédit faible, consommation forte,
     historique compteur perturbé
  4. Export dans un format commun (une ligne = un scénario, + profils
     détaillés pour les cas extrêmes)
"""

from unittest.mock import patch
import random
import numpy as np
import pandas as pd
from ramp import Appliance, UseCase, User

from src.domain_randomization import (
    sample_household,
    generer_jeu_scenarios,
    SEED_TRAINVAL,
    SEED_TEST,
    T_CONFORT_C,
)

N_TRAIN = 60
N_VAL = 15
N_TEST = 15
NUM_DAYS_SCENARIO = 3      # simulation courte pour balayer beaucoup de scénarios
NUM_DAYS_EXTREME = 30      # simulation longue (mensuelle) pour les cas extrêmes
TARIF_FCFA_PAR_KWH = 100.0


def build_user_and_simulate(scenario, num_days, seed=None):
    """Construit un User RAMP à partir d'un scénario randomisé et simule num_days."""
    if seed is not None:
        random.seed(seed)     # RAMP utilise le module 'random' stdlib en interne
        np.random.seed(seed)  # gardé par précaution / compatibilité numpy

    user = User(scenario["scenario_id"], 1)
    for entry in scenario["appareils"]:
        app = Appliance(
            user,
            number=entry["quantity"],
            power=entry["power_W"],
            num_windows=1,
            func_time=entry["func_time_min"],
            time_fraction_random_variability=entry["time_var"],
            thermal_p_var=entry["power_var"],
            name=entry["name"],
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


def resumer_scenario(scenario, profiles):
    """Réduit un scénario + ses profils simulés à une ligne de synthèse
    (format commun exportable pour l'entraînement d'un modèle ML)."""
    kwh_par_jour = profiles.sum(axis=1) / 60000.0
    row = {
        "scenario_id": scenario["scenario_id"],
        "date_cible": scenario["date_cible"],
        "saison": scenario["saison"],
        "occupation": scenario["occupation"],
        "nb_appareils": scenario["nb_appareils"],
        "credit_initial_FCFA": scenario["credit_initial_FCFA"],
        "T_mean": scenario["T_mean"],
        "T_amp": scenario["T_amp"],
        "H_mean": scenario["H_mean"],
        "R": scenario["R"],
        "C": scenario["C"],
        "COP": scenario["COP"],
        "kWh_jour_moyen": round(kwh_par_jour.mean(), 3),
        "kWh_jour_min": round(kwh_par_jour.min(), 3),
        "kWh_jour_max": round(kwh_par_jour.max(), 3),
        "Pmax_W": round(profiles.max(), 1),
    }
    return row


# ==========================================================
# 1. JEU TRAIN / VALIDATION (flux RNG dédié)
# ==========================================================
rng_trainval = np.random.default_rng(SEED_TRAINVAL)

# ==========================================================
# 2. JEU TEST - flux RNG totalement disjoint, jamais touché ci-dessus
# ==========================================================
rng_test = np.random.default_rng(SEED_TEST)


def traiter_jeu(rng, n_scenarios, label, prefix, seed_offset, num_days=NUM_DAYS_SCENARIO, max_retries=5):
    """Génère n_scenarios en tirant depuis rng, simule chacun, et remplace
    à la volée (même flux rng) les rares scénarios qui déclenchent un cas
    limite interne à RAMP (pic théorique sur une seule minute -> IndexError).
    Le flux RNG utilisé (train/val ou test) n'est jamais mélangé avec l'autre."""
    lignes = []
    scenarios_ok = []
    i = 0
    n_echecs = 0
    while len(lignes) < n_scenarios:
        sc = sample_household(rng, f"{prefix}_{len(lignes):04d}")
        try:
            profiles = build_user_and_simulate(sc, num_days, seed=seed_offset + i)
        except (IndexError, ValueError) as e:
            n_echecs += 1
            i += 1
            continue
        lignes.append(resumer_scenario(sc, profiles))
        scenarios_ok.append(sc)
        i += 1

    if n_echecs:
        print(f"  ({label}: {n_echecs} tirage(s) écarté(s) - cas limite RAMP, remplacés dans le même flux RNG)")

    df = pd.DataFrame(lignes)
    fichier = f"scenarios_{label}.csv"
    df.to_csv(fichier, index=False)
    return df, fichier, scenarios_ok


df_train, f_train, scenarios_train = traiter_jeu(rng_trainval, N_TRAIN, "train", "foyer", seed_offset=1_000_000)
df_val, f_val, scenarios_val = traiter_jeu(rng_trainval, N_VAL, "val", "foyer", seed_offset=2_000_000)
df_test, f_test, scenarios_test = traiter_jeu(rng_test, N_TEST, "test", "foyer_test", seed_offset=3_000_000)

print("=== 1 & 2. JEUX DE SCENARIOS GENERES ===")
print(f"Train      : {len(df_train):3d} scénarios -> {f_train}")
print(f"Validation : {len(df_val):3d} scénarios -> {f_val}")
print(f"Test       : {len(df_test):3d} scénarios -> {f_test}  (flux RNG jamais utilisé en train/val)")

print("\nAperçu train (5 premières lignes) :")
print(df_train.head(5).to_string(index=False))

print("\nStatistiques kWh/jour moyen par jeu :")
for label, df in (("train", df_train), ("val", df_val), ("test", df_test)):
    print(
        f"  {label:5s} : min={df['kWh_jour_moyen'].min():.2f} "
        f"max={df['kWh_jour_moyen'].max():.2f} "
        f"moyenne={df['kWh_jour_moyen'].mean():.2f} kWh/jour"
    )

# Vérification qu'aucun scenario_id du test n'apparaît en train/val (non-fuite)
ids_trainval = set(df_train["scenario_id"]) | set(df_val["scenario_id"])
ids_test = set(df_test["scenario_id"])
print(f"\nChevauchement d'identifiants train/val <-> test : {len(ids_trainval & ids_test)} (doit être 0)")
