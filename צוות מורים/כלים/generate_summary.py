from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    team_root = Path(__file__).resolve().parents[1]

    groups = _read_json(team_root / "נתונים" / "הקבצות.json").get("groups") or []
    homerooms = _read_json(team_root / "נתונים" / "כיתות_אם.json").get("classes") or []

    # Rules / constraints
    allowed_group_names = sorted({g.get("group_name") for g in groups if g.get("group_name")})

    homerooms_by_grade: dict[str, list[dict]] = defaultdict(list)
    for c in homerooms:
        homerooms_by_grade[c.get("grade", "?")].append(c)

    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = []
    lines.append("# כללים חשובים (מקור מסונכרן)")
    lines.append("")
    lines.append(f"עודכן לאחרונה: **{last_updated}**")
    lines.append("")
    lines.append(
        "מסמך זה נוצר אוטומטית מתוך תיקיית `נתונים/` ומרכז את הכללים, ההגדרות והאילוצים של הפרויקט. "
        "לא עורכים ידנית — משנים את המקור (`נתונים/` או קבצי הקבצות/כיתות אם) ומריצים ריענון."
    )
    lines.append("")

    lines.append("## מושגים (שפה אחידה)")
    lines.append("- **כיתת אם**: כיתה מנהלית (למשל ח3).")
    lines.append("- **הקבצה**: קבוצת לימוד במקצוע (כאן: מתמטיקה) — לא זהה לכיתת אם.")
    lines.append("- **קבוצת אקסל**: כל גיליון/קובץ באקסל הוא קבוצת לימוד נפרדת ונשמר כ-CSV בתיקיית ההקבצה.")
    lines.append("")

    lines.append("## עקרונות עבודה")
    lines.append("- מקור האמת הוא `נתונים/` (JSON/CSV).")
    lines.append("- מסד הנתונים באתר (SQLite) מסתנכרן מהנתונים — **אבל מדדים/ציונים נשמרים ב-SQLite ולא נדרסים בסנכרון**.")
    lines.append("- לכל תלמיד יש שיוך ל: כיתת אם + הקבצה במתמטיקה.")
    lines.append("")

    lines.append("## הקבצות במתמטיקה")
    if allowed_group_names:
        lines.append(f"- שמות הקבצות מותרים (כפי שמוגדר בנתונים): {', '.join(allowed_group_names)}")
    lines.append("- מבנה תיקיות ההקבצות: `הקבצות/<שכבה>/<מקצוע>/<הקבצה>`")
    lines.append("- דף הקבצה בכל תיקייה: `הקבצה_<שכבה>_<מקצוע>_<הקבצה>*.md`")
    lines.append("")

    lines.append("## כיתות אם ומחנכים")
    for grade in sorted(homerooms_by_grade.keys()):
        classes = sorted(homerooms_by_grade[grade], key=lambda x: x.get("homeroom_class", ""))
        class_codes = [c.get("homeroom_class", "") for c in classes if c.get("homeroom_class")]
        if class_codes:
            lines.append(f"- שכבה {grade}: {', '.join(class_codes)}")
    lines.append("")

    lines.append("### מחנכים לפי כיתה")
    for grade in sorted(homerooms_by_grade.keys()):
        classes = sorted(homerooms_by_grade[grade], key=lambda x: x.get("homeroom_class", ""))
        for c in classes:
            code = c.get("homeroom_class", "")
            teachers = ", ".join(c.get("homeroom_teachers") or [])
            if code and teachers:
                lines.append(f"- {code}: {teachers}")
    lines.append("")

    lines.append("## מורים להקבצות (מתמטיקה)")
    groups_by_grade: dict[str, list[dict]] = defaultdict(list)
    for g in groups:
        groups_by_grade[g.get("grade", "?")].append(g)

    for grade in sorted(groups_by_grade.keys()):
        lines.append(f"### שכבת {grade}")
        for g in sorted(
            groups_by_grade[grade],
            key=lambda x: (x.get("group_name", ""), x.get("variant", ""), x.get("folder", "")),
        ):
            group_name = g.get("group_name", "")
            if not group_name:
                continue
            variant = g.get("variant")
            teachers = ", ".join(g.get("teachers") or [])
            if not teachers:
                continue
            group_label = f"{group_name}{f' ({variant})' if variant else ''}".strip()
            lines.append(f"- {group_label}: {teachers}")
        lines.append("")

    lines.append("## קבצים וקישורים חשובים")
    lines.append("- נתונים (מקור אמת): `נתונים/הקבצות.json`, `נתונים/כיתות_אם.json`, `נתונים/excel_mapping.json`")
    lines.append("- אינדקס הקבצות: `הקבצות/INDEX.md`")
    lines.append("- אינדקס כיתות אם: `כיתות_אם/INDEX.md`")
    lines.append("- סיכום יבוא אקסל: `דוחות/סיכום_יבוא_אקסל.md`")
    lines.append("- עדכונים חשובים (נוצר אוטומטית): `עדכונים_חשובים.md`")
    lines.append("")

    lines.append("## אתר (FastAPI + SQLite) – תפעול")
    lines.append("- האתר נמצא ב: `אתר/`")
    lines.append("- מסד נתונים מקומי: `אתר/data/talmid.db` (נשמר מקומית ומוחרג מ-git)")
    lines.append("- סנכרון ל-DB: `python -m app.sync` (מתוך `אתר/`) או משימת VS Code: `TALMID: Sync DB`")
    lines.append("- הרצה בלייב: `uvicorn app.main:app --reload --port 8000` ואז לפתוח: http://127.0.0.1:8000")
    lines.append("")

    lines.append("## תהליך עבודה מומלץ (אוטומציה)")
    lines.append("1. ריענון נתונים מלא: `./refresh_data.ps1`")
    lines.append("2. סנכרון מסד נתונים: `TALMID: Sync DB`")
    lines.append("3. הרצת אתר: `TALMID: Run Web (reload)`")
    lines.append("")

    lines.append("## חריגים / תלמידים ידניים")
    lines.append("כאשר תלמיד לא מגיע מאקסל או צריך שיוך מיוחד (שילוב/חריג) — מזינים אותו ידנית ב-`נתונים/תלמידים.csv`.")
    lines.append("")
    lines.append("### קובץ מקור")
    lines.append("- `נתונים/תלמידים.csv`")
    lines.append("")
    lines.append("### עמודות (מינימום מומלץ)")
    lines.append("- `full_name` – חובה")
    lines.append("- `grade` – חובה (ז/ח/ט)")
    lines.append("- `math_group` – חובה (שם הקבצה כפי שמופיע בנתונים, למשל: א / א1 / מדעית / מקדמת)")
    lines.append("- `homeroom_class` – מומלץ (למשל ז3)")
    lines.append("- `notes` – מומלץ (טקסט חופשי לתיעוד החריג)")
    lines.append("")
    lines.append("### איך השיוך עובד")
    lines.append("- הסקריפט `כלים/generate_manual_group_students.py` ממפה `grade + math_group` לקובץ יעד בתוך תיקיית ההקבצה.")
    lines.append("- התוצר נכתב לכל הקבצה כקובץ: `הקבצות/**/תלמידים_ידני.csv`.")
    lines.append("- אם קיימות כמה קבוצות לאותו שם הקבצה באותה שכבה (למשל וריאנטים שונים) — זה יופיע כ'צריך החלטה' בדוח החריגים.")
    lines.append("- דוח סיכום חריגים נכתב ל: `דוחות/שילובים_וחריגים.md`.")
    lines.append("")
    lines.append("### אחרי שינוי (מה עושים בפועל)")
    lines.append("1. להריץ ריענון: `./refresh_data.ps1` (מייצר `תלמידים_ידני.csv` + מעדכן דוחות)")
    lines.append("2. לסנכרן למסד הנתונים: `TALMID: Sync DB`")
    lines.append("3. לרענן דפדפן באתר")
    lines.append("")

    _write_text(team_root / "מידע_חשוב.md", "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
