/* Diamond · Structure fonctionnelle: the boundary diagram (0.60.13). Inputs on the left, outputs on the right, the
   system frame (primary function) around the sub-systems (general view) or the tertiary functions grouped in the frame
   of their sub-system (detail view). Boxes are HTML buttons placed with the CSSOM; the SVG holds only the lines (no
   text in an image): one style per kind of flow, as in the legend of the course. A box is dragged with the pointer
   (or Alt + arrows); without a saved position, the layout below places it. */
(function () {
  "use strict";

  const { el } = DA;
  const NS = "http://www.w3.org/2000/svg";
  const W = 184, H = 56, PW = 184, PH = 58, GAP = 70, LEFT = 16, FRAME_X = 260, TOP = 64;
  const KINDS = ["energy", "material", "information"];

  const key = (type, id) => type + ":" + id;

  /* {boxes: Map key -> {key, type, id, x, y, w, h, item}, groups: [{f, x, y, w, h}], frame} */
  function layout(data, view, saved) {
    const boxes = new Map();
    const put = (type, item, x, y, w, h) => {
      const k = key(type, item.id);
      const p = saved.get(k);
      boxes.set(k, { key: k, type, id: item.id, item, x: p ? p.x : x, y: p ? p.y : y, w, h });
    };
    const fx = FRAME_X + 40;
    let bottom = TOP;
    if (view === "general") {
      const cols = data.secondaries.length > 3 ? 2 : 1, row = H + 64;  // two staggered columns: room for the flows
      data.secondaries.forEach((f, i) => {
        const col = i % cols;
        put("function", f, fx + col * (W + 120), TOP + 40 + Math.floor(i / cols) * row + (col ? row / 2 : 0), W, H);
      });
    } else {
      let y = TOP + 34;
      data.secondaries.forEach((s) => {
        const kids = data.views.detail.filter((f) => f.parent_id === s.id && f.level === 3);
        const members = kids.length ? kids : data.views.detail.filter((f) => f.id === s.id);
        members.forEach((f, j) => put("function", f, fx + j * (W + GAP), y + 28, W, H));
        y += H + 28 + 70;
      });
    }
    const funcs = [...boxes.values()];
    const right = Math.max(fx + W, ...funcs.map((b) => b.x + b.w)) + 40;
    funcs.forEach((b) => { bottom = Math.max(bottom, b.y + b.h); });
    const ins = data.ports.filter((p) => p.side === "in"), outs = data.ports.filter((p) => p.side === "out");
    const step = (n) => Math.max(PH + 22, (bottom - TOP) / Math.max(n, 1));
    ins.forEach((p, i) => put("port", p, LEFT, TOP + 30 + i * step(ins.length), PW, PH));
    outs.forEach((p, i) => put("port", p, right + 70, TOP + 30 + i * step(outs.length), PW, PH));
    return { boxes, view };
  }

  /* frames around the functions (the system) and around each sub-system in the detail view */
  function frames(data, box) {
    const funcs = [...box.boxes.values()].filter((b) => b.type === "function");
    const bound = (list, pad, head) => {
      if (!list.length) return null;
      const x = Math.min(...list.map((b) => b.x)) - pad, y = Math.min(...list.map((b) => b.y)) - pad - head;
      return { x, y, w: Math.max(...list.map((b) => b.x + b.w)) + pad - x, h: Math.max(...list.map((b) => b.y + b.h)) + pad - y };
    };
    const groups = box.view === "detail" ? data.secondaries.map((s) => {
      const list = funcs.filter((b) => b.item.parent_id === s.id || b.id === s.id);
      const r = bound(list, 12, 22);
      return r ? Object.assign(r, { f: s }) : null;
    }).filter(Boolean) : [];
    const all = groups.length ? groups.map((g) => ({ x: g.x, y: g.y, w: g.w, h: g.h })) : funcs;
    return { groups, system: bound(all, 24, 30) };
  }

  function svg(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, String(v)));
    return node;
  }

  function ends(flow) {
    const src = flow.src_port_id ? key("port", flow.src_port_id) : key("function", flow.src_function_id);
    const dst = flow.dst_port_id ? key("port", flow.dst_port_id) : key("function", flow.dst_function_id);
    return [src, dst];
  }

  /* a cubic curve leaving a side of the source towards the target; `shift` separates parallel flows */
  function geometry(a, b, shift) {
    const acx = a.x + a.w / 2, acy = a.y + a.h / 2, bcx = b.x + b.w / 2, bcy = b.y + b.h / 2;
    let p1, p2, c1, c2;
    if (b.x >= a.x + a.w || b.x + b.w <= a.x) {
      const dir = b.x >= a.x + a.w ? 1 : -1;
      p1 = [dir > 0 ? a.x + a.w : a.x, acy + shift];
      p2 = [dir > 0 ? b.x : b.x + b.w, bcy + shift];
      const d = Math.max(36, Math.abs(p2[0] - p1[0]) / 2);
      c1 = [p1[0] + dir * d, p1[1]]; c2 = [p2[0] - dir * d, p2[1]];
    } else {
      const dir = bcy >= acy ? 1 : -1;
      p1 = [acx + shift, dir > 0 ? a.y + a.h : a.y];
      p2 = [bcx + shift, dir > 0 ? b.y : b.y + b.h];
      const d = Math.max(28, Math.abs(p2[1] - p1[1]) / 2);
      c1 = [p1[0], p1[1] + dir * d]; c2 = [p2[0], p2[1] - dir * d];
    }
    const mid = [0, 1].map((i) => 0.125 * p1[i] + 0.375 * c1[i] + 0.375 * c2[i] + 0.125 * p2[i]);
    return { d: "M" + p1 + " C" + c1 + " " + c2 + " " + p2, mid };
  }

  /* opts: {data, view, saved: Map, selected: {type, id, key} | null, link, editable, showLabels, onSelect(sel), onMove(box), flows,
     parts: Map function id -> [part] | null} */
  function draw(opts) {
    const box = layout(opts.data, opts.view, opts.saved);
    const canvas = el("div", { class: "dm-st-canvas", role: "group", "aria-label": "Structure fonctionnelle" });
    const lines = svg("svg", { class: "dm-st-lines", "aria-hidden": "true" });
    const defs = svg("defs", {});
    KINDS.forEach((k) => {
      const m = svg("marker", { id: "dm-arrow-" + k, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" });
      m.append(svg("path", { d: "M0 0 L10 5 L0 10 z", class: "dm-head-" + k }));
      defs.append(m);
    });
    const frameLayer = el("div", { class: "dm-st-frames" });
    const labelLayer = el("div", { class: "dm-st-labels" });
    canvas.append(frameLayer, lines, labelLayer);
    const isSel = (type, id) => opts.selected && opts.selected.type === type && opts.selected.id === id;

    const redraw = () => {
      if (opts.selected && opts.selected.type !== "flow") opts.selected.key = key(opts.selected.type, opts.selected.id);
      while (lines.firstChild) lines.removeChild(lines.firstChild);
      while (labelLayer.firstChild) labelLayer.removeChild(labelLayer.firstChild);
      while (frameLayer.firstChild) frameLayer.removeChild(frameLayer.firstChild);
      lines.append(defs);
      const fr = frames(opts.data, box);
      if (fr.system) {
        const sys = el("div", { class: "dm-st-system" }, el("span", { class: "dm-st-system-label" },
          opts.data.primary ? "F" + opts.data.primary.number + " " + opts.data.primary.text : "Système"));
        place(sys, fr.system);
        frameLayer.append(sys);
      }
      fr.groups.forEach((g) => {
        const node = el("div", { class: "dm-st-group" }, el("span", { class: "dm-st-group-label" }, "Sous-système F" + g.f.number + " · " + g.f.text));
        place(node, g);
        frameLayer.append(node);
      });
      const seen = new Map();
      opts.flows.forEach((fl) => {
        const [s, t] = ends(fl);
        const a = box.boxes.get(s), b = box.boxes.get(t);
        if (!a || !b) return;
        const pair = [s, t].sort().join("|");
        const n = seen.get(pair) || 0;
        seen.set(pair, n + 1);
        const g = geometry(a, b, (n % 2 ? 1 : -1) * Math.ceil(n / 2) * 9);
        const cls = "dm-flow dm-f-" + fl.kind + (isSel("flow", fl.id) ? " dm-flow-sel" : "");
        lines.append(svg("path", { d: g.d, class: cls, "marker-end": "url(#dm-arrow-" + fl.kind + ")" }));
        const hit = svg("path", { d: g.d, class: "dm-flow-hit" });
        hit.addEventListener("click", () => opts.onSelect({ type: "flow", id: fl.id }));
        lines.append(hit);
        if (fl.label && (opts.showLabels || isSel("flow", fl.id) || (opts.selected && [s, t].includes(opts.selected.key)))) {
          const lab = el("button", { type: "button", class: "dm-st-flow-label dm-fl-" + fl.kind + (isSel("flow", fl.id) ? " dm-flow-sel" : ""),
            onclick: () => opts.onSelect({ type: "flow", id: fl.id }) }, fl.label);
          lab.style.left = g.mid[0] + "px";
          lab.style.top = g.mid[1] + "px";
          labelLayer.append(lab);
        }
      });
      const all = [...box.boxes.values()];
      const wMax = Math.max(600, ...all.map((b) => b.x + b.w)) + 40, hMax = Math.max(320, ...all.map((b) => b.y + b.h)) + 40;
      canvas.style.width = wMax + "px";
      canvas.style.height = hMax + "px";
      lines.setAttribute("width", wMax);
      lines.setAttribute("height", hMax);
    };

    box.boxes.forEach((b) => {
      const item = b.item;
      const node = el("button", { type: "button", "data-node": b.key,
        class: "dm-st-node " + (b.type === "port" ? "dm-st-port dm-st-" + item.side + " dm-fl-" + item.kind : "dm-st-func")
          + (isSel(b.type, b.id) ? " dm-selected" : "") + (opts.link && opts.link.key === b.key ? " dm-st-linking" : ""),
        "aria-pressed": isSel(b.type, b.id) ? "true" : "false", "data-tip": b.type === "port" ? item.label : item.text },
      b.type === "port" ? el("span", { class: "dm-code" }, item.side === "in" ? "Entrée" : "Sortie") : el("span", { class: "dm-code" }, "F" + item.number),
      el("span", { class: "dm-text" }, b.type === "port" ? item.label : item.text),
      partTags(opts.parts, b));
      place(node, b);
      drag(node, b, opts, redraw);
      canvas.append(node);
    });
    redraw();
    return el("div", { class: "dm-scroll dm-st-scroll" }, canvas);
  }

  /* 0.60.20 (D-O-031): the codes of the parts that carry out this function, on the lower edge of its box */
  function partTags(parts, b) {
    const list = b.type === "function" && parts ? parts.get(b.id) || [] : [];
    if (!list.length) return null;
    const shown = list.slice(0, 4).map((p) => el("span", { class: "dm-st-ptag" + (p.functions.length >= 2 ? " dm-st-ptag-multi" : "") }, "P-" + p.number));
    return el("span", { class: "dm-st-ptags" + (list.length >= 2 ? " dm-st-ptags-many" : ""), "aria-label": list.length + " pièce(s)" },
      shown, list.length > 4 ? el("span", { class: "dm-st-ptag" }, "+" + (list.length - 4)) : null);
  }

  function place(node, r) {
    node.style.left = r.x + "px";
    node.style.top = r.y + "px";
    if (r.w && !node.classList.contains("dm-st-node")) { node.style.width = r.w + "px"; node.style.height = r.h + "px"; }
  }

  /* pointer drag (the position is saved when the box is dropped), Alt + arrows from the keyboard */
  function drag(node, b, opts, redraw) {
    let start = null;
    node.addEventListener("pointerdown", (ev) => {
      if (!opts.editable || ev.button !== 0) return;
      start = { x: ev.clientX, y: ev.clientY, bx: b.x, by: b.y, moved: false };
      node.setPointerCapture(ev.pointerId);
    });
    node.addEventListener("pointermove", (ev) => {
      if (!start) return;
      const dx = ev.clientX - start.x, dy = ev.clientY - start.y;
      if (!start.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
      start.moved = true;
      b.x = Math.max(0, start.bx + dx); b.y = Math.max(0, start.by + dy);
      place(node, b);
      redraw();
    });
    node.addEventListener("pointerup", () => {
      const was = start;
      start = null;
      if (was && was.moved) opts.onMove(b);
    });
    node.addEventListener("click", () => opts.onSelect({ type: b.type, id: b.id, key: b.key }));  // also after a drag: it selects
    node.addEventListener("keydown", (ev) => {
      const step = { ArrowUp: [0, -10], ArrowDown: [0, 10], ArrowLeft: [-10, 0], ArrowRight: [10, 0] }[ev.key];
      if (!ev.altKey || !step || !opts.editable) return;
      ev.preventDefault();
      b.x = Math.max(0, b.x + step[0]); b.y = Math.max(0, b.y + step[1]);
      place(node, b);
      redraw();
      opts.onMove(b);
    });
  }

  DA.diamond = Object.assign(DA.diamond || {}, { structureDraw: draw, structureKey: key, flowEnds: ends });
})();
