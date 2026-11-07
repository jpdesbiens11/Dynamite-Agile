"""Diamond · « Coûts et budget » (0.60.61, D-O-070): what the product and the project cost, to decide and to convince.

Three inputs, one result:
  hypothèses  currency, number of prototypes, three production volumes (e.g. 100 / 1 000 / 10 000), contingency %, hourly
              rate given to the team's hours (Timesheet), notes;
  NRE         the one-time costs (non-recurring engineering): engineering, tooling and moulds, test and certification,
              software, equipment, fixtures… each with its PDP phase (A to D) and how sure the amount is (estimate, quote,
              committed, paid);
  pièces      the cost of each part of Diamond (« Structure fonctionnelle → Pièces ») and of any other line (packaging,
              assembly, notice…): quantity per unit, unit price in prototype and at the three volumes, supplier, basis;
  budget      computed (costs_budget.py): unit cost of the product in prototype and in production, the NRE amortised per
              unit at each volume, the project budget (NRE + prototypes + team time + contingency), what is already
              committed or paid -- the page shown to investors or to the department that supports the project.

Every table is tied to projects(id) (backup, copy, restore by the core); every write is journalled.
"""
import json

from core import audit, db, validate
from core.errors import ApiError

from . import functions as F

CURRENCIES = ("CAD", "USD", "EUR")
CATEGORIES = {"ingenierie": "Ingénierie et conception", "outillage": "Outillage et moules", "prototypes": "Prototypes et maquettes",
              "essais": "Essais et validation", "certification": "Certification et normes", "logiciel": "Logiciels et licences",
              "equipement": "Équipement et gabarits", "autre": "Autre"}
PHASES = {"": "—", "A": "A. Discovery", "B": "B. Concept", "C": "C. Design", "D": "D. Validation et lancement"}
BASES = {"estimation": "Estimation", "soumission": "Soumission", "engage": "Engagé", "paye": "Payé"}
MAX_NRE, MAX_LINES, MAX_AMOUNT = 200, 300, 1e9
DEFAULTS = {"currency": "CAD", "proto_qty": 3, "volumes": [100, 1000, 10000], "contingency": 15.0, "labour_rate": 0.0, "notes": ""}


def _num(body, name, label, low=0.0, high=MAX_AMOUNT, required=False, integer=False):
    raw = body.get(name)
    if raw in (None, ""):
        if required:
            raise ApiError(400, "{} obligatoire.".format(label))
        return None
    try:
        value = float(str(raw).replace(" ", "").replace(" ", "").replace(",", "."))
    except ValueError:
        raise ApiError(400, "{} : nombre attendu (reçu « {} »). Correctif : par exemple 1250 ou 12,50.".format(label, str(raw)[:20]))
    if value != value or value < low or value > high:
        raise ApiError(400, "{} : entre {:g} et {:g}.".format(label, low, high))
    return int(round(value)) if integer else round(value, 4)


def _text(body, name, label, limit, required=False):
    value = " ".join(str(body.get(name) or "").split())
    if required and not value:
        raise ApiError(400, "{} obligatoire. Correctif : quelques mots (ex. « Moule d'injection du boîtier »).".format(label))
    if len(value) > limit:
        raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(value)))
    return value


def _choice(body, name, allowed, label, default):
    value = str(body.get(name) if body.get(name) is not None else default)
    if value not in allowed:
        raise ApiError(400, "{} « {} » inconnu(e). Correctif : {}.".format(label, value[:20], ", ".join(k or "—" for k in allowed)))
    return value


def settings(conn, pid):
    row = conn.execute("SELECT * FROM diamond_cost_settings WHERE project_id = ?", (pid,)).fetchone()
    out = dict(DEFAULTS)
    if row:
        out.update({k: row[k] for k in ("currency", "proto_qty", "contingency", "labour_rate", "notes")})
        try:
            vols = json.loads(row["volumes"])
            if isinstance(vols, list) and len(vols) == 3:
                out["volumes"] = [int(v) for v in vols]
        except (TypeError, ValueError):
            pass
    return out


def nre_rows(conn, pid):
    return [dict(r) for r in conn.execute("SELECT * FROM diamond_cost_nre WHERE project_id = ? ORDER BY position, number", (pid,))]


