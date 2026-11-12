#!/bin/sh
# DynamiteAgile, read only (0.60.37, D-O-044): the one command Bob le mineur uses to read the tool.
#   dynamite spaces
#   dynamite search "<mots>" [SPACE]
#   dynamite pages SPACE
#   dynamite point SPACE "<écran ou #/…>" "<texte à montrer>" ["<note>"]
#   dynamite summary SPACE
# The key: DA_BOT_TOKEN in the environment, otherwise the line DA_BOT_TOKEN=… of the agent's .env file.
URL="${DA_URL:-{{URL}}}"
TOKEN="${DA_BOT_TOKEN:-}"
for f in "${DA_ENV_FILE:-}" /opt/data/.env "$HOME/.env"; do
  [ -z "$TOKEN" ] && [ -n "$f" ] && [ -r "$f" ] && TOKEN=$(grep '^DA_BOT_TOKEN=' "$f" | tail -1 | cut -d= -f2-)
done
if [ -z "$TOKEN" ]; then
  echo "Pas de clé DA_BOT_TOKEN. Correctif : l'administrateur crée une clé dans ⚙ Admin → Bob et la met dans le .env de l'agent."
  exit 2
fi

get() {
  route=$1; shift
  # 0.60.97 (D-O-103): the key goes through stdin (-H @-), never on curl's command line where `ps` shows it
  printf 'Authorization: Bearer %s\n' "$TOKEN" | curl -sS -G --max-time 20 -H @- "$@" "$URL/api/bot/v1/$route"
  echo
}

case "$1" in
  spaces)  get spaces ;;
  search)  [ -n "$2" ] || { echo "Usage : dynamite search \"<mots>\" [SPACE]"; exit 1; }
           if [ -n "$3" ]; then get search --data-urlencode "q=$2" --data-urlencode "space=$3"
           else get search --data-urlencode "q=$2"; fi ;;
  pages)   [ -n "$2" ] || { echo "Usage : dynamite pages SPACE"; exit 1; }
           get pages --data-urlencode "space=$2" ;;
  point)   [ -n "$4" ] || { echo "Usage : dynamite point SPACE \"<écran>\" \"<texte à montrer>\" [\"<note>\"]"; exit 1; }
           get point --data-urlencode "space=$2" --data-urlencode "page=$3" --data-urlencode "focus=$4" --data-urlencode "note=$5" ;;
  summary) [ -n "$2" ] || { echo "Usage : dynamite summary SPACE"; exit 1; }
           get summary --data-urlencode "space=$2" ;;
  *)       sed -n '3,7p' "$0" | sed 's/^# *//' ;;
esac
