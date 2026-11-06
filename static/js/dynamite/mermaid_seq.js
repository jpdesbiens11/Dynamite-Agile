/* Dynamite - Mermaid diagrams, part 4: sequence diagrams (0.60.60, D-O-069).
   Columns for the participants (wide enough for the messages between neighbours), one row per message, note or block;
   loop / alt / opt / par / critical / break frames around the rows they hold, their « else » sections dashed. Drawn with
   the helpers of mermaid_svg.js (createElementNS, textContent). */
(function () {
  "use strict";

  const MM = DA.dynamite.mermaid = DA.dynamite.mermaid || {};
  const FRAME_LABEL = { loop: "loop", alt: "alt", opt: "opt", par: "par", critical: "critical", break: "break" };

  function drawSequence(d, h) {
    const { s, text, measure, markers, LINE } = h;
    const id = "dymm" + h.uid();
    const actors = d.actors.map((a, i) => {
      const m = measure(a.text);
      return Object.assign({}, a, { i, w: Math.max(m.w + 24, 90), h: m.h + 18, tw: m.w });
    });
    const at = new Map(actors.map((a) => [a.id, a]));
    // gaps between neighbouring columns, widened for the messages and notes they carry
    const gap = actors.map(() => 40);
    const need = (i, j, width) => {
      const lo = Math.min(i, j), hi = Math.max(i, j);
      if (lo === hi) { gap[lo] = Math.max(gap[lo], width + 40); return; }
      let have = 0;
      for (let k = lo; k < hi; k++) have += actors[k].w / 2 + actors[k + 1].w / 2 + gap[k];
      if (have < width + 30) gap[hi - 1] += width + 30 - have;
    };
    let number = 0;
    d.items.forEach((it) => {
      if (it.type === "message") {
        const w = measure((d.autonumber ? "00 " : "") + it.text).w;
        need(at.get(it.from).i, at.get(it.to).i, it.from === it.to ? w + 20 : w);
      } else if (it.type === "note") {
        const w = measure(it.text).w + 20;
        const idx = it.who.map((x) => at.get(x).i);
        if (it.side === "right of") need(idx[0], idx[0], w);
        else if (it.side === "left of" && idx[0] > 0) need(idx[0] - 1, idx[0], w * 2 - 40);
        else if (idx.length > 1) need(Math.min(...idx), Math.max(...idx), w);
      }
    });
    let x = 20 + Math.max(0, ...d.items.filter((it) => it.type === "note" && it.side === "left of" && at.get(it.who[0]).i === 0)
      .map((it) => measure(it.text).w + 20 - actors[0].w / 2));
    actors.forEach((a, i) => { x += a.w / 2; a.x = x; x += a.w / 2 + (i < actors.length - 1 ? gap[i] : 0); });
    const boxH = Math.max(...actors.map((a) => a.h)) + (actors.some((a) => a.kind === "actor") ? 34 : 0);
    let y = boxH + 24;
    const rows = [], open = [], frames = [];
    const touch = (ids) => open.forEach((f) => ids.forEach((i) => f.who.add(i)));
    d.items.forEach((it) => {
      if (it.type === "message") {
        const m = measure(it.text);
        const self = it.from === it.to;
        y += Math.max(m.h, LINE) + 4;
        rows.push(Object.assign({}, it, { y, self, n: d.autonumber ? ++number : 0 }));
        y += self ? 44 : 22;
        touch([it.from, it.to]);
      } else if (it.type === "note") {
        const m = measure(it.text);
        rows.push(Object.assign({}, it, { y, mh: m.h + 14, mw: m.w + 20 }));
        y += m.h + 14 + 16;
        touch(it.who);
      } else if (it.type === "frame") {
        const f = { kind: it.kind, text: it.text, y0: y, sections: [], who: new Set(), depth: open.length };
        open.push(f); frames.push(f);
        y += 30;
      } else if (it.type === "section") {
        open[open.length - 1].sections.push({ y: y + 4, text: it.text });
        y += 30;
      } else if (it.type === "endframe") {
        const f = open.pop();
        f.y1 = y;
        y += 18;
        if (open.length) f.who.forEach((w) => open[open.length - 1].who.add(w));
      }
    });
    const bottom = y + 8;
    const width = Math.max(...actors.map((a) => a.x + a.w / 2)) + 40
      + Math.max(0, ...rows.filter((r) => r.type === "note" && r.side === "right of").map((r) => r.mw));
    const height = bottom + boxH + 12;
    const svg = s("svg", { viewBox: `0 0 ${width} ${height}`, width, height, class: "dy-mm-svg", role: "img", "aria-label": "Diagramme de séquence" }, [markers(id)]);

    frames.forEach((f) => {
      const who = Array.from(f.who).map((w) => at.get(w));
      const xs = who.length ? who : actors;
      const pad = 18 + (3 - Math.min(3, f.depth)) * 6;
      const x0 = Math.min(...xs.map((a) => a.x)) - Math.max(60, Math.min(...xs.map((a) => a.w)) / 2) - pad + 30;
      const x1 = Math.max(...xs.map((a) => a.x)) + Math.max(60, Math.min(...xs.map((a) => a.w)) / 2) + pad - 30;
      const left = Math.max(4, x0), right = Math.min(width - 4, Math.max(x1, left + 160));
      if (f.kind === "rect") { svg.appendChild(s("rect", { x: left, y: f.y0, width: right - left, height: f.y1 - f.y0, class: "dy-mm-band" })); return; }
      svg.appendChild(s("rect", { x: left, y: f.y0, width: right - left, height: f.y1 - f.y0, class: "dy-mm-frame" }));
      const tag = FRAME_LABEL[f.kind] || f.kind;
      const tw = measure(tag).w + 16;
      svg.appendChild(s("path", { d: `M${left},${f.y0} h${tw} v12 l-6,8 h-${tw - 6} z`, class: "dy-mm-frame-tag" }));
      svg.appendChild(text(left + 6, f.y0 + 10, tag, "dy-mm-frame-text", "start"));
      if (f.text) svg.appendChild(text(left + tw + 10, f.y0 + 10, "[" + f.text + "]", "dy-mm-label", "start"));
      f.sections.forEach((sec) => {
        svg.appendChild(s("line", { x1: left, y1: sec.y, x2: right, y2: sec.y, class: "dy-mm-frame-split" }));
        if (sec.text) svg.appendChild(text(left + 8, sec.y + 12, "[" + sec.text + "]", "dy-mm-label", "start"));
      });
    });
    actors.forEach((a) => svg.appendChild(s("line", { x1: a.x, y1: boxH, x2: a.x, y2: bottom, class: "dy-mm-life" })));
    const head = (a, top, low) => {
      if (a.kind === "actor") {
        const cy = top + 12;
        svg.appendChild(s("g", { class: "dy-mm-stick" }, [s("circle", { cx: a.x, cy, r: 8 }), s("path", { d: `M${a.x},${cy + 8} v16 M${a.x - 12},${cy + 14} h24 `
          + `M${a.x},${cy + 24} l-10,12 M${a.x},${cy + 24} l10,12` })]));
        svg.appendChild(text(a.x, top + 34 + a.h / 2, a.text, "dy-mm-text"));
        return;
      }
      const y0 = low ? top : top + boxH - a.h;
      svg.appendChild(s("rect", { x: a.x - a.w / 2, y: y0, width: a.w, height: a.h, rx: 3, class: "dy-mm-node" }));
      svg.appendChild(text(a.x, y0 + a.h / 2, a.text, "dy-mm-text"));
    };
    actors.forEach((a) => { head(a, 0, false); head(a, bottom, true); });

    rows.forEach((r) => {
      if (r.type === "note") {
        const idx = r.who.map((w) => at.get(w));
        let x0, w = r.mw;
        if (r.side === "right of") x0 = idx[0].x + 8;
        else if (r.side === "left of") x0 = idx[0].x - 8 - w;
        else if (idx.length > 1) { const a = Math.min(...idx.map((p) => p.x)), b = Math.max(...idx.map((p) => p.x)); w = Math.max(w, b - a + 40); x0 = (a + b) / 2 - w / 2; }
        else x0 = idx[0].x - w / 2;
        svg.appendChild(s("rect", { x: x0, y: r.y, width: w, height: r.mh, class: "dy-mm-note" }));
        svg.appendChild(text(x0 + w / 2, r.y + r.mh / 2, r.text, "dy-mm-text"));
        return;
      }
      const a = at.get(r.from), b = at.get(r.to);
      const dotted = r.arrow.includes("--");
      const end = /x$/.test(r.arrow) ? "cross" : />>$|\)$/.test(r.arrow) ? "arrow" : "";
      const start = r.arrow.startsWith("<<") ? "arrow" : "";
      const cls = "dy-mm-edge" + (dotted ? " dy-mm-dotted" : "") + (/\)$/.test(r.arrow) ? " dy-mm-async" : "");
      if (r.self) {
        svg.appendChild(s("path", { d: `M${a.x},${r.y} h36 v26 h-34`, class: cls, "marker-end": end ? `url(#${id}-${end})` : null }));
        svg.appendChild(text(a.x + 44, r.y + 13, r.text, "dy-mm-label", "start"));
      } else {
        const dir = Math.sign(b.x - a.x);
        svg.appendChild(s("line", { x1: a.x, y1: r.y, x2: b.x - dir * 2, y2: r.y, class: cls,
          "marker-end": end ? `url(#${id}-${end})` : null, "marker-start": start ? `url(#${id}-${start})` : null }));
        if (r.text) svg.appendChild(text((a.x + b.x) / 2, r.y - 4 - (r.text.split("\n").length * LINE) / 2, r.text, "dy-mm-label"));
      }
      if (r.n) {
        svg.appendChild(s("circle", { cx: a.x, cy: r.y, r: 9, class: "dy-mm-dot" }));
        svg.appendChild(text(a.x, r.y, String(r.n), "dy-mm-num"));
      }
    });
    return svg;
  }

  MM.drawSequence = drawSequence;
})();
