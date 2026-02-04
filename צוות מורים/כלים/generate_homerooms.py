import json
from pathlib import Path

AUTO_START = "<!-- AUTO:START -->"
AUTO_END = "<!-- AUTO:END -->"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _merge_auto_section(existing: str | None, auto_block: str) -> str:
    if not existing:
        return auto_block

    if AUTO_START in existing and AUTO_END in existing:
        before, rest = existing.split(AUTO_START, 1)
        _, after = rest.split(AUTO_END, 1)
        merged = before.rstrip() + "\n" + auto_block + after.lstrip("\n")
        return merged

    manual = existing.strip()
    if not manual:
        return auto_block

    return auto_block + "\n\n---\n\n## הערות ידניות\n\n" + manual + "\n"


def _format_readme(entry: dict) -> str:
    teachers = entry.get("homeroom_teachers") or []
    teachers_line = ", ".join(teachers) if teachers else ""

    grade = entry.get("grade", "")
    homeroom_class = entry.get("homeroom_class", "")
    class_type = entry.get("type", "")

    lines = [
        AUTO_START,
        f"מחנך/ת: {teachers_line}",
        "",
        f"שכבה: {grade}",
        f"כיתת אם: {homeroom_class}",
        f"סוג: {class_type}",
        "",
        "נוצר אוטומטית מתוך: נתונים/כיתות_אם.json",
        AUTO_END,
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    data_path = repo_root / "נתונים" / "כיתות_אם.json"

    data = _read_json(data_path)
    classes = data.get("classes") or []

    index_lines = [
        "# אינדקס כיתות אם",
        "",
        "מקור נתונים: נתונים/כיתות_אם.json",
        "",
    ]

    for entry in classes:
        grade = entry.get("grade")
        homeroom_class = entry.get("homeroom_class")
        if not grade or not homeroom_class:
            continue

        folder_path = repo_root / "כיתות_אם" / grade / homeroom_class
        readme_path = folder_path / "README.md"

        existing = None
        if readme_path.exists():
            existing = readme_path.read_text(encoding="utf-8")

        _write_text(readme_path, _merge_auto_section(existing, _format_readme(entry)))

        class_type = entry.get("type", "")
        teachers = ", ".join(entry.get("homeroom_teachers") or [])
        label = f"{homeroom_class} | {class_type} | {teachers}".strip(" |")
        rel = f"כיתות_אם/{grade}/{homeroom_class}/README.md"
        index_lines.append(f"- [{label}]({rel})")

    _write_text(repo_root / "כיתות_אם" / "INDEX.md", "\n".join(index_lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
