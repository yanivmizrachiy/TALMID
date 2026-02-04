from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _read_students_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def main() -> int:
    team_root = Path(__file__).resolve().parents[1]

    groups = _read_json(team_root / "נתונים" / "הקבצות.json").get("groups") or []

    # Map (grade, group_name) -> list of group entries (may have multiple variants)
    by_grade_group: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for g in groups:
        if g.get("subject") != "מתמטיקה":
            continue
        grade = str(g.get("grade") or "").strip()
        group_name = str(g.get("group_name") or "").strip()
        if not grade or not group_name:
            continue
        by_grade_group[(grade, group_name)].append(g)

    students = _read_students_csv(team_root / "נתונים" / "תלמידים.csv")

    # Target outputs grouped by folder
    out_by_folder: dict[str, list[dict[str, str]]] = defaultdict(list)

    ambiguous: list[str] = []
    missing: list[str] = []

    for s in students:
        full_name = (s.get("full_name") or "").strip()
        grade = (s.get("grade") or "").strip()
        homeroom_class = (s.get("homeroom_class") or "").strip()
        math_group = (s.get("math_group") or "").strip()
        notes = (s.get("notes") or "").strip()

        if not (full_name and grade and math_group):
            continue

        candidates = by_grade_group.get((grade, math_group), [])
        if not candidates:
            missing.append(f"{full_name} | שכבה {grade} | הקבצה {math_group}")
            continue

        if len(candidates) > 1:
            folders = ", ".join(sorted({c.get("folder", "") for c in candidates if c.get("folder")}))
            ambiguous.append(f"{full_name} | שכבה {grade} | הקבצה {math_group} | אפשרויות: {folders}")
            continue

        folder = str(candidates[0].get("folder") or "").strip()
        if not folder:
            missing.append(f"{full_name} | שכבה {grade} | הקבצה {math_group} (חסר folder)")
            continue

        out_by_folder[folder].append(
            {
                "full_name": full_name,
                "homeroom_class": homeroom_class,
                "notes": notes,
                "source": "manual",
            }
        )

    # Write per-group manual roster
    fieldnames = ["full_name", "homeroom_class", "notes", "source"]
    for folder, rows in out_by_folder.items():
        # stable order
        rows = sorted(rows, key=lambda r: (r.get("homeroom_class", ""), r.get("full_name", "")))
        _write_csv(team_root / folder / "תלמידים_ידני.csv", rows, fieldnames)

    # Write a report so it's documented in git
    report_lines: list[str] = []
    report_lines.append("# שילובים/חריגים (תלמידים ידניים)")
    report_lines.append("")
    report_lines.append("קובץ מקור: `נתונים/תלמידים.csv`")
    report_lines.append("התוצר: `הקבצות/**/תלמידים_ידני.csv`")
    report_lines.append("")

    if out_by_folder:
        report_lines.append("## שובצו בהצלחה")
        report_lines.append("")
        for folder in sorted(out_by_folder.keys()):
            report_lines.append(f"- {folder}: {len(out_by_folder[folder])} תלמידים")
        report_lines.append("")

    if ambiguous:
        report_lines.append("## צריך החלטה (הקבצה לא חד-משמעית)")
        report_lines.append("")
        for line in ambiguous:
            report_lines.append(f"- {line}")
        report_lines.append("")

    if missing:
        report_lines.append("## חסר יעד שייכון")
        report_lines.append("")
        for line in missing:
            report_lines.append(f"- {line}")
        report_lines.append("")

    (team_root / "דוחות").mkdir(parents=True, exist_ok=True)
    (team_root / "דוחות" / "שילובים_וחריגים.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Manual assignments written: {sum(len(v) for v in out_by_folder.values())}")
    if ambiguous:
        print(f"Ambiguous manual assignments: {len(ambiguous)}")
    if missing:
        print(f"Missing manual assignments: {len(missing)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
