"""Goldmine CSV (D-A-034): round-trip requirements through Excel, and load a
client specification in one pass.

Import rules (dynamic feedback, D-A-031):
- Only `statement` plus one of `key` / `external_id` are required; any
  other column may be absent -- an absent column is left untouched.
- Headers are matched loosely, so a client sheet with "ID", "Énoncé",
  "Catégorie", "Criticité", "Méthode"... is understood as is.
- `key` filled -> update that requirement. `key` empty but `external_id`
  already known in the project -> update it (a revised client spec
  re-imported does not duplicate anything). Otherwise -> create.
- Values accept the French labels shown on screen or the stored codes.
- `status` follows the requirement workflow (one transition at a time) and
  the verification guard (D-A-033), exactly like the ticket page.
- Every refused line lists all its problems with the fix; nothing is
  written for it.
- D-B-069: `mode: "preview"` runs the whole import and rolls it back, and
  lists every stored value the file would overwrite; `mode: "apply"` takes
  `keep` ({excel line: [fields]}) -- values the user chose to keep -- and
  `confirm_overwrites`, the number of overwrites he accepted (refused with
  409 if the base changed since the preview). No mode = apply everything
  (scripts, tests, the development catalogue).
- Export: `numbers=1-40,52` limits the file to the requirements shown on
  screen (the filtered subset).
"""
import unicodedata

from core import db
from core.errors import ApiError
from core.files import RawFile

from . import common as c
from . import csv_io, csv_rows, goldmine, goldmine_need, summary

EXPORT_FIELDS = ["key", "external_id", "kind", "stakeholder", "derived_from", "title", "statement", "status", "source", "source_doc",
                 "category", "lifecycle", "criticality", "verification_method", "acceptance_criteria",
                 "allocation", "verification_ref", "test_ref", "test_source", "functions", "need_status",
                 "revision", "received_at", "rationale",
                 "client_summary", "implemented_by", "updated_at", "last_change"]
READ_ONLY = {"implemented_by", "last_change", "test_source"}


def _norm(text):
    text = unicodedata.normalize("NFKD", (text or "").strip().casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch)).replace("_", " ").replace("-", " ")


HEADER_ALIASES = {_norm(alias): field for field, aliases in {
    "key": ["key", "cle", "ticket"],
    "external_id": ["external id", "id", "id externe", "identifiant", "req id", "requirement id", "ref", "reference"],
    "title": ["title", "titre", "nom", "resume"],
    "statement": ["statement", "enonce", "exigence", "requirement", "texte", "description", "text", "shall"],
    "status": ["status", "statut", "etat"],
    "source": ["source", "origine"],
    "source_doc": ["source doc", "document", "document source", "source document", "spec", "section"],
    "category": ["category", "categorie", "type exigence"],
    "kind": ["kind", "nature", "exigence ou besoin"],
    "stakeholder": ["stakeholder", "partie prenante", "parties prenantes"],
    "derived_from": ["derived from", "derivee de", "derive de", "besoin", "besoins", "besoin d'origine"],
    "lifecycle": ["lifecycle", "phase", "phase du cycle de vie", "cycle de vie", "dfx"],
    "last_change": ["last change", "derniere modification", "modifie par"],
    "criticality": ["criticality", "criticite", "criticité"],
    "verification_method": ["verification method", "methode", "methode de verification", "iadt", "verification"],
    "acceptance_criteria": ["acceptance criteria", "critere", "critere d'acceptation", "criteres d'acceptation"],
    "allocation": ["allocation", "sous systeme", "subsystem"],
    "verification_ref": ["verification ref", "ref verification", "reference de verification", "test", "preuve"],
    "test_ref": ["test ref", "test procedure", "test procedures", "procedure d'essai", "procedures d'essai", "essai",
                 "essais", "tests", "testing"],
    "functions": ["functions", "fonctions", "fonction", "product functions", "fonctions du produit"],
    "test_source": ["test source", "source de l'essai", "source essai", "source du test"],
    "revision": ["revision", "rev", "indice"],
    "received_at": ["received at", "recue le", "date de reception", "date"],
    "rationale": ["rationale", "justification", "raison"],
    "client_summary": ["client summary", "synthese client", "synthese", "commentaire principal",
                       "reponse client", "summary"],
    "implemented_by": ["implemented by", "implementee par"],
    "updated_at": ["updated at", "modifie le"],
}.items() for alias in aliases}
HEADER_ALIASES.update({_norm(a): f for f, aliases in goldmine_need.CSV_ALIASES.items() for a in aliases})  # D-B-086

