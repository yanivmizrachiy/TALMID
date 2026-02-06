"use strict";

document.documentElement.classList.add("js");

const CONFIG_URL = "data/config.json";
const DATA_URL = "data/data.json";

const FETCH_TIMEOUT_MS = 12000;

// Performance: cache JSON in sessionStorage for a short TTL.
// This makes navigation (home → grade → group) feel instant, while still
// fetching fresh data regularly so the site stays up-to-date.
const SESSION_CACHE_KEY = "talmid_json_cache_v1";
const SESSION_CACHE_TTL_MS = 90 * 1000;

// Keep a stable cache-bust token for a limited time to make prefetch useful.
const SESSION_BUST_KEY = "talmid_bust_v1";
const SESSION_BUST_TTL_MS = 10 * 60 * 1000;

function readSessionJSON(key) {
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function writeSessionJSON(key, value) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore (private mode / storage quota / disabled storage).
  }
}

function getSessionBust() {
  const now = Date.now();
  const cached = readSessionJSON(SESSION_BUST_KEY);
  if (cached && typeof cached.v === "number" && typeof cached.ts === "number") {
    if (now - cached.ts <= SESSION_BUST_TTL_MS) return cached.v;
  }
  const v = now;
  writeSessionJSON(SESSION_BUST_KEY, { v, ts: now });
  return v;
}

function markEntering() {
  document.body.classList.add("is-entering");
}

function markReady() {
  requestAnimationFrame(() => {
    document.body.classList.remove("is-entering");
    document.body.classList.add("is-ready");
  });
}

function installFastNav() {
  document.addEventListener("click", (ev) => {
    const a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
    if (!a) return;

    if (ev.defaultPrevented) return;
    if (ev.button !== 0) return;
    if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    if (a.target && a.target !== "_self") return;
    if (a.hasAttribute("download")) return;

    const href = a.getAttribute("href") || "";
    if (!href || href.startsWith("#")) return;

    let url;
    try {
      url = new URL(href, window.location.href);
    } catch {
      return;
    }

    if (url.origin !== window.location.origin) return;
    if (!url.pathname.endsWith(".html")) return;

    ev.preventDefault();
    document.body.classList.add("is-leaving");
    // Keep the delay extremely short so navigation feels instant.
    window.setTimeout(() => {
      window.location.href = url.href;
    }, 60);
  });
}

function qs(sel) {
  return document.querySelector(sel);
}

function getParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    gradeKey: params.get("g") || "",
    groupId: params.get("group") || "",
  };
}

function setGradeAccent(gradeKey) {
  const body = document.body;
  body.setAttribute("data-grade", gradeKey || "");
}

function safeText(el, text) {
  if (!el) return;
  el.textContent = String(text ?? "");
}

function showError(message) {
  const err = qs("#error");
  if (!err) return;
  err.hidden = false;
  err.textContent = message;
}

function hideError() {
  const err = qs("#error");
  if (!err) return;
  err.hidden = true;
  err.textContent = "";
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const t = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(t);
  }
}

function prefetch(urls) {
  const head = document.head;
  const existing = new Set(
    Array.from(head.querySelectorAll('link[rel="prefetch"]')).map((l) => l.getAttribute("href"))
  );

  for (const href of urls) {
    if (!href || existing.has(href)) continue;
    const link = document.createElement("link");
    link.rel = "prefetch";
    link.href = href;
    head.appendChild(link);
    existing.add(href);
  }
}

function startHomeClock() {
  const timeEl = qs("#clock-time");
  const dateEl = qs("#clock-date");
  if (!timeEl || !dateEl) return;

  const fmtTime = new Intl.DateTimeFormat("he-IL", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  const fmtDate = new Intl.DateTimeFormat("he-IL", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });

  const tick = () => {
    const now = new Date();
    safeText(timeEl, fmtTime.format(now));
    safeText(dateEl, fmtDate.format(now));
  };

  tick();
  window.setInterval(tick, 1000);
}

function sumStudentsInGrade(grade) {
  return (grade.groups || []).reduce((acc, grp) => acc + (grp.students || []).length, 0);
}

function sumAllStudents(data) {
  return (data.grades || []).reduce((acc, grade) => acc + sumStudentsInGrade(grade), 0);
}

