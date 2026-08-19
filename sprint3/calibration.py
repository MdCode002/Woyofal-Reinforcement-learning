"""
SPRINT M2 - Calibration des profils
Objectifs couverts :
  1. Comparer les profils simulés aux ordres de grandeur retenus pour les
     ménages prépayés (tranches tarifaires Woyofal / Senelec)
  2. Contrôler la consommation mensuelle, la pointe du soir et l'effet
     de la saison chaude
  3. Préparer l'usage des informations compteur Woyofal :
       801 solde | 820 mois précédent | 814 mois en cours | 813 & 808 (option)
  4. Ajuster les fenêtres d'usage et la charge de fond SANS reproduire
     exactement un historique (validation par ordre de grandeur, pas
     par calage point à point -> on garde l'aléa RAMP à chaque run)

Note de méthode : les bornes de tranches Woyofal (150 / 250 kWh) et le
tarif (~100 FCFA/kWh en tranche basse) sont des ordres de grandeur publics
couramment cités pour la clientèle domestique "petite puissance" ; ce sont
des repères de calibration, pas des données de facturation officielles
exactes (elles évoluent et dépendent du profil tarifaire du client).
"""

from unittest.mock import patch
import numpy as np
import pandas as pd
from ramp import Appliance, UseCase, User

from catalogue import SCENARIOS

NUM_DAYS = 30                    # 1 mois simulé
SEASON_FACTOR_HOT = 1.35         # +35% de temps d'usage pour les appareils "season_sensitive"
EVENING_START_H, EVENING_END_H = 18, 23   # fenêtre attendue de la pointe du soir
TARIF_FCFA_PAR_KWH = 100.0       # ordre de grandeur tranche basse (à ajuster si besoin)

# Repères Woyofal : bornes de tranches mensuelles couramment citées (kWh/mois)
# pour la clientèle domestique "petite puissance" - ordres de grandeur, pas
# des seuils contractuels universels.
TRANCHES_KWH_MOIS = {
    "Tranche_1 (sociale)": (0, 150),
    "Tranche_2": (150, 400),
    "Tranche_3": (400, np.inf),
}


def classer_tranche(kwh_mois):
    for label, (lo, hi) in TRANCHES_KWH_MOIS.items():
        if lo <= kwh_mois < hi:
            return label
    return "Hors grille"


def create_appliance_from_catalog(user, entry, season_factor=1.0):
    """Construit un Appliance RAMP ; applique un facteur saison sur le
    func_time des appareils marqués 'season_sensitive' (ventilateur, frigo,
    climatiseur). Si la fenêtre d'origine devient trop courte pour la
    nouvelle durée, on l'élargit symétriquement (usage plus tôt/plus tard
    dans la journée en saison chaude) - les autres appareils ne sont pas
    touchés."""
    func_time = entry["func_time_min"]
    window_start = entry["window_start_min"]
    window_end = entry["window_end_min"]

    if entry.get("season_sensitive") and season_factor != 1.0:
        func_time = min(1440, func_time * season_factor)
        marge = int(np.ceil(func_time * 1.15))  # marge de sécurité pour l'aléa RAMP
        largeur_actuelle = window_end - window_start
        if marge > largeur_actuelle:
            besoin = marge - largeur_actuelle
            extension_droite = min(besoin, 1440 - window_end)
            reste = besoin - extension_droite
            window_end = window_end + extension_droite
            window_start = max(0, window_start - reste)
        func_time = int(func_time)
        # garde-fou final : le func_time ne doit jamais dépasser la fenêtre
        func_time = min(func_time, window_end - window_start)

    app = Appliance(
        user,
        number=entry["quantity"],
        power=entry["power_W"],
        num_windows=1,
        func_time=func_time,
        time_fraction_random_variability=entry["time_var"],
        thermal_p_var=entry["power_var"],
        name=entry["name"],
    )
    app.windows(
        window_1=[window_start, window_end],
        random_var_w=entry["random_var"],
    )
    return app


