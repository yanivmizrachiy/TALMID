from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from .db import connect, migrate


def _team_root() -> Path:
    # team_root/אתר/app/sync.py -> team_root
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _load_excluded_full_names(team_root: Path) -> set[str]:
    path = team_root / "נתונים" / "excluded_students.json"
    if not path.exists():
        return set()
    try:
        data = _read_json(path)
    except Exception:
        return set()

    items = data.get("excluded_full_names") or []
    excluded: set[str] = set()
    for it in items:
        if isinstance(it, str):
            name = _norm(it)
        elif isinstance(it, dict):
            name = _norm(it.get("full_name", ""))
        else:
            name = ""
        if name:
            excluded.add(name)
    return excluded


def _slug_id(prefix: str, text: str) -> str:
    h = hashlib.sha1(_norm(text).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


def _guess_full_name(first_name: str, last_name: str, full_name: str) -> str:
    fn = _norm(first_name)
    ln = _norm(last_name)
    if fn and ln:
        return f"{fn} {ln}"
    if _norm(full_name):
        return _norm(full_name)
    if ln:
        return ln
    return fn


def _upsert_teacher(conn, name: str) -> str:
    name = _norm(name)
    if not name:
        return ""
    teacher_id = _slug_id("t", name)
    conn.execute(
        "INSERT OR IGNORE INTO teachers (id, name) VALUES (?, ?)",
        (teacher_id, name),
    )
    return teacher_id


def _upsert_group(conn, g: dict) -> str:
    folder = _norm(g.get("folder", ""))
    group_id = _slug_id("g", folder)
    conn.execute(
        """
        INSERT INTO groups (id, grade, subject, group_name, variant, folder)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            grade=excluded.grade,
            subject=excluded.subject,
            group_name=excluded.group_name,
            variant=excluded.variant,
            folder=excluded.folder
        """,
        (
            group_id,
            _norm(g.get("grade", "")),
            _norm(g.get("subject", "")),
            _norm(g.get("group_name", "")),
            _norm(g.get("variant", "")) or None,
            folder,
        ),
    )
    for t in g.get("teachers") or []:
        tid = _upsert_teacher(conn, t)
        if tid:
            conn.execute(
                "INSERT OR IGNORE INTO group_teachers (group_id, teacher_id) VALUES (?, ?)",
                (group_id, tid),
            )
    return group_id


def _upsert_homeroom(conn, c: dict) -> str:
    code = _norm(c.get("homeroom_class", ""))
    if not code:
        return ""
    conn.execute(
        """
        INSERT INTO homerooms (code, grade, type)
        VALUES (?, ?, ?)
        ON CONFLICT(code) DO UPDATE SET
            grade=excluded.grade,
            type=excluded.type
        """,
        (code, _norm(c.get("grade", "")), _norm(c.get("type", "")) or "רגילה"),
    )
    for t in c.get("homeroom_teachers") or []:
        tid = _upsert_teacher(conn, t)
        if tid:
            conn.execute(
                "INSERT OR IGNORE INTO homeroom_teachers (homeroom_code, teacher_id) VALUES (?, ?)",
                (code, tid),
            )
    return code


def _student_key(full_name: str, homeroom: str, grade: str) -> str:
    # Deterministic ID across sync runs (so metrics persist)
    base = f"{_norm(full_name)}|{_norm(homeroom)}|{_norm(grade)}"
    return _slug_id("s", base)


def _upsert_student(conn, *, full_name: str, first_name: str = "", last_name: str = "", grade: str = "", homeroom: str = "", notes: str = "", created_from: str = "", external_id: str = "") -> str:
    full_name = _norm(full_name)
    if not full_name:
        return ""

    external_id = _norm(external_id)

    # Prefer stable external IDs when available.
    if external_id:
        existing = conn.execute(
            "SELECT id FROM students WHERE external_id = ? LIMIT 1",
            (external_id,),
        ).fetchone()
        student_id = existing["id"] if existing else _slug_id("s", f"ext|{external_id}")
    else:
        student_id = _student_key(full_name, homeroom, grade)

    conn.execute(
        """
        INSERT INTO students (id, external_id, full_name, first_name, last_name, grade, homeroom_code, notes, created_from)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            external_id=CASE
                WHEN excluded.external_id IS NULL OR excluded.external_id = '' THEN students.external_id
                WHEN students.external_id IS NULL OR students.external_id = '' THEN excluded.external_id
                ELSE students.external_id
            END,
            full_name=excluded.full_name,
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            grade=COALESCE(excluded.grade, students.grade),
            homeroom_code=COALESCE(excluded.homeroom_code, students.homeroom_code),
            notes=CASE
                WHEN excluded.notes IS NULL OR excluded.notes = '' THEN students.notes
                WHEN students.notes IS NULL OR students.notes = '' THEN excluded.notes
                ELSE students.notes || '\n' || excluded.notes
            END,
            created_from=CASE
                WHEN students.created_from IS NULL OR students.created_from = '' THEN excluded.created_from
                ELSE students.created_from
            END
        """,
        (
            student_id,
            external_id or None,
            full_name,
            _norm(first_name) or None,
            _norm(last_name) or None,
            _norm(grade) or None,
            _norm(homeroom) or None,
            _norm(notes) or None,
            _norm(created_from) or None,
        ),
    )

    return student_id


def _add_membership(conn, group_id: str, student_id: str, source: str) -> None:
    if not (group_id and student_id):
        return
    conn.execute(
        "INSERT OR IGNORE INTO group_memberships (group_id, student_id, source) VALUES (?, ?, ?)",
        (group_id, student_id, _norm(source) or None),
    )


def main() -> int:
    team_root = _team_root()

    excluded_names = _load_excluded_full_names(team_root)

    conn = connect()
    migrate(conn)

    # Clean memberships each sync, but keep students + metrics stable.
    conn.execute("DELETE FROM group_memberships")

    groups_data = _read_json(team_root / "נתונים" / "הקבצות.json")
    homerooms_data = _read_json(team_root / "נתונים" / "כיתות_אם.json")

    folder_to_group_id: dict[str, str] = {}

    for g in groups_data.get("groups") or []:
        gid = _upsert_group(conn, g)
        folder_to_group_id[_norm(g.get("folder", ""))] = gid

    for c in homerooms_data.get("classes") or []:
        _upsert_homeroom(conn, c)

    # Import group rosters from Excel-generated CSVs
    roster_files = list((team_root / "הקבצות").rglob("תלמידים_מהאקסל__*.csv"))
    for path in roster_files:
        # group folder is relative from team_root
        rel_folder = str(path.parent.relative_to(team_root)).replace("\\", "/")
        group_id = folder_to_group_id.get(rel_folder)
        if not group_id:
            continue

        for row in _read_csv(path):
            external_id = _norm(row.get("student_id", ""))
            first_name = row.get("first_name", "")
            last_name = row.get("last_name", "")
            full_name = _guess_full_name(first_name, last_name, row.get("full_name", ""))

            if full_name and _norm(full_name) in excluded_names:
                continue
            homeroom = _norm(row.get("homeroom_class", ""))
            grade = homeroom[:1] if homeroom else ""
            notes = _norm(row.get("notes", ""))

            sid = _upsert_student(
                conn,
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                grade=grade,
                homeroom=homeroom,
                notes=notes,
                created_from=f"excel:{path.name}",
                external_id=external_id,
            )
            _add_membership(conn, group_id, sid, source="excel")

    # Import manual/exceptions students: נתונים/תלמידים.csv
    for row in _read_csv(team_root / "נתונים" / "תלמידים.csv"):
        external_id = _norm(row.get("student_id", ""))
        full_name = _norm(row.get("full_name", ""))
        grade = _norm(row.get("grade", ""))
        homeroom = _norm(row.get("homeroom_class", ""))
        math_group = _norm(row.get("math_group", ""))
        notes = _norm(row.get("notes", ""))

        if not (full_name and grade and math_group):
            continue

        if full_name in excluded_names:
            continue

        # pick unique group by grade+name. If multiple variants exist, keep the first match.
        candidate = None
        for g in groups_data.get("groups") or []:
            if _norm(g.get("subject", "")) != "מתמטיקה":
                continue
            if _norm(g.get("grade", "")) == grade and _norm(g.get("group_name", "")) == math_group:
                candidate = g
                break

        sid = _upsert_student(
            conn,
            full_name=full_name,
            grade=grade,
            homeroom=homeroom,
            notes=notes,
            created_from="manual",
            external_id=external_id,
        )

        if candidate:
            group_id = folder_to_group_id.get(_norm(candidate.get("folder", "")))
            if group_id:
                _add_membership(conn, group_id, sid, source="manual")

    # Write sync metadata
    conn.execute(
        "INSERT INTO app_meta (key, value) VALUES ('last_sync_at', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (datetime.now().isoformat(timespec="seconds"),),
    )

    conn.commit()

    # Hard-delete excluded students so they never appear in the app.
    # We delete by normalized full_name (names list is small and explicit).
    for name in sorted(excluded_names):
        if not name:
            continue
        rows = conn.execute("SELECT id FROM students WHERE full_name = ?", (name,)).fetchall()
        for r in rows:
            sid = r["id"]
            # Metrics + memberships are configured with ON DELETE CASCADE,
            # but delete metrics explicitly for older DBs / safety.
            conn.execute("DELETE FROM student_metrics WHERE student_id = ?", (sid,))
            conn.execute("DELETE FROM students WHERE id = ?", (sid,))

    conn.commit()

    # Basic stats
    total_students = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
    total_groups = conn.execute("SELECT COUNT(*) AS c FROM groups").fetchone()["c"]
    total_teachers = conn.execute("SELECT COUNT(*) AS c FROM teachers").fetchone()["c"]

    print(f"Sync OK. students={total_students}, groups={total_groups}, teachers={total_teachers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
