"""Diamond · « Coûts et budget », the computation and the CSV (0.60.61, D-O-070).

budget(settings, nre, lines, hours) -> the figures of the page, all in the currency of the Space:
  unit      cost of one product: in prototype, and at each production volume (a missing production price counts at the
            prototype price, and the line is reported, so a total is never silently too low);
  nre       total, by category, by phase, and what is already committed or paid;
  project   the project budget: NRE + prototypes (number x unit cost in prototype) + team time (Timesheet hours x hourly
            rate) + contingency on the whole;
  volumes   for each volume: parts cost, NRE per unit, full cost per unit, total programme cost (NRE + volume x parts);
  checks    what is missing or worth a look before showing the page (prices missing, estimates only, no NRE…).
"""
import csv
import io

from core.files import RawFile

from . import costs as C
from . import functions as F


def _money(x):
    return round(float(x or 0), 2)


def budget(s, nre, lines, hours):
    vols = s["volumes"]
    proto, prod = 0.0, [0.0, 0.0, 0.0]
    missing_proto, missing_prod = [], []
    for ln in lines:
        q = float(ln["qty"] if ln["qty"] is not None else 1)
        if ln["proto_unit"] is None:
            missing_proto.append(ln["code"] or ln["name"])
        unit_proto = float(ln["proto_unit"] or 0)
        proto += q * unit_proto
        for k in range(3):
            price = ln["prod_{}".format(k + 1)]
            if price is None:
                if ln["proto_unit"] is not None and (ln["code"] or ln["name"]) not in missing_prod:
                    missing_prod.append(ln["code"] or ln["name"])
                price = ln["proto_unit"] or 0
            prod[k] += q * float(price)
    nre_total = sum(float(r["amount"] or 0) for r in nre)
    by_cat = {}
    by_phase = {}
    for r in nre:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + float(r["amount"] or 0)
        by_phase[r["phase"] or ""] = by_phase.get(r["phase"] or "", 0) + float(r["amount"] or 0)
    committed = sum(float(r["amount"] or 0) for r in nre if r["basis"] in ("engage", "paye"))
    paid = sum(float(r["amount"] or 0) for r in nre if r["basis"] == "paye")
    prototypes = s["proto_qty"] * proto
    labour = hours * float(s["labour_rate"] or 0)
    subtotal = nre_total + prototypes + labour
    contingency = subtotal * float(s["contingency"] or 0) / 100
    volumes = []
    for k, v in enumerate(vols):
        per_unit_nre = nre_total / v if v else 0
        volumes.append({"volume": v, "parts": _money(prod[k]), "nre_per_unit": _money(per_unit_nre),
                        "full_unit": _money(prod[k] + per_unit_nre), "programme": _money(nre_total + v * prod[k])})
    checks = []
    if not lines:
        checks.append("Aucune pièce : ajoutez les pièces dans Diamond → Structure fonctionnelle → Pièces, ou des lignes libres ici.")
    if missing_proto:
        checks.append("Prix en prototype manquant pour {} ligne(s) ({}{}) : le coût unitaire est trop bas.".format(
            len(missing_proto), ", ".join(missing_proto[:6]), " …" if len(missing_proto) > 6 else ""))
    if missing_prod:
        checks.append("Prix de production manquant pour {} ligne(s) ({}{}) : compté au prix de prototype, donc probablement trop haut.".format(
            len(missing_prod), ", ".join(missing_prod[:6]), " …" if len(missing_prod) > 6 else ""))
    if not nre:
        checks.append("Aucun NRE : pensez à l'outillage, aux moules, aux essais, à la certification, aux gabarits.")
    elif nre_total and all(r["basis"] == "estimation" for r in nre):
        checks.append("Tous les NRE sont des estimations : une soumission sur les plus gros montants rendra le budget crédible.")
    if hours and not s["labour_rate"]:
        checks.append("{:g} h saisies dans Timesheet mais aucun taux horaire : le temps de l'équipe ne compte pas dans le budget.".format(round(hours, 1)))
    big = sorted(lines, key=lambda ln: -float(ln["qty"] or 1) * float(ln["proto_unit"] or 0))[:3]
    if proto and big:
        share = sum(float(ln["qty"] or 1) * float(ln["proto_unit"] or 0) for ln in big) / proto
        if share >= 0.5:
            checks.append("Trois lignes font {:.0f} % du coût unitaire ({}) : c'est là que se gagne le prix.".format(
                share * 100, ", ".join(ln["code"] or ln["name"] for ln in big)))
    return {"currency": s["currency"], "unit_proto": _money(proto), "nre_total": _money(nre_total),
            "nre_by_category": {k: _money(v) for k, v in by_cat.items()}, "nre_by_phase": {k: _money(v) for k, v in by_phase.items()},
            "nre_committed": _money(committed), "nre_paid": _money(paid), "proto_qty": s["proto_qty"], "prototypes": _money(prototypes),
            "hours": round(hours, 1), "labour_rate": s["labour_rate"], "labour": _money(labour), "subtotal": _money(subtotal),
            "contingency_pct": s["contingency"], "contingency": _money(contingency), "total": _money(subtotal + contingency),
            "volumes": volumes, "checks": checks}


def api_export(ctx):
    """CSV (Excel) : the summary, then the NRE, then the parts."""
    pid = F.access(ctx)
    data = C.payload(ctx.conn, pid)
    b, s, L = data["budget"], data["settings"], data["labels"]
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    cur = b["currency"]
    w.writerow(["Budget du projet", cur])
    for label, value in (("NRE", b["nre_total"]), ("Prototypes ({} × {})".format(b["proto_qty"], b["unit_proto"]), b["prototypes"]),
                         ("Temps de l'équipe ({} h × {})".format(b["hours"], b["labour_rate"]), b["labour"]),
                         ("Contingence ({} %)".format(b["contingency_pct"]), b["contingency"]), ("Total", b["total"]),
                         ("NRE engagés ou payés", b["nre_committed"])):
        w.writerow([label, value])
    w.writerow([])
    w.writerow(["Volume", "Pièces par unité", "NRE par unité", "Coût complet par unité", "Coût du programme"])
    for v in b["volumes"]:
        w.writerow([v["volume"], v["parts"], v["nre_per_unit"], v["full_unit"], v["programme"]])
    w.writerow([])
    w.writerow(["NRE", "Intitulé", "Catégorie", "Phase", "Montant", "Base", "Fournisseur", "Notes"])
    for r in data["nre"]:
        w.writerow(["NRE-{}".format(r["number"]), r["title"], L["categories"].get(r["category"], r["category"]), r["phase"],
                    r["amount"], L["bases"].get(r["basis"], r["basis"]), r["supplier"], r["notes"]])
    w.writerow([])
    vols = s["volumes"]
    w.writerow(["Pièce", "Désignation", "Quantité", "Prix prototype"] + ["Prix à {}".format(v) for v in vols] + ["Fournisseur", "Base", "Notes"])
    for ln in data["lines"]:
        w.writerow([ln["code"], ln["name"], ln["qty"], ln["proto_unit"], ln["prod_1"], ln["prod_2"], ln["prod_3"], ln["supplier"],
                    L["bases"].get(ln["basis"], ln["basis"]), ln["notes"]])
    key = ctx.conn.execute("SELECT key FROM projects WHERE id = ?", (pid,)).fetchone()["key"]
    C._log(ctx, "diamond_cost_export", "projects", pid)
    return RawFile(("\ufeff" + out.getvalue()).encode("utf-8"), "{}_couts_budget.csv".format(key), "text/csv")
