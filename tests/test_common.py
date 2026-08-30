from __future__ import annotations

from common import Piece
from common.units import convertir_en_kwh, convertir_en_watts


def test_conversion_watts_kwh_est_reversible():
    energie = convertir_en_kwh(1_200, 30)
    assert energie == 0.6
    assert convertir_en_watts(energie, 30) == 1_200


def test_scenario_final_est_valide(scenario_fixture):
    assert scenario_fixture.pas_minutes == 30
    assert scenario_fixture.sous_pas_thermique_minutes == 5
    assert 1 <= scenario_fixture.parametres_thermiques.constante_temps_heures <= 4
    assert not hasattr(scenario_fixture, "temperature_interieure_initiale_c")
    assert len(scenario_fixture.pieces) == 3
    assert scenario_fixture.pieces[2].puissance_climatisation_effective_w == 900.0


def test_quantites_confort_donnent_une_puissance_totale():
    piece = Piece(
        nom="Grand séjour", type_piece="salon", taille="grande",
        nombre_climatiseurs=2, nombre_ventilateurs=3,
        puissance_climatisation_w=1_500, puissance_ventilateur_w=60,
    )
    assert piece.climatisation and piece.ventilateur
    assert piece.puissance_climatisation_unitaire_effective_w == 1_500
    assert piece.puissance_climatisation_effective_w == 3_000
    assert piece.puissance_ventilateur_effective_w == 180