LABEL_TO_CODE = {
    "source": {_norm(v): k for k, v in goldmine.SOURCES.items()},
    "category": dict({_norm(v): k for k, v in goldmine.CATEGORIES.items()},
                     **{_norm(a): "regulatory" for a in ("Réglementaire", "Norme", "Standard", "Norme/Standard")}),
    "lifecycle": {_norm(v): k for k, v in goldmine.LIFECYCLE.items()},
    "kind": dict({_norm(v): k for k, v in goldmine.KINDS.items()}, **{"requirement": "requirement", "need": "need"}),
    "stakeholder": {_norm(v): k for k, v in goldmine.STAKEHOLDERS.items()},
}
LABEL_TO_CODE["source"].update({_norm("Norme"): "standard", _norm("Standard"): "standard"})
for _field, _mapping in goldmine_need.LABEL_TO_CODE.items():  # D-B-086: labels or codes
    LABEL_TO_CODE[_field] = dict({_norm(k): v for k, v in _mapping.items()}, **{_norm(v): v for v in _mapping.values()})
for _field, _aliases in goldmine.LEGACY_LABELS.items():  # D-B-085: files with the former French labels still import
    for _label, _code in _aliases.items():
        LABEL_TO_CODE[_field].setdefault(_norm(_label), _code)
for _field, _mapping in (("source", goldmine.SOURCES), ("category", goldmine.CATEGORIES), ("lifecycle", goldmine.LIFECYCLE),
                         ("stakeholder", goldmine.STAKEHOLDERS)):
    for _code in _mapping:  # the stored codes are accepted too
        LABEL_TO_CODE[_field].setdefault(_norm(_code), _code)


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
def _parse_numbers(raw):
    """'1-4,7' -> {1, 2, 3, 4, 7}; None when no selection was given."""
    raw = str(raw or "").strip()
    if not raw:
        return None
    numbers = set()
    for part in raw.split(","):
        part = part.strip()
        try:
            low, _, high = part.partition("-")
            low, high = int(low), int(high or low)
        except ValueError:
            raise ApiError(400, "Sélection « {} » illisible. Correctif : relancez l'export depuis l'écran "
                                "Goldmine (numéros ou plages séparés par des virgules, ex. 1-40,52).".format(part[:40]))
        if low < 1 or high < low or high - low > 100000:
            raise ApiError(400, "Plage « {} » invalide. Correctif : relancez l'export depuis l'écran "
                                "Goldmine.".format(part[:40]))
        numbers.update(range(low, high + 1))
    return numbers


def api_export(ctx):
    project_id, _ = c.access(ctx)
    listing = goldmine.api_list(ctx)
    if not listing["enabled"]:
        raise ApiError(409, "Goldmine n'est pas activé sur ce projet. Correctif : un administrateur "
                            "clique sur « Activer Goldmine » dans l'onglet Goldmine.")
    selection = _parse_numbers(ctx.query.get("numbers"))
    rows = []
    for r in listing["requirements"]:
        if selection is not None and r["number"] not in selection:
            continue
        row = {f: r.get(f, "") for f in EXPORT_FIELDS}
        row["source"] = goldmine.SOURCES.get(r["source"], r["source"])
        row["category"] = goldmine.CATEGORIES.get(r["category"], r["category"])
        row["lifecycle"] = goldmine.LIFECYCLE.get(r["lifecycle"], r["lifecycle"])
        row["kind"] = goldmine.KINDS.get(r["kind"], r["kind"])
        row["stakeholder"] = goldmine.STAKEHOLDERS.get(r["stakeholder"], r["stakeholder"])
        row["need_status"] = goldmine_need.NEED_STATUS.get(r["need_status"], r["need_status"])
        row["last_change"] = (r.get("last_change") or {}).get("stamp", "")
        row["status"] = r["status_name"]
        row["implemented_by"] = ";".join(r["implemented_by"])
        rows.append(row)
    key = c.project_key(ctx.conn, project_id)
    c.log(ctx, "goldmine_export", "project", project_id, {"rows": len(rows), "selection": selection is not None})
    name = ("{}_exigences_selection-{}.csv".format(key, len(rows)) if selection is not None
            else "{}_exigences.csv".format(key))
    return RawFile.csv(csv_io._write_csv(EXPORT_FIELDS, rows), name)


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------
def _map_headers(rows):
    """Rename loose headers to field names; return (rows, unknown headers)."""
    if not rows:
        return rows, []
    mapping, unknown = {}, []
    for header in rows[0].keys():
        if header is None:
            continue
        field = HEADER_ALIASES.get(_norm(header))
        if field and field not in mapping.values():
            mapping[header] = field
        else:
            unknown.append(header)
    return [{mapping[h]: v for h, v in row.items() if h in mapping} for row in rows], unknown


