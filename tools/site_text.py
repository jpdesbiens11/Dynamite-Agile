"""Texts of the website per language (D-O-015, D-O-017), read by tools/build_site.py.

The module names and the technical terms stay in English in both languages (docs/GLOSSARY_EN.md). The French pages are
tools/site/*.html, the English ones tools/site/en/*.html; what the pages share (the descent into the mine, the tools
grid, the terminal, the top bar and the footer) is built from the tables below.
"""

LANGS = ("fr", "en")

# 0.60.36 (D-O-045): banner of the installation page (latest version + date, how to update an installed portal)
LATEST = {
    "fr": ("Dernière version :", "Voir toutes les versions →",
           "Déjà installé ? ⚙ Admin → Update → « Mise à jour en ligne » : vérifier, lire, approuver, suivre en direct."),
    "en": ("Latest version:", "See all versions →",
           "Already installed? ⚙ Admin → Update → « Mise à jour en ligne » (online update): check, read, approve, follow live."),
}
NAV = {"fr": ("Accueil", "Installation", "Guide", "Versions"), "en": ("Home", "Installation", "Guide", "Versions")}  # 0.60.12
SWITCH = {"fr": ("EN", "English", "en"), "en": ("FR", "Français", "fr")}  # (label, title, hreflang) of the other language

# (logo, depth in m, name, {lang: (in the mine, in the project)}) -- the descent of the landing page and the guide (D-O-014);
# 0.60.40 (D-O-049): in the order of a project, deeper at every step, down to the diamonds. HeadLamp keeps its name.
MINE = [
    ("help", 0, "HeadLamp & Training", {
        "fr": ("On allume la HeadLamp avant de descendre : elle éclaire la galerie juste devant soi.",
               "Le <b>tour guidé</b>, un Space bac à sable pour s'exercer sans risque, et la <b>formation</b> de l'équipe."),
        "en": ("You switch on the HeadLamp before going down: it lights the tunnel just ahead.",
               "The <b>guided tour</b>, a sandbox Space to practise risk-free, and the team's <b>training</b>.")}),
    ("exploration", 60, "Exploration", {
        "fr": ("La prospection : on étudie le terrain et on décide où creuser, dans quel ordre.",
               "Le <b>plan du produit</b> : phases du PDP (Discovery, Concept, Design, Validation), MVP, jalons, Gantt."),
        "en": ("Prospecting: you study the ground and decide where to dig, in which order.",
               "The <b>product plan</b>: PDP phases (Discovery, Concept, Design, Validation), MVPs, milestones, Gantt.")}),
    ("dynamite", 140, "Dynamite", {
        "fr": ("La charge qui fait sauter la roche : on dynamite le savoir brut pour le dégager.",
               "Le <b>wiki</b> du produit : notes, comptes rendus, décisions, procédures, pages préparées avec l'IA."),
        "en": ("The charge that blasts the rock: raw knowledge is blasted loose and cleared.",
               "The product's <b>wiki</b>: notes, minutes, decisions, procedures, pages drafted with AI.")}),
    ("goldmine", 230, "Goldmine", {
        "fr": ("Le filon d'or : ce qu'on est venu chercher, trié pépite par pépite.",
               "Les <b>besoins du client et les requirements</b>, tracés jusqu'à l'essai qui les prouve."),
        "en": ("The gold vein: what you came for, sorted nugget by nugget.",
               "The <b>customer needs and requirements</b>, traced to the test that proves them.")}),
    ("tools", 330, "Tools & Generator", {
        "fr": ("La boîte à outils et le poinçon des lots : chaque wagon reçoit son numéro.",
               "Les <b>méthodes de conception</b> (idéation, Pugh, Kepner-Tregoe) et le nom de chaque livrable."),
        "en": ("The toolbox and the batch punch: every wagon gets its number.",
               "The <b>design methods</b> (ideation, Pugh, Kepner-Tregoe) and the name of every deliverable.")}),
    ("agile", 450, "Agile", {
        "fr": ("Les équipes de forage, par quarts : chacune sait quel front attaquer.",
               "<b>Backlog, sprints et Board</b> d'un MVP à l'autre ; Change Management quand la galerie dévie."),
        "en": ("The drilling crews, in shifts: each one knows which face to work.",
               "<b>Backlog, sprints and Board</b> from one MVP to the next; Change Management when the tunnel drifts.")}),
    ("testing", 580, "Testing", {
        "fr": ("L'essai du minerai : on mesure la teneur avant de déclarer le filon rentable.",
               "La <b>Test Base</b> du produit, ses procédures et ses plans qui prouvent chaque requirement."),
        "en": ("Assaying the ore: the grade is measured before the vein is declared worth it.",
               "The product's <b>Test Base</b>, its procedures and plans that prove each requirement.")}),
    ("timesheet", 720, "Timesheet", {
        "fr": ("Le carnet de quart : qui a travaillé à quel front, combien d'heures.",
               "Les <b>heures par étape du PDP</b>, les vacances, les réclamations de financement."),
        "en": ("The shift log: who worked which face, for how many hours.",
               "The <b>hours per PDP step</b>, vacation, funding claims.")}),
    ("diamond", 1000, "Diamond", {  # 0.60.11 (D-O-023): the deepest gallery
        "fr": ("Les diamants, à 1 000 m : la pierre la plus dure, taillée facette par facette.",
               "L'<b>analyse fonctionnelle</b> : arbre des fonctions, structure, pièces, risques et DFMEA, avec leurs responsables."),
        "en": ("The diamonds, 1,000 m down: the hardest stone, cut facet by facet.",
               "The <b>functional analysis</b>: function tree, structure, parts, risks and DFMEA, with their owners.")}),
]

