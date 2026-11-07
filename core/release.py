"""Official versions (0.60.12, D-O-024): update a deployed portal from one published version to a newer one, data kept.

Nothing leaves the server (FONDATIONS: closed network). The project publishes, on its website, one package per version
(tools/build_release.py, built by the Pages workflow): the code only, the same zip as Admin → Update (ROOT/...), plus
  docs/RELEASE.json     {format, version, date, files: {relative path: sha256}} -- every file of the package;
  docs/releases/*.json  one record per version (summary FR / EN, changes, files) -- the whole series;
  UPDATE_CHANGES.json   the changes of every version, merged (what a server older than 0.60.12 reviews).
The administrator downloads the package from the site (link in Admin → Update, with the installed version) and drops
it in Admin → Update. Here, on top of the usual checks (core/update.check): the files match the manifest (nothing
changed after the build), the review has one step per version newer than the installed one -- several versions can be
skipped and applied at once --, and the files edited by hand since the last official install are listed (they will
be replaced; the code before the update is saved, data/ is never touched). « Plus tard » leaves everything as it is:
the next package can be applied later from any older 0.60.x.
"""
import hashlib
import json
import re
from pathlib import Path

FORMAT = "dynamite-agile-release"
MANIFEST = "docs/RELEASE.json"
CHANGES = "UPDATE_CHANGES.json"  # read by the review, never written in the code (core/update._members)
RELEASES = re.compile(r"^docs/releases/(\d+\.\d+\.\d+)\.json$")
SITE = "https://dynamiteagile.ca/"
PAGES = {"fr": SITE + "versions.html", "en": SITE + "en/versions.html"}


def version_tuple(text):
    return tuple(int(x) for x in re.findall(r"\d+", text or "0")[:3])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest(version, date, contents):
    """contents: {relative path: bytes} (the manifest itself excluded)."""
    return {"format": FORMAT, "version": version, "date": date,
            "files": {rel: sha(data) for rel, data in sorted(contents.items()) if rel not in (MANIFEST, CHANGES)}}


def records(read, names):
    """[record] of docs/releases/*.json, oldest first. read(name) -> bytes."""
    out = []
    for name in names:
        if RELEASES.match(name):
            try:
                rec = json.loads(read(name).decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            if isinstance(rec, dict) and rec.get("version"):
                out.append(rec)
    return sorted(out, key=lambda r: version_tuple(r["version"]))


def verify(z, files, version):
    """(info | None, problems) for a zip: None when it carries no manifest (a package prepared with Claude)."""
    if MANIFEST not in files:
        return None, []
    try:
        man = json.loads(z.read(files[MANIFEST]).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return None, ["{} illisible ({}). Correctif : téléchargez de nouveau le paquet sur le site du projet.".format(MANIFEST, exc)]
    problems = []
    if not isinstance(man, dict) or man.get("format") != FORMAT or not isinstance(man.get("files"), dict):
        return None, ["{} : format inconnu. Correctif : téléchargez le paquet officiel sur le site du projet.".format(MANIFEST)]
    if man.get("version") != version:
        problems.append("Paquet {} mais code {} : paquet incohérent. Correctif : téléchargez-le de nouveau.".format(man.get("version"), version))
    listed = man["files"]
    altered = sorted(rel for rel in files if rel != MANIFEST and listed.get(rel) != sha(z.read(files[rel])))
    missing = sorted(rel for rel in listed if rel not in files)
    if altered:
        problems.append("{} fichier(s) différent(s) du paquet publié (ex. {}) : le zip a été modifié après sa publication. "
                        "Correctif : téléchargez le paquet officiel de nouveau, sans le modifier.".format(len(altered), ", ".join(altered[:3])))
    if missing:
        problems.append("{} fichier(s) du paquet absent(s) (ex. {}). Correctif : téléchargez le paquet de nouveau.".format(
            len(missing), ", ".join(missing[:3])))
    return {"version": man.get("version"), "date": man.get("date", ""), "files": len(listed)}, problems


def series(z, files, current, target):
    """The versions this package brings: newer than `current`, up to `target`, oldest first."""
    recs = records(lambda n: z.read(files[n]), list(files))
    return [r for r in recs if version_tuple(current) < version_tuple(r["version"]) <= version_tuple(target)]


def build_steps(report, current):
    """One review step per version of the series; files no version declares go with the newest version (the package's
    integrity is checked against its manifest)."""
    touched = {f: "added" for f in report["added"]}
    touched.update({f: "changed" for f in report["changed"]})
    touched.update({f: "removed" for f in report["removed"]})
    steps, covered = [], set()
    versions = series(report["zip"], report["files"], current, report["version"])
    for rec in versions:
        files = sorted({f for ch in rec.get("changes") or [] for f in ch.get("files") or [] if f in touched and f not in covered})
        covered.update(files)
        lines = ["• " + str(ch.get("title") or "") for ch in rec.get("changes") or []]
        steps.append({"id": "v" + rec["version"], "kind": "release", "unknown": [],
                      "title": "Version {} ({}) — {}".format(rec["version"], rec.get("date", ""), (rec.get("summary") or {}).get("fr", "")),
                      "why": "\n".join(lines)[:2000], "files": [{"path": f, "state": touched[f]} for f in files]})
    rest = sorted(f for f in touched if f not in covered)
    if rest:
        if steps:
            steps[-1]["files"] += [{"path": f, "state": touched[f]} for f in rest]
            steps[-1]["why"] += "\n• Autres fichiers du paquet ({}), conformes au manifeste.".format(len(rest))
        else:
            steps.append({"id": "v" + report["version"], "kind": "release", "unknown": [], "title": "Version " + report["version"],
                          "why": "Fichiers du paquet, conformes au manifeste.", "files": [{"path": f, "state": touched[f]} for f in rest]})
    for n, step in enumerate(steps, 1):
        step.update(n=n, status="pending", seen_by=[], by=None, at=None, comment="")
    return steps, [{"version": r["version"], "date": r.get("date", ""), "summary": r.get("summary") or {}} for r in versions]


def installed(root, current):
    """The manifest of the official package installed here ({} when none, or when the code is not that version)."""
    try:
        man = json.loads((Path(root) / MANIFEST).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return man if isinstance(man, dict) and man.get("version") == current and isinstance(man.get("files"), dict) else {}


def local_changes(root, current, code_files):
    """Files edited by hand since the official install: changed or added (paths), or None when unknown."""
    man = installed(root, current)
    if not man:
        return None
    listed = man["files"]
    out = []
    for rel in code_files:
        if rel == MANIFEST:
            continue
        digest = sha((Path(root) / rel).read_bytes())
        if listed.get(rel) != digest:
            out.append(rel)
    return out


def status(root, current, lang="fr"):
    """What Admin → Update shows above the import: where to find the versions, how this portal was installed."""
    page = PAGES.get(lang, PAGES["fr"])
    return {"page": page + "#depuis=" + current, "git": (Path(root) / ".git").exists(),
            "official": bool(installed(root, current))}


def api_later(ctx):
    """« Plus tard »: the checked package is dropped, nothing changes; any later package can be applied from here."""
    from . import audit, permissions, update
    permissions.require_admin(ctx.user)
    folder, token, path = update._incoming(ctx, ctx.body.get("token"))
    for leftover in (path, Path(folder) / (token + ".review.json")):
        try:
            leftover.unlink()
        except OSError:
            pass
    audit.log_action(ctx.conn, ctx.user["id"], "update_later", "update", None, {"token": token}, ctx.ip)
    return {"ok": True}
