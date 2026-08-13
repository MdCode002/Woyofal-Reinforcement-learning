# Contrats communs

**Responsable : M1.** Ce dossier est la source unique des formats échangés et des unités.

## Objectif

Empêcher M2, M3 et M4 de créer des versions incompatibles des mêmes données.

## API publique

- `Scenario` : configuration immuable d'un épisode ;
- `Observation` : état visible par l'agent ;
- `Action` : décision MVP ;
- `StepResult` : résultat d'un pas ;
- `FenetreUsage` : plage probabiliste donnée à M2, pas horaire certain ;
- `ReportCharge` : appareil concerné et durée exacte du report ;
- `ProfilChargePas` : sortie RAMP agrégée sur 30 minutes ;
- `Metriques` : métriques comparables entre stratégies ;
- `charger_scenario()` : chargement d'un JSON validé ;
- `convertir_en_kwh()` : conversion officielle W/minutes vers kWh.

## Règle de changement

Aucun membre ne modifie un contrat seul. Tout changement exige l'accord de l'équipe, une migration des consommateurs, des tests et la mise à jour de la documentation.

## Ce que ce module ne doit pas faire

Il ne simule ni usages, ni température, ni compteur, ni politique RL.

