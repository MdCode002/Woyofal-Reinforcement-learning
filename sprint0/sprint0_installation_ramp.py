"""
SPRINT 0 - Donnees / RAMP
Objectifs couverts :
  1. Installer RAMP et générer un premier foyer fictif sur 24h
  2. Déclarer TV, éclairage, ventilateur et réfrigérateur (puissance,
     fenêtres, durée)
  3. Vérifier que la sortie est récupérable APPAREIL PAR APPAREIL
     (appliance.daily_use après simulation) ET AGRÉGÉE (somme des users),
     avec un contrôle de cohérence entre les deux.

Installation (à faire une seule fois, dans le venv) :
    pip install rampdemand==0.5.0 "numpy<2" "pandas<2.2"
"""

from unittest.mock import patch
import numpy as np
import pandas as pd

# ==========================================================
# 0. VERIFICATION DE L'INSTALLATION
# ==========================================================
import ramp
from ramp import Appliance, UseCase, User

print("=== 0. VERIFICATION INSTALLATION RAMP ===")
print(f"RAMP importé avec succès depuis : {ramp.__file__}")

# ==========================================================
# 1. PREMIER FOYER FICTIF - declaration des 4 appareils
# ==========================================================
foyer = User("Foyer_Fictif_Sprint0", 1)

# Chaque appareil : puissance (W), quantité, fenêtre d'usage [debut,fin] en
# minutes depuis minuit, durée de fonctionnement (min/jour dans la fenêtre)
APPAREILS_SPRINT0 = [
    {
        "name": "TV",
        "power_W": 100.0,
        "quantity": 1,
        "window_start_min": 1080,  # 18:00
        "window_end_min": 1380,    # 23:00
        "func_time_min": 240,      # 4h d'usage effectif
        "random_var": 0.10,
    },
    {
        "name": "Eclairage_LED",
        "power_W": 12.0,
        "quantity": 5,
        "window_start_min": 1080,  # 18:00
        "window_end_min": 1380,    # 23:00
        "func_time_min": 300,      # 5h cumulées
        "random_var": 0.10,
    },
    {
        "name": "Ventilateur",
        "power_W": 50.0,
        "quantity": 2,
        "window_start_min": 720,   # 12:00
        "window_end_min": 1200,    # 20:00
        "func_time_min": 480,      # 8h cumulées
        "random_var": 0.15,
    },
    {
        "name": "Refrigerateur",
        "power_W": 150.0,
        "quantity": 1,
        "window_start_min": 0,     # disponible 24h/24
        "window_end_min": 1440,
        "func_time_min": 600,      # ~10h de marche compresseur (cycles)
        "random_var": 0.10,
    },
]

appliance_objects = {}  # nom -> objet Appliance RAMP (pour lecture ultérieure)
for entry in APPAREILS_SPRINT0:
    app = Appliance(
        foyer,
        number=entry["quantity"],
        power=entry["power_W"],
        num_windows=1,
        func_time=entry["func_time_min"],
        name=entry["name"],
    )
    app.windows(
        window_1=[entry["window_start_min"], entry["window_end_min"]],
        random_var_w=entry["random_var"],
    )
    appliance_objects[entry["name"]] = app

print("\n=== 1 & 2. CATALOGUE DU FOYER FICTIF ===")
df_catalogue = pd.DataFrame(APPAREILS_SPRINT0)
print(df_catalogue.to_string(index=False))

# ==========================================================
# 2. SIMULATION SUR 24H (1 jour)
# ==========================================================
use_case = UseCase(users=[foyer], date_start="2026-01-01")
with patch("builtins.input", return_value="1"):
    use_case.initialize()  # 1 jour par défaut

# Génère le profil agrégé du foyer (et, en interne, remplit .daily_use
# de chaque Appliance -> c'est ce qui permet la lecture par appareil ensuite)
profil_agrege = np.ravel(use_case.generate_daily_load_profiles())

# ==========================================================
# 3. RECUPERATION APPAREIL PAR APPAREIL
# ==========================================================
print("\n=== 3. RECUPERATION PAR APPAREIL (appliance.daily_use) ===")
profils_par_appareil = {}
for name, app in appliance_objects.items():
    profils_par_appareil[name] = np.array(app.daily_use)
    kwh_appareil = profils_par_appareil[name].sum() / 60000.0
    print(f"  {name:15s} -> {kwh_appareil:.3f} kWh/jour (récupéré individuellement)")

# ==========================================================
# 4. CONTROLE DE COHERENCE : somme(appareils) == agrégé
# ==========================================================
print("\n=== 4. CONTROLE DE COHERENCE INDIVIDUEL vs AGREGE ===")
somme_individuelle = sum(profils_par_appareil.values())
ecart_max_W = np.abs(somme_individuelle - profil_agrege).max()
kwh_individuel_total = somme_individuelle.sum() / 60000.0
kwh_agrege_total = profil_agrege.sum() / 60000.0

print(f"kWh total (somme des 4 appareils individuels) : {kwh_individuel_total:.4f} kWh")
print(f"kWh total (profil agrégé foyer)                : {kwh_agrege_total:.4f} kWh")
print(f"Ecart maximal instantané (W) entre les deux     : {ecart_max_W:.6f} W")

if ecart_max_W < 1e-6:
    print("CONTROLE VALIDE : la sortie agrégée est bien la somme exacte des sorties par appareil.")
else:
    print("ATTENTION : écart détecté entre somme individuelle et profil agrégé.")

# ==========================================================
# 5. EXPORT DANS UN FORMAT COMMUN (1 ligne = 1 minute)
# ==========================================================
df_export = pd.DataFrame({"minute": np.arange(1440)})
df_export["heure"] = df_export["minute"] / 60.0
for name in appliance_objects:
    df_export[f"{name}_W"] = profils_par_appareil[name]
df_export["Total_agrege_W"] = profil_agrege

print("\n=== 5. FORMAT DE SORTIE COMMUN (aperçu) ===")
print(df_export.head(3).to_string(index=False))
print("...")
print(df_export.iloc[1080:1083].to_string(index=False))  # extrait pendant la pointe du soir

df_export.to_csv("sprint0_foyer_fictif_24h.csv", index=False)
print("\nExport : sprint0_foyer_fictif_24h.csv")

# ==========================================================
# 6. RESUME FINAL
# ==========================================================
print("\n=== 6. RESUME ===")
pmax = profil_agrege.max()
print(f"Puissance maximale (Pmax)   : {pmax:.1f} W")
print(f"Energie totale simulée      : {kwh_agrege_total:.2f} kWh/jour")
print("Sortie récupérable appareil par appareil : OUI (df_export, colonnes *_W)")
print("Sortie récupérable agrégée                : OUI (colonne Total_agrege_W)")
