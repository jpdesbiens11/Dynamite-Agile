# Dynamite | Agile — Installer sur un VPS Linux

La procédure illustrée pas à pas, pour débutants, est sur le site du projet (`site/installation.html`) ; un guide pour
l'assistant IA qui accompagne la personne est publié à côté (`site/installer.md`). Ce fichier en est le résumé.

## Ce qu'il faut

- Un VPS Linux (Ubuntu 22.04 / 24.04 ou Debian 12), 1 vCPU et 1 Go de mémoire suffisent pour une équipe ; un accès
  SSH root (chez Hostinger, par exemple : hPanel → VPS → « SSH username » root, ou le bouton « Web console »).
- Un nom de domaine dont l'enregistrement **A** pointe vers l'adresse IP du VPS (chez l'hébergeur : gestionnaire DNS).
- Les ports **22, 80 et 443** ouverts dans le pare-feu du panneau de l'hébergeur, s'il en a un ; aucun autre
  programme ne doit déjà occuper 80 ou 443 sur ce VPS.

## Une commande

Connecté au serveur (`ssh root@<IP>` ou la console web de l'hébergeur) :

```bash
curl -fsSL https://dynamiteagile.ca/install.sh | sudo bash -s -- mon-domaine.ca moi@exemple.ca
```

Messages du script en anglais : `sudo DA_LANG=en bash -s -- …` (page anglaise : `site/en/installation.html`).

La commande récupère le code dans `/opt/dynamite_agile`, puis `deploy/install.sh` installe Python, git, certbot et le
pare-feu `ufw` (22, 80, 443), crée l'utilisateur système `dynamite`, vérifie que le domaine pointe vers le serveur et que
les ports 80 / 443 sont libres, obtient le certificat HTTPS Let's Encrypt (renouvelé automatiquement), écrit
`data/config.json` pour la production (`dev_mode: false`, HTTPS sur 443, redirection depuis 80), installe et démarre le
service systemd `dynamite-agile`, puis affiche le mot de passe temporaire du compte `admin`. On peut la relancer sans rien
perdre (`data/` est gardé). Sans curl, en trois commandes :

```bash
sudo apt update && sudo apt install -y git
sudo git clone https://github.com/jpdesbiens11/Dynamite-Agile.git /opt/dynamite_agile
sudo bash /opt/dynamite_agile/deploy/install.sh mon-domaine.ca moi@exemple.ca
```

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

## Essai privé, sans domaine

```bash
curl -fsSL https://dynamiteagile.ca/install.sh | sudo bash -s -- --essai     # sur le serveur
ssh -N -L 8080:127.0.0.1:8080 root@<IP du VPS>                                                # sur votre poste
```

Puis `http://127.0.0.1:8080`, admin / admin, avec l'équipe d'exemple : rien n'est exposé sur Internet (mode
développement, jamais avec de vraies données). Pour passer en ligne, relancez la commande avec votre domaine et votre
courriel.

## Le dossier `data/`

`data/` (base, pièces jointes, journaux, `config.json`, certificats) n'est jamais suivi par git et appartient à chaque
installation. Ne le copiez pas d'un serveur à l'autre à la main : pour déménager, ⚙ Admin → Update et sauvegardes →
« Site complet ».
