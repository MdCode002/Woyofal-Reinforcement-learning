# src/catalogue.py

def get_catalogue_sprint0():
    """
    Déclaration des 4 appareils requis pour le Sprint 0 (M2).
    """
    return [
        {
            "nom": "eclairage_led",
            "puissance_w": 10,
            "duree_min": 300,
            "fenetre_usage": (18, 23)
        },
        {
            "nom": "tv_led",
            "puissance_w": 60,
            "duree_min": 240,
            "fenetre_usage": (19, 23)
        },
        {
            "nom": "ventilateur",
            "puissance_w": 45,
            "duree_min": 480,
            "fenetre_usage": (12, 22)
        },
        {
            "nom": "refrigerateur",
            "puissance_w": 150,
            "duree_min": 1440,
            "fenetre_usage": (0, 24)
        }
    ]