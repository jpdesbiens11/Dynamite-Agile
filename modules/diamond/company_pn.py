"""The company part numbers in Diamond (0.60.103, D-O-112, increment 3 of D-O-109).

The BOM of the ERP comes in as CSV (PN, revision, designation, supplier, material), into diamond_company_parts -- the PN
is the key: a known PN is updated, a new one added, nothing is deleted. Each Diamond part covers one or more company PNs
(diamond_part_pns, many to many: one Diamond part may be a bracket and its magnet), set by hand or from the answer of an
AI assistant (pn_ai.py); a part no PN fits is marked « à créer dans l'ERP » (diamond_parts.erp_todo). The summary of the
special characteristics and the card of a C-n read the PNs from these links.
POST …/pn/bom {file, mode: preview | apply}: preview lists every new, changed and unchanged PN and every problem with
its Excel line; apply writes, in one transaction, journalled.
"""
import csv
import io
import re

from core import audit, db, validate
from core.errors import ApiError

from . import functions as F

MAX_BYTES, MAX_PNS = 600_000, 3000
COLUMNS = {"pn": ("pn", "part number", "numéro", "numero", "no", "# pièce", "# piece", "item", "article"),
           "rev": ("rev", "rév", "révision", "revision", "rev."),
           "designation": ("designation", "désignation", "description", "libellé", "libelle", "name", "nom"),
           "supplier": ("supplier", "fournisseur", "vendor", "manufacturer", "fabricant"),
           "material": ("material", "matière", "matiere", "matériau", "materiau")}
LIMITS = {"pn": 40, "rev": 12, "designation": 160, "supplier": 80, "material": 80}


def label(r):
    """« RVR-3140-02 C »: the PN and its revision."""
    return (r["pn"] + (" " + r["rev"] if r.get("rev") else "")).strip()


def bom(conn, pid):
    return [dict(r) for r in conn.execute("SELECT * FROM diamond_company_parts WHERE project_id = ? ORDER BY pn", (pid,))]


def links(conn, pid):
    """{part_id: [{id, pn, rev, label, designation, source, confidence, reason}]}"""
    out = {}
    for r in conn.execute("SELECT l.part_id, l.source, l.confidence, l.reason, c.* FROM diamond_part_pns l "
                          "JOIN diamond_company_parts c ON c.id = l.company_part_id WHERE l.project_id = ? ORDER BY c.pn", (pid,)):
        d = dict(r)
        out.setdefault(d["part_id"], []).append({"id": d["id"], "pn": d["pn"], "rev": d["rev"], "label": label(d), "designation": d["designation"],
                                                 "source": d["source"], "confidence": d["confidence"], "reason": d["reason"]})
    return out


def payload(conn, pid):
    by_part = links(conn, pid)
    parts = [dict(r) for r in conn.execute("SELECT id, number, name, kind, notes, erp_todo FROM diamond_parts WHERE project_id = ? ORDER BY number", (pid,))]
    for p in parts:
        p["code"], p["pns"] = "P-{}".format(p["number"]), by_part.get(p["id"], [])
    items = bom(conn, pid)
    used = {x["id"] for v in by_part.values() for x in v}
    for b in items:
        b["label"], b["used"] = label(b), b["id"] in used
    return {"parts": parts, "bom": items, "counts": {"parts": len(parts), "linked": sum(1 for p in parts if p["pns"]),
                                                      "todo": sum(1 for p in parts if p["erp_todo"]), "bom": len(items)}}


