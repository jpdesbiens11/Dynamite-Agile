"""Dynamite | Agile - open product-design workshop: requirements, wiki, tickets, tests (self-hosted).

Runs a small web server using only the Python standard library.
All runtime data (database, attachments, logs, config) lives in the
"data" folder next to this script, so the whole folder can be moved
to another machine without breaking any path.

Examples:
    python app_dynamite_agile.py
    python app_dynamite_agile.py --port 8090
    python app_dynamite_agile.py --host 0.0.0.0          (server only)
    python app_dynamite_agile.py --reset-password nina
    python app_dynamite_agile.py --lan                    (development: share with a colleague, D-B-091)
    python lancer_dev.py [local|reseau]                   (the same, from Spyder F5 or Lancer_dev_*.bat)
"""
import argparse
import logging
import logging.handlers
import os
import ssl
import stat
import sys
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core import APP_DESCRIPTION, APP_NAME, APP_VERSION  # noqa: E402
from core import audit, auth, db, devshare, modules, router, startup, tls  # noqa: E402
from core.config import load_config  # noqa: E402

DEFAULT_DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DB_FILENAME = "dynamite_agile.db"

log = logging.getLogger("dynamite_agile")


def parse_args(argv=None):
    """Build the command-line interface (also provides --help)."""
    parser = argparse.ArgumentParser(
        prog="app_dynamite_agile",
        description="{} v{} - {}".format(APP_NAME, APP_VERSION, APP_DESCRIPTION),
        epilog="Settings are stored in <data-dir>/config.json. "
               "Command-line options override them for this run only.",
    )
    parser.add_argument(
        "--host",
        help="Network interface to listen on (config default: 127.0.0.1). "
             "Use 0.0.0.0 on the server to accept VPN clients.",
    )
    parser.add_argument("--port", type=int, help="TCP port (config default: 8080).")
    parser.add_argument(
        "--data-dir", type=Path, default=DEFAULT_DATA_DIR,
        help="Folder for database, attachments, logs and config "
             "(default: 'data' next to this script).",
    )
    parser.add_argument(
        "--reset-password", metavar="USERNAME",
        help="Generate a new temporary password for USERNAME, "
             "reactivate the account, then exit.",
    )
    parser.add_argument(
        "--dev-admin", action="store_true",
        help="Force development mode for this run (same as dev_mode: true).",
    )
    parser.add_argument(
        "--exemple", action="store_true",
        help="0.60.41 (D-O-050): also create the example Space EQP and its four students (development only; a fresh "
             "installation is otherwise empty but for the HeadLamp sandbox).",
    )
    parser.add_argument(
        "--prod", action="store_true",
        help="Force production mode for this run: random temporary admin "
             "password, no pre-filled login, no example data.",
    )
    parser.add_argument(
        "--lan", action="store_true",
        help="Development only: share this server with a colleague on the local network "
             "(HTTPS with the development CA, private networks only, port 8443; D-B-091).",
    )
    parser.add_argument(
        "--allow", action="append", default=[], metavar="IP",
        help="With --lan: only these addresses (IP or CIDR, repeatable) may connect.",
    )
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + APP_VERSION)
    return parser.parse_args(argv)


def setup_logging(data_dir):
    """Log to the console and to a rotating file in data/logs."""
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        str(log_dir / "server.log"), maxBytes=5 * 1024 * 1024,
        backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger("dynamite_agile")
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.propagate = False


def make_private(data_dir):
    """0.60.97 (D-O-103): data/ holds the database (password hashes included), the backups and restore points, the SMTP
    password (mail.json), the TLS key and the first admin password: only the account running the server enters it (0700),
    whatever mode the files below were written with. POSIX only; never blocks the start."""
    if os.name != "posix":
        return
    try:
        if stat.S_IMODE(data_dir.stat().st_mode) & 0o077:
            os.chmod(data_dir, 0o700)
            log.info("data/ made private (0700): %s", data_dir)
    except OSError as exc:
        log.warning("data/ could not be made private (%s): other accounts of this server may read it. "
                    "Fix: chown the folder to the account running the server, then chmod 700.", exc)


def enable_tls(server, cfg, data_dir):
    """Core lot v0.24 (D-B-090): TLS 1.3, optional mTLS -- see core/tls.py and deploy/TLS.md."""
    tls.enable(server, cfg, data_dir)


