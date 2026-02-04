from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

from .db import connect, json_loads, json_dumps, migrate


APP_TITLE = "TALMID – ניהול תלמידים"

app = FastAPI(title=APP_TITLE)

BASE_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
md = MarkdownIt("commonmark")


def _url_grade(grade: str) -> str:
    return f"/שכבה/{grade}"


def _safe_slug(text: str) -> str:
    s = (text or "").strip()
    s = s.replace("\"", "").replace("'", "").replace("׳", "").replace("״", "")
    s = s.replace("/", " ").replace("\\", " ")
    s = " ".join(s.split())
    if not s:
        return "item"
    out = []
    for ch in s:
        if ch.isalnum() or ch in ["-", "_", " "]:
            out.append(ch)
        else:
            out.append(" ")
    s2 = "".join(out)
    s2 = " ".join(s2.split())
    return s2.replace(" ", "-")[:80] or "item"


def _short_id(entity_id: str) -> str:
    s = (entity_id or "").strip()
    return s[-6:] if len(s) >= 6 else s


def _group_folder_leaf(group_folder: str) -> str:
    s = (group_folder or "").replace("\\", "/").strip().rstrip("/")
    return s.split("/")[-1] if s else "group"


def _url_group_row(group_row) -> str:
    # Pretty + unique: /הקבצה/ז/מתמטיקה/א1_1-1a2b3c
    def _get(key: str, default: str = "") -> str:
        try:
            v = group_row[key]
            return "" if v is None else str(v)
        except Exception:
            return default

    grade = _get("grade", "")
    subject = _get("subject", "מתמטיקה")
    folder = _get("folder", "")
    if folder:
        leaf_src = _group_folder_leaf(folder)
    else:
        leaf_src = _get("group_name", "group") or "group"
    leaf = _safe_slug(leaf_src)
    return f"/הקבצה/{grade}/{subject}/{leaf}-{_short_id(_get('id'))}"


def _url_student_row(student_row) -> str:
    name_slug = _safe_slug(student_row["full_name"])
    return f"/תלמיד/{name_slug}-{_short_id(student_row['id'])}"


def _url_teacher_row(teacher_row) -> str:
    name_slug = _safe_slug(teacher_row["name"])
    return f"/מורה/{name_slug}-{_short_id(teacher_row['id'])}"


def _url_homeroom(code: str) -> str:
    return f"/כיתה/{code}"


def _extract_short_id_from_slug(slug: str) -> str:
    # expecting something like "some-name-1a2b3c"
    s = (slug or "").strip()
    if "-" not in s:
        return ""
    tail = s.rsplit("-", 1)[-1]
    if len(tail) != 6:
        return ""
    # IDs are sha1 hex snippets in this project.
    if not all(ch in "0123456789abcdef" for ch in tail.lower()):
        return ""
    return tail.lower()


def _crumb(label: str, url: str | None = None) -> dict[str, str | None]:
    return {"label": label, "url": url}


def _theme_class(grade: str | None) -> str:
    if grade == "ז":
        return "theme-z"
    if grade == "ח":
        return "theme-h"
    if grade == "ט":
        return "theme-t"
    return ""


def _with_common_context(request: Request, theme: str | None = None, **extra):
    return {
        "request": request,
        "app_title": APP_TITLE,
        "now": datetime.now(),
        "theme_class": _theme_class(theme),
        "url_grade": _url_grade,
        "url_group": _url_group_row,
        "url_student": _url_student_row,
        "url_teacher": _url_teacher_row,
        "url_homeroom": _url_homeroom,
        **extra,
    }


@app.on_event("startup")
def _startup() -> None:
    conn = connect()
    migrate(conn)
    conn.close()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = connect()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
        last_sync_at = conn.execute(
            "SELECT value FROM app_meta WHERE key='last_sync_at'",
        ).fetchone()
        last_sync_at = last_sync_at["value"] if last_sync_at else None
        grades = ["ז", "ח", "ט"]
        per_grade = {}
        for g in grades:
            per_grade[g] = conn.execute(
                "SELECT COUNT(*) AS c FROM students WHERE grade = ?",
                (g,),
            ).fetchone()["c"]

        return templates.TemplateResponse(
            "home.html",
            _with_common_context(
                request,
                title="דף ראשי – TALMID",
                breadcrumbs=[_crumb("בית")],
                total_students=total,
                per_grade=per_grade,
                last_sync_at=last_sync_at,
            ),
        )
    finally:
        conn.close()


