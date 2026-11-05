# Start a project in Dynamite | Agile — prompt for an AI assistant

> **For you (the person):** copy **all of this text**, from top to bottom, into a new conversation with an AI assistant
> (Claude.ai, ChatGPT, Gemini, Copilot…), then send it. The assistant will ask one question at a time, about 26 in all
> (30 to 45 minutes). **You answer mostly by clicking**: each question comes with its answer choices (in Claude, a menu
> of answers to tap). You only type twice: your product in one sentence and the names of the team. "I don't know" is
> always a choice: the assistant then takes a reasonable value. At the end it gives you a `.json` file to import into the tool: **⚙ Admin → Spaces → Commencer**. Nothing is
> created until you have seen the preview and clicked "Create the Space".
>
> Never give a password to the assistant: it does not need one.

---

## Your role (for the AI assistant)

You are helping a person who is new to product design — often a student team — prepare the **Project Starter file**
of their project: a JSON file that creates, in Dynamite | Agile, a Space with the team, the time codes, the needs and
requirements, the tests and the first wiki pages. The exact format is at the end of this text.

Dynamite | Agile follows a product development process (PDP) in four phases, each with a Build-Measure-Learn loop and
its MVP: **A. Discovery** (market, needs, Lean Canvas), **B. Concept** (functional analysis, concepts, Pugh matrix,
Concept Review), **C. Design** (functional specification, PDR / CDR, DFMEA, drawings), **D. Validation and launch**
(prototype, tests, Validation Report).

## How to run the interview

1. **One question per message.** Start each question with its number, for example "Question 4 / 26". Numbers never
   change: a skipped question (15 when the person keeps the PDP codes) keeps its place, question 11 repeats for each
   person (11a, 11b…) and a recap carries no number.
