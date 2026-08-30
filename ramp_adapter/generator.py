"""Génération RAMP minute par minute puis agrégation exacte à 30 minutes."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import random
from typing import Iterator, Sequence

import numpy as np
from ramp import UseCase, User, get_day_type

from common import Appareil, ProfilChargePas, Scenario
from common.units import PAS_DECISION_MINUTES


@contextmanager
def _graine_ramp(seed: int) -> Iterator[None]:
    """Isole les générateurs globaux utilisés en interne par RAMP."""

    etat_python = random.getstate()
    etat_numpy = np.random.get_state()
    random.seed(seed)
    np.random.seed(seed)
    try:
        yield
    finally:
        random.setstate(etat_python)
        np.random.set_state(etat_numpy)


def _minute(heure) -> int:
    valeur = heure.hour * 60 + heure.minute
    return 1440 if valeur == 1439 else valeur


def _fenetres_ramp(appareil: Appareil) -> list[list[int]]:
    fenetres: list[list[int]] = []
    for fenetre in appareil.fenetres_usage:
        debut, fin = _minute(fenetre.heure_debut), _minute(fenetre.heure_fin)
        if debut == fin or (debut == 0 and fin >= 1439):
            fenetres.append([0, 1440])
        elif debut < fin:
            fenetres.append([debut, fin])
        else:
            fenetres.extend(([debut, 1440], [0, fin]))
    if len(fenetres) > 3:
        raise ValueError(f"RAMP accepte au plus trois fenêtres pour {appareil.nom}")
    return fenetres


def _ajouter_appareil(utilisateur: User, appareil: Appareil):
    fenetres = _fenetres_ramp(appareil)
    duree = min(1440, sum(f.duree_moyenne_minutes for f in appareil.fenetres_usage))
    probabilite = max(f.probabilite_utilisation for f in appareil.fenetres_usage)
    variabilite = appareil.variabilite_puissance_pourcent
    est_froid = appareil.categorie == "froid"
    objet = utilisateur.Appliance(
        number=appareil.quantite,
        power=appareil.puissance_w,
        num_windows=len(fenetres),
        func_time=1440 if est_froid else max(1, duree),
        time_fraction_random_variability=variabilite,
        func_cycle=30 if est_froid else max(5, min(60, duree)),
        fixed="yes" if est_froid else "no",
        fixed_cycle=3 if est_froid else 0,
        occasional_use=probabilite,
        name=appareil.nom,
    )
    arguments = {"window_1": fenetres[0], "random_var_w": min(0.5, variabilite)}
    if len(fenetres) >= 2:
        arguments["window_2"] = fenetres[1]
    if len(fenetres) == 3:
        arguments["window_3"] = fenetres[2]
    objet.windows(**arguments)
    if est_froid:
        puissance = appareil.puissance_w
        objet.specific_cycle_1(puissance, 20, 5, 10)
        objet.specific_cycle_2(puissance, 15, 5, 15)
        objet.specific_cycle_3(puissance, 10, 5, 20)
        objet.cycle_behaviour(
            [580, 1200], [0, 0], [420, 579], [0, 0], [0, 419], [1201, 1440]
        )
    return objet


def generer_profils_ramp(
    scenario: Scenario,
    *,
    nombre_jours: int | None = None,
    seed: int | None = None,
) -> list[ProfilChargePas]:
    """Génère la demande non thermique de chaque appareil.

    La climatisation et le ventilateur, marqués ``controle_par_environnement``,
    sont exclus. RAMP produit des watts à chaque minute ; la conversion en kWh
    est faite par somme, ce qui conserve l'énergie à l'arrondi flottant près.
    """

    nombre_jours_demandes = nombre_jours
    if nombre_jours_demandes is None:
        nombre_pas_demandes = scenario.nombre_pas_max
    else:
        nombre_pas_demandes = min(
            scenario.nombre_pas_max,
            max(1, nombre_jours_demandes) * 1440 // PAS_DECISION_MINUTES,
        )
    minute_depart = scenario.date_debut.hour * 60 + scenario.date_debut.minute
    if minute_depart % PAS_DECISION_MINUTES:
        raise ValueError("date_debut doit être alignée sur un pas de 30 minutes")
    nombre_jours_generation = max(
        1,
        (minute_depart + nombre_pas_demandes * PAS_DECISION_MINUTES + 1439) // 1440,
    )
    date_calendaire_depart = scenario.date_debut.replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    non_controles = [a for a in scenario.appareils if not a.controle_par_environnement]
    if not non_controles:
        raise ValueError("Au moins un appareil non contrôlé est nécessaire pour RAMP")

    profils: list[ProfilChargePas] = []
    with _graine_ramp(scenario.seed if seed is None else seed):
        # RAMP randomise aussi lors de la construction des appareils et de la
        # plage de pointe : ces étapes doivent donc être dans le même contexte.
        utilisateur = User(user_name=scenario.identifiant_foyer, num_users=1)
        objets = [
            (appareil, _ajouter_appareil(utilisateur, appareil))
            for appareil in non_controles
        ]
        usage = UseCase(name=f"woyofal-{scenario.identifiant_foyer}", users=[utilisateur])
        usage.peak_time_range = usage.calc_peak_time_range()
        # Avec un profil maximal parfaitement plat, RAMP 0.5 peut produire
        # ``np.arange(x, x)``, donc une plage vide ensuite indexée en interne.
        if np.asarray(usage.peak_time_range).size < 2:
            usage.peak_time_range = np.array([0, 1439], dtype=np.int64)
        for index_jour in range(nombre_jours_generation):
            date_jour = date_calendaire_depart + timedelta(days=index_jour)
            jour_annee = date_jour.timetuple().tm_yday - 1
            utilisateur.generate_single_load_profile(
                jour_annee, usage.peak_time_range, get_day_type(date_jour)
            )
            minute_par_appareil = {
                appareil.nom: np.asarray(objet.daily_use, dtype=np.float64).copy()
                for appareil, objet in objets
            }
            for debut in range(0, 1440, PAS_DECISION_MINUTES):
                fin = debut + PAS_DECISION_MINUTES
                energie = {
                    nom: float(valeurs[debut:fin].sum() / 60_000.0)
                    for nom, valeurs in minute_par_appareil.items()
                }
                puissance = {
                    nom: float(valeurs[debut:fin].mean())
                    for nom, valeurs in minute_par_appareil.items()
                }
                decalables = {
                    appareil.nom: energie[appareil.nom]
                    for appareil, _ in objets
                    if appareil.decalage_autorise and energie[appareil.nom] > 0
                }
                non_pilotable = sum(
                    energie[appareil.nom]
                    for appareil, _ in objets
                    if not appareil.decalage_autorise
                )
                profils.append(
                    ProfilChargePas(
                        horodatage=date_jour.replace(hour=0, minute=0, second=0, microsecond=0)
                        + timedelta(minutes=debut),
                        pas_minutes=PAS_DECISION_MINUTES,
                        puissance_demandee_par_appareil_w=puissance,
                        energie_demandee_par_appareil_kwh=energie,
                        energie_non_pilotable_kwh=float(non_pilotable),
                        charges_decalables_kwh=decalables,
                    )
                )
    index_depart = minute_depart // PAS_DECISION_MINUTES
    return profils[index_depart:index_depart + nombre_pas_demandes]
