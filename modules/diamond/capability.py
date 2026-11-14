"""Measurements and capability of a characteristic C-n (0.60.103, D-O-115, increment 6 of D-O-109), computed by the server.

Individual measurements (one value per part; entered at the station or imported as CSV from a SPC software):
  Ppk  overall: the sample standard deviation s of every value;
  Cpk  within: σ estimated by the average moving range of consecutive values, MR̄ / 1,128 (d2 for n = 2) -- the usual estimate
       for individual measurements (I-MR chart);
  both min((USL − x̄) / 3σ, (x̄ − LSL) / 3σ), one-sided when the characteristic has only one limit. Fewer than 25 values: the
  figure is shown with « échantillon court » (an initial study usually asks for 25 subgroups or 100 values).
A characteristic checked by a 100 % test writes « essai 100 % » instead of a Cpk. Status: « Capable » (Cpk ≥ required),
« Sous l'exigé », « à mesurer », « essai 100 % ». Routes under /cplans: the « Plans de contrôle » switch covers them.
"""
import csv
import datetime as dt
import io
import math

from core import audit, db
from core.errors import ApiError

from . import char_spec as SP
from . import process as PR

D2 = 1.128
SHORT = 25
MAX_VALUES = 5000


def stats(values, lsl, usl):
    """{n, mean, s, sigma_within, ppk, cpk, short} from individual values (None where it cannot be computed)."""
    n = len(values)
    out = {"n": n, "mean": None, "s": None, "sigma_within": None, "ppk": None, "cpk": None, "short": n < SHORT}
    if n < 2 or (lsl is None and usl is None):
        if n:
            out["mean"] = sum(values) / n
        return out
    mean = sum(values) / n
    s = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    mr = [abs(b - a) for a, b in zip(values, values[1:])]
    sw = (sum(mr) / len(mr)) / D2 if mr else None

    def index(sigma):
        if not sigma:
            return None
        sides = []
        if usl is not None:
            sides.append((usl - mean) / (3 * sigma))
        if lsl is not None:
            sides.append((mean - lsl) / (3 * sigma))
        return round(min(sides), 2)
    out.update(mean=mean, s=s, sigma_within=sw, ppk=index(s), cpk=index(sw))
    return out


def values_of(conn, cid):
    return [r["value"] for r in conn.execute("SELECT value FROM diamond_measurements WHERE characteristic_id = ? ORDER BY taken_at, id", (cid,))]


def summary(conn, c):
    """What the summary shows for a characteristic: (cpk text, status key, status label, stats)."""
    if c["control"] == "test100":
        return "essai 100 %", "test100", "Essai 100 %", None
    st = stats(values_of(conn, c["id"]), c.get("lsl"), c.get("usl"))
    if st["cpk"] is None:
        return "à mesurer", "study", "Étude à faire", st
    req = c.get("cpk_req")
    text = SP.fmt(st["cpk"], 2)
    if req is not None and st["cpk"] < req:
        return text, "below", "Sous l'exigé", st
    return text, "capable", "Capable", st


def _char(conn, pid, cid):
    row = conn.execute("SELECT * FROM diamond_characteristics WHERE id = ? AND project_id = ?", (cid, pid)).fetchone()
    if row is None:
        raise ApiError(404, "Caractéristique introuvable dans ce Space.")
    return dict(row)


def parse(text, default_date):
    """Values from text: one per line, « valeur », « valeur ; date », « valeur ; date ; lot » or a CSV with a header
    (Valeur / Value, Date, Lot / Échantillon / Série). Returns ([(value, date, sample)], problems)."""
    text = str(text or "").lstrip("\ufeff")
    first = text.split("\n", 1)[0]
    # the separator: « ; » or a tab when there is one; a comma only when the first line is a header (« Valeur,Date,Lot ») --
    # otherwise « 2,05 » is one value with a decimal comma, never two cells
    delimiter = ";" if ";" in text else "\t" if "\t" in text else "," if any(ch.isalpha() for ch in first) and "," in first else None
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter)) if delimiter else [[line] for line in text.splitlines()]
    out, problems = [], []
    head = [h.strip().lower() for h in rows[0]] if rows else []
    start = 1 if any(h in ("valeur", "value", "mesure") for h in head) else 0
    iv = next((i for i, h in enumerate(head) if h in ("valeur", "value", "mesure")), 0) if start else 0
    idate = next((i for i, h in enumerate(head) if h in ("date", "taken_at", "horodatage")), 1) if start else 1
    isample = next((i for i, h in enumerate(head) if h in ("lot", "échantillon", "echantillon", "série", "serie", "sample", "n° de série")), 2) if start else 2
    for n, row in enumerate(rows[start:], start=start + 1):
        if not any(c.strip() for c in row):
            continue
        cell = lambda i: row[i].strip() if i < len(row) else ""  # noqa: E731
        try:
            value, _d = SP.number(cell(iv), "Valeur")
        except ApiError:
            value = None
        if value is None:
            problems.append("Ligne {} : valeur « {} » illisible — ignorée.".format(n, cell(iv)))
            continue
        out.append((value, cell(idate)[:25] or default_date, cell(isample)[:60]))
    if len(out) > MAX_VALUES:
        raise ApiError(413, "{} valeurs au plus par envoi.".format(MAX_VALUES))
    return out, problems


def api_measures(ctx):
    """POST …/cplans/measures {characteristic_id, values (text or CSV), source?}: the values appended (never replaced)."""
    pid = PR.access(ctx, "editor")
    c = _char(ctx.conn, pid, ctx.body.get("characteristic_id"))
    now = db.utc_now()
    values, problems = parse(ctx.body.get("values"), now[:19])
    if not values:
        raise ApiError(400, "Aucune valeur lue. Correctif : une valeur par ligne (ex. 2,05), ou un CSV avec une colonne Valeur.")
    source = "csv" if ctx.body.get("source") == "csv" else "manual"
    ctx.conn.executemany("INSERT INTO diamond_measurements (project_id, characteristic_id, value, taken_at, sample, source, entered_by, created_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [(pid, c["id"], v, d, smp, source, ctx.user["id"], now) for v, d, smp in values])
    audit.log_action(ctx.conn, ctx.user["id"], "diamond_measurements_add", "diamond_characteristics", c["id"], {"values": len(values), "source": source}, ctx.ip)
    return dict(api_get_one(ctx.conn, pid, c["id"]), added=len(values), problems=problems)


def api_get_one(conn, pid, cid):
    c = _char(conn, pid, cid)
    rows = [dict(r) for r in conn.execute("SELECT m.*, u.display_name AS by_name FROM diamond_measurements m LEFT JOIN users u ON u.id = m.entered_by "
                                          "WHERE m.characteristic_id = ? ORDER BY m.taken_at DESC, m.id DESC LIMIT 200", (cid,))]
    st = stats(values_of(conn, cid), c["lsl"], c["usl"])
    return {"characteristic_id": cid, "measurements": rows, "stats": st, "today": dt.date.today().isoformat()}


def api_get(ctx):
    pid = PR.access(ctx)
    return api_get_one(ctx.conn, pid, int(ctx.params["cid"]))
