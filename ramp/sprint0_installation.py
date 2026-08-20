"""
Sprint 0 : Installation RAMP, génération foyer fictif et vérification des sorties[cite: 1, 2].
"""
import pandas as pd
from src.catalogue import get_catalogue_sprint0
from src.moteur import simuler_foyer

def executer_sprint0():
    print("=== SPRINT 0 (M2) : Validation RAMP & Foyer 24h ===")
    
    # 1. Chargement des appareils
    appareils = get_catalogue_sprint0()
    print(f"\n[OK] {len(appareils)} appareils declares : TV, Eclairage, Ventilateur, Refrigerateur.")
    
    # 2. Simulation et verification du format de sortie
    df_resultat = simuler_foyer(catalogue_appareils=appareils, pas_minutes=1)
    
    print("\n--- Sortie agregee (Aperçu) ---")
    print(df_resultat.head())
    
    print("\n--- Total consomme sur 24h ---")
    energie_kwh = (df_resultat["puissance_w"].sum() / 1000.0) * (1 / 60.0)
    print(f"Consommation totale du foyer : {energie_kwh:.2f} kWh")

if __name__ == "__main__":
    executer_sprint0()