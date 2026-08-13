# Optimisation intelligente d'un budget Woyofal**

Woyofal doit estimer la durée restante d'un crédit Woyofal puis recommander des actions sur les appareils flexibles, en conciliant confort, consommation et risque de coupure.


## Architecture cible

```text
Scenario et données
        |
        v
RAMP - profils des appareils non thermiques (M2)
        |
        v
Thermique 1R1C + compteur Woyofal (M3)
        |
        v
Environnement Gymnasium (M3 + M4)
        |
        v
Agent DQN / PPO et recommandations (M4)
```



## Dossiers et responsabilités

| Dossier | Contenu attendu | Responsable |
|---|---|---|
| `common/` | Contrats et unités partagés | M1 |
| `data/` | Météo, appareils, ménages et données compteur | M2 |
| `ramp/` | Génération des profils non thermiques | M2 |
| `thermal/` | Modèle thermique 1R1C et consommation HVAC | M3 |
| `woyofal/` | Solde en kWh, recharge et coupure | M3 |
| `env/` | Couplage de la simulation et interface Gymnasium | M3 + M4 |
| `rl/` | DQN, PPO, récompense, entraînement et évaluation | M4 |
| `tests/` | Tests de chaque module et tests d'intégration | Toute l'équipe |
| `results/` | Logs, graphiques, modèles et comparaisons | Toute l'équipe |

Chaque dossier possède un `README.md` qui explique ce que son responsable doit recevoir, produire, tester et ne pas faire. La fiche [CONTRATS_EQUIPE.md](docs/CONTRATS_EQUIPE.md) résume ce qui doit être transmis à M2, M3 et M4.

## Unités communes

| Grandeur | Convention |
|---|---|
| Temps interne | minutes |
| Pas principal | 30 minutes |
| Énergie | kWh |
| Puissance | W |
| Température | °C |
| Humidité | % |
| Argent | FCFA |
| Crédit Woyofal | kWh |
| Dates | ISO 8601 avec fuseau horaire |

Conversion commune : `energie_kwh = puissance_w × duree_minutes / 60 / 1000`.

Le futur modèle thermique pourra utiliser des sous-pas de 5 à 15 minutes. Cependant, RAMP et l'environnement devront toujours échanger leurs résultats au pas principal de 30 minutes.

## Contrats communs

Les définitions se trouvent dans `common/models.py`. Leurs noms de classes restent ceux imposés par le sujet ; les champs sont en français.

### `Scenario`

Configuration fournie au début : foyer, occupants, appareils, crédit initial, date de début, date cible, pas temporel, météo simplifiée et état thermique initial. La date cible exprime « jusqu'à quand le crédit doit tenir » ; dans le fichier fictif, les dates sont uniquement des exemples.

Les températures ne sont pas supposées connues par l'utilisateur : leur provenance indique si elles sont mesurées ou estimées. La météo initiale vient normalement d'une source météo préparée par M2.

### `Observation`

État visible par l'agent : crédit restant, heure/jour, temps avant recharge, températures, humidité, occupation, consommation cumulée, rythme actuel, historique et état des appareils.

### `Action`

Décision MVP : climatisation active ou non, ventilateur actif ou non et report éventuel d'une charge. Un report indique maintenant précisément l'appareil et une durée multiple de 30 minutes.

### `StepResult`

Résultat de `env.step()` : nouvelle observation, consommation du pas, récompense, fin normale, troncature éventuelle et informations de diagnostic.

### `ProfilChargePas`

Contrat complémentaire pour M2 : une sortie RAMP agrégée à 30 minutes avec puissance W et énergie kWh par appareil.

## Métriques communes

- `consommation_kwh`
- `credit_restant_kwh`
- `temperature_interieure_c`
- `inconfort`
- `nombre_coupures`
- `duree_restante_minutes`
- `date_cible_atteinte`

Les futures baselines, DQN et PPO devront utiliser exactement ces métriques, avec le scénario, la seed, la configuration et la version du code.

## Scénario fictif

`data/scenarios/foyer_fictif.json` décrit un foyer de 3 personnes, un crédit de 20 kWh, un objectif de 5 jours et un pas de 30 minutes. Les dates, puissances, températures, probabilités et durées sont uniquement des valeurs d'exemple destinées à valider le format partagé ; elles ne sont pas présentées comme représentatives du Sénégal.

Les heures des appareils sont des fenêtres d'usage probable. Elles ne prétendent pas prédire l'heure exacte d'utilisation. M2 utilisera la probabilité, la durée moyenne et la variabilité pour générer plusieurs journées possibles.


## Stratégie Git

- `main` : version stable et démontrable ;
- `dev` : branche d'intégration ;
- `feature/ramp-*`, `feature/thermal-*`, `feature/woyofal-*`, `feature/env-*`, `feature/rl-*` : branches de travail.

Flux prévu :

```text
feature/* -> Pull Request -> revue d'un autre membre -> dev -> tests -> main
```

Chaque membre réalise son propre commit sur sa branche. Toute modification d'un contrat commun doit être validée collectivement.

