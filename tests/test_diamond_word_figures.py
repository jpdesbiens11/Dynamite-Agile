"""0.60.98 (D-O-105): the Word report of Diamond carries the visuals of the Space as numbered figures -- the 7 scenes of
the Storyline, the functional tree (overview then one figure per branch, as the PowerPoint), both views of the structure
and the risk map now and residual -- EMF pictures drawn on the server from the layout of draw.io / PowerPoint; the
template, its header / footer, its table of contents and the revision stamp of the core stay.

    python -m unittest tests.test_diamond_word_figures -v
"""
import io
import re
import struct
import sys
import tempfile
import threading
import unittest
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup  # noqa: E402
from core.config import load_config  # noqa: E402
from modules.diamond import emf, export_data as X, export_drawio as D, story, story_figure  # noqa: E402
from modules.diamond import report_figures  # noqa: E402
from modules.diamond.docx_figures import MAX_H, MAX_W, Figures  # noqa: E402
from tools.api_client import Client  # noqa: E402

STOCK = 0x80000000


def records(data):
    """Walk an EMF: [(type, payload)], checking what every reader relies on."""
    kind, size = struct.unpack_from("<II", data, 0)
    assert kind == 1 and size >= 88, "header"
    sig, _ver, total, count, handles = struct.unpack_from("<IIIIH", data, 40)
    assert sig == 0x464D4520, "signature"
    assert total == len(data), "size in the header"
    out, pos = [], 0
    while pos < len(data):
        kind, size = struct.unpack_from("<II", data, pos)
        assert size >= 8 and size % 4 == 0 and pos + size <= len(data), "record at {}".format(pos)
        out.append((kind, data[pos + 8:pos + size]))
        pos += size
    assert len(out) == count, "record count"
    assert out[-1][0] == 14, "ends with EMR_EOF"
    made = [struct.unpack_from("<I", p)[0] for k, p in out if k in (39, 82, 95)]
    used = [struct.unpack_from("<I", p)[0] for k, p in out if k == 37]
    assert all(0 < h < handles for h in made), "handles of the objects"
    assert all(h & STOCK or h in made for h in used), "only created or stock objects are selected"
    return out


def texts(data):
    """The strings of the EMR_EXTTEXTOUTW records."""
    out = []
    for kind, p in records(data):
        if kind == 84:
            n, off = struct.unpack_from("<II", p, 36)
            out.append(p[off - 8:off - 8 + 2 * n].decode("utf-16-le"))
    return out


class WordFiguresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "f.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)  # the DEMO Space, with the complete Rover example inside
        cls.server = router.create_server(cfg, BASE_DIR / "static", data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])
        cls.admin = Client(cls.url)
        cls.admin.login("admin", "admin")
        with db.connect() as conn:
            cls.pid = conn.execute("SELECT id FROM projects WHERE key = 'DEMO'").fetchone()["id"]
            cls.data = X.gather(conn, cls.pid)
        cls.body = cls.get(cls.pid)
        cls.zip = zipfile.ZipFile(io.BytesIO(cls.body))
        cls.doc = cls.zip.read("word/document.xml").decode("utf-8")
        cls.media = sorted((n for n in cls.zip.namelist() if n.startswith("word/media/diamond_fig")),
                           key=lambda n: int(re.sub(r"\D", "", n)))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    @classmethod
    def get(cls, pid):
        with cls.admin.opener.open(urllib.request.Request("{}/api/diamond/p/{}/export.docx".format(cls.url, pid))) as r:
            return r.read()

    def test_01_package_is_whole(self):
        for name in self.zip.namelist():
            if name.endswith(".xml") or name.endswith(".rels"):
                ET.fromstring(self.zip.read(name))  # every part well-formed
        self.assertIn(b'<Default Extension="emf" ContentType="image/x-emf"/>', self.zip.read("[Content_Types].xml"))
        rels = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', self.zip.read("word/_rels/document.xml.rels").decode()))
        embeds = re.findall(r'r:embed="([^"]+)"', self.doc)
        self.assertEqual(len(embeds), len(self.media))
        for rid in embeds:  # every picture points to a relationship and a part of the package
            self.assertIn("word/" + rels[rid], self.zip.namelist())
        ids = re.findall(r'<wp:docPr id="(\d+)"', self.doc)
        self.assertEqual(len(ids), len(set(ids)))

    def test_02_every_figure_is_a_valid_emf(self):
        for name in self.media:
            data = self.zip.read(name)
            kinds = {k for k, _p in records(data)}
            self.assertTrue({84, 3} & kinds or 7 in kinds, name)  # something drawn
            left, top, right, bottom = struct.unpack_from("<iiii", data, 24)  # the frame, 0.01 mm
            self.assertTrue(left == 0 and top == 0 and right > 1000 and bottom > 1000, name)
        for cx, cy in re.findall(r'<wp:extent cx="(\d+)" cy="(\d+)"/>', self.doc):
            self.assertLessEqual(int(cx), MAX_W)
            self.assertLessEqual(int(cy), MAX_H)

    def test_03_numbered_captions(self):
        scenes = self.data["story"]
        self.assertEqual(len(scenes), 7)
        branches = sum(1 for r in self.data["kids"][None] if r["in_tree"] for s in self.data["kids"].get(r["id"], [])
                       if self.data["kids"].get(s["id"]))
        expected = (["Scène {} : {}".format(k, s["title"]) for k, s in enumerate(scenes, 1)] + ["Arbre fonctionnel — vue d'ensemble"]
                    + ["Branche "] * branches + ["Structure fonctionnelle — vue générale", "Structure fonctionnelle — vue détaillée",
                                                 "Carte des risques — maintenant"])  # the Rover has no residual rating yet
        found = re.findall(r'SEQ Figure \\\* ARABIC </w:instrText>.*?<w:t>(\d+)</w:t>.*?<w:t xml:space="preserve"> — ([^<]*)</w:t>',
                           self.doc.replace("&apos;", "'"))
        self.assertEqual([int(n) for n, _t in found], list(range(1, len(expected) + 1)))
        self.assertEqual(len(found), len(self.media))
        for (_n, title), want in zip(found, expected):
            self.assertTrue(title.startswith(want), (title, want))

    def test_04_what_the_figures_show(self):
        pics = [texts(self.zip.read(n)) for n in self.media]
        scene1 = " ".join(pics[0])
        self.assertIn("Sam", scene1)  # the labels of the pictograms
        self.assertIn("Chargée de lab", scene1)
        overview = " ".join(pics[7])
        self.assertIn("F1", overview)
        self.assertTrue(all(code in overview for code in ("F2", "F9", "F36")))
        general, detail, now = (" ".join(p) for p in pics[-3:])
        self.assertIn("Système", general)
        self.assertIn("Entrée · Énergie", general)
        self.assertTrue(re.search(r"\bP-\d+\b", general))  # the part badges of the screen
        self.assertIn("F10", detail)
        self.assertIn("Probabilité →", now)
        self.assertTrue(re.search(r"R-\d+", now))
        self.assertTrue("la carte résiduelle s'ajoutera" in self.doc.replace("&apos;", "'"))

    def test_04b_residual_map_once_rated(self):
        data = dict(self.data, risks=[dict(r) for r in self.data["risks"]])
        data["risks"][0].update(residual_p=1, residual_i=2)
        figs = Figures()
        body = report_figures.risks(data, figs)
        self.assertEqual(figs.count, 2)
        self.assertIn("1 risque(s) sur 10 cotés", body)
        residual = " ".join(texts(figs.media[1][1]))
        self.assertIn("R-{}".format(data["risks"][0]["number"]), residual)
        self.assertNotIn("R-{}".format(data["risks"][1]["number"]), residual)

    def test_05_template_stamp_and_text(self):
        self.assertIn(X.MARK, "".join(self.zip.read(n).decode() for n in self.zip.namelist() if n.startswith("word/footer")))
        self.assertIn("Extrait le", self.zip.read("word/header1.xml").decode())  # the revision stamp of the core
        self.assertIn(b"DA Revision", self.zip.read("docProps/custom.xml"))
        self.assertIn("TOC \\", self.doc)  # the table of contents of the template (F9)
        self.assertIn(">Storyline<", self.doc)
        self.assertIn("exercice de divergence", self.doc)
        for heading in ("Arbre fonctionnel", "Structure fonctionnelle", "Risques projet", "DFMEA"):
            self.assertIn(">{}<".format(heading), self.doc)

    def test_06_branches_at_one_scale(self):
        extents = [int(cx) for cx in re.findall(r'<wp:extent cx="(\d+)"', self.doc)]
        widths = [struct.unpack_from("<i", self.zip.read(n), 32)[0] for n in self.media]  # frame right, 0.01 mm
        ratios = [cx / w for cx, w in zip(extents[8:-3], widths[8:-3])]
        self.assertGreater(len(ratios), 5)
        self.assertLess(max(ratios) / min(ratios), 1.01)

    def test_07_empty_space_has_no_picture(self):
        empty = self.admin.post("/api/admin/projects", {"key": "NUL", "name": "Vide"})["project"]["id"]
        z = zipfile.ZipFile(io.BytesIO(self.get(empty)))
        self.assertFalse([n for n in z.namelist() if n.startswith("word/media/diamond_fig")])
        self.assertIn("la Storyline de ce Space est vide", z.read("word/document.xml").decode())


