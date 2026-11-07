"""FR | EN display dictionary (0.60.66, D-O-073): list the French labels of static/js that static/i18n/en_*.json
does not translate yet, and merge a file of new translations.

    python tools/i18n_missing.py                 # prints the missing labels as a JSON list
    python tools/i18n_missing.py --merge new.json  # {"French": "English", ...} into the six dictionary files

A label is a string literal of the screens' code that looks like French text (an accent, or a capital and a space).
Fragments of a sentence built with variables are listed too: they are translated when they show alone on screen.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FILES = [BASE / "static" / "i18n" / "en_{}.json".format(n) for n in range(1, 7)]
LITERAL = re.compile(r'"((?:[^"\\\n]|\\.){2,160})"|\'((?:[^\'\\\n]|\\.){2,160})\'')


def dictionary():
    out = {}
    for path in FILES:
        if path.is_file():
            out.update(json.loads(path.read_text(encoding="utf-8")))
    return out


def labels():
    found = set()
    for path in sorted((BASE / "static" / "js").rglob("*.js")):
        if path.name.startswith("i18n"):
            continue
        text = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
        for match in LITERAL.finditer(text):
            value = match.group(1) or match.group(2)
            if re.search(r"[(){};=]|=>|\\n|^#|^/|^\.", value) or not re.search(r"[A-Za-zÀ-ÿ]{3}", value):
                continue
            if re.search(r"[À-ÿ]", value) or (value[:1].isupper() and " " in value):
                found.add(value)
    return found


def write(entries):
    keys = sorted(entries)
    size = (len(keys) + len(FILES) - 1) // len(FILES)
    for n, path in enumerate(FILES):
        part = {k: entries[k] for k in keys[n * size:(n + 1) * size]}
        path.write_text(json.dumps(part, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def main(argv):
    known = dictionary()
    if argv[:1] == ["--merge"]:
        new = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        known.update({k: v for k, v in new.items() if isinstance(v, str) and v.strip() and v != k})
        write(known)
        print("{} entries".format(len(known)))
        return 0
    missing = sorted(v for v in labels() if v not in known)
    print(json.dumps(missing, ensure_ascii=False, indent=0))
    print("{} missing".format(len(missing)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
