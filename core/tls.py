"""Secure transport (core lot v0.24, D-B-090): what protects the client/server exchange on the local network.

The VPN only encrypts up to its gateway; after it, and for any computer plugged in on site, the LAN is not trusted
(Zero Trust). So the server itself speaks HTTPS, with the Python standard library only (ssl):

- TLS 1.3 only (AEAD suites, ECDHE key exchange = forward secrecy); « tls_min_version »: "1.2" is the one fallback,
  then limited to ECDHE + AES-GCM / ChaCha20. No compression, no renegotiation.
- Certificate of your organisation or of a public CA, see deploy/TLS.md; expiry shown in Admin → Sécurité réseau.
- mTLS, coded but OFF by default: « tls_client_ca » (the CA that signs the computers / people) turns it on;
  « tls_client_required »: false = certificate checked when presented (pilot), true = no certificate, no handshake --
  an intruder on the LAN never even reaches the sign-in page. Optional CRL (« tls_client_crl »).
- Session bound to the client certificate (« tls_bind_session »): a session cookie stolen from one computer is
  refused on another one (the SHA-256 fingerprint of the certificate is stored with the session).
- Production fails closed: no certificate, no start -- unless the server only listens on the loopback (127.0.0.1),
  which nobody on the LAN can reach.
- HSTS and the « __Host- » cookie once HTTPS is on (never in development: HSTS would stick to localhost).
- « http_redirect_port »: a small plain-HTTP listener that only answers « go to https:// » (301), never content.
"""
import hashlib
import ipaddress
import logging
import re
import ssl
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

log = logging.getLogger("dynamite_agile.tls")

MIGRATIONS = [
    (12, """
        -- D-B-090 (core lot v0.24): SHA-256 fingerprint of the client certificate that opened the session (mTLS).
        ALTER TABLE sessions ADD COLUMN client_cert TEXT;
    """),
]

COOKIE_PLAIN = "da_session"
COOKIE_SECURE = "__Host-da_session"  # the browser only accepts it over HTTPS, Path=/, without Domain
EXPIRY_WARN_DAYS = 30
TLS12_CIPHERS = "ECDHE+AESGCM:ECDHE+CHACHA20"
HOSTNAME = re.compile(r"^[A-Za-z0-9.-]{1,253}$")


def data_path(value, data_dir):
    """Configured file path: absolute, or relative to data/."""
    path = Path(value)
    return path if path.is_absolute() else Path(data_dir) / path


def mtls_mode(cfg):
    if not cfg.get("tls_client_ca"):
        return "off"
    return "required" if cfg.get("tls_client_required") else "optional"


