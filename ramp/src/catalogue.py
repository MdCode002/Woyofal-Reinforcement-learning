# src/catalogue.py

def get_catalogue_sprint0():
    """Déclaration des 4 appareils de base du Sprint 0."""
    return [
        {"nom": "eclairage_led", "puissance_w": 10, "duree_min": 300, "fenetre_usage": (18, 23)},
        {"nom": "tv_led", "puissance_w": 60, "duree_min": 240, "fenetre_usage": (19, 23)},
        {"nom": "ventilateur", "puissance_w": 45, "duree_min": 480, "fenetre_usage": (12, 22)},
        {"nom": "refrigerateur", "puissance_w": 150, "duree_min": 1440, "fenetre_usage": (0, 24)}
    ]

# ==========================================
# SPRINT 1 : INCRÉMENT CATALOGUE DAKAR
# ==========================================
def get_catalogue_sprint1():
    """
    Catalogue Sprint 1 : Reprend les appareils de base et affine 
    les fenêtres d'usage pour un foyer à Dakar.
    """
    catalogue = get_catalogue_sprint0()
    
    # On peut affiner les plages ou ajouter des équipements types
    for app in catalogue:
        if app["nom"] == "ventilateur":
            app["duree_min"] = 600  # Usage plus intense à Dakar
            
    return catalogue