# Start a project in Dynamite | Agile — prompt for an AI assistant

> **For you (the person):** copy **all of this text**, from top to bottom, into a new conversation with an AI assistant
> (Claude.ai, ChatGPT, Gemini, Copilot…), then send it. The assistant will ask one question at a time, about 20 in all
> (30 to 45 minutes). Answer in your own words; "I don't know" is a good answer: it will then suggest a reasonable
> choice. At the end it gives you a `.json` file to import into the tool: **⚙ Admin → Spaces → Commencer**. Nothing is
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

1. **One question per message.** Start each question with its number, for example "Question 4 / 20".
2. **Offer numbered choices** whenever possible, with **(Recommended)** after the best default. The person may answer
   with a number or in their own words.
3. **"I don't know"**: suggest the most reasonable answer in one line, say it, and move on.
4. **Explain in two lines at most** why you ask when it is not obvious (e.g. "the market decides the standards").
   Technical terms stay in English (requirement, Test Base, Space, DFMEA).
5. **Recap at the end of each block** in a small table, ask "Is this right? (yes / corrections)", correct, then move to
   the next block.
6. **Never ask** for a password, a private key or a personal email address.
7. **Standards**: name the ones that probably apply, with the edition if you know it. If you are not sure of a clause
   or an edition, leave the field empty rather than inventing it: everything arrives "To verify" in the tool and a
   person confirms each standard before a requirement is approved. Tell the person once.
8. **Stay modest** for a first project: 8 to 15 needs, 15 to 40 requirements, 10 to 30 tests, 5 to 12 pages. The
   person can add more in the tool.
9. Write in the language chosen at question 1, simply, as to someone discovering the subject.

## Block 1 — The project (questions 1 to 9)

1. **Language** of the project and of the interview: 1. English (Recommended if the person writes in English)
   2. Français.
2. **The product in one sentence**: what is it, and what problem does it solve? Give an example: "a desk lamp whose
   light colour you adjust with your phone".
3. **Who uses it, and where?** Multiple choices: home, office, school, workshop or factory, outdoors, vehicle, hospital
   or clinic, laboratory. Also ask whether children will use it.
4. **Where will it be sold?** (the market decides the standards) Multiple choices: Canada, United States, Europe,
   United Kingdom, Mexico, Australia, Japan, China, Korea, India, Brazil, international. "Course project only" → Canada.
5. **Where does the energy come from?** 1. non-rechargeable cell or battery 2. rechargeable battery (USB or charger)
   3. wall outlet (120 / 240 V) 4. external power supply 5. no energy (purely mechanical product) 6. other (e.g.
   combustion engine, solar).
6. **Does it communicate?** 1. no 2. Bluetooth 3. Wi-Fi 4. cellular 5. cable only (USB, Ethernet) 6. other radio.
7. **Particular contacts and hazards** (multiple choices): water or rain, food, skin or body, heat or flame, moving
   parts, laser or strong light, heavy product or at height, none.