function findGrade(data, gradeKey) {
  return (data.grades || []).find((g) => g.key === gradeKey) || null;
}

function findGroup(grade, groupId) {
  return (grade.groups || []).find((gr) => gr.id === groupId) || null;
}

function createEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function withBPrefix(label) {
  const s = String(label || "").trim();
  if (!s) return "";
  // Hebrew usually attaches the prefix (בכיתה, בהקבצה, בחטיבה).
  // For Latin/digits, keep a space for readability.
  return /^[A-Za-z0-9]/.test(s) ? `ב ${s}` : `ב${s}`;
}

function normalizeGroupLabelForCount(name) {
  const s = String(name || "").trim();
  if (!s) return s;

  // Many group names start with the grade letter (ז/ח/ט). For the sentence
  // "תלמידים לומדים ב…" we prefer "בהקבצה …" rather than "בח …".
  const m = s.match(/^([זחט])\s+(.*)$/);
  if (!m) return s;

  const rest = m[2].trim();
  if (!rest) return s;
  if (rest === "מדעית") return "הקבצה מדעית";
  return rest;
}

function renderHome(cfg, data) {
  setGradeAccent("");

  safeText(qs("#cfg-title"), cfg.title);
  safeText(qs("#cfg-subtitle"), cfg.subtitle);
  safeText(qs("#cfg-managed"), cfg.managedBy);

  const container = qs("#grade-buttons");
  if (!container) return;
  container.innerHTML = "";

  const totalSchool = sumAllStudents(data);
  const schoolTotal = qs("#school-total");
  if (schoolTotal) {
    schoolTotal.innerHTML = `<span class="num">${totalSchool}</span> תלמידים לומדים בחטיבת הביניים`;
  }

  const gradeKeys = ["z", "h", "t"];
  prefetch(gradeKeys.map((k) => `grade.html?g=${encodeURIComponent(k)}`));

  const frag = document.createDocumentFragment();

  for (const key of gradeKeys) {
    const grade = findGrade(data, key);
    const label = grade ? grade.label : "שכבה";
    const count = grade ? sumStudentsInGrade(grade) : 0;

    const a = document.createElement("a");
    a.className = "btn";
    a.setAttribute("data-grade", key);
    a.href = `grade.html?g=${encodeURIComponent(key)}`;

    const t = createEl("div", "btn__title", label);
    const meta = createEl("div", "btn__meta");
    meta.innerHTML = `<span class="num">${count}</span> תלמידים לומדים ב${label}`;

    a.appendChild(t);
    a.appendChild(meta);
    frag.appendChild(a);
  }

  container.appendChild(frag);
}

function renderGrade(cfg, data, gradeKey) {
  setGradeAccent(gradeKey);

  const grade = findGrade(data, gradeKey);
  if (!grade) {
    showError("שכבה לא נמצאה");
    return;
  }

  const total = sumStudentsInGrade(grade);
  safeText(qs("#grade-title"), grade.label);

  const subtitle = qs("#grade-subtitle");
  if (subtitle) {
    subtitle.innerHTML = `<span class="num">${total}</span> תלמידים לומדים ${withBPrefix(grade.label)}`;
  }

  const groups = qs("#groups");
  if (!groups) return;
  groups.innerHTML = "";

  const groupPrefetch = [];

  const frag = document.createDocumentFragment();

  for (const grp of grade.groups || []) {
    const a = document.createElement("a");
    a.className = "groupCard";
    a.href = `group.html?g=${encodeURIComponent(gradeKey)}&group=${encodeURIComponent(grp.id)}`;

    const name = createEl("p", "groupCard__name", grp.name);
    const teacher = createEl("p", "groupCard__teacher", grp.teacher);

    const countLine = createEl("p", "groupCard__count");
    const c = (grp.students || []).length;
    const groupLabelForCount = normalizeGroupLabelForCount(grp.name);
    countLine.innerHTML = `<span class="num">${c}</span> תלמידים לומדים ${withBPrefix(groupLabelForCount)}`;

    a.appendChild(name);
    a.appendChild(teacher);
    a.appendChild(countLine);
    frag.appendChild(a);

    groupPrefetch.push(a.href);
  }

  groups.appendChild(frag);

  prefetch(groupPrefetch);

  const back = qs("#back");
  if (back) back.href = "index.html";

  document.title = cfg.title;
}

