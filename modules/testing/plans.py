"""Test plans for an external test supplier (D-A-048).

From tests chosen in the Testing base (e.g. the electrical safety tests), a test plan is made for one supplier
of the « Test Location » list (e.g. an accredited lab) and exported in the Word template of the tool, customised for
that supplier. The automated part only takes what exists: the procedure page of each subject (Dynamite, TESTING
Space) and the records of the chosen tests. Everything else is left as « À COMPLÉTER » to be written by hand.

Life cycle: Draft -> Sent to Supplier -> Results Received -> Closed (or Cancelled). The supplier writes its report
from the plan and sends the results back: the PDF is attached (Results Received), and the plan cannot be closed
without it. Tests and supplier are changed in Draft only.
"""
import json
import re

from core import audit, db, permissions, uploads, validate
from core.errors import ApiError
from core.files import RawFile

from . import bundles, catalog, word_doc as d, lists

STATUSES = {"draft": "Draft", "sent": "Sent to Supplier", "results": "Results Received", "closed": "Closed",
            "cancelled": "Cancelled"}
MOVES = {("draft", "sent"), ("sent", "draft"), ("results", "closed"), ("draft", "cancelled"), ("sent", "cancelled"),
         ("closed", "results")}
TODO = "C55A11"  # orange « À COMPLÉTER » runs
MAX_TESTS = 80


def _pid(ctx, minimum="reader"):
    """The Space of the plans (D-B-097: ?space=<KEY>, TESTING when absent): its own Test Base, its own plans."""
    if catalog.project_id(ctx.conn) is None:
        raise ApiError(409, "La Test Base de référence n'existe pas encore (Space DEMO). Correctif : redémarrez le serveur.")
    from .tests_api import space
    return space(ctx, minimum)[0]


def _log(ctx, action, plan_id, details=None):
    audit.log_action(ctx.conn, ctx.user["id"], action, "testing_plan", plan_id, details, ctx.ip)


def _row(ctx, pid):
    code = str(ctx.params.get("code") or "").upper()
    row = ctx.conn.execute("SELECT * FROM testing_plans WHERE project_id = ? AND code = ?", (pid, code)).fetchone()
    if row is None:
        raise ApiError(404, "Plan de test « {} » introuvable.".format(code))
    return row


def _public(conn, row):
    p = dict(row)
    p["tests"] = json.loads(row["tests"] or "[]")
    p["status_label"] = STATUSES[row["status"]]
    p["location_label"] = lists.labels(conn, "location").get(row["location"], row["location"])
    p["moves"] = [{"to": b, "label": STATUSES[b]} for a, b in sorted(MOVES) if a == row["status"]]
    p["has_results"] = bool(row["results_id"])
    return p


def _tests(conn, pid, value):
    if not isinstance(value, list) or not value:
        raise ApiError(400, "Aucun test choisi. Correctif : sélectionnez des tests dans la base (filtres), puis « Créer un "
                            "plan de test avec la sélection ».")
    ids = list(dict.fromkeys(str(v).strip().upper() for v in value if str(v).strip()))
    if len(ids) > MAX_TESTS:
        raise ApiError(400, "{} tests : {} au maximum par plan. Correctif : découpez en plusieurs plans.".format(len(ids), MAX_TESTS))
    known = {r["test_id"] for r in conn.execute("SELECT test_id FROM testing_tests WHERE project_id = ?", (pid,))}
    unknown = [i for i in ids if i not in known]
    if unknown:
        raise ApiError(400, "Test(s) inconnu(s) : {}. Correctif : utilisez les ID de la base Testing.".format(", ".join(unknown[:10])))
    return ids


def _location(conn, code):
    code = str(code or "").strip().upper()
    if not code:
        raise ApiError(400, "Fournisseur de test obligatoire. Correctif : choisissez-le dans la liste Test Location.")
    active = {r["code"] for r in lists.entries(conn, "location", active_only=True)}
    if code not in active:
        raise ApiError(400, "Fournisseur « {} » absent de la liste Test Location. Correctif : choisissez-en un, ou demandez "
                            "à un Admin du Space TESTING de l'ajouter (Testing → Listes centrales).".format(code))
    return code


def api_list(ctx):
    pid = _pid(ctx)
    rows = ctx.conn.execute("SELECT p.*, u.display_name AS author FROM testing_plans p LEFT JOIN users u ON u.id = p.created_by "
                            "WHERE p.project_id = ? ORDER BY p.id DESC", (pid,)).fetchall()
    locations = [{"code": r["code"], "label": r["label"]} for r in lists.entries(ctx.conn, "location", active_only=True)]
    return {"plans": [dict(_public(ctx.conn, r), author=r["author"]) for r in rows], "statuses": STATUSES,
            "locations": locations}