@app.get("/דשבורד", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = connect()
    try:
        total_students = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
        total_groups = conn.execute("SELECT COUNT(*) AS c FROM groups").fetchone()["c"]
        total_teachers = conn.execute("SELECT COUNT(*) AS c FROM teachers").fetchone()["c"]

        last_sync_at = conn.execute(
            "SELECT value FROM app_meta WHERE key='last_sync_at'",
        ).fetchone()
        last_sync_at = last_sync_at["value"] if last_sync_at else None

        grades = ["ז", "ח", "ט"]
        per_grade_values = [
            conn.execute("SELECT COUNT(*) AS c FROM students WHERE grade=?", (g,)).fetchone()["c"]
            for g in grades
        ]

        group_sizes = conn.execute(
            """
            SELECT g.id, g.grade, g.subject, g.group_name, g.variant, g.folder,
                   (SELECT COUNT(*) FROM group_memberships gm WHERE gm.group_id=g.id) AS student_count
            FROM groups g
            ORDER BY student_count DESC, g.grade, g.subject, g.group_name
            LIMIT 12
            """
        ).fetchall()

        teacher_load = conn.execute(
            """
            SELECT t.id, t.name,
                   (SELECT COUNT(*) FROM group_teachers gt WHERE gt.teacher_id=t.id) AS group_count,
                   (
                     SELECT COUNT(DISTINCT gm.student_id)
                     FROM group_teachers gt
                     JOIN group_memberships gm ON gm.group_id=gt.group_id
                     WHERE gt.teacher_id=t.id
                   ) AS student_count
            FROM teachers t
            ORDER BY student_count DESC, t.name
            LIMIT 12
            """
        ).fetchall()

        # Metrics summary (ignores missing)
        metrics_summary = conn.execute(
            """
            SELECT
              AVG(math_term_grade) AS avg_term,
              AVG(math_test1) AS avg_test1,
              AVG(math_test2) AS avg_test2,
              COUNT(*) AS rows
            FROM student_metrics
            """
        ).fetchone()

        return templates.TemplateResponse(
            "dashboard.html",
            _with_common_context(
                request,
                title="נתונים – TALMID",
                breadcrumbs=[_crumb("בית", "/"), _crumb("נתונים")],
                last_sync_at=last_sync_at,
                total_students=total_students,
                total_groups=total_groups,
                total_teachers=total_teachers,
                per_grade_labels=grades,
                per_grade_values=per_grade_values,
                group_sizes=group_sizes,
                teacher_load=teacher_load,
                metrics_summary=metrics_summary,
            ),
        )
    finally:
        conn.close()


# Canonical Hebrew URLs
@app.get("/שכבה/{grade}", response_class=HTMLResponse)
def grade_page_he(request: Request, grade: str):
    return _render_grade_page(request, grade)


@app.get("/הקבצה/{grade}/{subject}/{slug}", response_class=HTMLResponse)
def group_page_pretty(request: Request, grade: str, subject: str, slug: str):
    # Resolve by short-id suffix if present, else by folder leaf
    conn = connect()
    try:
        short_id = _extract_short_id_from_slug(slug)
        if short_id:
            row = conn.execute(
                "SELECT id FROM groups WHERE grade=? AND subject=? AND id LIKE '%' || ? LIMIT 2",
                (grade, subject, short_id),
            ).fetchall()
            if len(row) == 1:
                return _render_group_page(request, row[0]["id"])

        # fallback: treat as folder leaf
        leaf = slug.rsplit("-", 1)[0] if "-" in slug else slug
        folder = f"הקבצות/{grade}/{subject}/{leaf}"
        gid = conn.execute(
            "SELECT id FROM groups WHERE folder = ? LIMIT 1",
            (folder,),
        ).fetchone()
        if gid:
            return _render_group_page(request, gid["id"])

        raise HTTPException(status_code=404)
    finally:
        conn.close()


@app.get("/הקבצה/{group_id}", include_in_schema=False)
def group_page_he_legacy_id(group_id: str):
    # Redirect /הקבצה/{id} -> pretty URL
    conn = connect()
    try:
        g = conn.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
        if not g:
            raise HTTPException(status_code=404)
        return RedirectResponse(url=_url_group_row(g), status_code=307)
    finally:
        conn.close()


@app.get("/תלמיד/{slug}", response_class=HTMLResponse)
def student_page_pretty(request: Request, slug: str):
    short_id = _extract_short_id_from_slug(slug)
    if not short_id:
        raise HTTPException(status_code=404)
    conn = connect()
    try:
        rows = conn.execute("SELECT id FROM students WHERE id LIKE '%' || ? LIMIT 2", (short_id,)).fetchall()
        if len(rows) != 1:
            raise HTTPException(status_code=404)
        return _render_student_page(request, rows[0]["id"])
    finally:
        conn.close()


@app.post("/תלמיד/{slug}/מדדים")
def update_student_metrics_pretty(
    request: Request,
    slug: str,
    math_term_grade: str = Form(""),
    math_test1: str = Form(""),
    math_test2: str = Form(""),
    behavior_note: str = Form(""),
    extra_json: str = Form(""),
):
    short_id = _extract_short_id_from_slug(slug)
    if not short_id:
        raise HTTPException(status_code=404)
    conn = connect()
    try:
        rows = conn.execute("SELECT id FROM students WHERE id LIKE '%' || ? LIMIT 2", (short_id,)).fetchall()
        if len(rows) != 1:
            raise HTTPException(status_code=404)
        student_id = rows[0]["id"]
    finally:
        conn.close()

    return update_student_metrics(
        request,
        student_id,
        math_term_grade=math_term_grade,
        math_test1=math_test1,
        math_test2=math_test2,
        behavior_note=behavior_note,
        extra_json=extra_json,
    )


@app.get("/מורה/{slug}", response_class=HTMLResponse)
def teacher_page_pretty(request: Request, slug: str):
    short_id = _extract_short_id_from_slug(slug)
    if not short_id:
        raise HTTPException(status_code=404)
    conn = connect()
    try:
        rows = conn.execute("SELECT id FROM teachers WHERE id LIKE '%' || ? LIMIT 2", (short_id,)).fetchall()
        if len(rows) != 1:
            raise HTTPException(status_code=404)
        return _render_teacher_page(request, rows[0]["id"])
    finally:
        conn.close()


@app.get("/כיתה/{code}", response_class=HTMLResponse)
def homeroom_page_he(request: Request, code: str):
    return _render_homeroom_page(request, code)


@app.get("/מידע", response_class=HTMLResponse)
def info_page_he(request: Request):
    raise HTTPException(status_code=404)


@app.get("/כללים", include_in_schema=False)
def rules_page_alias():
    raise HTTPException(status_code=404)


@app.get("/עדכונים", response_class=HTMLResponse)
def updates_page_he(request: Request):
    raise HTTPException(status_code=404)


@app.get("/מורים", response_class=HTMLResponse)
def teachers_index(request: Request):
    conn = connect()
    try:
        teachers = conn.execute(
            """
            SELECT t.id, t.name,
                                     (
                                         SELECT COUNT(*)
                                         FROM group_teachers gt
                                         JOIN groups g ON g.id = gt.group_id
                                         WHERE gt.teacher_id=t.id AND g.subject = 'מתמטיקה'
                                     ) AS group_count,
                   (
                     SELECT COUNT(DISTINCT gm.student_id)
                     FROM group_teachers gt
                                         JOIN groups g ON g.id = gt.group_id
                     JOIN group_memberships gm ON gm.group_id = gt.group_id
                                         WHERE gt.teacher_id = t.id AND g.subject = 'מתמטיקה'
                   ) AS student_count
            FROM teachers t
                        WHERE EXISTS (
                            SELECT 1
                            FROM group_teachers gt
                            JOIN groups g ON g.id = gt.group_id
                            WHERE gt.teacher_id = t.id AND g.subject = 'מתמטיקה'
                        )
            ORDER BY t.name
            """
        ).fetchall()

        return templates.TemplateResponse(
            "teachers_index.html",
            _with_common_context(
                request,
                title="צוות מתמטיקה תשפ\"ו – TALMID",
                breadcrumbs=[_crumb("בית", "/"), _crumb("צוות מתמטיקה תשפ\"ו")],
                teachers=teachers,
            ),
        )
    finally:
        conn.close()


@app.get("/חיפוש", response_class=HTMLResponse)
def search_page(request: Request, q: str = ""):
    q = (q or "").strip()
    conn = connect()
    try:
        students = []
        teachers = []
        homerooms = []
        groups = []

        if q:
            like = f"%{q}%"

            students = conn.execute(
                """
                SELECT id, full_name, grade, homeroom_code
                FROM students
                WHERE full_name LIKE ? OR COALESCE(first_name,'') LIKE ? OR COALESCE(last_name,'') LIKE ?
                ORDER BY COALESCE(last_name, full_name), COALESCE(first_name, '')
                LIMIT 50
                """,
                (like, like, like),
            ).fetchall()

            teachers = conn.execute(
                """
                SELECT t.id, t.name,
                       (SELECT COUNT(*) FROM group_teachers gt WHERE gt.teacher_id=t.id) AS group_count,
                       (
                         SELECT COUNT(DISTINCT gm.student_id)
                         FROM group_teachers gt
                         JOIN group_memberships gm ON gm.group_id = gt.group_id
                         WHERE gt.teacher_id = t.id
                       ) AS student_count
                FROM teachers t
                WHERE t.name LIKE ?
                ORDER BY t.name
                LIMIT 50
                """,
                (like,),
            ).fetchall()

            homerooms = conn.execute(
                """
                SELECT code, grade, type
                FROM homerooms
                WHERE code LIKE ? OR grade LIKE ?
                ORDER BY grade, code
                LIMIT 30
                """,
                (like, like),
            ).fetchall()

            groups = conn.execute(
                """
                SELECT g.id, g.grade, g.subject, g.group_name, g.variant, g.folder,
                       (SELECT COUNT(*) FROM group_memberships gm WHERE gm.group_id=g.id) AS student_count
                FROM groups g
                WHERE g.group_name LIKE ? OR COALESCE(g.variant,'') LIKE ? OR g.folder LIKE ?
                ORDER BY g.grade, g.subject, g.group_name
                LIMIT 50
                """,
                (like, like, like),
            ).fetchall()

        return templates.TemplateResponse(
            "search.html",
            _with_common_context(
                request,
                title="חיפוש – TALMID",
                breadcrumbs=[_crumb("בית", "/"), _crumb("חיפוש")],
                q=q,
                students=students,
                teachers=teachers,
                homerooms=homerooms,
                groups=groups,
            ),
        )
    finally:
        conn.close()


@app.get("/מפה", response_class=HTMLResponse)
def sitemap(request: Request):
    conn = connect()
    try:
        grades = []
        for grade in ["ז", "ח", "ט"]:
            student_count = conn.execute("SELECT COUNT(*) AS c FROM students WHERE grade=?", (grade,)).fetchone()["c"]
            homeroom_count = conn.execute("SELECT COUNT(*) AS c FROM homerooms WHERE grade=?", (grade,)).fetchone()["c"]
            group_count = conn.execute(
                "SELECT COUNT(*) AS c FROM groups WHERE grade=? AND subject='מתמטיקה'",
                (grade,),
            ).fetchone()["c"]
            grades.append(
                {
                    "grade": grade,
                    "student_count": student_count,
                    "homeroom_count": homeroom_count,
                    "group_count": group_count,
                }
            )

        homerooms = conn.execute("SELECT code, grade, type FROM homerooms ORDER BY grade, code").fetchall()

        return templates.TemplateResponse(
            "sitemap.html",
            _with_common_context(
                request,
                title="מפת האתר – TALMID",
                breadcrumbs=[_crumb("בית", "/"), _crumb("מפת האתר")],
                grades=grades,
                homerooms=homerooms,
            ),
        )
    finally:
        conn.close()


def _render_grade_page(request: Request, grade: str):
    if grade not in {"ז", "ח", "ט"}:
        raise HTTPException(status_code=404)

    conn = connect()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM students WHERE grade = ?",
            (grade,),
        ).fetchone()["c"]

        groups = conn.execute(
            """
            SELECT g.id, g.grade, g.subject, g.group_name, g.variant, g.folder,
                   (SELECT COUNT(*) FROM group_memberships gm WHERE gm.group_id=g.id) AS student_count
            FROM groups g
            WHERE g.grade = ? AND g.subject = 'מתמטיקה'
                        ORDER BY
                            CASE g.group_name
                                WHEN 'מדעית' THEN 0
                                WHEN 'א' THEN 1
                                WHEN 'א1' THEN 2
                                WHEN 'מקדמת' THEN 3
                                ELSE 9
                            END,
                            COALESCE(g.variant, ''),
                            g.folder
            """,
            (grade,),
        ).fetchall()

        # teachers per group
        group_teachers = {}
        for row in groups:
            teachers = conn.execute(
                """
                SELECT t.id, t.name
                FROM teachers t
                JOIN group_teachers gt ON gt.teacher_id=t.id
                WHERE gt.group_id = ?
                ORDER BY t.name
                """,
                (row["id"],),
            ).fetchall()
            group_teachers[row["id"]] = teachers

        return templates.TemplateResponse(
            "grade.html",
            _with_common_context(
                request,
                theme=grade,
                title=f"שכבת {grade} – TALMID",
                breadcrumbs=[_crumb("בית", "/"), _crumb(f"שכבת {grade}")],
                grade=grade,
                total_students=total,
                groups=groups,
                group_teachers=group_teachers,
            ),
        )
    finally:
        conn.close()


