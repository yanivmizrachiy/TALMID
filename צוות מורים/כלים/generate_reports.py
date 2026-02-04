import json
from collections import defaultdict
from pathlib import Path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    groups_path = root / "נתונים" / "הקבצות.json"
    groups_data = _read_json(groups_path)

    by_teacher: dict[str, list[dict]] = defaultdict(list)
    for entry in (groups_data.get("groups") or []):
        for teacher in (entry.get("teachers") or []):
            by_teacher[teacher].append(entry)

    lines = ["# מורים והקבצות", ""]
    for teacher in sorted(by_teacher.keys()):
        lines.append(f"## {teacher}")
        for entry in sorted(
            by_teacher[teacher],
            key=lambda e: (e.get("grade", ""), e.get("subject", ""), e.get("group_name", ""), e.get("variant", "")),
        ):
            grade = entry.get("grade", "")
            subject = entry.get("subject", "")
            group_name = entry.get("group_name", "")
            variant = entry.get("variant")
            folder = entry.get("folder", "")
            label = f"{grade} | {subject} | {group_name}{f' ({variant})' if variant else ''}".strip(" |")
            link = folder.replace("\\", "/") + "/README.md" if folder else ""
            lines.append(f"- [{label}]({link})")
        lines.append("")

    _write_text(root / "דוחות" / "מורים.md", "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
