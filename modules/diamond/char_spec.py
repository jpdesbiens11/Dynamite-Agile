"""The specification of a characteristic C-n (0.60.102, D-O-110): read what a person types, write it back the way a
drawing does, and say what is still missing.

Stored: nominal, LSL, USL (REAL, any may be empty), the number of decimals typed (« 2,0 » keeps one), the unit, a prefix
(R for a radius, Ø for a diameter) and a free text. Written back:
  nominal ± t           2,0 ± 0,3 mm          (LSL and USL symmetric around the nominal)
  nominal +a / −b       2,0 +0,3 / −0,2 mm    (asymmetric)
  USL only              ≤ 50 ms               (one-sided: the Cpk then uses that limit only, increment 6)
  LSL only              R 3,0 mm min.
  LSL and USL           0,05 à 2,00 m
  no number             the free text (an attribute: « aucune fuite à 0,5 bar »)
The required Cpk comes from the characteristic, else from the customer of the Space and the class (1,67 for a CC, 1,33 for
a SC); a characteristic checked by a 100 % test writes « 100 % » instead of inventing a Cpk.
"""
from core.errors import ApiError

CONTROLS = {"spc": "Étude de capabilité (Cpk)", "test100": "Essai 100 %", "design": "Vérifiée en conception"}
NATURES = {"product": "Product", "process": "Process"}
STATUS = {"incomplete": "À compléter", "study": "Étude à faire", "test100": "Essai 100 %", "design": "Vérifiée en conception",
          "unclassed": "Sans classe"}
MAX_DECIMALS = 4


def number(value, label):
    """(float or None, decimals typed) from « 2,0 », « 0.25 », « -3 », « » ."""
    text = str(value if value is not None else "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
    if text in ("", "-", "+"):
        return None, 0
    try:
        out = float(text)
    except ValueError:
        raise ApiError(400, "{} « {} » : un nombre, avec une virgule ou un point (ex. 2,0 ou 0.25).".format(label, value))
    if out != out or abs(out) > 1e9:
        raise ApiError(400, "{} « {} » : nombre hors limites.".format(label, value))
    decimals = len(text.split(".")[1]) if "." in text else 0
    return out, min(decimals, MAX_DECIMALS)


def limits(body, current):
    """{nominal, lsl, usl, decimals} from the body: the nominal with tol (±) or tol_plus / tol_minus, or lsl / usl directly.
    current: the stored values (a limit left out of the body keeps its value)."""
    keys = ("nominal", "tol", "tol_plus", "tol_minus", "lsl", "usl")
    if not any(k in body for k in keys):
        return {}
    labels = {"nominal": "Nominal", "tol": "Tolérance ±", "tol_plus": "Tolérance +", "tol_minus": "Tolérance −", "lsl": "LSL", "usl": "USL"}
    got, decimals, typed = {}, 0, False
    for k in keys:
        if k in body:
            got[k], d = number(body.get(k), labels[k])
            decimals, typed = max(decimals, d), typed or got[k] is not None
    nominal = got["nominal"] if "nominal" in body else current.get("nominal")
    if any(k in body for k in ("tol", "tol_plus", "tol_minus")):
        plus, minus = got.get("tol_plus", got.get("tol")), got.get("tol_minus", got.get("tol"))
        if nominal is None and (plus is not None or minus is not None):
            raise ApiError(400, "Une tolérance demande un nominal. Correctif : écrivez le nominal (ex. 2,0), ou les limites LSL / USL.")
        usl = nominal + abs(plus) if plus is not None else None
        lsl = nominal - abs(minus) if minus is not None else None
    else:
        lsl = got["lsl"] if "lsl" in body else current.get("lsl")
        usl = got["usl"] if "usl" in body else current.get("usl")
    if lsl is not None and usl is not None and lsl >= usl:
        raise ApiError(400, "LSL ({}) doit être sous USL ({}). Correctif : vérifiez la tolérance ou les limites.".format(
            fmt(lsl, decimals), fmt(usl, decimals)))
    if nominal is not None and ((lsl is not None and nominal < lsl) or (usl is not None and nominal > usl)):
        raise ApiError(400, "Le nominal {} est hors des limites. Correctif : un nominal entre LSL et USL.".format(fmt(nominal, decimals)))
    return {"nominal": nominal, "lsl": None if lsl is None else round(lsl, 9), "usl": None if usl is None else round(usl, 9),
            "decimals": decimals if typed else current.get("decimals", 1)}


def fmt(x, decimals):
    if x is None:
        return ""
    text = "{:.{}f}".format(x, max(0, int(decimals or 0)))
    return text.replace("-", "−").replace(".", ",")


def spec(c):
    """The specification as a drawing writes it (see the module text)."""
    d, unit = c.get("decimals", 1), (" " + c["unit"]) if c.get("unit") else ""
    pre = (c.get("prefix") or "") + " " if c.get("prefix") else ""
    nominal, lsl, usl = c.get("nominal"), c.get("lsl"), c.get("usl")
    if nominal is not None and lsl is not None and usl is not None:
        up, down = usl - nominal, nominal - lsl
        if abs(up - down) < 1e-9:
            return "{}{} ± {}{}".format(pre, fmt(nominal, d), fmt(up, d), unit)
        return "{}{} +{} / −{}{}".format(pre, fmt(nominal, d), fmt(up, d), fmt(down, d), unit)
    if nominal is not None and usl is not None:
        return "{}{} +{} / −0{}".format(pre, fmt(nominal, d), fmt(usl - nominal, d), unit)
    if nominal is not None and lsl is not None:
        return "{}{} +0 / −{}{}".format(pre, fmt(nominal, d), fmt(nominal - lsl, d), unit)
    if lsl is not None and usl is not None:
        return "{}{} à {}{}".format(pre, fmt(lsl, d), fmt(usl, d), unit)
    if usl is not None:
        return "{}≤ {}{}".format(pre, fmt(usl, d), unit)
    if lsl is not None:
        return "{}{}{} min.".format(pre, fmt(lsl, d), unit)
    if nominal is not None:
        return "{}{}{}".format(pre, fmt(nominal, d), unit)
    return c.get("spec_text") or ""


def has_spec(c):
    return any(c.get(k) is not None for k in ("nominal", "lsl", "usl")) or bool((c.get("spec_text") or "").strip())


def cpk_required(c, code, cust):
    """The Cpk this characteristic must reach (None: a 100 % test or a design check, or no class)."""
    if c.get("control") != "spc":
        return None
    if c.get("cpk_required") is not None:
        return c["cpk_required"]
    if code in ("CC", "SC"):
        return cust.get(code.lower() + "_cpk")
    return None


def missing(c):
    """What a reviewer would still ask: the part that carries it, its specification, its drawing (a product
    characteristic), its test."""
    out = []
    if not c.get("part_id"):
        out.append("pièce")
    if not has_spec(c):
        out.append("spécification")
    if c.get("nature") == "product" and not (c.get("drawing") or "").strip():
        out.append("plan")
    if not c.get("test_id") and c.get("control") != "spc":
        out.append("essai")
    return out


def status(c, code):
    """(key, label) of the summary: incomplete first, then what the control asks for (measures: increment 6)."""
    if code not in ("CC", "SC"):
        return "unclassed", STATUS["unclassed"]
    gaps = missing(c)
    if gaps:
        return "incomplete", STATUS["incomplete"] + " : " + ", ".join(gaps)
    key = {"spc": "study", "test100": "test100", "design": "design"}.get(c.get("control"), "study")
    return key, STATUS[key]
