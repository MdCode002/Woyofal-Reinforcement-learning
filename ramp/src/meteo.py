"""
Génération des données météo horaires/minute pour Dakar (Température & Humidité).
"""
import pandas as pd
import numpy as np

def generer_meteo_dakar(pas_minutes=1):
    """Génère un profil météo 24h synthétique représentatif de Dakar."""
    pas_total = 1440 // pas_minutes
    heures = np.linspace(0, 24, pas_total)
    
    # Cycle de température typique Dakar (min ~22°C la nuit, max ~32°C à 14h)
    temperature = 27 + 5 * np.sin((heures - 9) * np.pi / 12)
    
    # Cycle d'humidité inversé (min ~50% à 14h, max ~85% la nuit)
    humidite = 67.5 - 17.5 * np.sin((heures - 9) * np.pi / 12)
    
    index_temps = pd.date_range("2026-01-01", periods=pas_total, freq=f"{pas_minutes}min")
    return pd.DataFrame({
        "temps": index_temps,
        "temperature_c": np.round(temperature, 1),
        "humidite_pct": np.round(humidite, 1)
    })