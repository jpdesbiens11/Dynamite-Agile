# Journal de mise à jour — 0.60.07

- **Version :** 0.60.06 → 0.60.07 (2026-11-04)
- **Changements :**
  1. **Écran « Commencer »** (⚙ Admin → Spaces, D-O-019) : choisir le fichier .json de l'assistant IA, ou un exemple ;
     aperçu de ce qui sera créé, normes « À vérifier », équipe (nouveau ou existant), codes de temps à renommer ou à
     retirer, ce qui bloque ; clé du Space modifiable ; création, puis mots de passe temporaires affichés une seule fois.
  2. **Dashboard** : pour un administrateur, la carte « Démarrez votre projet avec un assistant IA » mène à « Commencer »,
     tant qu'aucun projet n'a été démarré ainsi.
  3. **« À vérifier » et « Confirmer la norme »** : badge dans la liste Goldmine, bloc dans la fiche requirement et dans la
     fiche d'essai ; le dialogue demande l'édition en vigueur (et la clause) et garde la date et la personne.
     « Accepted » (requirement) et « Approved » (essai) sont refusés tant que la norme n'est pas confirmée.
- **Base de données :** aucune migration (colonnes ajoutées en 0.60.06).
