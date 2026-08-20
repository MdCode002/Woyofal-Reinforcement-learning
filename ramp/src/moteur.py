"""
Moteur de simulation RAMP stochastique multi-journées et multi-ménages.
"""
import pandas as pd
import numpy as np

def simuler_foyer_stochastique(catalogue_appareils, jours=1, var_puissance=0.1, var_duree=0.2):
    """
    Génère la consommation d'un foyer avec variabilité stochastique sur les puissances,
    les durées d'utilisation et les horaires.
    """
    pas_minutes = 1
    pas_par_jour = 1440
    pas_total = pas_par_jour * jours
    puissance_totale = np.zeros(pas_total)

    for jour in range(jours):
        offset_jour = jour * pas_par_jour
        
        for app in catalogue_appareils:
            qte = app.get("quantite", 1)
            
            for _ in range(qte):
                # Variabilité sur la puissance (+/- var_puissance)
                p_base = app["puissance_w"]
                p_effective = p_base * np.random.uniform(1 - var_puissance, 1 + var_puissance)
                
                # Variabilité sur la durée
                duree_base = app["duree_min"]
                duree_eff = int(duree_base * np.random.uniform(1 - var_duree, 1 + var_duree))
                duree_eff = max(1, duree_eff)
                
                # Variabilité sur l'horaire dans la fenêtre d'usage
                f_debut, f_fin = app["fenetre_usage"]
                min_debut = f_debut * 60
                min_fin = (f_fin * 60) if f_fin > f_debut else (f_fin + 24) * 60
                
                max_start = max(min_debut, min_fin - duree_eff)
                if max_start <= min_debut:
                    debut_min = min_debut
                else:
                    debut_min = np.random.randint(min_debut, max_start)
                
                debut_idx = offset_jour + (debut_min % pas_par_jour)
                fin_idx = min(pas_total, debut_idx + duree_eff)
                
                puissance_totale[debut_idx:fin_idx] += p_effective

    index_temps = pd.date_range("2026-01-01", periods=pas_total, freq="1min")
    return pd.DataFrame({"temps": index_temps, "puissance_w": np.round(puissance_totale, 2)})