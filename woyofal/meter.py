"""Compteur prépayé en kWh et conversion tarifaire indicative isolée."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultatCompteur:
    energie_demandee_kwh: float
    energie_servie_kwh: float
    energie_non_servie_kwh: float
    credit_restant_kwh: float

    @property
    def coupure(self) -> bool:
        return self.energie_non_servie_kwh > 1e-12


class CompteurWoyofal:
    """Le compteur ne peut ni fournir plus que son crédit, ni devenir négatif."""

    def __init__(self, credit_initial_kwh: float):
        if credit_initial_kwh < 0:
            raise ValueError("Le crédit initial doit être positif ou nul")
        self.credit_restant_kwh = float(credit_initial_kwh)
        self.energie_servie_cumulee_kwh = 0.0
        self.energie_non_servie_cumulee_kwh = 0.0

    @property
    def balance(self) -> float:
        return self.credit_restant_kwh

    def servir(self, energie_demandee_kwh: float) -> ResultatCompteur:
        if energie_demandee_kwh < 0:
            raise ValueError("La demande d'énergie ne peut pas être négative")
        servie = min(float(energie_demandee_kwh), self.credit_restant_kwh)
        non_servie = max(0.0, float(energie_demandee_kwh) - servie)
        self.credit_restant_kwh = max(0.0, self.credit_restant_kwh - servie)
        self.energie_servie_cumulee_kwh += servie
        self.energie_non_servie_cumulee_kwh += non_servie
        return ResultatCompteur(
            energie_demandee_kwh=float(energie_demandee_kwh),
            energie_servie_kwh=servie,
            energie_non_servie_kwh=non_servie,
            credit_restant_kwh=self.credit_restant_kwh,
        )

    def consume(self, energy_kwh: float) -> float:
        """Compatibilité temporaire : retourne le solde comme l'ancien module."""

        return self.servir(energy_kwh).credit_restant_kwh


def convertir_fcfa_en_kwh(montant_fcfa: float) -> float:
    """Conversion énergie seule de la grille DPP 2026 simplifiée."""

    if montant_fcfa < 0:
        raise ValueError("Le montant doit être positif ou nul")
    cout_premiere_tranche = 150.0 * 82.0
    if montant_fcfa <= cout_premiere_tranche:
        return montant_fcfa / 82.0
    return 150.0 + (montant_fcfa - cout_premiere_tranche) / 136.49


def convertir_kwh_en_fcfa(energie_kwh: float) -> float:
    """Estimation indicative, sans taxes, redevances, dettes ni arrondis compteur."""

    if energie_kwh < 0:
        raise ValueError("L'énergie doit être positive ou nulle")
    premiere = min(energie_kwh, 150.0) * 82.0
    suivante = max(0.0, energie_kwh - 150.0) * 136.49
    return premiere + suivante


WoyofalMeter = CompteurWoyofal
