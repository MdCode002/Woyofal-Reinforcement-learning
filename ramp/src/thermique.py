"""
src/thermique.py : Modèle thermique simplifiée (R, C, COP) pour la climatisation.
"""

class ModeleThermiquePiece:
    def __init__(self, R=0.02, C=5000.0, COP=3.0, temp_init=28.0):
        """
        - R : Résistance thermique (°C/W) [Plage: 0.01 - 0.05]
        - C : Capacité thermique (J/°C) [Plage: 2000 - 10000]
        - COP : Coefficient de Performance [Plage: 2.5 - 4.0]
        """
        self.R = R
        self.C = C
        self.COP = COP
        self.temp_interieure = temp_init
        
        # Constante de temps tau = R * C (en secondes)
        self.tau_heures = (self.R * self.C) / 3600.0

    def est_constante_temps_plausible(self):
        """Vérifie que tau est physiquement réaliste (entre 0.5h et 5h)."""
        return 0.5 <= self.tau_heures <= 5.0

    def mettre_a_jour_temperature(self, temp_exterieure, puissance_clim_w, pas_minutes=30):
        """
        Calcule la nouvelle température intérieure après un pas de temps (dt).
        """
        dt_sec = pas_minutes * 60.0
        
        # Apport thermique de l'extérieur + Froid produit par la clim (P_froid = P_elec * COP)
        flux_thermique = (temp_exterieure - self.temp_interieure) / self.R
        puissance_froid = puissance_clim_w * self.COP
        
        dT = ((flux_thermique - puissance_froid) / self.C) * dt_sec
        self.temp_interieure += dT
        return self.temp_interieure