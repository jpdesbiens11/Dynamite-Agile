"""0.60.82 (D-O-088): the PNG decoder of the PDF export never unpacks more than the header announces (a 400 KB file
held 400 MB of zeros) and stops at a budget of pixels per document (it decodes in Python, ~1.5 s per million pixels);
a refused image becomes « [image : … — voir l'export Word] », the Word export keeps it as it is.

    python -m unittest tests.test_export_png -v
"""
import struct
import sys
import unittest
import zlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.dynamite import export_pdf  # noqa: E402


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)


def png(w, h, raw, ctype=2):
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def plain(w, h):
    return png(w, h, (b"\x00" + b"\x10\x20\x30" * w) * h)


class PngTest(unittest.TestCase):
    def test_a_real_image_still_decodes(self):
        self.assertEqual(export_pdf.png_to_rgb(plain(4, 3)), (4, 3, 3, b"\x10\x20\x30" * 12))

    def test_bomb_refused(self):
        bomb = png(1, 1, b"\0" * 50_000_000)
        self.assertLess(len(bomb), 100_000)
        self.assertIsNone(export_pdf.png_to_rgb(bomb))

    def test_short_or_broken_data_refused(self):
        self.assertIsNone(export_pdf.png_to_rgb(png(4, 3, b"\x00\x01")))
        broken = plain(4, 3).replace(b"IDAT", b"IDAT\xff\xff", 1)
        self.assertIsNone(export_pdf.png_to_rgb(broken))

    def test_budget_per_document(self):
        budget = [30]
        self.assertIsNotNone(export_pdf.png_to_rgb(plain(4, 5), budget))  # 20 pixels
        self.assertEqual(budget, [10])
        self.assertIsNone(export_pdf.png_to_rgb(plain(4, 5), budget))  # 20 more: over the budget
        self.assertEqual(budget, [10])

    def test_pdf_gives_a_placeholder_once_the_budget_is_spent(self):
        doc = export_pdf.Pdf("pied")
        doc.pixel_budget = [20]
        doc.image(plain(4, 5), "image/png", "premier")
        doc.image(plain(4, 5), "image/png", "second")
        self.assertEqual(len(doc.images), 1)
        text = b"\n".join(doc.ops)  # the PDF writes the note word by word
        self.assertIn(b"(second ) Tj", text)
        self.assertIn(b"(Word]) Tj", text)


if __name__ == "__main__":
    unittest.main()
