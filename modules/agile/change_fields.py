"""Goldmine change management: fields of PR / bugs / ECN and the list of
items an ECN changes (D-B-010).

Vocabulary follows usual configuration management practice:
a PR (problem report) or software bug records a non-conformance; an ECN
(engineering change notice) proposes, gets approved by the CCB, is
implemented and verified. An ECN is classified major/minor (form, fit,
function, certification or safety impact => major) and lists every part,
assembly, document or software item it changes, from which revision to
which, with the disposition of existing stock.
"""
from core import db
from core.errors import ApiError

from . import common as c

# D-B-085: technical vocabulary in English (the stored codes do not change)
SEVERITIES = {"critique": "Critical", "majeure": "Major", "mineure": "Minor"}
DETECTED_IN = {"conception": "Design", "fabrication": "Manufacturing", "inspection": "Receiving Inspection",
               "essai": "Test / Qualification", "service": "In Service", "fournisseur": "Supplier"}
CLASSES = {"majeur": "Major", "mineur": "Minor"}
REASONS = {"correctif": "Corrective (from PR / bug)", "securite": "Safety / Compliance",
           "client": "Customer Requirement", "amelioration": "Performance Improvement",
           "fabrication": "Manufacturability", "cout": "Cost Reduction", "obsolescence": "Obsolescence",
           "documentation": "Documentation Only"}
ITEM_TYPES = {"piece": "Part", "assemblage": "Assembly", "plan": "Drawing",
              "document": "Document / Procedure", "logiciel": "Software / Firmware", "outillage": "Tooling"}
DISPOSITIONS = {"na": "N/A", "utiliser": "Use As Is", "retoucher": "Rework",
                "rebuter": "Scrap", "retour": "Return to Supplier", "epuiser": "Use Up Stock"}

# field -> (label, kind, limit or choices)
FIELDS = {
    "severity": ("Severity", "choice", SEVERITIES),
    "detected_in": ("Detected In", "choice", DETECTED_IN),
    "item_ref": ("Affected Item (P/N / Rev.)", "text", 200),
    "found_version": ("Software Version Found", "text", 60),
    "containment": ("Containment Action", "text", 4000),
    "root_cause": ("Root Cause", "text", 4000),
    "change_class": ("Change Class", "choice", CLASSES),
    "reason": ("Change Reason", "choice", REASONS),
    "impact_fff": ("Form / Fit / Function Impact", "bool", None),
    "impact_certification": ("Certification Impact", "bool", None),
    "impact_safety": ("Safety Impact", "bool", None),
    "impact_notes": ("Impact Analysis (cost, schedule, mass, stock)", "text", 4000),
    "effectivity": ("Effectivity (S/N, lot or date)", "text", 200),
    "approvers": ("CCB Approvers", "text", 300),
    "decision_date": ("CCB Decision Date", "date", None),
    "verification_ref": ("Implementation Verification Ref.", "text", 200),
}
PROBLEM_FIELDS = ("severity", "detected_in", "item_ref", "found_version", "containment", "root_cause")
ECN_FIELDS = ("change_class", "reason", "impact_fff", "impact_certification", "impact_safety",
              "impact_notes", "effectivity", "approvers", "decision_date", "verification_ref")
LONG_TEXT = ("containment", "root_cause", "impact_notes")
MAX_ITEMS = 200


def labels():
    return {"severities": SEVERITIES, "detected_in": DETECTED_IN, "classes": CLASSES, "reasons": REASONS,
            "item_types": ITEM_TYPES, "dispositions": DISPOSITIONS,
            "fields": {k: v[0] for k, v in FIELDS.items()}}


def fields_of(conn, issue_id):
    row = conn.execute("SELECT * FROM agile_changes WHERE issue_id = ?", (issue_id,)).fetchone()
    out = {}
    for field, (_, kind, _) in FIELDS.items():
        value = row[field] if row is not None else None
        out[field] = bool(value) if kind == "bool" else (value if value is not None else ("" if kind != "date" else None))
    return out


def items_of(conn, issue_id):
    return db.rows(conn.execute("SELECT id, item_type, item_number, item_title, rev_from, rev_to, disposition "
                                "FROM agile_change_items WHERE issue_id = ? ORDER BY position, id",
                                (issue_id,)).fetchall())


