"""
Logique du compteur prépayé Woyofal.
"""

class CompteurWoyofal:
    def __init__(self, credit_initial_kwh=15.0, tarif_kwh=91.17):
        self.credit_kwh = credit_initial_kwh
        self.tarif_kwh = tarif_kwh
        self.consommation_cumulee_kwh = 0.0

    def consommer(self, puissance_w, pas_minutes=30):
        """Calcule la consommation de l'intervalle et met à jour le solde."""
        energie_kwh = (puissance_w / 1000.0) * (pas_minutes / 60.0)
        self.consommation_cumulee_kwh += energie_kwh
        self.credit_kwh -= energie_kwh
        
        statut_coupure = 1 if self.credit_kwh <= 0 else 0
        return energie_kwh, self.credit_kwh, statut_coupure