"""Modèle thermique 1R1C stable, avec unités explicites."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

from collections.abc import Sequence

from common import MeteoPas, ParametresThermiques


@dataclass(frozen=True, slots=True)
class ResultatThermique:
    temperature_interieure_c: float
    energie_climatisation_kwh: float
    inconfort_degre_heures: float
    limite_confort_haute_c: float


class ModeleThermique1R1C:
    """Évolution d'une température moyenne représentative de la zone occupée.

    Il ne s'agit pas d'un thermomètre par pièce. Sans mesure intérieure, la
    température initiale est explicitement une estimation et l'incertitude est
    traitée par randomisation des scénarios.
    """

    def __init__(self, temperature_initiale_c: float, parametres: ParametresThermiques):
        if not -10.0 <= temperature_initiale_c <= 60.0:
            raise ValueError("La température intérieure initiale est hors plage")
        if not 1.0 <= parametres.constante_temps_heures <= 4.0:
            raise ValueError("La constante de temps R×C doit être comprise entre 1 et 4 h")
        self.temperature_interieure_c = float(temperature_initiale_c)
        self.parametres = parametres
        self._compresseur_actif = False

    def step(
        self,
        meteo: MeteoPas,
        *,
        climatisation_active: bool,
        ventilateur_actif: bool,
        occupation: bool,
        temperature_consigne_c: float | None = None,
        duree_minutes: int = 30,
        sous_pas_minutes: int = 5,
    ) -> ResultatThermique:
        if duree_minutes <= 0 or sous_pas_minutes <= 0 or duree_minutes % sous_pas_minutes:
            raise ValueError("Le sous-pas doit diviser exactement la durée")
        p = self.parametres
        gains_solaires_kw = p.coefficient_gains_solaires * meteo.rayonnement_w_m2
        dt_heures = sous_pas_minutes / 60.0
        facteur = exp(-dt_heures / p.constante_temps_heures)
        inconfort = 0.0
        energie_climatisation = 0.0
        if not climatisation_active:
            self._compresseur_actif = False
        limite_haute = p.temperature_confort_max_c + (
            p.gain_confort_ventilateur_c if ventilateur_actif and occupation else 0.0
        )
        for _ in range(duree_minutes // sous_pas_minutes):
            if climatisation_active:
                if temperature_consigne_c is None:
                    self._compresseur_actif = True
                elif self._compresseur_actif and self.temperature_interieure_c <= temperature_consigne_c - 0.2:
                    self._compresseur_actif = False
                elif not self._compresseur_actif and self.temperature_interieure_c >= temperature_consigne_c + 0.2:
                    self._compresseur_actif = True
            puissance_froid_kw = (
                p.puissance_climatisation_electrique_kw * p.cop_climatisation
                if self._compresseur_actif
                else 0.0
            )
            gains_nets_kw = p.gains_internes_kw + gains_solaires_kw - puissance_froid_kw
            equilibre_c = meteo.temperature_exterieure_c + p.resistance_c_par_kw * gains_nets_kw
            self.temperature_interieure_c = equilibre_c + (
                self.temperature_interieure_c - equilibre_c
            ) * facteur
            if self._compresseur_actif:
                energie_climatisation += p.puissance_climatisation_electrique_kw * dt_heures
            if occupation:
                ecart = max(
                    p.temperature_confort_min_c - self.temperature_interieure_c,
                    self.temperature_interieure_c - limite_haute,
                    0.0,
                )
                inconfort += ecart * dt_heures
        return ResultatThermique(
            temperature_interieure_c=self.temperature_interieure_c,
            energie_climatisation_kwh=energie_climatisation,
            inconfort_degre_heures=inconfort,
            limite_confort_haute_c=limite_haute,
        )


Thermal1R1C = ModeleThermique1R1C


def estimer_temperature_interieure_initiale(
    meteo: Sequence[MeteoPas],
    parametres: ParametresThermiques,
    *,
    pas_minutes: int = 30,
    sous_pas_minutes: int = 5,
    jours_stabilisation: int = 7,
) -> float:
    """Estime l'état thermique initial sans thermomètre intérieur.

    Le premier cycle météo disponible est répété plusieurs fois afin que le
    bâtiment atteigne un régime cohérent avec l'extérieur, son inertie, les
    gains internes et le soleil. Aucune valeur intérieure n'est saisie.
    """

    if not meteo:
        raise ValueError("La météo est obligatoire pour estimer la température intérieure")
    pas_par_jour = max(1, 24 * 60 // pas_minutes)
    cycle = tuple(meteo[:pas_par_jour])
    temperature_depart = sum(point.temperature_exterieure_c for point in cycle) / len(cycle)
    modele = ModeleThermique1R1C(temperature_depart, parametres)
    for _ in range(max(1, jours_stabilisation)):
        for point in cycle:
            modele.step(
                point,
                climatisation_active=False,
                ventilateur_actif=False,
                occupation=False,
                duree_minutes=pas_minutes,
                sous_pas_minutes=sous_pas_minutes,
            )
    return float(modele.temperature_interieure_c)
