"""Set settings in data/config.json from the command line (0.60.10, D-O-022) -- used by deploy/install.ps1.

    python tools/write_config.py --data-dir C:\\DynamiteAgile\\data host=0.0.0.0 port=443 dev_mode=false

Each value is read as JSON when it can be (443, false, "x", [..]), as text otherwise. The other settings are kept.
The file is written in UTF-8 without BOM.
"""
import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description="Set settings in data/config.json.")
    parser.add_argument("--data-dir", type=Path, default=BASE / "data")
    parser.add_argument("settings", nargs="+", help="key=value")
    args = parser.parse_args(argv)
    path = args.data_dir / "config.json"
    cfg = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    for item in args.settings:
        key, sep, raw = item.partition("=")
        if not sep or not key.strip():
            raise SystemExit("Réglage « {} » illisible. Correctif : écrivez clé=valeur, ex. port=443.".format(item))
        try:
            cfg[key.strip()] = json.loads(raw)
        except ValueError:
            cfg[key.strip()] = raw
    args.data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    print("{} : {}".format(path, ", ".join(sorted(k.partition("=")[0] for k in args.settings))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