def api_create(ctx):
    pid = _pid(ctx, "editor")
    conn = ctx.conn
    title = validate.text(ctx.body, "title", 200, required=False) or "Test Plan"
    tests = _tests(conn, pid, ctx.body.get("tests"))
    location = _location(conn, ctx.body.get("location"))
    n = conn.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code, 4) AS INTEGER)), 0) + 1 FROM testing_plans").fetchone()[0]
    code = "TP-{:03d}".format(n)
    now = db.utc_now()
    plan_id = conn.execute(
        "INSERT INTO testing_plans (project_id, code, title, location, tests, purpose, status, created_by, created_at, "
        "updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?)",
        (pid, code, title, location, json.dumps(tests), validate.text(ctx.body, "purpose", 4000, required=False),
         ctx.user["id"], now, ctx.user["id"], now)).lastrowid
    _log(ctx, "testing_plan_created", plan_id, {"code": code, "tests": len(tests), "location": location})
    return {"code": code}


def api_get(ctx):
    pid = _pid(ctx)
    row = _row(ctx, pid)
    p = _public(ctx.conn, row)
    marks = ",".join("?" * len(p["tests"])) or "NULL"
    tests = {r["test_id"]: r for r in ctx.conn.execute(
        "SELECT test_id, title, subject, standard, section, method, status FROM testing_tests WHERE project_id = ? AND "
        "test_id IN ({})".format(marks), [pid] + p["tests"])}
    pages = catalog.procedure_pages(ctx.conn, catalog.project_id(ctx.conn))  # shared wiki
    p["test_rows"] = [dict(tests[t], has_procedure=tests[t]["subject"] in pages) for t in p["tests"] if t in tests]
    p["results_name"] = row["results_name"]
    p.update(bundles.public(ctx.conn, row, ctx.config))  # 0.60.90 (D-O-096)
    return {"plan": p, "statuses": STATUSES}


def api_update(ctx):
    pid = _pid(ctx, "editor")
    row = _row(ctx, pid)
    changes = {}
    for key, limit in (("title", 200), ("purpose", 4000), ("docno", 40), ("rev", 10)):
        if key in ctx.body:
            changes[key] = validate.text(ctx.body, key, limit, required=False)
    if "tests" in ctx.body or "location" in ctx.body:
        if row["status"] != "draft":
            raise ApiError(409, "Plan {} « {} » : tests et fournisseur ne changent qu'en Draft. Correctif : « Draft » d'abord "
                                "(le fournisseur devra recevoir la nouvelle version).".format(row["code"], STATUSES[row["status"]]))
        if "tests" in ctx.body:
            changes["tests"] = json.dumps(_tests(ctx.conn, pid, ctx.body["tests"]))
        if "location" in ctx.body:
            changes["location"] = _location(ctx.conn, ctx.body["location"])
    if changes:
        changes.update(updated_by=ctx.user["id"], updated_at=db.utc_now())
        ctx.conn.execute("UPDATE testing_plans SET {} WHERE id = ?".format(", ".join(k + " = ?" for k in changes)),
                         list(changes.values()) + [row["id"]])
        _log(ctx, "testing_plan_updated", row["id"], {"fields": sorted(k for k in changes if not k.startswith("updated"))})
    return {"ok": True}


def api_status(ctx):
    pid = _pid(ctx, "editor")
    row = _row(ctx, pid)
    to = ctx.body.get("status")
    if (row["status"], to) not in MOVES:
        raise ApiError(400, "Passage « {} → {} » impossible. Correctif : {}.".format(
            STATUSES[row["status"]], STATUSES.get(to, to), " ou ".join(STATUSES[b] for a, b in sorted(MOVES) if a == row["status"])
            or "aucun passage depuis ce status"))
    if to == "closed" and not row["results_id"]:
        raise ApiError(409, "Plan {} : le PDF des résultats du fournisseur n'est pas joint. Correctif : « Joindre les résultats "
                            "(PDF) », puis fermez.".format(row["code"]))
    if to == "closed":  # 0.60.90 (D-O-096): every prototype tested has its bundle, every test its result and evidence
        blockers = bundles.close_blockers(ctx.conn, row)
        if blockers:
            raise ApiError(409, "Plan {} : pas prêt à fermer. Correctif : {}".format(row["code"], " ".join(blockers[:8])))
    now = db.utc_now()
    extra = {"sent": ", sent_at = ?", "closed": ", closed_at = ?, closed_by = {}".format(int(ctx.user["id"]))}.get(to, "")
    params = [to, ctx.user["id"], now] + ([now] if extra else []) + [row["id"]]
    ctx.conn.execute("UPDATE testing_plans SET status = ?, updated_by = ?, updated_at = ?{} WHERE id = ?".format(extra), params)
    _log(ctx, "testing_plan_status", row["id"], {"from": row["status"], "to": to})
    return {"ok": True}


