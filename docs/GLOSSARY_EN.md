# Technical vocabulary — always in English (D-B-085)

Rule: every technical term of the platform stays in English, also for French-speaking users (translations mean
nothing in our field). Sentences of the interface (help, buttons, messages) stay in French; the technical nouns,
field names, list values, statuses, types, categories and the catalogues provided by the platform are in English.
Full list with definitions and French equivalents: central lists « Acronym » and « Definition » (Testing → Listes), published in the BDC (Definitions, Acronyms, « Traduction des termes techniques (EN → FR) ») and inserted in the Word exports (D-A-037). Example content follows the interface: French sentences, English technical terms (D-A-038).
Stored codes never change (CSV / Excel exports keep working); the import also accepts the former French labels.

## Goldmine (requirements)

| Code / field | English label | Former French label |
|---|---|---|
| kind requirement / need | Requirement / Need | Exigence / Besoin |
| source client / standard / internal / derived | Customer / Standard / Internal / Derived | Client / Norme / Standard / Interne / Dérivée |
| category functional … regulatory | Functional, Performance, Interface, Environmental, Safety, Personnel Safety, Standard / Regulatory | Fonctionnelle, …, Sécurité des personnes, Norme / Standard |
| lifecycle | Design, Cost (DTC), Part Manufacturing (DFM), Assembly (DFA), Test & Verification (DFT), Transport & Storage, Installation & Integration, Operation (Use), Maintenance & Repair, Appearance & Appeal, Second Life, End of Life (Disassembly, Recycling) | Conception, … |
| stakeholder | Customer / Buyer, End User, Standards Body / Regulator, Integrator / Distributor, Production / Assemblers, Maintenance & Repair, Logistics, Recycling / End of Life, Marketing / Sales, Project Management, Health & Safety |
| verification method I A D T | Inspection, Analysis, Demonstration, Test | Inspection, Analyse, Démonstration, Test |
| fields | External ID, Kind, Stakeholder, Derived From, Source, Source Document, Statement, Rationale, Category, Life-Cycle Phase, Criticality, Verification Method, Acceptance Criteria, Allocation, Verification Ref., Test Procedure, Test Source, Functions, Revision, Received Date | ID externe, Nature, … |
| workflow « Requirement Workflow » | Received → In Analysis (↔ Customer Clarification) → Accepted → Allocated → Implemented → In Verification → Verified (or Rejected, Obsolete) | Reçue → En analyse … |
| Q&A status | Open, Answered, Closed, Cancelled | Ouverte, Répondue, Close, Annulée |

## Agile, Change Management, Exploration

| Item | English |
|---|---|
| Standard Workflow | To Do → In Progress → In Review → Done |
| Issue types | Epic, Story, Task, Bug, Sub-task, Requirement, PR, ECN, ECN Task |
| PR / Bug workflow | Open → In Analysis → Derived to ECN → Closed (or Rejected) |
| ECN workflow | Draft → Submitted → CCB Review → Approved → In Implementation → In Verification → Closed (or Rejected, Cancelled) |
| PR / ECN fields | Severity (Critical, Major, Minor), Detected In (Design, Manufacturing, Receiving Inspection, Test / Qualification, In Service, Supplier), Affected Item, Software Version Found, Containment Action, Root Cause, Change Class (Major, Minor), Change Reason, Form / Fit / Function Impact, Certification Impact, Safety Impact, Impact Analysis, Effectivity, CCB Approvers, CCB Decision Date, Implementation Verification Ref. |
| ECN items | Part, Assembly, Drawing, Document / Procedure, Software / Firmware, Tooling; dispositions N/A, Use As Is, Rework, Scrap, Return to Supplier, Use Up Stock |
| Exploration task status | To Do, In Progress, Done, Blocked |

## Testing

| Item | English |
|---|---|
| Subjects | Functional Performance, Electrical Safety, EMC (Emissions & Immunity), Thermal, Environmental, Ingress Protection (IP), Mechanical, Drop & Structural, Durability & Life, Materials & Compliance (RoHS), Electronics & Software, Usability & Ergonomics, Production & End-of-Line, Verification without Test (Inspection, Analysis, Demonstration) |
| Categories | Standard, Industry Practice, Custom Test (TBD) |
| Status | Draft, In Review, Approved, Obsolete |
| Level | Component, Subsystem, Product, Product in Use |
| Fields | Test ID, Title, Subject, Category, Standard, Section, Source, Level, Method, Test Location, Test Equipment, Functions, Objective, Acceptance Criteria, Test Means, Team Notes, Test Procedure |

