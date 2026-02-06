# RULES — מיקרו־אתר סטטי מבודד

## כלל ברזל — אין בלבולים
- התיקייה [הקבצות/](../הקבצות/) כבר קיימת בפרויקט, ולכן כדי למנוע בלבול ולשמור על בידוד מלא נוצרה תיקייה חדשה בשם `מיפוי_קבוצות_מתמטיקה/`.
- אסור בתכלית האיסור לגעת בתיקייה הקיימת [הקבצות/](../הקבצות/) או בכל רכיב אחר בפרויקט.

## העתק מלא של הדרישות (כפי שנמסרו)

You are working inside an existing GitHub repository that already contains a full student management system
(grades, notes, comments, sensitive data).

========================
ABSOLUTE SAFETY RULES
========================
- The existing repository and project are READ-ONLY.
- You must NOT modify, delete, rename, move, refactor, or reformat ANY existing file or folder.
- You must NOT touch grades, notes, comments, analytics, IDs, or any sensitive student data.
- You must NOT reuse or import any existing project HTML, CSS, JS, backend, or logic.
- You must NOT change package.json, build tools, routing, CI/CD, workflows, or repo configuration.
- You must NOT add dependencies or libraries.
- You may ONLY add a new isolated folder with new static files.

If any requirement conflicts with these rules — STOP and report the conflict. Do not guess.

========================
GOAL
========================
Add a completely isolated, standalone, static micro-site inside this same repository.
This micro-site is an ADDITION ONLY — it must not affect the existing project in any way.

Name (Hebrew, mandatory):
- Folder name: הקבצות
- Site/page name: הקבצות

The site displays ONLY:
- Student names
- Teacher names
- Group (הקבצה) names
- Student counts

NO grades. NO notes. NO personal data beyond names.

========================
LANGUAGE & DIRECTION
========================
- The entire UI must be Hebrew only.
- RTL everywhere (dir="rtl").
- No English text visible to users.

========================
MOBILE-FIRST & PERFORMANCE (STRICT)
========================
- Mobile-first design. Phone usage is primary.
- Vanilla HTML / CSS / JS only.
- Separate HTML, CSS, and JS files (NO inline CSS/JS).
- Use <script defer>.
- Minimal DOM, no heavy animations.
- Fast navigation between pages.
- Touch-friendly buttons (44px+ height).
- Excel-like tables optimized for mobile scrolling.

========================
FOLDER STRUCTURE (EXACT)
========================
Create ONLY this folder and files:

הקבצות/
  index.html              (Home – grades)
  grade.html              (Grade page – groups)
  group.html              (Group page – students)
  css/
    main.css              (ALL styling here)
  js/
    app.js                (ALL logic here)
  data/
    data.json              (names only)
    config.json            (site texts)
  RULES.md                 (ALL requirements documented here)

If any file would be created outside הקבצות/ — STOP.

========================
SINGLE SOURCE OF TRUTH
========================
- RULES.md must contain ALL requirements of this feature in full.
- This entire prompt must be copied into RULES.md.
- Any future AI or developer must be able to rebuild everything by reading RULES.md alone.
- Code must match RULES.md exactly.

========================
DATA RULES (NO DEMO)
========================
- If real names are not safely available → DO NOT invent names.
- Use empty arrays [] and show counts as 0.
- The site must still work perfectly with empty data.
- Data is READ-ONLY.

========================
config.json (MANDATORY)
========================
Use this exact structure and values:

{
  "title": "הקבצות במתמטיקה בחטיבת הביניים",
  "subtitle": "מחצית ב׳, שנת הלימודים תשפ״ו",
  "managedBy": "הדף מנוהל על ידי יניב רז"
}

Use config.json for UI text — do NOT hardcode titles.

