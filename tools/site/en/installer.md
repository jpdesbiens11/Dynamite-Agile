# Installing Dynamite | Agile — a guide for an AI assistant

This file is for the AI assistant (Claude or another) that a beginner has opened next to their terminal to install
Dynamite | Agile. The illustrated page for people is {{SITE_URL}}/en/installation.html.

## How to guide

- The person is a beginner: one command at a time, saying where to type it (**on their computer** or **on the server**)
  and what they should see. Wait until they paste the result before going on.
- Never ask for a password, a private key or the content of `INITIAL_ADMIN_PASSWORD.txt`: those are only typed or read in
  the terminal. An IP address and a domain name can be shared.
- On a server, the terminal line starts with `root@…` or `user@server-name`. On their computer it looks different
  (`PS C:\…>` on Windows, `…%` or `…$` on macOS / Linux). Help them know where they are.
- With `DA_LANG=en`, every message of the script is in English; each error starts with `Error:` and names the fix: read it
  with them.
- The script is public: {{REPO}}/blob/main/deploy/install.sh

## Four destinations

| Destination | For whom | What is needed |
|---|---|---|
| Online server | A team that connects from anywhere | Linux VPS (Ubuntu 22.04 / 24.04 or Debian 12), root access, a domain name, ports 22, 80 and 443 open |
| Server, private trial | Trying it before having a domain | Linux VPS and root access; nothing exposed, access through an SSH tunnel |
| Windows PC of the team | A team without Linux nor a domain, on its local network | Windows 10 / 11 or Server 2019+, always on, PowerShell as administrator |
| Their computer | Solo trial | Windows, macOS or Linux, Python 3.10 or newer |

## A. Online server

1. **The server**: Ubuntu 24.04 VPS. In the host's control-panel firewall, open 22, 80, 443. At Hostinger: hPanel → VPS →
   *OS & Panel* (system), *Overview* (IP, user `root`, *Root password → Change*), *Security → Firewall*.
2. **The domain**: an **A** record to the server's IP (name `workshop` or `@`). Check on their computer:
   `nslookup workshop.my-domain.com` must show the server's IP.
3. **Log in** (on their computer): `ssh root@IP`; answer `yes` the first time; the password does not show while typing.
   Alternative: the *Web console* button of the control panel.
4. **Install** (on the server), with one command. **Before giving it, confirm the person's case** with a multiple-choice
   question: does their server already run Docker applications with **Traefik** (often a Hostinger VPS with Docker)? To check
   on the server: `docker ps | grep -i traefik` (a line = yes; nothing or « command not
   found » = no).
   - No (the usual case): `curl -fsSL {{SITE_URL}}/install.sh | sudo DA_LANG=en bash -s -- workshop.my-domain.com me@example.com`
   - Yes, Traefik: `curl -fsSL {{SITE_URL}}/install.sh | sudo DA_LANG=en bash -s -- --traefik workshop.my-domain.com` (no email:
     Traefik gets the certificate; no firewall rule is changed).
   - When in doubt, the usual command is enough: it detects Traefik by itself and installs behind it.
   - **Update** later: run exactly the same command again; the data (`data/`) stays.
   The script prints `== 1/7` to `== 7/7 Installed`, then the address and the temporary password of the `admin` account.
   Without curl: `sudo apt update && sudo apt install -y git`, `sudo git clone {{REPO}}.git /opt/dynamite_agile`, then
   `sudo DA_LANG=en bash /opt/dynamite_agile/deploy/install.sh workshop.my-domain.com me@example.com`.
5. **Open** `https://workshop.my-domain.com`, account `admin`, the password shown, then choose a new one. Create the
   team: ⚙ Admin → Comptes → Règles d'accès; the project's Space: ⚙ Admin → Spaces.

## B. Server, private trial

