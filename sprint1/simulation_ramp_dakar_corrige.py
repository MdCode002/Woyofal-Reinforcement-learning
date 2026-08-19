"""
SPRINT M2 - Appareils / météo
Objectifs couverts :
  1. Catalogue initial des 7 appareils avec modules unitaires cohérents
     et calcul manuel reproduit (puissance/plage, quantité, fenêtres,
     durée, caractère flexible/non flexible)
  2. Série météo Dakar (température extérieure + humidité)
  3. Génération de PLUSIEURS profils RAMP (plusieurs jours simulés,
     stochastiques) et contrôle de l'ordre de grandeur des kWh
"""

from unittest.mock import patch
import numpy as np
import pandas as pd
from ramp import Appliance, UseCase, User

from catalogue import CATALOGUE

# ==========================================
# 1. PREPARATION SERIE METEO (DAKAR)
# ==========================================
minutes = np.arange(1440)
hours = minutes / 60
temp_dakar = 27.5 - 3.5 * np.cos(2 * np.pi * (hours - 14) / 24)
humidity_dakar = 72.5 + 12.5 * np.cos(2 * np.pi * (hours - 14) / 24)
df_meteo = pd.DataFrame(
    {"Minute": minutes, "Temp_C": temp_dakar, "Humidity_Pct": humidity_dakar}
)

# ==========================================
# 2. CATALOGUE + CALCUL MANUEL DE REFERENCE
# ==========================================
df_catalogue = pd.DataFrame(CATALOGUE)
df_catalogue["Wh_jour_manuel"] = (
    df_catalogue["power_W"]
    * df_catalogue["quantity"]
    * df_catalogue["func_time_min"]
    / 60.0
)
df_catalogue["kWh_jour_manuel"] = df_catalogue["Wh_jour_manuel"] / 1000.0

print("=== CATALOGUE INITIAL DES APPAREILS (Foyer Dakar M2) ===")
print(
    df_catalogue[
        [
            "name",
            "power_W",
            "quantity",
            "window_start_min",
            "window_end_min",
            "func_time_min",
            "random_var",
            "flexible",
            "kWh_jour_manuel",
        ]
    ].to_string(index=False)
)

kwh_manuel_total = df_catalogue["kWh_jour_manuel"].sum()
print(f"\n--- Calcul manuel de référence : {kwh_manuel_total:.2f} kWh/jour ---")
print("(somme de : puissance x quantité x durée de fonctionnement / 60)\n")

# ==========================================
# 3. CONFIGURATION RAMP A PARTIR DU CATALOGUE
# ==========================================
foyer_dakar = User("Foyer Dakar M2", 1)


def create_appliance_from_catalog(user, entry):
    """Construit un objet Appliance RAMP à partir d'une entrée du catalogue."""
    app = Appliance(
        user,
        number=entry["quantity"],
        power=entry["power_W"],
        num_windows=1,
        func_time=entry["func_time_min"],
        time_fraction_random_variability=entry["random_var"],
        name=entry["name"],
    )
    app.windows(
        window_1=[entry["window_start_min"], entry["window_end_min"]],
        random_var_w=entry["random_var"],
    )
    return app


appliances = [create_appliance_from_catalog(foyer_dakar, entry) for entry in CATALOGUE]

# ==========================================
# 4. GENERATION DE PLUSIEURS PROFILS RAMP
# ==========================================
NUM_DAYS = 7  # plusieurs profils stochastiques pour contrôler l'ordre de grandeur

my_use_case = UseCase(users=[foyer_dakar], date_start="2026-01-01")
with patch("builtins.input", return_value="1"):
    my_use_case.initialize(num_days=NUM_DAYS)

# flat=False -> un profil (1440 valeurs) par jour simulé, non concaténés
profiles = my_use_case.generate_daily_load_profiles(flat=False)
profiles = np.array(profiles).reshape(NUM_DAYS, 1440)

kwh_par_jour = profiles.sum(axis=1) / 60000.0  # W-minute -> kWh
pmax_par_jour = profiles.max(axis=1)

df_profils = pd.DataFrame(
    {
        "Jour": np.arange(1, NUM_DAYS + 1),
        "Pmax_W": pmax_par_jour,
        "kWh_jour": kwh_par_jour,
    }
)

print("=== PLUSIEURS PROFILS RAMP SIMULES ===")
print(df_profils.to_string(index=False))

kwh_moyen = kwh_par_jour.mean()
kwh_min = kwh_par_jour.min()
kwh_max = kwh_par_jour.max()
pmax_moyen = pmax_par_jour.mean()

print("\n=== SPRINT M2 : RESULTATS DE LA SIMULATION RAMP ===")
print(f"Calcul manuel de référence         : {kwh_manuel_total:.2f} kWh/jour")
print(f"Moyenne simulée sur {NUM_DAYS} profils      : {kwh_moyen:.2f} kWh/jour")
print(f"Min / Max simulés                  : {kwh_min:.2f} / {kwh_max:.2f} kWh/jour")
print(f"Puissance maximale moyenne (Pmax)  : {pmax_moyen:.2f} W")
print(f"Température moyenne Dakar          : {df_meteo['Temp_C'].mean():.1f} °C")
print(f"Humidité moyenne Dakar             : {df_meteo['Humidity_Pct'].mean():.1f} %")

print("\n--- Validation des ordres de grandeur ---")
ecart_pct = abs(kwh_moyen - kwh_manuel_total) / kwh_manuel_total * 100
print(f"Ecart simulation vs calcul manuel   : {ecart_pct:.1f} %")

if 3.5 <= kwh_moyen <= 7.0 and ecart_pct <= 20:
    print(
        "CONTROLE VALIDE : la consommation simulée correspond à l'estimation "
        "théorique et reste dans la plage attendue (3.5-7.0 kWh/jour) !"
    )
else:
    print(
        "ECART DETECTE : vérifier la durée d'activation des gros consommateurs "
        "ou la cohérence des fenêtres d'usage."
    )