def _find(conn, project_id, prefix, row):
    key = csv_rows._cell(row, "key")
    if key:
        return csv_rows._existing(conn, project_id, prefix, key, row), "clé"
    ext = csv_rows._cell(row, "external_id")
    if not ext:
        raise csv_rows.RowError("Ni clé ni ID externe.",
                                "Remplissez « external_id » (ex. SYS-045) pour un nouveau requirement, "
                                "ou « key » (ex. {}-4) pour en modifier une.".format(prefix))
    matches = conn.execute(
        "SELECT i.* FROM agile_issues i JOIN agile_requirements r ON r.issue_id = i.id "
        "WHERE i.project_id = ? AND r.external_id = ? COLLATE NOCASE", (project_id, ext)).fetchall()
    if len(matches) > 1:
        raise csv_rows.RowError("ID externe « {} » porté par {} requirements.".format(ext, len(matches)),
                                "Indiquez la clé exacte dans « key », ou corrigez le doublon dans Goldmine.")
    return (matches[0], "ID externe") if matches else (None, "")


METHOD_WORDS = {"i": "I", "inspection": "I", "a": "A", "analyse": "A", "analysis": "A",
                "d": "D", "demonstration": "D", "t": "T", "test": "T", "essai": "T", "essais": "T"}


def _methods_to_codes(value):
    """'Test, Analyse' / 'D + T' / 'TA' -> 'AT'. Unknown words are kept as
    typed so goldmine._clean reports them with the accepted values."""
    import re
    parts = [p for p in re.split(r"\s*(?:,|;|\+|/|\bet\b|\band\b)\s*", _norm(value)) if p]
    codes = [METHOD_WORDS.get(p) for p in parts]
    if parts and all(codes):
        return "".join(ch for ch in "IADT" if ch in codes)
    return value  # plain letters ("TA") or something to report


def _field_values(row, current):
    """Convert labels to codes and validate through goldmine._clean."""
    body, problems = {}, []
    for field in goldmine.FIELDS:
        if field not in row:
            continue
        value = (row.get(field) or "").strip()
        if field in LABEL_TO_CODE and value:
            value = LABEL_TO_CODE[field].get(_norm(value), value)
        if field == "verification_method" and value:
            value = _methods_to_codes(value)
        if field == "received_at" and value:
            try:
                value = csv_rows._due_date({"due_date": value})
            except csv_rows.RowError as exc:
                problems.extend((m.replace("Date", "Date de réception", 1), f) for m, f in exc.problems)
                continue
        body[field] = value
    cleaned = {}
    for field, value in body.items():
        try:
            one = {field: value}
            if field in goldmine_need.FIELDS and "kind" in body:  # D-B-086: the maturity depends on the kind of the line
                one["kind"] = LABEL_TO_CODE["kind"].get(_norm(body["kind"]), body["kind"])
            cleaned.update({k: v for k, v in goldmine._clean(one, current).items() if k == field})
        except ApiError as exc:
            message, fix = exc.message, "Corrigez la colonne « {} ».".format(field)
            for marker in (" Correctif : ", " Valeurs acceptées", " Utilisez "):
                if marker in message:
                    message, rest = message.split(marker, 1)
                    fix = (marker.strip(" :") + " " + rest).replace("Correctif ", "", 1).strip()
                    break
            problems.append((message.strip(), fix))
    return cleaned, problems


