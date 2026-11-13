"""Routes of the classes CC / SC (0.60.101, D-O-108, classes.py): the decision on a DFMEA row, the rules and the customer
dictionary of the Space. Every write needs the editor role and is journalled; a decision always carries its reason."""
import re

from core import audit, db
from core.errors import ApiError

from . import classes as CL
from . import dfmea as DF
from . import functions as F

DECISIONS = {"CC": "Confirmer CC", "SC": "Confirmer SC", "refused": "Refuser", "clear": "Retirer la décision"}
REASON_MIN, REASON_MAX = 3, 400


def _log(ctx, action, table, oid, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, table, oid, details, ctx.ip)


def _history(conn, did):
    rows = [dict(r) for r in conn.execute(
        "SELECT h.*, u.display_name AS by_name FROM diamond_class_decisions h LEFT JOIN users u ON u.id = h.decided_by "
        "WHERE h.dfmea_id = ? ORDER BY h.decided_at DESC, h.id DESC", (did,))]
    initials = CL._who(conn, {r["decided_by"] for r in rows if r["decided_by"]})
    for r in rows:
        r["by_initials"] = (initials.get(r["decided_by"]) or {}).get("initials", "")
    return rows


def api_history(ctx):
    pid = F.access(ctx)
    row = DF._row(ctx, pid)
    return {"history": _history(ctx.conn, row["id"]), "states": CL.STATES}


def api_decide(ctx):
    """{decision: CC | SC | refused | clear, reason}: a person decides the class of the row, and says why."""
    pid = F.access(ctx, "editor")
    row = DF._row(ctx, pid)
    decision = str(ctx.body.get("decision") or "")
    if decision not in DECISIONS:
        raise ApiError(400, "Décision « {} » inconnue. Correctif : {}.".format(decision, ", ".join(DECISIONS.values())))
    reason = " ".join(str(ctx.body.get("reason") or "").split())
    if len(reason) < REASON_MIN:
        raise ApiError(400, "Justification obligatoire ({} caractères au moins) : la décision est tracée avec son nom, sa date et "
                            "sa raison. Correctif : écrivez pourquoi (ex. « peut blesser une personne »).".format(REASON_MIN))
    if len(reason) > REASON_MAX:
        raise ApiError(400, "Justification : {} caractères au maximum (reçu {}).".format(REASON_MAX, len(reason)))
    proposed = CL.propose(row["severity"], row["occurrence"], CL.rules(ctx.conn, pid))
    if decision == "refused":
        code = proposed or (row["class_code"] if row["class_state"] == "confirmed" else "")
        if not code:
            raise ApiError(400, "Rien à refuser : la règle ne propose aucune classe pour cette ligne et aucune n'est confirmée. "
                                "Correctif : « Confirmer CC » ou « Confirmer SC » si la ligne en demande une malgré la règle.")
        state = "refused"
    elif decision == "clear":
        if not row["class_state"]:
            raise ApiError(400, "Aucune décision à retirer sur cette ligne. Correctif : confirmez ou refusez la classe proposée.")
        code, state = "", ""
    else:
        code, state = decision, "confirmed"
    now = db.utc_now()
    ctx.conn.execute("UPDATE diamond_dfmea SET class_code = ?, class_state = ?, class_by = ?, class_at = ?, class_reason = ?, "
                     "class_severity = ?, class_occurrence = ? WHERE id = ?",
                     (code, state, ctx.user["id"] if state else None, now if state else "", reason if state else "",
                      row["severity"] if state else None, row["occurrence"] if state else None, row["id"]))
    ctx.conn.execute("INSERT INTO diamond_class_decisions (project_id, dfmea_id, class_code, state, severity, occurrence, reason, "
                     "decided_by, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (pid, row["id"], code or row["class_code"], state or "cleared", row["severity"], row["occurrence"], reason,
                      ctx.user["id"], now))
    _log(ctx, "diamond_dfmea_class", "diamond_dfmea", row["id"], {"decision": decision, "class": code or row["class_code"],
                                                                 "proposed": proposed, "severity": row["severity"],
                                                                 "occurrence": row["occurrence"], "reason": reason})
    return DF.payload(ctx.conn, pid)


def settings_payload(conn, pid):
    rows = DF._rows(conn, pid)
    return {"rules": CL.rules(conn, pid), "customers": CL.customers(conn, pid), "fields": {k: v[0] for k, v in CL.CUSTOMER_FIELDS.items()},
            "counts": CL.counts(rows, CL.rules(conn, pid)), "names": CL.CLASSES, "presets": CL.PRESET_CODES,
            "proposed": {k: sum(1 for r in rows if r["class_status"] == "proposed" and r["class_proposed"] == k) for k in CL.CLASSES}}


def api_get(ctx):
    return settings_payload(ctx.conn, F.access(ctx))


def _rating(body, name, label):
    try:
        value = int(body.get(name))
    except (TypeError, ValueError):
        value = -1
    if not 1 <= value <= 10:
        raise ApiError(400, "{} « {} » : un nombre de 1 à 10.".format(label, body.get(name)))
    return value