def _rows(text):
    text = str(text or "").lstrip("﻿").strip()
    fence = re.search(r"```(?:csv)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    sample = "\n".join(text.splitlines()[:20])
    delimiter = max(";,\t", key=sample.count) if any(c in sample for c in ";,\t") else ";"
    return [[c.strip() for c in row] for row in csv.reader(io.StringIO(text), delimiter=delimiter)]


def parse(text):
    """{rows: [{line, pn, rev, designation, supplier, material}], problems: [...]} -- nothing written."""
    if len(str(text or "").encode("utf-8")) > MAX_BYTES:
        raise ApiError(413, "Fichier trop gros ({} Ko au plus). Correctif : exportez seulement les pièces du produit.".format(MAX_BYTES // 1000))
    rows = _rows(text)
    if not rows:
        raise ApiError(400, "Fichier vide. Correctif : un CSV avec au moins la colonne PN.")
    head = [h.lower().strip(" :") for h in rows[0]]
    index = {}
    for key, names in COLUMNS.items():
        for i, h in enumerate(head):
            if h in names and key not in index:
                index[key] = i
    if "pn" not in index:
        raise ApiError(400, "Colonne PN introuvable dans « {} ». Correctif : une première ligne d'en-têtes avec PN (ou Part number), "
                            "Révision, Désignation, Fournisseur, Matière.".format(" ; ".join(rows[0])[:200]))
    out, problems, seen = [], [], set()
    for n, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue
        item = {k: (row[i] if i < len(row) else "").strip() for k, i in index.items()}
        bad = [k for k, v in item.items() if len(v) > LIMITS[k]]
        if not item.get("pn"):
            problems.append("Ligne {} : PN vide — ligne ignorée.".format(n))
            continue
        if bad:
            problems.append("Ligne {} : {} trop long ({} caractères au plus).".format(n, ", ".join(bad), ", ".join(str(LIMITS[k]) for k in bad)))
            continue
        if item["pn"].upper() in seen:
            problems.append("Ligne {} : PN {} déjà plus haut dans le fichier — ligne ignorée.".format(n, item["pn"]))
            continue
        seen.add(item["pn"].upper())
        out.append(dict({k: item.get(k, "") for k in LIMITS}, line=n))
    if len(out) > MAX_PNS:
        raise ApiError(413, "{} PN au plus par Space. Correctif : seulement la nomenclature du produit.".format(MAX_PNS))
    return {"rows": out, "problems": problems}


def api_get(ctx):
    return payload(ctx.conn, F.access(ctx))


def api_bom(ctx):
    pid = F.access(ctx, "editor")
    mode = ctx.body.get("mode", "preview")
    parsed = parse(ctx.body.get("file"))
    current = {r["pn"].upper(): r for r in bom(ctx.conn, pid)}
    plan = []
    for r in parsed["rows"]:
        old = current.get(r["pn"].upper())
        changes = {k: r[k] for k in ("rev", "designation", "supplier", "material") if old and r[k] != old[k]} if old else None
        plan.append(dict(r, status="new" if old is None else "changed" if changes else "same", changes=changes or {}))
    counts = {k: sum(1 for p in plan if p["status"] == k) for k in ("new", "changed", "same")}
    if mode != "apply":
        return {"mode": "preview", "plan": plan, "problems": parsed["problems"], "counts": counts}
    now, uid = db.utc_now(), ctx.user["id"]
    for r in plan:
        if r["status"] == "new":
            ctx.conn.execute("INSERT INTO diamond_company_parts (project_id, pn, rev, designation, supplier, material, created_by, created_at, "
                             "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (pid, r["pn"], r["rev"], r["designation"], r["supplier"], r["material"], uid, now, uid, now))
        elif r["status"] == "changed":
            ctx.conn.execute("UPDATE diamond_company_parts SET {}, updated_by = ?, updated_at = ? WHERE id = ?".format(
                ", ".join(k + " = ?" for k in r["changes"])), list(r["changes"].values()) + [uid, now, current[r["pn"].upper()]["id"]])
    audit.log_action(ctx.conn, uid, "diamond_bom_import", "project", pid, counts, ctx.ip)
    return dict(payload(ctx.conn, pid), mode="apply", counts_import=counts, problems=parsed["problems"])


def set_part(conn, user_id, pid, part_id, company_ids, source="manual", detail=None):
    """The PNs a Diamond part covers, replaced by `company_ids` (a list); detail {company_id: (confidence, reason)}."""
    now = db.utc_now()
    if company_ids:
        conn.execute("DELETE FROM diamond_part_pns WHERE part_id = ? AND company_part_id NOT IN ({})".format(",".join("?" * len(company_ids))),
                     [part_id] + list(company_ids))
    else:
        conn.execute("DELETE FROM diamond_part_pns WHERE part_id = ?", (part_id,))
    for cid in company_ids:
        conf, reason = (detail or {}).get(cid, (None, ""))
        conn.execute("INSERT INTO diamond_part_pns (project_id, part_id, company_part_id, source, confidence, reason, created_by, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(part_id, company_part_id) DO NOTHING",
                     (pid, part_id, cid, source, conf, reason, user_id, now))
    if company_ids:
        conn.execute("UPDATE diamond_parts SET erp_todo = 0 WHERE id = ?", (part_id,))


def api_part(ctx):
    """PUT {pn_ids: [...], erp_todo?: bool}: what one Diamond part covers, set by hand."""
    pid = F.access(ctx, "editor")
    part = ctx.conn.execute("SELECT * FROM diamond_parts WHERE id = ? AND project_id = ?", (validate.int_param(ctx.params, "oid"), pid)).fetchone()
    if part is None:
        raise ApiError(404, "Pièce introuvable dans ce Space. Correctif : rechargez la page.")
    ids = ctx.body.get("pn_ids")
    if ids is not None:
        known = {r["id"] for r in bom(ctx.conn, pid)}
        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            ids = [-1]
        if any(i not in known for i in ids):
            raise ApiError(400, "PN inconnu dans la nomenclature de ce Space. Correctif : importez d'abord le BOM de l'ERP.")
        set_part(ctx.conn, ctx.user["id"], pid, part["id"], ids)
    if "erp_todo" in ctx.body:
        ctx.conn.execute("UPDATE diamond_parts SET erp_todo = ? WHERE id = ?", (1 if ctx.body.get("erp_todo") else 0, part["id"]))
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_part_pns", "diamond_parts", part["id"],
                     {"pn_ids": ids, "erp_todo": ctx.body.get("erp_todo")}, ctx.ip)
    return payload(ctx.conn, pid)
