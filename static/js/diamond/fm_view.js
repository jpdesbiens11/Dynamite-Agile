/* Diamond · DFMEA: reading the table (0.60.110, D-O-123). Called by dfmea.js after each drawing of the table:
   - compact rows: a long cell shows 2 lines; the chevron of a row (▸ / ▾) unfolds it in full, « Tout déplier » and
     « Tout replier » do every row; kept per viewer in this browser (localStorage), never sent to the server;
   - the horizontal scroll bar pinned to the bottom of the window, the tools / Function / Failure Mode columns kept on
     the left, Shift + wheel sideways, full screen (fm_scroll.js);
   - the magnifier (« Loupe »): off by default; on, the cell under the pointer shows in a larger floating card with its
     column, without catching the clicks; from the keyboard, a cell (Tab) + Enter opens the same card, Esc closes it;
   - « Essentiel »: the columns that carry the failure chain, one click (the « Colonnes » menu keeps the detail).
   Editing is untouched: the inputs and their saves are those of dfmea_table.js. */
(function () {
  "use strict";

  const { el } = DA;
  const D = DA.diamond;
  const FOLD = "diamond.dfmea.fold.", LOUPE = "diamond.dfmea.loupe";

  function read(key, fallback) {
    try { const v = JSON.parse(localStorage.getItem(key) || "null"); return v === null ? fallback : v; } catch (err) { return fallback; }
  }
  function write(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (err) { /* private window: not kept */ }
  }

  /* the fold state of a Space: {all: rows open by default?, ids: the rows that differ} */
  function foldState(space) {
    const s = read(FOLD + space, null);
    return s && typeof s === "object" && Array.isArray(s.ids) ? { all: !!s.all, ids: s.ids.map(Number) } : { all: false, ids: [] };
  }
  const isOpen = (s, id) => s.all !== s.ids.includes(Number(id));
  function setOpen(space, s, id, open) {
    const ids = s.ids.filter((x) => x !== Number(id));
    if (open !== s.all) ids.push(Number(id));
    const next = { all: s.all, ids };
    write(FOLD + space, next);
    return next;
  }
  function setAll(space, open) {
    const next = { all: !!open, ids: [] };
    write(FOLD + space, next);
    return next;
  }

  /* where the card goes: right of / below the pointer, flipped and clamped so that it stays in the window */
  function place(x, y, w, h, vw, vh) {
    const gap = 18, edge = 8;
    let left = x + gap, top = y + gap;
    if (left + w > vw - edge) left = x - gap - w;
    if (top + h > vh - edge) top = y - gap - h;
    left = Math.max(edge, Math.min(left, vw - w - edge));
    top = Math.max(edge, Math.min(top, vh - h - edge));
    return { left: Math.round(left), top: Math.round(top) };
  }

  function fit(area) {
    area.style.height = "auto";
    area.style.height = (area.scrollHeight + 2) + "px";
  }
  function applyRow(tr, open) {
    if (open) tr.setAttribute("data-fold", "open"); else tr.removeAttribute("data-fold");
    const btn = tr.querySelector(".dm-fv-fold");
    if (btn) {
      const line = btn.getAttribute("data-line");
      btn.setAttribute("aria-expanded", String(open));
      btn.textContent = open ? "▾" : "▸";
      btn.setAttribute("aria-label", (open ? "Replier la ligne " : "Déplier la ligne ") + line);
      btn.setAttribute("data-tip", open ? "Replier : 2 lignes par cellule" : "Déplier : tout le texte de la ligne");
    }
    tr.querySelectorAll("td.dm-fm-c textarea").forEach((a) => { if (open) fit(a); else a.style.height = ""; });
  }

  /* the text of a cell, as the reader sees it: the value of its fields, else its text without the [new] badges */
  function cellText(td) {
    const parts = [];
    td.querySelectorAll("textarea, input[type=text], input[type=date], select").forEach((f) => {
      const v = f.tagName === "SELECT" ? (f.selectedOptions[0] ? f.selectedOptions[0].textContent : "") : f.value;
      if (String(v).trim() && !/^—/.test(String(v).trim())) parts.push(String(v).trim());
    });
    if (!parts.length) {
      const copy = td.cloneNode(true);
      copy.querySelectorAll(".new-tag, button").forEach((n) => n.remove());
      const t = (copy.textContent || "").replace(/\s+\n/g, "\n").trim();
      if (t && t !== "—") parts.push(t);
    }
    return parts.join("\n");
  }
  function columnName(td) {
    const k = [...td.classList].find((c) => c.startsWith("dm-fm-k-"));
    const col = k && (D.DFMEA_COLS || []).find((c) => c.key === k.slice(8));
    if (col) return col.label;
    const table = td.closest("table"), th = table && table.tHead && table.tHead.rows[0].cells[td.cellIndex];
    return th ? th.textContent.replace("[new]", "").trim() : "";
  }

  let card = null;
  function loupeCard() {
    if (card && card.isConnected) return card;
    card = el("div", { class: "dm-fv-loupe", role: "tooltip", id: "dm-fv-loupe", hidden: true },
      el("div", { class: "dm-fv-loupe-h" }), el("div", { class: "dm-fv-loupe-t" }));
    document.body.append(card);
    return card;
  }
  function hideLoupe() {
    if (card) card.hidden = true;
    document.querySelectorAll("td[aria-describedby='dm-fv-loupe']").forEach((td) => td.removeAttribute("aria-describedby"));
  }
  function showLoupe(td, x, y) {
    const text = cellText(td);
    if (!text) { hideLoupe(); return false; }
    const c = loupeCard(), tr = td.closest("tr"), code = tr && tr.querySelector(".dm-code");
    DA.clear(c.firstChild);  // « Ligne » alone in its node: the English display translates it
    c.firstChild.append(code ? el("span", null, "Ligne ") : "", code ? code.textContent + " · " : "", columnName(td));
    c.lastChild.textContent = text;
    c.hidden = false;
    const at = place(x, y, c.offsetWidth, c.offsetHeight, window.innerWidth, window.innerHeight);
    c.style.left = at.left + "px";
    c.style.top = at.top + "px";
    return true;
  }

  function loupe(table, on) {
    table.classList.toggle("dm-fv-loupe-on", on);
    table.querySelectorAll("td.dm-fm-c").forEach((td) => { if (on) td.tabIndex = 0; else td.removeAttribute("tabindex"); });
    if (!on) hideLoupe();
  }
  function wireLoupe(table) {
    let timer = 0, over = null, px = 0, py = 0;
    table.addEventListener("mousemove", (ev) => {
      if (!table.classList.contains("dm-fv-loupe-on")) return;
      const td = ev.target.closest && ev.target.closest("td.dm-fm-c");
      px = ev.clientX; py = ev.clientY;
      if (td !== over) {
        over = td;
        clearTimeout(timer);
        if (!td) { hideLoupe(); return; }
        timer = setTimeout(() => { if (over === td) showLoupe(td, px, py); }, 90);
      } else if (td && card && !card.hidden) {
        const at = place(px, py, card.offsetWidth, card.offsetHeight, window.innerWidth, window.innerHeight);
        card.style.left = at.left + "px";
        card.style.top = at.top + "px";
      }
    });
    table.addEventListener("mouseleave", () => { over = null; clearTimeout(timer); hideLoupe(); });
    table.addEventListener("keydown", (ev) => {
      const td = ev.target;
      if (!table.classList.contains("dm-fv-loupe-on") || !td.matches || !td.matches("td.dm-fm-c")) return;
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        if (card && !card.hidden && td.getAttribute("aria-describedby")) { hideLoupe(); return; }
        const r = td.getBoundingClientRect();
        if (showLoupe(td, r.left, r.bottom - 12)) td.setAttribute("aria-describedby", "dm-fv-loupe");
      } else if (ev.key === "Escape") { ev.stopPropagation(); hideLoupe(); }
    });
    table.addEventListener("focusout", (ev) => { if (ev.target.matches && ev.target.matches("td.dm-fm-c")) hideLoupe(); });
  }

  function fmView(holder, state) {
    const box = holder.querySelector(".dm-fm-scroll"), table = box && box.querySelector("table.dm-fm");
    hideLoupe();  // a redraw removed the cell under the pointer
    if (!table) return;
    const space = state.key;
    let fold = foldState(space);
    table.classList.add("dm-fv-compact");
    table.querySelectorAll("tr.dm-fm-row").forEach((tr) => {
      const tools = tr.querySelector(".dm-fm-tools"), code = tools && tools.querySelector(".dm-code");
      if (!code) return;
      const btn = el("button", { type: "button", class: "dm-fv-fold", "data-line": code.textContent,
        onclick: () => { const open = !tr.hasAttribute("data-fold"); fold = setOpen(space, fold, tr.getAttribute("data-row"), open); applyRow(tr, open); } });
      const line = el("span", { class: "dm-fv-line" }, btn);
      code.before(line);
      line.append(code);
      applyRow(tr, isOpen(fold, tr.getAttribute("data-row")));
    });
    table.addEventListener("focusin", (ev) => {  // a folded cell grows while it is edited, then folds back
      const a = ev.target;
      if (a.tagName === "TEXTAREA" && !a.closest("tr").hasAttribute("data-fold")) fit(a);
    });
    table.addEventListener("focusout", (ev) => {
      const a = ev.target;
      if (a.tagName === "TEXTAREA" && !a.closest("tr").hasAttribute("data-fold")) a.style.height = "";
    });
    table.addEventListener("input", (ev) => {
      const a = ev.target;
      if (a.tagName === "TEXTAREA" && (a.closest("tr").hasAttribute("data-fold") || a === document.activeElement)) fit(a);
    });
    const mark = document.createComment("dfmea");
    box.before(mark);
    const wrap = D.fmScroller(box);
    mark.replaceWith(wrap);
    D.fmStick(wrap, ["function_id", "failure_mode"]);
    wireLoupe(table);
    const on = !!read(LOUPE, false);
    loupe(table, on);

    const all = (open) => {
      fold = setAll(space, open);
      table.querySelectorAll("tr.dm-fm-row").forEach((tr) => applyRow(tr, open));
    };
    const lens = el("button", { type: "button", class: "btn btn-small dm-fv-lens", "aria-pressed": String(on), "data-new": "0.60.110-fm-loupe",
      "data-tip": "Au survol, la cellule s'affiche en grand avec son titre de colonne. Au clavier : Tab jusqu'à la cellule, puis Entrée",
      onclick: () => { const now = lens.getAttribute("aria-pressed") !== "true"; lens.setAttribute("aria-pressed", String(now)); write(LOUPE, now); loupe(table, now); } },
    DA.icon ? DA.icon("search") : null, "Loupe");
    const full = el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.110-fm-full" },
      el("span", { class: "dm-fv-full-label" }, holder.classList.contains("dm-fv-full") ? "Quitter le plein écran" : "Plein écran"));
    D.fmFull(holder, full);
    const ess = state.essential || [];
    const isEss = ess.length && state.visible.size === ess.length && ess.every((k) => state.visible.has(k));
    const essential = state.setColumns ? el("button", { type: "button", class: "btn btn-small", "aria-pressed": String(!!isEss), "data-new": "0.60.110-fm-essential",
      "data-tip": isEss ? "Revenir à toutes les colonnes" : "Function, Failure Mode, Effect, S, Cause, O, Prevention, Detection, D, AP, Actions",
      onclick: () => state.setColumns(isEss ? null : ess) }, "Essentiel") : null;
    const group = el("div", { class: "dm-actions dm-fv-tools", role: "group", "aria-label": "Affichage du tableau" },
      el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.110-fm-unfold", "data-tip": "Tout le texte de chaque ligne", onclick: () => all(true) }, "Tout déplier"),
      el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.110-fm-fold", "data-tip": "2 lignes par cellule : plus de lignes à l'écran", onclick: () => all(false) }, "Tout replier"),
      essential, lens, full);
    const bar = holder.querySelector(".dm-fm-toolbar");
    if (bar) bar.append(group);
  }

  DA.diamond = Object.assign(DA.diamond || {}, { fmView, fmFold: { foldState, isOpen, setOpen, setAll }, fmPlace: place });
})();
