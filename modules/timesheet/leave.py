"""Absences in the time sheet (D-B-031, D-B-041; INT Space since 0.60.01): vacation bank and health leave.

- Two codes of the INT internal Space (catalog.INTERNAL_KEY, open to everyone): INT-VAC « Vacances » -- every hour
  is taken from the person's vacation bank -- and INT-SAN « Congé santé » -- NOT taken from the bank, allowed under
  the approver's decision. Neither is claimable from a funding organism (budget.NOT_CLAIMABLE). The principles are
  written in the INT Space (Dynamite → « Politique de l'équipe — vacances et congés »), to adapt.
- The bank (hours left at a date) and the approver (manager) are set by the person in his settings (core/prefs.py),
  journalled, correctable by an administrator; the approver always sees them on the week he approves.
- Balance = bank - INT-VAC hours dated from the bank date on (weeks in any state: what is typed is shown as already
  taken, « solde projeté »).
- The module name stays (core/objectives.py and Training import reports_of from here).
"""
import json

from . import catalog

VACATION = "INT-VAC"
HEALTH = "INT-SAN"


def _prefs(conn, user_id):
    from core import prefs
    return prefs.get(conn, user_id)


def balance(conn, user_id):
    p = _prefs(conn, user_id)
    bank, since = p.get("vacation_bank_hours"), p.get("vacation_bank_date")
    manager = None
    if p.get("manager_id"):
        row = conn.execute("SELECT id, display_name FROM users WHERE id = ?", (p["manager_id"],)).fetchone()
        manager = dict(row) if row else None
    if bank is None:
        return {"bank": None, "since": None, "used": 0, "remaining": None, "manager": manager}
    used = conn.execute(
        "SELECT COALESCE(SUM(e.hours), 0) FROM timesheet_entries e JOIN timesheet_weeks w ON w.id = e.week_id "
        "WHERE w.user_id = ? AND e.task_key = ? AND e.work_date >= ?", (user_id, VACATION, since or "0000")).fetchone()[0]
    return {"bank": bank, "since": since, "used": round(used, 2), "remaining": round(bank - used, 2), "manager": manager}


def week_summary(conn, user_id, rows):
    """Absences of one week + the bank, for the employee and his approver."""
    vac = round(sum(r["hours"] for r in rows if r["task_key"] == VACATION), 2)
    health = round(sum(r["hours"] for r in rows if r["task_key"] == HEALTH), 2)
    info = balance(conn, user_id)
    info.update(vacation_week=vac, health_week=health,
                overdrawn=info["remaining"] is not None and info["remaining"] < 0)
    return info


def reports_of(conn, manager_id):
    """Ids of the people whose approver is `manager_id`."""
    ids = []
    for row in conn.execute("SELECT user_id, prefs FROM user_prefs"):
        try:
            if json.loads(row["prefs"]).get("manager_id") == manager_id:
                ids.append(row["user_id"])
        except ValueError:
            continue
    return ids


def can_approve(conn, user, week_user_id):
    return bool(user["is_admin"]) or week_user_id in reports_of(conn, user["id"])


def dashboard(conn, user, projects):
    """Personal dashboard hook (core lot v0.10): this week, the bank, approvals waiting."""
    import datetime as dt
    from . import weeks
    start = weeks.monday()
    week = weeks.week_row(conn, user["id"], start)
    rows = weeks.entries(conn, week["id"]) if week else []
    total = round(sum(r["hours"] for r in rows), 2)
    missing = sum(1 for r in rows if not r["description"].strip())
    status = catalog.STATUSES[week["status"]] if week else "Draft"
    bank = balance(conn, user["id"])
    items = [{"title": "Semaine du {} : {} h saisies".format(start.isoformat(), total), "href": "#/timesheet",
              "project": "Timesheet", "status": status, "late": bool(missing), "due": None,
              "meta": "{} description(s) manquante(s)".format(missing) if missing else ""}]
    if bank["remaining"] is not None:
        items.append({"title": "Banque de vacances : {} h restantes".format(bank["remaining"]), "href": "#/settings",
                      "project": "Timesheet", "status": "", "late": bank["remaining"] < 0, "due": None,
                      "meta": "{} h au {}, {} h prises depuis".format(bank["bank"], bank["since"], bank["used"])})
    sections = [{"key": "timesheet", "title": "Ma feuille de temps", "items": items, "total": len(items), "empty": "",
                 "href": "#/timesheet", "kpi": {"label": "Heures cette semaine", "value": total,
                                                "tone": "warn" if missing else "neutral",
                                                "note": "{} sans description".format(missing) if missing else status}}]
    reports = None if user["is_admin"] else reports_of(conn, user["id"])
    if user["is_admin"] or reports:
        sql = ("SELECT w.week_start, u.display_name FROM timesheet_weeks w JOIN users u ON u.id = w.user_id "
               "WHERE w.status = 'submitted'")
        params = []
        if reports is not None:
            sql += " AND w.user_id IN ({})".format(",".join("?" * len(reports)))
            params = reports
        waiting = conn.execute(sql + " ORDER BY w.week_start", params).fetchall()
        sections.append({"key": "approvals", "title": "Feuilles de temps à approuver",
                         "items": [{"title": "{} · semaine du {}".format(r["display_name"], r["week_start"]),
                                    "href": "#/timesheet/approbation", "project": "Timesheet", "status": "Soumise",
                                    "late": r["week_start"] < (dt.date.today() - dt.timedelta(days=13)).isoformat(),
                                    "due": None, "meta": ""} for r in waiting],
                         "total": len(waiting), "empty": "Aucune feuille en attente.", "href": "#/timesheet/approbation",
                         "kpi": {"label": "À approuver", "value": len(waiting), "tone": "warn" if waiting else "neutral"}})
    return sections


def api_balance(ctx):
    """GET /api/timesheet/leave: my bank, what is taken, what is left (settings screen)."""
    info = balance(ctx.conn, ctx.user["id"])
    info["is_manager"] = bool(reports_of(ctx.conn, ctx.user["id"]))  # « Approbation » in the side bar
    return info
