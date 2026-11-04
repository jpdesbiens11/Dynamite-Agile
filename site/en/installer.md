# Installing Dynamite | Agile — a guide for an AI assistant

This file is for the AI assistant (Claude or another) that a beginner has opened next to their terminal to install
Dynamite | Agile. The illustrated page for people is https://jpdesbiens11.github.io/Dynamite-Agile/en/installation.html.

## How to guide

- The person is a beginner: one command at a time, saying where to type it (**on their computer** or **on the server**)
  and what they should see. Wait until they paste the result before going on.
- Never ask for a password, a private key or the content of `INITIAL_ADMIN_PASSWORD.txt`: those are only typed or read in
  the terminal. An IP address and a domain name can be shared.
- On a server, the terminal line starts with `root@…` or `user@server-name`. On their computer it looks different
  (`PS C:\…>` on Windows, `…%` or `…$` on macOS / Linux). Help them know where they are.
- With `DA_LANG=en`, every message of the script is in English; each error starts with `Error:` and names the fix: read it
  with them.
- The script is public: https://github.com/jpdesbiens11/Dynamite-Agile/blob/main/deploy/install.sh

## Three destinations

| Destination | For whom | What is needed |
|---|---|---|
| Online server | A team that connects from anywhere | Linux VPS (Ubuntu 22.04 / 24.04 or Debian 12), root access, a domain name, ports 22, 80 and 443 open |
| Server, private trial | Trying it before having a domain | Linux VPS and root access; nothing exposed, access through an SSH tunnel |
| Their computer | Solo trial | Windows, macOS or Linux, Python 3.10 or newer |

## A. Online server

1. **The server**: Ubuntu 24.04 VPS. In the host's control-panel firewall, open 22, 80, 443. At Hostinger: hPanel → VPS →
   *OS & Panel* (system), *Overview* (IP, user `root`, *Root password → Change*), *Security → Firewall*.
2. **The domain**: an **A** record to the server's IP (name `workshop` or `@`). Check on their computer:
   `nslookup workshop.my-domain.com` must show the server's IP.
3. **Log in** (on their computer): `ssh root@IP`; answer `yes` the first time; the password does not show while typing.
   Alternative: the *Web console* button of the control panel.
4. **Install** (on the server), with one command:
   `curl -fsSL https://jpdesbiens11.github.io/Dynamite-Agile/install.sh | sudo DA_LANG=en bash -s -- workshop.my-domain.com me@example.com`
   The script prints `== 1/7` to `== 7/7 Installed`, then the address and the temporary password of the `admin` account.
   Without curl: `sudo apt update && sudo apt install -y git`, `sudo git clone https://github.com/jpdesbiens11/Dynamite-Agile.git /opt/dynamite_agile`, then
   `sudo DA_LANG=en bash /opt/dynamite_agile/deploy/install.sh workshop.my-domain.com me@example.com`.
5. **Open** `https://workshop.my-domain.com`, account `admin`, the password shown, then choose a new one. Create the
   team: ⚙ Admin → Comptes → Règles d'accès; the project's Space: ⚙ Admin → Spaces.

## B. Server, private trial

1. `ssh root@IP` (on their computer).
2. On the server: `curl -fsSL https://jpdesbiens11.github.io/Dynamite-Agile/install.sh | sudo DA_LANG=en bash -s -- --essai`
3. On their computer, in a **new** terminal left open: `ssh -N -L 8080:127.0.0.1:8080 root@IP`
   (it looks frozen: that's normal). Open `http://127.0.0.1:8080`, account `admin` / `admin`, example team.
4. Going online later: follow path A; the same command with domain and email.

## C. Their computer

- **Windows**: `winget install -e --id Python.Python.3.12` (or python.org, ticking “Add python.exe to PATH”), close and
  reopen the terminal; download https://github.com/jpdesbiens11/Dynamite-Agile/archive/refs/heads/main.zip, extract it into Documents; double-click
  `Lancer_dev_local.bat`, or `cd $HOME\Documents\Dynamite-Agile-main` then `python app_dynamite_agile.py --dev-admin`.
- **macOS**: `xcode-select --install` (once), then `git clone https://github.com/jpdesbiens11/Dynamite-Agile.git ~/dynamite-agile` and
  `cd ~/dynamite-agile && python3 app_dynamite_agile.py --dev-admin`.
- **Linux**: `sudo apt update && sudo apt install -y python3 git`, `git clone https://github.com/jpdesbiens11/Dynamite-Agile.git ~/dynamite-agile`,
  `cd ~/dynamite-agile && python3 app_dynamite_agile.py --dev-admin`.
- Open `http://127.0.0.1:8080`, account `admin` / `admin` (development mode: never with real data).

## Common messages

| Message | Cause and fix |
|---|---|
| `ports 80 or 443 are already in use` | Another application (often Docker, installed by the control panel) uses the web ports. `sudo ss -ltnp \| grep -E ':(80\|443) '` and `docker ps` to find it; stop it or use another server. |
| `the domain … does not answer yet`, certbot `NXDOMAIN` or `Timeout` | The A record is not visible yet or port 80 is closed in the control-panel firewall. Check, wait, run the same command again. |
| `Permission denied` (ssh) | Wrong root password; set a new one in the control panel, or use the web console. |
| `curl: command not found` | `sudo apt update && sudo apt install -y curl` |
| `the service does not start` | The log is shown; to see it again: `journalctl -u dynamite-agile -n 50 --no-pager`. |
| `python is not recognized` (Windows) | Close and reopen the terminal after installing Python. |

## Afterwards

- Update: `sudo bash /opt/dynamite_agile/deploy/redeploy.sh` (data is never touched).
- Forgotten admin password: `sudo -u dynamite python3 /opt/dynamite_agile/app_dynamite_agile.py --reset-password admin`.
- Getting started: https://jpdesbiens11.github.io/Dynamite-Agile/en/guide.html; inside the tool, Help → the tour of the site.
- The tool's interface is in French today; English is coming in the next versions (the module names and technical terms
  are already in English).
