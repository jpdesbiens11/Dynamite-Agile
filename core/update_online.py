"""Online update (0.60.36, D-O-045): for a server that is on the Internet, an administrator may let the portal look at
the project's website itself, see what each newer version brings, approve, and follow the installation live.

Off by default -- the platform rule stays « no outbound call »; switching it on is an administrator's choice,
journalled (⚙ Admin → Update et sauvegardes → Framework). When on, and only when an administrator asks:
  check   GET <site>/updates/versions.json (the listing the website publishes, tools/build_release.py): the newer
          versions with their summary and changes -- enough to judge whether the update is worth it;
  start   every newer version read and ticked (D-B-094: never a one-click update), then a background job:
          download the package (progress by bytes) -> SHA-256 of the listing -> the usual checks of an official package
          (manifest, structure, syntax: core/update.check) -> code backup and restore point of the data -> new code
          written (data/ never touched) -> restart; the page follows /progress (percent, step, live lines) and,
          after the restart, /api/about until the new version answers.
The site is release.SITE, or config « release_site » (a mirror, a test server). HTTPS with certificate checks.
"""
import datetime as dt
import hashlib
import json
import re
import threading
import urllib.request
from pathlib import Path
from types import SimpleNamespace

from . import APP_VERSION, audit, db, permissions, release
from . import update as U
from .errors import ApiError

CHUNK = 64 * 1024
TIMEOUT = 20
MAX_PACKAGE = 100 * 1024 * 1024  # 0.60.83 (D-O-089): today's package is under 3 MB
PACKAGE_RE = re.compile(r"dynamite-agile-\d+\.\d+\.\d+\.zip")
SHA_RE = re.compile(r"[0-9a-f]{64}")
_lock = threading.Lock()
_job = {"state": "idle", "percent": 0, "step": "", "lines": [], "version": "", "error": "", "started_at": ""}


def _file(ctx):
    return Path(ctx.data_dir) / "updates" / "online.json"


def _settings(ctx):
    try:
        return json.loads(_file(ctx).read_text("utf-8"))
    except (OSError, ValueError):
        return {"enabled": False}


def _save(ctx, settings):
    _file(ctx).parent.mkdir(parents=True, exist_ok=True)
    _file(ctx).write_text(json.dumps(settings, ensure_ascii=False, indent=1), "utf-8")


def _site(cfg):
    return str(cfg.get("release_site") or release.SITE).rstrip("/") + "/"


LOOPBACK = re.compile(r"http://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?/")


def _https_only(url):
    """0.60.97 (D-O-103): the code to install comes over HTTPS only -- a « release_site » in http://, or a redirect to
    http://, is refused (plain HTTP only on this computer's loopback, for the tests)."""
    if not (url.startswith("https://") or LOOPBACK.match(url)):
        raise ValueError("adresse refusée, HTTPS seulement : {}. Correctif : « release_site » en https:// dans "
                         "data/config.json, ou vide pour le site officiel".format(url[:120]))
    return url


class _HttpsRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, _https_only(newurl))


_OPENER = urllib.request.build_opener(_HttpsRedirects)  # the default HTTPS handler checks the certificate


def _open(url):
    req = urllib.request.Request(_https_only(url), headers={"User-Agent": "DynamiteAgile/{} (update check)".format(APP_VERSION)})
    return _OPENER.open(req, timeout=TIMEOUT)


def _newer(listing):
    current = release.version_tuple(APP_VERSION)
    return [v for v in listing.get("versions") or [] if release.version_tuple(v.get("version")) > current]


def _state(ctx):
    s = _settings(ctx)
    listing = s.get("listing") or {}
    with _lock:
        job = dict(_job, lines=list(_job["lines"][-40:]))
    return {"enabled": bool(s.get("enabled")), "current": APP_VERSION, "site": _site(ctx.config), "last_check": s.get("last_check", ""),
            "latest": listing.get("latest", ""), "date": listing.get("date", ""), "bytes": listing.get("bytes", 0),
            "sha256": listing.get("sha256", ""), "newer": _newer(listing) if listing else [], "job": job}


def api_get(ctx):
    permissions.require_admin(ctx.user)
    return _state(ctx)


def api_set(ctx):
    permissions.require_admin(ctx.user)
    s = _settings(ctx)
    s["enabled"] = bool(ctx.body.get("enabled"))
    _save(ctx, s)
    audit.log_action(ctx.conn, ctx.user["id"], "update_online_" + ("enabled" if s["enabled"] else "disabled"), "update", None,
                     {"site": _site(ctx.config)}, ctx.ip)
    return _state(ctx)


