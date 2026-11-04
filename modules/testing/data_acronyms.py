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
        ("MIP", "Mémoire d'identification de projet (Project Identification Report)", "Mémoire d'identification de projet"),
        ("PDP", "Processus de développement de produit (Product Development Process)", "Processus de développement de produit"),
        ("RC", "Rapport de conception (Design Report)", "Rapport de conception"),
        ("RCS", "Rapport de conception système (System Design Report)", "Rapport de conception système"),
        ("RVE", "Rapport de validation expérimentale (Experimental Validation Report)", "Rapport de validation expérimentale"),
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
