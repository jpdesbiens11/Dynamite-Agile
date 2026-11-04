# Dynamite | Agile — État du projet (branche `open/v0.60`)

**Dernière mise à jour :** 2026-11-03 (v0.60.03)
**Version :** 0.60.03 — +1 sur le dernier chiffre à chaque livraison (D-O-001)
**Session active :** libre
**Chantier actif :** aucun — 0.60.03 livrée (installation pour débutants en une commande, assistant IA)

Décisions : `docs/DECISIONS.md` (D-O-xxx) ; décisions antérieures citées dans le code : `docs/DECISIONS_ANTERIEURES.md`.

---

## Table 1 : Feuille de route

| Version | Contenu | Statut |
|---|---|---|
| 0.60.01 | Identité générique, About, Test Base et requis grand public, Generator et Timesheet sur le PDP, équipe d'exemple et « Profil d'études », vacances et réclamations de financement, licence MIT (D-O-001 à D-O-011) | Livré |
| 0.60.02 | Base propre sans aucune référence à l'usage d'origine (D-O-012), réponses Q4 / Q5 (D-O-013), noms de la mine (D-O-014), site web distinct dans `site/` : page d'entrée en storyline, installation, guide (D-O-015), `deploy/install.sh` pour un VPS | Livré |
| 0.60.03 | Installation pour débutants : choix de la destination, commandes remplies et copiables, assistant IA guidé (`installer.md`), installation en une commande et essai privé (D-O-016) | Livré |
| 0.60.04 et suivantes | Une à la fois : analyse fonctionnelle visuelle (arbre à 3 niveaux, méthodes de recherche des fonctions, lien CdCF) ; boundary diagram éditable ; exemples remplis de Pugh et Kepner-Tregoe ; Storyline (outil) ; Spaces de référence réécrits (pistolet à colle, imprimante à jet d'encre, machine à commande numérique pour bois mou) ; notes de cours réécrites ; évaluation par les pairs ; captures du guide Agile sur l'équipe d'exemple | À faire |

## Table 2 : Questions ouvertes (brief §5, une à la fois)

| # | Question | Réponse |
|---|---|---|
| 1 | Droits sur le contenu de référence | Réécrit en contenu original (D-O-009) |
| 2 | Licence du code | MIT (D-O-010) |
| 3 | Hébergement et nom du dépôt public | GitHub, `dynamite-agile` (D-O-011) ; compte propriétaire à préciser (`REPO` dans `tools/build_site.py`, `OWNER` en attendant) |
| 4 | Modules hors cours | Gardés ; évaluation par les pairs à venir (D-O-013) |
| 5 | Profils d'études de l'équipe d'exemple | Confirmés (D-O-013) |
| 6 | Langue : français seulement ou FR / EN | En attente |
| 7 | Règle A/B à tour de rôle pour cette branche | En attente |

## Relais (fin de 0.60.03)

- Tests : `python3 -m unittest discover -s tests -t .` + `node tests/js/ai_markdown.js`, `node tests/js/editor_roundtrip.js`.
  `tests/test_open_v060.py` balaie tout le dépôt (noms de fichiers, textes, contenu des .docx) à la recherche des mots
  de l'usage d'origine (liste encodée dans le test) et vérifie que le site est à jour.
- Démarrage de développement : `python3 app_dynamite_agile.py --dev-admin` → Spaces EQP (équipe d'exemple, 47 besoins et
  requis génériques), INT (temps interne et congés), HEADLAMP, TESTING, TOOLS, TRAINING.
- Site web : `python3 tools/build_site.py` → `site/` (publié par `.github/workflows/pages.yml`) ; sources dans
  `tools/site/` ; il reprend le CSS, le sprite, les logos et la « journée » de la vitrine (`tools/build_vitrine.py`).
- Installation : `deploy/install.sh` (Ubuntu / Debian, Let's Encrypt, ufw, systemd) ; résumé dans
  `deploy/DEPLOIEMENT_VPS.md`, procédure illustrée dans `site/installation.html`, guide de l'assistant IA
  `site/installer.md`. Pas encore essayé sur un vrai VPS ; l'URL `OWNER.github.io` attend le compte GitHub.
- 0.60.02 est la base propre (D-O-012) : elle s'installe sur une base de données neuve ; migrations additives à partir d'ici.