# 0.60.40 (D-O-049): the storyline before the descent -- the need of the industry and of young engineers, scene by scene
STORY_HEAD = {"fr": ('Le <span class="hl" style="--hlc: var(--o)">besoin</span>, avant la mine',
                     "Pourquoi cet outil existe : ce qu'un jeune ingénieur vit en arrivant, ce que l'industrie lui demande."),
              "en": ('The <span class="hl" style="--hlc: var(--o)">need</span>, before the mine',
                     "Why this tool exists: what a young engineer lives on day one, what the industry expects.")}
STORY = [
    ("search", {"fr": ("Le premier projet", "Une idée, une équipe de quatre, un semestre. Les notes sont dans un cahier, les besoins "
                       "dans un courriel, le plan dans un tableur, les essais nulle part. Personne ne sait ce qui est décidé."),
                "en": ("The first project", "An idea, a team of four, one semester. Notes in a notebook, needs in an email, the plan "
                       "in a spreadsheet, tests nowhere. Nobody knows what has been decided.")}),
    ("audit", {"fr": ("Ce que l'industrie exige", "Chaque requirement relié au besoin du client et prouvé par un essai, les risques "
                      "analysés (DFMEA), des revues de conception, les heures justifiées pour le financement : c'est le métier."),
               "en": ("What the industry expects", "Every requirement tied to a customer need and proven by a test, risks analysed "
                      "(DFMEA), design reviews, hours justified for funding: that is the job.")}),
    ("spaces", {"fr": ("Ce qui manque", "Les outils des grandes entreprises coûtent cher et demandent des mois ; les outils gratuits "
                       "sont épars. L'équipe étudiante ou la start-up apprend la rigueur trop tard, souvent à ses dépens."),
                "en": ("What is missing", "Big-company tools are expensive and take months; free tools are scattered. Student teams "
                       "and start-ups learn rigour too late, often the hard way.")}),
    ("bolt", {"fr": ("Un Space, un produit", "DynamiteAgile réunit tout dans un Space par produit, du besoin au lancement, MVP0 à MVPx. "
                     "Un assistant IA prépare le Space au complet ; l'équipe apprend la méthode en l'appliquant."),
              "en": ("One Space, one product", "DynamiteAgile brings everything into one Space per product, from need to launch, "
                     "MVP0 to MVPx. An AI assistant prepares the whole Space; the team learns the method by applying it.")}),
]
DIAMONDS = {"fr": "Vous êtes au fond : <b>les diamants</b>. Un produit dont chaque fonction, chaque risque et chaque essai est connu, "
                  "et une équipe qui sait pourquoi.",
            "en": "You have reached the bottom: <b>the diamonds</b>. A product whose every function, risk and test is known, and a "
                  "team that knows why."}

