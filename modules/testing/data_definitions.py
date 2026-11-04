"""Default definitions of the tool (D-A-037), in English (D-B-085) with their French equivalent for the translation
page. Central list « definition » of the Testing lists; published in the BDC and inserted in the Word exports
(glossary.py). Wording is the tool's own; standards are cited by name only, never reproduced. Each team adds the
terms of its product.

Entry: (term, definition, French equivalent, source, standard term, standard definition). The last two are filled
only for a team term that replaces the term of a cited standard (nomenclature table).
"""

CONVENTIONS = (
    "Unless otherwise stated, metric units of the International System of Units (SI) are used. Temperatures are "
    "expressed in degrees Celsius (°C), corresponding to kelvin (K) in the SI base units.",
    "Requirement keywords: « shall » = mandatory, « should » = recommended (objective), « may » = permitted, "
    "« will » = statement of fact or intent.",
)

DEFINITIONS = {
    "Functional Analysis": [
        ("Function", "Action of the product, or of one of its parts, expressed by a verb and a complement, "
         "independent of any concept or technical solution.", "Fonction", "", "", ""),
        ("Service Function", "Function the product delivers to its user: a use function (action verb) or an esteem "
         "function (state verb).", "Fonction de service", "", "", ""),
        ("Constraint Function", "Function imposed by the environment, a standard or the client, limiting the freedom "
         "of design.", "Fonction de contrainte", "", "", ""),
        ("Technical Function", "Function that depends on a concept; kept aside in the design notes.",
         "Fonction technique", "", "", ""),
        ("Functional Tree", "Synthesis of the functions in three levels (primary, secondary, tertiary): « how? » from "
         "left to right, « why? » from right to left.", "Arbre fonctionnel", "", "", ""),
        ("Functional Structure", "Block diagram of the functions with the flows of material, energy and information "
         "between the inputs and the outputs of the product.", "Structure fonctionnelle", "", "", ""),
        ("Functional Specification", "Measurable specification derived from a function, independent of the concept: "
         "definition, level and flexibility.", "Spécification fonctionnelle", "", "", ""),
    ],
}
