# Modèle thermique

**Responsable principal : M3.**

## Objectif

Calculer l'évolution de la température intérieure et l'énergie électrique de climatisation avec un modèle 1R1C.

## Entrées

Températures intérieure/extérieure en °C, R en °C/kW, C en kWh/°C, état de la climatisation, COP et durée en minutes.

## Sortie

La température intérieure en °C et l'énergie HVAC en kWh, agrégées sur le pas de décision. Des sous-pas internes de 5 à 15 minutes sont autorisés. M3 choisira la structure interne avant de la proposer à l'équipe.

## Travail attendu de M3

Créer le prototype 1R1C, documenter R/C/COP, ajouter les gains internes/solaires utiles et tester la stabilité. Les paramètres incertains seront ensuite randomisés dans des plages plausibles.

## Tests obligatoires

Clim OFF par temps chaud : température monte ; clim ON : température baisse et énergie positive ; R/C/COP invalides : erreur ; constante de temps plausible.

## Ce que ce module ne doit pas faire

Ne pas générer les usages TV/frigo, gérer le crédit, exposer Gymnasium ou choisir des actions.

