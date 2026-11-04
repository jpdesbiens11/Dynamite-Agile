# Dynamite | Agile — Installer sur un VPS Linux

La procédure illustrée pas à pas est sur le site du projet (`site/installation.html`). Ce fichier en est le résumé
pour qui lit le dépôt.

## Ce qu'il faut

- Un VPS Linux (Ubuntu 22.04 / 24.04 ou Debian 12), 1 vCPU et 1 Go de mémoire suffisent pour une équipe ; un accès
  SSH root (chez Hostinger, par exemple : hPanel → VPS → « SSH username » root, ou le bouton « Web console »).
- Un nom de domaine dont l'enregistrement **A** pointe vers l'adresse IP du VPS (chez l'hébergeur : gestionnaire DNS).
- Les ports **22, 80 et 443** ouverts dans le pare-feu du panneau de l'hébergeur, s'il en a un ; aucun autre
  programme ne doit déjà occuper 80 ou 443 sur ce VPS.

## Les trois commandes

```bash
sudo apt update && sudo apt install -y git
sudo git clone https://github.com/<compte>/dynamite-agile.git /opt/dynamite_agile
sudo bash /opt/dynamite_agile/deploy/install.sh mon-domaine.ca moi@exemple.ca
```

`deploy/install.sh` installe Python, git, certbot et le pare-feu `ufw` (22, 80, 443), crée l'utilisateur système
`dynamite`, obtient le certificat HTTPS Let's Encrypt (renouvelé automatiquement), écrit `data/config.json` pour la
production (`dev_mode: false`, HTTPS sur 443, redirection depuis 80), installe et démarre le service systemd
`dynamite-agile`, puis affiche le mot de passe temporaire du compte `admin`. Le script peut être relancé sans rien
perdre (`data/` est gardé).

## Ensuite

| Action | Commande ou écran |
|---|---|
| Premier accès | `https://mon-domaine.ca`, compte `admin` et le mot de passe affiché (à changer tout de suite) |
| Créer l'équipe | ⚙ Admin → Comptes → Règles d'accès (une ligne par personne, vérification à blanc) |
| Mettre à jour le code | `sudo bash /opt/dynamite_agile/deploy/redeploy.sh` |
| Voir le journal du service | `journalctl -u dynamite-agile -n 100` |
| Mot de passe admin oublié | `sudo -u dynamite python3 /opt/dynamite_agile/app_dynamite_agile.py --reset-password admin` |
| Sauvegardes | ⚙ Admin → Update et sauvegardes (points de restauration, sauvegarde d'un Space) ; plus la sauvegarde du VPS chez l'hébergeur |
| Sécurité réseau | ⚙ Admin → Sécurité réseau (HTTPS actif, TLS 1.3, HSTS) ; mTLS optionnel : `deploy/TLS.md` |

## Essai sans domaine (tunnel SSH)

Pour essayer avant d'avoir un domaine : lancez le serveur en local sur le VPS et ouvrez-le par un tunnel SSH, sans
rien exposer sur Internet.

```bash
sudo -u dynamite python3 /opt/dynamite_agile/app_dynamite_agile.py --host 127.0.0.1 --port 8080 --dev-admin
# sur votre poste :
ssh -N -L 8080:127.0.0.1:8080 root@<IP du VPS>     # puis http://127.0.0.1:8080
```

Le mode développement (`--dev-admin`) crée l'équipe d'exemple et accepte admin / admin : jamais avec de vraies données.

## Le dossier `data/`

`data/` (base, pièces jointes, journaux, `config.json`, certificats) n'est jamais suivi par git et appartient à chaque
installation. Ne le copiez pas d'un serveur à l'autre à la main : pour déménager, ⚙ Admin → Update et sauvegardes →
« Site complet ».
