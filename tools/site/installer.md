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

## La page en 5 étapes (0.60.39, 0.60.44)

À l'étape 1, la personne choisit **où l'outil tourne** (serveur en ligne, serveur Linux local, PC Windows de l'équipe) et
**son propre ordinateur** (Windows, macOS, Linux) : les commandes à taper sur son ordinateur s'y adaptent (ouvrir un
terminal, protéger la clé Oracle avec `icacls` ou `chmod 600`, faire confiance au certificat de l'équipe). Le **serveur
Linux local** s'installe avec `install.sh --local` : HTTPS par l'autorité de certification de l'équipe, ports 80 et 443
ouverts au réseau local seulement ; Internet sert pendant l'installation seulement. Chez **Hostinger**, le nom gratuit du
VPS (`srvNNNNNN.hstgr.cloud`, ou `atelier.srvNNNNNN.hstgr.cloud`) pointe déjà vers son IP : aucun DNS à régler.


La page d'installation suit deux parcours : **Linux** (1. le système, 2. un VPS vide : Hostinger, Oracle Cloud Always Free ou
DigitalOcean, 3. l'adresse web et le courriel, 4. se connecter, 5. installer) et **Windows** (1. le système, 2. le PC, 3.
PowerShell en administrateur, 4. installer, 5. le certificat sur chaque poste). Elle suppose un serveur **vide** : si celui de
la personne ne l'est pas (Docker, Traefik, un panneau d'hébergeur, d'autres sites), c'est à toi d'adapter avec les cas
ci-dessous. L'essai privé et l'essai sur son ordinateur ne sont plus sur la page : propose-les seulement si on te les demande.

Selon l'hébergeur : **Oracle Cloud** donne l'utilisateur `ubuntu` (pas `root`) et une clé : `ssh -i fichier.key ubuntu@IP`, puis
`sudo` devant la commande (déjà dans la commande) ; ouvrir 80 et 443 dans la *Security List* du sous-réseau ; les règles
iptables de l'image sont ouvertes par l'installation. **DigitalOcean** et **Hostinger** donnent `root`. Sans domaine : un
sous-domaine gratuit DuckDNS (`nom.duckdns.org`) pointé sur l'IP.

## Quatre destinations

| Destination | Pour qui | Ce qu'il faut |
|---|---|---|
| Serveur en ligne | Une équipe qui s'y connecte de partout | VPS Linux (Ubuntu 22.04 / 24.04 ou Debian 12), accès root, nom de domaine, ports 22, 80 et 443 ouverts |
| Serveur en essai privé | Essayer avant d'avoir un domaine | VPS Linux et accès root ; rien d'exposé, accès par tunnel SSH |
| PC Windows de l'équipe | Une équipe sans Linux ni domaine, sur son réseau local | Windows 10 / 11 ou Server 2019+, toujours allumé, PowerShell en administrateur |
| Son ordinateur | Essai solo | Windows, macOS ou Linux, Python 3.10 ou plus récent |

## A. Serveur en ligne

1. **Le serveur** : VPS Ubuntu 24.04. Dans le pare-feu du panneau de l'hébergeur, ouvrir 22, 80, 443. Chez Hostinger : hPanel
   → VPS → *OS & Panel* (système), *Overview* (IP, utilisateur `root`, *Root password → Change*), *Security → Firewall*.
2. **Le domaine** : enregistrement **A** vers l'IP du serveur (nom `atelier` ou `@`). Vérifier sur son ordinateur :
   `nslookup atelier.mon-domaine.ca` doit montrer l'IP du serveur.
3. **Se connecter** (sur son ordinateur) : `ssh root@IP` ; répondre `yes` la première fois ; le mot de passe ne s'affiche pas
   pendant la frappe. Alternative : le bouton *Web console* du panneau.
4. **Installer** (sur le serveur), en une commande. **Avant de la donner, confirme le cas de la personne** par une question à
   choix : son serveur a-t-il déjà des applications Docker avec **Traefik** (souvent un VPS Hostinger avec Docker) ? Pour le
   vérifier sur le serveur : `docker ps | grep -i traefik` (une ligne = oui ; rien ou
   « command not found » = non).
   - Non (cas habituel) : `curl -fsSL {{SITE_URL}}/install.sh | sudo bash -s -- atelier.mon-domaine.ca moi@exemple.ca`
   - Oui, Traefik : `curl -fsSL {{SITE_URL}}/install.sh | sudo bash -s -- --traefik atelier.mon-domaine.ca` (pas de courriel :
     Traefik obtient le certificat ; aucune règle de pare-feu n'est changée).
   - Dans le doute, la commande habituelle suffit : elle détecte Traefik d'elle-même et s'installe derrière lui.
   - **Mettre à jour** plus tard : relancer exactement la même commande ; les données (`data/`) restent.
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

## D. PC Windows de l'équipe (réseau local)

Pour une équipe sans Linux ni domaine : un PC Windows 10 / 11 ou Server 2019+ toujours allumé héberge l'outil, en HTTPS
sur le réseau de l'école ou du bureau. Le terminal est **PowerShell en administrateur** (la ligne commence par
`PS C:\WINDOWS\system32>`) ; les autres postes de l'équipe sont « son ordinateur ».

