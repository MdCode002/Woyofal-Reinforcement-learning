# RAMP

**Responsable principal : M2.**

## Objectif

Générer, appareil par appareil, les usages non thermiques stochastiques à partir d'un `Scenario`.

## Entrée

`common.models.Scenario`, complété par les catalogues et séries de `data/`. Les `FenetreUsage` sont probabilistes : M2 ne doit pas allumer systématiquement l'appareil pendant toute la fenêtre.

## Sortie obligatoire

Un `common.models.ProfilChargePas` par pas de 30 minutes : horodatage, puissance W et énergie kWh par appareil, puis énergie non thermique totale. Les profils internes à la minute doivent être agrégés avant de quitter ce module.

## Dépendances et consommateurs

Lit `data/` et `common/`; sa sortie est consommée uniquement par `env/` ou le futur orchestrateur de simulation.

## Travail attendu de M2

1. Installer RAMP et créer son implémentation dans ce dossier.
2. Déclarer TV, éclairage, ventilateur et réfrigérateur sur 24 h.
3. Ajouter seed, fenêtres, durées et variabilité documentées.
4. Vérifier les ordres de grandeur et l'agrégation à 30 minutes.
5. Conserver exactement le contrat `ProfilChargePas`.

## Tests obligatoires

Même seed = même profil, une ligne par pas, énergie égale à W × durée, somme par appareil égale au total, aucune valeur négative.

