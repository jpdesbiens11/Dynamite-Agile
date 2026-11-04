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
