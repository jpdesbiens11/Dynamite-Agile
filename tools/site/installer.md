# Installer Dynamite | Agile — guide pour un assistant IA

Ce fichier s'adresse à l'assistant IA (Claude ou un autre) qu'une personne débutante a ouvert à côté de son terminal pour
installer Dynamite | Agile. La page humaine, illustrée, est {{SITE_URL}}/installation.html.

## Comment guider

- La personne débute : une seule commande à la fois, avec où la taper (**sur son ordinateur** ou **sur le serveur**) et ce
  qu'elle devrait voir. Attendez qu'elle colle le résultat avant de continuer.
- Ne demandez jamais un mot de passe, une clé privée ni le contenu de `INITIAL_ADMIN_PASSWORD.txt` : ils se tapent ou se
  lisent seulement dans le terminal. Une adresse IP et un nom de domaine peuvent être partagés.
- Sur un serveur, la ligne du terminal commence par `root@…` ou `utilisateur@nom-du-serveur`. Sur son ordinateur, c'est
  autre chose (`PS C:\…>` sous Windows, `…%` ou `…$` sous macOS / Linux). Aidez-la à savoir où elle est.
- Chaque message d'erreur du script commence par `Erreur :` et nomme le correctif : lisez-le avec elle.
- Le code du script est public : {{REPO}}/blob/main/deploy/install.sh

## Trois destinations

| Destination | Pour qui | Ce qu'il faut |
|---|---|---|
| Serveur en ligne | Une équipe qui s'y connecte de partout | VPS Linux (Ubuntu 22.04 / 24.04 ou Debian 12), accès root, nom de domaine, ports 22, 80 et 443 ouverts |
| Serveur en essai privé | Essayer avant d'avoir un domaine | VPS Linux et accès root ; rien d'exposé, accès par tunnel SSH |
| Son ordinateur | Essai solo | Windows, macOS ou Linux, Python 3.10 ou plus récent |

## A. Serveur en ligne

1. **Le serveur** : VPS Ubuntu 24.04. Dans le pare-feu du panneau de l'hébergeur, ouvrir 22, 80, 443. Chez Hostinger : hPanel
   → VPS → *OS & Panel* (système), *Overview* (IP, utilisateur `root`, *Root password → Change*), *Security → Firewall*.
2. **Le domaine** : enregistrement **A** vers l'IP du serveur (nom `atelier` ou `@`). Vérifier sur son ordinateur :
   `nslookup atelier.mon-domaine.ca` doit montrer l'IP du serveur.
3. **Se connecter** (sur son ordinateur) : `ssh root@IP` ; répondre `yes` la première fois ; le mot de passe ne s'affiche pas
   pendant la frappe. Alternative : le bouton *Web console* du panneau.
4. **Installer** (sur le serveur), en une commande :
   `curl -fsSL {{SITE_URL}}/install.sh | sudo bash -s -- atelier.mon-domaine.ca moi@exemple.ca`
   Le script affiche `== 1/7` à `== 7/7 C'est installé`, puis l'adresse et le mot de passe temporaire du compte `admin`.
   Sans curl : `sudo apt update && sudo apt install -y git`, `sudo git clone {{REPO}}.git /opt/dynamite_agile`, puis
   `sudo bash /opt/dynamite_agile/deploy/install.sh atelier.mon-domaine.ca moi@exemple.ca`.
5. **Ouvrir** `https://atelier.mon-domaine.ca`, compte `admin`, mot de passe affiché, puis en choisir un nouveau. Créer
   l'équipe : ⚙ Admin → Comptes → Règles d'accès ; le Space du projet : ⚙ Admin → Spaces.

## B. Serveur en essai privé

1. `ssh root@IP` (sur son ordinateur).
2. Sur le serveur : `curl -fsSL {{SITE_URL}}/install.sh | sudo bash -s -- --essai`
3. Sur son ordinateur, dans un **nouveau** terminal laissé ouvert : `ssh -N -L 8080:127.0.0.1:8080 root@IP`
   (il semble figé : c'est normal). Ouvrir `http://127.0.0.1:8080`, compte `admin` / `admin`, équipe d'exemple.
4. Passer en ligne plus tard : refaire le parcours A ; la même commande avec domaine et courriel.

## C. Son ordinateur

- **Windows** : `winget install -e --id Python.Python.3.12` (ou python.org en cochant « Add python.exe to PATH »), fermer et
  rouvrir le terminal ; télécharger {{REPO}}/archive/refs/heads/main.zip, l'extraire dans Documents ; double-cliquer
  `Lancer_dev_local.bat`, ou `cd $HOME\Documents\Dynamite-Agile-main` puis `python app_dynamite_agile.py --dev-admin`.
- **macOS** : `xcode-select --install` (une fois), puis `git clone {{REPO}}.git ~/dynamite-agile` et
  `cd ~/dynamite-agile && python3 app_dynamite_agile.py --dev-admin`.
- **Linux** : `sudo apt update && sudo apt install -y python3 git`, `git clone {{REPO}}.git ~/dynamite-agile`,
  `cd ~/dynamite-agile && python3 app_dynamite_agile.py --dev-admin`.
- Ouvrir `http://127.0.0.1:8080`, compte `admin` / `admin` (mode développement : jamais avec de vraies données).

## Messages fréquents

| Message | Cause et correctif |
|---|---|
| `les ports 80 ou 443 sont déjà pris` | Une autre application (souvent Docker, installée par le panneau) occupe le web. `sudo ss -ltnp \| grep -E ':(80\|443) '` et `docker ps` pour la trouver ; l'arrêter ou prendre un autre serveur. |
| `le domaine … ne répond pas encore`, certbot `NXDOMAIN` ou `Timeout` | L'enregistrement A n'est pas encore visible ou le port 80 est fermé dans le pare-feu du panneau. Vérifier, attendre, relancer la même commande. |
| `Permission denied` (ssh) | Mauvais mot de passe root ; en choisir un nouveau dans le panneau, ou utiliser la console web. |
| `curl: command not found` | `sudo apt update && sudo apt install -y curl` |
| `le service ne démarre pas` | Le journal s'affiche ; le revoir : `journalctl -u dynamite-agile -n 50 --no-pager`. |
| `python n'est pas reconnu` (Windows) | Fermer et rouvrir le terminal après l'installation de Python. |

## Ensuite

- Mettre à jour : `sudo bash /opt/dynamite_agile/deploy/redeploy.sh` (les données ne sont jamais touchées).
- Mot de passe admin oublié : `sudo -u dynamite python3 /opt/dynamite_agile/app_dynamite_agile.py --reset-password admin`.
- Prise en main : {{SITE_URL}}/guide.html ; dans l'outil, Help → le tour du site.
