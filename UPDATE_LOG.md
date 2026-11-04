# Journal de mise à jour — 0.60.10

- **Version :** 0.60.09 → 0.60.10 (2026-11-04)
- **Changements :**
  1. **Serveur d'équipe sur un PC Windows** (D-O-022) : nouvelle destination « Sur un PC Windows de l'équipe » de la page
     d'installation (FR / EN). Dans PowerShell en administrateur, une commande installe Python et Git, récupère le code,
     crée le certificat HTTPS de l'équipe, règle la production, ouvre le pare-feu pour les réseaux privés seulement et
     crée la tâche qui démarre l'outil avec Windows. La relancer met à jour sans toucher aux données.
  2. **HTTPS sans domaine** : `tools/make_team_ca.py` crée l'autorité de certification de l'équipe et le certificat du PC ;
     chaque poste importe une fois `ca-dynamite.crt`.
  3. **Configuration** : `tools/write_config.py` règle `data/config.json` en ligne de commande ; `config.json` modifié dans
     le Bloc-notes (avec BOM) est accepté.
- **Base de données :** aucune migration.