def api_check(ctx):
    permissions.require_admin(ctx.user)
    s = _settings(ctx)
    if not s.get("enabled"):
        raise ApiError(409, "La vérification en ligne est coupée. Correctif : activez « Vérifier les mises à jour en ligne » (ce serveur doit avoir accès à Internet).")
    url = _site(ctx.config) + "updates/versions.json"
    try:
        with _open(url) as r:
            listing = json.loads(r.read(2 * 1024 * 1024).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 -- the message names the cause and the fix
        raise ApiError(502, "Le site des versions ne répond pas ({}) : {}. Correctif : vérifiez l'accès Internet du serveur, ou "
                            "téléchargez le paquet à la main (Voir les versions publiées).".format(url, exc))
    if not isinstance(listing, dict) or not listing.get("latest") or not listing.get("package"):
        raise ApiError(502, "Réponse inattendue du site des versions ({}). Correctif : réessayez plus tard.".format(url))
    # 0.60.83 (D-O-089): the fingerprint and the size are required (the package was installed unchecked without them)
    size = listing.get("bytes")
    if (not PACKAGE_RE.fullmatch(str(listing["package"])) or not SHA_RE.fullmatch(str(listing.get("sha256") or ""))
            or not isinstance(size, int) or not 0 < size <= MAX_PACKAGE):
        raise ApiError(502, "Liste des versions incomplète ({}) : nom du paquet, taille ou empreinte SHA-256 absent ou invalide ; "
                            "rien n'est installé sans eux. Correctif : réessayez plus tard, ou installez le paquet à la main."
                            .format(url))
    s.update(listing=listing, last_check=dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    _save(ctx, s)
    audit.log_action(ctx.conn, ctx.user["id"], "update_online_checked", "update", None,
                     {"latest": listing["latest"], "newer": len(_newer(listing))}, ctx.ip)
    return _state(ctx)


def _say(step=None, percent=None, line=None, **extra):
    with _lock:
        if step is not None:
            _job["step"] = step
        if percent is not None:
            _job["percent"] = max(0, min(100, int(percent)))
        if line:
            _job["lines"].append("{} · {}".format(dt.datetime.now().strftime("%H:%M:%S"), line))
        _job.update(extra)


def _run(user, cfg, data_dir, ip, listing):
    url = _site(cfg) + "updates/" + listing["package"]
    try:
        _say("Téléchargement du paquet", 2, "Téléchargement de {} ({} Ko)".format(listing["package"], int(listing.get("bytes", 0)) // 1024))
        parts, got = [], 0
        total = int(listing["bytes"])
        with _open(url) as r:
            while True:
                chunk = r.read(CHUNK)
                if not chunk:
                    break
                parts.append(chunk)
                got += len(chunk)
                if got > total:  # 0.60.83 (D-O-089): never more than the size published
                    raise RuntimeError("le paquet dépasse la taille publiée ({} Ko) : rien n'a été modifié.".format(total // 1024))
                if total:
                    _say(percent=2 + 58 * got / total)
        data = b"".join(parts)
        _say("Vérification de l'empreinte", 62, "Reçu : {} Ko".format(len(data) // 1024))
        digest = hashlib.sha256(data).hexdigest()
        if digest != listing["sha256"]:
            raise RuntimeError("l'empreinte SHA-256 du paquet ({}…) n'est pas celle publiée ({}…) : rien n'a été modifié.".format(
                digest[:12], listing["sha256"][:12]))
        _say(None, 66, "Empreinte SHA-256 conforme : " + digest[:16] + "…")
        _say("Contrôles du paquet officiel", 70, "Manifeste, structure, syntaxe de chaque fichier…")
        with db.connect() as conn:
            ctx = SimpleNamespace(conn=conn, user=user, config=cfg, data_dir=data_dir, ip=ip, query={}, body={})
            report = U.check(U._cfg_root(ctx), data)
            if report["problems"]:
                raise RuntimeError("paquet refusé : " + " | ".join(report["problems"][:5]))
            _say(None, 78, "Paquet {} conforme : {} fichier(s) ajouté(s), {} modifié(s), {} retiré(s)".format(
                report["version"], len(report["added"]), len(report["changed"]), len(report["removed"])))
            _say("Sauvegarde du code et des données, puis écriture du nouveau code", 82,
                 "Copie du code actuel et point de restauration des données…")
            result = U._apply(ctx, data, "applied")
        _say(None, 94, "Nouveau code écrit ; copie de l'ancien : " + result["backup"])
        if result.get("restarting"):
            _say("Redémarrage du serveur", 96, "Redémarrage… la page attend la nouvelle version.", state="restarting")
        else:
            _say("Terminé", 100, "Mise à jour appliquée (redémarrez le service pour charger le nouveau code).", state="done")
    except Exception as exc:  # noqa: BLE001
        _say("Arrêtée", None, "Erreur : {}".format(exc), state="error", error=str(exc))


def api_start(ctx):
    permissions.require_admin(ctx.user)
    s = _settings(ctx)
    listing = s.get("listing") or {}
    if not s.get("enabled") or not listing:
        raise ApiError(409, "Vérifiez d'abord en ligne (bouton « Vérifier maintenant »).")
    newer = [v["version"] for v in _newer(listing)]
    if not newer:
        raise ApiError(409, "Ce portail est déjà à jour ({}).".format(APP_VERSION))
    read = {str(v) for v in ctx.body.get("read") or []}
    missing = [v for v in newer if v not in read]
    if missing:  # D-B-094: every version read before the update, never one click
        raise ApiError(400, "Version(s) pas encore lue(s) : {}. Correctif : cochez « Lu » sous chaque version.".format(", ".join(missing)))
    with _lock:
        if _job["state"] == "running":
            raise ApiError(409, "Une mise à jour est déjà en cours.")
        _job.update(state="running", percent=0, step="Préparation", lines=[], version=listing["latest"], error="",
                    started_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    audit.log_action(ctx.conn, ctx.user["id"], "update_online_started", "update", None,
                     {"from": APP_VERSION, "to": listing["latest"], "versions": newer}, ctx.ip)
    user = {k: ctx.user[k] for k in ctx.user.keys()} if hasattr(ctx.user, "keys") else dict(ctx.user)
    threading.Thread(target=_run, args=(user, dict(ctx.config), ctx.data_dir, ctx.ip, listing), daemon=True).start()
    return _state(ctx)


def api_progress(ctx):
    permissions.require_admin(ctx.user)
    with _lock:
        return dict(_job, lines=list(_job["lines"][-40:]))


ROUTES = [
    ("GET", r"/api/admin/update/online", api_get, "admin"),
    ("PUT", r"/api/admin/update/online", api_set, "admin"),
    ("POST", r"/api/admin/update/online/check", api_check, "admin"),
    ("POST", r"/api/admin/update/online/start", api_start, "admin"),
    ("GET", r"/api/admin/update/online/progress", api_progress, "admin"),
]
