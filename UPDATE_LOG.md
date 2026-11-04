# Journal de mise à jour — 0.60.03

- **Version :** 0.60.02 → 0.60.03 (2026-11-03)
- **Changements :**
  1. **Installation pour débutants** (D-O-016, `site/installation.html`) : choix de la destination (serveur en ligne,
     serveur en essai privé, mon ordinateur avec onglets Windows / macOS / Linux) ; champs domaine, courriel et IP qui
     remplissent les commandes ; chaque bloc dit où le coller et ce qu'on doit voir, et se copie d'un clic ; cases
     « C'est fait » et barre de progression ; aides Hostinger ; dépannage par message.
  2. **Assistant IA à côté** : un message prêt à coller avec le lien de la procédure, et `site/installer.md`, guide écrit
     pour l'assistant (une commande à la fois, jamais de mot de passe).
  3. **Une commande** : `curl -fsSL <site>/install.sh | sudo bash -s -- domaine courriel` (ou `--essai`) ; le script
     récupère le code, vérifie le DNS et les ports 80 / 443 avant le certificat.
- **Base de données :** aucune migration.