function renderGroup(cfg, data, gradeKey, groupId) {
  setGradeAccent(gradeKey);

  const grade = findGrade(data, gradeKey);
  if (!grade) {
    showError("שכבה לא נמצאה");
    return;
  }

  const grp = findGroup(grade, groupId);
  if (!grp) {
    showError("הקבצה לא נמצאה");
    return;
  }

  safeText(qs("#group-title"), grp.name);
  safeText(qs("#group-subtitle"), grp.teacher);

  const tbody = qs("#students");
  if (!tbody) return;
  tbody.innerHTML = "";

  const students = grp.students || [];
  const frag = document.createDocumentFragment();
  for (let i = 0; i < students.length; i++) {
    const tr = document.createElement("tr");

    const tdNum = createEl("td", "rowNum", String(i + 1));
    const tdName = createEl("td", "", students[i]);

    tr.appendChild(tdNum);
    tr.appendChild(tdName);
    frag.appendChild(tr);
  }

  tbody.appendChild(frag);

  const totalEl = qs("#group-total");
  if (totalEl) {
    totalEl.innerHTML = `סה״כ תלמידים בהקבצה: <span class="num">${students.length}</span>`;
  }

  const back = qs("#back");
  if (back) {
    back.href = `grade.html?g=${encodeURIComponent(gradeKey)}`;
  }

  document.title = cfg.title;
}

async function loadAll() {
  const now = Date.now();
  const cached = readSessionJSON(SESSION_CACHE_KEY);
  if (
    cached &&
    typeof cached.ts === "number" &&
    cached.cfg &&
    cached.data &&
    now - cached.ts <= SESSION_CACHE_TTL_MS
  ) {
    return { cfg: cached.cfg, data: cached.data };
  }

  // Fetch fresh data.
  // We still bust caches to avoid stale GitHub Pages/mobile caches, but we keep
  // a stable bust token for a short window to make revalidation cheap.
  const bust = `?v=${getSessionBust()}`;

  const [cfgRes, dataRes] = await Promise.all([
    fetchWithTimeout(`${CONFIG_URL}${bust}`, { cache: "no-cache" }),
    fetchWithTimeout(`${DATA_URL}${bust}`, { cache: "no-cache" }),
  ]);

  if (!cfgRes.ok) {
    throw new Error(`cfg fetch failed (${cfgRes.status})`);
  }
  if (!dataRes.ok) {
    throw new Error(`data fetch failed (${dataRes.status})`);
  }

  let cfg;
  let data;
  try {
    cfg = await cfgRes.json();
  } catch {
    throw new Error("cfg json parse failed");
  }
  try {
    data = await dataRes.json();
  } catch {
    throw new Error("data json parse failed");
  }

  writeSessionJSON(SESSION_CACHE_KEY, { ts: now, cfg, data });

  return { cfg, data };
}

(async function main() {
  hideError();

  markEntering();
  installFastNav();

  try {
    const { cfg, data } = await loadAll();
    const page = document.body.getAttribute("data-page") || "";
    const { gradeKey, groupId } = getParams();

    if (page === "home") {
      renderHome(cfg, data);
      startHomeClock();
      markReady();
      return;
    }

    if (page === "grade") {
      if (!gradeKey) {
        showError("חסרה שכבה בכתובת");
        markReady();
        return;
      }
      renderGrade(cfg, data, gradeKey);
      markReady();
      return;
    }

    if (page === "group") {
      if (!gradeKey || !groupId) {
        showError("חסרים פרטים בכתובת");
        markReady();
        return;
      }
      renderGroup(cfg, data, gradeKey, groupId);
      markReady();
      return;
    }

    showError("דף לא נתמך");
    markReady();
  } catch {
    if (window.location.protocol === "file:") {
      showError("לא ניתן לטעון נתונים מקומיים. יש לפתוח דרך שרת מקומי.");
    } else {
      showError("שגיאה בטעינת הנתונים. נסה לרענן את הדף.");
    }
    markReady();
  }
})();
