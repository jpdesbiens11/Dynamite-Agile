"""Texts of the website per language (D-O-015, D-O-017), read by tools/build_site.py.

The module names and the technical terms stay in English in both languages (docs/GLOSSARY_EN.md). The French pages are
tools/site/*.html, the English ones tools/site/en/*.html; what the pages share (the descent into the mine, the tools
grid, the terminal, the top bar and the footer) is built from the tables below.
"""

LANGS = ("fr", "en")
NAV = {"fr": ("Accueil", "Installation", "Guide"), "en": ("Home", "Installation", "Guide")}
SWITCH = {"fr": ("EN", "English", "en"), "en": ("FR", "Français", "fr")}  # (label, title, hreflang) of the other language

# (logo, depth in m, name, {lang: (in the mine, in the project)}) -- the descent of the landing page and the guide (D-O-014)
MINE = [
    ("exploration", 40, "Exploration", {
        "fr": ("La prospection : on étudie le terrain et on décide où creuser, dans quel ordre.",
               "Le <b>plan du projet</b> : phases du PDP, jalons, prédécesseurs, Gantt."),
        "en": ("Prospecting: you study the ground and decide where to dig, in which order.",
               "The <b>project plan</b>: PDP phases, milestones, predecessors, Gantt.")}),
    ("dynamite", 90, "Dynamite", {
        "fr": ("La charge qui fait sauter la roche : on dynamite le savoir brut pour le dégager.",
               "Le <b>wiki</b> de l'équipe : notes, comptes rendus, procédures, décisions."),
        "en": ("The charge that blasts the rock: raw knowledge is blasted loose and cleared.",
               "The team's <b>wiki</b>: notes, minutes, procedures, decisions.")}),
    ("goldmine", 150, "Goldmine", {
        "fr": ("Le filon d'or : ce qu'on est venu chercher, trié pépite par pépite.",
               "Les <b>besoins et requirements</b>, tracés du client jusqu'à leur essai."),
        "en": ("The gold vein: what you came for, sorted nugget by nugget.",
               "The <b>needs and requirements</b>, traced from the customer to their test.")}),
    ("agile", 210, "Agile", {
        "fr": ("Les équipes de forage, par quarts : chacune sait quel front attaquer.",
               "<b>Backlog, sprints et Board</b> ; Change Management quand la galerie dévie."),
        "en": ("The drilling crews, in shifts: each one knows which face to work.",
               "<b>Backlog, sprints and Board</b>; Change Management when the tunnel drifts.")}),
    ("testing", 270, "Testing", {
        "fr": ("L'essai du minerai : on mesure la teneur avant de déclarer le filon rentable.",
               "La <b>Test Base</b>, les procédures et les plans qui prouvent chaque requirement."),
        "en": ("Assaying the ore: the grade is measured before the vein is declared worth it.",
               "The <b>Test Base</b>, the procedures and the plans that prove each requirement.")}),
    ("tools", 330, "Tools & Generator", {
        "fr": ("La boîte à outils et le poinçon des lots : chaque wagon reçoit son numéro.",
               "Les <b>méthodes de conception</b> (Pugh, Kepner-Tregoe) et le nom de chaque document."),
        "en": ("The toolbox and the batch punch: every wagon gets its number.",
               "The <b>design methods</b> (Pugh, Kepner-Tregoe) and the name of every document.")}),
    ("timesheet", 390, "Timesheet", {
        "fr": ("Le carnet de quart : qui a travaillé à quel front, combien d'heures.",
               "Les <b>heures par étape du PDP</b>, les vacances, les réclamations de financement."),
        "en": ("The shift log: who worked which face, for how many hours.",
               "The <b>hours per PDP step</b>, vacation, funding claims.")}),
    ("training", 450, "Training & HeadLamp", {
        "fr": ("L'école de la mine et la lanterne qui éclaire la galerie.",
               "La <b>formation</b>, le tour guidé et un bac à sable pour s'exercer sans risque."),
        "en": ("The mining school and the headlamp that lights the tunnel.",
               "<b>Training</b>, the guided tour and a sandbox to practise risk-free.")}),
    ("diamond", 1000, "Diamond", {  # 0.60.11 (D-O-023): the deepest gallery
        "fr": ("Le diamant, à 1 000 m : la pierre la plus dure, taillée facette par facette.",
               "L'<b>analyse fonctionnelle</b> : arbre des fonctions, puis structure fonctionnelle, risques et DFMEA."),
        "en": ("The diamond, 1,000 m down: the hardest stone, cut facet by facet.",
               "The <b>functional analysis</b>: function tree, then functional structure, risks and DFMEA.")}),
]

