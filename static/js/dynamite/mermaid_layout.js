/* Dynamite - Mermaid diagrams, part 2: the layout of a flowchart or a state diagram (0.60.60, D-O-069).
   A layered drawing (Sugiyama, simplified): cycles broken by reversing the back edges, ranks by longest path, a dummy
   point on every rank an edge crosses, the order inside each rank improved by barycentres (members of a subgraph kept
   together), then positions pulled towards their neighbours without overlap. Works top-down; LR / RL / BT are the same
   drawing turned. Pure: sizes in, coordinates out -- no DOM (tests/js/mermaid.js runs it under node).

   DY.mermaid.layout(graph, measure) -> { width, height, nodes: [{id, x, y, w, h, …}], edges: [{…, points}], groups: [{…, x, y, w, h}] }
   measure(text) -> { w, h } of a label. */
(function () {
  "use strict";

  const MM = DA.dynamite.mermaid = DA.dynamite.mermaid || {};
  const GAP_RANK = 56, GAP_NODE = 28, PAD = 12, GROUP_PAD = 14, GROUP_TITLE = 22;

  function size(node, measure) {
    const t = measure(node.text || "");
    switch (node.shape) {
      case "start": case "end": return { w: 18, h: 18 };
      case "bar": return { w: 70, h: 8 };
      case "circle": case "dcircle": { const d = Math.max(t.w, t.h) + 28; return { w: d, h: d }; }
      case "diamond": return node.text ? { w: t.w * 1.5 + 30, h: t.h * 1.5 + 26 } : { w: 26, h: 26 };
      case "hexagon": return { w: t.w + 50, h: t.h + 2 * PAD };
      case "lean_r": case "lean_l": case "trapezoid": case "trapezoid_alt": return { w: t.w + 50, h: t.h + 2 * PAD };
      case "cylinder": return { w: t.w + 2 * PAD + 8, h: t.h + 2 * PAD + 14 };
      default: return { w: Math.max(t.w + 2 * PAD + 8, 40), h: t.h + 2 * PAD };
    }
  }

  function layout(g, measure) {
    const horizontal = g.dir === "LR" || g.dir === "RL";
    const nodes = g.nodes.map((n, i) => {
      const s = size(n, measure);
      // the layout is computed top-down; for LR / RL widths and heights swap, then the drawing is turned
      return Object.assign({}, n, { i, w: s.w, h: s.h, lw: horizontal ? s.h : s.w, lh: horizontal ? s.w : s.h, dummy: false });
    });
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const groupOf = new Map();
    (g.groups || []).forEach((gr, gi) => gr.nodes.forEach((id) => { if (!groupOf.has(id)) groupOf.set(id, gi); }));
    const edges = g.edges.filter((e) => byId.has(e.from) && byId.has(e.to)).map((e, k) => Object.assign({}, e, { k }));

    // 1. break cycles: a DFS in declaration order; an edge to a node on the current path is reversed for the ranking
    const out = new Map(nodes.map((n) => [n.id, []]));
    edges.forEach((e) => { if (e.from !== e.to) out.get(e.from).push(e); });
    const state = new Map(), reversed = new Set();
    const visit = (id) => {
      state.set(id, 1);
      out.get(id).forEach((e) => {
        const s = state.get(e.to);
        if (s === 1) reversed.add(e.k);
        else if (!s) visit(e.to);
      });
      state.set(id, 2);
    };
    nodes.forEach((n) => { if (!state.get(n.id)) visit(n.id); });
    const dag = edges.filter((e) => e.from !== e.to).map((e) => (reversed.has(e.k) ? { a: e.to, b: e.from, e } : { a: e.from, b: e.to, e }));

    // 2. ranks: longest path from the sources
    const rank = new Map(nodes.map((n) => [n.id, 0]));
    for (let pass = 0; pass < nodes.length; pass++) {
      let changed = false;
      dag.forEach(({ a, b }) => { if (rank.get(b) < rank.get(a) + 1) { rank.set(b, rank.get(a) + 1); changed = true; } });
      if (!changed) break;
    }
    // pull a source down next to its first successor, so a side input does not float at the top
    nodes.forEach((n) => {
      const ins = dag.filter((d) => d.b === n.id), outs = dag.filter((d) => d.a === n.id);
      if (!ins.length && outs.length) rank.set(n.id, Math.max(rank.get(n.id), Math.min(...outs.map((d) => rank.get(d.b))) - 1));
    });

    // 3. dummy points for edges that cross ranks
    const layers = [];
    const put = (n) => { const r = rank.get(n.id); (layers[r] = layers[r] || []).push(n); };
    nodes.forEach(put);
    const segs = [];  // [{ a, b, edge, rev }] between adjacent ranks
    dag.forEach(({ a, b, e }) => {
      let prev = a;
      const chain = [];
      for (let r = rank.get(a) + 1; r < rank.get(b); r++) {
        const d = { id: "·" + e.k + "·" + r, dummy: true, lw: 8, lh: 8, w: 8, h: 8, i: nodes.length + segs.length };
        byId.set(d.id, d); rank.set(d.id, r); put(d); groupOf.set(d.id, groupOf.get(a) === groupOf.get(b) ? groupOf.get(a) : undefined);
        segs.push({ a: prev, b: d.id }); chain.push(d.id); prev = d.id;
      }
      segs.push({ a: prev, b });
      e.via = chain;
      e.rev = reversed.has(e.k);
    });
    for (let r = 0; r < layers.length; r++) layers[r] = layers[r] || [];

    // 4. order inside the ranks: declaration order grouped by subgraph, then barycentre sweeps
    const groupKey = (n) => { const gi = groupOf.get(n.id); return gi === undefined ? -1 : gi; };
    layers.forEach((L) => L.sort((x, y) => (groupKey(x) - groupKey(y)) || (x.i - y.i)));
    const pos = new Map();
    const index = () => layers.forEach((L) => L.forEach((n, i) => pos.set(n.id, i)));
    index();
    const up = new Map(), down = new Map();
    segs.forEach(({ a, b }) => { (down.get(a) || down.set(a, []).get(a)).push(b); (up.get(b) || up.set(b, []).get(b)).push(a); });
    const bary = (n, side) => { const ns = side.get(n.id) || []; return ns.length ? ns.reduce((s, x) => s + pos.get(x), 0) / ns.length : pos.get(n.id); };
    for (let sweep = 0; sweep < 6; sweep++) {
      const order = sweep % 2 ? layers.slice().reverse() : layers;
      order.forEach((L) => {
        const side = sweep % 2 ? down : up;
        const score = new Map(L.map((n) => [n.id, bary(n, side)]));
        // a group keeps its members together: sort by the group's mean, then by the node's own score
        const gmean = new Map();
        L.forEach((n) => { const k = groupKey(n); const m = gmean.get(k) || [0, 0]; m[0] += score.get(n.id); m[1]++; gmean.set(k, m); });
        L.sort((x, y) => {
          const gx = groupKey(x), gy = groupKey(y);
          if (gx !== gy && gx >= 0 && gy >= 0) return gmean.get(gx)[0] / gmean.get(gx)[1] - gmean.get(gy)[0] / gmean.get(gy)[1];
          return score.get(x.id) - score.get(y.id);
        });
        L.forEach((n, i) => pos.set(n.id, i));
      });
    }

    // 5. coordinates (top-down): y by rank, x pulled towards the neighbours, never overlapping
    const groupGap = (x, y) => (groupKey(x) !== groupKey(y) ? GROUP_PAD * 2 : 0);
    let y = (g.groups || []).length ? GROUP_TITLE + GROUP_PAD : 0;
    const extra = (g.groups || []).length ? GROUP_TITLE : 0;
    layers.forEach((L) => {
      const h = Math.max(8, ...L.map((n) => n.lh));
      L.forEach((n) => { n.ly = y + h / 2; });
      y += h + GAP_RANK + extra * (L.some((n) => !n.dummy) ? 0.5 : 0);
    });
    layers.forEach((L) => {
      let x = 0;
      L.forEach((n, i) => { if (i) x += groupGap(L[i - 1], n); n.lx = x + n.lw / 2; x += n.lw + GAP_NODE; });
    });
    const centerOf = (ids) => ids.reduce((s, id) => s + byId.get(id).lx, 0) / ids.length;
    for (let it = 0; it < 8; it++) {
      const order = it % 2 ? layers.slice().reverse() : layers;
      order.forEach((L) => {
        const side = it % 2 ? down : up;
        L.forEach((n) => { const ns = side.get(n.id) || []; if (ns.length) n.want = centerOf(ns); else n.want = n.lx; });
        // left to right: as close to « want » as the left neighbour allows; then right to left
        L.forEach((n, i) => {
          const min = i ? L[i - 1].lx + L[i - 1].lw / 2 + GAP_NODE + groupGap(L[i - 1], n) + n.lw / 2 : -Infinity;
          n.lx = Math.max(min, n.want);
        });
        for (let i = L.length - 2; i >= 0; i--) {
          const n = L[i], r = L[i + 1];
          const max = r.lx - r.lw / 2 - GAP_NODE - groupGap(n, r) - n.lw / 2;
          if (n.lx > max) n.lx = Math.max(max, n.want < n.lx ? n.want : max);
        }
      });
    }
    // a subgraph box must not cover a node that is not in it: such a node moves out, to the nearer side, and pushes its
    // neighbours along (a member far below can widen the box over a rank where outsiders sit)
    const inside = (gi) => {
      let ids = new Set((g.groups[gi].nodes || []));
      g.groups.forEach((child, ci) => { if (child.parent === g.groups[gi]) membersSet(ci).forEach((id) => ids.add(id)); });
      return ids;
    };
    const membersSet = (gi) => inside(gi);
    (g.groups || []).forEach((gr, gi) => {
      const ids = membersSet(gi);
      const ms = layers.flat().filter((n) => ids.has(n.id) || (n.dummy && groupOf.get(n.id) === gi));
      if (!ms.length) return;
      const x0 = Math.min(...ms.map((n) => n.lx - n.lw / 2)) - GROUP_PAD, x1 = Math.max(...ms.map((n) => n.lx + n.lw / 2)) + GROUP_PAD;
      const r0 = Math.min(...ms.map((n) => rank.get(n.id))), r1 = Math.max(...ms.map((n) => rank.get(n.id)));
      const mid = (x0 + x1) / 2;
      for (let r = r0; r <= r1; r++) {
        const L = layers[r];
        L.forEach((n, i) => {
          if (ids.has(n.id) || (n.dummy && groupOf.get(n.id) === gi)) return;
          if (n.lx + n.lw / 2 <= x0 - GROUP_PAD || n.lx - n.lw / 2 >= x1 + GROUP_PAD) return;
          if (n.lx < mid) {
            n.lx = x0 - GROUP_PAD - n.lw / 2;
            for (let k = i - 1; k >= 0; k--) { const max = L[k + 1].lx - L[k + 1].lw / 2 - GAP_NODE - L[k].lw / 2; if (L[k].lx > max) L[k].lx = max; }
          } else {
            n.lx = x1 + GROUP_PAD + n.lw / 2;
            for (let k = i + 1; k < L.length; k++) { const min = L[k - 1].lx + L[k - 1].lw / 2 + GAP_NODE + L[k].lw / 2; if (L[k].lx < min) L[k].lx = min; }
          }
        });
      }
    });
    const all = layers.flat();
    const minX = Math.min(...all.map((n) => n.lx - n.lw / 2));
    all.forEach((n) => { n.lx -= minX - GROUP_PAD; });

    // 6. turn the drawing for LR / RL / BT
    const H = y - GAP_RANK, W = Math.max(...all.map((n) => n.lx + n.lw / 2)) + GROUP_PAD;
    const place = (n) => {
      if (g.dir === "LR") { n.x = n.ly; n.y = n.lx; } else if (g.dir === "RL") { n.x = H - n.ly; n.y = n.lx; }
      else if (g.dir === "BT") { n.x = n.lx; n.y = H - n.ly; } else { n.x = n.lx; n.y = n.ly; }
    };
    all.forEach(place);

    // 7. edges: through their dummy points
    const outEdges = edges.map((e) => {
      if (e.from === e.to) {
        const n = byId.get(e.from);
        return Object.assign({}, e, { self: true, points: [[n.x + n.w / 2, n.y - 6], [n.x + n.w / 2 + 22, n.y - 6], [n.x + n.w / 2 + 22, n.y + 6], [n.x + n.w / 2, n.y + 6]] });
      }
      const via = (e.via || []).map((id) => byId.get(id));
      const chain = e.rev ? via.slice().reverse() : via;
      const pts = [byId.get(e.from)].concat(chain, [byId.get(e.to)]).map((n) => [n.x, n.y]);
      return Object.assign({}, e, { points: pts });
    });

    // 8. subgraph boxes around their members (nested ones included)
    const boxes = (g.groups || []).map((gr) => Object.assign({}, gr, { members: [] }));
    const membersOf = (gi) => {
      const gr = g.groups[gi];
      let ids = gr.nodes.slice();
      g.groups.forEach((child, ci) => { if (child.parent === gr) ids = ids.concat(membersOf(ci)); });
      return ids;
    };
    const depth = (gr) => (gr.parent ? 1 + depth(gr.parent) : 0);
    boxes.forEach((b, gi) => {
      const ms = membersOf(gi).map((id) => byId.get(id)).filter(Boolean);
      if (!ms.length) { b.hidden = true; return; }
      const inner = g.groups.filter((c) => c.parent === g.groups[gi]).length ? GROUP_PAD : 0;
      const x0 = Math.min(...ms.map((n) => n.x - n.w / 2)) - GROUP_PAD - inner, x1 = Math.max(...ms.map((n) => n.x + n.w / 2)) + GROUP_PAD + inner;
      const y0 = Math.min(...ms.map((n) => n.y - n.h / 2)) - GROUP_PAD - GROUP_TITLE - inner, y1 = Math.max(...ms.map((n) => n.y + n.h / 2)) + GROUP_PAD + inner;
      Object.assign(b, { x: x0, y: y0, w: x1 - x0, h: y1 - y0, depth: depth(g.groups[gi]) });
    });
    const real = all.filter((n) => !n.dummy);
    const shown = boxes.filter((b) => !b.hidden);
    const minAll = [Math.min(0, ...shown.map((b) => b.x)), Math.min(0, ...shown.map((b) => b.y))];
    const shift = (p) => [p[0] - minAll[0] + 4, p[1] - minAll[1] + 4];
    real.forEach((n) => { [n.x, n.y] = shift([n.x, n.y]); });
    outEdges.forEach((e) => { e.points = e.points.map(shift); });
    shown.forEach((b) => { [b.x, b.y] = shift([b.x, b.y]); });
    const width = Math.max(...real.map((n) => n.x + n.w / 2), ...shown.map((b) => b.x + b.w), ...outEdges.flatMap((e) => e.points.map((p) => p[0]))) + 30;
    const height = Math.max(...real.map((n) => n.y + n.h / 2), ...shown.map((b) => b.y + b.h), ...outEdges.flatMap((e) => e.points.map((p) => p[1]))) + 10;
    return { width, height, nodes: real, edges: outEdges, groups: shown.sort((a, b) => a.depth - b.depth), horizontal };
  }

  MM.layout = layout;
})();
