# Fiche de transmission Sprint 0


## Décisions non négociables sans revue d'équipe

- Pas de décision : 30 minutes.
- Puissance : W ; énergie/crédit : kWh ; température : °C ; argent : FCFA.
- Horodatages : ISO 8601 avec fuseau.
- Contrats importés depuis `common.models`, jamais recopiés. Les champs sont nommés en français.
- Scénario commun : `data/scenarios/foyer_fictif.json`.
- Test commun : `python -m unittest discover -s tests -v`.

## Pour M2 - données et RAMP

Tu reçois un `Scenario`. Ses `FenetreUsage` expriment des probabilités, des durées moyennes et une variabilité, pas des heures certaines. Tu livres un `ProfilChargePas` par tranche de 30 minutes avec puissance et énergie par appareil. Tu ne calcules pas la climatisation thermique, le solde ou la récompense.

À fournir pour la revue : un foyer fictif sur 24 h, seed documentée, sortie appareil par appareil, agrégation vérifiée et test de conservation W -> kWh.

## Pour M3 - simulation

Tu reçois le profil non thermique de M2 et une `Action`. Tu livres la nouvelle température, l'énergie HVAC et le nouveau solde, puis tu aides à construire le `StepResult` dans `env/`. Tu ne choisis pas la politique RL.

À fournir pour la revue : cas manuels du solde, clim OFF/ON dans le bon sens, paramètres R/C/COP explicites, coupure à crédit nul et tests déterministes.

## Pour M4 - RL

Tu utiliseras uniquement `env.reset()` et `env.step(Action)`. Un éventuel `ReportCharge` contient l'appareil et la durée du report. Tu fixeras l'encodage numérique des observations/actions sans changer leur sens métier et tu enregistreras toutes les métriques communes.

À fournir pour la revue : espaces Gymnasium, `check_env()` vert, quelques épisodes DQN factices, seed/hyperparamètres/logs sauvegardés et aucune importation directe de `thermal` ou `woyofal`.

## Pour tous

Avant toute Pull Request : actualiser le README local, ajouter un test, lancer le test rapide et demander une revue à un autre membre. Signaler immédiatement à M1 tout besoin de changer un contrat au lieu de créer un champ parallèle.