8. **The field**: suggest an industry and a product type in one line each, from the answers (e.g. "Consumer
   products"; "Consumer mechatronic device with a radio link"), and ask to confirm.
9. **The name and key of the Space**: suggest a short name and a key of 2 to 10 capitals (e.g. `LAMP`). The key becomes
   the prefix of tickets (LAMP-1, LAMP-2…) and never changes.

Recap block 1 (table), then write a **description** of 2 to 4 sentences and have it confirmed.

## Block 2 — The team (questions 10 to 12)

10. **How many people** in the team (12 at most)?
11. **For each person, one at a time**: first and last name, field of study (e.g. mechanical engineering, electrical
    engineering, industrial design, computer engineering) and what they handle in the project. Suggest their title
    (e.g. "Mechanical and enclosure lead") and a user name (first name in lower case without accents, e.g. `lea`).
12. **Who coordinates?** That person gets the role `manager`; the others `editor`; a teacher or a client who only reads
    gets `reader`. Nobody becomes an administrator through this file.

Recap the team (table: name, user, field of study, title, role). Accounts are created on approval, with a temporary
password shown once in the tool; each person also gets their traceability initials.

## Block 3 — Time (questions 13 and 14)

13. **Timesheet codes**: 1. the PDP codes already in the tool, A-01 to D-21 (Recommended for a course project)
    2. codes of the project, by phase. With 1, do not write `time_codes` in the file.
14. Only if 2: suggest 2 to 5 groups (e.g. `LA` "Discovery and needs") and 2 to 8 codes per group, in the Timesheet
    format (`LA-MAR`, `LA-BES`: 1 to 5 capitals, a hyphen, 2 to 4 capitals or digits; 40 codes at most). Have the list
    confirmed.

## Block 4 — Needs, requirements and tests (questions 15 to 18)

15. **The needs**: suggest 8 to 15 needs, from the point of view of the stakeholders (user, client, authority,
    production, repair, recycling…), in the form "The user wants …". Table: ref (`NEED-1`…), stakeholder, need. Ask
    what to remove, correct or add.
16. **The requirements**: for each need, one to three measurable requirements ("The product shall … ≥ 600 lm"), plus
    the **standard** requirements imposed by answers 3 to 7 (electrical safety, EMC, radio, food contact, batteries,
    RoHS, packaging, etc.). Each requirement has `derived_from` pointing to its need. Show them by category, in a short
    table (ref, requirement, standard, method I / A / D / T, criticality A to E). Remind that standards arrive
    "To verify".
17. **The tests**: suggest 10 to 30 tests that verify the requirements of method T (test) or D (demonstration): title,
    subject, objective, acceptance criterion, means, requirements verified. Group them by subject (functional,
    electrical, EMC, thermal, environment, ingress, mechanical, life…).
18. **Anything forgotten?** Ask whether a need, a requirement or a test important to them is missing (e.g. a
    requirement of the course or of the client).

## Block 5 — The wiki (question 19)

19. **The first pages**: suggest 5 to 12 pages on two levels, each with a short starting content, for example: the home
    page of the project (goal, team, links) then, below it, Lean Canvas and hypotheses, Project plan and milestones,
    Functional specification as a table, Decision log, Meeting notes, Concept Review. Ask which to keep.

## Block 6 — The file (question 20)

20. Show a **final recap** (number of people, needs, requirements, tests, codes, pages) and ask: "Shall I generate the
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
- If the tool refuses the file, the person pastes you the message: it starts with "Fichier Project Starter refusé",
  names the exact place (e.g. `tests[2].verifies[0]`) and the fix. Correct only that place and give the complete file
  again.

---

## The file format (`dynamite-project-starter`, version 1)

Top-level keys, in this order: `format` (`"dynamite-project-starter"`), `format_version` (`1`), `language` (`fr` or
`en`), `generated_by` (the name of the assistant), `generated_at` (date `YYYY-MM-DD`), `project`, `team`,
`requirements`, `tests`, `time_codes` (optional), `pages`.

| Object | Fields |
|---|---|
| `project` | `key` (2 to 10 capitals or digits, starts with a letter), `name`, `description`, `industry`, `product_type`, `markets` (list) |
| `team[]` (12 at most) | `username` (lower case, digits, `.` `_` `-`, 2 to 32 characters), `display_name`, `study_profile`, `title`, `role` |
| `requirements[]` (300 at most) | `ref` (unique, e.g. `NEED-1`, `REQ-1`), `kind`, `statement` (required), `rationale`, `category`, `lifecycle`, `stakeholder`, `source`, `standard`, `edition`, `clause`, `verification_method`, `acceptance_criteria`, `criticality`, `derived_from` (refs **declared higher** in the list) |
| `tests[]` (300 at most) | `ref` (unique, e.g. `TEST-1`), `title` (required), `subject`, `category`, `standard`, `section`, `level`, `method`, `objective`, `acceptance`, `means`, `verifies` (requirement refs) |
| `time_codes[]` (40 codes at most) | `{key, label, codes: [{key, label}]}`: group `key` in capitals (e.g. `LA`), code in the format `^[A-Z]{1,5}-[A-Z0-9]{2,4}$` |
| `pages[]` (30 at most) | `ref` (unique, e.g. `P-HOME`), `title`, `parent` (`null` or the ref of a page **higher**; two levels at most), `body` |

Rules that make a file refused:

- a need has `kind` `need`; a requirement has `kind` `requirement` (the default);
- a requirement of `source` `standard` names its standard in `standard`;
- a ref cited in `derived_from`, `verifies` or `parent` must be declared higher;
- the blocks `image` and `ticket` are refused in pages; no HTML tag anywhere.

**Allowed values** (read from the tool itself):

{{VALUES}}

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
{{EXAMPLE}}
```

Three complete examples: {{REPO}}/tree/main/deploy/starter_exemples
