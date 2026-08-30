"""Mesure simple du temps d'inférence DQN."""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import numpy as np

from .train import charger_modele


def mesurer_inference(modele, observation: np.ndarray, repetitions: int = 1000) -> dict[str, float]:
    if repetitions <= 0:
        raise ValueError("repetitions doit être strictement positif")
    debut = perf_counter()
    for _ in range(repetitions):
        modele.predict(observation, deterministic=True)
    duree = perf_counter() - debut
    return {
        "repetitions": float(repetitions),
        "duree_totale_s": duree,
        "latence_moyenne_ms": duree / repetitions * 1000.0,
        "inferences_par_seconde": repetitions / duree,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Profiler le modèle DQN Woyofal")
    parser.add_argument("--algorithme", choices=("dqn",), default="dqn")
    parser.add_argument("--modele", default="results/models/production/modele.zip")
    parser.add_argument("--repetitions", type=int, default=1000)
    args = parser.parse_args()
    modele = charger_modele("dqn", Path(args.modele))
    from env import creer_environnement

    observation, _ = creer_environnement().reset(seed=42)
    resultat = mesurer_inference(modele, observation, args.repetitions)
    print(resultat)


if __name__ == "__main__":
    main()
