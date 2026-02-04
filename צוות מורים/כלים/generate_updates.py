from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _strip_leading_h1(md: str) -> str:
    s = (md or "").strip()
    if not s:
        return ""
    lines = s.splitlines()
    # remove a single leading H1 ("# ...") to avoid duplicate headings in the output
    if lines and lines[0].lstrip().startswith("# "):
        lines = lines[1:]
        # drop a single blank line after the H1 if it exists
        if lines and lines[0].strip() == "":
            lines = lines[1:]
    return "\n".join(lines).strip()


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    team_root = Path(__file__).resolve().parents[1]

    groups_data = _read_json(team_root / "נתונים" / "הקבצות.json")
    homerooms_data = _read_json(team_root / "נתונים" / "כיתות_אם.json")

    groups = groups_data.get("groups") or []
    homerooms = homerooms_data.get("classes") or []

    manual_students = _read_csv_rows(team_root / "נתונים" / "תלמידים.csv")

    excel_summary = _read_text(team_root / "דוחות" / "סיכום_יבוא_אקסל.md")
    exceptions_report = _read_text(team_root / "דוחות" / "שילובים_וחריגים.md")

    lines: list[str] = []
    lines.append("# עדכונים חשובים (מקור מסונכרן)")
    lines.append("")
    lines.append(f"עודכן לאחרונה: **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
    lines.append("")

    lines.append("## מה חשוב לזכור")
    lines.append("- **כיתה (כיתת אם) אינה הקבצה.**")
    lines.append("- הנתונים הרשמיים נשמרים ב-`נתונים/` וממנה נוצרים קבצים/דוחות/אתר.")
    lines.append("- מדדים/ציונים נשמרים ב-SQLite באתר ולא נדרסים בסנכרון.")
    lines.append("")

    lines.append("## סטטוס מהיר")
    lines.append(f"- מספר הקבצות (בנתונים): **{len(groups)}**")
    lines.append(f"- מספר כיתות אם (בנתונים): **{len(homerooms)}**")
    lines.append(f"- תלמידים ידניים/חריגים (נתונים/תלמידים.csv): **{len([r for r in manual_students if (r.get('full_name') or '').strip()])}**")
    lines.append("")

    lines.append("## סיכום דרישות (ללא כפילות)")
    lines.append("### אתר ועמודים")
    lines.append("- עמודי ליבה פעילים: בית, נתונים, שכבה, הקבצה, תלמיד, מורה, כיתת אם, מורים, חיפוש, מפת אתר.")
    lines.append("- בדף המורים מוצגים רק מורי מתמטיקה.")
    lines.append("- כללים ועדכונים מנוהלים כקבצי Markdown בתיקיות הפרויקט (לא מוצגים באתר).")
    lines.append("- בעמוד הבית: כותרת "
                 "\"מערכת חכמה לניהול תלמידים\" + שורת קרדיט "
                 "\"האתר מנוהל ע\"י יניב רז\"; סיכום תלמידים מוצג בגדול מתחת לכפתורים.")
    lines.append("")

    lines.append("### ניסוח ותוכן")
    lines.append("- ללא טקסט דמו/הדרכה בתצוגה.")
    lines.append("- ניסוח אחיד ללא נקודתיים בתוויות (לדוגמה: \"14 תלמידים בהקבצה\").")
    lines.append("- לשון יחיד/רבים חכמה: \"מורה\" כשיש 1, \"מורים\" כשיש יותר.")
    lines.append("")

    lines.append("### עיצוב וניווט")
    lines.append("- צבע ורקע לפי שכבה; בית וכללים נשארים בסגול.")
    lines.append("- בעמוד שכבה: רשימת הקבצות אנכית עם גוונים שונים (בהיר/כהה) בתוך צבע השכבה.")
    lines.append("- סדר הקבצות קבוע: מדעית → א → א1 → מקדמת.")
    lines.append("")

    lines.append("### נתונים ושמירה")
    lines.append("- שמירת מדדים/ציונים במסד SQLite אמיתי (`אתר/data/talmid.db`) עם שמירה גם אחרי סנכרון.")
    lines.append("- זיהוי תלמידים שופר: שימוש ב-`student_id` כשקיים כדי לשמר מדדים גם אחרי תיקוני שכבה/כיתת אם.")
    lines.append("")

    lines.append("### הפעלה ואוטומציה")
    lines.append("- קיצורי דרך לשולחן העבודה להפעלה/עצירה קבועים של האתר, גם אחרי שינויים.")
    lines.append("")

    lines.append("## קישורים שימושיים")
    lines.append("- קובץ כללים מרכזי: `מידע_חשוב.md`")
    lines.append("- דוח יבוא אקסל: `דוחות/סיכום_יבוא_אקסל.md`")
    lines.append("- דוח חריגים/שילובים: `דוחות/שילובים_וחריגים.md`")
    lines.append("")

    if excel_summary:
        lines.append("## דוחות")
        lines.append("### סיכום יבוא אקסל")
        lines.append(_strip_leading_h1(excel_summary))
        lines.append("")

    if exceptions_report:
        if not excel_summary:
            lines.append("## דוחות")
        lines.append("### חריגים ושילובים")
        lines.append(_strip_leading_h1(exceptions_report))
        lines.append("")

    out_path = team_root / "עדכונים_חשובים.md"
    _write_text(out_path, "\n".join(lines).rstrip() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