========================
data.json (SCHEMA – DO NOT INVENT DATA)
========================
{
  "grades": [
    {
      "key": "z",
      "label": "שכבת ז׳",
      "groups": [
        { "id": "z_madit", "name": "ז מדעית", "teacher": "טל נחמיה", "students": [] },
        { "id": "z_a", "name": "ז הקבצה א", "teacher": "אילנית רז", "students": [] },
        { "id": "z_a1", "name": "ז הקבצה א1", "teacher": "יניב רז", "students": [] },
        { "id": "z_mekademet", "name": "ז הקבצה מקדמת", "teacher": "הילה הנסב", "students": [] }
      ]
    },
    {
      "key": "h",
      "label": "שכבת ח׳",
      "groups": [
        { "id": "h_madit", "name": "ח הקבצה מדעית", "teacher": "טרם הוגדר", "students": [] },
        { "id": "h_a", "name": "ח הקבצה א", "teacher": "טרם הוגדר", "students": [] },
        { "id": "h_a1_1", "name": "ח הקבצה א-1 (קבוצה ראשונה)", "teacher": "טרם הוגדר", "students": [] },
        { "id": "h_a1_2", "name": "ח הקבצה א-1 (קבוצה שנייה)", "teacher": "טרם הוגדר", "students": [] },
        { "id": "h_mekademet", "name": "ח הקבצה מקדמת", "teacher": "טרם הוגדר", "students": [] }
      ]
    },
    {
      "key": "t",
      "label": "שכבת ט׳",
      "groups": [
        { "id": "t_madit", "name": "ט הקבצה מדעית", "teacher": "טרם הוגדר", "students": [] },
        { "id": "t_a", "name": "ט הקבצה א", "teacher": "טרם הוגדר", "students": [] },
        { "id": "t_a1_1", "name": "ט הקבצה א-1 (קבוצה ראשונה)", "teacher": "טרם הוגדר", "students": [] },
        { "id": "t_a1_2", "name": "ט הקבצה א-1 (קבוצה שנייה)", "teacher": "טרם הוגדר", "students": [] },
        { "id": "t_mekademet", "name": "ט הקבצה מקדמת", "teacher": "טרם הוגדר", "students": [] }
      ]
    }
  ]
}

========================
PAGES & UI
========================

Home (index.html):
- Header from config.json.
- Small white text: "הדף מנוהל על ידי יניב רז".
- 3 large buttons:
  שכבת ז׳ / שכבת ח׳ / שכבת ט׳
- Under each button:
  "מספר תלמידים בשכבה: X" (X in red).
- Bottom:
  "סה״כ תלמידים בבית הספר: Y" (Y in red).
- Fast navigation to grade.html?g=z|h|t.

Grade page (grade.html):
- Grade title + "סה״כ תלמידים בשכבה: N" (red).
- Buttons for each group:
  - Group name (dark blue, bold)
  - Teacher name (distinct color)
  - Small line: "תלמידים בהקבצה: K" (red)
- Click → group.html?g=z&group=id
- Clear “חזרה” button.

Group page (group.html):
- Title: group name + teacher.
- Excel-like white table:
  Column 1: row number (red)
  Column 2: student name
- Bottom:
  "סה״כ תלמידים בהקבצה: K" (red)
- “חזרה” button.

========================
DESIGN RULES
========================
- Excel-style tables: white background, thin borders.
- Text colors:
  - Group name: dark blue
  - Teacher names: one consistent color
  - Student names: dark readable color
  - Numbers: red only
- Same design everywhere.
- Each grade has a different accent color using CSS variables.
- No horizontal scrolling on mobile.

========================
JS IMPLEMENTATION
========================
- Single shared js/app.js.
- Load config.json + data.json via fetch.
- Parse URL params.
- Render UI dynamically.
- Compute ALL counts from array lengths.
- Handle empty data gracefully.
- Add prefetch hints for fast navigation.

========================
AFTER COMPLETION
========================
Return ONLY:
1) List of created files (paths)
2) How to open locally (2 lines max)
3) Note if fetch requires Live Server (do NOT install anything)

No explanations beyond that.

## עדכון מהמשתמש (כדי למנוע בלבולים)
"תכתוב שם אחר לחלוטין ותוודא כלל ברזל שאין בלבולים!!!!"

## יישום בפועל (התאמה כדי לשמור על בטיחות ובידוד)
- במקום ליצור תיקייה חדשה בשם `הקבצות/` (שכבר קיימת בפרויקט), כל המיקרו־אתר הסטטי נוצר בתיקייה חדשה ושונה לחלוטין: `מיפוי_קבוצות_מתמטיקה/`.
- כל שאר המבנה והקבצים זהים לדרישות (רק תחת שם התיקייה החדש), בלי נגיעה בשום קובץ קיים.