def setup_lan(cfg, args, data_dir):
    """D-B-091: development sharing -- every interface, HTTPS with a development certificate naming this computer's
    LAN addresses (made or renewed when needed), the old http://localhost:8080 redirecting to it. Returns the LAN
    addresses, or raises SystemExit with the reason."""
    try:
        devshare.parse_allow(args.allow or cfg.get("lan_allow"))
    except ValueError as exc:
        raise SystemExit("--allow : " + str(exc))
    addresses = devshare.lan_addresses()
    cfg.update(lan_share=True, host="0.0.0.0", lan_allow=args.allow or cfg.get("lan_allow") or [],
               lan_local_nets=devshare.local_nets(addresses))
    if not args.port:
        cfg["port"] = devshare.LAN_PORT
    if cfg.get("tls_cert"):  # a certificate is already configured: keep it
        return addresses
    cert = data_dir / "tls" / "server.crt"
    info = tls.cert_info(cert)
    fresh = (info.get("issuer", "").startswith("Dynamite Dev Root CA") and (info.get("days_left") or 0) > 30
             and all(ip in info.get("san", []) for ip in addresses))
    if not fresh:
        try:
            import contextlib
            import io
            from tools import make_dev_ca
            with contextlib.redirect_stdout(io.StringIO()):
                make_dev_ca.main(["--data-dir", str(data_dir)] + [x for ip in addresses for x in ("--ip", ip)])
        except SystemExit as exc:  # openssl not found or failed: share in plain HTTP, loudly
            log.warning("Development certificate not created (%s): sharing in plain HTTP.", exc)
            return addresses
    cfg.update(tls_cert="tls/server.crt", tls_key="tls/server.key", http_redirect_port=0 if args.port else 8080)
    return addresses


def reset_password(username):
    """CLI recovery: new temporary password for an existing account."""
    username = username.strip().lower()
    with db.connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            print("User not found: " + username, file=sys.stderr)
            return 1
        temp = auth.set_temp_password(conn, row["id"])
        conn.execute("UPDATE users SET is_active = 1 WHERE id = ?", (row["id"],))
        audit.log_action(conn, None, "cli_reset_password", "user", row["id"])
    print("Temporary password for {}: {}".format(username, temp))
    print("The user must change it at next login.")
    return 0


def print_dev_admin_warning():
    print("!" * 64)
    print("! DEVELOPMENT MODE: admin/admin, login pre-filled, example data.")
    print("! Never with real data: set \"dev_mode\": false in data/config.json")
    print("! or start with --prod.")
    print("!" * 64)


def seed_example_data(port, cafile=None):
    """Dev mode (0.60.01): the team project Space EQP and its four fictitious students, created through the API
    (audited like a real user). Idempotent. `cafile`: the development CA when the server speaks HTTPS (D-B-091)."""
    try:
        from tools import seed_demo
        from argparse import Namespace
        url = "{}://{}:{}".format("https" if cafile else "http", "localhost" if cafile else "127.0.0.1", port)
        created = seed_demo.run(Namespace(url=url, user="admin", password="admin", cafile=cafile))
        if created:
            log.info("Example team created: %s.", ", ".join(sorted(created)))
    except Exception as exc:  # never take the server down for example data
        log.warning("Example data not created (%s). If data/ comes from an older "
                    "version with another admin password, delete data/ once.", exc)


def print_initial_admin(temp_password, retired=False):
    """Show the first-launch administrator credentials (or the new ones replacing admin / admin, 0.60.97)."""
    print("=" * 64)
    print(" admin / admin RETIRED (production) - new temporary password" if retired else
          " FIRST LAUNCH - initial administrator account created")
    print("   Username : " + auth.INITIAL_ADMIN_USERNAME)
    print("   Password : " + temp_password)
    print(" Also saved in data/{} until the first password change.".format(
        auth.INITIAL_PASSWORD_FILE))
    print("=" * 64)


