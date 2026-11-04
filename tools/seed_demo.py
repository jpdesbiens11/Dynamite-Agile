"""Development example (0.60.01): the team project Space EQP and its four fictitious students.

Created at start-up in development mode, through the same admin API as the screens (so it is audited like a real
user's work); idempotent. Accounts come from deploy/utilisateurs_exemple.txt (Nina, Léa, Hugo, Alexis), the same base
⚙ Admin → Comptes → Règles d'accès offers to load. The Goldmine of EQP starts with the generic requirements of a
consumer mechatronic product (deploy/requis_generiques.csv, tools/generic_requirements.py), imported once.

    python tools/seed_demo.py --password admin
"""
import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools.api_client import ApiFailure, Client  # noqa: E402

KEY = "EQP"
NAME = "Projet d'équipe"
DESCRIPTION = "Space d'exemple : le projet de conception de l'équipe (Nina, Léa, Hugo, Alexis)."
STUDENTS = ("nina", "lea", "hugo", "alexis")


def import_example_team(admin):
    """Load deploy/utilisateurs_exemple.txt once; returns {username: temporary password} of the accounts created."""
    known = {u["username"] for u in admin.get("/api/admin/users")["users"]}
    if all(name in known for name in STUDENTS):
        return {}
    text = admin.get("/api/admin/access-rules/default")["text"]
    done = admin.post("/api/admin/access-rules", {"text": text})
    return {c["username"]: c["temp_password"] for c in done["created"]}


def import_generic_requirements(admin):
    """Import deploy/requis_generiques.csv into EQP once (nothing when its Goldmine already has items)."""
    pid = next(p["id"] for p in admin.get("/api/admin/projects")["projects"] if p["key"] == KEY)
    base = "/api/agile/p/{}".format(pid)
    if admin.get(base + "/goldmine")["requirements"]:
        return 0
    text = (BASE_DIR / "deploy" / "requis_generiques.csv").read_text(encoding="utf-8-sig")
    res = admin.post(base + "/import/requirements", {"csv": text})
    return sum(1 for r in res.get("report", []) if r.get("status") == "créée")


def run(args):
    admin = Client(args.url, getattr(args, "cafile", None))
    admin.login(args.user, args.password)
    if not admin.get("/api/me/prefs")["prefs"].get("initials"):  # D-B-058: no write without a 3-letter key
        admin.put("/api/me/prefs", {"initials": "ADM"})  # example data only (development mode)
    keys = {p["key"] for p in admin.get("/api/admin/projects")["projects"]}
    if KEY not in keys:
        admin.post("/api/admin/projects", {"key": KEY, "name": NAME, "description": DESCRIPTION})
    created = import_example_team(admin)
    count = import_generic_requirements(admin)
    if count:
        print("  {} generic requirements and needs imported into {}".format(count, KEY))
    for username, password in sorted(created.items()):
        print("  Example account {:<8} temporary password: {}".format(username, password))
    return created


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", required=True)
    try:
        run(parser.parse_args())
        return 0
    except ApiFailure as exc:
        print("API error: {}".format(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print("Server unreachable ({}). Is it running?".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
