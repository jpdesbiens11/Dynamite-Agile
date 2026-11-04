#!/usr/bin/env bash
# Dynamite | Agile -- installation on a Linux VPS (Ubuntu 22.04 / 24.04 or Debian 12), in production, with HTTPS.
#
#   sudo apt update && sudo apt install -y git
#   sudo git clone https://github.com/<compte>/dynamite-agile.git /opt/dynamite_agile
#   sudo bash /opt/dynamite_agile/deploy/install.sh mon-domaine.ca moi@exemple.ca
#
# Before: the domain (A record) points to the IP of the VPS, ports 22, 80 and 443 are open in the host's panel firewall.
# The script is idempotent: run it again after a change of domain, nothing is lost (data/ is kept).
# What it does: system packages, firewall, « dynamite » system user, Let's Encrypt certificate (renewed automatically),
# data/config.json for production (dev_mode false, HTTPS on 443, redirect from 80), systemd service, first admin password.
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$APP_DIR/data"
SERVICE=dynamite-agile

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[31mErreur : %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "lancez le script avec sudo (ou en root)."
[ -n "$DOMAIN" ] && [ -n "$EMAIL" ] || fail "usage : sudo bash deploy/install.sh mon-domaine.ca moi@exemple.ca"
[ "$APP_DIR" = "/opt/dynamite_agile" ] || fail "le code doit être dans /opt/dynamite_agile (ici : $APP_DIR). Correctif : sudo git clone <dépôt> /opt/dynamite_agile"

say "1/7 Paquets du système (python3, git, certbot, ufw)"
apt-get update -q
apt-get install -y -q python3 git certbot ufw
python3 -c 'import sys; assert sys.version_info >= (3, 10), sys.version' || fail "Python 3.10 ou plus récent est requis."

say "2/7 Pare-feu (SSH, 80, 443)"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
ufw status | sed -n '1,12p'

say "3/7 Utilisateur système « dynamite »"
id dynamite >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin dynamite
mkdir -p "$DATA_DIR/tls"

say "4/7 Certificat HTTPS Let's Encrypt pour $DOMAIN"
systemctl stop "$SERVICE" 2>/dev/null || true
if ss -ltnH '( sport = :80 or sport = :443 )' | grep -q .; then
  ss -ltnp '( sport = :80 or sport = :443 )'
  fail "les ports 80 ou 443 sont déjà pris par un autre programme (ci-dessus). Correctif : arrêtez-le, ou installez sur un autre VPS."
fi
certbot certonly --standalone --non-interactive --agree-tos -m "$EMAIL" -d "$DOMAIN" --keep-until-expiring \
  --pre-hook "systemctl stop $SERVICE || true" --post-hook "systemctl start $SERVICE || true"
HOOK=/etc/letsencrypt/renewal-hooks/deploy/dynamite-agile.sh
cat > "$HOOK" <<EOF
#!/bin/sh
# Copies the renewed certificate where the « dynamite » user can read it (installed by deploy/install.sh).
install -m 644 -o dynamite -g dynamite /etc/letsencrypt/live/$DOMAIN/fullchain.pem $DATA_DIR/tls/server.crt
install -m 600 -o dynamite -g dynamite /etc/letsencrypt/live/$DOMAIN/privkey.pem $DATA_DIR/tls/server.key
EOF
chmod 755 "$HOOK"
id dynamite >/dev/null && sh "$HOOK"

say "5/7 Configuration de production (data/config.json)"
python3 - "$DATA_DIR/config.json" "$DOMAIN" <<'EOF'
import json, sys
from pathlib import Path
path, domain = Path(sys.argv[1]), sys.argv[2]
cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
cfg.update({"host": "0.0.0.0", "port": 443, "tls_cert": "tls/server.crt", "tls_key": "tls/server.key",
            "http_redirect_port": 80, "public_name": domain, "dev_mode": False})
path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
print("  {} : host 0.0.0.0, port 443, HTTPS, redirection 80 → 443, dev_mode false".format(path))
EOF
chown -R dynamite:dynamite "$APP_DIR"

say "6/7 Service systemd « $SERVICE »"
install -m 644 "$APP_DIR/deploy/dynamite-agile.service" /etc/systemd/system/dynamite-agile.service
systemctl daemon-reload
systemctl enable --now "$SERVICE"
sleep 3
systemctl --no-pager --lines 5 status "$SERVICE" || fail "le service ne démarre pas. Correctif : journalctl -u $SERVICE -n 50"

say "7/7 Premier accès"
echo "  Ouvrez https://$DOMAIN"
if [ -f "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt" ]; then
  echo "  Compte administrateur initial (mot de passe à changer à la première connexion) :"
  sed 's/^/    /' "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt"
else
  echo "  Le compte administrateur existe déjà. Mot de passe oublié : sudo -u dynamite python3 $APP_DIR/app_dynamite_agile.py --reset-password admin"
fi
echo
echo "  Mise à jour du code plus tard : sudo bash $APP_DIR/deploy/redeploy.sh"
