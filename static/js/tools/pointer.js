/* « Le pointeur » (0.60.35, D-O-043): a link that opens a page AND shows the point of interest -- a translucent red box
   that flashes around it, an arrow at 45° pointing at it from the upper right, and an optional note.
     https://<server>/?focus=EQP-12&note=Regarde+ce+requis#/goldmine/EQP/issue/12
   focus: the text to find on the page (a key, a function number, a title, a sentence); note: the bubble's text.
   The query string sits before the « # », so the router of the hash is never disturbed. Used by Partager (the selected
   text becomes the focus), the @mentions and Bob le mineur (his answers are pointer links, D-O-044).
   DA.pointTo(text, note) points on the current page; DA.pointLink(text, note, hash) builds the link. The box follows
   the target while the page scrolls; Échap, a click on × or on the page closes it. */
(function () {
  "use strict";
  const { el } = DA;
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const norm = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim();
  const BLOCK = "tr, li, article, label, h1, h2, h3, h4, p, td, th, .dm-node, .dm-card, .card, .ag-card, [data-focus]";
  let active = null;

  function visible(node) {
    if (!node || !node.getClientRects().length) return false;
    const s = getComputedStyle(node);
    return s.visibility !== "hidden" && s.display !== "none";
  }

  /* the smallest visible element of the page whose text holds the focus, widened to its row, card or paragraph */
  function find(text) {
    const root = document.getElementById("main");
    const want = norm(text);
    if (!root || !want) return null;
    const exact = root.querySelector('[data-focus="' + CSS.escape(String(text)) + '"]');
    if (exact && visible(exact)) return { box: exact, spot: exact };
    let best = null, size = Infinity;
    const consider = (node) => {
      if (!node || !visible(node)) return;
      const len = norm(node.textContent).length;
      if (len < size) { best = node; size = len; }
    };
    const texts = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) texts.push(walker.currentNode);
    texts.forEach((n) => { if (norm(n.nodeValue) === want) consider(n.parentElement); });  // « F1 » is F1, not F12
    if (!best) texts.forEach((n) => { if (norm(n.nodeValue).includes(want)) consider(n.parentElement); });
    if (!best) {  // the words run over several nodes (bold inside a sentence…)
      root.querySelectorAll("p, li, td, h1, h2, h3, label, span, div").forEach((node) => {
        if (norm(node.textContent).includes(want)) consider(node);
      });
    }
    if (!best) return null;
    const field = best.closest("input, textarea, select") ? best : null;
    const row = best.closest("tr, article, li, .dm-node, .dm-card, .card, .ag-card");  // the whole row or card first
    const block = row && norm(row.textContent).length < 1200 ? row : best.closest(BLOCK);
    return { box: field || (block && norm(block.textContent).length < 1200 ? block : best), spot: best };
  }

  function close() {
    if (!active) return;
    cancelAnimationFrame(active.frame);
    active.nodes.forEach((n) => n.remove());
    document.removeEventListener("keydown", active.key, true);
    document.removeEventListener("pointerdown", active.down, true);
    active = null;
  }

  /* found: {box: the row or card framed, spot: the very text found, where the arrow points} */
  function show(found, note) {
    close();
    const target = found.box, spot = found.spot || found.box;
    target.scrollIntoView({ block: "center", inline: "nearest", behavior: reduce() ? "auto" : "smooth" });
    const box = el("div", { class: "da-point-box", "aria-hidden": "true" });  // a passing overlay: no [new] badge on it
    const arrow = el("div", { class: "da-point-arrow", "aria-hidden": "true" }, el("span", { class: "da-point-shaft" }), el("span", { class: "da-point-head" }));
    const bubble = el("div", { class: "da-point-note", role: "status" },
      el("span", null, note || "Ici"),
      el("button", { type: "button", class: "da-point-close", "aria-label": "Fermer le pointeur", onclick: close }, "×"));
    document.body.append(box, arrow, bubble);
    const place = () => {
      if (!target.isConnected) { close(); return; }
      const r = target.getBoundingClientRect();
      const pad = 6;
      Object.assign(box.style, { left: (r.left - pad) + "px", top: (r.top - pad) + "px", width: (r.width + 2 * pad) + "px", height: (r.height + 2 * pad) + "px" });
      // the arrow comes from the upper right at 45°, its head just right of the text found (inside a wide row)
      const t = spot.isConnected ? spot.getBoundingClientRect() : r;
      const tipX = Math.min(t.right + 4, window.innerWidth - 90), tipY = Math.max(t.top + Math.min(t.height / 2, 14), 70);
      Object.assign(arrow.style, { left: tipX + "px", top: tipY + "px" });
      Object.assign(bubble.style, { left: Math.min(tipX + 56, window.innerWidth - 260) + "px", top: Math.max(tipY - 96, 8) + "px" });
      active.frame = requestAnimationFrame(place);
    };
    active = { nodes: [box, arrow, bubble], frame: 0,
      key: (ev) => { if (ev.key === "Escape") close(); },
      down: (ev) => { if (!bubble.contains(ev.target)) close(); } };
    document.addEventListener("keydown", active.key, true);
    setTimeout(() => active && document.addEventListener("pointerdown", active.down, true), 400);  // not the click that opened it
    place();
    return true;
  }

  /* wait for the page to draw (the views load their data first): up to 8 seconds */
  function pointTo(text, note) {
    const started = Date.now();
    return new Promise((resolve) => {
      const tryNow = () => {
        const target = find(text);
        if (target) { resolve(show(target, note)); return; }
        if (Date.now() - started > 8000) {
          DA.toast("Le point d'intérêt « " + text + " » n'est pas sur cette page.", "info");
          resolve(false);
          return;
        }
        setTimeout(tryNow, 250);
      };
      tryNow();
    });
  }

  function pointLink(text, note, hash) {
    const q = new URLSearchParams({ focus: String(text || "").slice(0, 160) });
    if (note) q.set("note", String(note).slice(0, 200));
    return location.origin + "/?" + q.toString() + (hash || location.hash || "#/");
  }

  /* a pointer link: once the person is in and the page is drawn, show the point, then forget the query */
  function fromUrl() {
    const q = new URLSearchParams(location.search);
    const focus = q.get("focus");
    if (!focus || !DA.session || !DA.session.user) return;
    const note = q.get("note") || "";
    history.replaceState(null, "", location.pathname + location.hash);
    pointTo(focus, note);
  }

  let tries = 0;
  const wait = () => { if (DA.session && DA.session.user) fromUrl(); else if (tries++ < 120) setTimeout(wait, 250); };
  document.addEventListener("DOMContentLoaded", wait);
  DA.pointTo = pointTo;
  DA.pointLink = pointLink;
  DA.pointer = { find, close };
})();
