import json
from pathlib import Path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _fail(messages: list[str]) -> int:
    for message in messages:
        print(f"ERROR: {message}")
    return 1


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    groups_path = root / "נתונים" / "הקבצות.json"
    if not groups_path.exists():
        return _fail(["Missing נתונים/הקבצות.json"])

    groups_data = _read_json(groups_path)
    seen_folders: set[str] = set()
    for entry in (groups_data.get("groups") or []):
        folder = entry.get("folder")
        if not folder:
            errors.append("Group missing folder")
            continue

        if folder in seen_folders:
            errors.append(f"Duplicate folder in groups: {folder}")
        seen_folders.add(folder)

        # Teachers may be missing; allow empty without failing validation.

        if not (root / folder).exists():
            errors.append(f"Folder does not exist: {folder}")

    homerooms_path = root / "נתונים" / "כיתות_אם.json"
    if homerooms_path.exists():
        homerooms_data = _read_json(homerooms_path)
        for entry in (homerooms_data.get("classes") or []):
            grade = entry.get("grade")
            homeroom_class = entry.get("homeroom_class")
            if not grade or not homeroom_class:
                errors.append("Homeroom entry missing grade or homeroom_class")
                continue
            expected = root / "כיתות_אם" / grade / homeroom_class
            if not expected.exists():
                errors.append(f"Homeroom folder does not exist: כיתות_אם/{grade}/{homeroom_class}")

    if errors:
        return _fail(errors)

    print("OK: data looks consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
