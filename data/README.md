# Données

**Responsable principal : M2.** Ce dossier contient uniquement les entrées versionnées ou les pointeurs vers des sources externes.

## Contenu attendu

- `scenarios/` : configurations de foyers ;
- `weather/` : `horodatage`, `temperature_c`, `humidite_pourcent`, `rayonnement_solaire_w_m2` ;
- `appliances/` : nom, puissance W, caractère flexible/essentiel, fenêtres probables, durée et variabilité ;
- `households/` : occupation et caractéristiques utiles du logement ;
- `meter/` : données Woyofal anonymisées (801 obligatoire ; 820/814 recommandés ; 813/808 facultatifs).

## Entrées et sorties

M2 lira les sources brutes ici et fournira à `ramp/` des données nettoyées. Les horodatages sont ISO 8601 avec fuseau, la puissance est en W et l'énergie en kWh.

## Qualité attendue

Documenter source, licence, période, fuseau, fréquence, valeurs manquantes, transformations et limites. Ne jamais versionner de données personnelles non anonymisées.

## Exemple

`scenarios/foyer_fictif.json` est l'entrée commune du Sprint 0. Toutes ses valeurs sont fictives. Les fenêtres indiquent des périodes possibles avec une probabilité et non des horaires connus à l'avance.

## Ce que ce dossier ne doit pas contenir

Pas de logique métier, d'environnement virtuel, de modèle entraîné ni de résultats produits.
