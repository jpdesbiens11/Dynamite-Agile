# Journal de mise à jour — 0.60.06

- **Version :** 0.60.05 → 0.60.06 (2026-11-04)
- **Changements :**
  1. **« Commencer » côté serveur** (D-O-019) : `POST /api/starter/check` montre ce qu'un fichier Project Starter
     créerait et ce qui bloque (clé de Space ou code de temps déjà pris), sans rien écrire ; `POST /api/starter/apply`
     crée le nouveau Space à côté des exemples, en une seule transaction : l'équipe (mot de passe temporaire affiché une
     fois, jamais administrateur ; un compte existant est réutilisé tel quel), les codes de temps du projet, les essais
     (Draft) et les requis, liés entre eux et tous « À vérifier », les pages Dynamite en « Brouillon IA ». Clé du Space
     et codes ajustables avant la création. Réservé aux administrateurs, chaque étape au journal d'audit.
  2. **Format ajusté** : le `subject` d'un essai est un code de Testing (`func`, `elec`, `emc`…) ; un code de temps suit
     la forme de Timesheet (ex. `LA-MAR`). Exemples et `docs/STARTER_FORMAT.md` mis à jour.
- **Base de données :** migrations additives agile 15 (`standard_review`, `standard_checked` des requis) et testing 5
  (`review`, `review_checked` des essais).
