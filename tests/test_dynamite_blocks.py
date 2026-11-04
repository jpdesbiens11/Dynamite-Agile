"""Dynamite 0.8.0 blocks (D-B-006): table, text colour, status, table of
contents, sub-pages list -- accepted when well formed, refused with a fix
otherwise. Pure validation, no server.

    python -m unittest tests.test_dynamite_blocks -v
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.errors import ApiError  # noqa: E402
from modules.dynamite import content  # noqa: E402


def text(t, *marks):
    node = {"type": "text", "text": t}
    if marks:
        node["marks"] = list(marks)
    return node


def doc(*blocks):
    return {"type": "doc", "content": list(blocks)}


GOOD = doc(
    {"type": "toc"},
    {"type": "paragraph", "content": [text("Risque "), text("élevé", "bold", {"type": "color", "color": "red"}),
                                      {"type": "status", "text": "EN COURS", "color": "blue"}]},
    {"type": "table", "header": True, "rows": [[[text("Composant")], [text("Tension")]],
                                              [[text("NMC 21700")], [text("3,6 V", "code")]]]},
    {"type": "children"},
)


class BlocksTest(unittest.TestCase):
    def refused(self, body):
        with self.assertRaises(ApiError) as ctx:
            content.validate(body)
        self.assertIn("Correctif", ctx.exception.message)
        return ctx.exception.message

    def test_good_document_round_trips(self):
        self.assertEqual(json.loads(content.validate(GOOD)), GOOD)
        flat = content.plain_text(GOOD)
        self.assertIn("NMC 21700", flat)
        self.assertIn("[EN COURS]", flat)

    def test_unknown_colour_refused(self):
        msg = self.refused(doc({"type": "paragraph", "content": [text("x", {"type": "color", "color": "#f00"})]}))
        self.assertIn("red", msg)

    def test_status_rules(self):
        self.refused(doc({"type": "paragraph", "content": [{"type": "status", "text": "", "color": "blue"}]}))
        self.refused(doc({"type": "paragraph", "content": [{"type": "status", "text": "OK", "color": "pink"}]}))

    def test_table_rules(self):
        self.refused(doc({"type": "table", "rows": []}))
        self.refused(doc({"type": "table", "rows": [[]]}))
        self.refused(doc({"type": "table", "rows": [[[{"type": "ticket", "key": "DEMO-1"}]]]}))
        self.refused(doc({"type": "table", "header": "oui", "rows": [[[text("a")]]]}))


if __name__ == "__main__":
    unittest.main()
