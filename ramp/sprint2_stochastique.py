"""
Sprint 2 : Profils stochastiques multi-journées, multi-ménages et agrégation 30 min.
"""
import os
import pandas as pd
from src.catalogue import get_scenarios_menages
from src.moteur import simuler_foyer_stochastique

def executer_sprint2():
    print("=== SPRINT 2 (M2) : Profils Stochastiques Multi-Ménages ===")
    
    scenarios = get_scenarios_menages()
    nb_jours = 3
    df_tous_profils = pd.DataFrame()

    for nom_scenario, catalogue in scenarios.items():
        print(f"\n[+] Simulation du scénario : {nom_scenario} ({nb_jours} journées)...")
        
        # Simulation minute par minute
        df_simu = simuler_foyer_stochastique(catalogue, jours=nb_jours)
        
        # Agrégation au pas de 30 minutes
        df_simu = df_simu.set_index("temps")
        df_30min = df_simu.resample("30min")["puissance_w"].mean().reset_index()
        df_30min["menage_id"] = nom_scenario
        
        df_tous_profils = pd.concat([df_tous_profils, df_30min], ignore_index=True)

    # Réorganisation des colonnes
    df_tous_profils = df_tous_profils[["temps", "menage_id", "puissance_w"]]

    # Exportation dans data/
    os.makedirs("data", exist_ok=True)
    chemin_export = "data/profils_stochastiques.csv"
    df_tous_profils.to_csv(chemin_export, index=False)
    
    print(f"\n[OK] Profils exportés avec succès au pas de 30 min : {chemin_export}")
    print("\n--- Aperçu du fichier généré ---")
    print(df_tous_profils.head(10))

if __name__ == "__main__":
    executer_sprint2()