"""Ratings of the DFMEA (0.60.15, D-O-027): Severity, Occurrence, Detection on 1-10, the RPN and the Action Priority.

RPN = S x O x D (1-1000), the classic score, kept side by side with the AP for comparison and for training.
AP (Action Priority, AIAG-VDA FMEA Handbook, 2019) replaces the RPN: High / Medium / Low, read in a table by
severity band, then occurrence band, then detection band -- severity first, so a severe effect is never hidden by a low
occurrence or a good detection, as an RPN product can do. The table below follows the DFMEA table of the handbook;
check it against your copy of the handbook before a formal review (the handbook is the reference, not this file).
The descriptions of the scales are short teaching paraphrases, not the handbook's text.
"""

S_BANDS = ((9, 10), (7, 8), (4, 6), (2, 3), (1, 1))
O_BANDS = ((8, 10), (6, 7), (4, 5), (2, 3), (1, 1))
D_BANDS = ((7, 10), (5, 6), (2, 4), (1, 1))
# AP[s band][o band] = AP for each detection band (D 7-10, 5-6, 2-4, 1)
AP = {
    (9, 10): {(8, 10): "HHHH", (6, 7): "HHHH", (4, 5): "HHHM", (2, 3): "HMLL", (1, 1): "LLLL"},
    (7, 8): {(8, 10): "HHHH", (6, 7): "HHHM", (4, 5): "HMMM", (2, 3): "MMLL", (1, 1): "LLLL"},
    (4, 6): {(8, 10): "HHMM", (6, 7): "MMML", (4, 5): "MLLL", (2, 3): "LLLL", (1, 1): "LLLL"},
    (2, 3): {(8, 10): "MMLL", (6, 7): "LLLL", (4, 5): "LLLL", (2, 3): "LLLL", (1, 1): "LLLL"},
    (1, 1): {(8, 10): "LLLL", (6, 7): "LLLL", (4, 5): "LLLL", (2, 3): "LLLL", (1, 1): "LLLL"},
}
AP_LABELS = {"H": "High", "M": "Medium", "L": "Low"}
AP_MEANING = {
    "H": "Action obligatoire : améliorer la prévention ou la détection, ou justifier pourquoi les contrôles actuels suffisent.",
    "M": "Action recommandée : améliorer la prévention ou la détection, ou documenter pourquoi on ne le fait pas.",
    "L": "Action possible : on peut améliorer, sans obligation.",
}

SCALES = {
    "severity": [
        ((9, 10), "Sécurité de l'utilisateur ou non-conformité à une norme ou à la loi (10 : sans avertissement)."),
        ((7, 8), "Perte (8) ou dégradation (7) d'une fonction principale du produit."),
        ((4, 6), "Perte (6) ou dégradation (5) d'une fonction secondaire ; gêne marquée (4)."),
        ((2, 3), "Aspect, bruit ou confort : remarqué par beaucoup (3) ou par peu (2) d'utilisateurs."),
        ((1, 1), "Aucun effet perceptible."),
    ],
    "occurrence": [
        ((8, 10), "Très élevée : conception nouvelle sans expérience ni prévention efficace."),
        ((6, 7), "Élevée : conception nouvelle ou modifiée, prévention peu éprouvée."),
        ((4, 5), "Moyenne : conception proche d'une conception connue, prévention partiellement éprouvée."),
        ((2, 3), "Faible : conception éprouvée, prévention efficace (règles de conception, normes, calculs validés)."),
        ((1, 1), "Extrêmement faible : la défaillance est éliminée par la conception."),
    ],
    "detection": [
        ((7, 10), "Faible à nulle : aucune méthode d'essai, ou une méthode non éprouvée (10 : aucune)."),
        ((5, 6), "Moyenne : méthode d'essai éprouvée ailleurs, à valider pour ce produit."),
        ((2, 4), "Élevée : méthode d'essai éprouvée, faite assez tôt pour corriger la conception."),
        ((1, 1), "Très élevée : la défaillance ne peut pas se produire, ou elle est toujours détectée (analyse, simulation)."),
    ],
}


def band(value, bands):
    for low, high in bands:
        if low <= value <= high:
            return (low, high)
    raise ValueError(value)


def action_priority(s, o, d):
    """'H' | 'M' | 'L', or '' when a rating is missing."""
    if not (s and o and d):
        return ""
    row = AP[band(s, S_BANDS)][band(o, O_BANDS)]
    return row[D_BANDS.index(band(d, D_BANDS))]


def rpn(s, o, d):
    return s * o * d if s and o and d else None


def legend():
    """The AP table and the scales, for the legend page (training)."""
    return {"s_bands": S_BANDS, "o_bands": O_BANDS, "d_bands": D_BANDS,
            "table": [{"s": list(s), "rows": [{"o": list(o), "ap": list(AP[s][o])} for o in O_BANDS]} for s in S_BANDS],
            "labels": AP_LABELS, "meaning": AP_MEANING,
            "scales": {k: [{"range": list(r), "text": t} for r, t in v] for k, v in SCALES.items()}}
