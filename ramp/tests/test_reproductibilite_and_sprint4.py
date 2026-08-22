"""
tests/test_reproductibilite_and_sprint4.py : Validation du Sprint 4 et vérification des données.
"""
import os
import pandas as pd
from src.domain_randomization import POOL_APPAREILS, T_CONFORT_C


def test_constantes_domain_randomization():
    """Vérifie la présence des constantes de randomisation de domaine."""
    assert POOL_APPAREILS is not None
    assert isinstance(T_CONFORT_C, (int, float))


def test_fichiers_sprint4_existants():
    """Vérifie que les jeux de données et cas extrêmes du Sprint 4 ont bien été générés."""
    fichiers_attendus = [
        "data/scenarios_train.csv",
        "data/scenarios_val.csv",
        "data/scenarios_test.csv",
        "data/extreme_cas_resume.csv",
        "data/extreme_historique_perturbe.csv",
        "data/extreme_historique_anomalies.csv",
    ]
    for f in fichiers_attendus:
        assert os.path.exists(f), f"Le fichier {f} est manquant dans data/ !"


def test_contenu_scenarios():
    """Vérifie que les fichiers de scénarios contiennent des données valides."""
    df_train = pd.read_csv("data/scenarios_train.csv")
    assert not df_train.empty
    assert "scenario_id" in df_train.columns or "day_index" in df_train.columns