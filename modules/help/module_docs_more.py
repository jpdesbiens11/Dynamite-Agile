"""Documentation of the modules, second half (0.60.45, D-O-054): Agile, Testing, Timesheet and Diamond with its five
facets. Same shape as module_docs.FIRST."""


def _m(key, name, depth, refs, fr, en, parts=()):
    return {"key": key, "name": name, "depth": depth, "refs": list(refs), "fr": fr, "en": en, "parts": list(parts)}


def _part(name, refs, fr, en):
    return {"name": name, "refs": list(refs), "fr": fr, "en": en}


MORE = [
    _m("agile", "Agile", 450, ["scrum_fr", "scrum_hw", "kanban", "design_society", "manifesto", "arena_ecr", "kaizen_ecm", "scrum_en"], fr={
        "role": "Backlog, Sprints et Board d'un MVP à l'autre ; Change Management quand le design change.",
        "why": "Un plan de six mois se trompe toujours un peu. Scrum découpe le travail en Sprints courts qui livrent quelque chose "
               "de visible ; Kanban montre le flux et ce qui bloque. Quand un design approuvé doit changer, le Change Management "
               "garde la trace de la demande, de son impact et de son approbation.",
        "need": "Que chacun sache quoi faire aujourd'hui, que l'équipe voie ce qui avance et ce qui bloque, et qu'aucun changement "
                "de design ne passe sans décision.",
        "steps": [("Remplir le backlog", "Epics, stories, tasks et bugs ; chaque MVP est une Version, chaque ticket pointe vers la sienne."),
                  ("Planifier le Sprint", "Choisir les tickets des une ou deux prochaines semaines, avec leurs points et responsables."),
                  ("Suivre au Board", "To Do → In Progress → Done ; une @mention appelle un coéquipier."),
                  ("Relier", "Un ticket « implements » un requirement ; « Suivre dans Agile » transforme une action du DFMEA en ticket."),
                  ("Changer proprement", "Change Management : la demande (PR, bug, ECN), son impact, l'approbation du CCB.")],
        "mvps": ["Un Sprint d'entrevues et de maquettes papier ; le backlog de MVP 0 tient sur une page.",
                 "Les Sprints d'idéation et de prototypes de concept ; MVP 1 se ferme avec la Concept Review.",
                 "Les Sprints matériels et logiciels par sous-système ; les premiers ECN après la PDR.",
                 "Les Sprints de fabrication et d'essais ; chaque bug d'essai devient un ticket, chaque correction un ECN."]}, en={
        "role": "Backlog, Sprints and Board from one MVP to the next; Change Management when the design changes.",
        "why": "A six-month plan is always somewhat wrong. Scrum cuts the work into short Sprints that deliver something visible; "
               "Kanban shows the flow and what is blocked. When an approved design must change, Change Management keeps the "
               "request, its impact and its approval.",
        "need": "Everyone knows what to do today, the team sees what moves and what is stuck, and no design change goes through "
                "without a decision.",
        "steps": [("Fill the backlog", "Epics, stories, tasks and bugs; every MVP is a Version, every ticket points to its own."),
                  ("Plan the Sprint", "Pick the tickets of the next one or two weeks, with their points and owners."),
                  ("Follow the Board", "To Do → In Progress → Done; an @mention calls a teammate."),
                  ("Link", "A ticket « implements » a requirement; « Suivre dans Agile » turns a DFMEA action into a ticket."),
                  ("Change cleanly", "Change Management: the request (PR, bug, ECN), its impact, the CCB approval.")],
        "mvps": ["One Sprint of interviews and paper mock-ups; the MVP 0 backlog fits on one page.",
                 "Ideation Sprints and concept prototypes; MVP 1 closes with the Concept Review.",
                 "Hardware and software Sprints per subsystem; the first ECNs after the PDR.",
                 "Manufacturing and test Sprints; every test bug becomes a ticket, every fix an ECN."]}),
    _m("testing", "Testing", 580, ["sebok_verif", "dvpr", "nasa_se", "mathworks_v", "ccpsa", "scc_marks", "ices003", "fcc_auth",
                                   "osha_nrtl", "iec62368", "iec60335", "rohs"], fr={
        "role": "La Test Base du produit, ses procédures et ses plans qui prouvent chaque requirement.",
        "why": "Un requirement sans essai est une promesse. La vérification prouve qu'on a bien construit le produit (selon les "
               "requirements) ; la validation, qu'on a construit le bon produit (pour le client). Au Canada et aux États-Unis, un "
               "produit électrique grand public doit aussi passer la sécurité (CSA, UL) et la CEM (ICES-003, FCC Part 15).",
        "need": "Savoir quel essai prouve quoi, avec quel critère et quel moyen, et arriver au laboratoire de certification sans surprise.",
        "steps": [("Bâtir la Test Base", "Les essais du Space : sujet, catégorie, norme et article, méthode (T, A, I, D), objectif."),
                  ("Écrire la procédure", "Le moyen d'essai, les étapes et le critère d'acceptation, dans Testing ou une page Dynamite."),
                  ("Générer le Test Plan", "Choisir les essais d'un jalon : le plan liste requirements, échantillons et critères."),
                  ("Joindre le résultat", "Le rapport et les mesures ; le requirement relié passe « Verified »."),
                  ("Préparer la certification", "Les essais de sécurité et de CEM en pré-conformité avant le laboratoire reconnu.")],
        "mvps": ["Pas encore d'essai du produit : on mesure les hypothèses (entrevues, page d'essai).",
                 "Des essais rapides de concept (maquette, banc) et la liste des normes applicables.",
                 "La Test Base complète, une procédure par essai, les premiers essais de sous-systèmes et la pré-conformité.",
                 "Le Test Plan de validation, les essais sur prototypes de série, le rapport pour la certification."]}, en={
        "role": "The product's Test Base, its procedures and plans that prove each requirement.",
        "why": "A requirement without a test is a promise. Verification proves the product was built right (to the requirements); "
               "validation, that the right product was built (for the customer). In Canada and the United States, a consumer "
               "electrical product must also pass safety (CSA, UL) and EMC (ICES-003, FCC Part 15).",
        "need": "Knowing which test proves what, with which criterion and which means, and reaching the certification lab without surprises.",
        "steps": [("Build the Test Base", "The Space's tests: subject, category, standard and clause, method (T, A, I, D), objective."),
                  ("Write the procedure", "The test means, the steps and the acceptance criterion, in Testing or a Dynamite page."),
                  ("Generate the Test Plan", "Pick the tests of a milestone: the plan lists requirements, samples and criteria."),
                  ("Attach the result", "The report and the measurements; the linked requirement becomes « Verified »."),
                  ("Prepare certification", "Safety and EMC tests in pre-compliance before the recognised lab.")],
        "mvps": ["No product test yet: you measure the hypotheses (interviews, landing page).",
                 "Quick concept tests (mock-up, bench) and the list of applicable standards.",
                 "The full Test Base, one procedure per test, the first subsystem tests and pre-compliance.",
                 "The validation Test Plan, tests on production prototypes, the report for certification."]}),
    _m("timesheet", "Timesheet", 720, ["cra_salary", "cra_elig", "irap", "rq_rd", "cra_salt"], fr={
        "role": "Les heures par étape du PDP, les vacances et les réclamations de financement.",
        "why": "Le temps est la ressource la plus chère d'un projet. Le noter par étape du PDP montre où il passe vraiment ; pour "
               "la RS&DE, le PARI-CNRC ou un crédit de Revenu Québec, chaque heure réclamée doit être justifiée par une description.",
        "need": "Savoir combien coûte chaque phase, préparer une réclamation sans rien retaper, et respecter les congés de chacun.",
        "steps": [("Saisir la semaine", "Une plage par travail, sur le code de l'étape du PDP, avec une courte description."),
                  ("Soumettre", "Le vendredi ; l'approbateur (enseignant, chef d'équipe) approuve ou commente."),
                  ("Déclarer les congés", "Les codes de vacances et de congé santé du Space ne sont jamais réclamés."),
                  ("Rattacher au financement", "Un Funding Space et ses Budget Lines (réclamables ou non) pour le programme."),
                  ("Réclamer", "Export Excel ou rapport Word au destinataire, avec chaque plage et sa justification.")],
        "mvps": ["Les heures sur A-01 à A-06 : on voit le coût réel de la découverte client.",
                 "Les heures de la phase Concept (B-07 à B-12) ; première lecture du coût par livrable.",
                 "Les heures de conception par sous-système ; la description prépare la preuve d'incertitude technologique (RS&DE).",
                 "Les heures de fabrication et d'essais ; la réclamation de fin de projet sort en un export."]}, en={
        "role": "Hours per PDP step, vacation and funding claims.",
        "why": "Time is a project's most expensive resource. Logging it per PDP step shows where it really goes; for SR&ED, NRC IRAP "
               "or a Revenu Québec credit, every claimed hour must be justified by a description.",
        "need": "Knowing what each phase costs, preparing a claim without retyping anything, and respecting everyone's leave.",
        "steps": [("Fill in the week", "One slot per piece of work, on the PDP step code, with a short description."),
                  ("Submit", "On Friday; the approver (instructor, team lead) approves or comments."),
                  ("Declare leave", "The Space's vacation and sick-leave codes are never claimed."),
                  ("Attach to funding", "A Funding Space and its Budget Lines (claimable or not) for the programme."),
                  ("Claim", "Excel export or Word report to the recipient, with every slot and its justification.")],
        "mvps": ["Hours on A-01 to A-06: the real cost of customer discovery shows.",
                 "Hours of the Concept phase (B-07 to B-12); a first reading of the cost per deliverable.",
                 "Design hours per subsystem; the descriptions prepare the proof of technological uncertainty (SR&ED).",
                 "Manufacturing and test hours; the end-of-project claim comes out in one export."]}),
    _m("diamond", "Diamond", 1000, ["bordeaux", "aiag", "pahl", "watt_risk", "fs_first"], fr={
        "role": "L'analyse fonctionnelle : arbre des fonctions, structure, pièces, risques et DFMEA, avec leurs responsables.",
        "why": "On conçoit des fonctions avant de concevoir des pièces. L'analyse fonctionnelle oblige à dire ce que le produit doit "
               "faire, dans quel ordre et avec quels flux ; le DFMEA demande ensuite comment chaque fonction peut échouer, et quel "
               "essai le détectera. C'est la partie la plus profonde de la mine : là où sont les diamants.",
        "need": "Ne rien oublier : chaque fonction a sa solution, chaque pièce sert une fonction, chaque risque a son action et son "
                "responsable, chaque mode de défaillance grave a son essai.",
        "steps": [("Storyline", "L'usage du produit raconté scène par scène, avec des pictogrammes : on diverge en équipe."),
                  ("Arbre fonctionnel", "La fonction primaire, puis les secondaires et tertiaires (comment ↓, pourquoi ↑)."),
                  ("Structure fonctionnelle", "Le boundary diagram : entrées, fonctions et sorties reliées par des flux."),
                  ("Pièces", "La matrice pièces × fonctions : une pièce qui ne sert aucune fonction est à retirer."),
                  ("Risques projet", "Le registre R-n, probabilité × impact, stratégie, responsable, échéance."),
                  ("DFMEA", "Une ligne par fonction : défaillance, effet, cause, S / O / D, AP, prévention, essai clé, action.")],
        "mvps": ["La fonction primaire et les fonctions de service vues par le client ; les premiers risques projet.",
                 "L'arbre complet et la structure générale ; il guide la matrice morphologique et le CdCF.",
                 "La structure détaillée, les pièces sur les fonctions, le DFMEA avec ses actions suivies dans Agile.",
                 "Le DFMEA mis à jour avec les résultats d'essais ; les risques résiduels pour la décision de lancement."]}, en={
        "role": "The functional analysis: function tree, structure, parts, risks and DFMEA, with their owners.",
        "why": "You design functions before you design parts. Functional analysis forces you to say what the product must do, in which "
               "order and with which flows; the DFMEA then asks how each function can fail and which test will detect it. It is the "
               "deepest part of the mine: where the diamonds are.",
        "need": "Forgetting nothing: every function has its solution, every part serves a function, every risk has its action and "
                "owner, every severe failure mode has its test.",
        "steps": [("Storyline", "The use of the product told scene by scene with pictograms: the team diverges."),
                  ("Function tree", "The primary function, then secondary and tertiary ones (how ↓, why ↑)."),
                  ("Functional structure", "The boundary diagram: inputs, functions and outputs linked by flows."),
                  ("Parts", "The parts × functions matrix: a part that serves no function should go."),
                  ("Project risks", "The R-n register, probability × impact, strategy, owner, due date."),
                  ("DFMEA", "One row per function: failure, effect, cause, S / O / D, AP, prevention, key test, action.")],
        "mvps": ["The primary function and the service functions seen by the customer; the first project risks.",
                 "The full tree and the general structure; it drives the morphological chart and the CdCF.",
                 "The detailed structure, parts on functions, the DFMEA with its actions followed in Agile.",
                 "The DFMEA updated with test results; residual risks for the launch decision."]}, parts=[
        _part("Storyline", ["nng_storyboard", "ixdf_storyboard", "ideo"],
              fr="Qui, où, avec quoi, ce qui se passe et ce qu'on ressent, scène par scène ; un assistant IA s'en sert pour proposer l'arbre.",
              en="Who, where, with what, what happens and how it feels, scene by scene; an AI assistant uses it to propose the tree."),
        _part("Arbre fonctionnel", ["bordeaux", "eduscol", "save_fast", "toulouse", "nf16271", "fips183", "en17952", "en12973", "en1325"],
              fr="Primaire, secondaires, tertiaires et techniques ; comment · pourquoi · quand ; chemin critique ; numéros F gardés pour toujours.",
              en="Primary, secondary, tertiary and technical functions; how · why · when; critical path; F numbers kept for ever."),
        _part("Structure fonctionnelle", ["pahl", "nist_basis", "sys2win", "ulrich", "ptc_boundary", "ptc_pdiagram"],
              fr="Boundary diagram : entrées à gauche, fonctions au centre, sorties à droite ; flux d'énergie, de matière et d'information.",
              en="Boundary diagram: inputs on the left, functions in the middle, outputs on the right; energy, material and information flows."),
        _part("Risques projet", ["watt_risk", "iso31000", "csu_risk", "pmi_risk"],
              fr="Registre R-n, P × I sur 5 × 5, carte maintenant / résiduelle, stratégie, responsable, lien vers le DFMEA.",
              en="R-n register, P × I on 5 × 5, now / residual map, strategy, owner, link to the DFMEA."),
        _part("DFMEA", ["aiag", "carlson", "omnex", "levinson", "q1_fmea", "asq_fmea"],
              fr="Selon AIAG-VDA : S / O / D, Action Priority plutôt que RPN, prévention, essai clé de la Test Base en détection.",
              en="Per AIAG-VDA: S / O / D, Action Priority rather than RPN, prevention, key test of the Test Base as detection."),
        _part("Golden Nuggets", ["fs_first", "rebels", "wevolver", "fs_musk", "isaacson"],
              fr="Premiers principes et l'algorithme en 5 étapes : questionner chaque requirement, supprimer, simplifier, accélérer, automatiser.",
              en="First principles and the 5-step algorithm: question every requirement, delete, simplify, accelerate, automate."),
    ]),
]
