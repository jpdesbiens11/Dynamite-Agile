"""Writes the academic example « Rover » as a Project Starter file (0.60.46, D-O-055).

    python3 tools/make_rover_example.py   ->   deploy/spaces_exemples/rover.json

The file is not part of the platform: a fresh installation never loads it (D-O-050). The website publishes it on the
installation page (site/spaces/rover.json); a team that wants it downloads it and drops it in ⚙ Admin → Spaces → Commencer.
The file must pass core/starter.parse, like any file an AI assistant prepares.
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from tools.rover import agile, base, diamond, dfmea_more, methods, pages_ab, pages_cd  # noqa: E402

TARGET = BASE / "deploy" / "spaces_exemples" / "rover.json"


def build():
    from core import starter
    return {
        "format": starter.FORMAT, "format_version": starter.FORMAT_VERSION, "language": "fr",
        "generated_by": "DynamiteAgile — exemple académique Rover (tools/make_rover_example.py)", "generated_at": "2026-11-05",
        "project": base.PROJECT, "team": base.TEAM, "requirements": base.NEEDS + base.REQUIREMENTS, "tests": base.TESTS,
        "pages": pages_ab.PAGES_AB + pages_cd.PAGES_CD,
        "diamond": {"functions": diamond.FUNCTIONS, "ports": diamond.PORTS, "flows": diamond.FLOWS, "parts": diamond.PARTS,
                    "risks": diamond.RISKS, "dfmea": diamond.DFMEA + dfmea_more.MORE},
        "backlog": agile.BACKLOG, "deliverables": agile.DELIVERABLES, "tools": methods.TOOLS,
    }


def write():
    from core import starter
    text = json.dumps(build(), ensure_ascii=False, indent=1) + "\n"
    starter.parse(text)  # refused here with the path and the fix, like in « Commencer »
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8")
    return TARGET, len(text)


if __name__ == "__main__":
    path, size = write()
    print("{} ({} Ko)".format(path.relative_to(BASE), size // 1024))
