# Environnement

**Responsables : M3 + M4, sous contrôle d'intégration M1.** Ce dossier est la frontière officielle entre simulation et RL.

## Interface

`reset() -> Observation` et `step(Action) -> StepResult`. M4 ne doit jamais appeler directement `ramp/`, `thermal/` ou `woyofal/`.

## Observation MVP

Solde, heure/jour, minutes avant recharge, T_int/T_ext, humidité, occupation, consommation cumulée, rythme, historique récent et états appareils.

## Action MVP

Climatisation ON/OFF, ventilateur ON/OFF et `ReportCharge` optionnel. Le report précise l'appareil et sa durée. L'environnement devra vérifier que cet appareil est flexible et que son décalage est autorisé. M4 choisit un encodage compatible avec l'algorithme sans changer ce sens métier.

## Fin d'épisode

`terminated=True` si crédit épuisé ou date cible atteinte. `truncated=True` uniquement pour une limite externe/horizon de sécurité.

## Travail attendu

M3 créera le couplage du simulateur ; M4 déclarera `observation_space`/`action_space` et validera avec `check_env()`. Les deux conserveront les contrats communs.

## Tests obligatoires

Reset reproductible, pas de 30 minutes, débit égal à l'énergie totale, sens thermique cohérent, fins d'épisode et conformité Gymnasium.

