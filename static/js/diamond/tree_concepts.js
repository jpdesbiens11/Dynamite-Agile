/* Diamond · Arbre fonctionnel, the « Concept / Brique technologique » column (0.60.105, D-O-117). After the deepest column of
   functions, beyond a dotted line: one box per brick (CB-n), drawn once even when several functions share it, at the middle of
   its functions, each function joined to it by a thin bracket line. Bricks never overlap: each one is pushed below the one
   above when they would. A box is a button: it selects the brick (panel concept_panel.js). No text in the SVG. */
(function () {
  "use strict";

  const { el } = DA;
  const GAP = 64, SPACE = 10, CH = 86;  // a brick box is taller: its initial concept, its brick, and where it landed

  function conceptColumn(box, opts) {
    const D = DA.diamond, T = D.TREE, svg = D.svg;
    const levels = Math.max(box.levels, 3);
    const sep = T.PAD + (levels - 1) * T.COL + T.W + GAP / 2;
    const x0 = T.PAD + (levels - 1) * T.COL + T.W + GAP;
    const xm = sep + (x0 - sep) / 2;
    const placed = opts.concepts.map((c) => {
      const ys = c.function_ids.map((id) => box.nodes.get(id)).filter(Boolean).map((n) => n.y);
      return ys.length ? { c, ys, want: (Math.min(...ys) + Math.max(...ys) + T.H - CH) / 2 } : null;
    }).filter(Boolean).sort((a, b) => a.want - b.want);
    let floor = -Infinity;
    placed.forEach((p) => { p.y = Math.max(p.want, floor, 0); floor = p.y + CH + SPACE; });
    const height = Math.max(box.height, placed.length ? placed[placed.length - 1].y + CH + T.TOP : 0);
    const width = x0 + T.W + T.PAD;
    const g = svg("svg", { class: "dm-lines dm-concept-lines", width, height, "aria-hidden": "true" });
    g.append(svg("line", { x1: sep, y1: 0, x2: sep, y2: height, class: "dm-concept-sep" }));
    const nodes = placed.map((p) => {
      p.c.function_ids.forEach((id) => {
        const n = box.nodes.get(id);
        if (!n) return;
        g.append(svg("path", { d: "M" + (n.x + T.W) + " " + (n.y + T.H / 2) + " H" + xm + " V" + (p.y + CH / 2) + " H" + x0,
          class: "dm-edge-concept" + (p.c.id === opts.selectedConcept ? " dm-edge-concept-on" : "") }));
      });
      const shared = p.c.function_ids.length > 1 ? " · " + p.c.function_ids.length + " fonctions" : "";
      const node = el("button", {
        type: "button", class: "dm-node dm-concept dm-concept-" + p.c.kind + (p.c.id === opts.selectedConcept ? " dm-selected" : "")
          + (p.c.source === "ai" ? " dm-concept-ai" : ""),
        "data-tip": (p.c.initial_name ? "Concept initial « " + p.c.initial_name + " » — " : "") + p.c.name
          + (p.c.reference ? " — " + p.c.reference : "") + (p.c.selected_sheet ? " — retenu : " + p.c.selected_sheet.title : ""), "aria-pressed": p.c.id === opts.selectedConcept ? "true" : "false",
        onclick: () => opts.onConcept(p.c.id) },
      el("span", { class: "dm-code" }, p.c.code, el("span", { class: "dm-concept-kind" },
        (p.c.kind === "existing" ? "Existant" : "À définir") + shared + (p.c.source === "ai" ? " · IA" : ""))),
      el("strong", { class: "dm-concept-initial" }, p.c.initial_name ? "« " + p.c.initial_name + " »" : p.c.name),
      p.c.selected_sheet ? el("span", { class: "dm-concept-landed" }, "→ " + p.c.selected_sheet.code + " " + p.c.selected_sheet.title)
        : p.c.initial_name ? el("span", { class: "dm-concept-brick" }, p.c.name) : null);
      node.style.height = CH + "px";
      node.style.left = x0 + "px";
      node.style.top = p.y + "px";
      return node;
    });
    const head = el("span", { class: "dm-head dm-head-concept", "data-new": "0.60.105-concept-column" }, "Concept initial / Brique technologique");
    head.style.left = x0 + "px";
    return { svg: g, nodes, head, width, height };
  }

  DA.diamond = Object.assign(DA.diamond || {}, { conceptColumn });
})();