def _render_group_page(request: Request, group_id: str):
    conn = connect()
    try:
        group = conn.execute(
            "SELECT * FROM groups WHERE id = ?",
            (group_id,),
        ).fetchone()
        if not group:
            raise HTTPException(status_code=404)

        teachers = conn.execute(
            """
            SELECT t.id, t.name
            FROM teachers t
            JOIN group_teachers gt ON gt.teacher_id=t.id
            WHERE gt.group_id = ?
            ORDER BY t.name
            """,
            (group_id,),
        ).fetchall()

        students = conn.execute(
            """
            SELECT s.id, s.first_name, s.last_name, s.full_name, s.homeroom_code,
                   m.math_term_grade, m.math_test1, m.math_test2
            FROM students s
            JOIN group_memberships gm ON gm.student_id=s.id
            LEFT JOIN student_metrics m ON m.student_id=s.id
            WHERE gm.group_id = ?
            ORDER BY COALESCE(s.last_name, s.full_name), COALESCE(s.first_name, '')
            """,
            (group_id,),
        ).fetchall()

        total = len(students)

        variant_txt = f" ({group['variant']})" if group["variant"] else ""

        return templates.TemplateResponse(
            "group.html",
            _with_common_context(
                request,
                theme=group["grade"],
                title=f"הקבצה {group['group_name']} – שכבת {group['grade']} – TALMID",
                breadcrumbs=[
                    _crumb("בית", "/"),
                    _crumb(f"שכבת {group['grade']}", _url_grade(group["grade"])),
                    _crumb(f"הקבצה {group['group_name']}{variant_txt}"),
                ],
                group=group,
                teachers=teachers,
                students=students,
                total_students=total,
            ),
        )
    finally:
        conn.close()


