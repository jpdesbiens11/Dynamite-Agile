"""Timesheet copies (D-B-026): reuse what was already typed.

- copy ranges to other days of the same week (one range, or a whole day);
- copy a past week into the current one, day for day (lundi -> lundi…),
  added to what is there or replacing it.
Copies land in an editable week only (Brouillon / Renvoyée) and keep the
project, task, hours and description, to be fine-tuned afterwards. Nothing is
written if one target day would exceed 24 h (the message names the days);
ranges on a project no longer open to the person are skipped and reported.
"""
import datetime as dt

from core import db
from core.errors import ApiError

from . import catalog, weeks


def _insert(conn, week_id, entry, work_date):
    now = db.utc_now()
    return conn.execute(
        "INSERT INTO timesheet_entries (week_id, project_id, work_date, task_key, hours, description, created_at, "
        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (week_id, entry["project_id"], work_date, entry["task_key"], entry["hours"], entry["description"], now, now)).lastrowid


def _check_totals(conn, week_id, additions, replace=False):
    """additions: {iso day: hours to add}. Refuse if a day would pass 24 h."""
    over = []
    for day, hours in sorted(additions.items()):
        current = 0 if replace else conn.execute(
            "SELECT COALESCE(SUM(hours), 0) FROM timesheet_entries WHERE week_id = ? AND work_date = ?",
            (week_id, day)).fetchone()[0]
        if current + hours > catalog.MAX_DAY_HOURS:
            over.append("{} ({} h)".format(weeks.day_label(day), round(current + hours, 2)))
    if over:
        raise ApiError(400, "Copie refusée : plus de 24 h le {}. Correctif : copiez moins de plages, ou réduisez les "
                            "heures de ces journées d'abord.".format(", ".join(over)))


def _open_projects(ctx):
    return {p["id"] for p in weeks.loggable_projects(ctx.conn, ctx.user)}


def api_copy_days(ctx):
    """Copy ranges (entry_ids) to other days (to_days) of their week."""
    ids, to_days = ctx.body.get("entry_ids"), ctx.body.get("to_days")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, int) for i in ids) or len(ids) > 100:
        raise ApiError(400, "Aucune plage à copier. Correctif : choisissez une plage ou une journée.")
    if not isinstance(to_days, list) or not to_days or len(to_days) > 7:
        raise ApiError(400, "Aucun jour de destination. Correctif : cochez au moins un jour.")
    marks = ",".join("?" * len(ids))
    rows = db.rows(ctx.conn.execute(
        "SELECT e.*, w.user_id, w.status, w.week_start FROM timesheet_entries e JOIN timesheet_weeks w ON w.id = e.week_id "
        "WHERE e.id IN ({}) ORDER BY e.work_date, e.id".format(marks), ids).fetchall())
    if len(rows) != len(set(ids)) or any(r["user_id"] != ctx.user["id"] for r in rows) or len({r["week_id"] for r in rows}) != 1:
        raise ApiError(404, "Plages introuvables (elles doivent être à vous et dans la même semaine).")
    week = rows[0]
    weeks._editable_week(week)
    start = dt.date.fromisoformat(week["week_start"])
    days = sorted({weeks._date_in_week(d, start) for d in to_days})
    open_ids = _open_projects(ctx)
    usable = [r for r in rows if r["project_id"] in open_ids]
    additions = {}
    for day in days:
        additions[day] = sum(r["hours"] for r in usable if r["work_date"] != day)
    _check_totals(ctx.conn, week["week_id"], additions)
    made = 0
    for day in days:
        for r in usable:
            if r["work_date"] == day:
                continue  # never duplicate a range onto its own day
            _insert(ctx.conn, week["week_id"], r, day)
            made += 1
    weeks.log(ctx, "timesheet_copy_days", week["week_id"], {"entries": ids, "days": days, "created": made})
    result = weeks.api_week_for(ctx, start)
    result["copied"] = {"created": made, "skipped": len(rows) - len(usable)}
    return result


def api_recent(ctx):
    """The person's weeks that have ranges, most recent first (sources of a week copy)."""
    rows = ctx.conn.execute(
        "SELECT w.week_start, w.status, COUNT(e.id) AS ranges, COALESCE(SUM(e.hours), 0) AS total "
        "FROM timesheet_weeks w JOIN timesheet_entries e ON e.week_id = w.id WHERE w.user_id = ? "
        "GROUP BY w.id ORDER BY w.week_start DESC LIMIT 12", (ctx.user["id"],)).fetchall()
    return {"weeks": [dict(r, status_label=catalog.STATUSES[r["status"]]) for r in rows]}


def api_copy_week(ctx):
    """Copy the ranges of week `source` into week `start`, same weekday."""
    target = weeks.monday(ctx.body.get("start"))
    source = weeks.monday(ctx.body.get("source"))
    mode = ctx.body.get("mode", "add")
    if mode not in ("add", "replace"):
        raise ApiError(400, "Mode « {} » inconnu. Correctif : add (ajouter) ou replace (remplacer).".format(mode))
    if source == target:
        raise ApiError(400, "La semaine source est la semaine affichée. Correctif : choisissez une autre semaine.")
    src_week = weeks.week_row(ctx.conn, ctx.user["id"], source)
    rows = weeks.entries(ctx.conn, src_week["id"]) if src_week else []
    if not rows:
        raise ApiError(400, "La semaine du {} n'a aucune plage à copier. Correctif : choisissez une semaine remplie."
                       .format(source.isoformat()))
    week = weeks.week_row(ctx.conn, ctx.user["id"], target, create=True)
    weeks._editable_week(week)
    shift = target - source
    open_ids = _open_projects(ctx)
    usable = [r for r in rows if r["project_id"] in open_ids]
    additions = {}
    for r in usable:
        day = (dt.date.fromisoformat(r["work_date"]) + shift).isoformat()
        additions[day] = additions.get(day, 0) + r["hours"]
    _check_totals(ctx.conn, week["id"], additions, replace=mode == "replace")
    removed = 0
    if mode == "replace":
        removed = ctx.conn.execute("DELETE FROM timesheet_entries WHERE week_id = ?", (week["id"],)).rowcount
    for r in usable:
        _insert(ctx.conn, week["id"], r, (dt.date.fromisoformat(r["work_date"]) + shift).isoformat())
    weeks.log(ctx, "timesheet_copy_week", week["id"], {"from": source.isoformat(), "to": target.isoformat(),
                                                       "mode": mode, "created": len(usable), "removed": removed})
    result = weeks.api_week_for(ctx, target)
    result["copied"] = {"created": len(usable), "skipped": len(rows) - len(usable), "removed": removed}
    return result