1. `ssh root@IP` (on their computer).
2. On the server: `curl -fsSL {{SITE_URL}}/install.sh | sudo DA_LANG=en bash -s -- --essai`
3. On their computer, in a **new** terminal left open: `ssh -N -L 8080:127.0.0.1:8080 root@IP`
   (it looks frozen: that's normal). Open `http://127.0.0.1:8080`, account `admin` / `admin`, example team.
4. Going online later: follow path A; the same command with domain and email.

## D. Windows PC of the team (local network)

For a team without Linux nor a domain: a Windows 10 / 11 or Server 2019+ PC that stays on hosts the tool, over HTTPS on
the school or office network. The terminal is **PowerShell as administrator** (the line starts with
`PS C:\WINDOWS\system32>`); the other computers of the team are "their computer".

1. **The PC**: plugged into the team's network, sleep *Never*, network marked **Private** (otherwise the firewall blocks the team).
2. **PowerShell as administrator**: Win + X → *Terminal (Admin)* → Yes.
3. **Install** (on that PC, in one command):
   `irm {{SITE_URL}}/install.ps1 -OutFile $env:TEMP\install-dynamite.ps1; $env:DA_LANG = "en"; powershell -ExecutionPolicy Bypass -File $env:TEMP\install-dynamite.ps1`
   The script shows `== 1/7` to `== 7/7`, then `== Installed`, the address (`https://pc-name` and the IP) and the temporary
   password of the `admin` account. Options: `-Port 8443` when 443 is used, `-Dossier D:\DynamiteAgile`, `-Desinstaller`.
   Running it again updates without touching the data.
4. **Trust the certificate**, on each computer (once): copy `C:\DynamiteAgile\data\tls\partage\ca-dynamite.crt`, then in
   PowerShell (no administrator), in the folder of the file:
   `Import-Certificate -FilePath .\ca-dynamite.crt -CertStoreLocation Cert:\CurrentUser\Root` (answer Yes). macOS:
   double-click → Keychain → *Always Trust*. Never have the person bypass the browser's warning.
5. **Open** `https://pc-name` (or the IP), account `admin`, password shown; then ⚙ Admin → Spaces → Commencer.

Script messages: each error starts with `Error:` and names the fix. Port used by another service (PID 4 « System » = IIS
or http.sys) → `-Port 8443`; "not running as administrator" → Win + X → Terminal (Admin); `winget` not found → install
"App Installer" (Microsoft Store), or Python 3.12 (python.org, "Add python.exe to PATH") and Git for Windows by hand;
"the server does not start" → the last 20 lines of `data\logs\server.log` are shown, each refusal names the value and the fix.

## C. Their computer

- **Windows**: `winget install -e --id Python.Python.3.12` (or python.org, ticking “Add python.exe to PATH”), close and
  reopen the terminal; download {{REPO}}/archive/refs/heads/main.zip, extract it into Documents; double-click
  `Lancer_dev_local.bat`, or `cd $HOME\Documents\Dynamite-Agile-main` then `python app_dynamite_agile.py --dev-admin`.
- **macOS**: `xcode-select --install` (once), then `git clone {{REPO}}.git ~/dynamite-agile` and
  `cd ~/dynamite-agile && python3 app_dynamite_agile.py --dev-admin`.
- **Linux**: `sudo apt update && sudo apt install -y python3 git`, `git clone {{REPO}}.git ~/dynamite-agile`,
  `cd ~/dynamite-agile && python3 app_dynamite_agile.py --dev-admin`.
- Open `http://127.0.0.1:8080`, account `admin` / `admin` (development mode: never with real data).

## Common messages

| Message | Cause and fix |
|---|---|
| `ports 80 or 443 are already in use` | Another application (often Docker, installed by the control panel) uses the web ports. `sudo ss -ltnp \| grep -E ':(80\|443) '` and `docker ps` to find it; stop it or use another server. **If it is Traefik** (Hostinger VPS with Docker applications): do not stop it; install behind it with `curl -fsSL {{SITE_URL}}/install.sh \| sudo DA_LANG=en bash -s -- --traefik <address>` (Traefik keeps the ports and the certificate). |
| `already exists and is not an installation of this repository` | Another copy (often an older version) is in `/opt/dynamite_agile`; nothing was changed. Do not delete it: install next to it with `curl -fsSL {{SITE_URL}}/install.sh \| sudo DA_LANG=en DA_DIR=/opt/dynamite-agile-open bash -s -- --traefik <address>`. |
| `the domain … does not answer yet`, certbot `NXDOMAIN` or `Timeout` | The A record is not visible yet or port 80 is closed in the control-panel firewall. Check, wait, run the same command again. |
| `Permission denied` (ssh) | Wrong root password; set a new one in the control panel, or use the web console. |
| `curl: command not found` | `sudo apt update && sudo apt install -y curl` |
| `the service does not start` | The log is shown; to see it again: `journalctl -u dynamite-agile -n 50 --no-pager`. |
| `python is not recognized` (Windows) | Close and reopen the terminal after installing Python. |

## Afterwards

- Update: `sudo bash /opt/dynamite_agile/deploy/redeploy.sh` (data is never touched).
- Forgotten admin password: `sudo -u dynamite python3 /opt/dynamite_agile/app_dynamite_agile.py --reset-password admin`.
- Getting started: {{SITE_URL}}/en/guide.html; inside the tool, Help → the tour of the site.
- The tool's interface is in French today; English is coming in the next versions (the module names and technical terms
  are already in English).
