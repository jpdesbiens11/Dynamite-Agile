"""Sealed transfer files (core lot v0.26, D-B-094): « Données » and « Site complet » packages of Admin → Update.

A package is a zip with manifest.json (format, versions, author, SHA-256 of every other member) and SEAL.json: an
HMAC-SHA256 of manifest.json with a key derived from a passphrase (PBKDF2-HMAC-SHA256, 310 000 iterations, random
salt). Whoever does not know the passphrase cannot change one byte without the import refusing the file; the
passphrase itself is never stored, logged nor sent back. Confidentiality is the job of the medium (encrypted drive
or transfer approved by IT): the standard library has no cipher and home-made cryptography is not acceptable.

Also here: the folders of the transfers (data/updates/exports, data/updates/incoming), the one-time download of an
export and the reception of an uploaded package -- shared by core/datapack.py and core/sitemove.py.
"""
import hashlib
import hmac
import json
import re
import secrets
import time
import zipfile
from pathlib import Path

from . import APP_VERSION, db
from .errors import ApiError
from .files import RawFile

ITERATIONS = 310_000
MIN_PASSPHRASE = 12
SEAL_FILE, MANIFEST_FILE = "SEAL.json", "manifest.json"


def check_passphrase(passphrase):
    passphrase = str(passphrase or "")
    if len(passphrase) < MIN_PASSPHRASE:
        raise ApiError(400, "Phrase de passe de {} caractère(s) : {} au minimum. Correctif : choisissez une phrase longue "
                            "(par ex. 4 mots), à transmettre par un autre canal que le fichier.".format(len(passphrase), MIN_PASSPHRASE))
    return passphrase


def _key(passphrase, salt):
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, ITERATIONS)


def write(target, fmt, members, passphrase, extra):
    """Write a sealed zip to `target` (path or file object). `members`: iterable of (name, bytes)."""
    passphrase = check_passphrase(passphrase)
    hashes = {}
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for name, data in members:
            if name in hashes or name in (SEAL_FILE, MANIFEST_FILE):
                continue
            z.writestr(name, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        manifest = dict(extra, format=fmt, format_version=1, app_version=APP_VERSION, created_at=db.utc_now(), files=hashes)
        raw = json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8")
        salt = secrets.token_bytes(16)
        z.writestr(MANIFEST_FILE, raw)
        z.writestr(SEAL_FILE, json.dumps({"algorithm": "HMAC-SHA256", "kdf": "PBKDF2-HMAC-SHA256", "iterations": ITERATIONS,
                                          "salt": salt.hex(), "hmac": hmac.new(_key(passphrase, salt), raw, "sha256").hexdigest()}))
    return manifest


def open_sealed(path, passphrase, fmt, label):
    """(ZipFile, manifest) after checking the seal and every member; ApiError naming the problem otherwise."""
    passphrase = str(passphrase or "")
    try:
        z = zipfile.ZipFile(path)
        raw = z.read(MANIFEST_FILE)
        seal = json.loads(z.read(SEAL_FILE))
        manifest = json.loads(raw)
    except (zipfile.BadZipFile, KeyError, ValueError, OSError):
        raise ApiError(400, "Ce fichier n'est pas un paquet « {} » scellé (manifest.json ou SEAL.json absent). Correctif : "
                            "choisissez le .zip produit par Admin → Update → {}.".format(label, label))
    if manifest.get("format") != fmt:
        raise ApiError(400, "Paquet de type « {} » : attendu « {} ». Correctif : importez-le dans le bon volet de Admin → "
                            "Update.".format(manifest.get("format"), fmt))
    try:
        salt = bytes.fromhex(seal["salt"])
        # 0.60.88 (D-O-094): the count comes from the file -- a forged package asking for billions would hold the server;
        # every package written here uses ITERATIONS, so only that count is accepted
        if int(seal["iterations"]) != ITERATIONS:
            raise ValueError("iterations")
        expected = hmac.new(hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, ITERATIONS),
                            raw, "sha256").hexdigest()
        good = hmac.compare_digest(expected, str(seal["hmac"]))
    except (KeyError, ValueError, TypeError):
        good = False
    if not good:
        raise ApiError(403, "Sceau invalide : phrase de passe incorrecte, ou fichier modifié depuis son export. Correctif : "
                            "vérifiez la phrase de passe auprès de la personne qui a exporté ; si elle est juste, le fichier "
                            "n'est pas digne de confiance — refaites l'export.")
    files = manifest.get("files") or {}
    names = {i.filename for i in z.infolist() if not i.is_dir()} - {SEAL_FILE, MANIFEST_FILE}
    extra = sorted(names - set(files))
    if extra:
        raise ApiError(403, "Fichier(s) ajouté(s) après le scellé : {}. Le paquet est refusé.".format(", ".join(extra[:5])))
    for name, digest in files.items():
        if name not in names:
            raise ApiError(403, "« {} » manque dans le paquet. Correctif : refaites l'export.".format(name))
        h = hashlib.sha256()
        with z.open(name) as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != digest:
            raise ApiError(403, "« {} » a été modifié depuis l'export (empreinte SHA-256 différente). Le paquet est refusé.".format(name))
    return z, manifest


# --------------------------------------------------------------------------
# Folders, one-time download, reception
# --------------------------------------------------------------------------
def folder(ctx, name):
    path = Path(ctx.data_dir) / "updates" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


EXPORT_TTL, INCOMING_TTL = 3600, 7 * 86400  # an export not downloaded within an hour, an import abandoned for a week


def purge(ctx):
    """Delete forgotten packages: they hold the data of the site."""
    now = time.time()
    for name, ttl in (("exports", EXPORT_TTL), ("incoming", INCOMING_TTL)):
        for f in folder(ctx, name).iterdir():
            try:
                if f.is_file() and now - f.stat().st_mtime > ttl:
                    f.unlink()
            except OSError:
                pass


def new_token():
    return secrets.token_hex(16)


def clean_token(token):
    token = re.sub(r"[^a-f0-9]", "", str(token or ""))[:32]
    if len(token) != 32:
        raise ApiError(404, "Référence de transfert invalide.")
    return token


def download_once(ctx, prefix):
    """The export file <token>.<prefix>.zip, deleted once sent (it holds the data of the site)."""
    token = clean_token(ctx.params.get("token"))
    matches = sorted(folder(ctx, "exports").glob("{}.{}.*.zip".format(token, prefix)))
    if not matches:
        raise ApiError(404, "Export introuvable ou déjà téléchargé. Correctif : relancez l'export.")
    path = matches[0]
    data = path.read_bytes()
    path.unlink()
    return RawFile(data, path.name.split(".", 2)[2], "application/zip")


def receive(ctx, prefix):
    """Store an uploaded package (not yet opened) and return its token."""
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le .zip exporté.")
    purge(ctx)
    token = new_token()
    (folder(ctx, "incoming") / "{}.{}.zip".format(token, prefix)).write_bytes(upload.data)
    return token


def incoming(ctx, token, prefix):
    path = folder(ctx, "incoming") / "{}.{}.zip".format(clean_token(token), prefix)
    if not path.exists():
        raise ApiError(404, "Fichier reçu introuvable (expiré, appliqué ou abandonné). Correctif : importez-le de nouveau.")
    return path
