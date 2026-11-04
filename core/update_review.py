"""Step-by-step review of a framework update (core lot v0.26, D-B-094).

A checked update zip is never applied in one click: it is cut into review steps -- one per change declared by
Claude in UPDATE_CHANGES.json (title, reason, files), plus one « Changement non déclaré » step for every changed
file no declared change mentions. An administrator opens each step (its files and their line-by-line differences)
and approves or refuses it. All steps approved -> « Appliquer » is allowed (all or nothing: the code was tested as
a whole). One refusal closes the review and writes a « Retour pour Claude » text listing what was refused and why.

State: data/updates/incoming/<token>.review.json (next to <token>.zip). Every opening, decision and refusal goes
to the audit log. The same steps serve the « Site complet » import (core/sitemove.py) for its code part.
"""
import difflib
import hashlib
import json
import re
from pathlib import Path

from . import audit, db
from .errors import ApiError

CHANGES_FILE = "UPDATE_CHANGES.json"
UNDECLARED = "undeclared"
MAX_DIFF_LINES = 600
TEXT_EXT = re.compile(r"\.(py|js|css|md|txt|json|html|svg|bat|sh|cfg|toml|sql|csv)$|^\.gitignore$|/\.gitignore$")

CHANGES_HELP = ("UPDATE_CHANGES.json à la racine du zip : {\"changes\": [{\"id\": \"C1\", \"title\": \"…\", \"why\": \"…\", "
                "\"files\": [\"modules/…/x.py\", …]}, …]} — chaque fichier ajouté, modifié ou retiré figure dans au moins "
                "un changement.")


def _member(z, name):
    return next((i for i in z.infolist() if not i.is_dir() and (i.filename == name or i.filename.endswith("/" + name))
                 and i.filename.count("/") <= 1), None)