def _validate(ctx, project_id, prefix, row, role, rtype):
    conn = ctx.conn
    existing, matched_by = _find(conn, project_id, prefix, row)
    current = goldmine.fields_of(conn, existing["id"]) if existing else None
    if existing:
        itype = conn.execute("SELECT * FROM agile_issue_types WHERE id = ?", (existing["type_id"],)).fetchone()
        if not itype["is_requirement"]:
            raise csv_rows.RowError("{}-{} n'est pas un requirement.".format(prefix, existing["number"]),
                                    "Ce fichier ne modifie que des requirements : importez cette ligne par "
                                    "l'onglet Tickets, ou videz la clé.")
    else:
        itype = rtype
    fields, problems = _field_values(row, current)
    statement = fields.get("statement", current["statement"] if current else "")
    status = transition = None
    try:
        status, transition = csv_rows._status(conn, itype, row, existing, role)
    except csv_rows.RowError as exc:
        problems.extend(exc.problems)
    if status is not None and transition is not None:
        merged = dict(current or goldmine.fields_of(conn, -1), **fields)
        if status["name"] == goldmine.VERIFIED and not (merged["verification_method"] and merged["verification_ref"]):
            problems.append(("Passage à « Verified » sans méthode ou sans réf. de vérification.",
                             "Remplissez « verification_method » (I/A/D/T) et « verification_ref » "
                             "sur la même ligne, ou laissez le status actuel."))
    if "functions" in fields:  # D-B-082: central list of the product functions
        try:
            goldmine.function_guard(conn, fields, (current or {}).get("functions", ""))
        except ApiError as exc:
            problems.append((exc.message.split(" Correctif : ")[0], "Colonne « functions » : codes F-XX de la liste "
                             "centrale (Testing → Listes), séparés par des virgules."))
    refusal = None
    if existing is None or "test_ref" in fields or "kind" in fields:
        from modules.testing import catalog as testing
        merged = dict(current or goldmine.fields_of(conn, -1), **fields)
        refusal = testing.check_refs(conn, merged["kind"], merged["test_ref"], (current or {}).get("test_ref", ""), project_id)
    if refusal:
        problems.append((refusal[0], refusal[1] + " Colonne « test_ref » (Test Procedure)."))
    warning = ""
    if current and "statement" in fields and fields["statement"] != current["statement"] \
            and fields.get("revision", current["revision"]) == current["revision"]:
        warning = ("Énoncé modifié sans changement de révision (reste « {} »). Si la spec client a "
                   "changé, mettez aussi à jour « revision ».".format(current["revision"]))
    summary_value = summary.csv_cell(row)
    if summary_value is not None and len(summary_value) > summary.MAX_LENGTH:
        problems.append(summary.too_long_message(len(summary_value)))
    if problems:
        raise csv_rows.RowError(*problems[0], problems=problems)
    title = csv_rows._cell(row, "title") or (existing["title"] if existing else statement[:120])
    return existing, matched_by, fields, status, transition, title, warning


DISPLAY = {"source": goldmine.SOURCES, "category": goldmine.CATEGORIES, "lifecycle": goldmine.LIFECYCLE,
           "kind": goldmine.KINDS, "stakeholder": goldmine.STAKEHOLDERS,
           "need_status": goldmine_need.NEED_STATUS}
EXTRA_LABELS = {"title": "titre", "status": "status", "client_summary": "synthèse client"}


def _shown(field, value):
    return DISPLAY.get(field, {}).get(value, value) if value else ""


def _differences(conn, existing, fields, title, status, row):
    """Stored values of an existing requirement that this line would replace
    (D-B-069): [{field, label, current, new}] -- empty when nothing changes."""
    if existing is None:
        return []
    current = goldmine.fields_of(conn, existing["id"])
    out = [{"field": f, "label": goldmine.FIELD_LABELS[f], "current": _shown(f, current.get(f)),
            "new": _shown(f, v)} for f, v in fields.items() if (current.get(f) or "") != (v or "")]
    if title != existing["title"]:
        out.insert(0, {"field": "title", "label": EXTRA_LABELS["title"], "current": existing["title"], "new": title})
    if status is not None and status["id"] != existing["status_id"]:
        old = conn.execute("SELECT name FROM agile_statuses WHERE id = ?", (existing["status_id"],)).fetchone()["name"]
        out.append({"field": "status", "label": EXTRA_LABELS["status"], "current": old, "new": status["name"]})
    summary_value = summary.csv_cell(row)
    if summary_value is not None and summary_value != (existing["client_summary"] or ""):
        out.append({"field": "client_summary", "label": EXTRA_LABELS["client_summary"],
                    "current": existing["client_summary"] or "", "new": summary_value})
    return out


