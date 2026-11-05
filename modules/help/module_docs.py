"""Documentation of every module for learning students (0.60.45, D-O-054): why the module exists, the need it covers,
how to use it step by step, what it does from one MVP to the next (MVP 0 to MVP 3, then MVP x) and its references from the
most to the least relevant (module_docs_refs.py). One source for two readers:
- the HeadLamp library in the tool (module_docs_pages.py: one Dynamite page per module, regenerated while nobody edits it);
- the « Modules » page of the website (tools/build_site.py, French and English).

    MODULES = [{key, name, depth, refs: [ids], parts: [{name, fr, en, refs}], fr: {...}, en: {...}}]
    lang dict = {role, why, need, steps: [(title, text)], mvps: [MVP 0, MVP 1, MVP 2, MVP 3]}
The module names and the technical terms stay in English in both languages (docs/GLOSSARY_EN.md).
"""
from .module_docs_more import MORE

# the four loops of the PDP (D-O-021), then every later version
MVPS = {"fr": ("MVP 0 · Discovery — le problème existe-t-il ?", "MVP 1 · Concept — le concept plaît-il ?",
               "MVP 2 · Design — ça fonctionne ?", "MVP 3 · Validation — prêt pour le marché ?"),
        "en": ("MVP 0 · Discovery — does the problem exist?", "MVP 1 · Concept — do people want this concept?",
               "MVP 2 · Design — does it work?", "MVP 3 · Validation — ready for the market?")}
MVP_X = {"fr": "MVP x · Après le lancement, chaque nouvelle version du produit refait la même boucle Build-Measure-Learn, dans le même Space.",
         "en": "MVP x · After launch, every new version of the product runs the same Build-Measure-Learn loop, in the same Space."}


def _m(key, name, depth, refs, fr, en, parts=()):
    return {"key": key, "name": name, "depth": depth, "refs": list(refs), "fr": fr, "en": en, "parts": list(parts)}


