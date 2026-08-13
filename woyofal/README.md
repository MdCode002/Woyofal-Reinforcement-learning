# Compteur Woyofal

**Responsable principal : M3.**

## Objectif

Convertir séparément une recharge FCFA en kWh lorsque nécessaire, puis débiter l'énergie consommée du solde et signaler la coupure.

## Contrat MVP de consommation

Entrée : `balance_kwh`, `consumption_kwh`. Sortie : nouveau solde kWh, `power_cut` et énergie non servie. Pendant l'usage, aucun prix FCFA/kWh ne doit être réappliqué dans la récompense.

## Travail attendu de M3

Fiabiliser le débit, ajouter la recharge si elle entre dans l'épisode et isoler toute grille tarifaire 2026 dans une configuration validée par des calculs manuels.

## Tests obligatoires

Solde normal, consommation nulle, épuisement exact, demande supérieure au solde, entrées négatives et recharge par tranche si elle est ajoutée.

## Ce que ce module ne doit pas faire

Ne pas simuler les appareils/thermique, choisir les recommandations ou intégrer les coûts deux fois.

