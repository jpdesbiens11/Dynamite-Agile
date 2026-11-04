"""Behind a reverse proxy (0.60.17, D-O-029): Traefik, Caddy or nginx terminates HTTPS and passes the requests on.

Some servers already have a proxy on ports 80 and 443 (Hostinger VPS with Docker applications: Traefik, which obtains
the Let's Encrypt certificates). Dynamite | Agile then listens in plain HTTP on a private network (its own Docker
network, or the loopback) and the proxy forwards to it. Fail closed is kept:
  - « trusted_proxies » (config.json) lists the addresses or CIDR blocks of the proxy; empty = this mode is off;
  - a request from a trusted proxy carries the visitor's address (last X-Forwarded-For entry, the one the proxy added)
    and the scheme it was received in (X-Forwarded-Proto): « https » makes the request secure (Secure cookie,
    __Host- prefix), exactly as if the server had TLS itself;
  - any other client is refused in production (403): nobody reaches the server around the proxy, in clear text.
"""
import ipaddress

FORWARDED_FOR = "X-Forwarded-For"
FORWARDED_PROTO = "X-Forwarded-Proto"


def networks(cfg):
    out = []
    for item in cfg.get("trusted_proxies") or []:
        try:
            out.append(ipaddress.ip_network(str(item).strip(), strict=False))
        except ValueError:
            continue
    return out


def enabled(cfg):
    return bool(networks(cfg))


def trusted(cfg, peer_ip):
    try:
        addr = ipaddress.ip_address(str(peer_ip))
    except ValueError:
        return False
    return any(addr in net for net in networks(cfg))


def _last_address(value):
    for part in reversed([p.strip() for p in str(value or "").split(",")]):
        try:
            return str(ipaddress.ip_address(part))
        except ValueError:
            continue
    return ""


def client(cfg, peer_ip, headers, use_tls):
    """(visitor ip, secure) for one request."""
    if not use_tls and trusted(cfg, peer_ip):
        ip = _last_address(headers.get(FORWARDED_FOR)) or str(peer_ip)
        return ip, str(headers.get(FORWARDED_PROTO) or "").strip().lower() == "https"
    return str(peer_ip), bool(use_tls)


def refused(cfg, peer_ip, use_tls):
    """True when, in proxy mode and in production, the request does not come through the proxy."""
    if use_tls or cfg.get("dev_mode") or not enabled(cfg):
        return False
    return not trusted(cfg, peer_ip)


REFUSED = ("Accès direct refusé : ce serveur est derrière un proxy HTTPS. Correctif : ouvrez l'adresse https:// de "
           "l'outil plutôt que son port interne.")
