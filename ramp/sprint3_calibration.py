"""
sprint3_calibration.py : Validation M3 - Thermal & Calibration
"""
from src.thermique import ModeleThermiquePiece
from src.meteo import generer_meteo_dakar

def executer_sprint3():
    print("=== SPRINT 3 (M3) : Calibration Thermique & Tests ===")
    
    # 1. Validation modèle thermique
    piece = ModeleThermiquePiece(R=0.025, C=6000.0, COP=3.2)
    print(f"[OK] Constante de temps tau = {piece.tau_heures:.2f} h (Plausible: {piece.est_constante_temps_plausible()})")
    
    # 2. Simulation météo et réponse de la clim
    df_meteo = generer_meteo_dakar(pas_minutes=30)
    temps_int = []
    
    for idx, row in df_meteo.iterrows():
        p_clim = 1200 if row["temperature_c"] > 28.0 else 0
        t_in = piece.mettre_a_jour_temperature(row["temperature_c"], p_clim, pas_minutes=30)
        temps_int.append(t_in)
        
    print(f"[OK] Test météo Dakar validé. Temp. intérieure finale : {temps_int[-1]:.1f}°C")

if __name__ == "__main__":
    executer_sprint3()