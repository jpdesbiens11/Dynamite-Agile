"""« Mon équipe » and review messages (core lot v0.31, D-B-112).

- team_of(): the people who chose me as their manager (Settings → Gestionnaire).
- GET /api/team?year=: for each of them, the context (title, level, employee / intern), where the review stands
  (3 steps, who signed) and what is expected from ME now -- one sentence per person, with the link to open.
- notify_review(): a message in Dashboard → Messages when the other side signs a step or the manager reopens one, so
  the manager is asked to approve the annual plan (« Début d'année ») as soon as the employee signed it, and vice versa.
Private: only the manager sees his own team; the messages carry no private text, only the step and a link.
"""
import json

from . import audit, db, profile, validate

KIND = "review"


def team_of(conn, manager_id):
    """Active accounts whose manager (approver) is `manager_id`, by name."""
    ids = []
    for row in conn.execute("SELECT p.user_id, p.prefs FROM user_prefs p JOIN users u ON u.id = p.user_id WHERE u.is_active = 1"):
        try:
            if json.loads(row["prefs"]).get("manager_id") == manager_id and row["user_id"] != manager_id:
                ids.append(row["user_id"])
        except ValueError:
            continue
    if not ids:
        return []
    return [r["id"] for r in conn.execute("SELECT id FROM users WHERE id IN ({}) ORDER BY display_name".format(
        ", ".join("?" * len(ids))), ids)]


def _status(conn, user_id, year):
    """Where the review of `user_id` stands, seen by his manager."""
    from . import reviews
    head = profile.header(conn, user_id)
    labels = reviews.LABELS[head["kind"]]
    phases = reviews._phases(conn, user_id, year)
    current = next((p for p in reviews.PHASES if not phases[p]["signed"]), "done")
    items = reviews.items(conn, user_id, year)
    archived = reviews._archived(conn, user_id, year)
    if archived:
        todo, mine = "Année close et archivée.", False
    elif current == "done":
        todo, mine = "Les 3 étapes sont signées : vous pouvez clore l'année.", True
    else:
        ph = phases[current]
        if not items and current == "start":
            todo, mine = "Aucun objectif encore : l'employé prépare son plan annuel.", False
        elif ph["employee_signed_at"] and not ph["manager_signed_at"]:
            todo, mine = "À vous : relire et signer « {} ».".format(labels[current]), True
        elif ph["manager_signed_at"] and not ph["employee_signed_at"]:
            todo, mine = "En attente de la signature de l'employé (« {} »).".format(labels[current]), False
        else:
            left = reviews.missing(conn, user_id, year, current, "manager")
            if current != "start" and any(s.startswith(("Commentaire", "Verdict", "Grille", "Recommandation", "Appréciation"))
                                          for s in left):
                todo, mine = "À vous : compléter « {} » ({}).".format(labels[current], left[0].rstrip(".")), True
            else:
                todo, mine = "« {} » en cours : l'employé la prépare.".format(labels[current]), False
    return {"profile": head, "labels": labels, "current": current, "archived": archived, "items": len(items),
            "phases": {p: {"employee": bool(phases[p]["employee_signed_at"]), "manager": bool(phases[p]["manager_signed_at"])}
                       for p in reviews.PHASES},
            "todo": todo, "mine": mine}


def pending_count(conn, manager_id, year):
    """How many people of my team wait for me (shown next to « Mon équipe » in the account menu)."""
    return sum(1 for uid in team_of(conn, manager_id) if _status(conn, uid, year)["mine"])


def api_team(ctx):
    from .objectives import _year
    year = _year(ctx)
    people = []
    for uid in team_of(ctx.conn, ctx.user["id"]):
        row = dict(_status(ctx.conn, uid, year), id=uid)
        people.append(row)
    audit.log_action(ctx.conn, ctx.user["id"], "team_viewed", "user", ctx.user["id"], {"year": year, "people": len(people)}, ctx.ip)
    return {"year": year, "people": people, "pending": sum(1 for p in people if p["mine"])}


def notify_review(conn, author, target_id, year, phase, event):
    """Message to the other side of the review. event: 'signed' or 'reopened'."""
    from . import prefs, reviews
    head = profile.header(conn, target_id)
    labels = reviews.LABELS[head["kind"]]
    manager_id = prefs.get(conn, target_id).get("manager_id")
    phases = reviews._phases(conn, target_id, year)
    both = phases[phase]["signed"]
    nxt = reviews.PHASES[reviews.PHASES.index(phase) + 1] if phase != "end" else None
    if author["id"] == target_id:  # the employee acted: the manager is told
        recipient = manager_id
        who = head["name"]
        if both:
            text = "{} a signé « {} » : l'étape est signée par les deux. {}".format(who, labels[phase],
                   "Prochaine étape : « {} ».".format(labels[nxt]) if nxt else "Vous pouvez clore l'année.")
        else:
            text = "{} a signé « {} » : à vous de relire et de signer{}.".format(
                who, labels[phase], " pour approuver son plan annuel" if phase == "start" and head["kind"] != "intern" else "")
        href = "#/objectives/{}/{}/{}".format(target_id, year, phase)
    else:  # the manager acted: the employee is told
        recipient = target_id
        if event == "reopened":
            text = "Votre gestionnaire a rouvert « {} » : vous pouvez la modifier, puis la signer de nouveau.".format(labels[phase])
        elif both:
            text = "Votre gestionnaire a signé « {} » : l'étape est signée par les deux. {}".format(labels[phase],
                   "Prochaine étape : « {} ».".format(labels[nxt]) if nxt else "L'année peut être close.")
        else:
            text = "Votre gestionnaire a signé « {} » : à vous de relire et de signer.".format(labels[phase])
        href = "#/objectives/{}/{}/{}".format(target_id, year, phase)
    if not recipient or recipient == author["id"]:
        return False
    title = "Évaluation {} · {} · {}".format(year, head["name"], labels[phase])
    conn.execute("INSERT INTO mentions (user_id, author_id, project_id, kind, title, href, excerpt, source, created_at) "
                 "VALUES (?, ?, NULL, ?, ?, ?, ?, 'review', ?)", (recipient, author["id"], KIND, title[:200], href, text[:400], db.utc_now()))
    return True


ROUTES = [
    ("GET", r"/api/team", api_team, "user"),
]
