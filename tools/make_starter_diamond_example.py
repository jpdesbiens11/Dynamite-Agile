"""Writes the "diamond" object of deploy/starter_exemples/lampe_bureau.json from the Diamond example of the desk lamp
(modules/diamond/example*.py), so the two never drift apart (0.60.22, D-O-032).

    python3 tools/make_starter_diamond_example.py
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from modules.diamond import example, example_dfmea, example_parts, example_risks, example_structure  # noqa: E402

TARGET = BASE / "deploy" / "starter_exemples" / "lampe_bureau.json"
KEY_TESTS = {"Chaleur mal dissipée": "ESSAI-3", "Contact thermique insuffisant": "ESSAI-3", "Scintillement à faible intensité": "ESSAI-2",
             "Commande perdue": "ESSAI-5", "Surface trop chaude": "ESSAI-3", "La lampe bascule": "ESSAI-6"}


def build():
    keys = {key: "F{}".format(n) for n, (key, *_rest) in enumerate(example.LAMP, start=1)}
    text_ref = {row[2]: keys[row[0]] for row in example.LAMP}
    functions = []
    for key, parent, text, ftype, kano, importance, critical in example.LAMP:
        item = {"ref": keys[key], "text": text, "type": ftype, "parent": keys.get(parent)}
        if kano:
            item["kano"] = kano
        if importance:
            item["importance"] = importance
        if critical:
            item["critical"] = True
        if example.NOTES.get(key):
            item["notes"] = example.NOTES[key]
        functions.append(item)
    ports = [{"ref": "E{}".format(i + 1) if side == "in" else "S{}".format(i + 1), "side": side, "label": label, "kind": kind}
             for i, (side, label, kind) in enumerate(example_structure.PORTS)]

    def end(x):
        if isinstance(x, int):
            return "F{}".format(x)
        return next(p["ref"] for p in ports if p["label"].startswith(x))
    flows = [{"view": view, "kind": kind, "label": label, "src": end(s), "dst": end(d)}
             for view, rows in (("general", example_structure.GENERAL), ("detail", example_structure.DETAIL)) for s, d, kind, label in rows]
    parts = [{"name": n, "kind": k, "notes": notes, "functions": ["F{}".format(f) for f in fns]} for n, k, notes, fns in example_parts.PARTS]
    risks = []
    for title, cause, cons, cat, phase, p, i, resp, action, _rp, _ri, ftext, _dfmea in example_risks.LAMP:
        item = {"title": title, "cause": cause, "consequence": cons, "category": cat, "phase": phase, "probability": p, "impact": i,
                "response": resp, "action": action}
        if ftext:
            item["function"] = text_ref[ftext]
        risks.append(item)
    dfmea = [{"higher": example_dfmea.HIGHER, "focus": focus, "lower": lower, "function": text_ref[ftext], "requirement": req,
              "failure_mode": mode, "effect": effect, "severity": s, "cause": cause, "prevention": prev, "occurrence": o,
              "detection_ctrl": det, "detection": d, "action": action}
             for focus, lower, ftext, req, mode, effect, s, cause, prev, o, det, d, action, _risk in example_dfmea.LAMP]
    for row in dfmea:  # 0.60.24 (D-O-033): the key test of the lamp's tests that detects the failure
        if row["failure_mode"] in KEY_TESTS:
            row["test"] = KEY_TESTS[row["failure_mode"]]
    return {"functions": functions, "ports": ports, "flows": flows, "parts": parts, "risks": risks, "dfmea": dfmea}


def _block(diamond):
    """The "diamond" key in the hand-written style of the file: one item per line."""
    lists = []
    for name, items in diamond.items():
        lines = ",\n".join("      " + json.dumps(item, ensure_ascii=False) for item in items)
        lists.append('    "{}": [\n{}\n    ]'.format(name, lines))
    return '  "diamond": {\n' + ",\n".join(lists) + "\n  }"


def main():
    text = TARGET.read_text(encoding="utf-8")
    data = json.loads(text)
    data["diamond"] = build()
    head = text[:text.index(',\n  "diamond"')] if '"diamond"' in text else text.rstrip().rstrip("}").rstrip()
    TARGET.write_text(head + ",\n" + _block(data["diamond"]) + "\n}\n", encoding="utf-8")
    json.loads(TARGET.read_text(encoding="utf-8"))  # still valid JSON
    print("{} : {} fonctions, {} flux, {} pièces".format(TARGET.relative_to(BASE), len(data["diamond"]["functions"]),
                                                         len(data["diamond"]["flows"]), len(data["diamond"]["parts"])))


if __name__ == "__main__":
    main()
