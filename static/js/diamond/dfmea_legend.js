/* Diamond · DFMEA: the legend of the Action Priority (0.60.15, D-O-027), #/diamond/KEY/dfmeaap -- a page of its own (it
   is taller than a dialog may be): what the AP is and why it replaces the RPN, the AP table by severity, occurrence and
   detection bands, the S / O / D scales in short words, and the link to the Training topic. */
(function () {
  "use strict";

  const { api, el } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const SCALE_TITLES = { severity: "Severity (S) — la gravité de l'effet", occurrence: "Occurrence (O) — la probabilité de la cause, avec la prévention",
    detection: "Detection (D) — la capacité du contrôle à trouver la défaillance" };

  const range = (r) => (r[0] === r[1] ? String(r[0]) : r[0] + "–" + r[1]);

  async function view(page, ctx) {
    const data = await api.get(D.base(ctx) + "/dfmea");
    const L = data.legend;
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("a", { href: A.href(ctx, "dfmea") }, "DFMEA"), el("span", null, "Légende AP")]),
      el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.15-ap-page" }, "Action Priority (AP) et RPN"),
        el("p", { class: "muted" }, "Comment lire les deux scores de chaque ligne du DFMEA. L'AP suit le tableau du manuel AIAG-VDA "
          + "(2019) ; avant une revue formelle, vérifiez-le avec votre exemplaire du manuel : c'est lui la référence.")),
      el("section", { class: "dm-ap-why" }, el("h2", null, "Pourquoi l'AP plutôt que le RPN ?"),
        el("p", null, "Le RPN multiplie S × O × D (1 à 1000). Le produit cache la gravité : S 1, O 10, D 10 donne RPN 100, alors que "
          + "S 9, O 4, D 1 ne donne que 36 — pourtant le second touche à la sécurité. L'AP lit d'abord la sévérité, puis l'occurrence, "
          + "puis la détection : un effet grave n'est jamais noyé par une bonne détection."),
        el("ul", { class: "dm-ap-meaning" }, ["H", "M", "L"].map((k) => el("li", null, D.apBadge(k, L.labels), " ", L.meaning[k])))),
      el("section", null, el("h2", null, "Le tableau de l'AP"), apTable(L)),
      el("section", { class: "dm-ap-scales" }, el("h2", null, "Les échelles de 1 à 10"), Object.entries(L.scales).map(([k, rows]) =>
        el("div", { class: "dm-ap-scale" }, el("h3", null, SCALE_TITLES[k]),
          DA.table(["Note", "Ce que ça veut dire"], rows.map((r) => el("tr", null, el("td", { class: "nowrap" }, el("strong", null, range(r.range))),
            el("td", null, r.text)))))),
      el("p", { class: "muted" }, "Échelles résumées pour la formation, pas le texte du manuel ; une équipe peut les préciser pour son produit.")),
      el("div", { class: "dm-actions" }, el("a", { class: "btn btn-primary", href: A.href(ctx, "dfmea") }, "← Retour au DFMEA"),
        el("a", { class: "btn", href: "#/training" }, "Se former : Training → Diamond")));
  }

  function apTable(L) {
    const head = el("tr", null, el("th", { scope: "col" }, "S"), el("th", { scope: "col" }, "O"),
      L.d_bands.map((d) => el("th", { scope: "col", class: "dm-fm-narrow" }, "D " + range(d))));
    const rows = [];
    L.table.forEach((s) => s.rows.forEach((r, i) => rows.push(el("tr", { class: i === 0 ? "dm-ap-band" : null },
      i === 0 ? el("th", { scope: "rowgroup", rowspan: s.rows.length, class: "dm-ap-s" }, range(s.s)) : null,
      el("th", { scope: "row", class: "dm-ap-o" }, range(r.o)),
      r.ap.map((ap) => el("td", { class: "dm-ap-cell dm-ap-" + ap }, L.labels[ap]))))));
    return el("div", { class: "dm-scroll" }, el("table", { class: "data dm-ap-table" }, el("thead", null, head), el("tbody", null, rows)));
  }

  A.views.dfmeaap = view;
})();
