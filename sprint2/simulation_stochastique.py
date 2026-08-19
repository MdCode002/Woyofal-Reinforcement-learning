"""
SPRINT M2 - Profils stochastiques
Objectifs couverts :
  1. Variabilité sur horaires (random_var_w), durées (time_fraction_random_variability)
     et puissances (thermal_p_var) - déjà injectée via catalogue.py
  2. Plusieurs journées différentes pour un même foyer (NUM_DAYS profils stochastiques)
  3. Plusieurs types de ménages/scénarios, export dans un format commun (CSV long format)
  4. Vérification de l'agrégation des profils au pas de décision de 30 minutes
"""

from unittest.mock import patch
import numpy as np
import pandas as pd
from ramp import Appliance, UseCase, User

from catalogue import SCENARIOS

NUM_DAYS = 7          # plusieurs journées différentes par foyer
STEP_MIN = 30          # pas de décision à vérifier (minutes)
OUTPUT_CSV = "profils_stochastiques.csv"


def create_appliance_from_catalog(user, entry):
    """Construit un Appliance RAMP avec variabilité horaire, de durée et de puissance."""
    app = Appliance(
        user,
        number=entry["quantity"],
        power=entry["power_W"],
        num_windows=1,
        func_time=entry["func_time_min"],
        time_fraction_random_variability=entry["time_var"],   # variabilité DUREE
        thermal_p_var=entry["power_var"],                     # variabilité PUISSANCE
        name=entry["name"],
    )
    app.windows(
        window_1=[entry["window_start_min"], entry["window_end_min"]],
        random_var_w=entry["random_var"],                     # variabilité HORAIRES
    )
    return app


def simulate_scenario(scenario_name, catalog, num_days=NUM_DAYS, seed=None):
    """Simule num_days profils stochastiques (1 min) pour un scénario de foyer donné."""
    if seed is not None:
        np.random.seed(seed)

    user = User(scenario_name, 1)
    for entry in catalog:
        create_appliance_from_catalog(user, entry)

    use_case = UseCase(users=[user], date_start="2026-01-01")
    with patch("builtins.input", return_value="1"):
        use_case.initialize(num_days=num_days)

    profiles = use_case.generate_daily_load_profiles(flat=False)
    profiles = np.array(profiles).reshape(num_days, 1440)
    return profiles


# ==========================================================
# 1 & 2. GENERATION : plusieurs scénarios x plusieurs journées
# ==========================================================
all_records = []           # format long, résolution native 1 minute
summary_rows = []

for i, (scenario_name, catalog) in enumerate(SCENARIOS.items()):
    profiles = simulate_scenario(scenario_name, catalog, seed=42 + i)

    for day_idx in range(NUM_DAYS):
        day_profile = profiles[day_idx]
        kwh_jour = day_profile.sum() / 60000.0
        pmax = day_profile.max()
        summary_rows.append(
            {"scenario": scenario_name, "jour": day_idx + 1, "kWh": kwh_jour, "Pmax_W": pmax}
        )
        for minute in range(1440):
            all_records.append(
                {
                    "scenario": scenario_name,
                    "jour": day_idx + 1,
                    "minute": minute,
                    "power_W": day_profile[minute],
                }
            )

df_summary = pd.DataFrame(summary_rows)
df_long = pd.DataFrame(all_records)

print("=== VARIABILITE ENTRE JOURNEES (meme foyer) ===")
for scenario_name in SCENARIOS:
    sub = df_summary[df_summary["scenario"] == scenario_name]
    print(
        f"{scenario_name:15s} -> kWh/jour: min={sub['kWh'].min():.2f} "
        f"max={sub['kWh'].max():.2f} moyenne={sub['kWh'].mean():.2f} "
        f"ecart-type={sub['kWh'].std():.2f}"
    )

print("\n=== COMPARAISON DES SCENARIOS / TYPES DE MENAGES ===")
print(
    df_summary.groupby("scenario")["kWh"]
    .agg(["mean", "std", "min", "max"])
    .round(2)
    .to_string()
)

# ==========================================================
# 3. EXPORT DANS UN FORMAT COMMUN (long format, 1 ligne = 1 minute)
# ==========================================================
df_long.to_csv(OUTPUT_CSV, index=False)
print(f"\nExport format commun : {OUTPUT_CSV} ({len(df_long)} lignes)")
print(df_long.head(3).to_string(index=False))

# ==========================================================
# 4. VERIFICATION DE L'AGREGATION AU PAS DE 30 MINUTES
# ==========================================================
print(f"\n=== VERIFICATION AGREGATION AU PAS DE {STEP_MIN} MIN ===")

df_long["bloc_30min"] = df_long["minute"] // STEP_MIN

df_30min = (
    df_long.groupby(["scenario", "jour", "bloc_30min"])["power_W"]
    .mean()                       # puissance moyenne appelée sur le bloc de 30 min
    .reset_index()
)

# Energie 30 min (Wh) = puissance moyenne (W) x 0.5 h
df_30min["Wh_bloc"] = df_30min["power_W"] * (STEP_MIN / 60.0)

# Comparaison : énergie totale (kWh) recalculée à 30 min vs résolution native 1 min
kwh_1min = df_long.groupby(["scenario", "jour"])["power_W"].sum() / 60000.0
kwh_30min = df_30min.groupby(["scenario", "jour"])["Wh_bloc"].sum() / 1000.0

df_check = pd.DataFrame({"kWh_1min": kwh_1min, "kWh_30min": kwh_30min})
df_check["ecart_pct"] = (
    (df_check["kWh_30min"] - df_check["kWh_1min"]).abs() / df_check["kWh_1min"] * 100
)

print(df_check.round(4).to_string())

ecart_max = df_check["ecart_pct"].max()
print(f"\nEcart maximal 1min vs 30min : {ecart_max:.4f} %")
if ecart_max < 0.5:
    print("CONTROLE VALIDE : l'agregation au pas de 30 minutes conserve l'energie.")
else:
    print("ATTENTION : écart significatif détecté dans l'agrégation.")

df_30min.to_csv("profils_agreges_30min.csv", index=False)
print("Export agrege : profils_agreges_30min.csv")
