"""HTTP layer: routing, session/CSRF checks, JSON responses, static files.

Security headers are sent on every response. The Content-Security-Policy
allows scripts, styles and images from this server only, so the browser
itself refuses to contact any external host.
"""
import hmac
import json
import logging
import os
import re
import ssl
import sys
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from . import access_rules, admin, auth, backup, bot, bot_admin, update_online, proxy, static_cache, baseline_view, baselines, dashboard, datapack, db, devshare, members, mentions, modules, objectives, platform_config, prefs, profile, restorepoints, reviews, team, search, session_api, sitemove, spacecard, spacecopy, stamp, starter_apply, tls, ui_audit, update
from .errors import ApiError

# D-B-058: no write without the person's 3-letter traceability key, except to set it (and privacy events).
INITIALS_FREE = re.compile(r"/api/(me/prefs|privacy/event|logout|new/seen)")
INITIALS_MESSAGE = ("INITIALES_REQUISES: définissez d'abord votre clé de traçabilité de 3 lettres (Paramètres → "
                    "Mes initiales). Correctif : saisissez-la, puis refaites votre action.")
from .files import RawFile
from .uploads import Upload

log = logging.getLogger("dynamite_agile.http")

MAX_JSON_BYTES = 2 * 1024 * 1024
BODY_METHODS = ("POST", "PUT", "PATCH")

# Explicit types: on Windows, mimetypes reads the registry and can return
# text/plain for .js, which the browser then refuses to execute.
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",  # lot v0.15: example files offered for download
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".wasm": "application/wasm",  # core lot v0.32 (D-B-114): the STEP reader (OpenCascade compiled to WebAssembly)
    ".stp": "model/step",  # core lot v0.32: STEP models (no sample left in the platform since 0.50.14)
    ".txt": "text/plain; charset=utf-8",  # core lot v0.32: licence texts of static/vendor/
    ".woff2": "font/woff2",  # 0.60.32 (D-O-040): the letters of the logo, served from static/fonts/
}

# Core lot v0.32 (D-B-114): a background worker (static/**/<name>_worker.js) gets its OWN policy, stricter than the
# page on the network and the only place where WebAssembly may be compiled: no network at all (the page hands it the
# .wasm bytes), scripts from this server only, never eval (the vendored reader is patched, static/vendor/README.md).
# The page itself keeps SECURITY_HEADERS unchanged.
WORKER_SUFFIX = "_worker.js"
WORKER_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'none'; base-uri 'none'",
}
# Core lot v0.32: third-party libraries live in versioned folders (static/vendor/<name>-<version>/): a new version is
# a new path, so the browser may keep them (the reader alone is 7.6 MB, too heavy to download at every visit).
VENDOR_PREFIX = "vendor/"

# Lot noyau v0.15 (D-B-073): self-contained offline tools (one HTML file with inline scripts and styles, e.g. the
# showcase page) live in static/apps/<name>/. They keep their own code as is, so they get their own policy: inline
# code allowed, but NO network at all (connect-src 'none', nothing external) and a CSP sandbox without
# allow-same-origin -- the page runs in an opaque origin and can never read the session cookie or call /api/.
APP_PREFIX = "apps/"
APP_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline'; "
        "img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; base-uri 'none'; "
        "frame-ancestors 'self'; sandbox allow-scripts allow-downloads allow-modals allow-popups"
    ),
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",  # core lot v0.24 (D-B-090)
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), usb=(), serial=(), payment=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'self'"
    ),
}

ROUTES = [(method, re.compile(pattern), handler, access)
          for method, pattern, handler, access
          in session_api.ROUTES + admin.ROUTES + access_rules.ROUTES + search.ROUTES + ui_audit.ROUTES
          + members.ROUTES + prefs.ROUTES + backup.ROUTES + dashboard.ROUTES + platform_config.ROUTES + objectives.ROUTES + profile.ROUTES + reviews.ROUTES + team.ROUTES + mentions.ROUTES + update.ROUTES + tls.ROUTES
          + datapack.ROUTES + sitemove.ROUTES + spacecopy.ROUTES + spacecard.ROUTES + restorepoints.ROUTES + baselines.ROUTES
          + starter_apply.ROUTES + bot.ROUTES + bot_admin.ROUTES + update_online.ROUTES
          + modules.registered_routes()]