def _apply(ctx, project_id, prefix, row, role, rtype):
    conn = ctx.conn
    existing, matched_by, fields, status, transition, title, warning = _validate(
        ctx, project_id, prefix, row, role, rtype)
    now = db.utc_now()
    differences = _differences(conn, existing, fields, title, status, row)
    if existing is not None and not differences:  # identical line: nothing is written (as D-B-008)
        return {"row": "{}-{}".format(prefix, existing["number"]), "status": "inchangée", "reason": "",
                "fix": "", "warning": "", "differences": []}
    if existing is not None and "test_ref" not in fields:  # D-B-079: an old requirement saved without its test
        from modules.testing import catalog as testing
        stored = goldmine.fields_of(conn, existing["id"])
        refusal = testing.check_refs(conn, stored["kind"], stored["test_ref"], stored["test_ref"], project_id)
        if refusal:
            raise csv_rows.RowError(refusal[0], refusal[1] + " Ajoutez la colonne « test_ref » (Test Procedure).")
    if existing is not None and not c.can_edit(ctx, role, existing):
        raise csv_rows.RowError(
            "{} est attribué à quelqu'un d'autre : seul son responsable ou un administrateur peut le "
            "modifier.".format("{}-{}".format(prefix, existing["number"])),
            "Retirez cette ligne du fichier, ou demandez au responsable du ticket de l'importer.")
    if existing is None:
        number = conn.execute("UPDATE projects SET next_ticket_number = next_ticket_number + 1 "
                              "WHERE id = ? RETURNING next_ticket_number - 1 AS n", (project_id,)).fetchone()["n"]
        rank = conn.execute("SELECT COALESCE(MAX(rank), 0) + 1 FROM agile_issues WHERE project_id = ?",
                            (project_id,)).fetchone()[0]
        issue_id = conn.execute(
            "INSERT INTO agile_issues (project_id, number, type_id, status_id, title, reporter_id, assignee_id, "
            "rank, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, number, rtype["id"], status["id"], title, ctx.user["id"],
             None if role == "admin" else ctx.user["id"], rank, now, now)).lastrowid  # D-B-017
        c.add_history(ctx, issue_id, "created", None, title + " (import Goldmine)")
        key, result, old_status = "{}-{}".format(prefix, number), "créée", "(création)"
    else:
        issue_id, key = existing["id"], "{}-{}".format(prefix, existing["number"])
        old_status = conn.execute("SELECT name FROM agile_statuses WHERE id = ?",
                                  (existing["status_id"],)).fetchone()["name"]
        conn.execute("UPDATE agile_issues SET title = ?, status_id = ?, updated_at = ? WHERE id = ?",
                     (title, status["id"], now, issue_id))
        result = "mise à jour" + (" (par ID externe)" if matched_by == "ID externe" else "")
    current = goldmine.fields_of(conn, issue_id)
    merged = dict(current, **fields)
    conn.execute("INSERT INTO agile_requirements (issue_id, {cols}) VALUES (?, {marks}) "
                 "ON CONFLICT(issue_id) DO UPDATE SET {sets}".format(
                     cols=", ".join(goldmine.FIELDS), marks=", ".join("?" for _ in goldmine.FIELDS),
                     sets=", ".join("{0} = excluded.{0}".format(f) for f in goldmine.FIELDS)),
                 (issue_id,) + tuple(merged[f] for f in goldmine.FIELDS))
    for field in fields:
        if existing and current.get(field) != merged[field]:
            c.add_history(ctx, issue_id, "req:" + goldmine.FIELD_LABELS[field], None, "(import CSV)")
    if transition is not None:
        conn.execute("UPDATE agile_issues SET resolved_at = ? WHERE id = ?",
                     (now if status["category"] == "done" else None, issue_id))
        c.add_history(ctx, issue_id, "status", old_status,
                      "{} (transition « {} », import CSV)".format(status["name"], transition["name"]))
    summary_value = summary.csv_cell(row)
    if summary_value is not None:
        fresh = conn.execute("SELECT * FROM agile_issues WHERE id = ?", (issue_id,)).fetchone()
        summary.write(ctx, fresh, summary_value, "import Goldmine")
    return {"row": key, "status": result, "reason": "", "fix": "", "warning": warning, "differences": differences}


