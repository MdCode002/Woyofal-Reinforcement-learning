"""Récompense de l'agent DQN, décomposée pour rester explicable."""

from __future__ import annotations

from dataclasses import dataclass

from .config import ConfigurationRecompense


@dataclass(frozen=True, slots=True)
class DetailRecompense:
    survie: float
    energie_pilotable: float
    progression_budget: float
    inconfort: float
    non_servie: float
    tache_inachevee: float
    coupure: float
    changement: float
    action_invalide: float
    objectif: float

    @property
    def total(self) -> float:
        return sum((
            self.survie, self.energie_pilotable, self.progression_budget,
            self.inconfort, self.non_servie, self.tache_inachevee,
            self.coupure, self.changement, self.action_invalide, self.objectif,
        ))


def calculer_recompense(
    *,
    energie_pilotable_kwh: float,
    facteur_energie_pilotable: float,
    energie_non_servie_kwh: float,
    inconfort_degre_heures: float,
    energie_taches_inachevees_kwh: float,
    coupure: bool,
    action_changee: bool,
    action_invalide: bool,
    date_cible_atteinte: bool,
    progression_budget: float,
    configuration: ConfigurationRecompense,
) -> DetailRecompense:
    valeurs = (
        energie_pilotable_kwh, energie_non_servie_kwh, inconfort_degre_heures,
        energie_taches_inachevees_kwh, facteur_energie_pilotable,
    )
    if any(valeur < 0 for valeur in valeurs):
        raise ValueError("Énergie et inconfort doivent être positifs ou nuls")
    return DetailRecompense(
        survie=configuration.bonus_survie_pas,
        energie_pilotable=(
            -configuration.poids_energie_pilotable
            * facteur_energie_pilotable
            * energie_pilotable_kwh
        ),
        progression_budget=configuration.poids_progression_budget * progression_budget,
        inconfort=-configuration.poids_inconfort * inconfort_degre_heures,
        non_servie=-configuration.penalite_non_servie * energie_non_servie_kwh,
        tache_inachevee=-configuration.penalite_tache_inachevee * energie_taches_inachevees_kwh,
        coupure=-configuration.penalite_coupure if coupure else 0.0,
        changement=-configuration.penalite_changement if action_changee else 0.0,
        action_invalide=(
            -configuration.penalite_action_invalide if action_invalide else 0.0
        ),
        objectif=configuration.bonus_date_cible if date_cible_atteinte else 0.0,
    )
