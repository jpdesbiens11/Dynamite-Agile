#!/usr/bin/env bash
# Dynamite | Agile -- installation on a Linux server (Ubuntu 22.04 / 24.04 or Debian 12).
#
# In one command, on the server (the script fetches the code into /opt/dynamite_agile, then installs):
#   curl -fsSL <site>/install.sh | sudo bash -s -- atelier.mon-domaine.ca moi@exemple.ca     # online, HTTPS
#   curl -fsSL <site>/install.sh | sudo bash -s -- --essai                                   # private trial
#   curl -fsSL <site>/install.sh | sudo bash -s -- --traefik dynamite.srv123.hstgr.cloud      # behind Traefik (0.60.17)
# Or from a clone:  sudo bash /opt/dynamite_agile/deploy/install.sh atelier.mon-domaine.ca moi@exemple.ca
#
# Online: the domain (A record) points to the IP of the server, ports 22, 80 and 443 are open in the host's panel
# firewall; system packages, firewall, « dynamite » system user, Let's Encrypt certificate (renewed automatically),
# data/config.json for production (dev_mode false, HTTPS on 443, redirect from 80), systemd service, first admin
# password. Trial (--essai): no domain, nothing exposed; the service listens on 127.0.0.1:8080 in development mode
# (example team, admin / admin), reached through an SSH tunnel. Idempotent: run it again, data/ is kept.
# Messages in French by default, in English with DA_LANG=en (sudo DA_LANG=en bash -s -- …).
set -euo pipefail

REPO="${DA_REPO:-https://github.com/jpdesbiens11/Dynamite-Agile.git}"
TARGET="${DA_DIR:-/opt/dynamite_agile}"   # another folder: DA_DIR=/opt/autre (0.60.17, a second instance on the same server)
SERVICE=dynamite-agile