@uploads.binary_body
def api_results(ctx):
    pid = _pid(ctx, "editor")
    row = _row(ctx, pid)
    if row["status"] not in ("sent", "results"):
        raise ApiError(409, "Plan {} « {} » : les résultats se joignent quand le plan est « Sent to Supplier ». Correctif : "
                            "envoyez d'abord le plan.".format(row["code"], STATUSES[row["status"]]))
    stored = uploads.store_pdf(ctx, pid, "testing_plan", int(ctx.config.get("max_upload_mb", 50)) * 1048576)
    name = stored["original_name"] or "resultats.pdf"
    ctx.conn.execute("UPDATE testing_plans SET results_id = ?, results_name = ?, status = 'results', updated_by = ?, updated_at = ? "
                     "WHERE id = ?", (stored["id"], name, ctx.user["id"], db.utc_now(), row["id"]))
    _log(ctx, "testing_plan_results", row["id"], {"file": name, "size": stored["size"]})
    return {"ok": True, "name": name}


def api_results_file(ctx):
    pid = _pid(ctx)
    row = _row(ctx, pid)
    att = ctx.conn.execute("SELECT * FROM attachments WHERE id = ?", (row["results_id"],)).fetchone() if row["results_id"] else None
    if att is None:
        raise ApiError(404, "Aucun PDF de résultats joint à {}.".format(row["code"]))
    return RawFile(uploads.read(ctx.data_dir, att), "{}_resultats.pdf".format(row["code"]), "application/pdf", export=False)


# --------------------------------------------------------------------------
# Word
# --------------------------------------------------------------------------
def _todo(text):
    return d.para([d.run("[À COMPLÉTER] ", bold=True, color=TODO), d.run(text, italic=True, color=TODO)])


