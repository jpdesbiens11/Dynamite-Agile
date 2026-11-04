---
name: dynamite-design
description: Concevoir ou modifier un écran de Dynamite | Agile (Dynamite, Agile, Goldmine, Testing…) : jetons CSS, Thème par défaut et Terminal R&D, icônes, aucune ressource externe.
---

# Dynamite | Agile — design de l'outil

À utiliser pour tout écran, composant, style, icône ou page de Dynamite | Agile (dépôt `Dynamite_Agile/`).
Cette skill traduit les règles du projet en règles de design. **Ordre de priorité :** `docs/FONDATIONS.md` >
`CLAUDE.md` > cette skill > toute autre skill de design (frontend-design, Design, design-skills…).

**Source de vérité :** ce fichier, versionné dans le dépôt (`.claude/skills/dynamite-design/SKILL.md`,
D-B-093). Claude Code et les contributeurs le lisent ici. Une copie dans un compte claude.ai se
met à jour à partir de ce fichier, jamais l'inverse. Toute modification passe par une version et une décision,
comme le code.

Une autre skill de design apporte une **méthode** (direction esthétique, hiérarchie, rythme, micro-interactions,
critique). On garde la méthode et on la **traduit** dans les moyens de la plateforme : CSS et JS locaux, jetons
existants, `el()`. On ne reprend jamais sa pile technique (React, Tailwind, Google Fonts, npm).

## 1. Interdits absolus (vérifier avant chaque livraison)

- **Aucune ressource externe.** Pas de CDN, pas de Google Fonts, pas de `@import url(http…)`, pas d'icônes en
  ligne, pas d'appel réseau sortant. Tout est servi depuis `static/`, comme sur un serveur sans accès sortant.
- **Pas de framework ni d'outil de build.** Pas de React, Vue, Tailwind, Sass, npm, bundler. JavaScript natif
  (modules IIFE `(function () { "use strict"; … })();`), CSS natif (variables, `color-mix`, `:is`).
- **CSP stricte** (`script-src 'self'; style-src 'self'`). Donc :
  - pas de `<script>` ni de `<style>` en ligne, pas d'attribut `onclick=` ni `style=` dans le HTML ;
  - une valeur dynamique passe par le CSSOM (`node.style.left = …`), jamais par `setAttribute("style", …)` ;
  - les styles vont dans `static/css/<clé>.css`, déclaré dans `MODULE_MANIFEST`.
  - Seule exception : un outil autonome hors ligne dans `static/apps/<nom>/` (un seul fichier HTML, code
    intégré permis, `connect-src 'none'`, bac à sable sans `allow-same-origin`). C'est le cas de la page vitrine.
- **DOM sûr.** Construire avec `DA.el(tag, attrs, ...enfants)` et `textContent`. Jamais `innerHTML` sur une
  donnée venant du serveur. `el()` ignore `null`, `undefined` et `false` : jamais `append(null)` natif, qui
  affiche « null ».
- **Pas de texte dans une image.** Le texte reste sélectionnable et traduisible. Aucun `<text>` dans un SVG.
- **Pas de nouveau style de bouton, de carte, de tableau, de badge ou de dialogue en parallèle.** On réutilise
  `.btn` (`.btn-primary`, `.btn-small`), `.badge badge-<kind>` (`ok`, `warn`, `off`, `neutral`, `info`,
  `danger`), `table.data`, `.modal`, `.toast`, `.field`, `.subtabs`.
- **Aucune barre de défilement dans une fenêtre** (D-B-118). Un dialogue `.modal` tient dans l'écran (le
  rendre plus large plutôt que plus haut) ; un contenu plus haut que l'écran (éditeur de tables, long formulaire)
  devient une page avec sa propre adresse (`#/…/edit`), et c'est la page qui défile.
- **Fichiers sous 500 lignes** (JS et Python). On découpe plutôt que de laisser grossir.

## 2. Brancher un écran

- Un outil est un module : code Python dans `modules/<clé>/`, écran dans `static/js/<clé>/*.js` et
  `static/css/<clé>.css`, déclarés par `scripts` et `styles` dans `core/modules.py` → `MODULE_MANIFEST`.
  On ne modifie ni `core/router.py` ni `static/js/app.js` pour ajouter un onglet.
