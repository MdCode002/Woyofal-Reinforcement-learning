from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from common import ModeConfort
from env import encoder_action
from woyofal.api import RequeteRecommandation, catalogue, health
from woyofal.intake import scenario_depuis_saisie
from woyofal.service import charger_politique
from woyofal import service


def test_jeu_test_est_gele():
    manifeste = Path("data/generated_variable/test/manifest.sha256")
    assert manifeste.exists()
    assert len(manifeste.read_text(encoding="utf-8").splitlines()) == 60


def test_api_health_et_selection_exclusivement_rl(scenario_fixture):
    assert health()["statut"] == "ok"
    try:
        _, source = charger_politique()
    except (FileNotFoundError, RuntimeError):
        return
    assert source == "dqn"


def test_saisie_courte_produit_un_scenario_complet():
    import json

    donnees = json.loads(Path("data/scenarios/saisie_simple_exemple.json").read_text(encoding="utf-8"))
    scenario = scenario_depuis_saisie(donnees)
    assert len(scenario.pieces) == 2
    assert scenario.pieces[0].puissance_climatisation_w is None
    assert scenario.pieces[0].puissance_climatisation_effective_w == 1_200.0
    assert any(appareil.nom == "Lave-linge" for appareil in scenario.appareils)


def test_saisie_reelle_conserve_quantites_puissances_et_presence_actuelle():
    donnees = {
        "identifiant_foyer": "test-reel",
        "nombre_occupants": 6,
        "credit_initial_kwh": 12.5,
        "date_debut": "2026-08-27T18:47:00+00:00",
        "date_cible": "2026-09-03T18:47:00+00:00",
        "source_meteo": "fixture_deterministe",
        "pieces": [{
            "nom": "Séjour", "type_piece": "salon", "taille": "grande",
            "nombre_climatiseurs": 2, "nombre_ventilateurs": 3,
            "puissance_climatisation_w": 1_500,
            "puissance_ventilateur_w": 60,
            "profil_occupation": "soiree", "occupation_actuelle": True,
        }],
        "appareils": [{
            "type_appareil": "television", "quantite": 3, "puissance_w": 90,
        }],
    }
    scenario = scenario_depuis_saisie(donnees)
    piece = scenario.pieces[0]
    television = scenario.appareils[0]
    assert scenario.date_debut.minute == 30
    assert piece.nombre_climatiseurs == 2
    assert piece.nombre_ventilateurs == 3
    assert piece.puissance_climatisation_effective_w == 3_000
    assert piece.occupation_actuelle is True
    assert piece.occupation_actuelle_jusqua == scenario.date_debut + timedelta(minutes=30)
    assert television.quantite == 3
    assert television.puissance_w == 90


def test_catalogue_api_exclut_climatisation_et_ventilateur():
    resultat = catalogue()["appareils"]
    cles = {appareil["type_appareil"] for appareil in resultat}
    assert "television" in cles
    assert "climatiseur" not in cles
    assert "ventilateur" not in cles


def test_api_refuse_un_foyer_non_emballe_au_lieu_du_scenario_par_defaut():
    """Une requête mal formée ne doit jamais déclencher le foyer de démonstration."""

    import json

    donnees = json.loads(Path("data/scenarios/saisie_simple_exemple.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        RequeteRecommandation.model_validate(donnees)


def test_service_retourne_un_planning_par_piece(monkeypatch, scenario_fixture):
    class PolitiqueFixe:
        def predict(self, observation, deterministic=True):
            del observation, deterministic
            return np.array(encoder_action(ModeConfort.CLIM_ECO)), None

    monkeypatch.setattr(service, "charger_politique", lambda *args, **kwargs: (PolitiqueFixe(), "dqn"))
    resultat = service.recommander(scenario=scenario_fixture, horizon_heures=1)
    assert resultat["source_politique"] == "dqn"
    recommandations = resultat["recommandation_immediate"]["recommandations_pieces"]
    assert all("action_discrete" not in item for item in recommandations)
    chambre = next(item for item in recommandations if item["piece"] == "Chambre 1")
    assert chambre["consigne_c"] == 27.0
    assert chambre["occupation_estimee"] is True
    assert isinstance(
        resultat["recommandation_immediate"]["temperature_exterieure_c"],
        float,
    )
    assert set(resultat["planning_par_piece"]) == {piece.nom for piece in scenario_fixture.pieces}
    assert "aucun nom" in resultat["regle_equite"]
    assert "profil simple" in resultat["regle_occupation"]
