"""Service métier partagé par la CLI et l'API locale."""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import numpy as np

from common import ModeConfort, Scenario, charger_scenario
from env import DIMENSION_OBSERVATION, NOMBRE_ACTIONS, EnvironnementWoyofal
from ramp_adapter import generer_profils_ramp, meteo_avec_source_pour_scenario
from rl.train import charger_modele

SCENARIO_DEFAUT = Path(__file__).resolve().parents[1] / "data" / "scenarios" / "foyer_fictif.json"
RACINE_PROJET = Path(__file__).resolve().parents[1]
VERSION_SCHEMA_ENVIRONNEMENT = "politique_partagee_pieces_variables_v3"


@lru_cache(maxsize=4)
def _charger_modele_valide(algorithme: str, chemin: str, modification_ns: int):
    """Évite de relire les mêmes poids à chaque appel HTTP."""

    del modification_ns
    politique = charger_modele(algorithme, chemin)
    _verifier_compatibilite_modele(politique)
    return politique


def _verifier_compatibilite_modele(modele: Any) -> None:
    forme = getattr(getattr(modele, "observation_space", None), "shape", None)
    actions = getattr(getattr(modele, "action_space", None), "n", None)
    if forme != (DIMENSION_OBSERVATION,) or actions != NOMBRE_ACTIONS:
        raise RuntimeError(
            "Le modèle sauvegardé utilise l'ancien environnement. "
            "Il doit être réentraîné avec la politique partagée par pièce."
        )


def _verifier_metadonnees(chemin: Path) -> None:
    metadata = chemin.parent / "metadata.json"
    if not metadata.exists():
        raise RuntimeError("Les métadonnées du modèle sont absentes; sa compatibilité est inconnue.")
    contenu = json.loads(metadata.read_text(encoding="utf-8"))
    version = (
        contenu.get("configuration", {})
        .get("environnement", {})
        .get("version_schema")
    )
    if version != VERSION_SCHEMA_ENVIRONNEMENT:
        raise RuntimeError(
            "Le modèle utilise une ancienne signification des observations et doit être réentraîné."
        )


def charger_politique(
    modele: str | Path | None = None,
    algorithme: str | None = None,
) -> tuple[Any, str]:
    """Charge exclusivement le modèle DQN compatible et validé."""

    algorithme = (algorithme or "dqn").lower()
    if algorithme != "dqn":
        raise ValueError("L'algorithme du projet est 'dqn'")
    if modele is not None:
        chemin = Path(modele)
        if chemin.exists():
            _verifier_metadonnees(chemin)
            politique = _charger_modele_valide(
                "dqn", str(chemin.resolve()), chemin.stat().st_mtime_ns,
            )
            return politique, "dqn"
        raise ValueError("Le modèle explicite est absent")
    selection = RACINE_PROJET / "results" / "models" / "selection.json"
    if selection.exists():
        contenu = json.loads(selection.read_text(encoding="utf-8"))
        algo = contenu.get("algorithme", "dqn").lower()
        if algo != "dqn":
            raise RuntimeError("La sélection publiée ne désigne pas le modèle DQN")
        chemin = Path(contenu["chemin"])
        if not chemin.is_absolute():
            chemin = RACINE_PROJET / chemin
        if chemin.exists():
            _verifier_metadonnees(chemin)
            politique = _charger_modele_valide(
                "dqn", str(chemin.resolve()), chemin.stat().st_mtime_ns,
            )
            return politique, "dqn"
        raise FileNotFoundError(f"Modèle DQN sélectionné introuvable : {chemin}")
    raise FileNotFoundError(
        "Aucun modèle DQN validé dans results/models/selection.json"
    )


def _environnement(scenario: Scenario, seed: int) -> EnvironnementWoyofal:
    profils = generer_profils_ramp(scenario, seed=seed)
    meteo, source_meteo = meteo_avec_source_pour_scenario(scenario)
    environnement = EnvironnementWoyofal(scenario, profils, meteo)
    environnement.source_meteo_utilisee = source_meteo
    return environnement


