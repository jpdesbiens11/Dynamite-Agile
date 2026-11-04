#!/usr/bin/env bash
# Dynamite | Agile -- installation on a Linux server (Ubuntu 22.04 / 24.04 or Debian 12).
#
# In one command, on the server (the script fetches the code into /opt/dynamite_agile, then installs):
#   curl -fsSL <site>/install.sh | sudo bash -s -- atelier.mon-domaine.ca moi@exemple.ca     # online, HTTPS
#   curl -fsSL <site>/install.sh | sudo bash -s -- --essai                                   # private trial
# Or from a clone:  sudo bash /opt/dynamite_agile/deploy/install.sh atelier.mon-domaine.ca moi@exemple.ca
#
# Online: the domain (A record) points to the IP of the server, ports 22, 80 and 443 are open in the host's panel
# firewall; system packages, firewall, « dynamite » system user, Let's Encrypt certificate (renewed automatically),
# data/config.json for production (dev_mode false, HTTPS on 443, redirect from 80), systemd service, first admin
# password. Trial (--essai): no domain, nothing exposed; the service listens on 127.0.0.1:8080 in development mode
# (example team, admin / admin), reached through an SSH tunnel. Idempotent: run it again, data/ is kept.
set -euo pipefail

REPO="${DA_REPO:-https://github.com/OWNER/dynamite-agile.git}"
TARGET=/opt/dynamite_agile
SERVICE=dynamite-agile

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[31mErreur : %s\033[0m\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || fail "lancez la commande avec sudo (ou en root)."

MODE=online
if [ "${1:-}" = "--essai" ]; then MODE=trial; DOMAIN=""; EMAIL=""; else DOMAIN="${1:-}"; EMAIL="${2:-}"; fi
if [ "$MODE" = online ] && { [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; }; then
  fail "il manque le domaine ou le courriel. Exemple : sudo bash install.sh atelier.mon-domaine.ca moi@exemple.ca   (ou --essai sans domaine)"
fi

# ---------- 0. the code: when the script runs from curl (no clone yet), fetch it, then run the copy of the clone ----------
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")/.." 2>/dev/null && pwd || pwd)"
if [ ! -f "$HERE/app_dynamite_agile.py" ]; then
  say "0/7 Récupération du code dans $TARGET"
  apt-get update -q && apt-get install -y -q git
  if [ -d "$TARGET/.git" ]; then git -C "$TARGET" pull --ff-only; else git clone --depth 1 "$REPO" "$TARGET"; fi
  exec bash "$TARGET/deploy/install.sh" "$@"
fi
APP_DIR="$HERE"
DATA_DIR="$APP_DIR/data"
[ "$APP_DIR" = "$TARGET" ] || fail "le code doit être dans $TARGET (ici : $APP_DIR). Correctif : sudo git clone $REPO $TARGET"

say "1/7 Paquets du système (python3, git, certbot, ufw)"
apt-get update -q
apt-get install -y -q python3 git certbot ufw
python3 -c 'import sys; assert sys.version_info >= (3, 10), sys.version' || fail "Python 3.10 ou plus récent est requis."

say "2/7 Pare-feu"
ufw allow OpenSSH >/dev/null
if [ "$MODE" = online ]; then ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; fi
ufw --force enable >/dev/null
ufw status | sed -n '1,12p'

say "3/7 Utilisateur système « dynamite »"
id dynamite >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin dynamite
mkdir -p "$DATA_DIR/tls"
systemctl stop "$SERVICE" 2>/dev/null || true

if [ "$MODE" = online ]; then
  say "4/7 Certificat HTTPS Let's Encrypt pour $DOMAIN"
  ADDR="$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}')"
  [ -n "$ADDR" ] || fail "le domaine $DOMAIN ne répond pas encore. Correctif : créez l'enregistrement A vers l'IP du serveur, attendez quelques minutes, relancez."
  hostname -I | tr ' ' '\n' | grep -qx "$ADDR" \
    || echo "  Attention : $DOMAIN pointe vers $ADDR, qui n'est pas une adresse de ce serveur ($(hostname -I)). On essaie quand même."
  if ss -ltnH '( sport = :80 or sport = :443 )' | grep -q .; then
    ss -ltnp '( sport = :80 or sport = :443 )'
    fail "les ports 80 ou 443 sont déjà pris par un autre programme (ci-dessus, souvent une application Docker). Correctif : arrêtez-le (docker ps, puis docker stop <nom>), ou utilisez un autre serveur."
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
  sh "$HOOK"
else
  say "4/7 Essai privé : pas de certificat, rien d'exposé sur Internet"
fi

say "5/7 Configuration (data/config.json)"
python3 - "$DATA_DIR/config.json" "$MODE" "$DOMAIN" <<'EOF'
import json, sys
from pathlib import Path
path, mode, domain = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
if mode == "online":
    cfg.update({"host": "0.0.0.0", "port": 443, "tls_cert": "tls/server.crt", "tls_key": "tls/server.key",
                "http_redirect_port": 80, "public_name": domain, "dev_mode": False})
    print("  production : https://{} (port 443, redirection depuis 80), mode développement coupé".format(domain))
else:
    cfg.update({"host": "127.0.0.1", "port": 8080, "tls_cert": "", "tls_key": "", "http_redirect_port": 0,
                "public_name": "", "dev_mode": True})
    print("  essai privé : http://127.0.0.1:8080 sur le serveur seulement, équipe d'exemple, admin / admin")
path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
EOF
chown -R dynamite:dynamite "$APP_DIR"

say "6/7 Service « $SERVICE » (démarre aussi au redémarrage du serveur)"
install -m 644 "$APP_DIR/deploy/dynamite-agile.service" /etc/systemd/system/dynamite-agile.service
systemctl daemon-reload
systemctl enable --now "$SERVICE"
sleep 4
systemctl is-active --quiet "$SERVICE" || { journalctl -u "$SERVICE" -n 30 --no-pager; fail "le service ne démarre pas (journal ci-dessus)."; }
echo "  Service actif."

say "7/7 C'est installé"
if [ "$MODE" = online ]; then
  echo "  Ouvrez :  https://$DOMAIN"
  if [ -f "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt" ]; then
    echo "  Compte administrateur (mot de passe temporaire, à changer à la première connexion) :"
    sed 's/^/    /' "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt"
  else
    echo "  Le compte admin existe déjà. Mot de passe oublié : sudo -u dynamite python3 $APP_DIR/app_dynamite_agile.py --reset-password admin"
  fi
else
  IP="$(hostname -I | awk '{print $1}')"
  echo "  Sur VOTRE ordinateur, dans un nouveau terminal, laissez tourner :"
  echo "    ssh -N -L 8080:127.0.0.1:8080 root@$IP"
  echo "  puis ouvrez  http://127.0.0.1:8080  (admin / admin, équipe d'exemple : nina, lea, hugo, alexis / admin)."
  echo "  Passer en ligne plus tard : relancez la commande avec votre domaine et votre courriel."
fi
echo
echo "  Mettre à jour plus tard :  sudo bash $APP_DIR/deploy/redeploy.sh"