## Timesheet

| Item | English |
|---|---|
| Week status | Draft, Submitted, Approved, Returned |
| Budget structure | Funding Space (« espace financier »), Budget Line (« poste budgétaire »), Claimable, Active |
| Default code sets | Processus de développement de produit (A-01 … D-21), Temps interne et congés (INT-01 … INT-05, INT-VAC, INT-SAN) |

## Diamond (DFMEA, special characteristics)

| Code / field | English label | Note |
|---|---|---|
| class CC / SC (0.60.101, D-O-108) | Class: CC (Critical Characteristic), SC (Significant Characteristic) | AIAG, IATF 16949 § 8.3.3.3 ; shown with the symbol of the Space's customer (Ford YC / YS in the DFMEA, CC ∇ / SC in process; aerospace CSC / KC) |
| class state proposed / confirmed / refused | « Proposée », « Confirmée », « Refusée » | sentences of the DFMEA (« Confirmée par LEX · date · « reason » »), like the Diamond action statuses |
| CSR | Customer-Specific Requirements | where a customer's symbols and rules come from |
| fields | Function of Focus Element, Requirement / Characteristic, Failure Mode, Failure Effect, Failure Cause, Prevention Controls, Detection Controls, Higher-Level / Focus / Lower-Level Element, Action Priority (AP), RPN | AIAG-VDA |
| characteristic C-n (0.60.102, D-O-110) | Characteristic, nature Product / Process, Specification (nominal ± tolerance, LSL, USL), Cpk req. | « Caractéristique » in sentences; the summary keeps the AIAG column names (Char., Class, Characteristic, Specification, Part, Company PN, DFMEA, PFMEA, Control Plan, Cpk req., Cpk, Status) |
| control of a characteristic | « Étude de capabilité (Cpk) », « Essai 100 % », « Vérifiée en conception » | the status of the summary reads as a sentence (« Étude à faire », « À compléter : plan ») |
| company part number (0.60.103, D-O-112) | PN, BOM (ERP), « # de pièce de l'entreprise » | proposals « sûre », « à choisir », « à créer dans l'ERP », « refusée » |
| PFMEA (0.60.103, D-O-114) | Process Step, Product / Process Characteristic, Failure Mode, Failure Effect, Failure Cause, 5M (Man, Method, Material, Machine, Measurement), Prevention Controls, Detection Controls, S / O / D, AP | AIAG-VDA; code PF-30.1; the 5M read in French in sentences (main-d'œuvre, méthode, matière, machine, mesure); row states « Brouillon », « Validée », « Rejetée » |
| assembly line (0.60.103, D-O-113) | operation OP10, line configuration L1, control point | the tab is « Procédés » in French, « Process » in English |
| Control Plan (0.60.103, D-O-115) | Control Plan, Machine · Jig, Measurement Technique, Sample, Frequency, Control Method, Reaction Plan; phases Prototype, Pre-launch, Production | AIAG; codes PC-2, CP-30.1, CP-R.4 (reception); « Plans de contrôle » in sentences |
| capability (0.60.103, D-O-115) | Cpk (within, σ = MR̄ / 1,128), Ppk (overall), short sample (< 25 values) | statuses « Capable », « Sous l'exigé », « Étude à faire », « Essai 100 % », « À revoir (n) » after an ECN |
| waves (0.60.103, D-O-115) | « Prioriser », « Vague 1 — avant le prototype » | the due date of an action and of its Agile ticket follows its wave |
| AI round trip (0.60.104, D-O-116) | « Exporter (.csv) », « Prompt pour l'IA » (« Entrevue guidée », « Révision », « Générer »), « Importer… », « Appliquer la sélection » | preview kinds « Nouvelle », « Modifiée », « Identique », « Refusée » ; the JSON keys are the CSV headers (English AIAG names) |
| features (0.60.103, D-O-111) | « Modules et fonctions » | ⚙ Admin → Plateforme; Timesheet, Évaluation, objectifs et profil, Procédés, PFMEA, Plans de contrôle |