# the tools grid of the landing page in English (the French one comes from tools/build_vitrine.TOOLS)
TOOLS_EN = {
    "Dashboard": "Everything waiting for you in all your Spaces, with your @mentions and a status you change in place.",
    "Goldmine": "Needs and requirements: Need Status, F-XX functions, criticality, Test Procedure, customer Q&A.",
    "Diamond": "The functional analysis: tree, structure, parts x functions, risks and DFMEA; Excel, draw.io and Word export.",
    "Exploration": "The project plan over several months: phases, predecessors, milestones, Gantt and Excel round trip.",
    "Agile": "Backlog, Sprints and Board; Change Management with PRs, bugs and ECNs approved by the CCB.",
    "Dynamite": "The wiki: visual editor, live ticket blocks, procedures, BDC, Word and PDF export.",
    "Testing": "The Test Base of a consumer product (safety, EMC, IP, drop, life), Test Plans and central lists.",
    "Tools": "Brainwriting ideation, Pugh Matrix, Kepner-Tregoe and the Generator of the PDP deliverables.",
    "Training": "Topics, training plans, tests graded on the server, follow-up by the instructor.",
    "Timesheet": "My week per PDP step, approval, Excel export and Word report.",
    "Help & HeadLamp": "The step-by-step guide, the FAQ and a sandbox Space to learn risk-free.",
}
TOOLS_HEAD_EN = ('    <h2 class="reveal">Eleven tools, <span class="hl" style="--hlc: var(--b)">one sign-in</span></h2>\n'
                 '    <p class="sub reveal">One account, the same rights per Space, the same search everywhere and the same audit log.</p>')

# 0.60.34: what arrived lately, under the tools grid of the landing page -- (icon, accent, {lang: (title, text)})
NEWS = [
    ("bolt", "--y", {"fr": ("Commencer avec un assistant IA", "Une entrevue à choix de réponses avec Claude prépare le fichier du projet ; "
                            "« Commencer » crée l'équipe, les requirements, les essais, l'arbre fonctionnel, le DFMEA et le plan du PDP."),
                     "en": ("Start with an AI assistant", "A multiple-choice interview with Claude prepares the project file; « Commencer » "
                            "creates the team, requirements, tests, functional tree, DFMEA and PDP plan.")}),
    ("diamond", "--c", {"fr": ("Diamond, du premier coup d'œil au rapport", "Une ligne de DFMEA par fonction, l'essai clé relié, les bonnes "
                               "pratiques de l'industrie ; tout s'exporte en Excel, draw.io et Word pour un jury ou un investisseur."),
                        "en": ("Diamond, from first look to report", "One DFMEA row per function, the key test linked, industry good "
                               "practices; everything exports to Excel, draw.io and Word for a jury or an investor.")}),
    ("share", "--p", {"fr": ("Au téléphone, et partagé", "Goldmine, Testing et la feuille de temps en cartes, des pages Dynamite avec l'IA ; "
                             "Partager par texto, Messenger, WhatsApp, courriel ou code QR."),
                      "en": ("On the phone, and shared", "Goldmine, Testing and the timesheet as cards, Dynamite pages with AI; Share by "
                             "text, Messenger, WhatsApp, email or QR code.")}),
    ("spaces", "--g", {"fr": ("Mises à jour officielles", "⚙ Admin → Update : une version à la fois ou plusieurs d'un coup, les données "
                              "intactes ; l'interface plus légère sur le réseau."),
                       "en": ("Official updates", "⚙ Admin → Update: one version at a time or several at once, data intact; a lighter "
                              "interface on the network.")}),
]
NEWS_HEAD = {"fr": ('Les <span class="hl" style="--hlc: var(--y)">nouveautés</span>', "Ce qui est arrivé dans les dernières versions de la branche 0.60."),
             "en": ('What is <span class="hl" style="--hlc: var(--y)">new</span>', "What arrived in the latest versions of the 0.60 branch.")}

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
    text = ("DynamiteAgile · free software under the MIT licence · version {} · Jean-Philippe Desbiens · "
            if lang == "en" else "DynamiteAgile · logiciel libre sous licence MIT · version {} · Jean-Philippe Desbiens · ")
    return '<footer>' + text.format(version) + '<a href="{}">GitHub</a></footer>'.format(repo)
