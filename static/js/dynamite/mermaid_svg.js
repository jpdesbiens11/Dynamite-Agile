/* Dynamite - Mermaid diagrams, part 3: drawing (0.60.60, D-O-069).
   SVG built with createElementNS and textContent only. Colours come from the theme (CSS variables, dynamite.css), with
   the classDef / style colours of the diagram when they are plain values. DY.mermaid.figure(text) returns the block
   shown in a page: the drawing, a « Code » / « Diagramme » switch and, when the text cannot be drawn, the reason with
   its line number above the code -- an AI's diagram is audited, never trusted blindly.
   The sequence diagrams are drawn by mermaid_seq.js. */
(function () {
  "use strict";

  const { el } = DA;
  const MM = DA.dynamite.mermaid = DA.dynamite.mermaid || {};
  const NS = "http://www.w3.org/2000/svg";
  const FONT = 13, LINE = 17;
  let uid = 0;

  function s(tag, attrs, kids) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== false) n.setAttribute(k, String(v)); });
    (kids || []).forEach((k) => { if (k) n.appendChild(k); });
    return n;
  }

  let ctx2d = null;
  function measure(text) {
    const linesOf = String(text || "").split("\n");
    if (!ctx2d) {
      try { ctx2d = document.createElement("canvas").getContext("2d"); } catch (err) { ctx2d = null; }
      if (ctx2d) ctx2d.font = FONT + "px " + (getComputedStyle(document.body).fontFamily || "sans-serif");
    }
    const w = Math.max(0, ...linesOf.map((l) => (ctx2d ? ctx2d.measureText(l).width : l.length * 7)));
    return { w: Math.ceil(w), h: text ? linesOf.length * LINE : 0 };
  }

  /** Multi-line text centred on (x, y). */
  function text(x, y, value, cls, anchor) {
    const linesOf = String(value || "").split("\n");
    const top = y - ((linesOf.length - 1) * LINE) / 2;
    return s("text", { x, y: top, class: cls || "dy-mm-text", "text-anchor": anchor || "middle", "dominant-baseline": "central" },
      linesOf.map((l, i) => { const t = s("tspan", { x, y: top + i * LINE }); t.textContent = l; return t; }));
  }

  const SAFE = /^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{3,20}|rgba?\([\d\s.,%]+\)|\d{1,2}(\.\d)?px|[\d\s,.]{1,20})$/;
  function paint(node, classes) {
    const st = Object.assign({}, (classes || {})[node.cls] || {}, node.style || {});
    const out = {};
    if (SAFE.test(st.fill || "")) out.fill = st.fill;
    if (SAFE.test(st.stroke || "")) out.stroke = st.stroke;
    if (SAFE.test(st["stroke-width"] || "")) out["stroke-width"] = st["stroke-width"];
    if (SAFE.test(st["stroke-dasharray"] || "")) out["stroke-dasharray"] = st["stroke-dasharray"];
    return { shape: out, color: SAFE.test(st.color || "") ? st.color : null };
  }

  /** classDef / style colours: set through the CSSOM (allowed by the CSP, and stronger than the theme's classes). */
  function colour(node, look) {
    const targets = node.tagName === "g" || node.tag === "g" ? Array.from(node.childNodes || node.kids || []) : [node];
    targets.forEach((t) => {
      if (!t.style || !/dy-mm-node(\s|$)/.test(t.getAttribute("class") || "")) return;
      Object.entries(look).forEach(([k, v]) => t.style.setProperty(k, v));
    });
    return node;
  }

  function shape(n, look) {
    return colour(shapeOf(n), look || {});
  }

  function shapeOf(n) {
    const { x, y, w, h } = n, x0 = x - w / 2, y0 = y - h / 2;
    const a = { class: "dy-mm-node" };
    const poly = (pts) => s("polygon", Object.assign({ points: pts.map((p) => p.join(",")).join(" ") }, a));
    switch (n.shape) {
      case "round": return s("rect", Object.assign({ x: x0, y: y0, width: w, height: h, rx: 10 }, a));
      case "stadium": return s("rect", Object.assign({ x: x0, y: y0, width: w, height: h, rx: h / 2 }, a));
      case "circle": return s("circle", Object.assign({ cx: x, cy: y, r: w / 2 }, a));
      case "dcircle": return s("g", null, [s("circle", Object.assign({ cx: x, cy: y, r: w / 2 }, a)), s("circle", Object.assign({ cx: x, cy: y, r: w / 2 - 5 }, a))]);
      case "diamond": return poly([[x, y0], [x0 + w, y], [x, y0 + h], [x0, y]]);
      case "hexagon": return poly([[x0 + 15, y0], [x0 + w - 15, y0], [x0 + w, y], [x0 + w - 15, y0 + h], [x0 + 15, y0 + h], [x0, y]]);
      case "lean_r": return poly([[x0 + 15, y0], [x0 + w, y0], [x0 + w - 15, y0 + h], [x0, y0 + h]]);
      case "lean_l": return poly([[x0, y0], [x0 + w - 15, y0], [x0 + w, y0 + h], [x0 + 15, y0 + h]]);
      case "trapezoid": return poly([[x0 + 15, y0], [x0 + w - 15, y0], [x0 + w, y0 + h], [x0, y0 + h]]);
      case "trapezoid_alt": return poly([[x0, y0], [x0 + w, y0], [x0 + w - 15, y0 + h], [x0 + 15, y0 + h]]);
      case "flag": return poly([[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h], [x0 + 12, y]]);
      case "subroutine": return s("g", null, [s("rect", Object.assign({ x: x0, y: y0, width: w, height: h }, a)),
        s("line", { x1: x0 + 7, y1: y0, x2: x0 + 7, y2: y0 + h, class: "dy-mm-node-line" }),
        s("line", { x1: x0 + w - 7, y1: y0, x2: x0 + w - 7, y2: y0 + h, class: "dy-mm-node-line" })]);
      case "cylinder": {
        const ry = 7;
        return s("g", null, [s("path", Object.assign({ d: `M${x0},${y0 + ry} A${w / 2},${ry} 0 0,1 ${x0 + w},${y0 + ry} L${x0 + w},${y0 + h - ry} `
          + `A${w / 2},${ry} 0 0,1 ${x0},${y0 + h - ry} Z` }, a)),
          s("path", { d: `M${x0},${y0 + ry} A${w / 2},${ry} 0 0,0 ${x0 + w},${y0 + ry}`, class: "dy-mm-node-line" })]);
      }
      case "start": return s("circle", { cx: x, cy: y, r: 9, class: "dy-mm-dot" });
      case "end": return s("g", null, [s("circle", { cx: x, cy: y, r: 9, class: "dy-mm-node" }), s("circle", { cx: x, cy: y, r: 5, class: "dy-mm-dot" })]);
      case "bar": return s("rect", { x: x0, y: y - 4, width: w, height: 8, rx: 2, class: "dy-mm-dot" });
      default: return s("rect", Object.assign({ x: x0, y: y0, width: w, height: h, rx: 3 }, a));
    }
  }

  /** Where a line from the centre of n towards p leaves the shape. */
  function clip(n, p) {
    const dx = p[0] - n.x, dy = p[1] - n.y;
    if (!dx && !dy) return [n.x, n.y];
    let t;
    if (n.shape === "circle" || n.shape === "dcircle" || n.shape === "start" || n.shape === "end") t = (n.w / 2) / Math.hypot(dx, dy);
    else if (n.shape === "diamond") t = 1 / (Math.abs(dx) / (n.w / 2) + Math.abs(dy) / (n.h / 2));
    else t = Math.min(dx ? (n.w / 2) / Math.abs(dx) : Infinity, dy ? (n.h / 2) / Math.abs(dy) : Infinity);
    return [n.x + dx * t, n.y + dy * t];
  }

  function markers(id) {
    const m = (name, kids, w, h, refX) => s("marker", { id: id + name, viewBox: `0 0 ${w} ${h}`, refX, refY: h / 2, markerWidth: w,
      markerHeight: h, orient: "auto-start-reverse", markerUnits: "userSpaceOnUse" }, kids);
    return s("defs", null, [
      m("-arrow", [s("path", { d: "M0,0 L10,5 L0,10 z", class: "dy-mm-head" })], 10, 10, 9),
      m("-circle", [s("circle", { cx: 5, cy: 5, r: 4, class: "dy-mm-head" })], 10, 10, 5),
      m("-cross", [s("path", { d: "M1,1 L9,9 M9,1 L1,9", class: "dy-mm-cross" })], 10, 10, 5)]);
  }

  /** Curve through the points, leaving and entering along the flow direction. */
  function curve(pts, horizontal) {
    let d = `M${pts[0][0]},${pts[0][1]}`;
    for (let i = 1; i < pts.length; i++) {
      const [ax, ay] = pts[i - 1], [bx, by] = pts[i];
      if (horizontal) { const mx = (ax + bx) / 2; d += ` C${mx},${ay} ${mx},${by} ${bx},${by}`; } else { const my = (ay + by) / 2; d += ` C${ax},${my} ${bx},${my} ${bx},${by}`; }
    }
    return d;
  }

  function drawFlow(g) {
    const L = MM.layout(g, measure);
    const id = "dymm" + (++uid);
    const byId = new Map(L.nodes.map((n) => [n.id, n]));
    const svg = s("svg", { viewBox: `0 0 ${L.width} ${L.height}`, width: L.width, height: L.height, class: "dy-mm-svg", role: "img",
      "aria-label": "Diagramme" }, [markers(id)]);
    L.groups.forEach((b) => {
      svg.appendChild(s("rect", { x: b.x, y: b.y, width: b.w, height: b.h, rx: 6, class: "dy-mm-group" }));
      svg.appendChild(text(b.x + 10, b.y + 12, b.title || b.id, "dy-mm-group-title", "start"));
    });
    const labels = [];
    L.edges.forEach((e) => {
      if (e.style === "invisible") return;
      const a = byId.get(e.from), b = byId.get(e.to);
      let pts = e.points.slice();
      if (!e.self) {
        const flowAxis = (p, q) => (L.horizontal ? Math.abs(q[0] - p[0]) > 4 : Math.abs(q[1] - p[1]) > 4);
        const port = (n, toward) => {
          if (!flowAxis([n.x, n.y], toward)) return clip(n, toward);
          if (L.horizontal) return [n.x + Math.sign(toward[0] - n.x) * n.w / 2, n.y];
          return [n.x, n.y + Math.sign(toward[1] - n.y) * n.h / 2];
        };
        const straightA = ["diamond", "circle", "dcircle", "start", "end"].includes(a.shape);
        const straightB = ["diamond", "circle", "dcircle", "start", "end"].includes(b.shape);
        pts[0] = straightA ? clip(a, pts[1]) : port(a, pts[1]);
        pts[pts.length - 1] = straightB ? clip(b, pts[pts.length - 2]) : port(b, pts[pts.length - 2]);
      }
      const cls = "dy-mm-edge" + (e.style === "dotted" ? " dy-mm-dotted" : e.style === "thick" ? " dy-mm-thick" : "");
      svg.appendChild(s("path", { d: e.self ? "M" + pts.map((p) => p.join(",")).join(" L") : curve(pts, L.horizontal), class: cls,
        "marker-end": e.end ? `url(#${id}-${e.end})` : null, "marker-start": e.start ? `url(#${id}-${e.start})` : null }));
      if (e.text) {
        const k = Math.max(0, Math.floor((pts.length - 1) / 2));
        const p = pts[k], q = pts[Math.min(pts.length - 1, k + 1)];
        labels.push([(p[0] + q[0]) / 2 + (e.self ? 30 : 0), (p[1] + q[1]) / 2, e.text]);
      }
    });
    L.nodes.forEach((n) => {
      const look = paint(n, g.classes);
      svg.appendChild(shape(n, look.shape));
      if (n.text) {
        const t = text(n.x, n.y, n.text, "dy-mm-text");
        if (look.color && t.style) t.style.setProperty("fill", look.color);
        svg.appendChild(t);
      }
    });
    labels.forEach(([x, y, value]) => {
      const m = measure(value);
      svg.appendChild(s("rect", { x: x - m.w / 2 - 4, y: y - m.h / 2 - 2, width: m.w + 8, height: m.h + 4, rx: 3, class: "dy-mm-label-bg" }));
      svg.appendChild(text(x, y, value, "dy-mm-label"));
    });
    return svg;
  }

  function draw(source) {
    const d = MM.parse(source);
    return d.kind === "sequence" ? MM.drawSequence(d, { s, text, measure, markers, uid: () => ++uid, LINE }) : drawFlow(d);
  }

  /** The block of a page: drawing + switch to the code, or the reason it cannot be drawn above the code. */
  function figure(source, lang) {
    const code = el("pre", { class: "dy-code dy-mm-code" }, el("span", { class: "dy-code-lang" }, lang || "mermaid"), el("code", null, source));
    let drawing = null, problem = null;
    try { drawing = draw(source); } catch (err) {
      if (!err.mermaid) console.error(err);  // eslint-disable-line no-console
      problem = err.mermaid ? (err.line ? "Ligne " + err.line + " : " : "") + err.message : "Le diagramme n'a pas pu être dessiné (" + err.message + ").";
    }
    if (!drawing) {
      return el("figure", { class: "dy-mm dy-mm-failed", "data-new": "0.60.60-mermaid" },
        el("div", { class: "dy-mm-problem", role: "note" }, el("strong", null, "Diagramme Mermaid non dessiné. "), problem), code);
    }
    const view = el("div", { class: "dy-mm-view" }, drawing);
    code.hidden = true;
    const toggle = el("button", { type: "button", class: "btn btn-small dy-mm-toggle", "aria-pressed": "false" }, "Voir le code");
    toggle.addEventListener("click", () => {
      const showCode = code.hidden;
      code.hidden = !showCode; view.hidden = showCode;
      toggle.textContent = showCode ? "Voir le diagramme" : "Voir le code";
      toggle.setAttribute("aria-pressed", String(showCode));
    });
    return el("figure", { class: "dy-mm", "data-new": "0.60.60-mermaid" },
      el("div", { class: "dy-mm-bar" }, el("span", { class: "dy-code-lang" }, "mermaid"), toggle), view, code);
  }

  Object.assign(MM, { draw, figure, measure });
})();
