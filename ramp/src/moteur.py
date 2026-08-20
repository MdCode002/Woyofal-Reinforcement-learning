import pandas as pd
import numpy as np

def simuler_foyer(catalogue_appareils, pas_minutes=1, stochastique=False):
    minutes_journee = 1440
    pas_total = minutes_journee // pas_minutes
    puissance_totale = np.zeros(pas_total)

    for app in catalogue_appareils:
        p_nominale = app["puissance_w"]
        duree = app["duree_min"] // pas_minutes
        
        if stochastique and "variabilite" in app:
            duree = int(duree * np.random.uniform(0.8, 1.2))

        debut = np.random.randint(0, max(1, pas_total - duree))
        puissance_totale[debut:debut + duree] += p_nominale

    index_temps = pd.date_range("2026-01-01", periods=pas_total, freq=f"{pas_minutes}min")
    return pd.DataFrame({"temps": index_temps, "puissance_w": puissance_totale})