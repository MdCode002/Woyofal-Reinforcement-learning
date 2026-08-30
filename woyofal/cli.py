"""Interface en ligne de commande unifiée du projet Woyofal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _afficher(charge: object) -> None:
    print(json.dumps(charge, indent=2, ensure_ascii=False))


def construire_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="woyofal", description="Optimisation d'un budget Woyofal par DQN")
    sous = parser.add_subparsers(dest="commande", required=True)
    sous.add_parser("verifier", help="Vérifier l'installation et l'environnement Gymnasium")
    meteo = sous.add_parser("telecharger-meteo", help="Préparer le cache météo Dakar")
    meteo.add_argument("--debut", default="2018-01-01")
    meteo.add_argument("--fin", default="2025-12-31")
    meteo.add_argument("--sortie", default="data/weather/cache/dakar_2018_2025.csv")
    scenarios = sous.add_parser("generer-scenarios", help="Créer les jeux de scénarios 200/40/60")
    scenarios.add_argument("--sortie", default="data/generated_variable")
    scenarios.add_argument(
        "--partition", choices=("toutes", "train", "validation", "test"), default="toutes",
        help="Régénérer un seul jeu sans modifier les autres",
    )
    train = sous.add_parser("entrainer", help="Entraîner le modèle DQN")
    train.add_argument("--algorithme", choices=("dqn",), default="dqn")
    train.add_argument("--seed", type=int, default=17)
    train.add_argument("--timesteps", type=int)
    train.add_argument("--sortie")
    train.add_argument("--reprendre", help="Modèle compatible à poursuivre")
    evaluer = sous.add_parser("evaluer", help="Évaluer le modèle DQN")
    evaluer.add_argument("--seeds", nargs="+", type=int, default=[101, 211, 307, 401, 503])
    evaluer.add_argument("--modele", default="results/models/production/modele.zip")
    evaluer.add_argument("--sortie", default="results/evaluations/evaluation_dqn")
    evaluer.add_argument("--adoption", nargs="+", type=float, default=[1.0, 0.75, 0.5])
    evaluer.add_argument(
        "--partition", choices=("validation", "test"), default="test",
    )
    reco = sous.add_parser("recommander", help="Afficher l'action recommandée maintenant")
    reco.add_argument("--scenario", default="data/scenarios/foyer_fictif.json")
    reco.add_argument("--saisie-simple", help="JSON court avec pièces et appareils")
    reco.add_argument("--modele")
    reco.add_argument("--algorithme", choices=("dqn",), default="dqn")
    reco.add_argument("--horizon-heures", type=int, default=4)
    demo = sous.add_parser("demo", help="Exécuter une démonstration locale hors ligne")
    demo.add_argument("--scenario", default="data/scenarios/foyer_fictif.json")
    demo.add_argument("--saisie-simple", help="JSON court avec pièces et appareils")
    demo.add_argument("--simulations", type=int, default=5)
    return parser


def main(arguments: list[str] | None = None) -> int:
    parser = construire_parser()
    args = parser.parse_args(arguments)
    if args.commande == "verifier":
        from env import verifier_gymnasium

        verifier_gymnasium()
        _afficher({"statut": "ok", "gymnasium": "valide", "actions": 10, "observation": 33})
    elif args.commande == "telecharger-meteo":
        from ramp_adapter.weather import telecharger_meteo_dakar

        chemin = telecharger_meteo_dakar(
            debut=args.debut, fin=args.fin, chemin_sortie=args.sortie,
        )
        _afficher({"statut": "ok", "cache": str(chemin)})
    elif args.commande == "generer-scenarios":
        from ramp_adapter.scenarios import generer_jeux_scenarios, generer_partition_scenarios

        if args.partition == "toutes":
            _afficher(generer_jeux_scenarios(args.sortie))
        else:
            _afficher({
                args.partition: generer_partition_scenarios(args.sortie, args.partition)
            })
    elif args.commande == "entrainer":
        from rl.train import entrainer

        _afficher({"modele": str(entrainer(
            algorithme=args.algorithme, seed=args.seed,
            total_timesteps=args.timesteps, dossier_sortie=args.sortie,
            modele_initial=args.reprendre,
        ))})
    elif args.commande == "evaluer":
        from evaluation.runner import evaluer_politique
        from env import EnvironnementMultiScenario
        from rl.train import charger_modele
        import pandas as pd

        modele = charger_modele("dqn", args.modele)
        dossier_scenarios = Path(f"data/generated_variable/{args.partition}")
        fichiers = sorted(dossier_scenarios.glob("scenario_*.json"))
        tables = []
        for f in fichiers:
            table, _ = evaluer_politique(
                politique=modele,
                fabrique_environnement=lambda f=f: EnvironnementMultiScenario([f], taux_adoption=1.0),
                nom_strategie="dqn",
                seeds=args.seeds,
                contexte={"scenario": f.stem},
            )
            tables.append(table)
        if tables:
            df = pd.concat(tables, ignore_index=True)
            dossier_sortie = Path(args.sortie)
            dossier_sortie.mkdir(parents=True, exist_ok=True)
            df.to_csv(dossier_sortie / "episodes.csv", index=False)
            _afficher({"statut": "ok", "episodes": len(df), "sortie": str(dossier_sortie)})
        else:
            _afficher({"statut": "aucun_scenario", "partition": args.partition})
    elif args.commande == "recommander":
        from .intake import scenario_depuis_saisie
        from .service import recommander

        scenario = (
            scenario_depuis_saisie(json.loads(Path(args.saisie_simple).read_text(encoding="utf-8")))
            if args.saisie_simple
            else json.loads(Path(args.scenario).read_text(encoding="utf-8"))
        )
        _afficher(recommander(
            scenario=scenario,
            modele=args.modele,
            algorithme=args.algorithme,
            horizon_heures=args.horizon_heures,
        ))
    elif args.commande == "demo":
        from .service import demonstrateur_offline

        _afficher(demonstrateur_offline(
            chemin_scenario=args.saisie_simple or args.scenario,
            simulations=args.simulations,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
