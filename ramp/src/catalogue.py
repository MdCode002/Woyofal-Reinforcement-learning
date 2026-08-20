"""
Catalogue complet des appareils électroménagers pour Dakar (M2).
"""

def get_catalogue_sprint0():
    """Déclaration des appareils de base du Sprint 0."""
    return [
        {"nom": "eclairage_led", "puissance_w": 10, "quantite": 5, "duree_min": 300, "fenetre_usage": (18, 23), "flexible": False},
        {"nom": "tv_led", "puissance_w": 60, "quantite": 1, "duree_min": 240, "fenetre_usage": (19, 23), "flexible": True},
        {"nom": "ventilateur", "puissance_w": 45, "quantite": 2, "duree_min": 480, "fenetre_usage": (12, 22), "flexible": True},
        {"nom": "refrigerateur", "puissance_w": 150, "quantite": 1, "duree_min": 1440, "fenetre_usage": (0, 24), "flexible": False}
    ]


def get_catalogue_sprint1():
    """
    Catalogue complet avec puissance, quantité, fenêtres d'usage, 
    durée et caractère flexible/inflexible (Sprint 1).
    """
    return [
        {
            "nom": "eclairage_led",
            "puissance_w": 10,
            "quantite": 5,
            "duree_min": 300,
            "fenetre_usage": (18, 23),
            "flexible": False
        },
        {
            "nom": "tv_led",
            "puissance_w": 60,
            "quantite": 1,
            "duree_min": 240,
            "fenetre_usage": (19, 23),
            "flexible": True
        },
        {
            "nom": "ventilateur",
            "puissance_w": 45,
            "quantite": 2,
            "duree_min": 480,
            "fenetre_usage": (12, 22),
            "flexible": True
        },
        {
            "nom": "refrigerateur",
            "puissance_w": 150,
            "quantite": 1,
            "duree_min": 1440,
            "fenetre_usage": (0, 24),
            "flexible": False
        },
        {
            "nom": "fer_a_repasser",
            "puissance_w": 1000,
            "quantite": 1,
            "duree_min": 30,
            "fenetre_usage": (8, 12),
            "flexible": True
        },
        {
            "nom": "pompe_eau",
            "puissance_w": 750,
            "quantite": 1,
            "duree_min": 45,
            "fenetre_usage": (6, 9),
            "flexible": True
        },
        {
            "nom": "chauffe_eau",
            "puissance_w": 1500,
            "quantite": 1,
            "duree_min": 60,
            "fenetre_usage": (5, 8),
            "flexible": False
        }
    ]


def get_scenarios_menages():
    """Définit plusieurs types de ménages pour le Sprint 2."""
    base = get_catalogue_sprint1()
    
    # Ménage 1 : Modeste / Économe
    menage_econome = [app for app in base if app["nom"] in ["eclairage_led", "tv_led", "ventilateur", "refrigerateur"]]
    
    # Ménage 2 : Moyen (Catalogue standard)
    menage_moyen = base
    
    # Ménage 3 : Élevé / Confort (+ Climatiseur)
    menage_eleve = base + [{
        "nom": "climatiseur",
        "puissance_w": 1500,
        "quantite": 1,
        "duree_min": 360,
        "fenetre_usage": (21, 5),
        "flexible": True
    }]
    
    return {
        "menage_econome": menage_econome,
        "menage_moyen": menage_moyen,
        "menage_eleve": menage_eleve
    }