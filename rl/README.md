# Reinforcement Learning

**Responsable principal : M4.**

## Objectif

Entraîner, sauvegarder et évaluer DQN puis PPO à travers l'unique interface de `env/`.

## Entrée et sortie

L'agent reçoit une `Observation`, produit une `Action` et exploite la récompense/fin contenue dans `StepResult`. Il sauvegarde modèles, hyperparamètres, seeds et logs sous `results/`.

## Travail attendu de M4

1. Encoder l'action MVP dans un petit espace discret pour le premier DQN.
2. Ajouter PPO si l'action devient `MultiBinary` ou continue.
3. Définir la récompense : inconfort, énergie, coupure, commutations et bonus de date cible.
4. Entraîner sur plusieurs scénarios, avec validation puis test jamais vu.
5. Comparer exactement les mêmes métriques que les baselines.

## Tests obligatoires

Pipeline court reproductible, seed enregistrée, chargement du modèle, logs complets et aucune dépendance directe vers `thermal/` ou `woyofal/`.

## Ce que ce module ne doit pas faire

Ne pas recalculer le solde, la température ou les profils d'appareils. Ne pas ajuster les hyperparamètres sur le jeu de test final.