def lines(conn, pid):
    """Every part of Diamond (with its cost line when it has one), then the free lines."""
    costs = [dict(r) for r in conn.execute("SELECT * FROM diamond_cost_parts WHERE project_id = ? ORDER BY position, id", (pid,))]
    by_part = {c["part_id"]: c for c in costs if c["part_id"]}
    out = []
    for p in conn.execute("SELECT id, number, name, kind FROM diamond_parts WHERE project_id = ? ORDER BY position, number", (pid,)):
        c = by_part.get(p["id"]) or {"id": None, "part_id": p["id"], "qty": 1, "proto_unit": None, "prod_1": None, "prod_2": None,
                                     "prod_3": None, "supplier": "", "basis": "estimation", "notes": ""}
        out.append(dict(c, name=p["name"], code="P-{}".format(p["number"]), kind=p["kind"]))
    out += [dict(c, code="", kind="other") for c in costs if not c["part_id"]]
    return out


def labour_hours(conn, pid):
    try:
        return float(conn.execute("SELECT COALESCE(SUM(hours), 0) FROM timesheet_entries WHERE project_id = ?", (pid,)).fetchone()[0])
    except Exception:  # Timesheet absent from this installation
        return 0.0


def payload(conn, pid):
    from .costs_budget import budget
    s = settings(conn, pid)
    nre, ls = nre_rows(conn, pid), lines(conn, pid)
    return {"settings": s, "nre": nre, "lines": ls, "budget": budget(s, nre, ls, labour_hours(conn, pid)),
            "labels": {"categories": CATEGORIES, "phases": PHASES, "bases": BASES, "currencies": list(CURRENCIES)}}


def _log(ctx, action, table, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, table, oid, details, ctx.ip)


def api_get(ctx):
    return payload(ctx.conn, F.access(ctx))


def save_settings(conn, pid, s, user_id):
    conn.execute(
        "INSERT INTO diamond_cost_settings (project_id, currency, proto_qty, volumes, contingency, labour_rate, notes, updated_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET currency = excluded.currency, proto_qty = excluded.proto_qty, "
        "volumes = excluded.volumes, contingency = excluded.contingency, labour_rate = excluded.labour_rate, notes = excluded.notes, "
        "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
        (pid, s["currency"], s["proto_qty"], json.dumps(s["volumes"]), s["contingency"], s["labour_rate"], s["notes"], user_id, db.utc_now()))


def api_settings(ctx):
    pid = F.access(ctx, "editor")
    s = settings(ctx.conn, pid)
    b = ctx.body
    if "currency" in b:
        s["currency"] = _choice(b, "currency", CURRENCIES, "Devise", "CAD")
    if "proto_qty" in b:
        s["proto_qty"] = _num(b, "proto_qty", "Nombre de prototypes", 0, 10000, True, True)
    if "volumes" in b:
        vols = b.get("volumes")
        if not isinstance(vols, list) or len(vols) != 3:
            raise ApiError(400, "Trois volumes de production attendus (ex. 100, 1 000, 10 000).")
        vals = [_num({"v": v}, "v", "Volume", 1, 1e8, True, True) for v in vols]
        if not vals[0] < vals[1] < vals[2]:
            raise ApiError(400, "Volumes : du plus petit au plus grand (ex. 100, 1 000, 10 000).")
        s["volumes"] = vals
    if "contingency" in b:
        s["contingency"] = _num(b, "contingency", "Contingence (%)", 0, 100, True)
    if "labour_rate" in b:
        s["labour_rate"] = _num(b, "labour_rate", "Taux horaire de l'équipe", 0, 10000, True)
    if "notes" in b:
        s["notes"] = str(b.get("notes") or "").strip()[:2000]
    save_settings(ctx.conn, pid, s, ctx.user["id"])
    _log(ctx, "diamond_cost_settings", "projects", pid, {k: s[k] for k in ("currency", "proto_qty", "volumes", "contingency", "labour_rate")})
    return payload(ctx.conn, pid)


NRE_FIELDS = ("title", "category", "phase", "amount", "basis", "supplier", "notes")