1. **Le PC** : branché au réseau de l'équipe, mise en veille *Jamais*, réseau marqué **Privé** (sinon le pare-feu bloque l'équipe).
2. **PowerShell en administrateur** : Win + X → *Terminal (admin)* → Oui.
3. **Installer** (sur ce PC, en une commande) :
   `irm {{SITE_URL}}/install.ps1 -OutFile $env:TEMP\install-dynamite.ps1; powershell -ExecutionPolicy Bypass -File $env:TEMP\install-dynamite.ps1`
   Le script affiche `== 1/7` à `== 7/7`, puis `== C'est installé`, l'adresse (`https://nom-du-pc` et l'IP) et le mot de passe
   temporaire du compte `admin`. Options : `-Port 8443` si 443 est pris, `-Dossier D:\DynamiteAgile`, `-Desinstaller`. Le
   relancer met à jour sans toucher aux données. Messages en anglais avec `$env:DA_LANG = "en"`.
4. **Faire confiance au certificat**, sur chaque poste (une fois) : copier `C:\DynamiteAgile\data\tls\partage\ca-dynamite.crt`,
   puis dans PowerShell (sans administrateur), dans le dossier du fichier :
   `Import-Certificate -FilePath .\ca-dynamite.crt -CertStoreLocation Cert:\CurrentUser\Root` (répondre Oui). macOS :
   double-clic → Trousseau → *Toujours approuver*. Ne jamais faire contourner l'avertissement du navigateur.
5. **Ouvrir** `https://nom-du-pc` (ou l'IP), compte `admin`, mot de passe affiché ; puis ⚙ Admin → Spaces → Commencer.

Messages du script : chaque erreur commence par `Erreur :` et nomme le correctif. Port pris par un autre service
(PID 4 « System » = IIS ou http.sys) → `-Port 8443` ; « n'est pas ouvert en administrateur » → Win + X → Terminal (admin) ;
`winget` introuvable → installer « App Installer » (Microsoft Store), ou Python 3.12 (python.org, « Add python.exe to PATH »)
et Git pour Windows à la main ; « le serveur ne démarre pas » → les 20 dernières lignes de `data\logs\server.log` sont
affichées, chaque refus y nomme la valeur et le correctif.

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
| `les ports 80 ou 443 sont déjà pris` | Une autre application (souvent Docker, installée par le panneau) occupe le web. `sudo ss -ltnp \| grep -E ':(80\|443) '` et `docker ps` pour la trouver ; l'arrêter ou prendre un autre serveur. **Si c'est Traefik** (VPS Hostinger avec applications Docker) : ne pas l'arrêter ; installer derrière lui avec `curl -fsSL {{SITE_URL}}/install.sh \| sudo bash -s -- --traefik <adresse>` (Traefik garde les ports et le certificat). |
| `existe déjà et n'est pas une installation de ce dépôt` | Une autre copie (souvent une version plus ancienne) est dans `/opt/dynamite_agile` ; rien n'a été modifié. Ne pas l'effacer : installer à côté avec `curl -fsSL {{SITE_URL}}/install.sh \| sudo DA_DIR=/opt/dynamite-agile-open bash -s -- --traefik <adresse>`. |
| `le domaine … ne répond pas encore`, certbot `NXDOMAIN` ou `Timeout` | L'enregistrement A n'est pas encore visible ou le port 80 est fermé dans le pare-feu du panneau. Vérifier, attendre, relancer la même commande. |
| `Permission denied` (ssh) | Mauvais mot de passe root ; en choisir un nouveau dans le panneau, ou utiliser la console web. |
| `curl: command not found` | `sudo apt update && sudo apt install -y curl` |
| `le service ne démarre pas` | Le journal s'affiche ; le revoir : `journalctl -u dynamite-agile -n 50 --no-pager`. |
| `python n'est pas reconnu` (Windows) | Fermer et rouvrir le terminal après l'installation de Python. |

## Ensuite

- Mettre à jour : `sudo bash /opt/dynamite_agile/deploy/redeploy.sh` (les données ne sont jamais touchées).
- Mot de passe admin oublié : `sudo -u dynamite python3 /opt/dynamite_agile/app_dynamite_agile.py --reset-password admin`.
- Prise en main : {{SITE_URL}}/guide.html ; dans l'outil, Help → le tour du site.

## Le Space DEMO (0.60.49)

Une installation neuve s'ouvre sur un seul Space, DEMO : le tour guidé, un bac à sable, la formation, la bibliothèque de référence et l'exemple complet du Rover (tous les modules remplis). Aucun compte d'exemple n'est créé. Quand l'équipe commence son vrai projet (⚙ Admin → Spaces → Commencer), un administrateur cache DEMO pour tous : ⚙ Admin → Spaces → DEMO → « Cacher pour tous ».
