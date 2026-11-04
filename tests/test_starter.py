"""0.60.05 (D-O-019): the Project Starter file written by an AI assistant, checked by core/starter.py."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import starter  # noqa: E402
from core.errors import ApiError  # noqa: E402

EXAMPLES = sorted((BASE_DIR / "deploy" / "starter_exemples").glob("*.json"))


def minimal():
    return {"format": starter.FORMAT, "format_version": 1, "project": {"key": "DEMO", "name": "Démo"},
            "requirements": [{"ref": "R1", "statement": "Faire une chose.", "source": "standard", "standard": "IEC 62368-1"}],
            "tests": [{"ref": "T1", "title": "Essai", "verifies": ["R1"]}],
            "time_codes": [{"key": "G1", "label": "Groupe", "codes": [{"key": "G1-A", "label": "Code"}]}],
            "pages": [{"ref": "P1", "title": "Accueil", "parent": None,
                       "body": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Bonjour"}]}]}}]}


class StarterTest(unittest.TestCase):
    def refused(self, data, fragment):
        with self.assertRaises(ApiError) as ctx:
            starter.parse(data)
        self.assertIn(fragment, ctx.exception.message)
        self.assertIn("Correctif", ctx.exception.message)

    def test_01_examples_are_accepted(self):
        self.assertEqual(len(EXAMPLES), 3)
        for f in EXAMPLES:
            clean, _ = starter.parse(f.read_bytes())
            self.assertTrue(clean["requirements"] and clean["tests"] and clean["pages"], f.name)

    def test_02_what_the_file_cannot_decide(self):
        data = minimal()
        data["tests"][0]["status"] = "Approved"
        data["requirements"][0]["review"] = "verified"
        clean, warnings = starter.parse(json.dumps(data).encode("utf-8"))
        self.assertEqual(clean["requirements"][0]["review"], "to_verify")
        self.assertEqual((clean["tests"][0]["status"], clean["tests"][0]["review"]), ("Draft", "to_verify"))
        page = clean["pages"][0]
        self.assertTrue(page["ai_draft"])
        self.assertEqual(page["body"]["content"][0]["type"], "panel")
        self.assertIn("Brouillon IA", json.dumps(page["body"], ensure_ascii=False))
        self.assertTrue(any("À vérifier" in w for w in warnings))
        again, _ = starter.parse(clean)                              # the AI-draft panel is not added twice
        self.assertEqual(len(again["pages"][0]["body"]["content"]), len(page["body"]["content"]))

    def test_03_team_never_admin_never_password(self):
        for member in ({"username": "nina", "display_name": "Nina", "role": "admin"},
                       {"username": "nina", "display_name": "Nina", "password": "x"}):
            data = minimal()
            data["team"] = [member]
            self.refused(data, "team[0]")
        data = minimal()
        data["team"] = [{"username": "admin", "display_name": "A"}]
        self.refused(data, "réservé")
        data["team"] = [{"username": "lea", "display_name": "Léa"}, {"username": "lea", "display_name": "Léa B"}]
        self.refused(data, "team[1].username")

    def test_04_links_must_exist(self):
        data = minimal()
        data["tests"][0]["verifies"] = ["R9"]
        self.refused(data, "tests[0].verifies[0]")
        data = minimal()
        data["requirements"].append({"ref": "R2", "statement": "x", "derived_from": ["R3"]})
        self.refused(data, "requirements[1].derived_from[0]")
        data = minimal()
        data["requirements"].append({"ref": "R1", "statement": "doublon"})
        self.refused(data, "déjà utilisée")

    def test_05_two_levels_and_limits(self):
        data = minimal()
        data["time_codes"][0]["codes"][0]["codes"] = [{"key": "X", "label": "x"}]
        self.refused(data, "troisième niveau")
        data = minimal()
        data["time_codes"] = [{"key": "G{}".format(i), "label": "g"} for i in range(41)]
        self.refused(data, "40 au maximum")
        data = minimal()
        data["pages"] += [{"ref": "P2", "title": "a", "parent": "P1"}, {"ref": "P3", "title": "b", "parent": "P2"}]
        self.refused(data, "troisième niveau de pages")

    def test_06_text_only(self):
        data = minimal()
        data["project"]["description"] = "<script>alert(1)</script>"
        self.refused(data, "balise HTML")
        for block in ({"type": "image", "id": 3}, {"type": "ticket", "key": "DEMO-1"}, {"type": "iframe"}):
            data = minimal()
            data["pages"][0]["body"]["content"].append(block)
            self.refused(data, "pages[0].body")

    def test_07_vocabularies_and_format(self):
        data = minimal()
        data["requirements"][0]["category"] = "avionics"
        self.refused(data, "requirements[0].category")
        data = minimal()
        data["requirements"][0]["standard"] = ""
        self.refused(data, "sans norme")
        data = minimal()
        data["project"]["key"] = "demo"
        self.refused(data, "project.key")
        bad = copy.deepcopy(minimal())
        bad["format_version"] = 2
        self.refused(bad, "format_version")
        self.refused(b"{not json", "JSON illisible")
        self.refused({"format": "autre"}, "format")

    def test_08_command_line(self):
        ok = subprocess.run([sys.executable, str(BASE_DIR / "tools" / "check_starter.py"), str(EXAMPLES[0])],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("Fichier accepté", ok.stdout)
        ko = subprocess.run([sys.executable, str(BASE_DIR / "tools" / "check_starter.py"), str(BASE_DIR / "README.md")],
                            capture_output=True, text=True)
        self.assertEqual(ko.returncode, 1)
        self.assertIn("Erreur :", ko.stdout)


if __name__ == "__main__":
    unittest.main()
