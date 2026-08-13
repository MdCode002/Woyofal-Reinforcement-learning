# Résultats

**Responsables : toute l'équipe ; protocole comparatif piloté par M1.**

## Contenu

- `logs/` : traces d'exécution et d'entraînement ;
- `figures/` : graphiques reproductibles ;
- `evaluations/` : CSV/JSON de comparaison ;
- `models/` : modèles entraînés et métadonnées.

## Schéma minimal d'évaluation

`strategie`, `identifiant_scenario`, `seed`, `consommation_kwh`, `credit_restant_kwh`, `temperature_interieure_c`, `inconfort`, `nombre_coupures`, `duree_restante_minutes`, `date_cible_atteinte`, `identifiant_configuration`, `version_code`.

Baseline, DQN et PPO doivent utiliser les mêmes scénarios et définitions. Enregistrer moyenne et dispersion sur plusieurs seeds.

## Versionnement

Les fichiers produits sont ignorés par Git par défaut pour éviter de gonfler le dépôt. Versionner seulement un petit résultat de référence explicitement approuvé ; conserver ailleurs les artefacts lourds avec leur checksum et leur provenance.
