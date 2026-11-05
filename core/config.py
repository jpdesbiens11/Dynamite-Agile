"""Load data/config.json, creating it with defaults on first launch."""
import json
from pathlib import Path

DEFAULTS = {
    "host": "127.0.0.1",          # 0.0.0.0 on the server to accept VPN clients
    "port": 8080,
    "session_hours": 10,          # Session lifetime (one work day)
    "max_upload_mb": 50,          # Used from step 3.4 (attachments)
    "max_transfer_mb": 2048,      # D-B-094: « Données » / « Site complet » packages of Admin → Update
    "login_max_failures": 5,      # Failed logins before a temporary lock
    "login_lock_minutes": 5,
    "tls_cert": "",               # Path to certificate (relative to data/) for HTTPS
    "tls_key": "",
    # Core lot v0.24 (D-B-090, deploy/TLS.md): secure transport
    "tls_min_version": "1.3",     # "1.2" only for an old client (then ECDHE + AEAD only)
    "tls_client_ca": "",          # mTLS: CA that signs the client certificates ("" = mTLS off)
    "tls_client_required": False, # true = no valid client certificate, no connection
    "tls_client_crl": "",         # optional CRL (PEM) of revoked client certificates
    "tls_bind_session": True,     # session refused from another client certificate than the one that opened it
    "hsts_max_age": 31536000,     # Strict-Transport-Security, once HTTPS is on (never in dev_mode)
    "http_redirect_port": 0,      # e.g. 80: plain-HTTP listener that only redirects to https:// (0 = off)
    "public_name": "",            # DNS name of the server for that redirect ("" = the Host header)
    "trusted_proxies": [],        # 0.60.17 (D-O-029): addresses / CIDR of an HTTPS reverse proxy (Traefik); [] = off
    # 0.60.36 (D-O-045): online update -- where the listing is read ("" = the project's website), the code to update
    # ("" = this installation) and the restart after an update (false: restart the service yourself)
    "release_site": "",
    "code_root": "",
    "update_restart": True,
    # D-B-091: development sharing on the local network (lancer_dev.py reseau / --lan), never in production
    "lan_share": False,
    "lan_allow": [],              # IPs or CIDR allowed to connect ([] = private networks only)
    # DEVELOPMENT PHASE: true until production. admin/admin, login form
    # pre-filled, example team (EQP) seeded on first launch. Set to false
    # (or start with --prod) before any real data -- see deploy/.
    "dev_mode": True,
}


def load_config(data_dir):
    """Return the merged configuration dict. Unknown keys are ignored."""
    cfg_path = Path(data_dir) / "config.json"
    cfg = dict(DEFAULTS)
    if not cfg_path.exists():
        with cfg_path.open("w", encoding="utf-8") as handle:
            json.dump(DEFAULTS, handle, indent=2)
        return cfg
    try:
        with cfg_path.open("r", encoding="utf-8-sig") as handle:  # 0.60.10: a BOM (Notepad, PowerShell 5.1) is accepted
            user_cfg = json.load(handle)
        if not isinstance(user_cfg, dict):
            raise ValueError("the file must contain a JSON object")
    except (OSError, ValueError) as exc:
        raise SystemExit("Invalid configuration file {}: {}".format(cfg_path, exc))
    cfg.update({key: value for key, value in user_cfg.items() if key in DEFAULTS})
    return cfg