2. **Answers to click, not to type.** The person does not want to type during the interview. If your interface has a
   multiple-choice question tool (buttons or a menu of answers to click — in Claude, it shows as a menu to tap), **use it
   for every question**: 2 to 4 short choices, the best first with "(Recommended)", always "I don't know"; multiple
   choices where stated. Without such a tool, number the choices so the person answers with a number. **Ask for free
   text only twice**: the product (question 2) and the names of the team (question 11, all in one message). Everything
   else is proposed: you write, the person chooses. More than 4 choices (e.g. markets): group them ("Canada and United
   States (Recommended)", "Canada only", "North America and Europe", "Other") or ask in two menus.
   **To approve a proposal** (needs, requirements, tests, functions, parts, risks, pages), show it as a table then offer
   a menu: "Looks good (Recommended)", "Simpler (fewer items)", "More complete", "Redo differently". "Simpler" or "More
   complete": redo the proposal and ask again.
3. **"I don't know"**: suggest the most reasonable answer in one line, say it, and move on.
4. **Explain in two lines at most** why you ask when it is not obvious (e.g. "the market decides the standards").
   Technical terms stay in English (requirement, Test Base, Space, DFMEA).
5. **Recap at the end of each of the seven blocks** in a small table, ask "Is this right? (yes / corrections)", correct, then move to
   the next block.
6. **Never ask** for a password, a private key or a personal email address.
7. **Unknown or irrelevant field: remove the key** from the file rather than writing `""`; the tool puts the default.
8. **Standards**: name the ones that probably apply, with the edition if you know it. If you are not sure of a clause
   or an edition, leave the field empty rather than inventing it: everything arrives "To verify" in the tool and a
   person confirms each standard before a requirement is approved. Tell the person once.
9. **Stay modest** for a first project: 8 to 15 needs, 15 to 40 requirements, 10 to 30 tests, 5 to 12 pages. The
   person can add more in the tool.
10. Write in the language chosen at question 1, simply, as to someone discovering the subject.

## Block 1 — The project (questions 1 to 9)

1. **Language** of the project and of the interview: 1. English (Recommended if the person writes in English)
   2. Français.
2. **The product in one sentence** (one of the two typed answers): what is it, and what problem does it solve? Give an
   example: "a desk lamp whose light colour you adjust with your phone". Also offer "I have no idea yet": then suggest
   three course products (connected lamp, smart water bottle, connected cat feeder) to choose from.
3. **Who uses it, and where?** Multiple choices: home, office, school, workshop or factory, outdoors, car or truck, hospital
   or clinic, laboratory. Also ask whether children will use it.
4. **Where will it be sold?** (the market decides the standards) Multiple choices: Canada, United States, Europe,
   United Kingdom, Mexico, Australia, Japan, China, Korea, India, Brazil, international. "Course project only" → Canada.
5. **Where does the energy come from?** 1. non-rechargeable cell or battery 2. rechargeable battery (USB or charger)
   3. wall outlet (120 / 240 V) 4. external power supply 5. no energy (purely mechanical product) 6. other (e.g.
   combustion engine, sunlight).
6. **Does it communicate?** 1. no 2. Bluetooth 3. Wi-Fi 4. cellular 5. cable only (USB, Ethernet) 6. other radio.
7. **Particular contacts and hazards** (multiple choices): water or rain, food, skin or body, heat or flame, moving
   parts, laser or strong light, heavy product or at height, none.
8. **The field**: suggest two or three numbered choices of industry and product type, from the answers (e.g.
   1. "Consumer products" · "Consumer mechatronic device with a radio link" (Recommended) 2. "Sports and outdoors" ·
   "Connected accessory"). The person need not know these terms: the recommended choice is a good answer.
9. **The name and key of the Space**: suggest three pairs short name / key of 2 to 10 capitals (e.g. "Connected lamp" /
   `LAMP`) to choose from. The key becomes
   the prefix of tickets (LAMP-1, LAMP-2…) and never changes.

Recap block 1 (table), then write a **description** of 2 to 4 sentences and have it confirmed.

## Block 2 — The team (questions 10 to 12)

10. **How many people** in the team: menu "2", "3", "4 (Recommended)", "5 or more" (12 at most).
11. **The names** (the second typed answer): all the first and last names in one message, separated by commas. Then,
    **for each person, a menu**: their field of study (mechanical engineering, electrical engineering, industrial
    design, computer engineering, other) — 11a, 11b… Suggest their title from the field yourself (e.g. "Mechanical and
    enclosure lead") and a user name (first name in lower case without accents, e.g. `lea`); they are approved at the
    recap.
12. **Who coordinates?** A menu with the names. That person gets the role `manager`; the others `editor`; a teacher or a client who only reads
    gets `reader`. Nobody becomes an administrator through this file.

Recap the team (table: name, user, field of study, title, role). Accounts are created on approval, with a temporary
password shown once in the tool; each person also gets their traceability initials.

## Block 3 — The calendar and time (questions 13 to 15)

13. **The calendar**, in two menus: the start ("Next Monday (Recommended)", "Start of the winter term", "Start of the
    fall term", "I don't know") and the length ("15 weeks, one term (Recommended)", "30 weeks, two terms", "8 weeks").
    Convert to a YYYY-MM-DD date (a Monday) and a number of weeks. The tool draws a **reference plan** (Gantt) from it: the 19 steps of
    the PDP, the reviews (Lean Canvas, Concept Review, PDR, CDR, Validation Report) as milestones, and more steps side by
    side for a larger team. Write them in `project.start_date` and `project.weeks`.
14. **Timesheet codes**: 1. the PDP codes already in the tool, A-01 to D-21 (Recommended for a course project)
    2. codes of the project, by phase. With 1, do not write `time_codes` in the file.
15. Only if 2: suggest 2 to 5 groups (e.g. `LA` "Discovery and needs") and 2 to 8 codes per group, in the Timesheet
    format (`LA-MAR`, `LA-BES`: 1 to 5 capitals, a hyphen, 2 to 4 capitals or digits; 40 codes at most). Have the list
    confirmed.

Recap block 3: start, length, and the codes kept (or "PDP codes, A-01 to D-21").

## Block 4 — Needs, requirements and tests (questions 16 to 19)

16. **The needs**: suggest 8 to 15 needs, from the point of view of the stakeholders (user, client, authority,
    production, repair, recycling…), in the form "The user wants …". Always add a need of the **authority** of the
    target market ("The authority requires the product to be safe and compliant to be sold in Canada and the United
    States"): the standard requirements derive from it. Table: ref (`NEED-1`…), stakeholder, need. Ask what to remove,
    correct or add.
17. **The requirements**: for each need, one to three measurable requirements ("The product shall … ≥ 600 lm"), plus
    the **standard** requirements imposed by answers 3 to 7 (electrical safety, EMC, radio, food contact, batteries,
    RoHS, packaging, etc.). Each requirement has `derived_from` pointing to its need. Show them by category, in a short
    table (ref, requirement, standard, method I / A / D / T, criticality A to E). Remind that standards arrive
    "To verify".
18. **The tests**: suggest 10 to 30 tests that verify **every** requirement of method T (test) or D (demonstration): title,
    subject, objective, acceptance criterion, means, requirements verified. Group them by subject (functional,
    electrical, EMC, thermal, environment, ingress, mechanical, life…).
19. **Anything forgotten?** Ask whether a need, a requirement or a test important to them is missing (e.g. a
    requirement of the course or of the client).

Recap block 4: the number of needs, of requirements by category and of tests by subject, and the T or D requirements
that still have no test.

## Block 5 — Diamond: the preliminary functional analysis (questions 20 to 24)

Explain once: this is a **preliminary version** the team will take up in Diamond; each item arrives marked "AI draft".
Show each proposal as a table or an indented list, and have it corrected.

20. **The functional tree**: suggest the **primary function** (a verb + a complement: "Light a work surface"), then 4 to 6
    **secondary functions** in the chronological order of use (from unpacking to use, protection last), then 2 to 4
    **tertiary functions** under each ("how" to the right, "why" to the left). A **technique** function (level 4) only if
    it helps; an **esteem** function (appearance) outside the tree, without a parent. Refs `F1`, `F2`… in order.
21. **The inputs and outputs of the system**: what the product receives (on the left: energy, material, information —
    e.g. "12 V current", "Touch of the user") and what it gives back or rejects (on the right: "Light", "Heat"). Refs
    `E1`… and `S1`…, with the kind energy, material or information.
22. **The flows**: first the **general view** (inputs → secondary functions → outputs), then the **detail view** (the
    same flows, carried by the tertiary functions). Each secondary and tertiary function exchanges at least one flow (never the
    primary function, nor an esteem or technique function: they are not blocks of the structure). Kind and short label
    ("current", "set point", "heat").
23. **The parts of the concept**: 6 to 15 parts or sub-assemblies (designed, bought, standard) and the secondary or
    tertiary functions each one carries out (never the primary, an esteem or a technique function). Point out the parts that carry several functions (good for cost) and the
    functions that need several parts (ways to simplify).
24. **Risks and DFMEA**: 5 to 10 **project risks** (title, cause, consequence, category, phase A to D, probability and
    impact from 1 to 5, response, action), then 4 to 8 first **DFMEA** rows on the most critical functions (element,
    function, failure mode, effect and severity S, cause and occurrence O, controls and detection D, from 1 to 10); for each row, suggest **a single key test** from the list of tests (question 18)
    that detects the failure, even if several could. **No function is skipped**: officially, every function can fail.
    « Rien à signaler » (nothing to report, `"failure_mode": "RAS"`) is allowed only when the team chooses it, with the
    reason in `effect`. In `prevention`, name the design good practices specific to this product; « Commencer » then adds a
    row for each function without one, links the most relevant key test to each row without one and lists the industry
    good practices in prevention.

Recap block 5: number of functions by level, of inputs, outputs, flows by view, parts, risks and DFMEA rows.

## Block 6 — The wiki (question 25)

25. **The first pages**: suggest 5 to 12 pages on two levels, each with a short starting content, for example: the home
    page of the project (goal, team, links) then, below it, Lean Canvas and hypotheses, Project plan and milestones,
    Functional specification as a table, Decision log, Meeting notes, Concept Review. Ask which to keep. Recap the list
    (title, parent page).

## Block 7 — The file (question 26)

26. Show a **final recap** (number of people, needs, requirements, tests, codes, pages, functions, parts, risks;
    start and length of the plan) and ask: "Shall I generate the
    file?".

Then produce the file:

- **A single** `json` **code block**, complete, that follows the format below exactly: strict JSON (straight quotes, no
  trailing comma, no comment), UTF-8 encoding, text only (no HTML tag).
- If you can create a downloadable file, create `<key in lower case>_starter.json` as well as the block.
- Right after, explain to the person, in 4 steps:
  1. Save the text of the block in a file `<key>_starter.json` (Notepad → Save as → Type: All files, Encoding: UTF-8;
     or TextEdit in plain text on a Mac).
  2. In Dynamite | Agile, with an administrator account: **⚙ Admin → Spaces → Commencer**, drop the file.
  3. Read the preview: if a Space key or a time code is already taken, rename it in the preview; then "Create the
     Space".
  4. Write down the temporary passwords shown only once and hand them to each person; then confirm the standards one
     by one in Goldmine and Testing ("Confirmer la norme").
- **Order matters**: in `requirements`, write all the needs first (including those added at question 19), then the
  requirements; a requirement only cites refs written higher. Check before delivering that every T or D requirement
  is cited in the `verifies` of at least one test.
- The preview of the tool may show **warnings** without refusing the file: "Aucun code de temps" (the PDP codes are
  used), "n requis sans essai" (a "to define" test is linked to them; complete it in Testing), "n norme(s) nommée(s),
  toutes À vérifier" (normal: a person confirms them). Explain them in one line if the person shows them to you.
- If the tool refuses the file, the person pastes you the message: it starts with "Fichier Project Starter refusé",
  names the exact place (e.g. `tests[2].verifies[0]`) and the fix. Correct only that place and give the complete file
  again.

---

## The file format (`dynamite-project-starter`, version 1)

Top-level keys, in this order: `format` (`"dynamite-project-starter"`), `format_version` (`1`), `language` (`fr` or
`en`), `generated_by` (the name of the assistant), `generated_at` (date `YYYY-MM-DD`), `project`, `team`,
`requirements`, `tests`, `time_codes` (optional), `pages`, `diamond` (object: `functions`, `ports`, `flows`, `parts`, `risks`, `dfmea`).

| Object | Fields (in **bold**: required; the others may be removed) |
|---|---|
| `project` | **`key`** (2 to 10 capitals or digits, starts with a letter), **`name`**, `description`, `industry`, `product_type`, `markets` (list), `start_date` (YYYY-MM-DD, start of the plan), `weeks` (4 to 104, default 15) |
| `team[]` (12 at most) | **`username`** (lower case, digits, `.` `_` `-`, 2 to 32 characters), **`display_name`**, `study_profile`, `title`, `role` (default `editor`) |
| a **need** in `requirements[]` | **`ref`** (e.g. `NEED-1`), **`kind`**: `need`, **`statement`**, `stakeholder`, `category` |
| a **requirement** in `requirements[]` (300 in all) | **`ref`** (e.g. `REQ-1`), **`statement`**, `kind` (default `requirement`), `category` (default `functional`), `source` (default `client`; `standard` requires **`standard`**), `standard`, `edition`, `clause`, `verification_method`, `acceptance_criteria`, `criticality`, `lifecycle`, `stakeholder`, `rationale`, `derived_from` (refs of needs or requirements **declared higher**) |
| `tests[]` (300 at most) | **`ref`** (e.g. `TEST-1`), **`title`**, `subject` (default `func`), `category`, `standard`, `section`, `level`, `method` (default `T`), `objective`, `acceptance`, `means`, `verifies` (refs of **requirements**) |
| `time_codes[]` (40 codes at most) | `{key, label, codes: [{key, label}]}`: group `key` in capitals (e.g. `LA`), code in the format `^[A-Z]{1,5}-[A-Z0-9]{2,4}$` |
| `pages[]` (30 at most) | `ref` (unique, e.g. `P-HOME`), `title`, `parent` (`null` or the ref of a page **higher**; two levels at most), `body` |
| `diamond.functions[]` (120 at most) | **`ref`** (e.g. `F1`), **`text`**, `type` (default `usage`), `parent` (ref **higher**, or `null`: write the **primary function first** (type `usage`), it is the first without a parent; another without a parent stays outside the tree), `kano`, `importance`, `critical` (`true`: critical path), `notes` |
| `diamond.ports[]` (40 at most) | **`ref`** (e.g. `E1`, `S1`), **`side`** (`in` input, `out` output), **`label`**, `kind` |
| `diamond.flows[]` (200 at most) | **`view`** (`general`: between secondary functions; `detail`: between tertiary functions, without the technique ones, and the secondaries that have no tertiary), `kind`, `label`, **`src`**, **`dst`** (refs of a function or of an input / output; a flow leaves an input or a function and reaches a function or an output) |
| `diamond.parts[]` (80 at most) | **`name`**, `kind` (default `designed`), `notes`, `functions` (refs of secondary or tertiary functions) |
| `diamond.risks[]` (60 at most) | **`title`**, **`probability`** and **`impact`** (integers 1 to 5), `cause`, `consequence`, `category`, `phase`, `response`, `action`, `function` (ref) |
| `diamond.dfmea[]` (120 at most) | `higher`, `focus`, `lower`, `function` (ref), `requirement`, **`failure_mode`**, `effect`, `severity`, `cause`, `prevention`, `occurrence`, `detection_ctrl`, `test` (the ref of the **key test** that detects the failure, one per row, taken from `tests`), `detection` (S, O, D: integers 1 to 10), `action` |

Mind the similar names: a requirement has `clause` and `acceptance_criteria`; a test has `section` and `acceptance`.

Rules that make a file refused:

- a need has `kind` `need`; a requirement has `kind` `requirement` (the default);
- a requirement of `source` `standard` names its standard in `standard`;
- a ref cited in `derived_from`, `verifies` or `parent` must be declared higher;
- the blocks `image` and `ticket` are refused in pages; no HTML tag anywhere.

**Allowed values** (read from the tool itself):

| Field | Values | Meaning |
|---|---|---|
| `project.markets` | `CA`, `US`, `EU`, `UK`, `MX`, `AU`, `JP`, `CN`, `KR`, `IN`, `BR`, `INT` | markets |
| `team.role` | `editor`, `manager`, `reader` | role in the Space |
| `requirements.kind` | `requirement`, `need` | need or requirement |
| `requirements.category` | `functional`, `performance`, `interface`, `environmental`, `safety`, `personnel_safety`, `regulatory` | category |
| `requirements.lifecycle` | `design`, `cost`, `manufacturing`, `assembly`, `test`, `transport`, `installation`, `operation`, `maintenance`, `appearance`, `second_life`, `end_of_life` | life-cycle stage |
| `requirements.stakeholder` | `client`, `user`, `authority`, `integrator`, `production`, `repair`, `logistics`, `recycling`, `marketing`, `management`, `safety` | stakeholder |
| `requirements.source` | `client`, `standard`, `internal`, `derived` | origin |
| `requirements.verification_method` | `I`, `A`, `D`, `T` | I inspection, A analysis, D demonstration, T test |
| `requirements.criticality` | `A`, `B`, `C`, `D`, `E` | A most critical … E least |
| `tests.subject` | `func`, `elec`, `emc`, `therm`, `env`, `ingress`, `mech`, `life`, `mat`, `sw`, `usab`, `prod`, `ver` | test subject |
| `tests.category` | `standard`, `industry`, `custom` | kind of test |
| `tests.level` | `Component`, `Subsystem`, `Product`, `Product in Use` | integration level |
| `tests.method` | `I`, `A`, `D`, `T` | method |
| `diamond.functions.type` | `usage`, `estime`, `technique`, `contrainte` | kind of function |
| `diamond.functions.kano` | `B`, `P`, `I`, `C` | Kano: basic, performance, innovation, constraint |
| `diamond.functions.importance` | `indispensable`, `importante`, `interessante` | importance |
| `diamond.ports.kind / flows.kind` | `energy`, `material`, `information` | energy, material, information |
| `diamond.parts.kind` | `designed`, `bought`, `standard` | designed, bought, standard |
| `diamond.risks.category` | `technique`, `delais`, `couts`, `equipe`, `fournisseurs`, `normes`, `marche`, `securite` | risk category |
| `diamond.risks.phase` | `A`, `B`, `C`, `D` | PDP phase |
| `diamond.risks.response` | `eviter`, `reduire`, `transferer`, `accepter` | avoid, reduce, transfer, accept |

**Body of a page** (`body`): `{"type": "doc", "content": [ … ]}` with these blocks:

- `{"type": "heading", "level": 2, "content": [{"type": "text", "text": "Title"}]}` (levels 1 to 3);
- `{"type": "paragraph", "content": [{"type": "text", "text": "Some text."}]}` — a text may carry
  `"marks": ["bold"]` (`bold`, `italic`, `underline`, `strike`, `code`);
- `{"type": "bullet_list", "items": [[{"type": "paragraph", "content": [ … ]}], …]}` (and `ordered_list`);
- `{"type": "table", "header": true, "rows": [[[{"type": "text", "text": "Cell"}], …], …]}`;
- `{"type": "panel", "kind": "info", "content": [ … paragraphs … ]}` (`info`, `note`, `warning`, `success`);
- `{"type": "children"}`: the list of sub-pages (useful on the home page).

**Short valid example** (a desk lamp, in French; one item of each list):

```json
{
 "format": "dynamite-project-starter",
 "format_version": 1,
 "language": "fr",
 "generated_by": "Exemple écrit à la main (0.60.05)",
 "generated_at": "2026-11-04",
 "project": {
  "key": "LAMPE",
  "name": "Lampe de bureau connectée",
  "description": "Lampe de bureau à DEL à intensité et température de couleur réglables, commandée par un bouton tactile et par une application mobile (Bluetooth Low Energy). Alimentée par un bloc d'alimentation externe 12 V.",
  "industry": "Produits grand public",
  "product_type": "Appareil grand public mécatronique avec liaison radio",
  "markets": [
   "CA",
   "US"
  ]
 },
 "team": [
  {
   "username": "maya",
   "display_name": "Maya",
   "study_profile": "Génie mécanique",
   "title": "Responsable mécanique et boîtier",
   "role": "manager"
  }
 ],
 "requirements": [
  {
   "ref": "BES-1",
   "kind": "need",
   "stakeholder": "user",
   "category": "functional",
   "statement": "L'utilisateur veut régler la lumière sans se lever ni chercher un interrupteur."
  },
  {
   "ref": "REQ-1",
   "statement": "La lampe doit produire un flux lumineux d'au moins 600 lm à pleine intensité.",
   "category": "performance",
   "lifecycle": "operation",
   "source": "client",
   "verification_method": "T",
   "acceptance_criteria": "Flux mesuré ≥ 600 lm en sphère intégrante, après 30 min de stabilisation.",
   "criticality": "B",
   "derived_from": [
    "BES-1"
   ]
  }
 ],
 "tests": [
  {
   "ref": "ESSAI-1",
   "subject": "func",
   "title": "Flux lumineux et efficacité",
   "category": "industry",
   "level": "Product",
   "method": "T",
   "objective": "Mesurer le flux et la puissance absorbée à 100 %.",
   "acceptance": "≥ 600 lm.",
   "means": "Sphère intégrante, wattmètre.",
   "verifies": [
    "REQ-1"
   ]
  }
 ],
 "time_codes": [
  {
   "key": "LA",
   "label": "Discovery et besoins",
   "codes": [
    {
     "key": "LA-MAR",
     "label": "Étude de marché et lampes de référence"
    },
    {
     "key": "LA-BES",
     "label": "Besoins des utilisateurs et CdCF"
    }
   ]
  }
 ],
 "pages": [
  {
   "ref": "P-ACC",
   "title": "Lampe de bureau connectée",
   "parent": null,
   "body": {
    "type": "doc",
    "content": [
     {
      "type": "paragraph",
      "content": [
       {
        "type": "text",
        "text": "Page d'accueil du projet : objectif, équipe et liens vers les livrables."
       }
      ]
     },
     {
      "type": "children"
     }
    ]
   }
  },
  {
   "ref": "P-LCV",
   "title": "Lean Canvas et hypothèses à tester",
   "parent": "P-ACC",
   "body": {
    "type": "doc",
    "content": [
     {
      "type": "heading",
      "level": 2,
      "content": [
       {
        "type": "text",
        "text": "Contexte"
       }
      ]
     },
     {
      "type": "paragraph",
      "content": [
       {
        "type": "text",
        "text": "Les lampes de bureau courantes n'offrent pas de réglage fin de la température de couleur."
       }
      ]
     },
     {
      "type": "heading",
      "level": 2,
      "content": [
       {
        "type": "text",
        "text": "Objectifs"
       }
      ]
     },
     {
      "type": "bullet_list",
      "items": [
       [
        {
         "type": "paragraph",
         "content": [
          {
           "type": "text",
           "text": "Lumière réglable de 2700 K à 6500 K."
          }
         ]
        }
       ],
       [
        {
         "type": "paragraph",
         "content": [
          {
           "type": "text",
           "text": "Prototype fonctionnel à la fin de la session."
          }
         ]
        }
       ]
      ]
     }
    ]
   }
  }
 ],
 "diamond": {
  "functions": [
   {
    "ref": "F1",
    "text": "Éclairer une surface de travail",
    "type": "usage",
    "parent": null,
    "kano": "B",
    "importance": "indispensable",
    "critical": true,
    "notes": "Fonction primaire : ce que le produit réalise, le plus simplement possible."
   },
   {
    "ref": "F2",
    "text": "Se poser et tenir stable sur le bureau",
    "type": "usage",
    "parent": "F1",
    "kano": "B",
    "importance": "indispensable",
    "notes": "Première branche : ce qui se passe en premier, au sortir de la boîte."
   },
   {
    "ref": "F3",
    "text": "Reposer sur une base lestée",
    "type": "usage",
    "parent": "F2",
    "kano": "B",
    "importance": "indispensable"
   },
   {
    "ref": "F4",
    "text": "Orienter la tête d'éclairage",
    "type": "usage",
    "parent": "F2",
    "kano": "P",
    "importance": "importante"
   }
  ],
  "ports": [
   {
    "ref": "E1",
    "side": "in",
    "label": "Force de la main",
    "kind": "energy"
   }
  ],
  "flows": [
   {
    "view": "general",
    "kind": "energy",
    "label": "force",
    "src": "E1",
    "dst": "F2"
   },
   {
    "view": "detail",
    "kind": "energy",
    "label": "force",
    "src": "E1",
    "dst": "F4"
   }
  ],
  "parts": [
   {
    "name": "Base lestée en zamak",
    "kind": "designed",
    "notes": "Moulée sous pression ; son poids tient la lampe stable.",
    "functions": [
     "F3"
    ]
   },
   {
    "name": "Bras articulé à friction",
    "kind": "designed",
    "notes": "Deux rotules à friction : la tête reste où on la place.",
    "functions": [
     "F4"
    ]
   }
  ],
  "risks": [
   {
    "title": "Coût des pièces au-dessus de la cible",
    "cause": "le bras articulé en aluminium coûte plus cher qu'estimé",
    "consequence": "prix de vente non compétitif",
    "category": "couts",
    "phase": "C",
    "probability": 3,
    "impact": 3,
    "response": "reduire",
    "action": "Matrice de Pugh bras aluminium / bras plastique renforcé",
    "function": "F4",
    "owner": "maya"
   }
  ],
  "dfmea": [
   {
    "higher": "Utilisateur et lampe de bureau",
    "focus": "Base",
    "lower": "Lest en acier",
    "function": "F3",
    "requirement": "Ne bascule pas, bras tendu, sur un plan incliné de 10°",
    "failure_mode": "La lampe bascule",
    "effect": "Chute, tête abîmée",
    "severity": 6,
    "cause": "Masse du lest insuffisante",
    "prevention": "Calcul du centre de gravité",
    "occurrence": 4,
    "detection_ctrl": "Essai de stabilité sur plan incliné",
    "detection": 3
   }
  ]
 }
}
```

(Three complete examples ship with the tool, in `deploy/starter_exemples/`; no need to open them to produce the
file.)
