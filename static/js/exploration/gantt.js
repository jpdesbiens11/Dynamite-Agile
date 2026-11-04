/* Exploration - Gantt drawing (D-B-019): one SVG per row, so the timeline
   lines up with the table cells and stays printable. Colours come from CSS
   classes (the CSP forbids inline styles): planned, done, late, blocked,
   milestone, phase summary, today line. */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const DAY = 86400000;
  const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  // "fit": px per day computed by the screen so the whole plan fits (exploration.js).
  const SCALES = { fit: { px: 2, label: "Tout le plan" }, week: { px: 4, label: "Semaines" }, month: { px: 1.4, label: "Mois" } };
  const ROW_H = 30;

  function svg(tag, attrs, ...children) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => { if (v !== null && v !== undefined) node.setAttribute(k, String(v)); });
    children.flat().forEach((c) => { if (c !== null && c !== undefined) node.append(c instanceof Node ? c : document.createTextNode(String(c))); });
    return node;
  }

  const parse = (iso) => new Date(iso + "T00:00:00Z");
  const iso = (date) => date.toISOString().slice(0, 10);
  const days = (a, b) => Math.round((b - a) / DAY);

  /* Visible window: from the Monday of the plan start to two weeks after the last end. */
  function range(tasks, startIso, todayIso) {
    let first = parse(startIso);
    first = new Date(first.getTime() - ((first.getUTCDay() + 6) % 7) * DAY);
    let last = new Date(first.getTime() + 12 * 7 * DAY);
    tasks.forEach((t) => { const e = parse(t.end); if (e > last) last = e; });
    const today = parse(todayIso);
    if (today > last && days(last, today) < 90) last = today;
    last = new Date(last.getTime() + 14 * DAY);
    return { first, last, today, total: days(first, last) };
  }

  function width(r, scale) { return Math.ceil(r.total * SCALES[scale].px); }
  function x(r, scale, date) { return days(r.first, date) * SCALES[scale].px; }

  function header(r, scale) {
    const px = SCALES[scale].px, w = width(r, scale);
    const root = svg("svg", { class: "ex-gantt-head", width: w, height: 38, viewBox: "0 0 " + w + " 38",
      "aria-hidden": "true" });
    // Months (top band).
    let m = new Date(Date.UTC(r.first.getUTCFullYear(), r.first.getUTCMonth(), 1));
    while (m < r.last) {
      const next = new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 1));
      const x0 = Math.max(0, x(r, scale, m)), x1 = Math.min(w, x(r, scale, next));
      root.append(svg("line", { class: "ex-grid-month", x1: x0, x2: x0, y1: 0, y2: 38 }));
      if (x1 - x0 > 26) {
        const label = MONTHS[m.getUTCMonth()] + ((m.getUTCMonth() === 0 || x0 === 0) && x1 - x0 > 62 ? " " + m.getUTCFullYear() : "");
        root.append(svg("text", { class: "ex-head-month", x: x0 + 4, y: 14 }, label));
      }
      m = next;
    }
    // Weeks (bottom band) in week scale: Monday's day number.
    if (px >= 2.5) {
      for (let d = new Date(r.first); d < r.last; d = new Date(d.getTime() + 7 * DAY)) {
        const xx = x(r, scale, d);
        root.append(svg("line", { class: "ex-grid-week", x1: xx, x2: xx, y1: 20, y2: 38 }),
          svg("text", { class: "ex-head-week", x: xx + 3, y: 32 }, String(d.getUTCDate())));
      }
    }
    if (r.today >= r.first && r.today <= r.last) {
      const t = x(r, scale, r.today);
      root.append(svg("line", { class: "ex-today", x1: t, x2: t, y1: 18, y2: 38 }));
    }
    root.append(svg("title", null, "1 semaine = " + 7 * px + " px"));
    return root;
  }

  function background(root, r, scale) {
    const w = width(r, scale);
    let m = new Date(Date.UTC(r.first.getUTCFullYear(), r.first.getUTCMonth(), 1));
    while (m < r.last) {
      const xx = x(r, scale, m);
      if (xx > 0) root.append(svg("line", { class: "ex-grid-month", x1: xx, x2: xx, y1: 0, y2: ROW_H }));
      m = new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 1));
    }
    if (r.today >= r.first && r.today <= r.last) {
      const t = x(r, scale, r.today);
      root.append(svg("line", { class: "ex-today", x1: t, x2: t, y1: 0, y2: ROW_H }));
    }
    return w;
  }

  function stateOf(task) {
    if (task.status === "done") return "done";
    if (task.late) return "late";
    if (task.status === "blocked") return "blocked";
    return "planned";
  }

  function bar(task, r, scale) {
    const w = width(r, scale);
    const root = svg("svg", { class: "ex-gantt-row", width: w, height: ROW_H, viewBox: "0 0 " + w + " " + ROW_H });
    background(root, r, scale);
    const s = parse(task.start), e = parse(task.end);
    const x0 = x(r, scale, s), x1 = x(r, scale, e);
    const tip = task.code + " — " + task.title + "\n" + task.start + " → " + task.end + " · " + task.status_label
      + (task.late ? " · en retard" : "") + (task.owner_name ? " · " + task.owner_name : "");
    if (Number(task.duration_weeks) === 0) {
      const cx = x0, cy = ROW_H / 2, k = 7;
      root.append(svg("path", { class: "ex-milestone ex-" + stateOf(task), d: "M" + cx + " " + (cy - k) + " L" + (cx + k) + " " + cy
        + " L" + cx + " " + (cy + k) + " L" + (cx - k) + " " + cy + " Z" }, svg("title", null, tip)));
      return root;
    }
    const bw = Math.max(3, x1 - x0);
    const g = svg("g", { class: "ex-bar ex-" + stateOf(task) },
      svg("rect", { class: "ex-bar-bg", x: x0, y: 7, width: bw, height: ROW_H - 14, rx: 4 }),
      task.progress > 0 && task.status !== "done"
        ? svg("rect", { class: "ex-bar-progress", x: x0, y: 7, width: Math.max(2, bw * task.progress / 100), height: ROW_H - 14, rx: 4 })
        : null,
      svg("title", null, tip));
    root.append(g);
    if (bw > 60 && task.owner_name) {
      root.append(svg("text", { class: "ex-bar-label", x: x0 + 6, y: ROW_H / 2 + 4 }, task.owner_name.split(" ")[0]));
    }
    return root;
  }

  function phaseBar(tasks, r, scale) {
    const w = width(r, scale);
    const root = svg("svg", { class: "ex-gantt-row", width: w, height: ROW_H, viewBox: "0 0 " + w + " " + ROW_H });
    background(root, r, scale);
    if (!tasks.length) return root;
    const s = tasks.map((t) => parse(t.start)).reduce((a, b) => (a < b ? a : b));
    const e = tasks.map((t) => parse(t.end)).reduce((a, b) => (a > b ? a : b));
    const x0 = x(r, scale, s), x1 = Math.max(x0 + 3, x(r, scale, e));
    root.append(svg("path", { class: "ex-phase-bar", d: "M" + x0 + " 10 H" + x1 + " V20 L" + (x1 - 5) + " 15 H" + (x0 + 5)
      + " L" + x0 + " 20 Z" }, svg("title", null, iso(s) + " → " + iso(e))));
    return root;
  }

  DA.exploration = Object.assign(DA.exploration || {}, { gantt: { range, header, bar, phaseBar, SCALES, stateOf } });
})();