def _page_blocks(ctx, pid, page_id):
    """The procedure page of a subject, in the template's styles (its own « Tests Covered » table is left out:
    the plan has its table of the chosen tests)."""
    from modules.dynamite import export
    page = ctx.conn.execute("SELECT * FROM dynamite_pages WHERE id = ?", (page_id,)).fetchone()
    body = ctx.conn.execute("SELECT body FROM dynamite_versions WHERE page_id = ? AND version = ?",
                            (page_id, page["current_version"])).fetchone()
    items = export.flatten(ctx, pid, page, json.loads(body["body"]), depth_offset=2)
    text = lambda runs: [d.run(t, bold=s.get("bold", False), italic=s.get("italic", False)) for t, s in runs]
    out, skip = [], False
    for it in items:
        kind = it[0]
        if kind == "h":
            title = "".join(t for t, _ in it[2])
            skip = "Tests Covered" in title
            if not skip:  # the template numbers the headings: the page's own « 1. » is dropped
                out.append(d.heading(3, re.sub(r"^\s*\d+(\.\d+)*\.?\s+", "", title)))
        elif skip:
            continue
        elif kind == "p":
            out.append(d.para(text(it[1]) or [d.run("")]))
        elif kind == "li":
            out.append(d.para(text(it[3]) or [d.run("")], style="Paragraphedeliste", bullet=True))
        elif kind == "code":
            out.append(d.para([d.run(it[1])]))
        elif kind == "table" and it[2]:
            rows = [["".join(t for t, _ in cell) for cell in row] for row in it[2]]
            width = max(len(r) for r in rows)
            rows = [r + [""] * (width - len(r)) for r in rows]
            head, body_rows = (rows[0], rows[1:]) if it[1] else ([""] * width, rows)
            out.append(d.table(head, body_rows, [9400 // width] * width))
    return out


def body(ctx, pid, plan, supplier):
    conn = ctx.conn
    tests = {r["test_id"]: r for r in conn.execute("SELECT * FROM testing_tests WHERE project_id = ?", (pid,))}
    chosen = [tests[t] for t in plan["tests"] if t in tests]
    ref = catalog.project_id(conn)  # D-B-097: the procedure pages are the shared wiki TESTING
    pages = catalog.procedure_pages(conn, ref)
    subjects = list(dict.fromkeys(t["subject"] for t in chosen))
    out = [d.heading(1, "Purpose and Scope"),
           d.para("This test plan asks {} to perform the {} test(s) listed in section 3 on the team's test article, to write its "
                  "test report following this plan section by section, and to return the results to the team as a PDF file."
                  .format(supplier["label"], len(chosen)))]
    out.append(d.para(plan["purpose"]) if plan["purpose"].strip() else _todo("Contexte du programme, article testé, but de la campagne "
                                                                               "et requirements visés."))
    out += [d.heading(1, "Test Supplier and Responsibilities"),
            d.table(["Item", "Value"], [["Test supplier", supplier["label"]], ["Supplier code (Test Location list)", supplier["code"]],
                                        ["Team test plan", plan["code"] + " rev. " + (plan["rev"] or "A")],
                                        ["Team contact", plan["author"]]], [3200, 6200]),
            _todo("Contact chez le fournisseur, accréditation / portée (ex. ISO/IEC 17025), lieu et dates prévues."),
            d.heading(1, "Tests Requested"),
            d.table(["Test", "Title", "Standard · Section", "Level", "Method"],
                    [[t["test_id"], t["title"], (t["standard"] + " · " + t["section"]).strip(" ·"), t["level"], t["method"]]
                     for t in chosen], [1300, 3300, 2800, 1000, 1000]),
            d.heading(1, "Test Article and Configuration"),
            _todo("Numéro de série, révisions matériel et logiciel, état à la livraison, conditionnement et "
                  "transport, instrumentation fournie par l'équipe.")]
    out.append(d.heading(1, "Test Procedures"))
    for subject in subjects:
        out.append(d.heading(2, catalog.SUBJECTS.get(subject, subject)))
        if subject in pages:
            out.append(d.para([d.run("Procedure (Dynamite, TESTING Space): ", bold=True), d.run(pages[subject]["title"])]))
            out += _page_blocks(ctx, ref, pages[subject]["id"])
        else:
            out.append(_todo("Aucune procédure existante pour ce sujet : rédigez-la à la main (moyens, conditions, séquence)."))
        for t in (x for x in chosen if x["subject"] == subject):
            out += [d.heading(3, "{} — {}".format(t["test_id"], t["title"])),
                    d.table(["Item", "Value"], [["Standard · Section", (t["standard"] + " · " + t["section"]).strip(" ·")],
                                                ["Level · Method", "{} · {}".format(t["level"], t["method"])],
                                                ["Test Equipment", t["equipment"] or "—"], ["Objective", t["objective"] or "—"],
                                                ["Acceptance Criteria", t["acceptance"] or "—"],
                                                ["Test Means", t["means"] or "—"]], [2600, 6800])]
            if not (t["means"] or "").strip():
                out.append(_todo("Montage, instrumentation et réglages particuliers de ce test chez le fournisseur."))
    out += [d.heading(1, "Test Report and Deliverables"),
            d.para("The supplier's test report follows this plan: for each test, the configuration actually tested, the means "
                   "used, the raw and processed results, the pass / fail decision against the acceptance criteria, and every "
                   "deviation. The report is returned to the team as one PDF file; the team attaches it to plan " + plan["code"] +
                   " before closing it."),
            _todo("Délais de remise, format des données brutes, conservation des échantillons, confidentialité."),
            d.heading(1, "Approvals"),
            d.table(["Role", "Name", "Signature and date"], [["Team — prepared by", plan["author"], ""], ["Team — approved by", "", ""],
                                                             [supplier["label"] + " — accepted by", "", ""]], [3000, 3200, 3200])]
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'testing_lists'").fetchone():
        from . import glossary
        out += glossary.docx_sections(conn, d, "en", "Definitions and Conventions", [("Method", "I Inspection, A Analysis, "
                                                                                           "D Demonstration, T Test")])
    return out


def api_docx(ctx):
    pid = _pid(ctx)
    row = _row(ctx, pid)
    plan = _public(ctx.conn, row)
    author = ctx.conn.execute("SELECT display_name FROM users WHERE id = ?", (row["created_by"],)).fetchone()
    plan["author"] = author["display_name"] if author else ""
    loc = next((e for e in lists.entries(ctx.conn, "location") if e["code"] == row["location"]), None)
    supplier = {"code": row["location"], "label": loc["label"] if loc else row["location"]}
    meta = d.meta_from_query({"title": "{} — {}".format(row["title"], supplier["label"]), "docno": row["docno"] or row["code"],
                              "rev": row["rev"] or "A", "doctype": "Test Plan", "prepared": plan["author"], "lang": "en"}, {})
    data = d.build(meta, "".join(body(ctx, pid, plan, supplier)), "Issued to " + supplier["label"], ctx.user["display_name"])
    _log(ctx, "testing_plan_docx", row["id"], {"supplier": supplier["code"]})
    safe = re.sub(r"[^A-Za-z0-9]+", "-", supplier["label"]).strip("-")[:30]
    return RawFile(data, "{}_Test_Plan_{}_rev{}.docx".format(row["code"], safe, row["rev"] or "A"),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