def _nre_fields(body, partial):
    out = {}
    if not partial or "title" in body:
        out["title"] = _text(body, "title", "Intitulé", 160, True)
    if not partial or "category" in body:
        out["category"] = _choice(body, "category", CATEGORIES, "Catégorie", "ingenierie")
    if not partial or "phase" in body:
        out["phase"] = _choice(body, "phase", PHASES, "Phase", "")
    if not partial or "amount" in body:
        out["amount"] = _num(body, "amount", "Montant") or 0.0
    if not partial or "basis" in body:
        out["basis"] = _choice(body, "basis", BASES, "Base", "estimation")
    if not partial or "supplier" in body:
        out["supplier"] = _text(body, "supplier", "Fournisseur", 120)
    if not partial or "notes" in body:
        out["notes"] = str(body.get("notes") or "").strip()[:2000]
    return out


def add_nre(conn, user_id, pid, fields):
    if conn.execute("SELECT COUNT(*) FROM diamond_cost_nre WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_NRE:
        raise ApiError(409, "{} lignes NRE au maximum par Space. Correctif : regroupez des lignes voisines.".format(MAX_NRE))
    number, pos = conn.execute("SELECT COALESCE(MAX(number), 0) + 1, COALESCE(MAX(position), -1) + 1 FROM diamond_cost_nre "
                               "WHERE project_id = ?", (pid,)).fetchone()
    values = dict({"category": "ingenierie", "phase": "", "amount": 0.0, "basis": "estimation", "supplier": "", "notes": ""}, **fields)
    now = db.utc_now()
    return conn.execute("INSERT INTO diamond_cost_nre (project_id, number, position, {}, created_by, created_at, updated_by, updated_at) "
                        "VALUES (?, ?, ?, {}, ?, ?, ?, ?)".format(", ".join(NRE_FIELDS), ", ".join("?" * len(NRE_FIELDS))),
                        [pid, number, pos] + [values[k] for k in NRE_FIELDS] + [user_id, now, user_id, now]).lastrowid


def _row(ctx, pid, table, label):
    row = ctx.conn.execute("SELECT * FROM {} WHERE id = ? AND project_id = ?".format(table),
                           (validate.int_param(ctx.params, "oid"), pid)).fetchone()
    if row is None:
        raise ApiError(404, "{} introuvable dans ce Space. Correctif : rechargez la page.".format(label))
    return dict(row)


def api_nre_create(ctx):
    pid = F.access(ctx, "editor")
    fields = _nre_fields(ctx.body, partial=False)
    oid = add_nre(ctx.conn, ctx.user["id"], pid, fields)
    _log(ctx, "diamond_nre_create", "diamond_cost_nre", oid, {"title": fields["title"], "amount": fields["amount"]})
    return dict(payload(ctx.conn, pid), created=oid)


def api_nre_update(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid, "diamond_cost_nre", "Ligne NRE")
    fields = _nre_fields(ctx.body, partial=True)
    if fields:
        ctx.conn.execute("UPDATE diamond_cost_nre SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
            ", ".join("{} = ?".format(k) for k in fields)), list(fields.values()) + [ctx.user["id"], db.utc_now(), row["id"]])
        _log(ctx, "diamond_nre_update", "diamond_cost_nre", row["id"], {k: [row[k], v] for k, v in fields.items() if row[k] != v})
    return payload(ctx.conn, pid)


def api_nre_delete(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid, "diamond_cost_nre", "Ligne NRE")
    ctx.conn.execute("DELETE FROM diamond_cost_nre WHERE id = ?", (row["id"],))
    _log(ctx, "diamond_nre_delete", "diamond_cost_nre", row["id"], {"title": row["title"], "amount": row["amount"]})
    return payload(ctx.conn, pid)


LINE_FIELDS = ("name", "qty", "proto_unit", "prod_1", "prod_2", "prod_3", "supplier", "basis", "notes")