- Le script appelle `DA.registerModule("<clé>", render)`, avec `render(main, parts)` (`parts` = segments du hash
  `#/<clé>/...`).
- Mise en page commune avec panneau de gauche :

  ```js
  const page = DA.moduleLayout(main, {
    label: "Mon outil", mark: DA.mark("<clé>"),
    picker: DA.spaces.picker(key, (k) => "#/<clé>/" + k),  // outil par Space : liste déroulante (D-B-103)
    nav: [["#/<clé>", "Vue principale", view === "main"], ["#/<clé>/liste", "Liste", view === "liste"]],
    admin: [["#/<clé>/reglages", "Réglages", view === "reglages"]],  // administrateurs seulement
  });
  page.append(DA.el("div", { class: "page-head" }, DA.el("h1", null, "Titre"),
    DA.el("p", { class: "muted" }, "Une phrase qui dit à quoi sert l'écran.")));
  ```

- Outils fournis par `DA` : `api.get/post/put/patch/del/upload`, `el`, `clear`, `field(label, input, hint)`,
  `badge(texte, kind)`, `table(entêtes, lignes)`, `modal(titre, contenu)`, `toast(message, kind)`,
  `icon(nom)`, `mark(clé)`, `setModuleAccent(clé)`.

## 3. Jetons de couleur et de forme

Jamais de couleur codée en dur dans un module : toujours `var(--…)`. Valeurs de base dans `static/css/app.css`
(`:root`). Chaque thème les redéfinit.

| Jeton | Rôle |
|---|---|
| `--bg`, `--surface`, `--surface-2` | fond de page, cartes, zones secondaires |
| `--ink`, `--muted`, `--line` | texte, texte secondaire, filets |
| `--panel`, `--panel-ink` | barre du haut |
| `--brand-blue` | bleu de la marque (aide, accents) |
| `--agile`, `--agile-strong` | actions et liens |
| `--dynamite`, `--exploration` | accents historiques du wiki et du plan |
| `--danger`, `--warn`, `--ok` | états |
| `--radius-sm`, `--radius-lg`, `--shadow` | formes |
| `--font` (Segoe UI Variable Text, police système), `--mono` (Cascadia Mono) | typographie, aucun fichier à charger |
| `--acc` | **accent de l'outil courant**, donné par `<html data-module="<clé>">` |

Si `FONDATIONS.md` (Table 3) et `app.css` divergent, `app.css` fait foi jusqu'à l'alignement, et on signale
l'écart.

Un **nouvel outil** choisit son accent (ni orange Dynamite, ni bleu Agile) et l'ajoute aux **deux** thèmes :