def _render_student_page(request: Request, student_id: str):
    conn = connect()
    try:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            raise HTTPException(status_code=404)

        metrics = conn.execute(
            "SELECT * FROM student_metrics WHERE student_id = ?",
            (student_id,),
        ).fetchone()

        memberships = conn.execute(
            """
            SELECT g.id, g.grade, g.subject, g.group_name, g.variant, g.folder
            FROM groups g
            JOIN group_memberships gm ON gm.group_id=g.id
            WHERE gm.student_id = ?
                        ORDER BY
                            g.subject,
                            CASE g.group_name
                                WHEN 'מדעית' THEN 0
                                WHEN 'א' THEN 1
                                WHEN 'א1' THEN 2
                                WHEN 'מקדמת' THEN 3
                                ELSE 9
                            END,
                            COALESCE(g.variant, ''),
                            g.folder
            """,
            (student_id,),
        ).fetchall()

        return templates.TemplateResponse(
            "student.html",
            _with_common_context(
                request,
                theme=student["grade"],
                title=f"{student['full_name']} – TALMID",
                breadcrumbs=[
                    _crumb("בית", "/"),
                    _crumb("חיפוש", "/חיפוש"),
                    _crumb(student["full_name"]),
                ],
                student=student,
                metrics=metrics,
                memberships=memberships,
            ),
        )
    finally:
        conn.close()


