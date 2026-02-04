from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    # team_root/אתר/app/db.py -> team_root/אתר/data/talmid.db
    site_root = Path(__file__).resolve().parents[1]
    return site_root / "data" / "talmid.db"


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS teachers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY,
            grade TEXT NOT NULL,
            subject TEXT NOT NULL,
            group_name TEXT NOT NULL,
            variant TEXT,
            folder TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS group_teachers (
            group_id TEXT NOT NULL,
            teacher_id TEXT NOT NULL,
            PRIMARY KEY (group_id, teacher_id),
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS homerooms (
            code TEXT PRIMARY KEY,
            grade TEXT NOT NULL,
            type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS homeroom_teachers (
            homeroom_code TEXT NOT NULL,
            teacher_id TEXT NOT NULL,
            PRIMARY KEY (homeroom_code, teacher_id),
            FOREIGN KEY (homeroom_code) REFERENCES homerooms(code) ON DELETE CASCADE,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            external_id TEXT,
            full_name TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            grade TEXT,
            homeroom_code TEXT,
            notes TEXT,
            created_from TEXT,
            FOREIGN KEY (homeroom_code) REFERENCES homerooms(code)
        );

        CREATE TABLE IF NOT EXISTS group_memberships (
            group_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            source TEXT,
            PRIMARY KEY (group_id, student_id),
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );

        -- Keep flexible metrics: some are explicit columns, plus JSON blob.
        CREATE TABLE IF NOT EXISTS student_metrics (
            student_id TEXT PRIMARY KEY,
            math_term_grade REAL,
            math_test1 REAL,
            math_test2 REAL,
            behavior_note TEXT,
            extra_json TEXT,
            updated_at TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """
    )

    # Backward-compatible: ensure new columns exist for existing DBs.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()}
    if "external_id" not in cols:
        conn.execute("ALTER TABLE students ADD COLUMN external_id TEXT")

    # external_id is optional, but when present it should be unique.
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_external_id
        ON students(external_id)
        WHERE external_id IS NOT NULL AND external_id != ''
        """
    )
    conn.commit()


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value: str | None) -> object:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}
