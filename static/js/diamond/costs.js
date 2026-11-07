/* Diamond · « Coûts et budget » (0.60.61, D-O-070): #/diamond/KEY/costs. What the product and the project cost:
   the summary first (the page shown to investors or to the department: budget, unit cost in prototype and at three
   volumes, NRE by category, what is committed), then the assumptions, the NRE and the cost of each part
   (costs_tables.js). « Version investisseurs » prints the summary alone (or saves it as PDF from the print window). */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  function money(cur, digits) {
    const f = new Intl.NumberFormat("fr-CA", { style: "currency", currency: cur || "CAD", maximumFractionDigits: digits === undefined ? 0 : digits,
      minimumFractionDigits: digits === undefined ? 0 : digits });
    return (v) => (v === null || v === undefined || v === "" ? "—" : f.format(Number(v)));
  }
  const int = (v) => new Intl.NumberFormat("fr-CA").format(Number(v || 0));

  async function view(page, ctx) {
    const base = D.base(ctx);
    const state = { data: await api.get(base + "/costs") };
    const holder = el("div", { class: "dm-page dm-costs" });
    page.append(holder);
    const run = async (path, body, method) => {
      try {
        state.data = await api[method || "post"](base + path, body || {});
      } catch (err) { toast(err.message, "error"); }
      D.later(() => draw(holder, ctx, state, run));
    };
    draw(holder, ctx, state, run);
  }

  function draw(holder, ctx, state, run) {
    clear(holder);
    const data = state.data, editable = A.canEdit(ctx);
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Coûts et budget")], [
      el("a", { class: "btn btn-small", href: D.base(ctx) + "/costs/export.csv", download: "" }, "Exporter (.csv)"),
      el("button", { type: "button", class: "btn btn-small", "data-new": "0.60.61-cost-print", onclick: () => printSummary() }, "Version investisseurs (imprimer)")]
      .concat(D.costTools ? D.costTools(ctx, editable, (fresh) => { state.data = fresh; draw(holder, ctx, state, run); }) : [])),
    el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.61-costs" }, "Coûts et budget"),
      el("p", { class: "muted" }, "Combien coûte le produit, et combien coûte le projet. Les NRE (coûts uniques : outillage, moules, essais, "
        + "certification, gabarits…), le coût de chaque pièce en prototype puis en production, le temps de l'équipe (heures de "
        + "Timesheet) : le budget se calcule seul. La synthèse est la page à montrer aux investisseurs ou au département.")));
    holder.append(summary(ctx, data));
    holder.append(D.costTables(ctx, data, run, editable));
  }

  /** Only the summary on paper: a copy of it in a host at the root of the page, the rest of the page not printed. */
  function printSummary() {
    const src = document.querySelector(".dm-cost-summary");
    if (!src) return;
    const host = el("div", { class: "dm-print-host" }, src.cloneNode(true));
    document.body.append(host);
    document.body.classList.add("dm-print-costs");
    const done = () => { document.body.classList.remove("dm-print-costs"); host.remove(); window.removeEventListener("afterprint", done); };
    window.addEventListener("afterprint", done);
    window.print();
    setTimeout(done, 1500);
  }

  function summary(ctx, data) {
    const b = data.budget, s = data.settings, L = data.labels;
    const m = money(b.currency), m2 = money(b.currency, 2);
    const card = (label, value, sub, strong) => el("div", { class: "dm-cost-card" + (strong ? " dm-cost-card-main" : "") },
      el("span", { class: "dm-cost-card-label" }, label), el("strong", null, value), sub ? el("span", { class: "muted" }, sub) : null);
    const cards = el("div", { class: "dm-cost-cards" },
      card("Budget du projet", m(b.total), "contingence de " + b.contingency_pct + " % comprise", true),
      card("NRE", m(b.nre_total), m(b.nre_committed) + " engagés ou payés"),
      card("Coût d'un prototype", m2(b.unit_proto), b.proto_qty + " prototype(s) au budget"),
      card("Coût unitaire en production", m2(b.volumes[b.volumes.length - 1].parts), "à " + int(b.volumes[b.volumes.length - 1].volume) + " unités, sans les NRE"));
    const rows = [["NRE (coûts uniques)", m(b.nre_total)],
      ["Prototypes : " + b.proto_qty + " × " + m2(b.unit_proto), m(b.prototypes)],
      ["Temps de l'équipe : " + String(b.hours).replace(".", ",") + " h × " + m2(b.labour_rate) + "/h", m(b.labour)],
      ["Sous-total", m(b.subtotal)], ["Contingence (" + b.contingency_pct + " %)", m(b.contingency)], ["Budget du projet", m(b.total)]];
    const budget = el("table", { class: "dm-cost-table dm-cost-budget" }, el("tbody", null, rows.map(([k, v], i) =>
      el("tr", { class: i >= rows.length - 1 ? "dm-cost-total" : i === 3 ? "dm-cost-sub" : null }, el("th", { scope: "row" }, k), el("td", { class: "num" }, v)))));
    const vols = el("table", { class: "dm-cost-table" },
      el("thead", null, el("tr", null, el("th", null, "Volume"), el("th", { class: "num" }, "Pièces par unité"), el("th", { class: "num" }, "NRE par unité"),
        el("th", { class: "num" }, "Coût complet par unité"), el("th", { class: "num" }, "Coût du programme"))),
      el("tbody", null, b.volumes.map((v) => el("tr", null, el("th", { scope: "row" }, int(v.volume) + " unités"), el("td", { class: "num" }, m2(v.parts)),
        el("td", { class: "num" }, m2(v.nre_per_unit)), el("td", { class: "num" }, el("strong", null, m2(v.full_unit))), el("td", { class: "num" }, m(v.programme))))));
    const cats = Object.entries(b.nre_by_category).sort((x, y) => y[1] - x[1]);
    const top = Math.max(1, ...cats.map((c) => c[1]));
    const bars = el("div", { class: "dm-cost-bars", role: "list", "aria-label": "NRE par catégorie" }, cats.map(([k, v]) =>
      el("div", { class: "dm-cost-bar", role: "listitem" }, el("span", { class: "dm-cost-bar-label" }, L.categories[k] || k),
        el("span", { class: "dm-cost-bar-track" }, el("span", { class: "dm-cost-bar-fill", style: null, "data-w": String(Math.round((v / top) * 100)) })),
        el("span", { class: "num" }, m(v)))));
    bars.querySelectorAll(".dm-cost-bar-fill").forEach((n) => { n.style.width = n.getAttribute("data-w") + "%"; });
    const phases = Object.entries(b.nre_by_phase).filter(([, v]) => v).sort();
    const box = el("section", { class: "dm-cost-summary", "aria-label": "Synthèse" },
      el("div", { class: "dm-cost-print-title" }, el("h2", null, ctx.meta.project.name + " — budget du projet"),
        el("p", { class: "muted" }, "Montants en " + b.currency + ". " + (s.notes || ""))),
      cards,
      el("div", { class: "dm-cost-grid" },
        el("div", null, el("h3", null, "Budget du projet"), budget),
        el("div", null, el("h3", null, "Coût unitaire selon le volume"), vols,
          el("p", { class: "muted dm-cost-hint" }, "Coût complet = pièces + NRE répartis sur le volume. Le programme = NRE + volume × pièces."))),
      cats.length ? el("div", { class: "dm-cost-grid" },
        el("div", null, el("h3", null, "NRE par catégorie"), bars),
        el("div", null, el("h3", null, "NRE par phase du PDP"), el("table", { class: "dm-cost-table" }, el("tbody", null,
          phases.map(([k, v]) => el("tr", null, el("th", { scope: "row" }, k ? L.phases[k] || k : "Sans phase"), el("td", { class: "num" }, m(v)))))),
          el("p", { class: "muted dm-cost-hint" }, "Déjà payé : " + m(b.nre_paid) + " · engagé (bon de commande) : " + m(b.nre_committed - b.nre_paid) + "."))) : null);
    if (b.checks.length) {
      box.append(el("details", { class: "dm-advice dm-cost-checks", open: true },
        el("summary", null, "À vérifier avant de présenter (" + b.checks.length + ")"), el("ul", null, b.checks.map((c) => el("li", null, c)))));
    }
    return box;
  }

  Object.assign(D, { costMoney: money });
  A.views.costs = view;
})();
