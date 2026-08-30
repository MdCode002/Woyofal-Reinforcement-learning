# Woyofal — Optimisation et Pilotage Énergétique par Deep Q-Network (DQN)

> **Projet de Master 2 — Apprentissage par Renforcement**  
> *Système intelligent d'aide à la décision pour l'optimisation de budget d'électricité prépayée Woyofal (Senelec - Dakar).*

---

## 1. Présentation du Projet

À Dakar, la majorité des ménages utilise le système d'électricité prépayée **Woyofal** de la Senelec. Lorsqu'un compteur affiche un solde résiduel (ex. 20 kWh via le code **801**), il est difficile pour un foyer d'anticiper avec précision la durée restante de son crédit, particulièrement lors des périodes de forte chaleur où l'usage de la climatisation et de la ventilation entraîne des surconsommations imprévues.

Ce projet implémente un système complet fondé sur l'**Apprentissage par Renforcement Profond (Deep Q-Network - DQN)** capable de :
1. **Prédire la durée probable du crédit** sous forme d'estimations stochastiques (médiane, percentiles P10-P90) et calculer la probabilité d'atteindre une date cible de recharge.
2. **Recommander en temps réel (par pas de 30 minutes)** les réglages optimaux de confort pièce par pièce (climatisation, ventilation, arrêt) et le report des charges énergivores (fer à repasser, lave-linge, pompe).
3. **Fonctionner sans capteur invasif** : aucune sonde de température ni objet connecté n'est requis ; les températures intérieures sont estimées par modélisation physique à partir des données météo locales de Dakar.

---

## 2. Architecture & Modélisation

```text
       Données du foyer (Code 801, pièces, appareils, habitudes)
                                  │
                                  ▼
      ┌────────────────────────────────────────────────────────┐
      │                   Moteur de Simulation                 │
      │  • RAMP Adapter : charge stochastique & météo Dakar    │
      │  • Modèle Thermique 1R1C : dynamique des températures  │
      │  • Compteur Woyofal : gestion du crédit & coupures     │
      └───────────────────────────┬────────────────────────────┘
                                  │
                                  ▼
      ┌────────────────────────────────────────────────────────┐
      │               Environnement Gymnasium                  │
      │  • Observation normalisée : 33 dimensions              │
      │  • Espace d'action discret : 10 modes par pièce        │
      │  • Récompense : préservation du budget & confort       │
      └───────────────────────────┬────────────────────────────┘
                                  │
                                  ▼
      ┌────────────────────────────────────────────────────────┐
      │                 Agent Décisionnel DQN                  │
      │  • MLP [256, 256], Experience Replay, Target Network   │
      │  • Politique partagée invariante au nombre de pièces   │
      │  • Prévisions probabilistes & Recommandations 30 min   │
      └────────────────────────────────────────────────────────┘
```

### A. Modélisation Physique & Données
- **Demande stochastique (RAMP)** : Simulation minute par minute des charges non pilotables (éclairage, réfrigérateur, télévision, appareils de veille) et des charges flexibles.
- **Modèle Thermique 1R1C** : Résolution différentielle de la température intérieure de chaque pièce selon le rayonnement solaire, la température extérieure de Dakar, l'inertie des parois et la puissance active des climatiseurs/ventilateurs.
- **Compteur Woyofal** : Gestion du crédit en kWh, détection de coupure à solde nul et application de la grille tarifaire DPP.

### B. Formulation du Problème RL
- **Espace d'état (33 dimensions)** : Solde de crédit restant, progression vers la date cible, heure de la journée, météo Dakar (température, rayonnement), caractéristiques thermiques de la pièce, historique de consommation récente.
- **Espace d'action (10 actions discrètes)** :
  - `0` : Arrêt complet
  - `1` : Ventilateur seul
  - `2-4` : Climatisation (27 °C éco / 25 °C confort / 23 °C boost)
  - `5-9` : Mêmes modes combinés à l'autorisation d'exécuter une charge reportable.