def simulate_month(scenario_name, catalog, season_factor=1.0, num_days=NUM_DAYS, seed=None):
    """Simule un mois (num_days) de profils 1-min pour un foyer, avec un
    facteur saison optionnel appliqué aux appareils sensibles."""
    if seed is not None:
        np.random.seed(seed)

    user = User(scenario_name, 1)
    for entry in catalog:
        create_appliance_from_catalog(user, entry, season_factor=season_factor)

    use_case = UseCase(users=[user], date_start="2026-01-01")
    with patch("builtins.input", return_value="1"):
        use_case.initialize(num_days=num_days)

    profiles = use_case.generate_daily_load_profiles(flat=False)
    return np.array(profiles).reshape(num_days, 1440)


# ==========================================================
# 1 & 2. SIMULATION MENSUELLE : saison fraiche vs saison chaude
# ==========================================================
resultats = []
profils_par_scenario = {}   # pour les champs compteur ensuite

for i, (scenario_name, catalog) in enumerate(SCENARIOS.items()):
    profils_fraiche = simulate_month(scenario_name, catalog, season_factor=1.0, seed=100 + i)
    profils_chaude = simulate_month(scenario_name, catalog, season_factor=SEASON_FACTOR_HOT, seed=200 + i)

    profils_par_scenario[scenario_name] = {
        "fraiche": profils_fraiche,
        "chaude": profils_chaude,
    }

    for saison, profils in (("Fraiche", profils_fraiche), ("Chaude", profils_chaude)):
        kwh_mois = profils.sum() / 60000.0
        pic_instantane_W = profils.max()  # peut être un gros appareil ponctuel (chauffe-eau...)

        # profil moyen minute par minute sur le mois, pour lisser l'aléa RAMP
        profil_moyen_jour = profils.mean(axis=0)

        # Pointe du soir = pic du profil moyen restreint au créneau 18h-23h,
        # comparé à la moyenne journalière -> détecte un vrai "bosse" du soir,
        # sans se faire polluer par un pic ponctuel matinal (fer/chauffe-eau).
        idx_soir = slice(EVENING_START_H * 60, EVENING_END_H * 60)
        pic_soir_W = profil_moyen_jour[idx_soir].max()
        heure_pic_soir = (idx_soir.start + np.argmax(profil_moyen_jour[idx_soir])) / 60.0
        moyenne_jour_W = profil_moyen_jour.mean()
        ratio_soir_moyenne = pic_soir_W / moyenne_jour_W if moyenne_jour_W > 0 else np.nan

        # charge de fond = 5e percentile de puissance (creux de nuit), plus robuste
        # qu'un minimum strict pouvant tomber sur un artefact d'une seule minute
        charge_de_fond_W = np.percentile(profils, 5, axis=1).mean()

        resultats.append(
            {
                "scenario": scenario_name,
                "saison": saison,
                "kWh_mois": kwh_mois,
                "tranche_woyofal": classer_tranche(kwh_mois),
                "pic_instantane_W": round(pic_instantane_W, 0),
                "pic_soir_W": round(pic_soir_W, 1),
                "heure_pic_soir": round(heure_pic_soir, 2),
                "ratio_pic_soir_vs_moyenne": round(ratio_soir_moyenne, 2),
                "charge_de_fond_W": round(charge_de_fond_W, 1),
            }
        )

df_resultats = pd.DataFrame(resultats)

print("=== 1. COMPARAISON AUX ORDRES DE GRANDEUR WOYOFAL (mensuel) ===")
print(df_resultats.to_string(index=False))

print("\n=== 2. CONTROLE POINTE DU SOIR ===")
print(
    "(on vérifie qu'il existe une vraie bosse de charge en soirée, en comparant\n"
    " le pic du créneau 18h-23h à la moyenne journalière - pas au pic instantané\n"
    " global, qui peut être dominé par un gros appareil ponctuel le matin)\n"
)
for _, row in df_resultats.iterrows():
    statut = "OK (pointe soir marquée)" if row["ratio_pic_soir_vs_moyenne"] >= 1.3 else "A VERIFIER (pointe soir faible)"
    h = row["heure_pic_soir"]
    print(
        f"{row['scenario']:15s} ({row['saison']:7s}) -> pic soir {row['pic_soir_W']:7.1f} W vers "
        f"{int(h)}h{int((h%1)*60):02d}, x{row['ratio_pic_soir_vs_moyenne']:.2f} la moyenne journalière "
        f"[{statut}]  | pic instantané journée: {row['pic_instantane_W']:.0f} W"
    )

