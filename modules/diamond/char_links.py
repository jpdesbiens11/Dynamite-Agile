"""The characteristics C-n of each DFMEA row (0.60.102, D-O-110): what the DFMEA shows in its columns « Part » and
« Characteristic », and what the filter « SC sans caractéristique » reads. Imported by dfmea.py (no import of it here)."""
from . import char_spec as SP


def code(number):
    return "C-{:02d}".format(number)


def part_code(number):
    return "P-{}".format(number) if number else ""


def by_row(conn, pid):
    """{dfmea_id: [characteristic summary]} for the characteristics in service (archived ones are left out)."""
    out = {}
    for r in conn.execute(
            "SELECT c.*, p.number AS part_number, p.name AS part_name, q.number AS part2_number, q.name AS part2_name "
            "FROM diamond_characteristics c LEFT JOIN diamond_parts p ON p.id = c.part_id LEFT JOIN diamond_parts q ON q.id = c.part2_id "
            "WHERE c.project_id = ? AND c.archived = 0 AND c.dfmea_id IS NOT NULL ORDER BY c.number", (pid,)):
        c = dict(r)
        out.setdefault(c["dfmea_id"], []).append({
            "id": c["id"], "code": code(c["number"]), "label": c["label"], "spec": SP.spec(c),
            "part": part_code(c["part_number"]), "part_name": c["part_name"] or "",
            "part2": part_code(c["part2_number"]), "part2_name": c["part2_name"] or ""})
    return out


def attach(conn, pid, rows):
    """Adds `characteristics` (a list, maybe empty) to every DFMEA row."""
    found = by_row(conn, pid)
    for row in rows:
        row["characteristics"] = found.get(row["id"], [])
    return rows
