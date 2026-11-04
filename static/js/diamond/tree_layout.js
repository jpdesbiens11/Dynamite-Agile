/* Diamond · Arbre fonctionnel: the drawing (0.60.11). The primary function on the left, its « comment » to the right,
   siblings from top to bottom in the order of use (« quand »). Boxes are HTML buttons placed with the CSSOM over an SVG
   that holds only the lines (no text in an image): elbow connectors, thick ones on the critical path, dotted curves for
   the feedback of the control functions. A box can be dragged onto another one: it becomes one of its « comment ». */
(function () {
  "use strict";

  const { el } = DA;
  const NS = "http://www.w3.org/2000/svg";
  const W = 196, H = 62, COL = 248, ROW = 78, PAD = 18, TOP = 8;
  const HEADS = ["Fonction primaire", "Secondaires", "Tertiaires", "Techniques"];

  function children(items, id) {
    return items.filter((f) => f.parent_id === id && !f.is_primary).sort((a, b) => a.position - b.position || a.number - b.number);
  }

  /* {nodes: Map id -> {f, x, y}, width, height, levels} for the functions hanging from the primary one */
  function layout(items) {
    const primary = items.find((f) => f.is_primary);
    const nodes = new Map();
    if (!primary) return { nodes, width: 0, height: 0, levels: 0 };
    let row = 0, deepest = 1;
    const place = (f, depth) => {
      deepest = Math.max(deepest, depth);
      const kids = children(items, f.id);
      kids.forEach((k) => place(k, depth + 1));
      const y = kids.length ? (nodes.get(kids[0].id).y + nodes.get(kids[kids.length - 1].id).y) / 2 : TOP + ROW * row++;
      nodes.set(f.id, { f, x: PAD + (depth - 1) * COL, y, depth });
    };
    place(primary, 1);
    return { nodes, width: PAD * 2 + (deepest - 1) * COL + W + 70, height: TOP + ROW * Math.max(row, 1), levels: deepest };
  }

  function svg(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, String(v)));
    return node;
  }

  function lines(box, items) {
    const g = svg("svg", { class: "dm-lines", width: box.width, height: box.height, "aria-hidden": "true" });
    const defs = svg("defs", {});
    const marker = svg("marker", { id: "dm-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" });
    marker.append(svg("path", { d: "M0 0 L10 5 L0 10 z", class: "dm-arrow-head" }));
    defs.append(marker);
    g.append(defs);
    box.nodes.forEach(({ f, x, y }) => {
      const parent = box.nodes.get(f.parent_id);
      if (!parent || f.is_primary) return;
      const x1 = parent.x + W, y1 = parent.y + H / 2, x2 = x, y2 = y + H / 2, xm = x1 + (COL - W) / 2;
      const critical = f.critical && (parent.f.critical || parent.f.is_primary);
      g.append(svg("path", { d: "M" + x1 + " " + y1 + " H" + xm + " V" + y2 + " H" + x2,
        class: "dm-edge" + (critical ? " dm-edge-critical" : "") + (f.level === 4 ? " dm-edge-tech" : "") }));
    });
    box.nodes.forEach(({ f, x, y }) => {
      const target = f.feedback_to && box.nodes.get(f.feedback_to);
      if (!target) return;
      const sx = x + W, sy = y + H / 2, tx = target.x + W, ty = target.y + H / 2, bulge = Math.max(sx, tx) + 46;
      g.append(svg("path", { d: "M" + sx + " " + sy + " C" + bulge + " " + sy + " " + bulge + " " + ty + " " + tx + " " + ty,
        class: "dm-feedback", "marker-end": "url(#dm-arrow)" }));
    });
    return g;
  }

  /* opts: {items, selected, editable, onSelect(id), onDrop(dragId, targetId | null), onKey(ev, f)} */
  function draw(opts) {
    const box = layout(opts.items);
    const canvas = el("div", { class: "dm-canvas", role: "group", "aria-label": "Arbre fonctionnel" });
    canvas.style.width = box.width + "px";
    canvas.style.height = box.height + "px";
    canvas.append(lines(box, opts.items));
    box.nodes.forEach(({ f, x, y }) => {
      const node = el("button", {
        type: "button", class: "dm-node dm-l" + f.level + (f.critical ? " dm-critical" : "") + (f.id === opts.selected ? " dm-selected" : "")
          + (f.ftype !== "usage" ? " dm-t-" + f.ftype : ""),
        "data-tip": f.text, "data-f": f.number, "aria-pressed": f.id === opts.selected ? "true" : "false",
        draggable: opts.editable && !f.is_primary ? "true" : null,
        onclick: () => opts.onSelect(f.id), onkeydown: (ev) => opts.onKey(ev, f) },
      el("span", { class: "dm-code" }, "F" + f.number), el("span", { class: "dm-text" }, f.text));
      node.style.left = x + "px";
      node.style.top = y + "px";
      if (opts.editable) dropTarget(node, f.id, opts.onDrop, !f.is_primary);
      canvas.append(node);
    });
    const heads = el("div", { class: "dm-heads", "aria-hidden": "true" });
    heads.style.width = box.width + "px";
    HEADS.slice(0, Math.max(box.levels, 3)).forEach((label, i) => {
      const h = el("span", { class: "dm-head dm-head-" + (i + 1) }, label);
      h.style.left = (PAD + i * COL) + "px";
      heads.append(h);
    });
    return el("div", { class: "dm-scroll" }, heads, canvas);
  }

  /* drag source and drop target in one: a box dragged onto another becomes its « comment » */
  function dropTarget(node, id, onDrop, source) {
    if (source) node.addEventListener("dragstart", (ev) => { ev.dataTransfer.setData("text/plain", String(id)); ev.dataTransfer.effectAllowed = "move"; });
    node.addEventListener("dragover", (ev) => { ev.preventDefault(); node.classList.add("dm-drop"); });
    node.addEventListener("dragleave", () => node.classList.remove("dm-drop"));
    node.addEventListener("drop", (ev) => {
      ev.preventDefault();
      node.classList.remove("dm-drop");
      const dragged = Number(ev.dataTransfer.getData("text/plain"));
      if (dragged && dragged !== id) onDrop(dragged, id);
    });
  }

  DA.diamond = Object.assign(DA.diamond || {}, { layout, drawTree: draw, dropTarget, children });
})();
