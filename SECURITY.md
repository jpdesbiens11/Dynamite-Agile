# Sécurité · Security

## Signaler une vulnérabilité · Reporting a vulnerability

**FR** · N'ouvrez pas d'issue publique pour une faille. Utilisez le signalement privé de GitHub : onglet **Security** du
dépôt → **Report a vulnerability**. Décrivez la version (`/api/about`, champ `version`), les étapes pour reproduire et
l'effet. Le projet est maintenu par une seule personne : la réponse vient dès que possible ; un correctif publié porte
la mention du signalement dans `docs/releases/`, avec votre nom si vous le souhaitez.

**EN** · Do not open a public issue for a vulnerability. Use GitHub's private reporting: the repository's **Security**
tab → **Report a vulnerability**. Give the version (`/api/about`, field `version`), the steps to reproduce and the
impact. The project has a single maintainer: the answer comes as soon as possible; a published fix credits the report in
`docs/releases/`, with your name if you wish.

## Versions prises en charge · Supported versions

Seule la dernière version publiée reçoit les correctifs : mettez à jour par ⚙ Admin → Update → « Mise à jour en ligne ».
Only the latest published version gets fixes: update through ⚙ Admin → Update → "Online update".

## Dans le périmètre · In scope

- Le serveur (`core/`, `modules/`), les pages (`static/`), les scripts d'installation (`deploy/install.sh`,
  `install_traefik.sh`, `install.ps1`) et la mise à jour en ligne (`core/update.py`, `core/release.py`).
- The server, the pages, the install scripts and the online update listed above.

La démo publique `demo.dynamiteagile.ca` est un bac à sable : n'y lancez ni test de charge ni balayage automatisé ;
décrivez le problème, nous le reproduirons sur une installation de test.
The public demo is a sandbox: no load tests or automated scans against it; describe the issue and it will be reproduced
on a test installation.

## Vérifier ce que vous installez · Check what you install

- Tapez toujours `https://dynamiteagile.ca/…`, jamais `http://` : un script reçu en clair peut avoir été modifié en route.
  Always type `https://dynamiteagile.ca/…`, never `http://`: a script received in clear may have been changed on the way.
- Le script se lit avant d'être lancé · You can read the script before running it:

  ```bash
  curl -fsSL https://dynamiteagile.ca/install.sh -o install.sh && less install.sh && sudo bash install.sh <adresse> <courriel>
  ```