def _inventaire_interprete(scenario: Scenario) -> dict[str, Any]:
    return {
        "pieces": [
            {
                "nom": piece.nom,
                "type_piece": piece.type_piece,
                "taille": piece.taille,
                "profil_occupation": piece.profil_occupation.value,
                "occupation_actuelle": piece.occupation_actuelle,
                "nombre_climatiseurs": piece.nombre_climatiseurs,
                "puissance_climatisation_unitaire_w": (
                    piece.puissance_climatisation_unitaire_effective_w
                    if piece.climatisation else 0.0
                ),
                "puissance_climatisation_totale_w": piece.puissance_climatisation_effective_w,
                "nombre_ventilateurs": piece.nombre_ventilateurs,
                "puissance_ventilateur_unitaire_w": (
                    piece.puissance_ventilateur_unitaire_effective_w
                    if piece.ventilateur else 0.0
                ),
                "puissance_ventilateur_totale_w": piece.puissance_ventilateur_effective_w,
            }
            for piece in scenario.pieces
        ],
        "appareils": [
            {
                "nom": appareil.nom,
                "categorie": appareil.categorie,
                "quantite": appareil.quantite,
                "puissance_unitaire_w": appareil.puissance_w,
                "puissance_installee_w": appareil.quantite * appareil.puissance_w,
                "decalable": appareil.decalage_autorise,
                "essentiel": appareil.essentiel,
            }
            for appareil in scenario.appareils
        ],
    }


def prevoir(
    *,
    scenario: Scenario | None = None,
    simulations: int = 20,
    modele: str | Path | None = None,
    algorithme: str | None = None,
) -> dict[str, Any]:
    """Estime durée et probabilité sur plusieurs réalisations RAMP."""

    if simulations < 3 or simulations > 200:
        raise ValueError("simulations doit être compris entre 3 et 200")
    scenario = scenario or charger_scenario(SCENARIO_DEFAUT)
    politique, source = charger_politique(modele, algorithme)
    durees, succes, credits, inconforts, energies_servies = [], [], [], [], []
    sources_meteo: set[str] = set()
    for numero in range(simulations):
        environnement = _environnement(scenario, scenario.seed + numero * 997)
        sources_meteo.add(environnement.source_meteo_utilisee)
        observation, _ = environnement.reset(seed=scenario.seed + numero)
        termine = tronque = False
        info: dict[str, Any] = {}
        while not (termine or tronque):
            action, _ = politique.predict(observation, deterministic=True)
            observation, _, termine, tronque, info = environnement.step(int(np.asarray(action).item()))
        durees.append(float(info["index_pas"]) * scenario.pas_minutes / 60.0)
        succes.append(bool(info.get("date_cible_atteinte", False)))
        credits.append(float(info.get("credit_restant_kwh", 0.0)))
        inconforts.append(float(info.get("inconfort_pilotable_cumule_degre_heures", 0.0)))
        energies_servies.append(float(info.get("energie_servie_cumulee_kwh", 0.0)))
        environnement.close()
    return {
        "source_politique": source,
        "source_meteo": sorted(sources_meteo),
        "inventaire_interprete": _inventaire_interprete(scenario),
        "simulations": simulations,
        "duree_mediane_heures": round(float(np.median(durees)), 2),
        "duree_p10_heures": round(float(np.percentile(durees, 10)), 2),
        "duree_p90_heures": round(float(np.percentile(durees, 90)), 2),
        "probabilite_atteindre_date": (
            round(float(np.mean(succes)), 3) if scenario.date_cible is not None else None
        ),
        "credit_final_median_kwh": round(float(np.median(credits)), 3),
        "inconfort_pilotable_median_degre_heures": round(
            float(np.median(inconforts)), 2
        ),
        "energie_servie_mediane_kwh": round(float(np.median(energies_servies)), 3),
        "nature_consommation": "estimation_simulee_recalibrable_par_lectures_woyofal",
    }


def _texte_mode(piece: str | None, mode: str | None) -> str:
    if piece is None or mode is None:
        return "Conserver les modes actuels et réévaluer dans 30 minutes."
    mode_enum = ModeConfort(mode)
    if mode_enum == ModeConfort.ARRET:
        return f"Arrêter la climatisation ou le ventilateur de {piece}."
    if mode_enum == ModeConfort.VENTILATEUR:
        return f"Utiliser le ventilateur de {piece}."
    return f"Régler la climatisation de {piece} à {mode_enum.consigne_c:.0f} °C."