def _keep_map(ctx):
    """{excel line: set of fields to keep} sent back after the preview."""
    keep = ctx.body.get("keep") or {}
    if not isinstance(keep, dict):
        raise ApiError(400, "« keep » doit associer un numéro de ligne à une liste de champs.")
    allowed = set(goldmine.FIELDS) | set(EXTRA_LABELS)
    out = {}
    for line, fields in keep.items():
        if not isinstance(fields, list) or not all(isinstance(f, str) and f in allowed for f in fields):
            raise ApiError(400, "Champs à conserver illisibles pour la ligne {}. Correctif : relancez l'import "
                                "depuis l'écran Goldmine.".format(str(line)[:10]))
        out[str(line)] = set(fields)
    return out


def api_import(ctx):
    project_id, role = c.access(ctx, "editor")
    mode = ctx.body.get("mode") or "direct"
    if mode not in ("direct", "preview", "apply"):
        raise ApiError(400, "Mode d'import « {} » inconnu (preview ou apply).".format(str(mode)[:20]))
    keep = _keep_map(ctx) if mode == "apply" else {}
    rtype = goldmine.requirement_type(ctx.conn, project_id)
    if rtype is None:
        raise ApiError(409, "Goldmine n'est pas activé sur ce projet. Correctif : un administrateur "
                            "clique sur « Activer Goldmine » dans l'onglet Goldmine.")
    prefix = c.project_key(ctx.conn, project_id)
    raw = csv_io._read_csv_body(ctx, [])
    rows, unknown = _map_headers(raw)
    present = set(rows[0].keys()) if rows else set()
    if "statement" not in present or not ({"key", "external_id"} & present):
        raise ApiError(400, "Colonnes indispensables introuvables : il faut « statement » (ou "
                            "« Énoncé ») et « external_id » (ou « ID ») ou « key ». En-têtes non "
                            "reconnus : {}. Correctif : renommez ces colonnes, ou partez d'un export "
                            "Goldmine.".format(", ".join(unknown) or "(aucun)"))
    report, kept = [], 0
    ctx.conn.execute("SAVEPOINT goldmine_import")
    try:
        for index, row in enumerate(rows):
            if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
                continue
            line = index + 2
            label = csv_rows._cell(row, "key") or csv_rows._cell(row, "external_id") or "(ligne)"
            for field in keep.get(str(line), ()):  # keep the stored value: as if the column were absent
                if field in row:
                    row.pop(field)
                    kept += 1
            try:
                entry = _apply(ctx, project_id, prefix, row, role, rtype)
            except csv_rows.RowError as exc:
                entry = {"row": label, "status": "refusée", "reason": exc.message, "fix": exc.fix, "warning": "",
                         "problems": [{"message": m, "fix": f} for m, f in exc.problems], "differences": []}
            if mode == "preview" and entry["status"] == "créée":
                entry["row"] = "nouvelle · " + label
            entry["line"] = line
            report.append(entry)
        overwrites = sum(len(r["differences"]) for r in report)
        if mode == "apply" and ctx.body.get("confirm_overwrites") is not None \
                and int(ctx.body.get("confirm_overwrites")) != overwrites:
            raise ApiError(409, "La base a changé depuis l'aperçu : {} champ(s) seraient écrasés au lieu des {} "
                                "confirmés. Rien n'a été écrit. Correctif : relancez l'import pour revoir les "
                                "différences.".format(overwrites, ctx.body.get("confirm_overwrites")))
    except Exception:
        ctx.conn.execute("ROLLBACK TO goldmine_import")
        ctx.conn.execute("RELEASE goldmine_import")
        raise
    if mode == "preview":
        ctx.conn.execute("ROLLBACK TO goldmine_import")
    ctx.conn.execute("RELEASE goldmine_import")
    note = ("Colonne(s) ignorée(s), non reconnue(s) : {}.".format(", ".join(unknown)) if unknown else "")
    result = {"report": report, "note": note, "mode": mode, "overwrites": overwrites,
              "overwrite_rows": sum(1 for r in report if r["differences"]), "kept": kept}
    if mode != "preview":
        c.log(ctx, "goldmine_import", "project", project_id,
              {"rows": len(report), "rejected": sum(1 for r in report if r["status"] == "refusée"),
               "overwrites": overwrites, "kept": kept})
    return result
