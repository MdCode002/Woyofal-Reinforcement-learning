"""
Sprint 1 : Simulation RAMP adaptée au contexte de Dakar.
"""
from src.catalogue import get_catalogue_sprint1
from src.moteur import simuler_foyer

def executer_sprint1():
    print("=== SPRINT 1 : Simulation RAMP Dakar ===")
    
    # 1. Chargement du catalogue Dakar
    catalogue = get_catalogue_sprint1()
    print(f"[OK] {len(catalogue)} appareils charges depuis le catalogue Dakar.")
    
    # 2. Exécution de la simulation via le moteur
    df_simu = simuler_foyer(catalogue_appareils=catalogue, pas_minutes=1)
    
    print("\n--- Sortie de la simulation Dakar (Aperçu) ---")
    print(df_simu.head())
    
    print("\n--- Métriques de consommation ---")
    energie_kwh = (df_simu["puissance_w"].sum() / 1000.0) * (1 / 60.0)
    puissance_max = df_simu["puissance_w"].max()
    print(f"Énergie totale sur 24h : {energie_kwh:.2f} kWh")
    print(f"Pic de puissance atteint : {puissance_max:.0f} W")

if __name__ == "__main__":
    executer_sprint1()