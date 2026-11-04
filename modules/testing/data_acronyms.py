"""Default acronyms of the tool (D-A-037): central list « acronym » of the Testing lists (lists.py), published in the
BDC and inserted in the Word exports of Goldmine and Testing (glossary.py). One entry per acronym; several meanings
are separated by « ; ». Each team adds the acronyms of its product.

Entry: (acronym, expansion, French equivalent or "").
"""

ACRONYMS = {
    "Conception de produit": [
        ("AFNOR", "Association française de normalisation (function ranking: IND, IMP, INT, ACC)", ""),
        ("CdCF", "Cahier des charges fonctionnel (Functional Specification)", "Cahier des charges fonctionnel"),
        ("DFQ", "Déploiement de la fonction qualité (Quality Function Deployment, QFD)", "Déploiement de la fonction qualité"),
        ("ECN", "Engineering Change Notice", "Avis de modification technique"),
        ("FMEA", "Failure Mode and Effects Analysis", "AMDEC"),
        ("IADT", "Inspection, Analysis, Demonstration, Test (verification methods)", "Inspection, analyse, démonstration, essai"),
        ("BML", "Build-Measure-Learn (the Lean Startup loop)", "Construire, mesurer, apprendre"),
        ("CDR", "Critical Design Review", "Revue critique de conception"),
        ("CRV", "Concept Review", "Revue de concept"),
        ("LCV", "Lean Canvas", "Lean Canvas et hypothèses à tester"),
        ("MVP", "Minimum Viable Product", "Produit minimum viable"),
        ("PDP", "Processus de développement de produit (Product Development Process)", "Processus de développement de produit"),
        ("PDR", "Preliminary Design Review", "Revue préliminaire de conception"),
        ("V&V", "Verification and Validation", "Vérification et validation"),
        ("VVR", "Validation Report (verification and validation)", "Rapport de vérification et de validation"),
        ("SAFE", "Sequential Analysis of Functional Elements", "Analyse séquentielle des éléments fonctionnels"),
        ("TBD", "To Be Determined", "À déterminer"),
    ],
    "Conformité grand public": [
        ("CEM", "Compatibilité électromagnétique (EMC)", "Compatibilité électromagnétique"),
        ("CSA", "CSA Group (Canadian Standards Association)", ""),
        ("EMC", "Electromagnetic Compatibility", "Compatibilité électromagnétique"),
        ("ESD", "Electrostatic Discharge", "Décharge électrostatique"),
        ("IEC", "International Electrotechnical Commission", "Commission électrotechnique internationale"),
        ("IP", "Ingress Protection (IEC 60529)", "Indice de protection"),
        ("RoHS", "Restriction of Hazardous Substances", "Restriction des substances dangereuses"),
        ("UL", "UL Solutions (Underwriters Laboratories)", ""),
    ],
}
