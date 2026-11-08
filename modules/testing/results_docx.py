"""Word summary of the results of a test plan (0.60.92, D-O-098): prototypes tested, a result for each test of each
bundle with its justification and evidence, and the index of the evidence files. Built from what the bundles hold;
the evidence files themselves stay on the server (named here, not embedded)."""
import json
import re

from core.files import RawFile

from . import bundles, plans, word_doc as d

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _size(n):
    if n is None:  # 0.60.94 (D-O-100): a network reference without a declared size
        return "—"
    return "{:.1f} MB".format(n / 1048576) if n >= 1048576 else "{} KB".format(max(1, round(n / 1024)))


def _where(e):
    """0.60.94 (D-O-100): the version on the platform, or where a file too large for it lies on the network."""
    return "Network: " + e["link"] if e.get("kind") == "link" else "Platform (v{})".format(e.get("version") or 1)


def build_body(conn, row, data):
    titles = {r["test_id"]: r["title"] for r in conn.execute("SELECT test_id, title FROM testing_tests WHERE project_id = ?",
                                                             (row["project_id"],))}
    tests = json.loads(row["tests"] or "[]")
    names = {e["id"]: e["name"] for e in data["evidence"]}
    out = [d.heading(1, "Purpose and Scope"),
           d.para("Summary of the results of test plan {} (status: {}): one section per prototype actually tested, with the result of "
                  "each test, its justification and the evidence that supports it.".format(row["code"], plans.STATUSES[row["status"]])),
           d.heading(1, "Prototypes Tested")]
    if not data["bundles"]:
        out.append(d.para("No prototype has been recorded yet."))
    else:
        out.append(d.table(["Prototype", "Serial number", "Results", "Note"], [
            [b["proto"], b["serial"] or "—", "{} / {}".format(sum(1 for t in tests if (b["results"].get(t) or {}).get("result")), len(tests)),
             b["note"] or "—"] for b in data["bundles"]], [2200, 2000, 1400, 3800]))
    out.append(d.heading(1, "Results by Prototype"))
    for b in data["bundles"]:
        out.append(d.heading(2, "Prototype {}{}".format(b["proto"], " · S/N " + b["serial"] if b["serial"] else "")))
        rows = []
        for t in tests:
            r = b["results"].get(t) or {"result": "", "note": "", "evidence": []}
            rows.append([t + " — " + titles.get(t, ""), bundles.RESULTS.get(r["result"], "Not recorded"), r["note"] or "—",
                         ", ".join(names[i] for i in r["evidence"] if i in names) or "—"])
        out.append(d.table(["Test", "Result", "Justification", "Evidence"], rows, [2800, 1500, 2600, 2500]))
    out.append(d.heading(1, "Evidence Index"))
    if data["evidence"]:
        label = {b["id"]: b["proto"] for b in data["bundles"]}
        out.append(d.table(["File", "Location", "Size", "Filed by", "Bundle"], [
            [e["name"], _where(e), _size(e["size"]), e["by"] or "", label.get(e["bundle_id"], "Bulk")] for e in data["evidence"]],
            [2800, 2600, 1000, 1700, 1300]))
    else:
        out.append(d.para("No evidence file has been filed."))
    return out


def api_results_docx(ctx):
    pid = plans._pid(ctx)
    row = plans._row(ctx, pid)
    data = bundles.public(ctx.conn, row)
    meta = d.meta_from_query({"title": "{} — Test Results".format(row["title"]), "docno": row["docno"] or row["code"],
                              "rev": row["rev"] or "A", "doctype": "Test Results", "prepared": ctx.user["display_name"], "lang": "en"}, {})
    blob = d.build(meta, "".join(build_body(ctx.conn, row, data)), "Results summary", ctx.user["display_name"])
    plans._log(ctx, "testing_plan_results_docx", row["id"], {"bundles": len(data["bundles"])})
    return RawFile(blob, "{}_Results_rev{}.docx".format(row["code"], re.sub(r"[^A-Za-z0-9]+", "-", row["rev"] or "A")), DOCX)
