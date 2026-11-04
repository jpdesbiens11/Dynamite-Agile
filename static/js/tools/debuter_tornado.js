/* Dynamite | Agile - the « tornado » of « Débuter » (0.60.09, D-O-021): the project as a rising spiral. Each turn is one
   phase -- one Build-Measure-Learn loop around its MVP, closed by an industry review and the decision to persevere or
   pivot -- wider and higher than the one before, until the product leaves the top at full speed. The SVG holds no text
   (FONDATIONS §5): the legend beside it is HTML. Built with createElementNS (el() makes HTML elements). */
(function () {
  "use strict";

  const { el } = DA;
  const NS = "http://www.w3.org/2000/svg";
  const W = 360, H = 300, CX = 160;

  function svg(tag, attrs) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, String(v)));
    return node;
  }

  /* Point of the spiral at s turns (0 at the bottom, 4 at the top): it climbs and widens like a tornado. */
  function at(s) {
    const rx = 28 + 31 * s, ry = rx * 0.2, cy = H - 34 - 58 * s, a = 2 * Math.PI * s;  // each turn ends on its right edge
    return [CX + rx * Math.cos(a), cy + ry * Math.sin(a)];
  }

  function turn(k) {
    const pts = [];
    for (let i = 0; i <= 60; i += 1) pts.push(at(k + i / 60));
    return "M" + pts.map(([x, y]) => x.toFixed(1) + " " + y.toFixed(1)).join(" L");
  }

  function figure(phases) {
    const drawing = svg("svg", { viewBox: "0 0 " + W + " " + H, class: "dbt-tornado-svg", role: "img",
      "aria-label": "Spirale du projet : une boucle Build-Measure-Learn par phase, de A en bas à D en haut, puis la sortie du produit." });
    const defs = svg("defs");
    const marker = svg("marker", { id: "dbt-arrow", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" });
    marker.append(svg("path", { d: "M0 0 L10 5 L0 10 z", class: "dbt-exit-head" }));
    defs.append(marker);
    drawing.append(defs);
    phases.forEach((p, k) => {
      drawing.append(svg("path", { d: turn(k), class: "dbt-turn dbt-turn-" + p.id }));
      const [x, y] = at(k + 0.5);
      drawing.append(svg("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: 5, class: "dbt-mvp dbt-mvp-" + p.id }));
    });
    const [ex, ey] = at(phases.length);
    drawing.append(svg("path", { d: "M" + ex.toFixed(1) + " " + ey.toFixed(1) + " Q" + (ex + 14) + " " + (ey - 26) + " " + (W - 8) + " 8",
      class: "dbt-exit", "marker-end": "url(#dbt-arrow)" }));
    const legend = el("ul", { class: "dbt-legend" },
      el("li", { class: "dbt-legend-exit" }, el("strong", null, "Sortie : le produit"), el("span", { class: "muted" }, "lancé, puis amélioré par les mêmes boucles")),
      phases.slice().reverse().map((p) => el("li", { class: "dbt-legend-" + p.id },
        el("span", { class: "dbt-chip dbt-chip-" + p.id, "aria-hidden": "true" }),
        el("span", null, el("strong", null, p.id + ". " + p.title), " — " + p.mvp,
          el("span", { class: "muted" }, " Revue : " + p.review + ".")))));
    return el("figure", { class: "dbt-tornado", "data-new": "0.60.09-tornado" },
      el("div", { class: "dbt-tornado-draw" }, drawing),
      el("figcaption", null,
        el("p", { class: "dbt-loop" }, el("strong", null, "Build → Measure → Learn"), " : à chaque phase, construire le MVP qui teste les "
          + "hypothèses les plus risquées, mesurer, apprendre, puis persévérer ou pivoter. Les Sprints Agile rythment le travail "
          + "matériel et logiciel à l'intérieur de chaque boucle."),
        legend));
  }

  DA.debuterTornado = figure;
})();