@app.post("/students/{student_id}/metrics")
def update_student_metrics(
    request: Request,
    student_id: str,
    math_term_grade: str = Form("") ,
    math_test1: str = Form("") ,
    math_test2: str = Form("") ,
    behavior_note: str = Form("") ,
    extra_json: str = Form(""),
):
    def to_float(v: str):
        v = (v or "").strip()
        if v == "":
            return None
        try:
            return float(v)
        except Exception:
            return None

    conn = connect()
    try:
        exists = conn.execute("SELECT 1 FROM students WHERE id=?", (student_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404)

        # validate extra_json if provided
        extra_blob = None
        if (extra_json or "").strip() != "":
            try:
                parsed = json_loads(extra_json)
                extra_blob = json_dumps(parsed)
            except Exception:
                extra_blob = json_dumps({"raw": extra_json})

        conn.execute(
            """
            INSERT INTO student_metrics (student_id, math_term_grade, math_test1, math_test2, behavior_note, extra_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                math_term_grade=excluded.math_term_grade,
                math_test1=excluded.math_test1,
                math_test2=excluded.math_test2,
                behavior_note=excluded.behavior_note,
                extra_json=COALESCE(excluded.extra_json, student_metrics.extra_json),
                updated_at=excluded.updated_at
            """,
            (
                student_id,
                to_float(math_term_grade),
                to_float(math_test1),
                to_float(math_test2),
                (behavior_note or "").strip() or None,
                extra_blob,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()

        # Redirect to pretty student page
        student_row = conn.execute("SELECT id, full_name FROM students WHERE id=?", (student_id,)).fetchone()
        if student_row:
            return RedirectResponse(url=_url_student_row(student_row), status_code=303)
        return RedirectResponse(url="/", status_code=303)
    finally:
        conn.close()


def _render_teacher_page(request: Request, teacher_id: str):
    conn = connect()
    try:
        teacher = conn.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)).fetchone()
        if not teacher:
            raise HTTPException(status_code=404)

        groups = conn.execute(
            """
            SELECT g.id, g.grade, g.subject, g.group_name, g.variant, g.folder,
                   (SELECT COUNT(*) FROM group_memberships gm WHERE gm.group_id=g.id) AS student_count
            FROM groups g
            JOIN group_teachers gt ON gt.group_id=g.id
            WHERE gt.teacher_id = ? AND g.subject = 'מתמטיקה'
                        ORDER BY
                            g.grade,
                            CASE g.group_name
                                WHEN 'מדעית' THEN 0
                                WHEN 'א' THEN 1
                                WHEN 'א1' THEN 2
                                WHEN 'מקדמת' THEN 3
                                ELSE 9
                            END,
                            COALESCE(g.variant, ''),
                            g.folder
            """,
            (teacher_id,),
        ).fetchall()

        return templates.TemplateResponse(
            "teacher.html",
                _with_common_context(request, title=f"מורה: {teacher['name']} – TALMID", teacher=teacher, groups=groups, breadcrumbs=[_crumb("בית", "/"), _crumb("מורים", "/מורים"), _crumb(teacher["name"])]),
        )
    finally:
        conn.close()


def _render_homeroom_page(request: Request, code: str):
    conn = connect()
    try:
        homeroom = conn.execute("SELECT * FROM homerooms WHERE code=?", (code,)).fetchone()
        if not homeroom:
            raise HTTPException(status_code=404)

        teachers = conn.execute(
            """
            SELECT t.id, t.name
            FROM teachers t
            JOIN homeroom_teachers ht ON ht.teacher_id=t.id
            WHERE ht.homeroom_code = ?
            ORDER BY t.name
            """,
            (code,),
        ).fetchall()

        students = conn.execute(
            """
            SELECT s.id, s.first_name, s.last_name, s.full_name
            FROM students s
            WHERE s.homeroom_code = ?
            ORDER BY COALESCE(s.last_name, s.full_name), COALESCE(s.first_name, '')
            """,
            (code,),
        ).fetchall()

        # for each student, list math groups
        math_groups_by_student = {}
        for s in students:
            g = conn.execute(
                """
                SELECT g.id, g.grade, g.subject, g.group_name, g.variant, g.folder
                FROM groups g
                JOIN group_memberships gm ON gm.group_id=g.id
                WHERE gm.student_id=? AND g.subject='מתמטיקה'
                                ORDER BY
                                    CASE g.group_name
                                        WHEN 'מדעית' THEN 0
                                        WHEN 'א' THEN 1
                                        WHEN 'א1' THEN 2
                                        WHEN 'מקדמת' THEN 3
                                        ELSE 9
                                    END,
                                    COALESCE(g.variant, ''),
                                    g.folder
                """,
                (s["id"],),
            ).fetchall()
            math_groups_by_student[s["id"]] = g

        return templates.TemplateResponse(
            "homeroom.html",
            _with_common_context(
                request,
                theme=homeroom["grade"],
                title=f"כיתה {homeroom['code']} – TALMID",
                breadcrumbs=[
                    _crumb("בית", "/"),
                    _crumb(f"שכבת {homeroom['grade']}", _url_grade(homeroom["grade"])),
                    _crumb(f"כיתה {homeroom['code']}")
                ],
                homeroom=homeroom,
                teachers=teachers,
                students=students,
                math_groups_by_student=math_groups_by_student,
            ),
        )
    finally:
        conn.close()


def _render_info_page(request: Request):
    # Render the existing auto-generated summary.
    team_root = Path(__file__).resolve().parents[2]
    md_path = team_root / "מידע_חשוב.md"
    text = md_path.read_text(encoding="utf-8") if md_path.exists() else "(חסר קובץ מידע_חשוב.md)"
    html = md.render(text)
    return templates.TemplateResponse(
        "info.html",
        _with_common_context(
            request,
            title="כללים חשובים – TALMID",
            breadcrumbs=[_crumb("בית", "/"), _crumb("כללים חשובים")],
            info_html=html,
        ),
    )


def _render_updates_page(request: Request):
    team_root = Path(__file__).resolve().parents[2]
    md_path = team_root / "עדכונים_חשובים.md"
    text = md_path.read_text(encoding="utf-8") if md_path.exists() else "(חסר קובץ עדכונים_חשובים.md)"
    html = md.render(text)
    return templates.TemplateResponse(
        "updates.html",
        _with_common_context(
            request,
            title="עדכונים חשובים – TALMID",
            breadcrumbs=[_crumb("בית", "/"), _crumb("עדכונים")],
            updates_html=html,
        ),
    )


# Legacy redirects to canonical Hebrew paths (keep old links working)
@app.get("/grade/{grade}/", include_in_schema=False)
@app.get("/grade/{grade}", include_in_schema=False)
def _legacy_grade_redirect(grade: str):
    return RedirectResponse(url=_url_grade(grade), status_code=307)


@app.get("/groups/{group_id}/", include_in_schema=False)
@app.get("/groups/{group_id}", include_in_schema=False)
def _legacy_group_redirect(group_id: str):
    return RedirectResponse(url=f"/הקבצה/{group_id}", status_code=307)


@app.get("/students/{student_id}/", include_in_schema=False)
@app.get("/students/{student_id}", include_in_schema=False)
def _legacy_student_redirect(student_id: str):
    conn = connect()
    try:
        s = conn.execute("SELECT id, full_name FROM students WHERE id=?", (student_id,)).fetchone()
        if not s:
            return RedirectResponse(url="/", status_code=307)
        return RedirectResponse(url=_url_student_row(s), status_code=307)
    finally:
        conn.close()


@app.get("/teachers/{teacher_id}/", include_in_schema=False)
@app.get("/teachers/{teacher_id}", include_in_schema=False)
def _legacy_teacher_redirect(teacher_id: str):
    conn = connect()
    try:
        t = conn.execute("SELECT id, name FROM teachers WHERE id=?", (teacher_id,)).fetchone()
        if not t:
            return RedirectResponse(url="/", status_code=307)
        return RedirectResponse(url=_url_teacher_row(t), status_code=307)
    finally:
        conn.close()


@app.get("/homerooms/{code}/", include_in_schema=False)
@app.get("/homerooms/{code}", include_in_schema=False)
def _legacy_homeroom_redirect(code: str):
    return RedirectResponse(url=_url_homeroom(code), status_code=307)


@app.get("/info/", include_in_schema=False)
@app.get("/info", include_in_schema=False)
def _legacy_info_redirect():
    raise HTTPException(status_code=404)
