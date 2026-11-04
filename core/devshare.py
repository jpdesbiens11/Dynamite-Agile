"""Development sharing on the local network (D-B-091): let a colleague on the same network use the development server
of this computer -- without a production server and without IT -- while the platform is still being developed.

Started by `python lancer_dev.py reseau` (or `app_dynamite_agile.py --lan`), development mode only:
- listens on every interface, HTTPS with the development CA (tools/make_dev_ca.py, the certificate names the LAN
  addresses of this computer), port 8443; the usual http://localhost:8080 only redirects to it;
- only private-network addresses may connect (10/8, 172.16/12, 192.168/16, VPN 100.64/10, IPv6 ULA / link-local),
  or only the addresses given with --allow (« lan_allow »); everybody else gets 403 before any page;
- the development « admin / admin » opens only from this computer: the colleague gets his own account
  (Admin → Utilisateurs), and the sign-in page is pre-filled only on this computer.
Not a production setting: production is deploy/TLS.md (dev_mode false, a real certificate).
"""
import ipaddress
import socket

from . import auth
from .errors import ApiError

PRIVATE = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10",
                                              "169.254.0.0/16", "fc00::/7", "fe80::/10")]
LAN_PORT = 8443
ADMIN_REMOTE = ("Le compte admin / admin de développement ne s'ouvre que sur le poste qui fait tourner le serveur. "
                "Correctif : connectez-vous avec le compte que l'on vous a créé (Admin → Utilisateurs sur ce poste).")


def _address(ip):
    try:
        address = ipaddress.ip_address(str(ip).split("%")[0])
    except ValueError:
        return None
    return address.ipv4_mapped or address if address.version == 6 else address


def is_local(ip):
    address = _address(ip)
    return bool(address and address.is_loopback)


def parse_allow(values):
    """« lan_allow » / --allow entries (IP or CIDR) -> networks; raises ValueError with the bad entry."""
    out = []
    for value in values or ():
        try:
            out.append(ipaddress.ip_network(str(value).strip(), strict=False))
        except ValueError:
            raise ValueError("adresse « {} » invalide (ex. 192.168.1.40 ou 192.168.1.0/24)".format(value))
    return out


def client_allowed(cfg, ip):
    """Every client when not sharing; when sharing: this computer, then the allow list, else private networks only."""
    if not cfg.get("lan_share"):
        return True
    address = _address(ip)
    if address is None:
        return False
    if address.is_loopback:
        return True
    networks = parse_allow(cfg.get("lan_allow")) or PRIVATE + parse_allow(cfg.get("lan_local_nets"))
    return any(address in net for net in networks if net.version == address.version)


def prefill(cfg, ip):
    """The sign-in page is pre-filled with admin / admin only in development, and only on this computer."""
    return bool(cfg.get("dev_mode")) and (not cfg.get("lan_share") or is_local(ip))


def guard_login(ctx, username):
    """Refuse the development admin / admin from another computer (the password is known by everybody)."""
    if not ctx.config.get("lan_share") or is_local(ctx.ip):
        return
    if str(username or "").strip().lower() != auth.INITIAL_ADMIN_USERNAME:
        return
    row = ctx.conn.execute("SELECT password_hash FROM users WHERE username = ?", (auth.INITIAL_ADMIN_USERNAME,)).fetchone()
    if row and auth.verify_password("admin", row["password_hash"]):
        raise ApiError(403, ADMIN_REMOTE)


def lan_addresses():
    """IPv4 addresses of this computer on the local network (no packet is sent: a UDP connect only picks the route)."""
    found = []
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        found.append(probe.getsockname()[0])
    except OSError:
        pass
    finally:
        probe.close()
    try:
        found += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    out = []
    for ip in found:
        address = _address(ip)
        if address and not address.is_loopback and not address.is_unspecified and ip not in out:
            out.append(ip)
    return out


def local_nets(addresses):
    """The /24 of each address of this computer: some company networks use public ranges internally."""
    return [str(ipaddress.ip_network(ip + "/24", strict=False)) for ip in addresses if ":" not in ip]


def banner(cfg, scheme, port, addresses, ca_path="data/tls/ca.crt"):
    """Console text shown at start-up: what to give the colleague, and what is (not) protected."""
    allow = cfg.get("lan_allow") or []
    lines = ["=" * 72,
             " PARTAGE RÉSEAU (développement) — pas un serveur de production",
             "   Sur ce poste     : {}://localhost:{}".format(scheme, port)]
    for ip in addresses or ["(adresse réseau introuvable : ipconfig)"]:
        lines.append("   Pour un collègue : {}://{}:{}".format(scheme, ip, port))
    lines.append("   Accès permis     : " + (", ".join(allow) if allow else "réseaux privés et le sous-réseau de ce poste ({})".format(
        ", ".join(cfg.get("lan_local_nets") or []) or "—")))
    if scheme == "https":
        lines.append("   Certificat       : {} à envoyer au collègue (sinon : avertissement du navigateur)".format(ca_path))
    else:
        lines.append("   ! HTTP clair : openssl introuvable, les échanges sont lisibles sur le réseau.")
    lines += ["   admin / admin    : seulement depuis ce poste. Compte du collègue : Admin → Utilisateurs.",
              "   Pare-feu Windows : autoriser Python sur les réseaux privés, sinon le collègue ne voit rien.",
              "   Arrêt            : Ctrl+C, ou fermer cette fenêtre.",
              "=" * 72]
    return "\n".join(lines)
