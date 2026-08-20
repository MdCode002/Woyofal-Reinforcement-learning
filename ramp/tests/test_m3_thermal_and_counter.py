"""
tests/test_m3_thermal_and_counter.py : Suite de tests unitaires pour le jalon M3.
Validation du modèle thermique (R, C, COP) et du compteur Woyofal.
"""
from src.thermique import ModeleThermiquePiece
from src.compteur import CompteurWoyofal


def test_constante_de_temps_plausible():
    # C = 360 000 J/°C (100 Wh/°C) -> Tau = (0.02 * 360000) / 3600 = 2.0 h (Plausible)
    modele = ModeleThermiquePiece(R=0.02, C=360000.0)
    assert modele.est_constante_temps_plausible(), f"Tau non plausible: {modele.tau_heures}h"


def test_evolution_thermique_et_clim():
    modele = ModeleThermiquePiece(R=0.02, C=360000.0, COP=3.0, temp_init=28.0)
    
    # 1. Sans climatisation, la pièce chauffe sous une température extérieure de 35°C
    t1 = modele.mettre_a_jour_temperature(temp_exterieure=35.0, puissance_clim_w=0)
    assert t1 > 28.0, "La température intérieure devrait augmenter sans climatisation"
    
    # 2. Avec climatisation (1200 W), la température doit baisser
    t2 = modele.mettre_a_jour_temperature(temp_exterieure=35.0, puissance_clim_w=1200)
    assert t2 < t1, "La température intérieure devrait diminuer avec la climatisation active"


def test_conservation_energie_et_solde_woyofal():
    compteur = CompteurWoyofal(credit_initial_kwh=10.0)
    
    # Consommation de 2000 W pendant 30 minutes = 1 kWh
    e_kwh, credit_restant, coupure = compteur.consommer(puissance_w=2000, pas_minutes=30)
    
    assert round(e_kwh, 2) == 1.0, f"Énergie calculée incorrecte : {e_kwh} kWh"
    assert round(credit_restant, 2) == 9.0, f"Crédit restant incorrect : {credit_restant} kWh"
    assert coupure == 0, "Le compteur ne devrait pas être en coupure"


def test_recharge_woyofal():
    compteur = CompteurWoyofal(credit_initial_kwh=1.0)
    
    # Épuisement du crédit (3000 W pendant 30 min = 1.5 kWh)
    _, credit_apres_conso, coupure = compteur.consommer(puissance_w=3000, pas_minutes=30)
    assert coupure == 1, "Le compteur devrait être coupé après épuisement du crédit"
    assert credit_apres_conso <= 0
    
    # Recharge de 10 kWh
    compteur.credit_kwh += 10.0
    assert compteur.credit_kwh > 0, "Le crédit devrait être positif après recharge"