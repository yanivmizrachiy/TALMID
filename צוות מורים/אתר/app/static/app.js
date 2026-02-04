(() => {
  function normalizeText(s) {
    return (s || "")
      .toString()
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function attachTableFilter(input) {
    const tableId = input.getAttribute("data-filter-table");
    if (!tableId) return;

    const table = document.getElementById(tableId);
    if (!table) return;

    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll("tr[data-row]"));

    const countId = input.getAttribute("data-filter-count");
    const countEl = countId ? document.getElementById(countId) : null;

    function update() {
      const q = normalizeText(input.value);
      let visible = 0;
      for (const row of rows) {
        const text = normalizeText(row.textContent);
        const ok = q === "" || text.includes(q);
        row.style.display = ok ? "" : "none";
        if (ok) visible += 1;
      }
      if (countEl) countEl.textContent = String(visible);
    }

    input.addEventListener("input", update);
    update();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const inputs = Array.from(document.querySelectorAll("input[data-filter-table]"));
    for (const input of inputs) attachTableFilter(input);
  });
})();