print("\n=== 2bis. EFFET SAISON CHAUDE ===")
pivot = df_resultats.pivot(index="scenario", columns="saison", values="kWh_mois")
pivot["delta_pct"] = (pivot["Chaude"] - pivot["Fraiche"]) / pivot["Fraiche"] * 100
print(pivot.round(2).to_string())

# ==========================================================
# 3. PREPARATION DES CHAMPS COMPTEUR WOYOFAL (801/820/814/813/808)
# ==========================================================
print("\n=== 3. CHAMPS COMPTEUR WOYOFAL SIMULES ===")


def construire_fiche_compteur(scenario_name, profils_mois, solde_initial_fcfa, jour_courant):
    """Construit, pour un jour donné du mois en cours, les champs qu'un
    compteur Woyofal afficherait. Ne fait AUCUN calage sur un historique
    réel : les valeurs proviennent uniquement de la simulation RAMP.

    jour_courant : index 1..NUM_DAYS, jour "aujourd'hui" dans le mois en cours
    """
    kwh_mois_precedent = None  # nécessite le mois N-1 ; voir usage plus bas
    kwh_mois_courant = profils_mois[: jour_courant].sum() / 60000.0
    kwh_veille = profils_mois[jour_courant - 1].sum() / 60000.0
    puissance_instantanee_W = profils_mois[jour_courant - 1, -1]  # dernière minute connue

    cout_fcfa = kwh_mois_courant * TARIF_FCFA_PAR_KWH
    solde_restant_fcfa = max(0.0, solde_initial_fcfa - cout_fcfa)

    return {
        "801_solde_FCFA": round(solde_restant_fcfa, 0),
        "814_conso_mois_en_cours_kWh": round(kwh_mois_courant, 2),
        "813_conso_veille_kWh": round(kwh_veille, 2),          # option
        "808_puissance_instantanee_W": round(puissance_instantanee_W, 1),  # option
    }


SOLDE_INITIAL_FCFA = 30000.0  # hypothèse de recharge en début de mois
JOUR_COURANT = 15             # exemple : on se place au 15e jour du mois

fiches = []
for scenario_name in SCENARIOS:
    profils_mois_precedent = profils_par_scenario[scenario_name]["fraiche"]
    profils_mois_courant = profils_par_scenario[scenario_name]["chaude"]

    kwh_820_mois_precedent = profils_mois_precedent.sum() / 60000.0

    fiche = construire_fiche_compteur(
        scenario_name, profils_mois_courant, SOLDE_INITIAL_FCFA, JOUR_COURANT
    )
    fiche["scenario"] = scenario_name
    fiche["820_conso_mois_precedent_kWh"] = round(kwh_820_mois_precedent, 2)
    fiches.append(fiche)

df_compteur = pd.DataFrame(fiches)[
    [
        "scenario",
        "801_solde_FCFA",
        "820_conso_mois_precedent_kWh",
        "814_conso_mois_en_cours_kWh",
        "813_conso_veille_kWh",
        "808_puissance_instantanee_W",
    ]
]
print(f"(instantané simulé au jour {JOUR_COURANT} du mois, solde initial {SOLDE_INITIAL_FCFA:.0f} FCFA)")
print(df_compteur.to_string(index=False))

df_compteur.to_csv("fiches_compteur_woyofal.csv", index=False)
print("\nExport : fiches_compteur_woyofal.csv")

# ==========================================================
# 4. RAPPEL METHODOLOGIQUE - PAS DE CALAGE SUR HISTORIQUE
# ==========================================================
print("\n=== 4. NOTE DE CALIBRATION ===")
print(
    "Les fenêtres d'usage et la charge de fond ont été ajustées pour retomber\n"
    "dans les bons ordres de grandeur (tranches Woyofal, pointe du soir,\n"
    "delta saison chaude), mais chaque simulation reste stochastique\n"
    "(graines différentes, variabilité RAMP active) : le but est un profil\n"
    "PLAUSIBLE et cohérent avec les repères connus, pas la reproduction\n"
    "exacte d'un relevé de compteur historique précis."
)