def _line_fields(body, partial, free):
    out = {}
    if free and (not partial or "name" in body):
        out["name"] = _text(body, "name", "Désignation", 160, True)
    if not partial or "qty" in body:
        out["qty"] = _num(body, "qty", "Quantité par produit", 0, 100000) if body.get("qty") not in (None, "") else 1
    for k, label in (("proto_unit", "Prix unitaire en prototype"), ("prod_1", "Prix au 1er volume"), ("prod_2", "Prix au 2e volume"),
                     ("prod_3", "Prix au 3e volume")):
        if not partial or k in body:
            out[k] = _num(body, k, label)
    if not partial or "supplier" in body:
        out["supplier"] = _text(body, "supplier", "Fournisseur", 120)
    if not partial or "basis" in body:
        out["basis"] = _choice(body, "basis", BASES, "Base", "estimation")
    if not partial or "notes" in body:
        out["notes"] = str(body.get("notes") or "").strip()[:1000]
    return out


def add_line(conn, user_id, pid, part_id, fields):
    if conn.execute("SELECT COUNT(*) FROM diamond_cost_parts WHERE project_id = ?", (pid,)).fetchone()[0] >= MAX_LINES:
        raise ApiError(409, "{} lignes de coût au maximum par Space.".format(MAX_LINES))
    values = dict({"name": "", "qty": 1, "proto_unit": None, "prod_1": None, "prod_2": None, "prod_3": None, "supplier": "",
                   "basis": "estimation", "notes": ""}, **fields)
    pos = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM diamond_cost_parts WHERE project_id = ?", (pid,)).fetchone()[0]
    now = db.utc_now()
    return conn.execute("INSERT INTO diamond_cost_parts (project_id, part_id, position, {}, created_by, created_at, updated_by, updated_at) "
                        "VALUES (?, ?, ?, {}, ?, ?, ?, ?)".format(", ".join(LINE_FIELDS), ", ".join("?" * len(LINE_FIELDS))),
                        [pid, part_id, pos] + [values[k] for k in LINE_FIELDS] + [user_id, now, user_id, now]).lastrowid


def api_line_create(ctx):
    """A cost for a part of Diamond (part_id) or a free line (name: packaging, assembly, notice…)."""
    pid = F.access(ctx, "editor")
    part_id = ctx.body.get("part_id")
    if part_id not in (None, ""):
        try:
            part_id = int(part_id)
        except (TypeError, ValueError):
            raise ApiError(400, "Pièce inconnue. Correctif : rechargez la page.")
        if not ctx.conn.execute("SELECT 1 FROM diamond_parts WHERE id = ? AND project_id = ?", (part_id, pid)).fetchone():
            raise ApiError(404, "Pièce introuvable dans ce Space. Correctif : rechargez la page.")
        if ctx.conn.execute("SELECT 1 FROM diamond_cost_parts WHERE part_id = ?", (part_id,)).fetchone():
            raise ApiError(409, "Cette pièce a déjà sa ligne de coût. Correctif : rechargez la page.")
        fields = _line_fields(ctx.body, partial=True, free=False)
    else:
        part_id = None
        fields = _line_fields(ctx.body, partial=False, free=True)
    oid = add_line(ctx.conn, ctx.user["id"], pid, part_id, fields)
    _log(ctx, "diamond_cost_line_create", "diamond_cost_parts", oid, {"part_id": part_id, **{k: v for k, v in fields.items() if v not in (None, "")}})
    return dict(payload(ctx.conn, pid), created=oid)


def api_line_update(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid, "diamond_cost_parts", "Ligne de coût")
    fields = _line_fields(ctx.body, partial=True, free=row["part_id"] is None)
    if fields:
        ctx.conn.execute("UPDATE diamond_cost_parts SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
            ", ".join("{} = ?".format(k) for k in fields)), list(fields.values()) + [ctx.user["id"], db.utc_now(), row["id"]])
        _log(ctx, "diamond_cost_line_update", "diamond_cost_parts", row["id"], {k: [row[k], v] for k, v in fields.items() if row[k] != v})
    return payload(ctx.conn, pid)


def api_line_delete(ctx):
    pid = F.access(ctx, "editor")
    row = _row(ctx, pid, "diamond_cost_parts", "Ligne de coût")
    ctx.conn.execute("DELETE FROM diamond_cost_parts WHERE id = ?", (row["id"],))
    _log(ctx, "diamond_cost_line_delete", "diamond_cost_parts", row["id"], {"name": row["name"], "part_id": row["part_id"]})
    return payload(ctx.conn, pid)
