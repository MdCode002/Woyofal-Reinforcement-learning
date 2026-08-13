# Tests

**Responsables : toute l'équipe ; cohérence d'intégration suivie par M1.**



## Travail futur

Chaque responsable ajoutera les tests de son propre module :

- M2 : profils RAMP, seed, agrégation et conservation de l'énergie ;
- M3 : solde, coupure, recharge et évolution thermique ;
- M4 : `reset()`, `step()`, espaces Gymnasium et pipeline RL ;
- M1 : tests d'intégration une fois les prototypes des autres membres disponibles.

## Commande commune

```bash
python -m unittest discover -s tests -v
```

Aucune fusion vers `dev`, puis `main`, ne doit être réalisée si la suite échoue.
