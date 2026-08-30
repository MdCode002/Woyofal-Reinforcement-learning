from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from gymnasium.utils.env_checker import check_env
import numpy as np

from common import MeteoPas, ModeConfort, Piece, ProfilChargePas
from env import (
    DIMENSION_OBSERVATION,
    NOMBRE_ACTIONS,
    EnvironnementPiece,
    EnvironnementWoyofal,
    creer_environnement,
    encoder_action,
)
from ramp_adapter.catalogue import construire_appareil


def _avancer_pas(environnement, modes=None, *, report=False):
    """Décide une fois pour chaque pièce puis avance de 30 minutes."""

    modes = modes or {}
    resultat = None
    for numero in range(len(environnement._pieces)):
        nom = environnement._pieces[environnement._index_piece_courante].nom
        resultat = environnement.step(encoder_action(modes.get(nom, ModeConfort.ARRET), report))
        assert resultat[4]["decision_physique_appliquee"] is (numero == len(environnement._pieces) - 1)
    assert resultat is not None
    return resultat


def test_check_env_et_reset_deterministe():
    environnement = creer_environnement(seed=12)
    check_env(environnement, skip_render_check=True)
    observation_1, _ = environnement.reset(seed=99)
    transition_1 = environnement.step(encoder_action(ModeConfort.VENTILATEUR))
    observation_2, _ = environnement.reset(seed=99)
    transition_2 = environnement.step(encoder_action(ModeConfort.VENTILATEUR))
    assert observation_1.shape == (DIMENSION_OBSERVATION,)
    assert environnement.action_space.n == NOMBRE_ACTIONS == 10
    np.testing.assert_array_equal(observation_1, observation_2)
    np.testing.assert_array_equal(transition_1[0], transition_2[0])
    assert transition_1[1:] == transition_2[1:]


def test_report_ne_perd_pas_energie(scenario_fixture):
    scenario = replace(
        scenario_fixture,
        date_debut=scenario_fixture.date_debut.replace(hour=6),
        date_cible=None,
        horizon_max_minutes=90,
        credit_initial_kwh=2.0,
    )
    profils, meteo = [], []
    for index in range(3):
        heure = scenario.date_debut + timedelta(minutes=30 * index)
        profils.append(ProfilChargePas(
            horodatage=heure, pas_minutes=30,
            puissance_demandee_par_appareil_w={"Fer à repasser": 800.0 if index == 0 else 0.0},
            energie_demandee_par_appareil_kwh={"Fer à repasser": 0.4 if index == 0 else 0.0},
            energie_non_pilotable_kwh=0.0,
            charges_decalables_kwh={"Fer à repasser": 0.4} if index == 0 else {},
        ))
        meteo.append(MeteoPas(heure, 28.0, 70.0, 0.0))
    environnement = EnvironnementWoyofal(scenario, profils, meteo)
    environnement.reset(seed=1)
    _, _, termine, tronque, info = _avancer_pas(environnement, report=True)
    assert not termine and not tronque
    assert info["energie_servie_pas_kwh"] == 0.0
    _, _, _, _, info = _avancer_pas(environnement)
    assert info["energie_servie_cumulee_kwh"] == 0.4
    assert info["energie_taches_en_attente_kwh"] == 0.0


def test_report_concerne_toutes_les_portions_du_meme_lave_linge(scenario_fixture):
    scenario = replace(
        scenario_fixture,
        date_debut=scenario_fixture.date_debut.replace(hour=8),
        date_cible=None,
        horizon_max_minutes=90,
        credit_initial_kwh=3.0,
        appareils=(*scenario_fixture.appareils, construire_appareil("lave_linge")),
    )
    profils, meteo = [], []
    for index in range(3):
        heure = scenario.date_debut + timedelta(minutes=30 * index)
        energie = 0.25 if index < 2 else 0.0
        profils.append(ProfilChargePas(
            horodatage=heure, pas_minutes=30,
            puissance_demandee_par_appareil_w={"Lave-linge": energie * 2_000},
            energie_demandee_par_appareil_kwh={"Lave-linge": energie},
            energie_non_pilotable_kwh=0.0,
            charges_decalables_kwh={"Lave-linge": energie} if energie else {},
        ))
        meteo.append(MeteoPas(heure, 28.0, 70.0, 0.0))
    environnement = EnvironnementWoyofal(scenario, profils, meteo)
    environnement.reset(seed=4)
    _avancer_pas(environnement, report=True)
    _, _, _, _, info = _avancer_pas(environnement, report=True)
    assert info["energie_servie_cumulee_kwh"] == 0.0
    assert info["energie_taches_en_attente_kwh"] == 0.5
    _, _, _, _, info = _avancer_pas(environnement)
    assert info["energie_servie_cumulee_kwh"] == 0.5


def test_pieces_sont_pilotees_independamment_sans_priorite(scenario_fixture):
    scenario = replace(
        scenario_fixture,
        date_debut=scenario_fixture.date_debut.replace(hour=21),
        date_cible=None,
    )
    environnement = creer_environnement(scenario, seed=22)
    environnement.reset(seed=22)
    _, _, _, _, info = _avancer_pas(environnement, {
        "Chambre 1": ModeConfort.CLIM_ECO,
        "Salon": ModeConfort.VENTILATEUR,
        "Chambre 2": ModeConfort.CLIM_CONFORT,
    })
    assert info["modes_pieces"] == {
        "Chambre 1": ModeConfort.CLIM_ECO.value,
        "Salon": ModeConfort.VENTILATEUR.value,
        "Chambre 2": ModeConfort.CLIM_CONFORT.value,
    }


