"""
Sprint 1 : Simulation RAMP complète, météo Dakar et contrôle théorique des kWh.
"""
import pandas as pd
from src.catalogue import get_catalogue_sprint1
from src.meteo import generer_meteo_dakar
from src.moteur import simuler_foyer

def calculer_kwh_theorique(catalogue):
    """Calcul manuel théorique de la consommation journalière en kWh."""
    total_kwh = 0.0
    for app in catalogue:
        p_totale_w = app["puissance_w"] * app["quantite"]
        duree_h = app["duree_min"] / 60.0
        total_kwh += (p_totale_w * duree_h) / 1000.0
    return total_kwh

def executer_sprint1():
    print("=== SPRINT 1 (M2) : Appareils / Météo Dakar ===")
    
    # 1. Catalogue et météo
    catalogue = get_catalogue_sprint1()
    df_meteo = generer_meteo_dakar(pas_minutes=1)
    
    # 2. Calcul théorique manuel
    kwh_theorique = calculer_kwh_theorique(catalogue)
    print(f"[1] Consommation théorique calculée manuellement : {kwh_theorique:.2f} kWh")
    
    # 3. Génération de profils RAMP
    df_simu = simuler_foyer(catalogue_appareils=catalogue, pas_minutes=1)
    df_complet = pd.merge(df_simu, df_meteo, on="temps")
    
    kwh_simule = (df_complet["puissance_w"].sum() / 1000.0) * (1 / 60.0)
    print(f"[2] Consommation simulée RAMP : {kwh_simule:.2f} kWh")
    print(f"[3] Métriques météo Dakar (Temp : {df_meteo['temperature_c'].min()}°C à {df_meteo['temperature_c'].max()}°C)")
    
    print("\n--- Aperçu du jeu de données final ---")
    print(df_complet.head())

if __name__ == "__main__":
    executer_sprint1()