/* Platform search results page (D-B-076): #/search/<words>?spaces=..&types=..&in=title&since=..&until=..&open=1&sort=date
   Search box, advanced search (Spaces, result types, titles only, dates, open items only, sort), counts per type that
   filter on click, results by relevance (or date) with the searched words highlighted. */
(function () {
  "use strict";

  const { api, el, clear, formatDate, field } = DA;
  const S = () => DA.search;

  function parse(parts) {
    const raw = parts.join("/");
    const cut = raw.indexOf("?");
    const query = decodeURIComponent(cut >= 0 ? raw.slice(0, cut) : raw).trim();
    const params = new URLSearchParams(cut >= 0 ? raw.slice(cut + 1) : "");
    const opts = {};
    ["spaces", "types", "in", "since", "until", "open", "sort", "adv"].forEach((k) => { if (params.get(k)) opts[k] = params.get(k); });
    return { query, opts };
  }

  function advancedPanel(query, opts, types, run) {
    const spaces = DA.session.projects.slice().sort((a, b) => a.key.localeCompare(b.key));
    const chosenSpaces = new Set((opts.spaces || "").split(",").filter(Boolean));
    const chosenTypes = new Set((opts.types || "").split(",").filter(Boolean));
    const spaceBoxes = spaces.map((p) => el("label", { class: "check ts-opt" },
      el("input", { type: "checkbox", value: p.key, checked: chosenSpaces.has(p.key) }), p.key + " · " + p.name));
    const groups = {};
    Object.entries(types).forEach(([code, t]) => { (groups[t.group] = groups[t.group] || []).push([code, t.label]); });
    const typeBoxes = [];
    const typeCols = Object.entries(groups).map(([group, list]) => el("div", { class: "ts-type-group" }, el("strong", null, group),
      list.map(([code, label]) => {
        const box = el("input", { type: "checkbox", value: code, checked: chosenTypes.has(code) });
        typeBoxes.push(box);
        return el("label", { class: "check ts-opt" }, box, label);
      })));
    const where = el("select", null, el("option", { value: "" }, "Tout le contenu (titres, textes, champs, commentaires)"),
      el("option", { value: "title", selected: opts.in === "title" }, "Titres et clés seulement"));
    const since = el("input", { type: "date", value: opts.since || "" });
    const until = el("input", { type: "date", value: opts.until || "" });
    const openOnly = el("input", { type: "checkbox", checked: !!opts.open });
    const sort = el("select", null, el("option", { value: "" }, "Pertinence"), el("option", { value: "date", selected: opts.sort === "date" }, "Date de modification"));
    const words = el("input", { type: "search", value: query, maxlength: 200, placeholder: "Mots, \"phrase exacte\", -exclu, EQP-12" });
    const setAll = (boxes, on) => boxes.forEach((b) => { b.checked = on; });
    const apply = (ev) => {
      if (ev) ev.preventDefault();
      const pick = (boxes) => boxes.filter((b) => b.checked).map((b) => b.value);
      const sp = pick(spaceBoxes.map((l) => l.querySelector("input")));
      const ty = pick(typeBoxes);
      run(words.value, {
        spaces: sp.length && sp.length < spaces.length ? sp.join(",") : "",
        types: ty.length && ty.length < typeBoxes.length ? ty.join(",") : "",
        in: where.value, since: since.value, until: until.value, open: openOnly.checked ? "1" : "", sort: sort.value, adv: "1" });
    };
    return el("form", { class: "ag-form ts-adv", onsubmit: apply },
      el("div", { class: "form-row" }, field("Rechercher", words), field("Chercher dans", where), field("Trier par", sort)),
      el("div", { class: "ts-adv-cols" },
        el("fieldset", { class: "ts-fieldset" }, el("legend", null, "Où : Spaces"),
          el("div", { class: "ts-adv-links" }, el("button", { type: "button", class: "link-btn", onclick: () => setAll(spaceBoxes.map((l) => l.querySelector("input")), true) }, "tous"),
            el("button", { type: "button", class: "link-btn", onclick: () => setAll(spaceBoxes.map((l) => l.querySelector("input")), false) }, "aucun = tous")),
          el("div", { class: "ts-opts" }, spaceBoxes)),
        el("fieldset", { class: "ts-fieldset ts-fieldset-wide" }, el("legend", null, "Quoi : types de résultats"),
          el("div", { class: "ts-adv-links" }, el("button", { type: "button", class: "link-btn", onclick: () => setAll(typeBoxes, true) }, "tous"),
            el("button", { type: "button", class: "link-btn", onclick: () => setAll(typeBoxes, false) }, "aucun = tous")),
          el("div", { class: "ts-type-groups" }, typeCols))),
      el("div", { class: "form-row" }, field("Modifié depuis le", since), field("Modifié avant le", until),
        el("label", { class: "check ts-open" }, openOnly, "Masquer les éléments fermés, terminés ou annulés")),
      el("p", { class: "muted ts-syntax" }, "Syntaxe : tous les mots doivent apparaître (accents et majuscules ignorés) ; \"coupure "
        + "thermique\" = phrase exacte ; -collage = exclure ; une clé (EQP-12, REQ-012, Qteam-003) remonte en premier. "
        + "Aucune case cochée = partout."),
      el("div", { class: "form-actions" },
        el("a", { class: "btn", href: S().hashFor(query) }, "Réinitialiser les filtres"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Rechercher")));
  }

  async function render(main, parts) {
    const { query, opts } = parse(parts);
    const run = (q, o) => { S().go(q, o); if (!String(q || "").trim()) location.hash = "#/search/?adv=1"; };
    const filtered = ["spaces", "types", "in", "since", "until", "open", "sort"].some((k) => opts[k]);
    const holder = el("div", { "aria-live": "polite" }, el("p", { class: "muted" }, query ? "Recherche…" : ""));
    const quick = el("input", { type: "search", class: "ts-page-input", value: query, maxlength: 200,
      placeholder: "Rechercher partout…", "aria-label": "Rechercher" });
    quick.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); run(quick.value, opts); } });
    const details = el("details", { class: "ts-adv-box", open: !!(opts.adv || filtered || !query) },
      el("summary", null, "⚙ Recherche avancée" + (filtered ? " (filtres actifs)" : "")));
    main.append(el("div", { class: "page-head ts-head" }, S().magnifier("ts-page-mark"),
      el("div", { class: "ts-head-main" }, el("h1", null, query ? "Recherche : « " + query + " »" : "Recherche"),
        el("div", { class: "ts-page-row" }, quick, el("button", { type: "button", class: "btn btn-primary", onclick: () => run(quick.value, opts) }, "Rechercher")),
        el("p", { class: "muted" }, "Partout où vous avez accès : pages et commentaires Dynamite, tickets et commentaires, requirements et "
          + "needs, tests Testing, PR / bugs / ECN, questions client, tasks Exploration, idées et analyses Tools, références Generator, "
          + "personnes et observations Audit."))), details, holder);

    let data;
    try { data = await api.get(S().apiUrl(query || "", opts)); }
    catch (err) { clear(holder); holder.append(el("div", { class: "empty" }, el("p", null, err.message))); return; }
    details.append(advancedPanel(query, opts, data.types, run));
    clear(holder);
    if (!query) { holder.append(el("p", { class: "muted" }, "Tapez des mots-clés, choisissez où chercher et quels résultats, puis « Rechercher »."));
      return; }
    S().remember(query);
    const words = S().queryWords(query);
    if (!data.results.length) {
      holder.append(el("div", { class: "empty" }, el("p", null, "Aucun résultat pour « " + query + " »" + (filtered ? " avec ces filtres." : ".")),
        el("p", { class: "muted" }, "Tous les mots doivent apparaître. Essayez moins de mots, un mot plus court"
          + (filtered ? ", ou « Réinitialiser les filtres »." : "."))));
      return;
    }
    const current = new Set((opts.types || "").split(",").filter(Boolean));
    const chips = el("div", { class: "ts-facets" }, Object.entries(data.counts).sort((a, b) => b[1] - a[1]).map(([code, n]) =>
      el("a", { class: "ts-facet ts-t-" + code + (current.size === 1 && current.has(code) ? " active" : ""),
        href: S().hashFor(query, Object.assign({}, opts, { types: current.size === 1 && current.has(code) ? "" : code })),
        title: "Afficher seulement ce type (clic de nouveau : tout)" }, data.types[code].label + " ", el("strong", null, String(n)))));
    holder.append(el("p", { class: "ts-total" }, el("strong", null, data.total + " résultat(s)"),
      data.truncated ? el("span", { class: "muted" }, " — les " + data.results.length + " plus pertinents affichés ; affinez avec la recherche avancée.") : ""),
    chips,
    el("ul", { class: "ts-results" }, data.results.map((r) => el("li", { class: "ts-result" + (r.closed ? " ts-closed" : "") },
      el("div", { class: "ts-result-top" },
        el("span", { class: "badge ts-kind ts-t-" + r.type }, r.kind), r.project ? el("span", { class: "key" }, r.project) : null,
        el("a", { href: r.href, class: "ts-title" }, S().highlight(r.title, words)),
        r.extra ? el("span", { class: "badge ts-extra" }, r.extra) : null, r.closed ? el("span", { class: "muted" }, "fermé") : null),
      r.snippet ? el("p", { class: "ts-snippet" }, S().highlight(r.snippet, words)) : null,
      r.updated_at ? el("span", { class: "muted ts-date" }, "Modifié le " + formatDate(r.updated_at)) : null))));
  }

  DA.coreViews = DA.coreViews || {};
  DA.coreViews.search = render;
})();