def build_context(cfg, data_dir):
    """Server SSLContext from the configuration (raises OSError / ssl.SSLError on a bad file)."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    if str(cfg.get("tls_min_version", "1.3")) == "1.2":
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers(TLS12_CIPHERS)  # TLS 1.2 fallback: forward secrecy + AEAD only
    else:
        context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.options |= ssl.OP_NO_COMPRESSION | ssl.OP_CIPHER_SERVER_PREFERENCE
    context.options |= getattr(ssl, "OP_NO_RENEGOTIATION", 0)
    key = data_path(cfg["tls_key"], data_dir) if cfg.get("tls_key") else None
    context.load_cert_chain(str(data_path(cfg["tls_cert"], data_dir)), str(key) if key else None)
    mode = mtls_mode(cfg)
    if mode != "off":
        context.load_verify_locations(cafile=str(data_path(cfg["tls_client_ca"], data_dir)))
        context.verify_mode = ssl.CERT_REQUIRED if mode == "required" else ssl.CERT_OPTIONAL
        if cfg.get("tls_client_crl"):
            context.load_verify_locations(cafile=str(data_path(cfg["tls_client_crl"], data_dir)))
            context.verify_flags |= ssl.VERIFY_CRL_CHECK_LEAF
    return context


def enable(server, cfg, data_dir):
    """Wrap the listening socket with TLS. The handshake runs in the worker thread (do_handshake_on_connect=False),
    so a slow or hostile client cannot block accept()."""
    context = build_context(cfg, data_dir)
    server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    server.use_tls = True
    server.tls_mode = mtls_mode(cfg)
    info = cert_info(data_path(cfg["tls_cert"], data_dir))
    if info.get("days_left") is not None:
        level = log.error if info["days_left"] < 0 else log.warning if info["days_left"] <= EXPIRY_WARN_DAYS else log.info
        level("TLS certificate %s expires on %s (%d day(s)).", info.get("subject", "?"), info["not_after"], info["days_left"])


def is_loopback(host):
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_start(cfg, dev):
    """Return None if the server may start, else the French message explaining why not (fail closed)."""
    if cfg.get("tls_client_required") and not cfg.get("tls_client_ca"):
        return ("mTLS demandé (« tls_client_required ») sans « tls_client_ca » : indiquez le fichier de la CA qui signe "
                "les certificats clients, dans data/config.json.")
    if not dev and not cfg.get("tls_cert") and not is_loopback(str(cfg.get("host", ""))) and not _behind_proxy(cfg):
        return ("Production refusée : HTTPS est obligatoire dès que le serveur écoute sur le réseau (« host » = {}). "
                "Correctif : indiquez « tls_cert » et « tls_key » (certificat de votre organisation ou d'une autorité publique, voir "
                "deploy/TLS.md) dans data/config.json, ou, derrière un proxy HTTPS (Traefik), « trusted_proxies ».".format(cfg.get("host")))
    return None


def _behind_proxy(cfg):
    """0.60.17 (D-O-029): plain HTTP on the network is allowed only behind a trusted HTTPS proxy (core/proxy.py)."""
    from . import proxy
    return proxy.enabled(cfg)


def cookie_name(secure):
    return COOKIE_SECURE if secure else COOKIE_PLAIN


def transport_headers(server):
    """Headers added to every response once HTTPS is on (not in development: HSTS would stick to localhost)."""
    if not getattr(server, "use_tls", False) or server.app_config.get("dev_mode"):
        return {}
    value = "max-age={}".format(int(server.app_config.get("hsts_max_age", 31536000)))
    return {"Strict-Transport-Security": value + "; includeSubDomains"}


def peer(connection):
    """What the TLS connection says: protocol, cipher, client certificate (fingerprint, subject) -- or {} over HTTP."""
    if not isinstance(connection, ssl.SSLSocket):
        return {}
    out = {"version": connection.version()}
    cipher = connection.cipher()
    if cipher:
        out["cipher"], out["bits"] = cipher[0], cipher[2]
    der = connection.getpeercert(binary_form=True)
    if der:
        out["client_cert"] = hashlib.sha256(der).hexdigest()
        subject = dict(pair[0] for pair in (connection.getpeercert() or {}).get("subject", ()))
        out["client_subject"] = subject.get("commonName", "")
    return out


def _name(rdns):
    fields = dict(pair[0] for pair in rdns or ())
    return fields.get("commonName") or ", ".join("{}={}".format(k, v) for k, v in fields.items())


def cert_info(path):
    """Subject, issuer, SAN and expiry of a PEM certificate (the server's own) -- {} if it cannot be read."""
    decode = getattr(getattr(ssl, "_ssl", None), "_test_decode_cert", None)  # stdlib, no public equivalent
    if decode is None or not Path(path).is_file():
        return {}
    try:
        raw = decode(str(path))
    except (OSError, ssl.SSLError, ValueError):
        return {}
    info = {"subject": _name(raw.get("subject")), "issuer": _name(raw.get("issuer")),
            "san": [value for kind, value in raw.get("subjectAltName", ()) if kind in ("DNS", "IP Address")]}
    if raw.get("notAfter"):
        end = datetime.fromtimestamp(ssl.cert_time_to_seconds(raw["notAfter"]), timezone.utc)
        info["not_after"] = end.date().isoformat()
        info["days_left"] = (end - datetime.now(timezone.utc)).days
    return info


# --------------------------------------------------------------------------- plain-HTTP listener: redirect only
class _RedirectHandler(BaseHTTPRequestHandler):
    server_version = "DynamiteAgile"
    sys_version = ""

    def _redirect(self):
        name = self.server.public_name or (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        if not HOSTNAME.fullmatch(name or ""):
            self.send_error(400)
            return
        port = "" if self.server.https_port == 443 else ":{}".format(self.server.https_port)
        path = self.path if self.path.startswith("/") else "/"
        self.send_response(301)
        self.send_header("Location", "https://{}{}{}".format(name, port, path))
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        self._redirect()

    do_HEAD = do_GET

    def _refuse(self):  # a write sent in clear is not replayed over HTTPS: the browser must start again on https://
        self.send_error(403, "HTTPS requis")

    do_POST = do_PUT = do_PATCH = do_DELETE = _refuse

    def log_message(self, fmt, *args):
        log.info("%s (http->https) %s", self.client_address[0], fmt % args)


def start_redirect(cfg):
    """Start the redirect listener in a daemon thread if « http_redirect_port » is set; return the server or None."""
    port = int(cfg.get("http_redirect_port") or 0)
    if not port:
        return None
    server = ThreadingHTTPServer((cfg["host"], port), _RedirectHandler)
    server.daemon_threads = True
    server.https_port = int(cfg["port"])
    server.public_name = str(cfg.get("public_name") or "")
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True).start()
    log.info("HTTP redirect listener on port %s -> https port %s", port, cfg["port"])
    return server


# --------------------------------------------------------------------------- Admin → Sécurité réseau
def api_status(ctx):
    cfg = ctx.config
    server_cert = cert_info(data_path(cfg["tls_cert"], ctx.data_dir)) if cfg.get("tls_cert") else {}
    client_ca = cert_info(data_path(cfg["tls_client_ca"], ctx.data_dir)) if cfg.get("tls_client_ca") else {}
    version = ssl.OPENSSL_VERSION_INFO
    return {
        "https": bool(ctx.secure), "dev_mode": bool(cfg.get("dev_mode")), "host": cfg.get("host"),
        "min_version": "TLS 1.2" if str(cfg.get("tls_min_version", "1.3")) == "1.2" else "TLS 1.3",
        "connection": ctx.transport, "server_cert": server_cert, "expiry_warn_days": EXPIRY_WARN_DAYS,
        "mtls": mtls_mode(cfg), "client_ca": client_ca.get("subject", ""), "crl": bool(cfg.get("tls_client_crl")),
        "bind_session": bool(cfg.get("tls_bind_session", True)),
        "hsts": bool(ctx.secure and not cfg.get("dev_mode")), "cookie": cookie_name(ctx.secure),
        "redirect_port": int(cfg.get("http_redirect_port") or 0),
        "openssl": ssl.OPENSSL_VERSION, "pq_default": tuple(version[:2]) >= (3, 5),
        "lan_share": bool(cfg.get("lan_share")), "lan_allow": list(cfg.get("lan_allow") or []),  # D-B-091
    }


ROUTES = [
    ("GET", r"/api/admin/transport", api_status, "admin"),
]
