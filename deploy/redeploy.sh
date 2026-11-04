#!/usr/bin/env bash
# Dynamite | Agile -- update the code on the server to the latest version of the repository, then restart.
#   sudo bash /opt/dynamite_agile/deploy/redeploy.sh
# The data (data/: database, attachments, configuration, certificates) is never touched by git.
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sudo -u dynamite git -C "$APP_DIR" pull --ff-only
systemctl restart dynamite-agile
sleep 2
systemctl status dynamite-agile --no-pager -n 10
