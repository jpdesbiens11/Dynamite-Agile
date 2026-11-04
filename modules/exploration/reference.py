"""Reference plan (0.60.22, D-O-032): a Gantt drawn from the product development process (PDP) of the course and the size
of the team -- the starting plan of a Space created by « Commencer », to adjust in Exploration.

The 19 steps of the PDP (the Timesheet codes A-01 … D-21, so hours and tasks share their codes) in four phases that
share the weeks of the project (A. Discovery 20 %, B. Concept 25 %, C. Design 30 %, D. Validation 25 %), with the
reviews as milestones: Lean Canvas, Concept Review, PDR, CDR, Validation Report. A larger team runs more steps of a
phase side by side (1 track up to 2 people, 2 tracks for 3 or 4, 3 tracks from 5): each step lasts longer, the phase
does not. The owners take the tracks in turn. Finish-to-start links, so moving a task moves what follows.
"""
import datetime as dt
import math

from modules.timesheet import catalog

PHASES = [("A", "A. Discovery", 0.20), ("B", "B. Concept", 0.25), ("C", "C. Design", 0.30), ("D", "D. Validation et lancement", 0.25)]
# milestone after a step (code of the step -> (milestone code, title)); the last step of a phase closes it
MILESTONES = {"A-03": ("LCV", "Lean Canvas validé (jalon)"), "B-12": ("CRV", "Concept Review (jalon)"),
              "C-14": ("PDR", "PDR — Preliminary Design Review (jalon)"), "C-15": ("CDR", "CDR — Critical Design Review (jalon)"),
              "D-21": ("VVR", "Validation Report (jalon)")}
MIN_WEEKS, MAX_WEEKS, DEFAULT_WEEKS = 4, 104, 15


def tracks(team_size):
    return 1 if team_size <= 2 else 2 if team_size <= 4 else 3


def steps():
    """[(phase letter, code, title)] -- the PDP of the Timesheet catalogue, the phase prefix removed."""
    out = []
    for code, label in catalog.TASK_SETS[catalog.DEFAULT_SET][1]:
        title = label.split(" · ", 1)[-1]
        out.append((code[0], code, title))
    return out


def build(weeks, owners, first="J0"):
    """Tasks for exploration_tasks (code, phase, title, description, owner_id, duration_weeks, predecessors)."""
    weeks = max(MIN_WEEKS, min(int(weeks or DEFAULT_WEEKS), MAX_WEEKS))
    k = tracks(len(owners))
    out, gate = [], first
    all_steps = steps()
    for letter, phase, share in PHASES:
        mine = [s for s in all_steps if s[0] == letter]
        if not mine:
            continue
        segments, size = [], 0  # a milestone inside the phase closes a segment: its steps wait for it
        for _l, code, _t in mine:
            size += 1
            if code in MILESTONES:
                segments.append(size)
                size = 0
        segments += [size] if size else []
        rounds = sum(math.ceil(n / k) for n in segments)
        length = max(0.5, round(weeks * share / rounds * 2) / 2)  # half weeks
        last_of_track, opened = {}, gate
        for i, (_l, code, title) in enumerate(mine):
            track = i % k
            preds = [last_of_track.get(track, opened)]
            owner = owners[(len(out) + track) % len(owners)] if owners else None
            out.append({"code": code, "phase": phase, "title": title, "owner_id": owner, "duration_weeks": length,
                        "predecessors": " ".join(p for p in preds if p),
                        "description": "Étape du PDP (code de temps {}). Plan de référence : ajustez la durée et le responsable.".format(code)})
            last_of_track[track] = code
            if code in MILESTONES:
                mcode, mtitle = MILESTONES[code]
                ends = [last_of_track[t] for t in sorted(last_of_track)]  # the review waits for every track of the phase
                out.append({"code": mcode, "phase": phase, "title": mtitle, "owner_id": None, "duration_weeks": 0,
                            "predecessors": " ".join(dict.fromkeys(ends)), "description": "Revue du PDP."})
                last_of_track = {t: mcode for t in last_of_track}
                opened = mcode
        ends = list(dict.fromkeys(last_of_track[t] for t in sorted(last_of_track)))
        gate = ends[0] if len(ends) == 1 else ends[-1]
        if len(ends) > 1:  # a phase ends when all its tracks end
            gate_code = "FIN-" + letter
            out.append({"code": gate_code, "phase": phase, "title": "Fin de la phase " + phase, "owner_id": None,
                        "duration_weeks": 0, "predecessors": " ".join(ends), "description": ""})
            gate = gate_code
    return out


def apply(ctx, project_id, start, weeks, owners):
    """Replaces the kick-off-only plan of a new Space by the reference plan. Returns the number of tasks."""
    from . import plan
    have = ctx.conn.execute("SELECT code FROM exploration_tasks WHERE project_id = ?", (project_id,)).fetchall()
    if any(r["code"] != "J0" for r in have):
        return 0  # a plan already made: never touched
    if start:
        plan.set_start(ctx.conn, project_id, start)
    pos = len(have)
    if not have:
        plan.insert(ctx, project_id, {"code": "J0", "phase": "Lancement", "title": "Lancement du projet", "description": "",
                                      "owner_id": None, "duration_weeks": 0, "start_date": None, "predecessors": "",
                                      "status": "todo", "progress": 0, "note": ""}, 0)
        pos = 1
    for i, t in enumerate(build(weeks, owners)):
        plan.insert(ctx, project_id, dict(t, start_date=None, status="todo", progress=0, note=""), pos + i)
    ctx.conn.execute("INSERT INTO exploration_counters (project_id, next_task) VALUES (?, 1) ON CONFLICT(project_id) DO NOTHING",
                     (project_id,))
    return len(build(weeks, owners))


def parse_start(value):
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