def api_settings(ctx):
    """{customer?, cc_severity?, sc_severity?, sc_occurrence?}: the rules of the proposal and the customer of the Space."""
    pid = F.access(ctx, "editor")
    conn, body = ctx.conn, ctx.body
    r = CL.rules(conn, pid)
    labels = {"cc_severity": "Sévérité qui propose une CC", "sc_severity": "Sévérité la plus basse d'une SC",
              "sc_occurrence": "Occurrence qui propose une SC"}
    for name, label in labels.items():
        if name in body:
            r[name] = _rating(body, name, label)
    if "customer" in body:
        code = str(body.get("customer") or "")
        if code not in {c["code"] for c in CL.customers(conn, pid)}:
            raise ApiError(400, "Client « {} » absent du dictionnaire du Space. Correctif : choisissez un client de la liste, ou "
                                "ajoutez-le.".format(code))
        r["customer"] = code
    if r["sc_severity"] >= r["cc_severity"]:
        raise ApiError(400, "La sévérité la plus basse d'une SC ({}) doit être sous celle qui propose une CC ({}). Correctif : par "
                            "exemple CC à 9, SC de 5 à 8.".format(r["sc_severity"], r["cc_severity"]))
    conn.execute("INSERT INTO diamond_class_settings (project_id, customer, cc_severity, sc_severity, sc_occurrence, updated_by, updated_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET customer = excluded.customer, "
                 "cc_severity = excluded.cc_severity, sc_severity = excluded.sc_severity, sc_occurrence = excluded.sc_occurrence, "
                 "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                 (pid, r["customer"], r["cc_severity"], r["sc_severity"], r["sc_occurrence"], ctx.user["id"], db.utc_now()))
    _log(ctx, "diamond_class_settings", "diamond_class_settings", pid, r)
    return settings_payload(conn, pid)


def _customer_fields(body, base):
    out = dict(base)
    for name, (label, limit) in CL.CUSTOMER_FIELDS.items():
        if name in body:
            out[name] = " ".join(str(body.get(name) or "").split())
        if len(out.get(name, "")) > limit:
            raise ApiError(400, "{} : {} caractères au maximum (reçu {}).".format(label, limit, len(out[name])))
    missing = [CL.CUSTOMER_FIELDS[k][0] for k in ("name", "cc_dfmea", "sc_dfmea", "cc_symbol", "sc_symbol") if not out.get(k)]
    if missing:
        raise ApiError(400, "{} : obligatoire. Correctif : écrivez le symbole du client tel que ses CSR le donnent (ex. CC, SC).".format(
            ", ".join(missing)))
    return out


def _save_customer(conn, pid, user_id, code, fields):
    now = db.utc_now()
    cols = list(CL.CUSTOMER_FIELDS)
    conn.execute("INSERT INTO diamond_class_customers (project_id, code, {}, updated_by, updated_at) VALUES (?, ?, {}, ?, ?) "
                 "ON CONFLICT(project_id, code) DO UPDATE SET {}, updated_by = excluded.updated_by, updated_at = excluded.updated_at".format(
                     ", ".join(cols), ", ".join("?" * len(cols)), ", ".join("{0} = excluded.{0}".format(c) for c in cols)),
                 [pid, code] + [fields[c] for c in cols] + [user_id, now])


def api_customer_create(ctx):
    """A customer of the Space with its own symbols, written from its CSR."""
    pid = F.access(ctx, "editor")
    items = CL.customers(ctx.conn, pid)
    if len(items) >= CL.MAX_CUSTOMERS:
        raise ApiError(409, "{} clients au plus par Space. Correctif : modifiez un client existant.".format(CL.MAX_CUSTOMERS))
    fields = _customer_fields(ctx.body, {k: "" for k in CL.CUSTOMER_FIELDS})
    stem = re.sub(r"[^a-z0-9]+", "-", fields["name"].lower()).strip("-")[:24] or "client"
    code, n = stem, 1
    while code in {c["code"] for c in items}:
        n += 1
        code = "{}-{}".format(stem, n)
    _save_customer(ctx.conn, pid, ctx.user["id"], code, fields)
    _log(ctx, "diamond_class_customer_create", "diamond_class_customers", pid, dict(fields, code=code))
    return dict(settings_payload(ctx.conn, pid), created=code)


def _find(ctx, pid):
    code = str(ctx.params.get("code") or "")
    found = next((c for c in CL.customers(ctx.conn, pid) if c["code"] == code), None)
    if found is None:
        raise ApiError(404, "Client « {} » introuvable dans le dictionnaire du Space. Correctif : rechargez la page.".format(code))
    return found


def api_customer_update(ctx):
    pid = F.access(ctx, "editor")
    found = _find(ctx, pid)
    fields = _customer_fields(ctx.body, {k: found[k] for k in CL.CUSTOMER_FIELDS})
    _save_customer(ctx.conn, pid, ctx.user["id"], found["code"], fields)
    _log(ctx, "diamond_class_customer_update", "diamond_class_customers", pid, dict(fields, code=found["code"]))
    return settings_payload(ctx.conn, pid)


def api_customer_delete(ctx):
    """A preset goes back to its start values; a customer added by the team is removed (never the customer in use)."""
    pid = F.access(ctx, "editor")
    found = _find(ctx, pid)
    if not found["preset"] and CL.rules(ctx.conn, pid)["customer"] == found["code"]:
        raise ApiError(409, "« {} » est le client du Space. Correctif : choisissez d'abord un autre client.".format(found["name"]))
    ctx.conn.execute("DELETE FROM diamond_class_customers WHERE project_id = ? AND code = ?", (pid, found["code"]))
    _log(ctx, "diamond_class_customer_reset" if found["preset"] else "diamond_class_customer_delete", "diamond_class_customers", pid,
         {"code": found["code"], "name": found["name"]})
    return settings_payload(ctx.conn, pid)

