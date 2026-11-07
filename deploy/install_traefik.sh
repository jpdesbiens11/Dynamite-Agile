#!/usr/bin/env bash
# Dynamite | Agile -- installation behind Traefik (0.60.17, D-O-029), called by deploy/install.sh --traefik <domain>.
#
# For a server where Traefik already holds ports 80 and 443 (Hostinger VPS with Docker applications): Traefik keeps
# them and obtains the Let's Encrypt certificate; Dynamite | Agile runs in its own container (python:3.12-slim, the code
# of /opt/dynamite_agile mounted, data in /opt/dynamite_agile/data), found by Traefik through its labels, like the
# other applications. Nothing else is changed: no firewall rule, no other container, no Traefik setting.
# The server listens in plain HTTP on its private Docker network only, and trusts only that network as its proxy
# (core/proxy.py): any other client is refused. Run it again to update: the code follows the published branch,
# the container restarts, data/ is kept.
set -euo pipefail

DOMAIN="${1:-}"
shift || true
ALSO="$*"  # 0.60.71 (D-O-077): other addresses served too (the old one, while shared links still point to it)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # the clone (/opt/dynamite_agile)
DATA_DIR="$APP_DIR/data"
NAME="$(basename "$APP_DIR" | tr 'A-Z_' 'a-z-' | tr -cd 'a-z0-9-')"          # /opt/dynamite_agile -> dynamite-agile
STACK="${DA_STACK_DIR:-/docker/$NAME}"                 # next to the other Docker applications of the host
EN=0; case "${DA_LANG:-fr}" in en*) EN=1 ;; esac
t() { if [ "$EN" = 1 ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[31m%s %s\033[0m\n' "$(t "Erreur :" "Error:")" "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || [ -n "${DA_STACK_DIR:-}" ] || fail "$(t "lancez la commande avec sudo (ou en root)." "run the command with sudo (or as root).")"
[ -n "$DOMAIN" ] || fail "$(t "il manque l'adresse. Exemple : sudo bash install.sh --traefik dynamite.srv123.hstgr.cloud" "the address is missing. Example: sudo DA_LANG=en bash install.sh --traefik dynamite.srv123.hstgr.cloud")"

say "1/5 $(t "Vérifications : Docker, Traefik et l'adresse" "Checks: Docker, Traefik and the address") $DOMAIN"
docker compose version >/dev/null 2>&1 || fail "$(t "Docker Compose est introuvable sur ce serveur. Correctif : utilisez l'installation habituelle (sans --traefik)." "Docker Compose not found on this server. Fix: use the usual installation (without --traefik).")"
TRAEFIK="$(docker ps --format '{{.Names}} {{.Image}}' | awk '$2 ~ /traefik/ {print $1; exit}')"
[ -n "$TRAEFIK" ] || fail "$(t "aucun conteneur Traefik ne tourne. Correctif : utilisez l'installation habituelle (sans --traefik)." "no Traefik container is running. Fix: use the usual installation (without --traefik).")"
RESOLVER="$(docker inspect -f '{{join .Args " "}}' "$TRAEFIK" | grep -o 'certificatesresolvers\.[A-Za-z0-9_-]*' | head -1 | cut -d. -f2)"
RESOLVER="${RESOLVER:-letsencrypt}"
ENTRY="$(docker inspect -f '{{join .Args " "}}' "$TRAEFIK" | grep -o 'entrypoints\.[A-Za-z0-9_-]*\.address=:443' | head -1 | cut -d. -f2)"
ENTRY="${ENTRY:-websecure}"
echo "  Traefik : $TRAEFIK · $(t "point d'entrée" "entry point") $ENTRY · $(t "certificats" "certificates") $RESOLVER"
getent hosts "$DOMAIN" >/dev/null || fail "$(t "l'adresse $DOMAIN ne répond pas. Correctif : créez l'enregistrement DNS vers ce serveur, attendez quelques minutes, relancez." "the address $DOMAIN does not answer. Fix: create the DNS record to this server, wait a few minutes, run again.")"
echo "  DNS : $(getent hosts "$DOMAIN" | awk '{print $1}' | tr '\n' ' ')"
RULE="Host(\`$DOMAIN\`)"
for extra in $ALSO; do
  case "$extra" in *[!A-Za-z0-9.-]*|"") fail "$(t "adresse invalide : $extra" "invalid address: $extra")" ;; esac
  RULE="$RULE || Host(\`$extra\`)"
  echo "  $(t "Aussi servie :" "Also served:") $extra"
done

say "2/5 Configuration (data/config.json)"
mkdir -p "$DATA_DIR"
# The systemd service of a previous installation IN THIS FOLDER only; another instance of the server keeps running.
if [ "$(systemctl show -p WorkingDirectory --value dynamite-agile 2>/dev/null)" = "$APP_DIR" ]; then
  systemctl disable --now dynamite-agile 2>/dev/null || true
fi
python3 - "$DATA_DIR/config.json" "$DOMAIN" "$EN" <<'EOF'
import json, sys
from pathlib import Path
path, domain, en = Path(sys.argv[1]), sys.argv[2], sys.argv[3] == "1"
cfg = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
cfg.update({"host": "0.0.0.0", "port": 8080, "tls_cert": "", "tls_key": "", "http_redirect_port": 0,
            "public_name": domain, "dev_mode": False, "trusted_proxies": ["172.16.0.0/12", "192.168.0.0/16"]})
path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
print(("  behind Traefik: https://{} (HTTPS by Traefik), development mode off" if en else
       "  derrière Traefik : https://{} (HTTPS par Traefik), mode développement coupé").format(domain))
EOF

say "3/5 $(t "Le conteneur et ses étiquettes Traefik" "The container and its Traefik labels") ($STACK)"
mkdir -p "$STACK"
cat > "$STACK/docker-compose.yml" <<EOF
# Dynamite | Agile behind Traefik -- written by deploy/install_traefik.sh (D-O-029). Run the installation again to update.
services:
  dynamite-agile:
    image: python:3.12-slim
    restart: unless-stopped
    working_dir: /app
    command: ["python3", "app_dynamite_agile.py"]
    environment:
      - PYTHONUNBUFFERED=1
      - TZ=America/Toronto
    volumes:
      - $APP_DIR:/app
    labels:
      - traefik.enable=true
      - traefik.http.routers.$NAME.rule=$RULE
      - traefik.http.routers.$NAME.entrypoints=$ENTRY
      - traefik.http.routers.$NAME.tls.certresolver=$RESOLVER
      - traefik.http.routers.$NAME.middlewares=$NAME-sec
      - traefik.http.middlewares.$NAME-sec.headers.stsSeconds=31536000
      - traefik.http.middlewares.$NAME-sec.headers.contentTypeNosniff=true
      - traefik.http.services.$NAME.loadbalancer.server.port=8080
EOF
echo "  $STACK/docker-compose.yml"

say "4/5 $(t "Démarrage" "Start")"
docker compose -f "$STACK/docker-compose.yml" up -d --force-recreate
for _ in $(seq 1 45); do   # the server writes « Listening on … » once it accepts requests (first start: up to a minute)
  if docker compose -f "$STACK/docker-compose.yml" logs --no-color 2>/dev/null | grep -q "Listening on"; then break; fi
  sleep 2
done
STATE="$(docker inspect -f '{{.State.Status}}' "$(docker compose -f "$STACK/docker-compose.yml" ps -q dynamite-agile)")"
[ "$STATE" = running ] || { docker compose -f "$STACK/docker-compose.yml" logs --tail 40 --no-color; fail "$(t "le conteneur ne tourne pas (journal ci-dessus)." "the container is not running (log above).")"; }
echo "  $(t "Conteneur actif." "Container running.")"

say "5/5 $(t "C'est installé" "Installed")"
echo "  $(t "Ouvrez :" "Open:")  https://$DOMAIN"
echo "  $(t "(le premier chargement peut prendre une minute : Traefik obtient le certificat HTTPS)" "(the first load may take a minute: Traefik obtains the HTTPS certificate)")"
if [ -f "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt" ]; then
  echo "  $(t "Compte administrateur (mot de passe temporaire, à changer à la première connexion) :" "Administrator account (temporary password, to change at first login):")"
  sed 's/^/    /' "$DATA_DIR/INITIAL_ADMIN_PASSWORD.txt"
else
  echo "  $(t "Le compte admin existe déjà. Mot de passe oublié :" "The admin account already exists. Forgotten password:") docker compose -f $STACK/docker-compose.yml exec dynamite-agile python3 app_dynamite_agile.py --reset-password admin"
fi
echo
echo "  $(t "Journal :" "Log:")  docker compose -f $STACK/docker-compose.yml logs -f"
echo "  $(t "Mettre à jour plus tard : relancez la même commande d'installation." "Updating later: run the same installation command again.")"