FIRST = [
    _m("help", "HeadLamp & Training", 0, ["mit_ocw", "ulrich", "ries", "blank"], fr={
        "role": "Apprendre l'outil et la méthode sans rien casser.",
        "why": "On n'apprend pas la rigueur d'ingénierie dans un document : on l'apprend en la pratiquant. HeadLamp est un Space "
               "bac à sable où chaque outil a son exercice ; Training suit ce que chaque membre de l'équipe doit savoir.",
        "need": "Une équipe nouvelle doit être productive en une semaine, sans peur d'abîmer le vrai projet, et l'enseignant ou le "
                "chef d'équipe doit voir qui sait faire quoi.",
        "steps": [("Rejoindre HeadLamp", "Help → « Rejoindre HeadLamp [Sandbox] » : vous devenez éditeur du bac à sable."),
                  ("Suivre le tour", "Help montre les étapes dans l'ordre d'un projet ; chaque étape a son ticket d'exercice."),
                  ("Lire la documentation", "Cette bibliothèque : une page par module, avec ses références."),
                  ("Planifier la formation", "Training : un plan par personne, les topics à couvrir et leur échéance."),
                  ("Se tester", "Les tests de Training sont corrigés par le serveur ; l'instructeur suit les résultats.")],
        "mvps": ["Chacun fait le parcours HeadLamp et lit les pages Exploration, Goldmine et Dynamite.",
                 "Les pages Tools et Diamond (arbre fonctionnel) avant de choisir un concept.",
                 "Les pages Agile, Diamond (DFMEA) et Testing avant de concevoir les sous-systèmes.",
                 "Les pages Testing et Timesheet avant la validation et la réclamation de financement."]}, en={
        "role": "Learn the tool and the method without breaking anything.",
        "why": "Engineering rigour is not learned from a document: it is learned by practising it. HeadLamp is a sandbox Space where "
               "every tool has its exercise; Training follows what each team member must know.",
        "need": "A new team must be productive within a week, without fear of damaging the real project, and the instructor or team "
                "lead must see who can do what.",
        "steps": [("Join HeadLamp", "Help → « Rejoindre HeadLamp [Sandbox] »: you become an editor of the sandbox."),
                  ("Follow the tour", "Help shows the steps in the order of a project; every step has its exercise ticket."),
                  ("Read the documentation", "This library: one page per module, with its references."),
                  ("Plan the training", "Training: one plan per person, the topics to cover and their due date."),
                  ("Test yourself", "Training tests are graded by the server; the instructor follows the results.")],
        "mvps": ["Everyone does the HeadLamp path and reads the Exploration, Goldmine and Dynamite pages.",
                 "The Tools and Diamond (function tree) pages before choosing a concept.",
                 "The Agile, Diamond (DFMEA) and Testing pages before designing the subsystems.",
                 "The Testing and Timesheet pages before validation and the funding claim."]}),
    _m("exploration", "Exploration", 60, ["ulrich", "stagegate", "cooper_agile", "ries", "leancanvas", "watt_plan", "nasa_wbs",
                                          "seneca_cpm", "blank", "running_lean", "bmc"], fr={
        "role": "Le plan du produit : phases du PDP, MVP, jalons et Gantt.",
        "why": "Un projet de produit est une suite de paris : on ne peut pas tout concevoir d'un coup. Le PDP découpe le travail en "
               "phases qui se ferment sur une revue ; le Lean Startup ajoute un MVP par phase pour tester d'abord les hypothèses "
               "les plus risquées.",
        "need": "Savoir quoi faire cette semaine, ce qui bloque quoi (chemin critique) et quand la prochaine revue décide de "
                "persévérer ou de pivoter.",
        "steps": [("Partir du plan de référence", "« Commencer » crée un plan du PDP selon la durée du projet et l'équipe."),
                  ("Ajuster les tâches", "Une ligne par livrable : code, phase, durée, prédécesseurs, responsable."),
                  ("Placer les jalons", "Lean Canvas, Concept Review, PDR, CDR et Validation Report ferment chaque phase."),
                  ("Lire le Gantt", "Le chemin critique montre les tâches sans marge : ce sont elles qu'on protège."),
                  ("Faire l'aller-retour Excel", "Exporter, retravailler hors ligne, réimporter : les codes servent de clé.")],
        "mvps": ["Planifier les entrevues clients, le Lean Canvas et la page d'essai ; jalon : hypothèses validées ou non.",
                 "Planifier l'idéation, la matrice de Pugh et la Concept Review ; jalon : un concept retenu.",
                 "Planifier les sous-systèmes, les calculs et les revues PDR et CDR ; jalon : le design figé.",
                 "Planifier la fabrication, les essais et le Validation Report ; jalon : prêt pour le marché."]}, en={
        "role": "The product plan: PDP phases, MVPs, milestones and Gantt.",
        "why": "A product project is a series of bets: you cannot design everything at once. The PDP cuts the work into phases that end "
               "on a review; the Lean Startup adds one MVP per phase to test the riskiest hypotheses first.",
        "need": "Knowing what to do this week, what blocks what (critical path) and when the next review decides to persevere or pivot.",
        "steps": [("Start from the reference plan", "« Commencer » creates a PDP plan from the length of the project and the team."),
                  ("Adjust the tasks", "One line per deliverable: code, phase, duration, predecessors, owner."),
                  ("Place the milestones", "Lean Canvas, Concept Review, PDR, CDR and Validation Report close each phase."),
                  ("Read the Gantt", "The critical path shows the tasks without slack: those are the ones to protect."),
                  ("Round-trip with Excel", "Export, rework offline, import again: the codes are the key.")],
        "mvps": ["Plan the customer interviews, the Lean Canvas and the landing page; milestone: hypotheses confirmed or not.",
                 "Plan ideation, the Pugh Matrix and the Concept Review; milestone: one concept chosen.",
                 "Plan the subsystems, the calculations and the PDR and CDR; milestone: design frozen.",
                 "Plan manufacturing, tests and the Validation Report; milestone: ready for the market."]}),
    _m("dynamite", "Dynamite", 140, ["uga_notebook", "fda_design", "gds_adr", "uab_notebook", "writethedocs"], fr={
        "role": "Le wiki du produit : notes, comptes rendus, décisions, procédures.",
        "why": "Ce qui n'est pas écrit n'existe pas : une décision oubliée se reprend trois fois. Le cahier d'ingénierie et le Design "
               "History File de l'industrie gardent la trace du pourquoi ; Dynamite en est la version vivante et partagée.",
        "need": "Retrouver en dix secondes pourquoi on a choisi telle solution, qui l'a décidé, et la procédure à suivre.",
        "steps": [("Créer la page", "« + Page » dans le Space du produit, ou « ✨ Avec l'IA » pour importer un brouillon en Markdown."),
                  ("Structurer", "Titres, tableaux, panneaux, status colorés ; la table des matières se construit seule."),
                  ("Relier", "Un bloc Ticket montre le status vivant d'un ticket Agile ; un lien mène au requirement."),
                  ("Décider par écrit", "Une page « Décisions » : contexte, décision, conséquences, date (comme un ADR)."),
                  ("Garder l'historique", "Chaque enregistrement est une version ; l'historique montre qui a changé quoi.")],
        "mvps": ["Le Lean Canvas, les notes d'entrevues clients et la liste des hypothèses.",
                 "Les comptes rendus d'idéation et la page de décision du concept retenu.",
                 "Les notes de calcul, les comptes rendus des revues PDR et CDR, les procédures d'assemblage.",
                 "Les procédures d'essai, le rapport de validation et les leçons apprises."]}, en={
        "role": "The product's wiki: notes, minutes, decisions, procedures.",
        "why": "What is not written does not exist: a forgotten decision gets made three times. The engineering notebook and the "
               "industry's Design History File keep the trace of the why; Dynamite is its living, shared version.",
        "need": "Finding in ten seconds why a solution was chosen, who decided, and which procedure to follow.",
        "steps": [("Create the page", "« + Page » in the product's Space, or « ✨ Avec l'IA » to import a Markdown draft."),
                  ("Structure it", "Headings, tables, panels, coloured status; the table of contents builds itself."),
                  ("Link it", "A Ticket block shows the live status of an Agile ticket; a link leads to the requirement."),
                  ("Decide in writing", "A « Decisions » page: context, decision, consequences, date (like an ADR)."),
                  ("Keep the history", "Every save is a version; the history shows who changed what.")],
        "mvps": ["The Lean Canvas, the customer interview notes and the list of hypotheses.",
                 "The ideation minutes and the decision page of the chosen concept.",
                 "Calculation notes, PDR and CDR minutes, assembly procedures.",
                 "Test procedures, the validation report and lessons learned."]}),
    _m("goldmine", "Goldmine", 230, ["nf16271", "bordeaux", "griffin", "incose_gtwr", "sebok_needs", "volere", "jama"], fr={
        "role": "Les besoins du client et les requirements, tracés jusqu'à l'essai qui les prouve.",
        "why": "Un produit réussi répond à un besoin réel. Le cahier des charges fonctionnel (CdCF) traduit ce besoin en requirements "
               "mesurables ; la traçabilité besoin → requirement → essai prouve qu'on a livré ce qui était demandé.",
        "need": "Savoir à tout moment ce que le client veut, ce que le produit doit faire, avec quel critère, et si c'est prouvé.",
        "steps": [("Noter les besoins", "Un Need par besoin, avec la partie prenante qui l'exprime et son importance."),
                  ("Poser les questions", "Le registre Q&A garde chaque question au client et sa réponse, liée au besoin."),
                  ("Écrire les requirements", "Une phrase vérifiable, sa raison, sa source (client, norme), son critère d'acceptation."),
                  ("Confirmer les normes", "Un requirement tiré d'une norme arrive « À vérifier » : on confirme l'édition et l'article."),
                  ("Tracer", "Chaque requirement pointe vers son essai (Testing) ; « Verified » quand le résultat est joint.")],
        "mvps": ["Les besoins des entrevues clients et les questions ouvertes ; quelques requirements de départ.",
                 "Le CdCF : fonctions de service, critères, niveaux et flexibilité ; les normes applicables.",
                 "Les requirements dérivés des sous-systèmes, chacun relié à son essai.",
                 "La matrice de traçabilité complète : chaque requirement « Verified » ou justifié."]}, en={
        "role": "Customer needs and requirements, traced to the test that proves them.",
        "why": "A successful product answers a real need. The functional specification (CdCF) turns that need into measurable "
               "requirements; traceability need → requirement → test proves you delivered what was asked.",
        "need": "Knowing at any time what the customer wants, what the product must do, with which criterion, and whether it is proven.",
        "steps": [("Write down the needs", "One Need per need, with the stakeholder who expresses it and its importance."),
                  ("Ask the questions", "The Q&A register keeps every question to the customer and its answer, tied to the need."),
                  ("Write the requirements", "A verifiable sentence, its rationale, its source (customer, standard), its acceptance criterion."),
                  ("Confirm the standards", "A requirement taken from a standard arrives « À vérifier »: confirm the edition and clause."),
                  ("Trace", "Every requirement points to its test (Testing); « Verified » once the result is attached.")],
        "mvps": ["The needs from customer interviews and the open questions; a few starting requirements.",
                 "The CdCF: service functions, criteria, levels and flexibility; the applicable standards.",
                 "Requirements derived for the subsystems, each tied to its test.",
                 "The full traceability matrix: every requirement « Verified » or justified."]}),
    _m("tools", "Tools & Generator", 330, ["illinois_pugh", "kt_prework", "ideo", "zwicky", "scamper", "triz", "kt_book",
                                          "leancanvas", "bmc"], fr={
        "role": "Les méthodes de conception (idéation, Pugh, Kepner-Tregoe) et le nom de chaque livrable.",
        "why": "Le premier concept est rarement le bon. Les méthodes de créativité élargissent le choix ; la matrice de Pugh et "
               "Kepner-Tregoe le réduisent avec des critères écrits, pas des préférences. Le Generator donne à chaque livrable du "
               "PDP une référence unique.",
        "need": "Produire beaucoup d'idées, choisir de façon défendable devant un jury ou un investisseur, et retrouver chaque document.",
        "steps": [("Idéer", "Brainwriting : chacun écrit ses idées, puis les enrichit ; SCAMPER et la matrice morphologique aident."),
                  ("Comparer", "Matrice de Pugh : un concept de référence, chaque critère en +, 0 ou −, puis la version pondérée."),
                  ("Décider", "Kepner-Tregoe : critères MUST (éliminatoires) et WANT (pondérés), puis les risques du choix."),
                  ("Nommer les livrables", "Generator : type (LCV, CRV, CDCF, PDR, CDR, VVR…), étape du PDP, révision."),
                  ("Archiver", "Le livrable porte sa référence ; la page de décision dans Dynamite la cite.")],
        "mvps": ["Lean Canvas (LCV) et hypothèses ; brainstorm sur le problème, pas encore sur la solution.",
                 "Brainwriting, matrice morphologique, Pugh puis Kepner-Tregoe ; Concept Review (CRV).",
                 "Pugh sur les solutions de chaque sous-système ; références PDR et CDR.",
                 "Kepner-Tregoe sur les choix de fabrication ; Validation Report (VVR)."]}, en={
        "role": "Design methods (ideation, Pugh, Kepner-Tregoe) and the name of every deliverable.",
        "why": "The first concept is rarely the right one. Creativity methods widen the choice; the Pugh Matrix and Kepner-Tregoe "
               "narrow it with written criteria, not preferences. The Generator gives every PDP deliverable a unique reference.",
        "need": "Producing many ideas, choosing in a way you can defend before a jury or an investor, and finding every document.",
        "steps": [("Ideate", "Brainwriting: everyone writes ideas, then builds on the others'; SCAMPER and the morphological chart help."),
                  ("Compare", "Pugh Matrix: one reference concept, each criterion as +, 0 or −, then the weighted version."),
                  ("Decide", "Kepner-Tregoe: MUST criteria (eliminating) and WANT criteria (weighted), then the risks of the choice."),
                  ("Name the deliverables", "Generator: type (LCV, CRV, CDCF, PDR, CDR, VVR…), PDP step, revision."),
                  ("Archive", "The deliverable carries its reference; the decision page in Dynamite cites it.")],
        "mvps": ["Lean Canvas (LCV) and hypotheses; brainstorm on the problem, not yet on the solution.",
                 "Brainwriting, morphological chart, Pugh then Kepner-Tregoe; Concept Review (CRV).",
                 "Pugh on the solutions of each subsystem; PDR and CDR references.",
                 "Kepner-Tregoe on manufacturing choices; Validation Report (VVR)."]}),
]

MODULES = FIRST + MORE
