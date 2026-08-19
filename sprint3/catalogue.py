"""
Catalogue des appareils - foyers types de Dakar
Chaque entrée documente : puissance unitaire, quantité, fenêtre(s) d'usage,
durée de fonctionnement, variabilité (horaire / durée / puissance),
et caractère flexible ou non.

Variabilité stochastique (Sprint M2 - Profils stochastiques) :
  - random_var       -> variabilité des HORAIRES (déplacement de la fenêtre d'usage)
  - time_var         -> variabilité de la DUREE de fonctionnement
  - power_var        -> variabilité de la PUISSANCE appelée (thermal_p_var RAMP)
"""

# --------------------------------------------------------------------
# Catalogue de référence "Foyer Standard" (M2)
# --------------------------------------------------------------------
CATALOGUE_STANDARD = [
    {
        "name": "TV",
        "power_W": 100.0,
        "quantity": 1,
        "window_start_min": 1080,
        "window_end_min": 1380,
        "func_time_min": 240,
        "random_var": 0.10,
        "time_var": 0.10,
        "power_var": 0.05,
        "flexible": False,
        "season_sensitive": False,
    },
    {
        "name": "Eclairage_LED",
        "power_W": 12.0,
        "quantity": 5,
        "window_start_min": 1080,
        "window_end_min": 1380,
        "func_time_min": 300,
        "random_var": 0.10,
        "time_var": 0.10,
        "power_var": 0.02,
        "flexible": False,
        "season_sensitive": False,
    },
    {
        "name": "Ventilateur",
        "power_W": 50.0,
        "quantity": 2,
        "window_start_min": 720,
        "window_end_min": 1200,
        "func_time_min": 480,
        "random_var": 0.15,
        "time_var": 0.15,
        "power_var": 0.10,
        "flexible": True,
        "season_sensitive": True,   # usage accru en saison chaude
    },
    {
        "name": "Refrigerateur",
        "power_W": 150.0,
        "quantity": 1,
        "window_start_min": 0,
        "window_end_min": 1440,
        "func_time_min": 600,
        "random_var": 0.10,
        "time_var": 0.10,
        "power_var": 0.08,
        "flexible": False,
        "season_sensitive": True,   # compresseur cycle plus en saison chaude
    },
    {
        # Décalé après la douche/chauffe-eau pour éviter un cumul irréaliste
        # (repassage + douche chaude + pompe en même temps).
        "name": "Fer_Repasser",
        "power_W": 1200.0,
        "quantity": 1,
        "window_start_min": 480,   # 08:00
        "window_end_min": 600,     # 10:00
        "func_time_min": 30,
        "random_var": 0.20,
        "time_var": 0.20,
        "power_var": 0.05,
        "flexible": True,
        "season_sensitive": False,
    },
    {
        # Décalé en milieu de matinée : remplissage de réservoir, indépendant
        # du pic douche/petit-déjeuner de 6h-8h.
        "name": "Pompe_Eau",
        "power_W": 750.0,
        "quantity": 1,
        "window_start_min": 600,   # 10:00
        "window_end_min": 780,     # 13:00
        "func_time_min": 45,
        "random_var": 0.20,
        "time_var": 0.20,
        "power_var": 0.05,
        "flexible": True,
        "season_sensitive": False,
    },
    {
        "name": "Chauffe_Eau",
        "power_W": 1500.0,
        "quantity": 1,
        "window_start_min": 330,   # 05:30
        "window_end_min": 450,     # 07:30
        "func_time_min": 60,
        "random_var": 0.10,
        "time_var": 0.10,
        "power_var": 0.10,
        "flexible": False,
        "season_sensitive": False,
    },
    {
        # Charge de fond : chargeurs, routeur wifi, veille TV/box, etc.
        # Toujours active à faible puissance -> fixe le plancher de conso (base load).
        "name": "Veille_Divers",
        "power_W": 15.0,
        "quantity": 1,
        "window_start_min": 0,
        "window_end_min": 1440,
        "func_time_min": 1440,
        "random_var": 0.0,
        "time_var": 0.0,
        "power_var": 0.05,
        "flexible": False,
        "season_sensitive": False,
    },
]

# --------------------------------------------------------------------
# Scénario "Foyer Modeste" : moins d'appareils, pas de chauffe-eau/pompe
# --------------------------------------------------------------------
CATALOGUE_MODESTE = [
    dict(a, quantity=1) for a in CATALOGUE_STANDARD
    if a["name"] in ("TV", "Eclairage_LED", "Ventilateur", "Refrigerateur", "Veille_Divers")
]

# --------------------------------------------------------------------
# Scénario "Foyer Aise" : catalogue standard + climatiseur + plus d'éclairage
# --------------------------------------------------------------------
CATALOGUE_AISE = [dict(a) for a in CATALOGUE_STANDARD]
for a in CATALOGUE_AISE:
    if a["name"] == "Eclairage_LED":
        a["quantity"] = 8
CATALOGUE_AISE.append(
    {
        "name": "Climatiseur",
        "power_W": 1000.0,
        "quantity": 1,
        "window_start_min": 1260,  # 21:00
        "window_end_min": 1440,    # minuit
        "func_time_min": 180,
        "random_var": 0.10,
        "time_var": 0.15,
        "power_var": 0.15,
        "flexible": False,
        "season_sensitive": True,  # climatiseur : usage très accru en saison chaude
    }
)

# --------------------------------------------------------------------
# Registre des scénarios / types de ménages disponibles
# --------------------------------------------------------------------
SCENARIOS = {
    "Foyer_Modeste": CATALOGUE_MODESTE,
    "Foyer_Standard": CATALOGUE_STANDARD,
    "Foyer_Aise": CATALOGUE_AISE,
}

# Conservé pour compatibilité avec le sprint précédent
CATALOGUE = CATALOGUE_STANDARD
