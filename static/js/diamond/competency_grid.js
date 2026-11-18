/* Diamond · Arbre fonctionnel, the grid of the competencies (0.60.116, D-O-129). Right of the « Concept / Brique technologique »
   column, beyond a dashed line: one column per competency used in the Space (its icon on top, the legend under the tree), one
   row of dashed cells per function line that ends with a brick, at the height of the function. A cell holds the rating 1 to 5
   (5: at the heart of the development); a click opens the choice, the keys 1 to 5 set it, 0 or Delete clears it. The row of
   the line stays with its function through a light dashed guide at its height. No text in the SVG. */
(function () {
  "use strict";

  const { el } = DA;
  const NS = "http://www.w3.org/2000/svg";
  const GAP = 56, CW = 34, RH = 30, ADD = 40;

  const sprite = () => (document.documentElement.hasAttribute("data-term") ? "/img/competencies-term.svg" : "/img/competencies.svg");
  const refresh = DA.refreshIcons;  // a theme change redraws the icons already on screen with the other sprite
  DA.refreshIcons = function () {
    if (refresh) refresh();
    document.querySelectorAll("svg.dm-comp use").forEach((u) => u.setAttribute("href", sprite() + "#" + u.getAttribute("href").split("#")[1]));
  };

  function compIcon(key, cls) {
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "dm-comp" + (cls ? " " + cls : ""));
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    const use = document.createElementNS(NS, "use");
    use.setAttribute("href", sprite() + "#k-" + (key || "person"));
    svg.append(use);
    return svg;
  }

  /* the columns: the competencies this Space chose for its grid, in their order (0.60.117, D-O-130: server side, « columns ») */
  function columns(comp) {
    const byCode = new Map(comp.catalog.map((c) => [c.code, c]));
    return (comp.columns || []).map((code) => byCode.get(code)).filter(Boolean);
  }

  /* opts: {comp, editable, onRate(fid, code, n), onAddCol(code), onRemoveCol(code)}; column: what conceptColumn returned */
  function competencyGrid(box, column, opts) {
    const D = DA.diamond, T = D.TREE;
    const cols = columns(opts.comp);
    const sep = column.width + GAP / 2 - T.PAD;
    const x0 = column.width + GAP - T.PAD;
    const width = x0 + cols.length * CW + (opts.editable ? ADD : 0) + T.PAD;
    const g = D.svg("svg", { class: "dm-lines dm-cg-lines", width, height: column.height, "aria-hidden": "true" });
    g.append(D.svg("line", { x1: sep, y1: 0, x2: sep, y2: column.height, class: "dm-concept-sep" }));
    const bricks = new Map(column.placed.map((p) => [p.c.id, p]));
    const nodes = [];
    opts.comp.lines.forEach((ln) => {
      const n = box.nodes.get(ln.function_id);
      const p = bricks.get(ln.brick.id);
      if (!n || !p) return;
      const y = n.y + (T.H - RH) / 2;
      // a light guide at the height of the function: the row reads with its function (the brick is joined to it on the left)
      g.append(D.svg("line", { x1: column.x0 + T.W + 6, y1: y + RH / 2, x2: x0, y2: y + RH / 2, class: "dm-edge-comp" }));
      const row = el("div", { class: "dm-cg-row" + (ln.brick.frozen ? " dm-cg-frozen" : ""), role: "group",
        "aria-label": ln.code + " · " + ln.brick.code + " — compétences" });
      row.style.left = x0 + "px";
      row.style.top = y + "px";
      cols.forEach((c) => row.append(cell(ln, c, opts)));
      nodes.push(row);
    });
    const head = el("div", { class: "dm-cg-head" });
    head.style.left = x0 + "px";
    cols.forEach((c) => head.append(headButton(c, opts)));
    if (opts.editable) head.append(addButton(opts, cols));
    return { svg: g, nodes, head, width, cols };
  }

  function cell(ln, c, opts) {
    const value = ln.ratings[c.code] || 0;
    const tip = ln.code + " · " + c.name + " : " + (value ? value + " / 5" : "non nécessaire");
    const node = el("button", { type: "button", class: "dm-cg-cell dm-cg-" + value, "data-tip": tip, "aria-label": tip,
      disabled: opts.editable ? null : "disabled" }, value ? String(value) : "·");
    if (!opts.editable) return node;
    node.addEventListener("click", () => chooser(node, ln, c, value, opts));
    node.addEventListener("keydown", (ev) => {
      const k = ev.key === "Delete" || ev.key === "Backspace" ? "0" : ev.key;
      if (/^[0-5]$/.test(k)) { ev.preventDefault(); opts.onRate(ln.function_id, c.code, Number(k)); }
    });
    return node;
  }

  /* the small menu of a cell: — (not needed), then 1 to 5 */
  function chooser(anchor, ln, c, value, opts) {
    document.querySelectorAll(".dm-cg-menu").forEach((m) => m.remove());
    const close = () => { menu.remove(); document.removeEventListener("keydown", esc); anchor.focus(); };
    const esc = (ev) => { if (ev.key === "Escape") close(); };
    const menu = el("div", { class: "dm-cg-menu", role: "menu", "aria-label": c.name + " pour " + ln.code },
      el("span", { class: "dm-cg-menu-name" }, c.name),
      [0, 1, 2, 3, 4, 5].map((n) => el("button", { type: "button", role: "menuitem", class: "dm-cg-cell dm-cg-" + n + (n === value ? " dm-cg-on" : ""),
        "data-tip": n ? ["", "Presque pas", "Un peu", "Régulièrement", "Beaucoup", "Au cœur du développement"][n] : "Retirer de la ligne",
        onclick: () => { menu.remove(); document.removeEventListener("keydown", esc); opts.onRate(ln.function_id, c.code, n); } }, n ? String(n) : "—")));
    document.addEventListener("keydown", esc);
    anchor.parentNode.parentNode.append(menu);
    menu.style.left = (anchor.parentNode.offsetLeft + anchor.offsetLeft) + "px";
    menu.style.top = (anchor.parentNode.offsetTop + anchor.offsetHeight + 4) + "px";
    menu.querySelector("button").focus();
  }

  /* the title of a column: its icon and its code, always readable; a click offers to take it out of the grid */
  function headButton(c, opts) {
    const rated = opts.comp.lines.filter((ln) => ln.ratings[c.code]).length;
    const node = el("button", { type: "button", class: "dm-cg-icon", "data-tip": c.name + " (" + c.code + ")"
      + (opts.editable ? " — cliquez pour la retirer de la grille" : ""), "aria-label": c.name, disabled: opts.editable ? null : "disabled" },
    compIcon(c.icon), el("span", { class: "dm-cg-code" }, c.code));
    if (!opts.editable) return node;
    node.addEventListener("click", () => {
      document.querySelectorAll(".dm-cg-menu").forEach((m) => m.remove());
      const close = () => { menu.remove(); document.removeEventListener("keydown", esc); node.focus(); };
      const esc = (ev) => { if (ev.key === "Escape") close(); };
      const menu = el("div", { class: "dm-cg-menu dm-cg-colmenu", role: "menu", "aria-label": c.name },
        el("span", { class: "dm-cg-menu-name" }, c.name + (rated ? " · " + rated + " ligne" + (rated > 1 ? "s" : "") + " notée" + (rated > 1 ? "s" : "") : "")),
        el("button", { type: "button", role: "menuitem", class: "btn btn-small btn-danger", onclick: () => {
          if (rated && !window.confirm("Retirer " + c.name + " de la grille ? Ses notes sur " + rated + " ligne" + (rated > 1 ? "s" : "")
            + " sont effacées (les personnes prévues pour elle restent dans la synthèse).")) return;
          close();
          opts.onRemoveCol(c.code);
        } }, "Retirer de la grille"),
        el("button", { type: "button", role: "menuitem", class: "btn btn-small", onclick: close }, "Annuler"));
      document.addEventListener("keydown", esc);
      node.parentNode.parentNode.append(menu);
      menu.style.left = (node.parentNode.offsetLeft + node.offsetLeft) + "px";
      menu.style.top = (node.offsetTop + node.offsetHeight + 4) + "px";
      menu.querySelector("button").focus();
    });
    return node;
  }

  function addButton(opts, cols) {
    const shown = new Set(cols.map((c) => c.code));
    const pick = el("select", { class: "dm-cg-add", "aria-label": "Ajouter une compétence à la grille", "data-tip": "Ajouter une compétence" },
      el("option", { value: "" }, "+"), opts.comp.catalog.filter((c) => c.active && !shown.has(c.code))
        .map((c) => el("option", { value: c.code }, c.name)));
    pick.addEventListener("change", () => { if (pick.value) opts.onAddCol(pick.value); });
    return pick;
  }

  /* under the tree: what each icon means, the scale, and the way to the summary */
  function competencyLegend(ctx, comp, cols) {
    const items = cols.map((c) => el("span", { class: "dm-cg-key" }, compIcon(c.icon),
      c.bdc ? el("a", { href: c.bdc, "data-tip": "Profil, formation, outils et livrables (BDC)" }, c.name) : el("span", null, c.name)));
    return el("div", { class: "dm-cg-legend", "aria-label": "Légende des compétences", "data-new": "0.60.116-competency-legend" },
      el("strong", null, "Compétences"), items.length ? items : el("span", { class: "muted" }, comp.lines.length
        ? "Aucune compétence notée : ajoutez une colonne avec « + » à droite de l'arbre, ou faites remplir la grille par l'IA (« ↔ IA »)."
        : "Donnez une brique technologique aux fonctions tertiaires : chaque ligne qui aboutit à une brique reçoit sa grille."),
      el("span", { class: "muted dm-cg-scale" }, "1 presque pas · 3 régulièrement · 5 au cœur du développement"),
      el("a", { class: "btn btn-small", href: DA.agile.href(ctx, "competencies") }, "Compétences et équipe →"));
  }

  DA.diamond = Object.assign(DA.diamond || {}, { compIcon, competencyGrid, competencyLegend, competencyColumns: columns });
})();