def _compresser_planning(
    trajectoire: list[dict[str, Any]], scenario: Scenario,
) -> dict[str, list[dict[str, Any]]]:
    planning: dict[str, list[dict[str, Any]]] = {piece.nom: [] for piece in scenario.pieces}
    for piece in scenario.pieces:
        segments = planning[piece.nom]
        for pas in trajectoire:
            mode = pas["modes_pieces"][piece.nom]
            debut = datetime.fromisoformat(pas["horodatage"])
            fin = debut + timedelta(minutes=scenario.pas_minutes)
            if segments and segments[-1]["mode"] == mode and segments[-1]["fin"] == debut.isoformat():
                segments[-1]["fin"] = fin.isoformat()
            else:
                mode_enum = ModeConfort(mode)
                segments.append({
                    "debut": debut.isoformat(),
                    "fin": fin.isoformat(),
                    "mode": mode,
                    "consigne_c": mode_enum.consigne_c,
                })
    return planning


def recommander(
    *,
    scenario: Scenario | None = None,
    modele: str | Path | None = None,
    algorithme: str | None = None,
    horizon_heures: int = 4,
) -> dict[str, Any]:
    """Produit une décision pour toutes les pièces et un planning glissant."""

    if horizon_heures < 1 or horizon_heures > 12:
        raise ValueError("horizon_heures doit être compris entre 1 et 12")
    scenario = scenario or charger_scenario(SCENARIO_DEFAUT)
    politique, source = charger_politique(modele, algorithme)
    environnement = _environnement(scenario, scenario.seed)
    source_meteo = environnement.source_meteo_utilisee
    observation, _ = environnement.reset(seed=scenario.seed)
    trajectoire: list[dict[str, Any]] = []
    recommandation_immediate = None
    recommandations_appareils = []
    extinctions_inoccupation = []
    termine = tronque = False
    nombre_pas = min(
        int(horizon_heures * 60 / scenario.pas_minutes), scenario.nombre_pas_max,
    )
    for _ in range(nombre_pas):
        if termine or tronque:
            break
        decision_physique_appliquee = False
        while not decision_physique_appliquee and not (termine or tronque):
            prediction, _ = politique.predict(observation, deterministic=True)
            action = int(np.asarray(prediction).item())
            observation, _, termine, tronque, info = environnement.step(action)
            decision_physique_appliquee = bool(info["decision_physique_appliquee"])

        if info["extinctions_automatiques_inoccupation"]:
            pieces_vides = sorted(info["extinctions_automatiques_inoccupation"])
            if not extinctions_inoccupation or extinctions_inoccupation[-1]["pieces"] != pieces_vides:
                extinctions_inoccupation.append({
                    "horodatage": info["horodatage"],
                    "pieces": pieces_vides,
                    "raison": "Pièce estimée inoccupée selon le profil choisi par le foyer.",
                })
        if recommandation_immediate is None:
            recommandations_pieces = []
            for piece in scenario.pieces:
                mode = ModeConfort(info["actions_recommandees_pieces"][piece.nom])
                recommandations_pieces.append({
                    "piece": piece.nom,
                    "mode": mode.value,
                    "consigne_c": mode.consigne_c,
                    "explication": _texte_mode(piece.nom, mode.value),
                    "occupation_estimee": bool(info["occupations_estimees"][piece.nom]),
                    "temperature_interieure_estimee_c": round(
                        float(info["temperatures_pieces_c"][piece.nom]), 1,
                    ),
                })
            recommandation_immediate = {
                "horodatage": info["horodatage"],
                "recommandations_pieces": recommandations_pieces,
                "recommandation_appareil": info["recommandation_charge"],
                "temperature_exterieure_c": round(float(info["temperature_exterieure_c"]), 1),
                "credit_restant_apres_pas_kwh": round(float(info["credit_restant_kwh"]), 3),
                "consommation_estimee_pas_kwh": round(
                    float(info["energie_demandee_pas_kwh"]), 4,
                ),
                "detail_consommation_pas_kwh": {
                    "non_pilotable": round(float(info["energie_non_pilotable_pas_kwh"]), 4),
                    "charges_flexibles": round(float(info["energie_flexible_pas_kwh"]), 4),
                    "climatisation": round(float(info["energie_climatisation_pas_kwh"]), 4),
                    "ventilateurs": round(float(info["energie_ventilateur_pas_kwh"]), 4),
                },
            }
        if info["recommandation_charge"]:
            recommandations_appareils.append({
                "horodatage": info["horodatage"],
                "appareil": info["appareil_flexible_reporte"],
                "recommandation": info["recommandation_charge"],
            })
        trajectoire.append({
            "horodatage": info["horodatage"],
            "modes_pieces": dict(info["modes_pieces"]),
            "temperatures_pieces_c": {
                nom: round(float(valeur), 2)
                for nom, valeur in info["temperatures_pieces_c"].items()
            },
            "occupations_estimees": dict(info["occupations_estimees"]),
            "credit_restant_kwh": round(float(info["credit_restant_kwh"]), 3),
        })

    puissance_max_kwh = sum(
        (piece.puissance_climatisation_effective_w + piece.puissance_ventilateur_effective_w)
        * scenario.pas_minutes / 60_000.0
        for piece in scenario.pieces
    )
    energie_pilotable_premier_pas = 0.0
    if trajectoire:
        for piece in scenario.pieces:
            mode = ModeConfort(trajectoire[0]["modes_pieces"][piece.nom])
            if mode == ModeConfort.VENTILATEUR:
                energie_pilotable_premier_pas += (
                    piece.puissance_ventilateur_effective_w * scenario.pas_minutes / 60_000.0
                )
            elif mode.consigne_c is not None:
                energie_pilotable_premier_pas += (
                    piece.puissance_climatisation_effective_w * scenario.pas_minutes / 60_000.0
                )
    environnement.close()
    avertissements = [
        "Les températures intérieures sont estimées par pièce sans thermomètre.",
        "La consommation du pas est simulée à partir des appareils et habitudes.",
        "Une puissance inconnue est estimée selon la taille de la pièce.",
        "Le profil d'occupation est une estimation modifiable, pas une détection de présence.",
    ]
    if source_meteo == "fixture_deterministe":
        avertissements.append(
            "La météo utilisée est la fixture locale de démonstration, pas une mesure réelle."
        )
    elif "climatologie" in source_meteo:
        avertissements.append(
            "La partie non couverte par une prévision utilise la climatologie Dakar 2018-2025."
        )
    return {
        "source_politique": source,
        "source_meteo": source_meteo,
        "inventaire_interprete": _inventaire_interprete(scenario),
        "recommandation_immediate": recommandation_immediate,
        "horizon_planification_heures": horizon_heures,
        "planning_par_piece": _compresser_planning(trajectoire, scenario),
        "recommandations_appareils_energivores": recommandations_appareils,
        "extinctions_pieces_inoccupees": extinctions_inoccupation,
        "regle_equite": (
            "La même politique décide pour chaque pièce; aucun nom, numéro ou ordre de chambre "
            "ne reçoit de priorité."
        ),
        "regle_occupation": (
            "Climatisation et ventilateur sont arrêtés lorsque la pièce est estimée vide. "
            "Le foyer choisit un profil simple par pièce : nuit, soirée, journée, variable ou toujours."
        ),
        "credit_lu_code_801_kwh": scenario.credit_initial_kwh,
        "credit_estime_fin_horizon_kwh": (
            trajectoire[-1]["credit_restant_kwh"] if trajectoire else scenario.credit_initial_kwh
        ),
        "economie_estimee_premier_pas_kwh": round(
            max(0.0, puissance_max_kwh - energie_pilotable_premier_pas), 4,
        ),
        "recalcul": "Le planning est indicatif et doit être recalculé toutes les 30 minutes.",
        "facteurs_prise_en_compte": [
            "profil d'occupation choisi pour chaque pièce",
            "cycle jour-nuit",
            "températures intérieure et extérieure estimées",
            "crédit restant et temps jusqu'à la date cible",
            "consommation domestique simulée et charges reportables",
        ],
        "avertissements": avertissements,
    }
