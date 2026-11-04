"""Lancer la plateforme en DÉVELOPPEMENT (D-B-091) -- F5 dans Spyder, ou double-clic sur Lancer_dev_local.bat /
Lancer_dev_reseau.bat. Jamais pour la production (deploy/TLS.md).

    MODE = "local"   ce poste seulement : http://localhost:8080, admin / admin pré-rempli, données d'exemple.
    MODE = "reseau"  partage avec un collègue du réseau local : https://<adresse de ce poste>:8443 (certificat de
                     développement créé tout seul), réseaux privés seulement ; admin / admin seulement sur ce poste,
                     le collègue a son propre compte (Admin → Utilisateurs).

En ligne de commande : python lancer_dev.py reseau [--allow 192.168.1.40] [--confiance]
    --confiance  installe la CA de développement (data/tls/ca.crt) dans le magasin Windows de l'utilisateur
                 (sans droits administrateur) : plus d'avertissement du navigateur sur ce poste. Le collègue fait de
                 même avec le fichier ca.crt qu'on lui envoie (double-clic → Installer le certificat → Utilisateur
                 actuel → Autorités de certification racines de confiance).
"""
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# ---- Réglages pour Spyder (F5) ---------------------------------------------------------------------------------------
MODE = "local"            # "local" ou "reseau"
COLLEGUES = []            # ex. ["192.168.1.40"] : seulement ces postes ; [] = tout le réseau privé
OUVRIR_NAVIGATEUR = True
# ----------------------------------------------------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))


def trust_dev_ca():
    """Windows: put data/tls/ca.crt in the CURRENT USER root store (certutil -user, no administrator rights)."""
    ca = BASE / "data" / "tls" / "ca.crt"
    if not ca.exists():
        print("Pas encore de CA de développement : lancez d'abord le mode « reseau » une fois.")
        return
    if sys.platform != "win32":
        print("Installez " + str(ca) + " comme autorité de confiance de votre navigateur.")
        return
    print("Windows va demander de confirmer l'installation du certificat « Dynamite Dev Root CA » : répondez Oui.")
    subprocess.run(["certutil", "-user", "-addstore", "Root", str(ca)], check=False)


def open_when_ready(url):
    """Open the browser once the server answers (the first start can take a few seconds: example data)."""
    import ssl
    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE  # local probe only, nothing is sent
    candidates = [url, url.replace("https://", "http://")] if url.startswith("https") else [url]
    for _ in range(60):
        for candidate in candidates:  # « reseau » falls back to plain HTTP when openssl is missing
            try:
                urllib.request.urlopen(candidate + "/api/about", timeout=1, context=context)
                webbrowser.open(candidate)
                return
            except OSError:
                pass
        time.sleep(0.5)


def main(argv):
    mode = MODE
    args = list(argv)
    if args and args[0] in ("local", "reseau"):
        mode = args.pop(0)
    if "--confiance" in args:
        args.remove("--confiance")
        trust_dev_ca()
    import app_dynamite_agile
    cli = []  # data/config.json decides development mode (dev_mode: true by default); never forced here
    if mode == "reseau":
        cli.append("--lan")
        for ip in COLLEGUES:
            cli += ["--allow", ip]
    url = "https://localhost:8443" if mode == "reseau" else "http://localhost:8080"
    if "--port" in args:
        port = args[args.index("--port") + 1]
        url = url.rsplit(":", 1)[0] + ":" + port
    if OUVRIR_NAVIGATEUR:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    return app_dynamite_agile.main(cli + args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
