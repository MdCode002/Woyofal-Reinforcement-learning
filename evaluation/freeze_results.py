"""Gèle les résultats finaux par manifeste SHA-256 sans les modifier."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def geler_resultats(dossier: str | Path, manifeste: str | Path | None = None) -> Path:
    dossier = Path(dossier)
    if not dossier.is_dir():
        raise ValueError(f"Dossier de résultats introuvable : {dossier}")
    manifeste = Path(manifeste or dossier / "MANIFESTE_GELE.json")
    fichiers = []
    for chemin in sorted(dossier.rglob("*")):
        if chemin.is_file() and chemin.resolve() != manifeste.resolve():
            empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()
            fichiers.append(
                {
                    "chemin": chemin.relative_to(dossier).as_posix(),
                    "sha256": empreinte,
                    "taille_octets": chemin.stat().st_size,
                }
            )
    contenu = {
        "gele_le_utc": datetime.now(timezone.utc).isoformat(),
        "dossier": str(dossier),
        "nombre_fichiers": len(fichiers),
        "fichiers": fichiers,
    }
    manifeste.write_text(
        json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifeste


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Geler un dossier de résultats")
    parser.add_argument("dossier")
    parser.add_argument("--manifeste")
    arguments = parser.parse_args()
    print(geler_resultats(arguments.dossier, arguments.manifeste))