- **Politique partagée** : Le réseau DQN évalue successivement chaque pièce du foyer, garantissant une équité parfaite et permettant de piloter des logements de 1 à 8 pièces (et jusqu'à 50 techniquement) avec un seul modèle.
- **Fonction de récompense** :
  $$R_t = R_{\text{survie}} + R_{\text{budget}} - \lambda_{\text{inconfort}} \cdot \Delta T_{\text{inconfort}} - \lambda_{\text{coupure}} \cdot \mathbb{I}_{\text{coupure}} + R_{\text{bonus\_cible}}$$

---

## 3. Résultats de l'Agent DQN

L'agent DQN a été entraîné sur **500 000 pas de décision** à travers 200 scénarios diversifiés de foyers dakarois :

- **Taux de réussite global sur le banc de test gelé 2025** : **77,3 %** d'atteinte de l'objectif sans coupure (dépassant l'objectif cible de 70 %).
- **Sur foyers standards (1 à 4 pièces)** : Taux de réussite de **82,7 %**.
- **Gestion des pièces inoccupées** : Extinction automatique de la climatisation dès qu'une pièce est estimée vide selon le profil d'usage du foyer.

---

## 4. Structure du Répertoire

```text
├── common/                  # Modèles de données Pydantic, unités et scénarios
├── config/                  # Catalogue des appareils domestiques et puissances priors
├── data/                    # Scénarios générés (train/val/test) et cache météo Dakar
├── env/                     # Environnement Gymnasium (woyofal_env, politique partagée)
├── evaluation/              # Métriques, validation et suivi de performances
├── frontend/                # Interface utilisateur Web (Nuxt 4, Vue 3, Tailwind/Vanilla CSS)
├── results/                 # Modèle DQN entraîné de production (modele.zip)
├── rl/                      # Pipeline DQN, réseau de neurones, configuration SB3
├── tests/                   # Suite complète de tests unitaires (pytest)
├── thermal/                 # Simulateur thermique 1R1C
├── woyofal/                 # Package applicatif (Compteur, API FastAPI, CLI, Service)
├── docker-compose.yml       # Orchestration des conteneurs (API + Frontend)
├── Dockerfile.api           # Image Docker optimisée CPU pour l'API
├── pyproject.toml           # Métadonnées du projet et configuration des scripts
└── requirements.txt         # Dépendances Python du projet
```

---

## 5. Installation et Exécution Locale

### Prérequis
- Python 3.10 ou 3.11
- Node.js 20+ et `pnpm` (pour l'interface web)

### 1. Installation de l'environnement Python
```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Validation des Tests
```powershell
pytest -v
```

### 3. Commandes CLI Woyofal
Le package intègre une interface en ligne de commande unifiée :

```powershell
# Vérifier la conformité de l'environnement Gymnasium
python -m woyofal verifier

# Télécharger/Mettre à jour le cache météo Dakar (Open-Meteo)
python -m woyofal telecharger-meteo --debut 2018-01-01 --fin 2025-12-31

# Exécuter une démonstration locale hors-ligne avec le modèle DQN
python -m woyofal demo --simulations 5

# Calculer une recommandation immédiate pour un foyer
python -m woyofal recommander --scenario data/scenarios/foyer_fictif.json
```

---

## 6. Lancement de l'Application (API & Interface Web)

### Option A : Avec Docker Compose (Recommandé)
```powershell
docker compose up --build
```
- **Interface Web** : `http://localhost:3000`
- **API FastAPI & Swagger** : `http://localhost:8000/docs`

### Option B : Lancement Manuel des Services

1. **Serveur Backend (FastAPI)** :
   ```powershell
   uvicorn woyofal.api:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Serveur Frontend (Nuxt 4 / Vue 3)** :
   ```powershell
   cd frontend
   pnpm install
   pnpm dev
   ```
