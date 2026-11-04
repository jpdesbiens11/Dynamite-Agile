"""Official package of the current version (0.60.12, D-O-024), for the « Mises à jour » page of the website.

    python3 tools/build_release.py [--out site/updates]

Writes, in --out (never in git: built by .github/workflows/pages.yml at each publication):
  dynamite-agile-<version>.zip   the code only, same zip as Admin → Update (Dynamite_Agile/...), with
                                 docs/RELEASE.json (sha256 of every file) and UPDATE_CHANGES.json (every version merged,
                                 so that a portal older than 0.60.12 can review it too);
  versions.json                  the series (newest first), the package name, its size and its SHA-256 -- read by the page.
Needs docs/releases/<version>.json for the current version (summary FR / EN and changes). The zip is reproducible
(sorted entries, the date of the version as timestamp).
"""
import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from core import APP_VERSION, release, update  # noqa: E402


def merged_changes(recs):
    out = []
    for rec in recs:
        for ch in rec.get("changes") or []:
            out.append(dict(ch, id="{}-{}".format(rec["version"], ch.get("id") or "C")))
    return {"changes": out}


def build(root=BASE, version=APP_VERSION):
    files = [rel for rel in update.code_files(root) if rel not in (release.MANIFEST, "UPDATE_CHANGES.json")]
    recs = release.records(lambda n: (root / n).read_bytes(), files)
    current = next((r for r in recs if r["version"] == version), None)
    if current is None:
        raise SystemExit("docs/releases/{}.json absent. Correctif : écrivez le résumé de la version (FR / EN) et ses "
                         "changements avant de publier.".format(version))
    date = current.get("date") or "2026-01-01"
    contents = {rel: (root / rel).read_bytes() for rel in files}
    contents["UPDATE_CHANGES.json"] = json.dumps(merged_changes(recs), ensure_ascii=False, indent=1).encode("utf-8")
    man = release.manifest(version, date, contents)
    contents[release.MANIFEST] = json.dumps(man, ensure_ascii=False, indent=1).encode("utf-8")
    stamp = tuple(int(x) for x in date.split("-")) + (12, 0, 0)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(contents):
            info = zipfile.ZipInfo(update.ROOT + "/" + rel, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, contents[rel])
    data = buf.getvalue()
    listing = {"latest": version, "package": "dynamite-agile-{}.zip".format(version), "bytes": len(data),
               "sha256": hashlib.sha256(data).hexdigest(), "date": date,
               "versions": [{"version": r["version"], "date": r.get("date", ""), "summary": r.get("summary") or {},
                             "changes": [str(c.get("title") or "") for c in r.get("changes") or []]} for r in reversed(recs)]}
    return data, listing


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the official package of the current version.")
    parser.add_argument("--out", type=Path, default=BASE / "site" / "updates")
    args = parser.parse_args(argv)
    data, listing = build()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / listing["package"]).write_bytes(data)
    (args.out / "versions.json").write_text(json.dumps(listing, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print("{} ({} Ko) · SHA-256 {}".format(listing["package"], len(data) // 1024, listing["sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