EN=0; case "${DA_LANG:-fr}" in en*) EN=1 ;; esac
t() { if [ "$EN" = 1 ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }   # t "français" "English"
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[31m%s %s\033[0m\n' "$(t "Erreur :" "Error:")" "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || fail "$(t "lancez la commande avec sudo (ou en root)." "run the command with sudo (or as root).")"

MODE=online
if [ "${1:-}" = "--essai" ]; then MODE=trial; DOMAIN=""; EMAIL=""
elif [ "${1:-}" = "--traefik" ]; then MODE=traefik; DOMAIN="${2:-}"; EMAIL=""  # D-O-029: Traefik keeps 80 / 443
else DOMAIN="${1:-}"; EMAIL="${2:-}"; fi
if [ "$MODE" = online ] && { [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; }; then
  fail "$(t "il manque le domaine ou le courriel. Exemple : sudo bash install.sh atelier.mon-domaine.ca moi@exemple.ca   (ou --essai sans domaine)" "the domain or the email is missing. Example: sudo DA_LANG=en bash install.sh workshop.my-domain.com me@example.com   (or --essai without a domain)")"
fi
[ "$MODE" = traefik ] || [ "$TARGET" = /opt/dynamite_agile ] || fail "$(t "DA_DIR ne sert qu'avec --traefik (le service systemd attend /opt/dynamite_agile)." "DA_DIR is only for --traefik (the systemd service expects /opt/dynamite_agile).")"

# ---------- 0. the code: when the script runs from curl (no clone yet), fetch it, then run the copy of the clone ----------
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")/.." 2>/dev/null && pwd || pwd)"
if [ ! -f "$HERE/app_dynamite_agile.py" ]; then
  say "0/7 $(t "Récupération du code dans" "Fetching the code into") $TARGET"
  # 0.60.17: a folder that is not a clone of this repository (another application, an older private copy) is never touched.
  if [ -d "$TARGET/.git" ] && ! git -C "$TARGET" remote get-url origin 2>/dev/null | grep -qi 'dynamite-agile'; then
    fail "$(t "$TARGET contient un autre dépôt git ; rien n'a été modifié. Correctif : choisissez un autre dossier, par exemple  curl … | sudo DA_DIR=/opt/dynamite-agile-open bash -s -- …" "$TARGET holds another git repository; nothing was changed. Fix: choose another folder, for example  curl … | sudo DA_DIR=/opt/dynamite-agile-open bash -s -- …")"
  fi
  if [ ! -d "$TARGET/.git" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
    fail "$(t "$TARGET existe déjà et n'est pas une installation de ce dépôt (une version plus ancienne ?) ; rien n'a été modifié. Correctif : installez à côté, dans un autre dossier :  curl … | sudo DA_DIR=/opt/dynamite-agile-open bash -s -- …" "$TARGET already exists and is not an installation of this repository (an older version?); nothing was changed. Fix: install next to it, in another folder:  curl … | sudo DA_DIR=/opt/dynamite-agile-open bash -s -- …")"
  fi
  apt-get update -q && apt-get install -y -q git
  if [ -d "$TARGET/.git" ]; then
    # 0.60.12 (D-O-024): files changed since the last update (a package applied in Admin → Update, an edit by hand) never
    # block it: they are saved as a patch in data/updates/, then the code follows the published branch; data/ stays.
    if [ -n "$(git -C "$TARGET" status --porcelain --untracked-files=no)" ]; then
      mkdir -p "$TARGET/data/updates"; SAVED="$TARGET/data/updates/code-local-$(date +%Y%m%d-%H%M%S).patch"
      git -C "$TARGET" diff > "$SAVED"; say "$(t "Code modifié sur ce serveur : copie dans" "Code changed on this server: copy in") $SAVED"
    fi
    git -C "$TARGET" fetch --depth 1 origin && git -C "$TARGET" reset --hard '@{u}'
  else git clone --depth 1 "$REPO" "$TARGET"; fi
  exec bash "$TARGET/deploy/install.sh" "$@"
fi
APP_DIR="$HERE"
DATA_DIR="$APP_DIR/data"
# 0.60.34: a server whose web is already held by Traefik (Hostinger VPS with Docker applications) gets the installation
# behind it even with the usual command -- before any firewall or certificate change (the email is not needed there).
if [ "$MODE" = online ] && command -v docker >/dev/null 2>&1 \
   && docker ps 2>/dev/null | grep -qi traefik; then
  say "$(t "Traefik détecté : il garde les ports 80 / 443 et le certificat ; installation derrière lui (comme --traefik)" "Traefik detected: it keeps ports 80 / 443 and the certificate; installing behind it (as --traefik)")"
  MODE=traefik
fi
if [ "$MODE" = traefik ]; then exec bash "$APP_DIR/deploy/install_traefik.sh" "$DOMAIN"; fi
[ "$APP_DIR" = "$TARGET" ] || fail "$(t "le code doit être dans $TARGET (ici : $APP_DIR). Correctif : sudo git clone $REPO $TARGET" "the code must be in $TARGET (here: $APP_DIR). Fix: sudo git clone $REPO $TARGET")"

say "1/7 $(t "Paquets du système" "System packages") (python3, git, certbot, ufw)"
apt-get update -q
apt-get install -y -q python3 git certbot ufw iproute2
python3 -c 'import sys; assert sys.version_info >= (3, 10), sys.version' || fail "$(t "Python 3.10 ou plus récent est requis." "Python 3.10 or newer is required.")"

say "2/7 $(t "Pare-feu" "Firewall")"
ufw allow OpenSSH >/dev/null
if [ "$MODE" = online ]; then ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; fi
ufw --force enable >/dev/null
ufw status | sed -n '1,12p'

say "3/7 $(t "Utilisateur système" "System user") « dynamite »"
id dynamite >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin dynamite
mkdir -p "$DATA_DIR/tls"
systemctl stop "$SERVICE" 2>/dev/null || true

if [ "$MODE" = online ]; then
  say "4/7 $(t "Certificat HTTPS Let's Encrypt pour" "Let's Encrypt HTTPS certificate for") $DOMAIN"
  ADDR="$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}')"
  [ -n "$ADDR" ] || fail "$(t "le domaine $DOMAIN ne répond pas encore. Correctif : créez l'enregistrement A vers l'IP du serveur, attendez quelques minutes, relancez." "the domain $DOMAIN does not answer yet. Fix: create the A record to the server's IP, wait a few minutes, run again.")"
  hostname -I | tr ' ' '\n' | grep -qx "$ADDR" \
    || echo "  $(t "Attention : $DOMAIN pointe vers $ADDR, qui n'est pas une adresse de ce serveur" "Warning: $DOMAIN points to $ADDR, which is not an address of this server") ($(hostname -I)). $(t "On essaie quand même." "Trying anyway.")"
  if ss -ltnH '( sport = :80 or sport = :443 )' | grep -q .; then
    ss -ltnp '( sport = :80 or sport = :443 )'
    fail "$(t "les ports 80 ou 443 sont déjà pris par un autre programme (ci-dessus, souvent Traefik, le portier des applications Docker). Correctif : s'il s'agit de Traefik, installez derrière lui : sudo bash $APP_DIR/deploy/install.sh --traefik $DOMAIN" "ports 80 or 443 are already in use by another program (above, often Traefik, the gate of Docker applications). Fix: if it is Traefik, install behind it: sudo DA_LANG=en bash $APP_DIR/deploy/install.sh --traefik $DOMAIN")"
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
  say "4/7 $(t "Essai privé : pas de certificat, rien d'exposé sur Internet" "Private trial: no certificate, nothing exposed to the Internet")"
fi

say "5/7 Configuration (data/config.json)"
python3 - "$DATA_DIR/config.json" "$MODE" "$DOMAIN" "$EN" <<'EOF'
import json, sys
from pathlib import Path
path, mode, domain, en = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4] == "1"
cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
if mode == "online":
    cfg.update({"host": "0.0.0.0", "port": 443, "tls_cert": "tls/server.crt", "tls_key": "tls/server.key",
                "http_redirect_port": 80, "public_name": domain, "dev_mode": False})
    print(("  production: https://{} (port 443, redirect from 80), development mode off" if en else
           "  production : https://{} (port 443, redirection depuis 80), mode développement coupé").format(domain))
else:
    cfg.update({"host": "127.0.0.1", "port": 8080, "tls_cert": "", "tls_key": "", "http_redirect_port": 0,
                "public_name": "", "dev_mode": True})
    print("  private trial: http://127.0.0.1:8080 on the server only, example team, admin / admin" if en else
          "  essai privé : http://127.0.0.1:8080 sur le serveur seulement, équipe d'exemple, admin / admin")
path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
EOF
chown -R dynamite:dynamite "$APP_DIR"

say "6/7 Service « $SERVICE » ($(t "démarre aussi au redémarrage du serveur" "also starts when the server reboots"))"
install -m 644 "$APP_DIR/deploy/dynamite-agile.service" /etc/systemd/system/dynamite-agile.service
systemctl daemon-reload
systemctl enable --now "$SERVICE"
sleep 4
systemctl is-active --quiet "$SERVICE" || { journalctl -u "$SERVICE" -n 30 --no-pager; fail "$(t "le service ne démarre pas (journal ci-dessus)." "the service does not start (log above).")"; }
echo "  $(t "Service actif." "Service running.")"

say "7/7 $(t "C'est installé" "Installed")"
if [ "$MODE" = online ]; then
  echo "  $(t "Ouvrez :" "Open:")  https://$DOMAIN"
  if [ -f "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt" ]; then
    echo "  $(t "Compte administrateur (mot de passe temporaire, à changer à la première connexion) :" "Administrator account (temporary password, to change at first login):")"
    sed 's/^/    /' "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt"
  else
    echo "  $(t "Le compte admin existe déjà. Mot de passe oublié :" "The admin account already exists. Forgotten password:") sudo -u dynamite python3 $APP_DIR/app_dynamite_agile.py --reset-password admin"
  fi
else
  IP="$(hostname -I | awk '{print $1}')"
  echo "  $(t "Sur VOTRE ordinateur, dans un nouveau terminal, laissez tourner :" "On YOUR computer, in a new terminal, leave this running:")"
  echo "    ssh -N -L 8080:127.0.0.1:8080 root@$IP"
  echo "  $(t "puis ouvrez" "then open")  http://127.0.0.1:8080  (admin / admin; $(t "équipe d'exemple" "example team"): nina, lea, hugo, alexis / admin)."
  echo "  $(t "Passer en ligne plus tard : relancez la commande avec votre domaine et votre courriel." "Going online later: run the command again with your domain and your email.")"
fi
echo
echo "  $(t "Mettre à jour plus tard :" "Updating later:")  sudo bash $APP_DIR/deploy/redeploy.sh"