class RequestContext:
    """Everything a handler needs about the current request."""

    def __init__(self, conn, user, token, body, params, query, ip, secure, config, data_dir):
        self.conn = conn
        self.user = user
        self.token = token
        self.body = body
        self.params = params
        self.query = query
        self.ip = ip
        self.secure = secure
        self.config = config
        self.data_dir = data_dir
        self.upload = None  # core.uploads.Upload for @binary_body routes
        self.cookies_out = []
        self.transport = {}  # core lot v0.24: TLS version, cipher, client certificate (core.tls.peer)

    @property
    def client_cert(self):
        return self.transport.get("client_cert")

    def set_session_cookie(self, token, max_age):
        parts = ["{}={}".format(tls.cookie_name(self.secure), token), "Path=/", "HttpOnly",
                 "SameSite=Strict", "Max-Age={}".format(max_age)]
        if self.secure:
            parts.append("Secure")
        self.cookies_out.append("; ".join(parts))

    def clear_session_cookie(self):
        self.set_session_cookie("", 0)


class AppHandler(BaseHTTPRequestHandler):
    server_version = "DynamiteAgile"
    sys_version = ""

    head_only = False

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self.head_only = True
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def log_message(self, fmt, *args):
        log.info("%s %s", self._peer()[0], fmt % args)

    def _peer(self):
        """(visitor ip, secure): the socket's, or what a trusted reverse proxy says (0.60.17, core/proxy.py)."""
        if getattr(self, "_peer_cache", None) is None:
            self._peer_cache = proxy.client(getattr(self.server, "app_config", {}) or {}, self.client_address[0],
                                            self.headers or {}, getattr(self.server, "use_tls", False))
        return self._peer_cache

    # ------------------------------------------------------------------
    def _dispatch(self, method):
        path = urlsplit(self.path).path
        self._peer_cache = None  # one connection may carry the requests of several visitors (keep-alive from the proxy)
        try:
            if proxy.refused(self.server.app_config, self.client_address[0], self.server.use_tls):
                log.warning("Refused (not through the trusted proxy): %s", self.client_address[0])
                raise ApiError(403, proxy.REFUSED)
            if not devshare.client_allowed(self.server.app_config, self.client_address[0]):
                log.warning("Refused (not in the development sharing allow list): %s", self.client_address[0])
                raise ApiError(403, "Accès refusé : ce poste n'est pas autorisé sur ce serveur de développement.")
            if path.startswith("/api/"):
                self._handle_api(method)
            elif method == "GET":
                self._serve_static(path)
            else:
                raise ApiError(405, "Méthode non permise.")
        except ApiError as exc:
            self._send_json(exc.status, {"error": exc.message})
        except (BrokenPipeError, ConnectionResetError):
            pass  # Browser closed the connection; nothing to answer
        except Exception:
            log.exception("Unhandled error on %s %s", method, self.path)
            self._send_json(500, {"error": "Erreur interne du serveur. Consultez le journal."})

    def _handle_api(self, method):
        parts = urlsplit(self.path)
        route, params = self._match(method, parts.path)
        _, _, handler, access = route
        upload = None
        if method in BODY_METHODS and getattr(handler, "accepts_binary", False):
            body, upload = {}, self._read_upload(handler)
        else:
            body = self._read_json() if method in BODY_METHODS else {}
        query = {key: values[-1] for key, values in parse_qs(parts.query).items()}
        token = self._session_token()
        transport = tls.peer(getattr(self, "connection", None))  # the demo bridge has no socket
        try:  # D-B-104: the first request of the day takes the daily restore point (state at the end of the day before)
            restorepoints.daily(getattr(self.server, "data_dir", None), getattr(self.server, "app_config", None))
        except Exception:  # never blocks the request
            log.exception("Daily restore point failed")

        with db.connect() as conn:
            if access == "bot":  # 0.60.36 (D-O-044): an AI agent's key, read-only, no session (core/bot.py)
                if method != "GET":
                    raise ApiError(405, "Une clé d'agent ne fait que lire.")
                ctx = RequestContext(conn, None, None, {}, params, query, self._peer()[0], self._peer()[1],
                                     self.server.app_config, self.server.data_dir)
                ctx.bot = bot.authenticate(conn, self.headers.get("Authorization"))
                ctx.host = (self.headers.get("Host") or "").strip()
                result = handler(ctx)
                self._send_json(200, result)
                return
            session = auth.get_session(conn, token)
            if (session is not None and session["client_cert"] and self.server.app_config.get("tls_bind_session", True)
                    and session["client_cert"] != transport.get("client_cert")):
                log.warning("Session refused: presented from another client certificate (%s).", self.client_address[0])
                session = None  # D-B-090: a cookie taken from one computer does not open the session on another
            if access != "public":
                if session is None:
                    raise ApiError(401, "Authentification requise.")
                if method != "GET":
                    self._check_csrf(session)
                if session["must_change_password"] and access != "pending_ok":
                    raise ApiError(403, "Vous devez d'abord changer votre mot de passe.")
                if access == "admin" and not session["is_admin"]:
                    raise ApiError(403, "Réservé aux administrateurs.")
                if (method != "GET" and access != "pending_ok" and self.server.app_config.get("require_initials", True)
                        and not INITIALS_FREE.fullmatch(parts.path) and not prefs.ensure_initials(conn, session["id"])):  # 0.60.19
                    raise ApiError(428, INITIALS_MESSAGE)
            ctx = RequestContext(conn, session, token, body, params, query,
                                 self._peer()[0], self._peer()[1],
                                 self.server.app_config, self.server.data_dir)
            ctx.upload = upload
            ctx.transport = transport
            # Core lot v0.33 (D-B-129): a person viewing a revision reads its working copy; writing is refused.
            ctx.baseline = baseline_view.active(conn, session, self.server.data_dir) if access != "public" else None
            frozen = baseline_view.guard(method, parts.path, ctx.baseline)
            work = baseline_view.open_copy(self.server.data_dir, ctx.baseline, session["id"]) if frozen else None
            try:
                if work is not None:
                    ctx.conn = work
                result = handler(ctx)
            finally:
                if work is not None:
                    work.rollback()
                    work.close()
                    ctx.conn = conn
            if stamp.wants(result) and session is not None and self.server.data_dir:
                result = stamp.apply(ctx, result, parts.path, conn)  # revision in the name and inside, register
        if isinstance(result, RawFile):
            self._send_raw(result, ctx.cookies_out)
        else:
            self._send_json(200, result if result is not None else {"ok": True}, ctx.cookies_out)

    def _match(self, method, path):
        path_exists = False
        for route in ROUTES:
            match = route[1].fullmatch(path)
            if match:
                if route[0] == method:
                    return route, match.groupdict()
                path_exists = True
        if path_exists:
            raise ApiError(405, "Méthode non permise.")
        raise ApiError(404, "Ressource introuvable.")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "En-tête Content-Length invalide.")
        if length > MAX_JSON_BYTES:
            raise ApiError(413, "Requête trop volumineuse.")
        if length == 0:
            return {}
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            raise ApiError(415, "Contenu JSON attendu.")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ApiError(400, "JSON invalide.")
        if not isinstance(data, dict):
            raise ApiError(400, "Objet JSON attendu.")
        return data

    def _read_upload(self, handler=None):
        """Raw body of a file upload (core lot v0.4). The file name travels
        URL-encoded in X-File-Name; the type is decided later from the bytes."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "En-tête Content-Length invalide.")
        setting = "max_transfer_mb" if getattr(handler, "transfer", False) else "max_upload_mb"  # D-B-094: packages of a site
        limit = int(self.server.app_config.get(setting, 50)) * 1024 * 1024
        if length > limit:
            # Drain (bounded) so the browser reads our 413 instead of a reset.
            self.close_connection = True
            remaining = min(length, 4 * limit)
            while remaining > 0:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
            raise ApiError(413, "Fichier de plus de {} Mo. Correctif : réduisez-le, ou demandez à "
                                "l'administrateur d'augmenter « {} » (data/config.json).".format(limit // 1048576, setting))
        data = self.rfile.read(length) if length else b""
        name = unquote(self.headers.get("X-File-Name", ""))[:255]
        return Upload(data, self.headers.get("Content-Type", ""), name)

    def _session_token(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        jar = cookies.SimpleCookie()
        try:
            jar.load(raw)
        except cookies.CookieError:
            return None
        morsel = jar.get(tls.cookie_name(self._peer()[1]))
        return morsel.value if morsel and morsel.value else None

    def _check_csrf(self, session):
        sent = self.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(sent, session["csrf_token"]):
            raise ApiError(403, "Jeton de sécurité invalide. Rechargez la page.")

    # ------------------------------------------------------------------
    def _serve_static(self, path):
        static_dir = self.server.static_dir
        relative = "index.html" if path in ("", "/") else unquote(path).lstrip("/")
        try:
            target = (static_dir / relative).resolve()
            target.relative_to(static_dir)  # Blocks ../ path traversal
        except (ValueError, OSError):
            raise ApiError(404, "Fichier introuvable.")
        content_type = STATIC_TYPES.get(target.suffix.lower())
        if content_type is None or not target.is_file():
            raise ApiError(404, "Fichier introuvable.")
        # 0.60.31 (D-O-039): ETag -> 304 when the browser already has the file; gzip for the text types
        entry = static_cache.get(target)
        fresh = static_cache.not_modified(entry, self.headers.get("If-None-Match"))
        packed = entry.gz is not None and static_cache.accepts_gzip(self.headers.get("Accept-Encoding"))
        data = b"" if fresh else (entry.gz if packed else entry.raw)
        self.send_response(304 if fresh else 200)
        self.send_header("Content-Type", content_type)
        if not fresh:
            self.send_header("Content-Length", str(len(data)))
        if packed and not fresh:
            self.send_header("Content-Encoding", "gzip")
        if entry.gz is not None:
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("ETag", static_cache.gzip_etag(entry.etag) if packed else entry.etag)
        vendor = relative.startswith(VENDOR_PREFIX)
        self.send_header("Cache-Control", "public, max-age=31536000, immutable" if vendor else "no-cache")
        if relative.startswith(APP_PREFIX) and target.suffix.lower() == ".html":
            for name, value in APP_HEADERS.items():  # lot v0.15: isolated offline tool
                self.send_header(name, value)
            for name, value in tls.transport_headers(self.server).items():
                self.send_header(name, value)
        elif relative.endswith(WORKER_SUFFIX):
            for name, value in WORKER_HEADERS.items():  # core lot v0.32: background worker, own policy
                self.send_header(name, value)
            for name, value in tls.transport_headers(self.server).items():
                self.send_header(name, value)
        else:
            self._send_security_headers()
        self.end_headers()
        if not self.head_only and data:
            self.wfile.write(data)

    def _send_raw(self, raw, cookies_out=()):
        """Send a handler-built file (see RawFile) instead of JSON -- used
        for CSV export and any future download (attachments, reports)."""
        try:
            self.send_response(200)
            self.send_header("Content-Type", raw.content_type)
            self.send_header("Content-Length", str(len(raw.data)))
            self.send_header("Content-Disposition", '{}; filename="{}"'.format(
                "inline" if raw.inline else "attachment", raw.filename))
            self.send_header("Cache-Control", "private, max-age=86400" if raw.inline else "no-store")
            for cookie in cookies_out:
                self.send_header("Set-Cookie", cookie)
            self._send_security_headers()
            self.end_headers()
            if not self.head_only:
                self.wfile.write(raw.data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_json(self, status, payload, cookies_out=()):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            for cookie in cookies_out:
                self.send_header("Set-Cookie", cookie)
            self._send_security_headers()
            self.end_headers()
            if not self.head_only:
                self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_security_headers(self):
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        for name, value in tls.transport_headers(self.server).items():  # HSTS once HTTPS is on
            self.send_header(name, value)


class AppServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows, SO_REUSEADDR lets a second server silently share the port.
    allow_reuse_address = os.name != "nt"

    def handle_error(self, request, client_address):
        """A refused TLS handshake (no client certificate, plain HTTP on the HTTPS port, old TLS) is one log line,
        not a traceback."""
        exc = sys.exc_info()[1]
        if isinstance(exc, (ssl.SSLError, ConnectionResetError, BrokenPipeError, TimeoutError)):
            log.info("Connection refused from %s: %s", client_address[0], getattr(exc, "reason", None) or exc)
        else:
            super().handle_error(request, client_address)


def create_server(cfg, static_dir, data_dir):
    server = AppServer((cfg["host"], int(cfg["port"])), AppHandler)
    server.app_config = cfg
    server.static_dir = static_dir.resolve()
    server.data_dir = data_dir
    server.use_tls = False
    server.tls_mode = "off"
    return server
