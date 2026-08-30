from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite

from common import MeteoPas, ParametresThermiques
from thermal import ModeleThermique1R1C, estimer_temperature_interieure_initiale
from woyofal import CompteurWoyofal, convertir_fcfa_en_kwh, convertir_kwh_en_fcfa


def test_thermique_off_chauffe_on_refroidit():
    meteo = MeteoPas(datetime(2025, 8, 1, tzinfo=timezone.utc), 34.0, 70.0, 0.0)
    parametres = ParametresThermiques(gains_internes_kw=0.1, coefficient_gains_solaires=0.0)
    off = ModeleThermique1R1C(28.0, parametres).step(
        meteo, climatisation_active=False, ventilateur_actif=False, occupation=True
    )
    on = ModeleThermique1R1C(28.0, parametres).step(
        meteo, climatisation_active=True, ventilateur_actif=False, occupation=True
    )
    assert off.temperature_interieure_c > 28.0
    assert on.temperature_interieure_c < 28.0
    assert on.energie_climatisation_kwh == 0.6


def test_thermique_ne_diverge_pas_sur_30_jours():
    meteo = MeteoPas(datetime(2025, 8, 1, tzinfo=timezone.utc), 35.0, 80.0, 800.0)
    modele = ModeleThermique1R1C(29.0, ParametresThermiques(coefficient_gains_solaires=0.0005))
    for _ in range(30 * 48):
        resultat = modele.step(
            meteo, climatisation_active=False, ventilateur_actif=False, occupation=True
        )
    assert isfinite(resultat.temperature_interieure_c)
    assert -10 < resultat.temperature_interieure_c < 60


def test_consigne_eco_consomme_moins_que_boost_quand_elle_suffit():
    meteo = MeteoPas(datetime(2025, 8, 1, tzinfo=timezone.utc), 31.0, 70.0, 0.0)
    parametres = ParametresThermiques(gains_internes_kw=0.1, coefficient_gains_solaires=0.0)
    eco = ModeleThermique1R1C(28.0, parametres).step(
        meteo, climatisation_active=True, ventilateur_actif=False,
        occupation=True, temperature_consigne_c=27.0,
    )
    boost = ModeleThermique1R1C(28.0, parametres).step(
        meteo, climatisation_active=True, ventilateur_actif=False,
        occupation=True, temperature_consigne_c=23.0,
    )
    assert eco.energie_climatisation_kwh < boost.energie_climatisation_kwh
    assert eco.temperature_interieure_c > boost.temperature_interieure_c


def test_temperature_initiale_est_estimee_sans_thermometre():
    meteo = [
        MeteoPas(datetime(2025, 8, 1, hour=heure, tzinfo=timezone.utc), 27 + heure / 12, 70.0, 0.0)
        for heure in range(24)
    ]
    estimation = estimer_temperature_interieure_initiale(
        meteo, ParametresThermiques(coefficient_gains_solaires=0.0), pas_minutes=60
    )
    assert 20.0 < estimation < 40.0


def test_compteur_cap_et_conversion_tarifaire():
    compteur = CompteurWoyofal(0.4)
    resultat = compteur.servir(0.7)
    assert resultat.energie_servie_kwh == 0.4
    assert abs(resultat.energie_non_servie_kwh - 0.3) < 1e-12
    assert resultat.credit_restant_kwh == 0.0
    assert convertir_fcfa_en_kwh(convertir_kwh_en_fcfa(175.0)) == 175.0
