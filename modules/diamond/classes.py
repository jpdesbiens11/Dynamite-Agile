"""Special characteristics in the DFMEA (0.60.101, D-O-108): the class CC / SC of a failure chain.

AIAG (APQP, Control Plan) and IATF 16949:2016 § 8.3.3.3: a Critical Characteristic (CC) touches safety or the law; a
Significant Characteristic (SC) touches the fit, the function, the performance or the satisfaction of the customer. The
platform proposes, a person decides -- nothing becomes CC by itself:
  proposal  computed at every read from S and O and the rules of the Space (start: S >= 9 -> CC; S 5 to 8 and O >= 4 ->
            SC, the YC / YS logic of Ford), never stored;
  decision  on the row (class_code, class_state confirmed | refused, who, when, why, S and O at that moment) and appended
            to diamond_class_decisions: a refusal is kept, so that one knows the question was asked;
  symbols   the class is internal (CC, SC); the dictionary of the Space's customer translates it on screen and in the
            exports -- generic AIAG, Ford (YC / YS in the DFMEA, CC ∇ / SC in process), aerospace AS9100 / AS9103 (CSC /
            KC). The symbols of other OEMs are never hard-coded: the team writes them from the customer's CSR.
The routes are in classes_api.py.
"""
from core import prefs

CLASSES = {"CC": "Critical Characteristic", "SC": "Significant Characteristic"}
STATES = {"proposed": "Proposée", "confirmed": "Confirmée", "refused": "Refusée"}
RULES = {"customer": "aiag", "cc_severity": 9, "sc_severity": 5, "sc_occurrence": 4}
CUSTOMER_FIELDS = {"name": ("Nom du client", 80), "cc_dfmea": ("Symbole CC au DFMEA", 12), "sc_dfmea": ("Symbole SC au DFMEA", 12),
                   "cc_symbol": ("Symbole CC au procédé et à l'export", 12), "sc_symbol": ("Symbole SC au procédé et à l'export", 12),
                   "cc_label": ("Libellé CC", 80), "sc_label": ("Libellé SC", 80), "source": ("Source", 300)}
# 0.60.102 (D-O-110): the Cpk a customer requires of a characteristic of each class (AIAG start values)
CUSTOMER_NUMBERS = {"cc_cpk": ("Cpk exigé d'une CC", 1.67), "sc_cpk": ("Cpk exigé d'une SC", 1.33)}
CSR = "À confirmer dans les CSR (Customer-Specific Requirements) du client avant une revue formelle."
PRESETS = [
    {"code": "aiag", "name": "AIAG générique", "cc_dfmea": "CC", "sc_dfmea": "SC", "cc_symbol": "CC", "sc_symbol": "SC",
     "cc_label": "Critical Characteristic", "sc_label": "Significant Characteristic",
     "source": "Classes de base de l'AIAG (APQP, Control Plan) et de l'IATF 16949:2016 § 8.3.3.3."},
    {"code": "ford", "name": "Ford", "cc_dfmea": "YC", "sc_dfmea": "YS", "cc_symbol": "CC ∇", "sc_symbol": "SC",
     "cc_label": "Critical Characteristic (YC au DFMEA)", "sc_label": "Significant Characteristic (YS au DFMEA)",
     "source": "Ford SCCAF : YC / YS au DFMEA, CC (∇) / SC au procédé. " + CSR},
    {"code": "aero", "name": "Aéro AS9100 / AS9103", "cc_dfmea": "CSC", "sc_dfmea": "KC", "cc_symbol": "CSC", "sc_symbol": "KC",
     "cc_label": "Critical Safety Characteristic", "sc_label": "Key Characteristic (AS9103)",
     "source": "SAE AS9100, AS9103 (Variation Management of Key Characteristics), IAQG. " + CSR},
]
PRESET_CODES = [p["code"] for p in PRESETS]
MAX_CUSTOMERS = 20


def rules(conn, pid):
    row = conn.execute("SELECT * FROM diamond_class_settings WHERE project_id = ?", (pid,)).fetchone()
    out = dict(RULES)
    if row:
        out.update({k: row[k] for k in RULES})
    return out


def customers(conn, pid):
    """The presets (with the Space's changes over them), then the customers the team added."""
    own = {r["code"]: dict(r) for r in conn.execute("SELECT * FROM diamond_class_customers WHERE project_id = ? ORDER BY id", (pid,))}
    out = []
    starts = {k: v[1] for k, v in CUSTOMER_NUMBERS.items()}
    for p in PRESETS:
        row = dict(starts, **p, preset=True, edited=p["code"] in own)
        if p["code"] in own:
            row.update({k: own[p["code"]][k] for k in CUSTOMER_FIELDS})
            row.update({k: own[p["code"]][k] for k in CUSTOMER_NUMBERS if own[p["code"]][k] is not None})
        out.append(row)
    for code, r in own.items():
        if code not in PRESET_CODES:
            row = dict({k: r[k] for k in CUSTOMER_FIELDS}, code=code, preset=False, edited=True)
            row.update({k: r[k] if r[k] is not None else starts[k] for k in CUSTOMER_NUMBERS})
            out.append(row)
    return out


def customer(conn, pid, code=None):
    items = customers(conn, pid)
    code = code or rules(conn, pid)["customer"]
    return next((c for c in items if c["code"] == code), items[0])