def clean(body, allowed):
    """Validated subset of `body` for the fields `allowed` (ApiError names the fix)."""
    out = {}
    for field in allowed:
        if field not in body:
            continue
        label, kind, spec = FIELDS[field]
        value = body[field]
        if kind == "bool":
            if not isinstance(value, bool):
                raise ApiError(400, "Champ « {} » : oui ou non attendu.".format(label))
            out[field] = int(value)
            continue
        value = "" if value is None else value
        if not isinstance(value, str):
            raise ApiError(400, "Champ « {} » : texte attendu.".format(label))
        value = value.strip()
        if kind == "choice" and value and value not in spec:
            raise ApiError(400, "{} « {} » inconnue. Correctif : choisissez parmi {}.".format(
                label, value, ", ".join(spec.values())))
        if kind == "text" and len(value) > spec:
            raise ApiError(400, "Champ « {} » : {} caractères au maximum ({} reçus).".format(label, spec, len(value)))
        if kind == "date":
            if value and not c.is_real_date(value):
                raise ApiError(400, "{} « {} » invalide. Correctif : format aaaa-mm-jj.".format(label, value))
            value = value or None
        out[field] = value
    return out


def save_fields(ctx, issue_id, changes, note=None):
    """Upsert `changes` and write one history line per field."""
    conn = ctx.conn
    current = fields_of(conn, issue_id)
    changes = {k: v for k, v in changes.items() if (bool(v) if FIELDS[k][1] == "bool" else v) != current[k]}
    if not changes:
        return []
    merged = dict(current, **changes)
    cols = list(FIELDS)
    values = [int(merged[f]) if FIELDS[f][1] == "bool" else merged[f] for f in cols]
    conn.execute("INSERT INTO agile_changes (issue_id, {cols}) VALUES (?, {marks}) ON CONFLICT(issue_id) "
                 "DO UPDATE SET {sets}".format(cols=", ".join(cols), marks=", ".join("?" for _ in cols),
                                               sets=", ".join("{0} = excluded.{0}".format(f) for f in cols)),
                 [issue_id] + values)
    conn.execute("UPDATE agile_issues SET updated_at = ? WHERE id = ?", (db.utc_now(), issue_id))
    for field, value in changes.items():
        label, kind, spec = FIELDS[field]
        old = current[field]
        if kind == "choice":
            old, value = spec.get(old, old) or None, spec.get(value, value) or None
        elif kind == "bool":
            old, value = ("oui" if old else "non"), ("oui" if value else "non")
        elif field in LONG_TEXT:
            old, value = None, "(modifié)"
        c.add_history(ctx, issue_id, "chg:" + label, old or None,
                      (value or None) if not note else "{} ({})".format(value or "vide", note))
    return sorted(changes)


def clean_items(raw):
    if not isinstance(raw, list):
        raise ApiError(400, "Liste d'articles attendue.")
    if len(raw) > MAX_ITEMS:
        raise ApiError(400, "{} articles au maximum par ECN. Correctif : découpez en plusieurs ECN "
                            "(sous-changements) liés au même problème.".format(MAX_ITEMS))
    items = []
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ApiError(400, "Article {} invalide.".format(i))
        get = lambda k, n: str(item.get(k) or "").strip()[:n]  # noqa: E731
        entry = {"item_type": get("item_type", 20), "item_number": get("item_number", 60),
                 "item_title": get("item_title", 200), "rev_from": get("rev_from", 10),
                 "rev_to": get("rev_to", 10), "disposition": get("disposition", 20) or "na"}
        if not entry["item_number"]:
            raise ApiError(400, "Article {} : numéro manquant. Correctif : indiquez le numéro de pièce, "
                                "de plan ou de document (ex. DWG-46000-12345).".format(i))
        if entry["item_type"] not in ITEM_TYPES:
            raise ApiError(400, "Article {} : type « {} » inconnu. Correctif : {}.".format(
                i, entry["item_type"], ", ".join(ITEM_TYPES.values())))
        if entry["disposition"] not in DISPOSITIONS:
            raise ApiError(400, "Article {} : disposition « {} » inconnue. Correctif : {}.".format(
                i, entry["disposition"], ", ".join(DISPOSITIONS.values())))
        items.append(entry)
    return items


def save_items(ctx, issue_id, items):
    conn = ctx.conn
    before = items_of(conn, issue_id)
    key = lambda it: tuple(it[k] for k in ("item_type", "item_number", "item_title", "rev_from", "rev_to",  # noqa: E731
                                           "disposition"))
    if [key(it) for it in before] == [key(it) for it in items]:
        return False
    conn.execute("DELETE FROM agile_change_items WHERE issue_id = ?", (issue_id,))
    for pos, it in enumerate(items):
        conn.execute("INSERT INTO agile_change_items (issue_id, position, item_type, item_number, item_title, "
                     "rev_from, rev_to, disposition) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (issue_id, pos, it["item_type"], it["item_number"], it["item_title"], it["rev_from"],
                      it["rev_to"], it["disposition"]))
    conn.execute("UPDATE agile_issues SET updated_at = ? WHERE id = ?", (db.utc_now(), issue_id))
    c.add_history(ctx, issue_id, "chg:Articles touchés", "{} article(s)".format(len(before)),
                  ", ".join("{} {}→{}".format(it["item_number"], it["rev_from"] or "—", it["rev_to"] or "—")
                            for it in items)[:500] or "aucun")
    return True
