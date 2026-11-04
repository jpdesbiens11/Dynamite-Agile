"""Check a Project Starter file before importing it (0.60.05, D-O-019).

    python3 tools/check_starter.py mon_projet.json

Prints what « Commencer » would create, the warnings, or the first fault with its fix. Reads the file only: no
database, no network. Exit code 0 when the file is accepted, 1 otherwise.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import starter  # noqa: E402
from core.errors import ApiError  # noqa: E402

LABELS = (("team", "membre(s) de l'équipe"), ("needs", "besoin(s)"), ("requirements", "requis"),
          ("tests", "essai(s)"), ("time_codes", "code(s) de temps"), ("pages", "page(s) Dynamite"))


def main(argv):
    if len(argv) != 2:
        print("Usage : python3 tools/check_starter.py <fichier.json>")
        return 1
    path = Path(argv[1])
    if not path.is_file():
        print("Erreur : fichier introuvable : {}".format(path))
        return 1
    try:
        clean, warnings = starter.parse(path.read_bytes())
    except ApiError as error:
        print("Erreur : " + error.message)
        return 1
    info = starter.summary(clean)
    print("Fichier accepté : {}".format(info["project"]))
    for key, label in LABELS:
        print("  {:>4} {}".format(info[key], label))
    for line in warnings:
        print("Attention : " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
