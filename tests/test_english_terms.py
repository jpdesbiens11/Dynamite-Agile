"""0.60.109 (D-O-122): the French text the platform ships keeps its sentences in French and its technical terms in English
(D-O-121) -- the DFMEA good practices, Help, Training, the Testing catalogues and the example content (lamp starter, Rover).

    python -m unittest tests.test_english_terms -v
"""
import ast
import json
import re
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.diamond import dfmea_io, dfmea_practices as GP  # noqa: E402
from tools.i18n_missing import literals  # noqa: E402

# French technical nouns that must not come back in shipped content (accent-insensitive start of word)
FRENCH_TERMS = re.compile(r"(?<![\w@-])(capteurs?|batterie|boîtiers?|micrologiciels?|connecteurs?|condensateurs?|fusibles?|"
                          r"dissipateurs?|variateurs?|microrupteurs?|interrupteurs?|chien de garde|détrompage|"
                          r"vernis de tropicalisation|centrales? inertielles?|télémétrie|pare-chocs|châssis|courroies?|"
                          r"multimètres?|chronomètre|emballement thermique|arrêts? d'urgence|bancs? d'essai)(?![\w-])", re.I)
ACRONYMS = re.compile(r"(?<![\w-])(DEL|CEM|MLI)(?![\w-])")
UI_QUOTE = re.compile(r"«[^»]*»")


def _python_strings(path):
    tree = ast.parse(path.read_text("utf-8"))
    docs = {ast.get_docstring(n, clean=False) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value not in docs]


def _json_strings(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            _json_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _json_strings(v, out)
    elif isinstance(obj, str):
        out.append(obj)
    return out


def shipped_texts():
    """(file, text) of the content the platform ships in French."""
    files = [BASE_DIR / "modules/diamond/dfmea_practices.py"]
    files += sorted((BASE_DIR / "modules/help").glob("*.py")) + sorted((BASE_DIR / "modules/training").rglob("*.py"))
    files += sorted((BASE_DIR / "tools/rover").glob("*.py"))
    files += [f for f in sorted((BASE_DIR / "modules/testing").glob("data_*.py"))
              if f.name not in ("data_acronyms.py", "data_definitions.py")]  # these keep the French equivalent on purpose
    for f in files:
        for text in _python_strings(f):
            yield f, text
    for f in sorted((BASE_DIR / "static/js/help").glob("*.js")):
        for text in literals(f.read_text("utf-8")):
            yield f, text
    for f in sorted((BASE_DIR / "deploy/starter_exemples").glob("*.json")) + [BASE_DIR / "deploy/spaces_exemples/rover.json"]:
        for text in _json_strings(json.loads(f.read_text("utf-8")), []):
            yield f, text


class EnglishTermsTest(unittest.TestCase):
    def test_01_good_practices_in_english(self):
        block = GP.block(list(GP.THEMES), ("bought", "standard"))
        self.assertTrue(block.startswith(GP.MARK))
        self.assertIsNone(FRENCH_TERMS.search(block), block)
        self.assertIsNone(ACRONYMS.search(block))
        for word in ("Watchdog", "poka-yoke", "Conformal coating", "End-of-line test", "Derating", "heat", "connector"):
            self.assertIn(word.lower(), block.lower())

    def test_02_stored_rows_keep_their_text(self):
        """The marker never changes: a row written before 0.60.109 is still split, never given a second block."""
        self.assertEqual(GP.MARK, "Bonnes pratiques (industrie) :")
        stored = "Rampe de démarrage\nBonnes pratiques (industrie) :\nThermique :\n• Bilan thermique calculé ou simulé"
        team, practices = dfmea_io.split_practices(stored)
        self.assertEqual(team, "Rampe de démarrage")
        self.assertTrue(practices.startswith(GP.MARK))
        self.assertEqual(GP.RAS, "Rien à signaler (RAS)")

    def test_03_no_french_technical_term_left(self):
        hits = []
        for f, text in shipped_texts():
            if re.fullmatch(r"[a-zà-ÿ]+", text):
                continue  # a stem of the matching, an icon key or a code, never shown as such
            bare = UI_QUOTE.sub("", text)  # a quoted screen label follows the screen
            m = FRENCH_TERMS.search(bare) or ACRONYMS.search(bare)
            if m:
                hits.append("{}: {} … {}".format(f.relative_to(BASE_DIR), m.group(0), bare[max(0, m.start() - 30):m.end() + 30]))
        self.assertEqual(hits, [], "\n".join(hits[:40]))

    def test_04_english_display_follows(self):
        en, demo = {}, {}
        for n in range(1, 7):
            en.update(json.loads((BASE_DIR / "static/i18n/en_{}.json".format(n)).read_text("utf-8")))
            demo.update(json.loads((BASE_DIR / "static/i18n/demo_en_{}.json".format(n)).read_text("utf-8")))
        for theme in GP.THEMES.values():
            for practice in theme["practices"]:
                self.assertIn(practice, en)
        for text in GP.GENERAL + list(GP.PART_KINDS.values()):
            self.assertIn(text, en)
        for theme in GP.THEMES.values():  # the labels are the English names of the Testing subjects
            self.assertRegex(theme["label"], r"^[A-Z][A-Za-z ,]+$")
        # the former French text stays translated: rows stored before 0.60.109 keep it
        self.assertIn("Chien de garde (watchdog) et état sûr défini au démarrage, en défaut et à la perte d'alimentation", en)
        self.assertIn("Watchdog et emergency stop", demo)  # the Rover (demo dictionary)


if __name__ == "__main__":
    unittest.main()
