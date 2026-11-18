"""Diamond · the platform's catalogue of competencies (0.60.116, D-O-129): add, rename, change the icon or the BDC content,
reorder, deactivate, choose the starter columns of a new Space (0.60.118, D-O-131). Only an administrator or an « Admin du Space » of DEMO (which holds the catalogue and the BDC) does it.
A competency is never deleted: deactivated, it is no longer offered, and the ratings that use it stay. Its BDC page is
regenerated after each change (competency_bdc.py), unless someone edited it by hand. Every write is journalled.
"""
import json

from core import audit, db
from core.errors import ApiError

from . import competencies as CP
from . import data_competencies as DC

MAX_COMPETENCIES = 60


def _require(ctx):
    pid = CP.host_id(ctx.conn)
    if pid is None:
        raise ApiError(409, "Le Space DEMO (qui porte la BDC) n'existe pas encore. Correctif : redémarrez le serveur, il le crée.")
    if not CP.can_manage(ctx.conn, ctx.user):
        raise ApiError(403, "Catalogue des compétences : réservé aux administrateurs et aux Admin du Space DEMO.")
    CP.seed(ctx.conn)
    return pid


def _text(body, name, label, limit, required=False):
    value = " ".join(str(body.get(name) or "").split())
    if required and not value:
        raise ApiError(400, "{} obligatoire.".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
    return value


def _fields(body, partial):
    out = {}
    if not partial or "name" in body:
        out["name"] = _text(body, "name", "Nom (terme technique en anglais, ex. « Thermal analysis »)", CP.LIMITS["name"], True)
    if not partial or "summary" in body:
        out["summary"] = _text(body, "summary", "Résumé", CP.LIMITS["summary"])
    if not partial or "icon" in body:
        icon = str(body.get("icon") or "").strip()
        if icon not in DC.ICONS:
            raise ApiError(400, "Icône « {} » inconnue. Correctif : {}.".format(icon[:20], ", ".join(DC.ICONS)))
        out["icon"] = icon
    if "details" in body:
        details = body.get("details")
        if not isinstance(details, dict):
            raise ApiError(400, "details : un objet {} attendu.".format(", ".join(DC.DETAIL_KEYS)))
        clean = {}
        for key in DC.DETAIL_KEYS:
            value = str(details.get(key) or "").strip()
            if len(value) > CP.LIMITS["detail"]:
                raise ApiError(400, "{} : {} caractères au maximum.".format(DC.DETAIL_LABELS[key], CP.LIMITS["detail"]))
            clean[key] = value
        out["details"] = json.dumps(clean, ensure_ascii=False)
    if "active" in body:
        out["active"] = 1 if body.get("active") else 0
    if "starter" in body:
        out["starter"] = 1 if body.get("starter") else 0
    if "position" in body:
        out["position"] = int(body.get("position") or 0)
    return out


def _after(ctx):
    from . import competency_bdc
    competency_bdc.after_change(ctx)


def api_create(ctx):
    pid = _require(ctx)
    code = str(ctx.body.get("code") or "").strip().upper()
    if not CP.CODE_RE.match(code):
        raise ApiError(400, "Code « {} » : 2 à 8 lettres ou chiffres majuscules, commençant par une lettre (ex. EMC, OPTICS).".format(code[:12]))
    if ctx.conn.execute("SELECT 1 FROM diamond_competencies WHERE code = ?", (code,)).fetchone():
        raise ApiError(409, "Le code {} existe déjà dans le catalogue. Correctif : un autre code, ou réactivez celui-ci.".format(code))
    if ctx.conn.execute("SELECT COUNT(*) FROM diamond_competencies").fetchone()[0] >= MAX_COMPETENCIES:
        raise ApiError(409, "{} compétences au maximum. Correctif : regroupez des compétences proches.".format(MAX_COMPETENCIES))
    fields = _fields(ctx.body, partial=False)
    fields.setdefault("details", json.dumps({k: "" for k in DC.DETAIL_KEYS}))
    position = ctx.conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM diamond_competencies").fetchone()[0]
    now = db.utc_now()
    ctx.conn.execute("INSERT INTO diamond_competencies (project_id, code, name, icon, summary, details, position, active, starter, "
                     "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
                     (pid, code, fields["name"], fields["icon"], fields["summary"], fields["details"], position,
                      fields.get("starter", 0), now, now))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_competency_create", "project", pid, {"code": code, "name": fields["name"]}, ctx.ip)
    _after(ctx)
    return {"catalog": CP.catalog(ctx.conn), "created": code}


def api_update(ctx):
    pid = _require(ctx)
    code = str(ctx.params.get("code") or "").upper()
    if not ctx.conn.execute("SELECT 1 FROM diamond_competencies WHERE code = ?", (code,)).fetchone():
        raise ApiError(404, "Compétence {} absente du catalogue. Correctif : rechargez la page.".format(code))
    fields = _fields(ctx.body, partial=True)
    if fields:
        sets = ", ".join("{} = ?".format(k) for k in fields)
        ctx.conn.execute("UPDATE diamond_competencies SET {}, updated_at = ? WHERE code = ?".format(sets),
                         tuple(fields.values()) + (db.utc_now(), code))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_competency_update", "project", pid, {"code": code, "fields": sorted(fields)}, ctx.ip)
    _after(ctx)
    return {"catalog": CP.catalog(ctx.conn)}
