# Dynamite | Agile

**FR** · L'atelier libre des équipes de conception de produit : besoins et requirements, plan du projet, sprints, wiki,
essais, formation et feuilles de temps, du besoin du client jusqu'au prototype validé. Pour les étudiants du baccalauréat
en conception de produit et les équipes de start-up. Hébergé sur votre propre serveur, sans aucune ressource externe.

**EN** · The free workshop of product-design teams: needs and requirements, project plan, sprints, wiki, tests, training
and timesheets, from the customer's need to the validated prototype. For product-design students and start-up teams.
Hosted on your own server, with no external resource.

Site · Website : https://dynamiteagile.ca ([English](https://dynamiteagile.ca/en/))

## Installer · Install

Serveur Linux (Ubuntu 22.04 / 24.04, Debian 12), domaine pointé vers le serveur, ports 22, 80 et 443 ouverts ·
Linux server, domain pointing to it, ports 22, 80 and 443 open:

```bash
curl -fsSL https://dynamiteagile.ca/install.sh | sudo bash -s -- atelier.mon-domaine.ca moi@exemple.ca
curl -fsSL https://dynamiteagile.ca/install.sh | sudo DA_LANG=en bash -s -- workshop.my-domain.com me@example.com
```

Essai privé sans domaine · Private trial without a domain: `… | sudo bash -s -- --essai`.
Procédure illustrée pour débutants · Step-by-step guide for beginners:
[installation](https://dynamiteagile.ca/installation.html) ·
[installation (EN)](https://dynamiteagile.ca/en/installation.html).

Sur votre ordinateur · On your computer (Python 3.10+):

```bash
git clone https://github.com/jpdesbiens11/Dynamite-Agile.git && cd Dynamite-Agile
python3 app_dynamite_agile.py --dev-admin      # http://127.0.0.1:8080, admin / admin
```

## Les outils · The tools

Dashboard, Goldmine (needs, requirements), Exploration (plan, Gantt), Agile (backlog, sprints, Board, Change Management),
Dynamite (wiki), Testing (Test Base, Test Plans), Tools (Pugh, Kepner-Tregoe, Generator), Training, Timesheet (PDP steps,
vacation, funding claims), Help & HeadLamp. Les noms viennent de la mine · The names come from the mine:
[docs/NOMS_DES_MODULES.md](docs/NOMS_DES_MODULES.md).

## Développer · Develop

Bibliothèque standard Python seulement · Python standard library only. Tests:

```bash
python3 -m unittest discover -s tests -t .
node tests/js/ai_markdown.js && node tests/js/editor_roundtrip.js
```

Règles techniques · Technical rules: [docs/FONDATIONS.md](docs/FONDATIONS.md) · décisions · decisions:
[docs/DECISIONS.md](docs/DECISIONS.md) · état du projet · project status: [docs/ETAT_PROJET.md](docs/ETAT_PROJET.md).
L'interface est en français aujourd'hui ; l'anglais arrive par étapes · The interface is in French today; English is
coming step by step.

## Licence · License

MIT © 2026 Jean-Philippe Desbiens — conçu et construit avec Claude Opus 5.5 · designed and built with Claude Opus 5.5.