class PictureTest(unittest.TestCase):
    def test_sprite_has_every_pictogram(self):
        shapes = story_figure.pictos()
        self.assertEqual(set(shapes), set(story.PICTOS))
        for key, parts in shapes.items():
            self.assertTrue(any(kind == "stroke" for kind, *_r in parts), key)

    def test_scene_with_everything(self):
        items = [{"p": key, "x": (i % 8) * 12 + 6, "y": (i // 8) * 20 + 10, "s": 1 + i % 3, "f": i % 2, "t": "É{}".format(i)}
                 for i, key in enumerate(story.PICTOS)]
        data, w, h = story_figure.render({"items": items})
        self.assertEqual((w, h), (960, 540))
        self.assertIn("É3", texts(data))

    def test_damaged_items_are_skipped(self):
        # every write goes through story.clean_items; a restored or edited row may not: the scene loses the item, not the report
        bad = ["texte", None, {"p": ["liste"], "x": 10}, {"p": "adulte", "x": "a"}, {"p": "adulte", "s": "x"},
               {"p": "adulte", "x": float("nan")}, {"p": "inconnu", "x": 50, "y": 50, "t": "Reste"},
               {"p": "adulte", "x": 1e308, "y": -5, "s": 3, "t": "\x07Bord\x00"}]
        data, _w, _h = story_figure.render({"items": bad})
        self.assertEqual(texts(data), ["Reste", "\x07Bord\x00"])  # the label of an unknown pictogram stays; NUL is data in EMF
        self.assertEqual(story_figure.render({"items": "pas une liste"})[1:], (960, 540))

    def test_odd_text_and_numbers(self):
        pic = emf.Picture(200, 100)
        long = "x" * 5000
        pic.text(0, 20, long, 12)
        pic.text(0, 40, "   ", 12)  # nothing to draw
        pic.rect(float("nan"), 0, float("inf"), 10, fill="FFFFFF")
        self.assertEqual(texts(pic.data()), [long])

    def test_dashes_and_text(self):
        parts = emf.dashes([(0, 0), (30, 0), (30, 30)], 7, 5)
        self.assertEqual(len(parts), 5)
        self.assertTrue(all(len(p) >= 2 for p in parts))
        self.assertEqual(emf.dashes([(0, 0), (10, 0)], 0, 5), [[(0, 0), (10, 0)]])  # never an endless loop
        self.assertEqual(emf.dashes([(0, 0), (0, 0), (8, 0)], 4, 2)[0][0], (0, 0))   # a segment of no length
        pic = emf.Picture(100, 50)
        width = pic.text(4, 20, "Être · 𝄞", 12)
        self.assertAlmostEqual(width, emf.measure("Être · 𝄞", 12), delta=0.2)
        self.assertEqual(texts(pic.data()), ["Être · 𝄞"])  # a character beyond the BMP keeps its two UTF-16 units

    def test_drawio_and_pptx_unchanged(self):
        page = D.Page("t")
        page.box(0, 0, 10, 10, "a", "")
        page.role(1, "chrome")
        self.assertNotIn("role", page.xml(1))  # the roles are for the Word figure, not the draw.io file
        self.assertEqual(page.items[0]["role"], "chrome")


if __name__ == "__main__":
    unittest.main()