def declared_changes(z):
    """([change dicts], [problems]) read from UPDATE_CHANGES.json; ([], []) when the file is absent."""
    info = _member(z, CHANGES_FILE)
    if info is None:
        return [], []
    try:
        raw = json.loads(z.read(info).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return [], ["{} illisible ({}). Correctif : {}".format(CHANGES_FILE, exc, CHANGES_HELP)]
    items = raw.get("changes") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return [], ["{} : liste « changes » absente. Correctif : {}".format(CHANGES_FILE, CHANGES_HELP)]
    out, problems = [], []
    for n, item in enumerate(items, 1):
        if not isinstance(item, dict) or not str(item.get("title") or "").strip():
            problems.append("{} : changement n° {} sans titre. Correctif : {}".format(CHANGES_FILE, n, CHANGES_HELP))
            continue
        files = item.get("files") or []
        if not isinstance(files, list):
            files = [files]
        out.append({"id": re.sub(r"[^\w.-]", "", str(item.get("id") or "C{}".format(n)))[:20] or "C{}".format(n),
                    "title": str(item["title"]).strip()[:200], "why": str(item.get("why") or "").strip()[:2000],
                    "files": [re.sub(r"^(\./)+|^/+", "", str(f).strip().replace("\\", "/")) for f in files if str(f).strip()][:500]})
    return out, problems


def build_steps(report):
    """Review steps of a checked report (core.update.check): declared changes, then the undeclared files."""
    touched = {f: "added" for f in report["added"]}
    touched.update({f: "changed" for f in report["changed"]})
    touched.update({f: "removed" for f in report["removed"]})
    declared, _problems = declared_changes(report["zip"])
    steps, covered = [], set()
    for ch in declared:
        files = [f for f in ch["files"] if f in touched]
        covered.update(files)
        steps.append({"id": ch["id"], "title": ch["title"], "why": ch["why"], "kind": "declared",
                      "files": [{"path": f, "state": touched[f]} for f in files],
                      "unknown": [f for f in ch["files"] if f not in touched][:50]})
    rest = sorted(f for f in touched if f not in covered)
    if rest:
        steps.append({"id": UNDECLARED, "title": "Changement non déclaré", "kind": UNDECLARED,
                      "why": ("Fichiers ajoutés, modifiés ou retirés qu'aucun changement de {} ne mentionne. Vérifiez chacun : "
                              "un changement non expliqué est une raison de refuser.").format(CHANGES_FILE),
                      "files": [{"path": f, "state": touched[f]} for f in rest], "unknown": []})
    for n, step in enumerate(steps, 1):
        step.update(n=n, status="pending", seen_by=[], by=None, at=None, comment="")
    return steps


# --------------------------------------------------------------------------
# State on disk
# --------------------------------------------------------------------------
def _path(folder, token):
    token = re.sub(r"[^a-f0-9]", "", str(token or ""))[:32]
    if not token:
        raise ApiError(404, "Revue introuvable.")
    return Path(folder) / (token + ".review.json")


def create(folder, token, version, current, steps, kind="framework", extra=None):
    state = {"token": token, "kind": kind, "version": version, "current": current, "created_at": db.utc_now(),
             "closed": False, "refused": False, "steps": steps}
    state.update(extra or {})
    _path(folder, token).write_text(json.dumps(state, ensure_ascii=False, indent=1), "utf-8")
    return state


def load(folder, token):
    path = _path(folder, token)
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        raise ApiError(404, "Revue introuvable (expirée, appliquée ou abandonnée). Correctif : vérifiez de nouveau le fichier.")


def save(folder, state):
    _path(folder, state["token"]).write_text(json.dumps(state, ensure_ascii=False, indent=1), "utf-8")


def summary(state):
    steps = state["steps"]
    cut = [{k: s.get(k) for k in ("n", "id", "title", "why", "kind", "status", "by", "at", "comment", "options")}
           | {"files": len(s.get("files", [])), "count": s.get("count")} for s in steps]
    approved = sum(1 for s in steps if s["status"] == "approved")
    return {"token": state["token"], "kind": state["kind"], "version": state.get("version"), "current": state.get("current"),
            "closed": state["closed"], "refused": state["refused"], "steps": cut, "approved": approved, "total": len(steps),
            "ready": not state["closed"] and approved == len(steps) and bool(steps),
            "feedback": feedback(state) if state["refused"] else ""}


def step_of(state, n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 0
    if not 1 <= n <= len(state["steps"]):
        raise ApiError(404, "Étape {} introuvable : la revue a {} étape(s).".format(n, len(state["steps"])))
    return state["steps"][n - 1]


# --------------------------------------------------------------------------
# Differences of one step
# --------------------------------------------------------------------------
def _text(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def file_diff(path, old, new):
    """{path, state, diff | binary} for one file: unified diff (bounded) or sizes and SHA-256 of a binary."""
    state = "added" if old is None else "removed" if new is None else "changed"
    out = {"path": path, "state": state}
    old_t = "" if old is None else _text(old)
    new_t = "" if new is None else _text(new)
    if old_t is None or new_t is None or not TEXT_EXT.search(path):
        sha = lambda b: hashlib.sha256(b).hexdigest()[:16] if b is not None else "—"
        out["binary"] = "Fichier binaire : {} → {} octets (SHA-256 {} → {}).".format(
            len(old) if old is not None else 0, len(new) if new is not None else 0, sha(old), sha(new))
        return out
    lines = list(difflib.unified_diff(old_t.splitlines(), new_t.splitlines(), "avant/" + path, "après/" + path, n=3, lineterm=""))
    out["plus"] = sum(1 for x in lines if x.startswith("+") and not x.startswith("+++"))
    out["minus"] = sum(1 for x in lines if x.startswith("-") and not x.startswith("---"))
    out["truncated"] = max(0, len(lines) - MAX_DIFF_LINES)
    out["diff"] = lines[:MAX_DIFF_LINES]
    return out


def framework_detail(step, root, z, files):
    """Files of a framework step with their differences (old = code in place under root, new = zip)."""
    out = []
    for f in step.get("files", []):
        rel = f["path"]
        old = (root / rel).read_bytes() if (root / rel).is_file() else None
        new = z.read(files[rel]) if rel in files else None
        out.append(file_diff(rel, old, new))
    return out


# --------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------
def mark_seen(state, step, user):
    if user["username"] not in step["seen_by"]:
        step["seen_by"].append(user["username"])


def decide(ctx, folder, state, n, decision, comment="", options=None, need_seen=True):
    """Approve or refuse step n. Refusal closes the review. Returns the summary."""
    if state["closed"]:
        raise ApiError(409, "Cette revue est close ({}). Correctif : vérifiez de nouveau le fichier.".format(
            "refusée" if state["refused"] else "appliquée"))
    step = step_of(state, n)
    if decision not in ("approve", "refuse"):
        raise ApiError(400, "Décision « {} » inconnue (acceptées : approve, refuse).".format(decision))
    comment = str(comment or "").strip()[:4000]
    if decision == "approve" and need_seen and ctx.user["username"] not in step["seen_by"]:
        raise ApiError(409, "Étape {} jamais ouverte par vous. Correctif : ouvrez-la et lisez ses différences avant de "
                            "l'approuver.".format(step["n"]))
    if decision == "refuse" and not comment:
        raise ApiError(400, "Refus sans raison. Correctif : écrivez ce qui ne va pas ; ce texte part dans le retour pour Claude.")
    step.update(status="approved" if decision == "approve" else "refused", by=ctx.user["display_name"], at=db.utc_now(),
                comment=comment)
    if options is not None:
        step["options"] = options
    if decision == "refuse":
        state.update(closed=True, refused=True)
    save(folder, state)
    audit.log_action(ctx.conn, ctx.user["id"], "review_" + decision, "update", None,
                     {"kind": state["kind"], "version": state.get("version"), "step": step["n"], "title": step["title"],
                      "comment": comment[:300]}, ctx.ip)
    return summary(state)


def require_ready(state):
    if state["closed"]:
        raise ApiError(409, "Cette revue est close ({}). Correctif : vérifiez de nouveau le fichier.".format(
            "refusée" if state["refused"] else "déjà appliquée"))
    waiting = [s for s in state["steps"] if s["status"] != "approved"]
    if waiting or not state["steps"]:
        raise ApiError(409, "Application refusée : {} étape(s) sur {} pas encore approuvée(s) ({}). Correctif : ouvrez et "
                            "approuvez chaque étape de la revue.".format(len(waiting), len(state["steps"]),
                                                                        ", ".join(str(s["n"]) for s in waiting[:10])))


def close(folder, state):
    state["closed"] = True
    save(folder, state)


def feedback(state):
    """« Retour pour Claude »: what was refused and why, what was approved (to paste in the next conversation)."""
    lines = ["# Retour de revue — mise à jour {} (en ligne : {})".format(state.get("version"), state.get("current")), "",
             "La revue pas à pas de Admin → Update a refusé cette mise à jour. Corrige ce qui suit, garde ce qui a été "
             "approuvé, mets à jour {} et rends un nouveau zip du code (même structure).".format(CHANGES_FILE), ""]
    for s in state["steps"]:
        if s["status"] == "refused":
            lines += ["## Refusé — {} ({})".format(s["title"], s["id"]), "Par {} le {}.".format(s["by"], (s["at"] or "")[:16]),
                      "", s["comment"], "", "Fichiers : " + ", ".join(f["path"] for f in s.get("files", [])[:40]), ""]
    approved = [s for s in state["steps"] if s["status"] == "approved"]
    if approved:
        lines += ["## Approuvé (à garder)"] + ["- {} ({})".format(s["title"], s["id"]) for s in approved] + [""]
    pending = [s for s in state["steps"] if s["status"] == "pending"]
    if pending:
        lines += ["## Pas encore revu"] + ["- {} ({})".format(s["title"], s["id"]) for s in pending]
    return "\n".join(lines).strip() + "\n"