def propose(severity, occurrence, r):
    """The class the rules propose for S and O ('' when none, or when S is not rated yet)."""
    if not severity:
        return ""
    if severity >= r["cc_severity"]:
        return "CC"
    if r["sc_severity"] <= severity < r["cc_severity"] and (occurrence or 0) >= r["sc_occurrence"]:
        return "SC"
    return ""


def status(row, proposed):
    """confirmed | proposed | refused | '' -- a refusal of the class proposed now keeps the row out of « proposed »."""
    if row["class_state"] == "confirmed":
        return "confirmed"
    if proposed and not (row["class_state"] == "refused" and row["class_code"] == proposed):
        return "proposed"
    return "refused" if row["class_state"] == "refused" else ""


def symbol(cust, code, where="dfmea"):
    """The customer's symbol of an internal class, in the DFMEA or in the process documents and exports."""
    if code not in CLASSES:
        return ""
    return cust[code.lower() + ("_dfmea" if where == "dfmea" else "_symbol")] or code


def _who(conn, ids):
    out = {}
    for uid in ids:
        row = conn.execute("SELECT display_name, username FROM users WHERE id = ?", (uid,)).fetchone()
        if row:
            out[uid] = {"name": row["display_name"] or row["username"], "initials": prefs.get(conn, uid).get("initials") or ""}
    return out


def enrich(conn, pid, rows):
    """Adds to each DFMEA row: class_proposed, class_status, class_symbol, class_by_name / initials, class_changed, special."""
    r, cust = rules(conn, pid), customer(conn, pid)
    who = _who(conn, {row["class_by"] for row in rows if row.get("class_by")})
    asked = {h["dfmea_id"]: h["n"] for h in conn.execute(
        "SELECT dfmea_id, COUNT(*) AS n FROM diamond_class_decisions WHERE project_id = ? GROUP BY dfmea_id", (pid,))}
    for row in rows:
        proposed = propose(row["severity"], row["occurrence"], r)
        st = status(row, proposed)
        shown = proposed if st == "proposed" else row["class_code"] if st else ""
        by = who.get(row.get("class_by")) or {}
        decided = row["class_state"] in ("confirmed", "refused")
        row.update(class_proposed=proposed, class_status=st, class_shown=shown, class_symbol=symbol(cust, shown),
                   class_by_name=by.get("name", ""), class_by_initials=by.get("initials", ""), class_history=asked.get(row["id"], 0),
                   class_changed=decided and (row["severity"], row["occurrence"]) != (row["class_severity"], row["class_occurrence"]),
                   special=st == "confirmed" and row["class_code"] in CLASSES)
    return rows


def counts(rows, r):
    """What the filters of the DFMEA show: every row, CC · SC confirmed, S >= the CC threshold, CC proposed, and the confirmed
    classes that no characteristic C-n carries yet (0.60.102, D-O-110; char_links.attach)."""
    return {"all": len(rows), "special": sum(1 for x in rows if x["special"]),
            "severe": sum(1 for x in rows if (x["severity"] or 0) >= r["cc_severity"]),
            "cc_proposed": sum(1 for x in rows if x["class_status"] == "proposed" and x["class_proposed"] == "CC"),
            "no_characteristic": sum(1 for x in rows if no_characteristic(x))}


def no_characteristic(row):
    """0.60.102 (D-O-110): a confirmed class with no characteristic C-n (0.60.101: an empty Requirement / Characteristic)."""
    return row["special"] and not row.get("characteristics")


def checks(rows, r):
    """The advice of the method about the classes, in the « Conseils de la méthode » of the DFMEA."""
    out = []
    lines = lambda items: ", ".join(str(x["line"]) for x in items[:12])
    cc = [x for x in rows if x["class_status"] == "proposed" and x["class_proposed"] == "CC"]
    if cc:
        out.append("Ligne(s) {} : CC proposée (S ≥ {}) — une personne la confirme ou la refuse, avec une justification.".format(lines(cc), r["cc_severity"]))
    sc = [x for x in rows if x["class_status"] == "proposed" and x["class_proposed"] == "SC"]
    if sc:
        out.append("Ligne(s) {} : SC proposée (S {} à {} et O ≥ {}) — à confirmer ou refuser, avec une justification.".format(
            lines(sc), r["sc_severity"], r["cc_severity"] - 1, r["sc_occurrence"]))
    blank = [x for x in rows if no_characteristic(x)]
    if blank:
        out.append("Ligne(s) {} : CC ou SC confirmée sans caractéristique C-n — « + Caractéristique » la crée : la cote, le seuil "
                   "ou le temps exact, la pièce qui le porte, le plan.".format(lines(blank)))
    moved = [x for x in rows if x["class_status"] == "confirmed" and x["class_changed"] and x["class_proposed"] != x["class_code"]]
    if moved:
        out.append("Ligne(s) {} : S ou O a changé depuis la confirmation de la classe et la règle ne la propose plus — relisez "
                   "la décision.".format(lines(moved)))
    return out


def info(conn, pid, rows):
    """The part of the DFMEA payload about the classes."""
    r = rules(conn, pid)
    return {"rules": r, "customer": customer(conn, pid, r["customer"]), "counts": counts(rows, r), "states": STATES, "names": CLASSES}