def main(argv=None):
    args = parse_args(argv)
    data_dir = args.data_dir if args.data_dir.is_absolute() else BASE_DIR / args.data_dir
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print("Cannot create data folder {}: {}".format(data_dir, exc), file=sys.stderr)
        return 1

    setup_logging(data_dir)
    make_private(data_dir)
    cfg = load_config(data_dir)
    if args.host:
        cfg["host"] = args.host
    if args.port:
        cfg["port"] = args.port

    db.init_db(data_dir / DB_FILENAME, modules.registered_schema(),
               modules.registered_migrations())
    log.info("%s v%s | Python %s | SQLite %s | data: %s", APP_NAME, APP_VERSION,
             sys.version.split()[0], db.sqlite_version(), data_dir)

    if args.reset_password:
        return reset_password(args.reset_password)

    dev = (bool(cfg.get("dev_mode")) or args.dev_admin) and not args.prod
    cfg["dev_mode"] = dev
    lan = None
    if args.lan or cfg.get("lan_share"):
        if not dev:
            log.error("--lan est réservé au développement. En production : deploy/TLS.md.")
            return 1
        lan = setup_lan(cfg, args, data_dir)
    refused = tls.check_start(cfg, dev)  # D-B-090: fail closed
    if refused:
        log.error(refused)
        return 1
    if dev:
        print_dev_admin_warning()
        log.warning("Development mode: fixed admin/admin credentials, example data.")
        auth.DEV_TEMP_PASSWORD = str(cfg.get("dev_temp_password") or "admin")  # D-A-040: team tests
    retired, admin_temp = [], None
    with db.connect() as conn:
        temp = auth.ensure_initial_admin(conn, data_dir, dev_password="admin" if dev else None)
        auth.purge_expired_sessions(conn)
        if dev:
            auth.mark_dev_passwords(conn)
        else:  # 0.60.97 (D-O-104): a trial that went online never keeps admin / admin
            retired, admin_temp = auth.retire_dev_passwords(conn, data_dir, ("admin", cfg.get("dev_temp_password")))
    if retired:
        log.warning("Development passwords retired (%s): each account got a new random temporary password (%s).",
                    ", ".join(retired), "; ".join(
                        (["admin: printed below and in data/" + auth.INITIAL_PASSWORD_FILE] if admin_temp else [])
                        + (["the others: give them again in Admin → Comptes"] if len(retired) > (1 if admin_temp else 0) else [])))
    if admin_temp:
        print_initial_admin(admin_temp, retired=True)
    startup.run(data_dir, cfg)  # core lot v0.7: module start-up hooks (e.g. the TESTING Space)
    if dev:
        with db.connect() as conn:
            count = auth.reset_pending_temp_passwords(conn)
        log.warning("Development mode: temporary password « %s » for %d account(s) not yet activated "
                    "(change required at first login).", auth.DEV_TEMP_PASSWORD, count)
    if temp and not dev:
        print_initial_admin(temp)

    if not cfg.get("tls_cert"):
        log.warning("HTTP without TLS: the exchanges are readable on the network. Development or loopback only "
                    "(see deploy/TLS.md).")

    try:
        server = router.create_server(cfg, STATIC_DIR, data_dir)
    except OSError as exc:
        log.error("Cannot listen on %s:%s (%s). Is the port already in use?",
                  cfg["host"], cfg["port"], exc)
        return 1

    if cfg.get("tls_cert"):
        try:
            enable_tls(server, cfg, data_dir)
        except (OSError, ssl.SSLError) as exc:
            log.error("TLS setup failed: %s", exc)
            server.server_close()
            return 1

    if server.use_tls:
        try:
            tls.start_redirect(cfg)
        except OSError as exc:
            log.warning("HTTP redirect listener not started (%s).", exc)
        log.info("TLS: minimum %s, mTLS %s.", "1.2" if str(cfg.get("tls_min_version")) == "1.2" else "1.3", server.tls_mode)

    if dev and (args.exemple or cfg.get("example_space")):  # 0.60.41 (D-O-050): no example Space unless asked
        ca = data_dir / "tls" / "ca.crt"
        cafile = str(ca) if server.use_tls and ca.exists() else None
        if not server.use_tls or cafile:
            threading.Thread(target=seed_example_data, args=(server.server_address[1], cafile),
                             daemon=True).start()

    scheme = "https" if server.use_tls else "http"
    shown_host = "127.0.0.1" if cfg["host"] in ("0.0.0.0", "") else cfg["host"]
    log.info("Listening on %s://%s:%s  (Ctrl+C or close this window to stop)",
             scheme, shown_host, cfg["port"])
    if lan is not None:
        print(devshare.banner(cfg, scheme, server.server_address[1], lan, data_dir / "tls" / "ca.crt"), flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        log.info("Stop requested, shutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
