/* Command palette (D-B-088, core lot v0.23): Ctrl+K (⌘K) anywhere, or the « Ctrl K » button of the top bar.
   Type a few letters of a tab, a Space or a page and press Entrée: a quicker way to go where the menus already go --
   every destination is an existing screen, nothing new is done here. The last line always searches the platform.
   Available in every theme. */
(function () {
  "use strict";

  const { el, clear } = DA;
  const SPACE_VIEWS = [  // per-Space screens: [module key, label, route suffix]
    ["goldmine", "Goldmine", ""], ["exploration", "Exploration", ""], ["agile", "Agile · Backlog", "/backlog"],
    ["agile", "Agile · Board", "/board"], ["agile", "Change Management", "/changes"], ["dynamite", "Dynamite", ""],
  ];
  const ADMIN = [["users", "Utilisateurs"], ["rights", "Droits"], ["rules", "Règles d'accès"], ["projects", "Spaces"],
    ["setup", "Setup des Spaces"], ["update/restore", "Restaurer (versions et points)"], ["update/framework", "Update du Framework"],
    ["update/config", "Configuration"], ["update/data", "Données et sauvegardes"], ["update/site", "Site complet"],
    ["transport", "Sécurité réseau"], ["privacy", "Confidentialité"], ["audit", "Journal d'audit"]];

  function entries() {
    const s = DA.session || {};
    const available = (s.modules || []).filter((m) => m.available);
    const has = (key) => available.some((m) => m.key === key);
    const icon = (key) => (DA.NAV && DA.NAV.items[key] ? DA.NAV.items[key][0] : "spaces");
    const out = [["Dashboard", "#/dashboard", "dashboard", "Onglet"], ["Accueil — mes Spaces", "#/home", "spaces", "Onglet"]];
    available.forEach((m) => out.push([m.label, "#/" + m.key, icon(m.key === "codex" ? "tools" : m.key), "Onglet"]));
    (s.projects || []).forEach((p) => SPACE_VIEWS.forEach(([key, label, suffix]) => {
      if (has(key)) out.push([label + " · " + p.key + " — " + p.name, "#/" + key + "/" + p.key + suffix, icon(key), "Space"]);
    }));
    out.push(["Paramètres", "#/settings", "admin", "Compte"], ["Mes objectifs", "#/objectives", "training", "Compte"],
      ["Liste Audit", "#/audit", "auditlist", "Outil"], ["Recherche avancée", "#/search/?adv=1", "search", "Outil"]);
    if (s.user && s.user.is_admin) ADMIN.forEach(([view, label]) => out.push(["Admin · " + label, "#/admin/" + view, "admin", "Admin"]));
    return out.map(([label, href, ic, kind]) => ({ label, href, icon: ic, kind }));
  }

  /* subsequence match, with a bonus for consecutive letters and word starts; accents and case ignored */
  const fold = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  function word(text, q) {
    let at = 0, total = 0, run = 0;
    for (const ch of q) {
      const found = text.indexOf(ch, at);
      if (found < 0) return 0;
      run = found === at ? run + 1 : 0;
      total += 1 + run * 2 + (found === 0 || /[\s·—\-/]/.test(text[found - 1]) ? 3 : 0);
      at = found + 1;
    }
    return total;
  }
  function score(label, query) {  // every word of the query must match, in any order (« eqp gold » finds Goldmine · EQP)
    const text = fold(label), words = fold(query).split(/\s+/).filter(Boolean);
    if (!words.length) return 1;
    let total = 0;
    for (const w of words) {
      const s = word(text, w);
      if (!s) return 0;
      total += s;
    }
    return total - text.length * .01;
  }

  let overlay = null;
  function close() { if (overlay) { overlay.remove(); overlay = null; } }

  function open() {
    if (overlay || !DA.session || !DA.session.user) return;
    const all = entries();
    const input = el("input", { type: "text", class: "pal-input", placeholder: "Aller à… (onglet, Space, page) — Entrée pour ouvrir",
      "aria-label": "Palette de commandes", autocomplete: "off", spellcheck: "false" });
    const list = el("ul", { class: "pal-list", role: "listbox" });
    let shown = [], index = 0;
    function go(item) {
      close();
      location.hash = item.href;
    }
    function draw() {
      const q = input.value.trim();
      shown = all.map((e) => [e, score(e.label, q)]).filter(([, s]) => s > 0).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([e]) => e);
      if (q) shown.push({ label: "Rechercher « " + q + " » partout", href: "#/search/" + encodeURIComponent(q), icon: "search", kind: "Recherche" });
      index = Math.min(index, Math.max(0, shown.length - 1));
      clear(list);
      shown.forEach((item, i) => {
        const li = el("li", { class: "pal-item" + (i === index ? " on" : ""), role: "option", "aria-selected": i === index ? "true" : "false",
          onmousedown: (ev) => { ev.preventDefault(); go(item); }, onmousemove: () => { if (index !== i) { index = i; draw(); } } },
        DA.icon ? DA.icon(item.icon) : null, el("span", { class: "pal-label" }, item.label), el("span", { class: "pal-kind" }, item.kind));
        list.append(li);
      });
      const on = list.querySelector(".on");
      if (on) on.scrollIntoView({ block: "nearest" });
    }
    input.addEventListener("input", () => { index = 0; draw(); });
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowDown") { ev.preventDefault(); index = Math.min(shown.length - 1, index + 1); draw(); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); index = Math.max(0, index - 1); draw(); }
      else if (ev.key === "Enter") { ev.preventDefault(); if (shown[index]) go(shown[index]); }
      else if (ev.key === "Escape") { ev.preventDefault(); close(); }
    });
    overlay = el("div", { class: "pal-overlay", onmousedown: (ev) => { if (ev.target === overlay) close(); } },
      el("div", { class: "pal-box", role: "dialog", "aria-label": "Palette de commandes" },
        el("div", { class: "pal-head" }, el("span", { class: "pal-prompt", "aria-hidden": "true" }, "❯"), input),
        list, el("div", { class: "pal-foot" }, "↑ ↓ pour choisir · Entrée pour ouvrir · Échap pour fermer")));
    document.body.append(overlay);
    draw();
    input.focus();
  }
  DA.openPalette = open;

  document.addEventListener("keydown", (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && !ev.altKey && (ev.key === "k" || ev.key === "K")) {
      ev.preventDefault();
      if (overlay) close(); else open();
    }
  });
  window.addEventListener("hashchange", close);

  function paletteButton() {
    return el("button", { type: "button", class: "tb-palette", "data-new": "0.45.0-palette", "data-tip": "Palette : aller n'importe où au clavier (Ctrl+K)",
      "aria-label": "Palette de commandes (Ctrl+K)", onclick: (ev) => { ev.stopPropagation(); open(); } },
    el("kbd", null, "Ctrl"), el("kbd", null, "K"));
  }
  paletteButton.order = 15;  // right after the search box
  DA.topbarTools = DA.topbarTools || [];
  DA.topbarTools.push(paletteButton);
})();
