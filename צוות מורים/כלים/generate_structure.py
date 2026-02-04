import json
import os
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
    teachers = entry.get("teachers") or []
    teachers_line = ", ".join(teachers) if teachers else ""

    grade = entry.get("grade", "")
    subject = entry.get("subject", "")
    group_name = entry.get("group_name", "")
    variant = entry.get("variant")
    class_hint = entry.get("class_hint")

    lines = [AUTO_START, f"מורה מלמד/ת: {teachers_line}", ""]
    if grade:
        lines.append(f"שכבה: {grade}")
    if subject:
        lines.append(f"מקצוע: {subject}")
    if group_name:
        lines.append(f"הקבצה: {group_name}{f' ({variant})' if variant else ''}")
    if class_hint:
        lines.append(f"כיתה קשורה/רמז: {class_hint}")

    lines.append("")
    lines.append("נוצר אוטומטית מתוך: נתונים/הקבצות.json")
    lines.append(AUTO_END)
    return "\n".join(lines) + "\n"


def _safe_filename_part(text: str) -> str:
    cleaned = []
    for ch in str(text or "").strip():
        if ch.isalnum() or ch in ["א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ", "ק", "ר", "ש", "ת"]:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    out = "".join(cleaned)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "file"


def _group_page_filename(entry: dict) -> str:
    grade = _safe_filename_part(entry.get("grade", ""))
    group_name = _safe_filename_part(entry.get("group_name", ""))
    variant = _safe_filename_part(entry.get("variant", "")) if entry.get("variant") else ""
    subject = _safe_filename_part(entry.get("subject", ""))

    parts = [p for p in ["הקבצה", grade, subject, group_name, variant] if p]
    return "_".join(parts) + ".md"


def _format_group_page(entry: dict) -> str:
    teachers = entry.get("teachers") or []
    teachers_line = ", ".join(teachers) if teachers else ""
    grade = entry.get("grade", "")
    subject = entry.get("subject", "")
    group_name = entry.get("group_name", "")
    variant = entry.get("variant")
    class_hint = entry.get("class_hint")

    title = f"הקבצה {group_name}{f' ({variant})' if variant else ''} – שכבה {grade} ({subject})".strip()
    lines = [
        f"# {title}",
        "",
        f"מורה מלמד/ת: {teachers_line}",
    ]
    if class_hint:
        lines.append(f"כיתה קשורה/רמז: {class_hint}")
    lines += [
        "",
        "קבצים בתיקייה זו:",
        "- README.md – סיכום קצר (אוטומטי + הערות ידניות)",
        "- תלמידים_מהאקסל__*.csv – רשימות תלמידים לפי גיליונות האקסל (כל גיליון = קבוצת לימוד נפרדת)",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    data_path = repo_root / "נתונים" / "הקבצות.json"

    data = _read_json(data_path)
    groups = data.get("groups") or []

    index_lines = [
        "# אינדקס הקבצות",
        "",
        "מקור נתונים: נתונים/הקבצות.json",
        ""
    ]

    for entry in groups:
        folder = entry.get("folder")
        if not folder:
            continue

        folder_path = repo_root / folder
        readme_path = folder_path / "README.md"
        existing = None
        if readme_path.exists():
            existing = readme_path.read_text(encoding="utf-8")
        _write_text(readme_path, _merge_auto_section(existing, _format_readme(entry)))

        page_path = folder_path / _group_page_filename(entry)
        _write_text(page_path, _format_group_page(entry))

        grade = entry.get("grade", "")
        subject = entry.get("subject", "")
        group_name = entry.get("group_name", "")
        variant = entry.get("variant")
        teachers = ", ".join(entry.get("teachers") or [])
        label = f"{grade} | {subject} | {group_name}{f' ({variant})' if variant else ''} | {teachers}".strip(" |")

        rel = folder.replace("\\", "/") + "/README.md"
        index_lines.append(f"- [{label}]({rel})")

    _write_text(repo_root / "הקבצות" / "INDEX.md", "\n".join(index_lines) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
