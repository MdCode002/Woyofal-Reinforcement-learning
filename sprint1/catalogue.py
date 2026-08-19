"""
Catalogue des appareils du foyer type - Dakar
Chaque entrée documente : puissance unitaire, quantité, fenêtre(s) d'usage,
durée de fonctionnement quotidienne, variabilité aléatoire, et caractère flexible.
"flexible" = l'usage peut être déplacé dans le temps (ex: fer à repasser)
"non flexible" = usage contraint (frigo en continu, éclairage au moment précis du besoin)
"""

CATALOGUE = [
    {
        "name": "TV",
        "power_W": 100.0,
        "quantity": 1,
        "window_start_min": 1080,  # 18:00
        "window_end_min": 1380,    # 23:00
        "func_time_min": 240,      # 4h d'usage effectif dans la fenêtre
        "random_var": 0.1,
        "flexible": False,         # usage lié au moment de la soirée, peu déplaçable
    },
    {
        "name": "Eclairage_LED",
        "power_W": 12.0,
        "quantity": 5,
        "window_start_min": 1080,  # 18:00
        "window_end_min": 1380,    # 23:00
        "func_time_min": 300,      # 5h cumulées (pièces différentes)
        "random_var": 0.1,
        "flexible": False,         # dépend de la tombée de la nuit
    },
    {
        "name": "Ventilateur",
        "power_W": 50.0,
        "quantity": 2,
        "window_start_min": 720,   # 12:00
        "window_end_min": 1200,    # 20:00
        "func_time_min": 480,      # 8h cumulées (chaleur de journée)
        "random_var": 0.15,
        "flexible": True,          # peut être décalé selon confort thermique
    },
    {
        "name": "Refrigerateur",
        "power_W": 150.0,
        "quantity": 1,
        "window_start_min": 0,     # disponible 24h/24
        "window_end_min": 1440,
        "func_time_min": 600,      # ~10h de marche compresseur cumulée/j (cycles)
        "random_var": 0.1,
        "flexible": False,         # cycle thermostatique non déplaçable
    },
    {
        "name": "Fer_Repasser",
        "power_W": 1200.0,
        "quantity": 1,
        "window_start_min": 420,   # 07:00
        "window_end_min": 540,     # 09:00
        "func_time_min": 30,
        "random_var": 0.2,
        "flexible": True,          # peut être fait à un autre moment de la journée
    },
    {
        "name": "Pompe_Eau",
        "power_W": 750.0,
        "quantity": 1,
        "window_start_min": 360,   # 06:00
        "window_end_min": 600,     # 10:00
        "func_time_min": 45,
        "random_var": 0.2,
        "flexible": True,          # remplissage de réservoir décalable
    },
    {
        "name": "Chauffe_Eau",
        "power_W": 1500.0,
        "quantity": 1,
        "window_start_min": 330,   # 05:30
        "window_end_min": 510,     # 08:30
        "func_time_min": 60,
        "random_var": 0.1,
        "flexible": False,         # lié à l'heure de la douche matinale
    },
]
