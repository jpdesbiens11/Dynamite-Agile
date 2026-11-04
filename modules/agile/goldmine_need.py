"""Maturity of a Goldmine need (D-B-086, generic since 0.60.01).

One field of agile_requirements (migration agile 14), used by stakeholder needs:
- need_status: maturity of a need -- a team assumption, confirmed by the client, or contractual. It is what
  justifies, in an extract, that a requirement answers a real client need (or a documented assumption).
Codes are stable; labels are English technical terms (D-B-085).
"""
from core.errors import ApiError

NEED_STATUS = {"assumption": "Assumption", "confirmed": "Customer Confirmed", "contractual": "Contractual"}
FIELDS = ("need_status",)
FIELD_LABELS = {"need_status": "Need Status"}
TEXT_LIMITS = {}
CSV_ALIASES = {
    "need_status": ["need status", "statut du besoin", "maturite", "maturity", "hypothese ou ferme"],
}
LABEL_TO_CODE = {
    "need_status": dict({v: k for k, v in NEED_STATUS.items()}, **{"Hypothèse": "assumption", "Confirmé": "confirmed",
                                                                    "Contractuel": "contractual", "Firm": "confirmed"}),
}


def clean(field, value, kind):
    """Normalised value of the field, or ApiError with the fix (D-A-031)."""
    if value and value not in NEED_STATUS:
        raise ApiError(400, "Need Status « {} » inconnu. Valeurs acceptées : {}, ou vide.".format(
            value, ", ".join(NEED_STATUS.values())))
    return value if kind == "need" else ""  # a requirement has no maturity of its own: its needs carry it


def labels():
    return {"need_status": NEED_STATUS}
