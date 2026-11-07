"""FR | EN display dictionary (0.60.66, D-O-073): list the French labels of static/js that static/i18n/en_*.json
does not translate yet, and merge a file of new translations.

    python tools/i18n_missing.py                 # prints the missing labels as a JSON list
    python tools/i18n_missing.py --merge new.json  # {"French": "English", ...} into the six dictionary files

A label is a string literal of the screens' code that looks like French text (an accent, or a capital and a space), or
a French string constant of the server (modules/, core/) that reaches the screen.
Fragments of a sentence built with variables are listed too: they are translated when they show alone on screen.
"""
import ast
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FILES = [BASE / "static" / "i18n" / "en_{}.json".format(n) for n in range(1, 7)]


def dictionary():
    out = {}
    for path in FILES:
        if path.is_file():
            out.update(json.loads(path.read_text(encoding="utf-8")))
    return out


def literals(text):
    """The string literals of a JavaScript file, read like the browser does (quotes, escapes, comments, regexes skipped
    roughly): a French apostrophe inside "…" never starts a string."""
    out, i, n, last = [], 0, len(text), -1
    while i < n:
        c = text[i]
        if c == "/" and text[i + 1:i + 2] == "/":
            i = text.find("\n", i)
            i = n if i < 0 else i
        elif c == "/" and text[i + 1:i + 2] == "*":
            i = text.find("*/", i + 2)
            i = n if i < 0 else i + 2
        elif c in "\"'`":
            j, buf = i + 1, []
            while j < n and text[j] != c:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == "\n" and c != "`":
                    break
                buf.append(text[j])
                j += 1
            if c != "`" or "${" not in "".join(buf):
                value = "".join(buf)
                if out and re.fullmatch(r"\s*\+\s*", text[last:i]):  # "a, " + "b": the screen shows one sentence
                    out[-1] += value
                else:
                    out.append(value)
            i = j + 1
            last = i
        else:
            i += 1
    return out


def labels():
    found = set()
    for path in sorted((BASE / "static" / "js").rglob("*.js")):
        if path.name.startswith("i18n"):
            continue
        for value in literals(path.read_text(encoding="utf-8")):
            if not 2 <= len(value) <= 1500:
                continue
            if re.search(r"[(){};=]|=>|\\n|^#|^/|^\.", value) or not re.search(r"[A-Za-zÀ-ÿ]{3}", value):
                continue
            if re.search(r"[À-ÿ]", value) or (value[:1].isupper() and " " in value):
                found.add(value)
    return found


def server_labels():
    """0.60.67: what the server sends to the screen (status labels, categories, method tips, error messages): the French
    string constants of modules/ and core/, docstrings, SQL and format templates left out."""
    found = set()
    for path in sorted(list((BASE / "modules").rglob("*.py")) + list((BASE / "core").rglob("*.py"))):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        docs = {ast.get_docstring(n, clean=False) for n in ast.walk(tree)
                if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            value = node.value
            if value in docs or "{" in value or not 3 <= len(value) <= 400 or re.search(r"SELECT |INSERT |UPDATE |CREATE |DELETE ", value):
                continue
            if re.search(r"[À-ÿ]", value) or (value[:1].isupper() and re.search(r"\b(le|la|les|des|du|et|une|pour)\b", value)):
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
    missing = sorted(v for v in labels() | server_labels() if v not in known)
    print(json.dumps(missing, ensure_ascii=False, indent=0))
    print("{} missing".format(len(missing)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
