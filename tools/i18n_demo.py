"""FR | EN of the demo content (0.60.67, D-O-073): the texts of the Rover and of the reference library, as a fresh
installation writes them in its database, for the display dictionary static/i18n/demo_en_*.json.

    python tools/i18n_demo.py DATA_DIR                    # prints the texts not translated yet (JSON list)
    python tools/i18n_demo.py DATA_DIR --merge new.json   # {"French": "English"} into the six demo files

DATA_DIR is the data folder of a fresh development server (python app_dynamite_agile.py --dev-admin --data-dir DIR),
so only the demo and the reference content are in it. Every text column is read, and the JSON ones (wiki pages,
Storyline) text node by text node, which is what the screen shows.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FILES = [BASE / "static" / "i18n" / "demo_en_{}.json".format(n) for n in range(1, 7)]
SKIP_TABLE = re.compile(r"^(sqlite_|audit|sessions|users|user_prefs|app_settings|revisions|core_|search|privacy|exports|login|"
                        r"guest|schema|migrations|baselines|restore|update)")
SKIP_COLUMN = {"created_at", "updated_at", "key", "status", "username", "password_hash", "icon_key", "color", "code", "test_id",
               "sent_at", "closed_at", "decided_at", "resolved_at", "due_date", "start_date", "work_date", "week_start", "date"}


def texts(db_path):
    found = set()

    def add(value):
        if not isinstance(value, str):
            return
        value = value.strip()
        if len(value) < 2 or len(value) > 1500 or not re.search(r"[A-Za-zÀ-ÿ]{3}", value):
            return
        if " " in value or re.search(r"[À-ÿ]", value):
            found.add(value)

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and k not in ("type", "kind", "href", "src", "p", "icon"):
                    add(v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
        if SKIP_TABLE.match(table):
            continue
        cols = [c[1] for c in con.execute("PRAGMA table_info({})".format(table)) if c[2].upper() in ("TEXT", "") and c[1] not in SKIP_COLUMN]
        if not cols:
            continue
        for row in con.execute("SELECT {} FROM {}".format(", ".join(cols), table)):
            for col in cols:
                value = row[col]
                if isinstance(value, str) and value[:1] in "{[":
                    try:
                        walk(json.loads(value))
                        continue
                    except ValueError:
                        pass
                add(value)
    return found


def known():
    out = {}
    for path in FILES:
        if path.is_file():
            out.update(json.loads(path.read_text(encoding="utf-8")))
    return out


def write(entries):
    keys = sorted(entries)
    size = (len(keys) + len(FILES) - 1) // len(FILES)
    for n, path in enumerate(FILES):
        path.write_text(json.dumps({k: entries[k] for k in keys[n * size:(n + 1) * size]}, ensure_ascii=False, indent=0,
                                   sort_keys=True), encoding="utf-8")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    have = known()
    if argv[1:2] == ["--merge"]:
        new = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        have.update({k: v for k, v in new.items() if isinstance(v, str) and v.strip() and v != k})
        write(have)
        print("{} entries".format(len(have)))
        return 0
    missing = sorted(t for t in texts(Path(argv[0]) / "dynamite_agile.db") if t not in have)
    print(json.dumps(missing, ensure_ascii=False, indent=0))
    print("{} missing".format(len(missing)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
