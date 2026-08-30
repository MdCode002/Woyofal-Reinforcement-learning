from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import random

import numpy as np

from ramp_adapter import generer_profils_ramp
from ramp_adapter.catalogue import construire_appareil
from ramp_adapter.scenarios import _pieces


def _vecteur(profils):
    return np.array([
        [*p.energie_demandee_par_appareil_kwh.values()]
        for p in profils
    ])


def test_ramp_seed_et_48_pas(scenario_fixture):
    premier = generer_profils_ramp(scenario_fixture, nombre_jours=1, seed=123)
    second = generer_profils_ramp(scenario_fixture, nombre_jours=1, seed=123)
    different = generer_profils_ramp(scenario_fixture, nombre_jours=1, seed=124)
    assert len(premier) == 48
    np.testing.assert_allclose(_vecteur(premier), _vecteur(second), atol=0, rtol=0)
    assert not np.array_equal(_vecteur(premier), _vecteur(different))


def test_ramp_conserve_energie_et_exclut_controles(scenario_fixture):
    profils = generer_profils_ramp(scenario_fixture, nombre_jours=1, seed=7)
    for profil in profils:
        somme = sum(profil.energie_demandee_par_appareil_kwh.values())
        decomposee = profil.energie_non_pilotable_kwh + sum(profil.charges_decalables_kwh.values())
        assert abs(somme - decomposee) < 1e-12
        noms = " ".join(profil.energie_demandee_par_appareil_kwh).lower()
        assert "clim" not in noms
        assert "ventil" not in noms


def test_ramp_respecte_heure_debut_non_minuit(scenario_fixture):
    scenario = replace(
        scenario_fixture,
        date_debut=scenario_fixture.date_debut.replace(hour=22, minute=30),
        date_cible=None,
    )
    profils = generer_profils_ramp(scenario, nombre_jours=1, seed=9)
    assert len(profils) == 48
    assert profils[0].horodatage == scenario.date_debut
    assert profils[-1].horodatage == scenario.date_debut + timedelta(minutes=47 * 30)


def test_scenarios_exposent_le_rl_a_plusieurs_dispositions_de_pieces():
    inventaire = (construire_appareil("climatiseur"), construire_appareil("ventilateur"))
    layouts = set()
    positions_climatisees = set()
    for index in range(200):
        pieces = _pieces(
            random.Random(10_000 + index), inventaire,
            entrainement=True, index=index,
        )
        layouts.add(tuple(piece.type_piece for piece in pieces))
        positions_climatisees.update(
            numero for numero, piece in enumerate(pieces) if piece.climatisation
        )
    assert any(len(layout) >= 7 for layout in layouts)
    assert any("salon" in layout for layout in layouts)
    assert positions_climatisees.issuperset({0, 1, 2, 3, 4, 5, 6})
