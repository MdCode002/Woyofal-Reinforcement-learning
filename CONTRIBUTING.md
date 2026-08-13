# Contribution à Woyofal

## Cycle d'une modification

1. Partir de `dev` à jour.
2. Créer une branche courte `feature/<module>-<objectif>`.
3. Modifier un seul sujet cohérent.
4. Ajouter ou adapter les tests et le README local.
5. Lancer `python quick_test.py` puis `python -m unittest discover -s tests -v`.
6. Ouvrir une Pull Request vers `dev`.
7. Obtenir la revue d'au moins un autre membre.
8. Fusionner seulement si les tests sont verts.

`main` reçoit uniquement une version de `dev` démontrable en fin de sprint.

## Modification d'un contrat partagé

Une modification de `common/models.py` ou `common/units.py` exige :

- l'accord de M1, M2, M3 et M4 ;
- une justification dans la Pull Request ;
- la mise à jour de tous les consommateurs ;
- la mise à jour des exemples, tests et README concernés.

## Définition de terminé

Le code s'exécute sans correction manuelle, respecte les unités, fournit un test reproductible, place ses paramètres dans une configuration et est relu avant fusion.