def test_nuit_eteint_salon_mais_pas_chambre(scenario_fixture):
    scenario = replace(
        scenario_fixture,
        date_debut=scenario_fixture.date_debut.replace(hour=23, minute=0),
        date_cible=None,
        horizon_max_minutes=30,
        credit_initial_kwh=5.0,
    )
    horodatage = scenario.date_debut
    profil = ProfilChargePas(horodatage, 30, {}, {}, 0.0, {})
    environnement = EnvironnementWoyofal(
        scenario, [profil], [MeteoPas(horodatage, 31.0, 75.0, 0.0)],
    )
    environnement.reset(seed=7)
    _, _, _, _, info = _avancer_pas(environnement, {
        "Chambre 1": ModeConfort.VENTILATEUR,
        "Salon": ModeConfort.VENTILATEUR,
    })
    assert info["modes_pieces"]["Chambre 1"] == ModeConfort.VENTILATEUR.value
    assert info["modes_pieces"]["Salon"] == ModeConfort.ARRET.value
    assert info["extinctions_automatiques_nuit"] == ["Salon"]
    assert info["energie_ventilateur_pas_kwh"] == 0.0275


def test_salon_reste_eteint_a_six_heures_car_inoccupe(scenario_fixture):
    scenario = replace(
        scenario_fixture,
        date_debut=scenario_fixture.date_debut.replace(hour=6, minute=0),
        date_cible=None,
        horizon_max_minutes=30,
        credit_initial_kwh=5.0,
    )
    horodatage = scenario.date_debut
    profil = ProfilChargePas(horodatage, 30, {}, {}, 0.0, {})
    environnement = EnvironnementWoyofal(
        scenario, [profil], [MeteoPas(horodatage, 30.0, 75.0, 0.0)],
    )
    environnement.reset(seed=8)
    _, _, _, _, info = _avancer_pas(environnement, {"Salon": ModeConfort.VENTILATEUR})
    assert not info["occupations_estimees"]["Salon"]
    assert info["modes_pieces"]["Salon"] == ModeConfort.ARRET.value
    assert info["extinctions_automatiques_inoccupation"] == ["Salon"]
    assert info["energie_ventilateur_pas_kwh"] == 0.0


def test_observation_distingue_budget_journalier_serre_et_genereux(scenario_fixture):
    serre, _ = creer_environnement(scenario_fixture, seed=5).reset(seed=5)
    genereux, _ = creer_environnement(
        replace(scenario_fixture, credit_initial_kwh=100.0), seed=5,
    ).reset(seed=5)
    assert genereux[8] > serre[8]


def test_sous_environnement_piece_est_gymnasium_et_normalise_action_impossible(scenario_fixture):
    scenario = replace(
        scenario_fixture,
        date_debut=scenario_fixture.date_debut.replace(hour=12),
        date_cible=None,
    )
    environnement = creer_environnement(scenario, seed=23)
    environnement.reset(seed=23)
    assert isinstance(environnement._environnements_pieces[0], EnvironnementPiece)
    check_env(environnement._environnements_pieces[0], skip_render_check=True)
    environnement.reset(seed=23)
    _, _, _, _, info = _avancer_pas(environnement, {"Salon": ModeConfort.CLIM_ECO})
    assert info["action_invalide_normalisee"]
    assert info["actions_recommandees_pieces"]["Salon"] == ModeConfort.VENTILATEUR.value


def test_fins_credit_et_date_cible(scenario_fixture):
    environnement = creer_environnement(replace(scenario_fixture, credit_initial_kwh=0.0))
    environnement.reset(seed=2)
    _, _, termine, tronque, info = _avancer_pas(environnement)
    assert termine and not tronque and info["raison_fin"] == "credit_epuise"

    cible = scenario_fixture.date_debut + timedelta(minutes=30)
    environnement = creer_environnement(
        replace(scenario_fixture, date_cible=cible, horizon_max_minutes=60),
    )
    environnement.reset(seed=2)
    _, _, termine, tronque, info = _avancer_pas(environnement)
    assert termine and not tronque and info["date_cible_atteinte"]


def test_meme_environnement_supporte_sept_pieces(scenario_fixture):
    pieces = tuple(
        Piece(
            nom=f"Chambre {numero + 1}", type_piece="chambre",
            taille="moyenne", climatisation=numero % 2 == 0,
            ventilateur=True, profil_occupation="nuit",
        )
        for numero in range(7)
    )
    scenario = replace(
        scenario_fixture, pieces=pieces, date_cible=None, horizon_max_minutes=30,
    )
    environnement = creer_environnement(scenario, seed=31)
    observation, _ = environnement.reset(seed=31)
    assert observation.shape == (DIMENSION_OBSERVATION,)
    _, _, _, tronque, info = _avancer_pas(
        environnement, {piece.nom: ModeConfort.VENTILATEUR for piece in pieces},
    )
    assert tronque
    assert info["nombre_pieces"] == 7
    assert set(info["actions_recommandees_pieces"]) == {piece.nom for piece in pieces}
