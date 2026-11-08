"""0.60.87 (D-O-093): the .xlsx reader (Exploration, Q&R of Goldmine, Timesheet budget lines) padded each row up to the
column of its cells and the sheet up to the number of its rows: a 775-byte file claiming cell « ZZZZZZZ1 » or row
999 999 999 filled the memory of the server. Excel's limits now apply, with a budget of cells per workbook; a cell
« inf » is kept as text instead of a 500.

    python -m unittest tests.test_xlsx_limits -v
"""
import io
import sys
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from modules.exploration import xlsx  # noqa: E402

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def book(sheet_xml):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="{}" xmlns:r="{}"><sheets><sheet name="Plan" sheetId="1" '
                                      'r:id="rId1"/></sheets></workbook>'.format(NS, R))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                   'relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="{}"><sheetData>{}</sheetData></worksheet>'.format(NS, sheet_xml))
    return out.getvalue()


def cell(ref, text):
    return '<c r="{}" t="inlineStr"><is><t>{}</t></is></c>'.format(ref, text)


class XlsxLimitsTest(unittest.TestCase):
    def test_a_normal_sheet(self):
        rows = xlsx.read(book('<row r="1">{}{}</row><row r="3">{}</row>'.format(cell("A1", "Tâche"), cell("C1", "Durée"),
                                                                                  cell("B3", "x"))))["Plan"]
        self.assertEqual(rows, [["Tâche", "", "Durée"], [], ["", "x"]])

    def test_column_beyond_excel_refused(self):
        with self.assertRaises(xlsx.XlsxError) as caught:
            xlsx.read(book('<row r="1">{}</row>'.format(cell("ZZZZZZZ1", "x"))))
        self.assertIn("colonnes d'Excel", str(caught.exception))
        xlsx.read(book('<row r="1">{}</row>'.format(cell("XFD1", "x"))))  # the last column of Excel is fine

    def test_row_beyond_excel_refused(self):
        with self.assertRaises(xlsx.XlsxError) as caught:
            xlsx.read(book('<row r="999999999">{}</row>'.format(cell("A999999999", "x"))))
        self.assertIn("lignes d'Excel", str(caught.exception))

    def test_budget_of_cells(self):
        many = "".join('<row r="{0}">{1}</row>'.format(n, cell("XFD{}".format(n), "x")) for n in range(1, 200))
        with self.assertRaises(xlsx.XlsxError) as caught:
            xlsx.read(book(many))  # 199 rows padded to 16 384 cells: over 2 million
        self.assertIn("cellules", str(caught.exception))

    def test_odd_numbers_kept_as_text(self):
        rows = xlsx.read(book('<row r="1"><c r="A1"><v>inf</v></c><c r="B1"><v>nan</v></c><c r="C1"><v>12</v></c></row>'))["Plan"]
        self.assertEqual(rows, [["inf", "nan", "12"]])


if __name__ == "__main__":
    unittest.main()