- `static/css/sketch.css` : `html[data-sketch][data-module="<clé>"] { --acc: var(--hl-…); }`
- `static/css/terminal.css` : `html[data-term][data-module="<clé>"] { --acc: #…; }`
- `static/js/tools/sketch.js` → `DA.NAV` : place dans `groups` (ordre d'usage) et `items[<clé>] = [icône, info-bulle]`.

## 4. Les thèmes : toujours tester les deux principaux

- **Thème par défaut** (clé `carnet`) : `data-theme="atlassian"` + `data-sketch="carnet"`, règles dans `sketch.css`. Papier
  quadrillé (`--paper`, `--grid`), graphite (`--graphite`), surligneurs `--hl-yellow|orange|cyan|green|pink|violet|blue|teal|red`,
  rectangle tracé au crayon `--r-hand`, cartes `--r-card`, ombre décalée `--shadow-sketch`, rebond `--ease-pop`.
  La police manuscrite `--hand` sert aux titres décoratifs seulement, jamais au texte courant.
- **Terminal R&D** : `data-theme="dark"` + `data-term="on"`, règles dans `terminal.css`. Fond quasi noir,
  `--acc` couleur de coloration syntaxique, `--mono` pour titres, clés, nombres, `--acc-glow`, `--sel`.
  **Piège connu :** un module qui pose des fonds clairs locaux (ex. `background: #fff`) donne du texte clair sur
  fond clair. Utiliser les jetons, ou ajouter une règle `html[data-term] .ma-zone { … }`.
- Autres thèmes au choix (`themes.css`) : `light`, `dark`, `atlassian`, `contrast`, `system`
  (`prefers-color-scheme`). Ils marchent seuls si on n'utilise que des jetons.
- Les choix sont dans menu à votre nom → Thème (Thème par défaut / Terminal) et Paramètres (tous).

## 5. Icônes, logos, illustrations

- **Icônes fonctionnelles** = SVG en `currentColor` : `DA.icon("nom")` lit `static/img/icons.svg` (Thème par défaut) ou
  `icons-term.svg` (Terminal). Les deux sprites ont **les mêmes noms**.
- On ne retouche jamais un sprite à la main : on ajoute la forme dans `tools/make_sketch_assets.py` (`ICONS`,
  `MARKS`, tracés de `tools/sketch_rough.py`, générateur à graine fixe), puis on relance
  `python tools/make_sketch_assets.py`. `tests/test_lot_v034.py` vérifie que la génération est reproductible
  et que chaque icône utilisée existe.
- **Logo d'outil** : `DA.mark("<clé>")` → `static/img/marks/<clé>.svg` et `static/img/marks-term/<clé>.svg`
  (les deux obligatoires). Le logo de l'outil est son nom en texte (`companyBrand` de `app.js`) avec le favicon.
- Un PNG de marque est permis s'il est servi localement depuis `static/img/`, sans texte et de quelques dizaines
  de Ko.

## 6. Interaction, accessibilité, mouvement

- Focus clavier visible partout. Tout est atteignable au clavier, avec `aria-label` sur les boutons à icône seule.
- Info-bulle : attribut `data-tip="…"`, affiché par la bulle JS de `sketch.js`. Ne jamais compter sur `title`
  seul.
- Survols : lever légèrement (`translateY(-1px)`) et surligner avec `--acc`. Une animation courte, utile et
  interruptible.
- `@media (prefers-reduced-motion: reduce)` coupe toute animation non essentielle. Contraste AA minimum.
- Tester aussi en largeur étroite : la barre du haut se compacte (`tabs-tight` → `tabs-partial` →
  `tabs-compact`), les sous-onglets passent à la ligne.

## 7. Mots et états

- Phrases, boutons et aide **en français**. **Termes techniques en anglais** (status, workflow, requirement,
  Test Plan… ; voir `docs/GLOSSARY_EN.md`). Code et commentaires en anglais.
- Tout message d'erreur nomme la valeur fautive **et** le correctif (« Correctif : … »).
- États vides : une phrase qui dit quoi faire, avec un bouton vers l'action. Jamais « null », « undefined » ou une
  zone vide. Un onglet vide d'un Space utilise `DA.spaces.startHere(titre, texte, actions)` (carte « Commencer ici »,
  D-B-134).
- **Nouveauté :** tout champ, bouton, onglet ou section ajouté porte `data-new="<version>-<clé>"` (badge [new]
  jusqu'à la première utilisation, D-A-049).

## 8. Vérification avant de livrer

1. Aucune ressource chargée de l'extérieur : `grep -rnE "(src|href)\s*[:=]\s*[\"']https?://|url\([\"']?https?://|@import" static/js static/css static/index.html`
   ne renvoie rien. (L'espace de noms SVG `http://www.w3.org/2000/svg` et les exemples de liens tapés par
   l'utilisateur ne sont pas des ressources.)
2. `grep -rnE "\.innerHTML\s*=|setAttribute\(\"style" static/js` : seule exception connue, le gabarit d'icônes
   SVG constant de `static/js/agile/agile.js` (aucune donnée serveur).
3. `python -m unittest discover -s tests -t .` (et `tests/js/*` avec node).
4. Démarrer `python lancer_dev.py` (ou `app_dynamite_agile.py --port 8080`). Capturer l'écran avec Playwright en
   **Thème par défaut** et en **Terminal** (Training ou Admin), à 1440 px et en largeur étroite. Console sans erreur, aucun « null » à l'écran.
5. Mettre à jour `APP_VERSION`, `docs/ETAT_PROJET.md`, `docs/DECISIONS.md` et `CLAUDE.md`. Ajouter
   `docs/FONDATIONS.md` si le noyau ou le §5 change.
