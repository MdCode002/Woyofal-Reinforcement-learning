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

# Woyofal & RAMP Simulation (M2 - M3)

Ce projet simule la consommation électrique résidentielle stochastique adaptée au contexte de Dakar (Sénégal) sous le système de prépaiement **Woyofal** (Senelec). Il intègre également la modélisation thermique d'un espace climatiser et des tests unitaires automatisés.

---

## 🛠️ Architecture du Projet

````text
ramp/
├── data/                         # Export des profils et fiches compteurs
│   ├── profils_stochastiques.csv
│   └── fiches_compteur_woyofal.csv
├── src/                          # Modules sources
│   ├── catalogue.py              # Catalogue des appareils électroménagers
│   ├── compteur.py               # Logique du compteur prépayé Woyofal
│   ├── meteo.py                  # Profils météo synthétiques de Dakar
│   ├── moteur.py                 # Moteur stochastique de simulation RAMP
│   └── thermique.py              # Modèle thermique de pièce (R, C, COP)
├── tests/                        # Tests unitaires
│   └── test_m3_thermal_and_counter.py
├── requirements.txt              # Dépendances du projet
├── sprint1_simulation_dakar.py   # Simulation initiale et contrôle kWh
├── sprint2_stochastique.py       # Génération stochastique multi-ménages
└── sprint3_calibration.py        # Calibration et intégration thermique
🚀 Jalons & Fonctionnalités (M1 - M3)
.M1 / M2 - Appareils & Météo Dakar
  .Catalogue complet : Éclairage, TV, ventilateur, réfrigérateur, fer à repasser, pompe, chauffe-eau, climatiseur
  .Météo Dakar : Température extérieure ($22^\circ\text{C}$ à $32^\circ\text{C}$) et humidité relative
  .Moteur RAMP Stochastique : Variabilité sur la puissance, les durées et les fenêtres horaires d'utilisation
  .Agrégation au pas de décision de 30 minutes et export CSV
.M3 - Compteur Woyofal & Modèle Thermique
  .Compteur Woyofal : Gestion du solde en kWh, tarification et détection de la coupure de courant.
  .Modèle Thermique : Simulation du transfert de chaleur via Résistance ($R$), Capacité ($C$) et $COP$ du climatiseur avec contrôle de la constante de temps ($\tau = R \times C$)
  .Calibration : Ajustement de la courbe de charge théorique sur la consommation réelle constatée.

### Exécution des Tests & Simulations
0.##  Installation & Exécution

  ### 1. Configuration de l'environnement virtuel (venv)

  **Sur Windows (PowerShell) :**
  ```bash
  # Création du venv
  py -3.11 -m venv venv #pour des raisons de verions

  # Activation du venv
  .\venv\Scripts\Activate.ps1
  Sur Linux / macOS :

  Bash
  # Création du venv
  py -3.11 -m venv venv

  # Activation du venv
  source venv/bin/activate

1. Installation des dépendances
Bash
pip install -r requirements.txt

2. Exécution des sprints
Bash
python sprint1_simulation_dakar.py
python sprint2_stochastique.py
python sprint3_calibration.py

3. Lancement des tests unitairesBashpython -m pytest tests/

📊 Formats des Données Exportéesdata/profils_stochastiques.csv : Horodatage, identifiant du ménage et puissance moyenne absorbée (W) toutes les 30 min.data/fiches_compteur_woyofal.csv : Consommation (kWh), crédit restant (kWh) et statut de coupure (0 ou 1).
````

### Remarque

1. Installer pytest directement via le Python de votre venv
   Forcez l'installation de pytest dans le binaire exact de votre environnement virtuel en lançant :

Bash
python -m pip install pytest

-----> Si pytest ne s'installe pas correctement suivre cette étape
