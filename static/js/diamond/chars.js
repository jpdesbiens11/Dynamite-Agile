/* Diamond · « Caractéristiques » (0.60.102, D-O-110): #/diamond/KEY/chars -> the summary of the special characteristics
   (one line per C-n whose DFMEA row has a confirmed class, read from the links: nothing typed twice), its Excel and Word
   exports with the customer's symbols; #/diamond/KEY/chars/all -> every characteristic, new ones, the archived ones;
   #/diamond/KEY/chars/C-14 -> the card of one characteristic (char_card.js). */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  function chip(c) {
    if (!c.class_code) return el("span", { class: "dm-cls dm-cls-none" }, "aucune");
    return el("span", { class: "dm-cls dm-cls-" + c.class_code, "data-tip": c.class_label || c.class_code },
      c.class_code === "CC" && !/[∇▼]/.test(c.class_symbol) ? el("span", { class: "dm-cls-mark", "aria-hidden": "true" }, "▼") : null, c.class_symbol);
  }
  const statusBadge = (c) => el("span", { class: "dm-ch-st dm-ch-st-" + c.status }, c.status_label);
  const parts = (c) => (c.part ? [el("span", { "data-tip": c.part_name || null }, c.part + (c.part_name ? " " + c.part_name : "")),
    c.part2 ? el("span", { class: "muted", "data-tip": c.part2_name || null }, " · " + c.part2) : null] : el("span", { class: "dm-ch-miss" }, "à préciser"));
  const cpkReq = (c) => (c.control === "test100" ? "100 %" : c.cpk_req != null ? String(c.cpk_req.toFixed(2)).replace(".", ",") : "—");
  const cpk = (c) => (c.control === "test100" ? el("strong", { class: "dm-ch-ok" }, "essai 100 %") : c.control === "design" ? "—" : el("span", { class: "muted" }, "à mesurer"));
  const later = (tip) => el("span", { class: "muted", "data-tip": tip }, "—");

  async function view(page, ctx) {
    const base = D.base(ctx) + "/characteristics";
    const state = { ctx, base, editable: A.canEdit(ctx), data: await api.get(base) };
    const holder = el("div", { class: "dm-page dm-ch-page" });
    page.append(holder);
    state.redraw = () => D.later(() => draw(holder, state));
    state.send = async (method, path, body, done) => {
      try {
        state.data = await api[method](base + path, body || {});
        if (done) toast(done, "success");
        state.redraw();
        return state.data;
      } catch (err) { toast(err.message, "error"); return null; }
    };
    draw(holder, state);
  }

  function draw(holder, state) {
    clear(holder);
    const ctx = state.ctx, arg = ctx.arg || "";
    if (/^C-?\d+$/i.test(arg)) { D.charCard(holder, state, arg.toUpperCase().replace(/^C-?/, "C-")); return; }
    const all = arg === "all", pn = arg === "pn", d = state.data;  // 0.60.103: « pn » = # de pièce de l'entreprise (pn.js)
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Caractéristiques")], [
      el("a", { class: "btn btn-small", href: D.base(ctx) + "/characteristics/summary.xlsx", download: "", "data-new": "0.60.102-chars-xlsx" }, "Excel"),
      el("a", { class: "btn btn-small", href: D.base(ctx) + "/characteristics/summary.docx", download: "", "data-new": "0.60.102-chars-docx" }, "Word")]),
    el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.102-chars" }, "Caractéristiques"),
      el("p", { class: "muted" }, "Une caractéristique spéciale vit sur une cote précise d'une pièce précise : C-n relie la ligne du DFMEA et sa "
        + "classe, la pièce Diamond (et la seconde pièce d'une interface), le plan, la cote, le Cpk exigé et l'essai. Le sommaire se lit "
        + "des liens : rien n'y est ressaisi.")),
    el("nav", { class: "subtabs", "aria-label": "Vues des caractéristiques" },
      el("a", { href: A.href(ctx, "chars"), class: "subtab" + (all || pn ? "" : " active"), "aria-current": all || pn ? null : "page" }, "Sommaire des caractéristiques spéciales"),
      el("a", { href: A.href(ctx, "chars") + "/all", class: "subtab" + (all ? " active" : ""), "aria-current": all ? "page" : null },
        "Toutes les caractéristiques (" + d.items.length + ")"),
      el("a", { href: A.href(ctx, "chars") + "/pn", class: "subtab" + (pn ? " active" : ""), "aria-current": pn ? "page" : null, "data-new": "0.60.103-pn-tab" },
        "# de pièce de l'entreprise")));
    if (pn) { D.pnView(holder, state); return; }
    if (d.checks.length) {
      holder.append(el("details", { class: "dm-advice", open: true }, el("summary", null, "Conseils de la méthode (" + d.checks.length + ")"),
        el("ul", null, d.checks.map((c) => el("li", null, c)))));
    }
    if (all) list(holder, state); else summary(holder, state);
  }

  function summary(holder, state) {
    const d = state.data, ctx = state.ctx;
    holder.append(el("p", { class: "dm-ch-count" }, el("span", { class: "badge badge-neutral" }, d.counts.CC + " CC · " + d.counts.SC + " SC"),
      " symboles du client : " + d.customer.name + " (" + d.customer.cc_symbol + " / " + d.customer.sc_symbol + ")"));
    if (!d.summary.length) {
      holder.append(DA.spaces.startHere("Aucune caractéristique spéciale", "Confirmez une classe CC ou SC dans le DFMEA, puis « + Caractéristique » "
        + "sur sa ligne : la cote exacte de la pièce qui la porte.", [["Ouvrir le DFMEA", A.href(ctx, "dfmea"), true]]));
      return;
    }
    const head = ["Char.", "Class", "Characteristic", "Specification", "Part (Diamond)", "Company PN", "DFMEA", "PFMEA", "Control Plan", "Cpk req.", "Cpk", "Status"];
    const tips = { "Company PN": "Le # de pièce de l'entreprise, relié à la pièce Diamond (et à la seconde pièce d'une interface)", PFMEA: "La ligne du PFMEA qui protège la caractéristique (à venir)",
      "Control Plan": "La ligne du plan de contrôle (à venir)", Cpk: "Le Cpk mesuré (à venir) ; « essai 100 % » pour une caractéristique testée à 100 %" };
    holder.append(el("div", { class: "dm-scroll" }, el("table", { class: "data dm-ch-table", "data-new": "0.60.102-chars-summary" },
      el("thead", null, el("tr", null, head.map((h) => el("th", { scope: "col", "data-tip": tips[h] || null }, h)))),
      el("tbody", null, d.summary.map((c) => el("tr", { class: "dm-ch-row dm-ch-" + c.class_code },
        el("td", null, el("a", { class: "dm-code", href: A.href(ctx, "chars") + "/" + c.code }, c.code)), el("td", null, chip(c)),
        el("td", null, c.label), el("td", { class: "dm-ch-spec" }, c.spec || el("span", { class: "dm-ch-miss" }, "à écrire")),
        el("td", null, parts(c)), el("td", { class: "dm-ch-pn" }, (c.pns || []).length ? c.pns.join(" · ") : later("Aucun # d'entreprise relié à la pièce : onglet « # de pièce de l'entreprise »")),
        el("td", null, c.dfmea ? el("a", { class: "dm-code", href: A.href(ctx, "dfmea") }, "L" + c.dfmea.line) : "—"),
        el("td", null, later("PFMEA (à venir)")), el("td", null, later("Plan de contrôle (à venir)")),
        el("td", { class: "nowrap" }, cpkReq(c)), el("td", { class: "nowrap" }, cpk(c)), el("td", null, statusBadge(c))))))));
  }

  function list(holder, state) {
    const d = state.data, ctx = state.ctx;
    if (state.editable) {
      holder.append(el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-small btn-primary", "data-new": "0.60.102-chars-new",
        onclick: async () => {
          const res = await state.send("post", "", { label: "Nouvelle caractéristique" }, null);
          if (res) location.hash = A.href(ctx, "chars") + "/" + res.created;
        } }, "Nouvelle caractéristique")));
    }
    if (!d.items.length) {
      holder.append(DA.spaces.startHere("Aucune caractéristique", "Une caractéristique part d'une ligne du DFMEA (« + Caractéristique ») ou d'ici.", []));
    } else {
      holder.append(el("div", { class: "dm-scroll" }, el("table", { class: "data dm-ch-table" },
        el("thead", null, el("tr", null, ["Char.", "Class", "Nature", "Characteristic", "Specification", "Part (Diamond)", "DFMEA", "Contrôle", "Status"]
          .map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", null, d.items.map((c) => el("tr", { class: "dm-ch-row" + (c.class_code ? " dm-ch-" + c.class_code : "") },
          el("td", null, el("a", { class: "dm-code", href: A.href(ctx, "chars") + "/" + c.code }, c.code)), el("td", null, chip(c)),
          el("td", null, d.labels.natures[c.nature] || c.nature), el("td", null, c.label), el("td", { class: "dm-ch-spec" }, c.spec || "—"),
          el("td", null, parts(c)), el("td", null, c.dfmea ? "L" + c.dfmea.line : "—"), el("td", null, d.labels.controls[c.control] || c.control),
          el("td", null, statusBadge(c))))))));
    }
    if (d.archived.length) {
      holder.append(el("details", { class: "dm-ch-archived" }, el("summary", null, "Retirées (" + d.archived.length + ") — leur numéro n'est jamais redonné"),
        el("ul", null, d.archived.map((c) => el("li", null, c.code + " · " + c.label + " ",
          state.editable ? el("button", { type: "button", class: "link-btn", onclick: () => state.send("post", "/" + c.id + "/archive", { archived: false }, c.code + " rétablie.") }, "Rétablir") : null)))));
    }
  }

  DA.diamond = Object.assign(DA.diamond || {}, { charChip: chip, charStatus: statusBadge, charParts: parts, charCpkReq: cpkReq });
  A.views.chars = view;
})();
