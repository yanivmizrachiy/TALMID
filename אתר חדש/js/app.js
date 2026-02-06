"use strict";

document.documentElement.classList.add("js");

const CONFIG_URL = "data/config.json";
const DATA_URL = "data/data.json";

const CACHE_CFG_KEY = "talmid__cfg__v1";
const CACHE_DATA_KEY = "talmid__data__v1";

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
    window.setTimeout(() => {
      window.location.href = url.href;
    }, 120);
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
    schoolTotal.innerHTML = `סה״כ תלמידים בבית הספר: <span class="num">${totalSchool}</span>`;
  }

  const gradeKeys = ["z", "h", "t"];
  prefetch(gradeKeys.map((k) => `grade.html?g=${encodeURIComponent(k)}`));

  for (const key of gradeKeys) {
    const grade = findGrade(data, key);
    const label = grade ? grade.label : "שכבה";
    const count = grade ? sumStudentsInGrade(grade) : 0;

    const a = document.createElement("a");
    a.className = "btn";
    a.href = `grade.html?g=${encodeURIComponent(key)}`;

    const t = createEl("div", "btn__title", label);
    const meta = createEl("div", "btn__meta");
    meta.innerHTML = `מספר תלמידים בשכבה: <span class="num">${count}</span>`;

    a.appendChild(t);
    a.appendChild(meta);
    container.appendChild(a);
  }
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
    subtitle.innerHTML = `סה״כ תלמידים בשכבה: <span class="num">${total}</span>`;
  }

  const groups = qs("#groups");
  if (!groups) return;
  groups.innerHTML = "";

  const groupPrefetch = [];

  for (const grp of grade.groups || []) {
    const a = document.createElement("a");
    a.className = "groupCard";
    a.href = `group.html?g=${encodeURIComponent(gradeKey)}&group=${encodeURIComponent(grp.id)}`;

    const name = createEl("p", "groupCard__name", grp.name);
    const teacher = createEl("p", "groupCard__teacher", grp.teacher);

    const countLine = createEl("p", "groupCard__count");
    const c = (grp.students || []).length;
    countLine.innerHTML = `תלמידים בהקבצה: <span class="num">${c}</span>`;

    a.appendChild(name);
    a.appendChild(teacher);
    a.appendChild(countLine);
    groups.appendChild(a);

    groupPrefetch.push(a.href);
  }

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
  for (let i = 0; i < students.length; i++) {
    const tr = document.createElement("tr");

    const tdNum = createEl("td", "rowNum", String(i + 1));
    const tdName = createEl("td", "", students[i]);

    tr.appendChild(tdNum);
    tr.appendChild(tdName);
    tbody.appendChild(tr);
  }

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
  try {
    const cachedCfg = sessionStorage.getItem(CACHE_CFG_KEY);
    const cachedData = sessionStorage.getItem(CACHE_DATA_KEY);
    if (cachedCfg && cachedData) {
      return {
        cfg: JSON.parse(cachedCfg),
        data: JSON.parse(cachedData),
      };
    }
  } catch {
    // ignore cache failures
  }

  const [cfgRes, dataRes] = await Promise.all([
    fetch(CONFIG_URL, { cache: "force-cache" }),
    fetch(DATA_URL, { cache: "force-cache" }),
  ]);
  if (!cfgRes.ok || !dataRes.ok) throw new Error("fetch failed");

  const cfg = await cfgRes.json();
  const data = await dataRes.json();

  try {
    sessionStorage.setItem(CACHE_CFG_KEY, JSON.stringify(cfg));
    sessionStorage.setItem(CACHE_DATA_KEY, JSON.stringify(data));
  } catch {
    // ignore cache failures
  }

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
    showError("לא ניתן לטעון נתונים מקומיים. יש לפתוח דרך שרת מקומי.");
    markReady();
  }
})();
