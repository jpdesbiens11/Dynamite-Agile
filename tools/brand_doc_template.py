"""Brand the Word template of the exports (0.60.01): your logo in the header, your footer text.

    python tools/brand_doc_template.py --logo mon_logo.png --footer "Équipe 7 — projet de session"

The template modules/testing/templates/document.docx carries the cover page, header / footer, styles and the table of
content of every Word export (Goldmine, Testing, Timesheet); modules/testing/word_doc.py fills its placeholders. This
script swaps only the header picture (a PNG, shown about 1.2 cm wide, square works best) and the footer text,
in place, standard library only. Without --logo, the picture stays; without --footer, the footer stays.
"""
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

TEMPLATE = Path(__file__).resolve().parent.parent / "modules" / "testing" / "templates" / "document.docx"
FOOTER_DEFAULT = "Document généré par Dynamite | Agile. La version électronique fait foi ; la version imprimée est pour référence."


def rebrand(template, logo=None, footer=None, clean_cover=False):
    """Rewrite the template in place. Returns the list of what changed."""
    if logo is not None and logo.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("--logo : un fichier PNG est attendu.")
    changed = []
    tmp = template.with_suffix(".tmp")
    with zipfile.ZipFile(template) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if logo is not None and item.filename == "word/media/image1.png":
                data = logo.read_bytes()
                changed.append("logo")
            elif footer is not None and item.filename == "word/footer1.xml":
                text = data.decode("utf-8")
                texts = list(re.finditer(r"(<w:t(?: [^>]*)?>)([^<]*)(</w:t>)", text))
                for m in reversed(texts):  # the footer becomes one line: the first text run, the others emptied
                    text = text[:m.start(2)] + (escape(footer) if m is texts[0] else "") + text[m.end(2):]
                if texts:
                    data = text.encode("utf-8")
                    changed.append("footer")
            elif clean_cover and item.filename == "word/document.xml":
                text = data.decode("utf-8")
                rows = re.findall(r"<w:tr [^>]*>(?:(?!</w:tr>).)*</w:tr>", text, flags=re.S)
                for row in rows:  # a sample « Prepared by » row left in the source document
                    if ">Administrateur<" in row:
                        text = text.replace(row, "")
                        changed.append("cover")
                data = text.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(str(tmp), str(template))
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--logo", type=Path, help="PNG picture for the header")
    parser.add_argument("--footer", help="text of the footer (default kept)")
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--clean-cover", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.template.exists():
        print("Gabarit introuvable : {}".format(args.template), file=sys.stderr)
        return 1
    print("Modifié : " + (", ".join(rebrand(args.template, args.logo, args.footer, args.clean_cover)) or "rien"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