# the tools grid of the landing page in English (the French one comes from tools/build_vitrine.TOOLS)
TOOLS_EN = {
    "Dashboard": "Everything waiting for you in all your Spaces, with your @mentions and a status you change in place.",
    "Goldmine": "Needs and requirements: Need Status, F-XX functions, criticality, Test Procedure, customer Q&A.",
    "Exploration": "The project plan over several months: phases, predecessors, milestones, Gantt and Excel round trip.",
    "Agile": "Backlog, Sprints and Board; Change Management with PRs, bugs and ECNs approved by the CCB.",
    "Dynamite": "The wiki: visual editor, live ticket blocks, procedures, BDC, Word and PDF export.",
    "Testing": "The Test Base of a consumer product (safety, EMC, IP, drop, life), Test Plans and central lists.",
    "Tools": "Brainwriting ideation, Pugh Matrix, Kepner-Tregoe and the Generator of the PDP deliverables.",
    "Training": "Topics, training plans, tests graded on the server, follow-up by the instructor.",
    "Timesheet": "My week per PDP step, approval, Excel export and Word report.",
    "Help & HeadLamp": "The step-by-step guide, the FAQ and a sandbox Space to learn risk-free.",
}
TOOLS_HEAD_EN = ('    <h2 class="reveal">Ten tools, <span class="hl" style="--hlc: var(--b)">one sign-in</span></h2>\n'
                 '    <p class="sub reveal">One account, the same rights per Space, the same search everywhere and the same audit log.</p>')

# what the vitrine script types in the Test Plan of the « day with the team » and the label of the hero sketch
TYPED = {"fr": "Objectif : vérifier que le pistolet chaud tombé d'un mètre reste sûr et fonctionnel.",
         "en": "Objective: check that the hot glue gun dropped from one metre stays safe and working."}
HERO_LABEL = {"fr": "Un arbre de fonctions à trois niveaux, des engrenages et un crayon",
              "en": "A three-level function tree, gears and a pencil"}


def term(lang, site_url):
    """The lines the terminal of the landing page types."""
    if lang == "en":
        return ["$ ssh root@203.0.113.10",
                "root@server:~# curl -fsSL {}/install.sh | sudo DA_LANG=en bash -s -- workshop.my-domain.com me@example.com"
                .format(site_url),
                "== 1/7 System packages … == 6/7 Service « dynamite-agile »",
                "== 7/7 Installed",
                "✓ Open https://workshop.my-domain.com — account admin, password shown above"]
    return ["$ ssh root@203.0.113.10",
            "root@serveur:~# curl -fsSL {}/install.sh | sudo bash -s -- atelier.mon-domaine.ca moi@exemple.ca".format(site_url),
            "== 1/7 Paquets du système … == 6/7 Service « dynamite-agile »",
            "== 7/7 C'est installé",
            "✓ Ouvrez https://atelier.mon-domaine.ca — compte admin, mot de passe affiché ci-dessus"]


def footer(lang, version, repo):
    text = ("Dynamite | Agile · free software under the MIT licence · version {} · Jean-Philippe Desbiens · "
            if lang == "en" else "Dynamite | Agile · logiciel libre sous licence MIT · version {} · Jean-Philippe Desbiens · ")
    return '<footer>' + text.format(version) + '<a href="{}">GitHub</a></footer>'.format(repo)
