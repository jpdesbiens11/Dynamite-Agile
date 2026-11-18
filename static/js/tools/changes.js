/* « Changements » #/changes/<KEY> (core lot v0.39, 0.60.120, D-O-133): every change of a Space, by hand or by an AI
   assistant, newest first -- when, who (three letters), how, the tab, the item (a link that opens its page and points at
   it), what changed and whether it is new for me. Filters: since (my last visit, days, a date, a revision), tab, person,
   source, new only. « Tout marquer vu » moves my last visit to now; opening an item marks its line « Vu ». el() only. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const state = { since: "visit", tab: "", who: "", source: "", news: false };
  const SOURCES = { "": ["à la main", "neutral"], ai: ["IA", "info"], import: ["fichier", "neutral"] };

  function when(ts) {
    const d = new Date(ts);
    if (isNaN(d)) return ts;
    return d.toLocaleDateString("fr-CA", { day: "numeric", month: "short" }) + " " + d.toLocaleTimeString("fr-CA", { hour: "2-digit", minute: "2-digit" });
  }

  function query(key) {
    const q = new URLSearchParams({ space: key, since: state.since });
    if (state.tab) q.set("tab", state.tab);
    if (state.who) q.set("who", state.who);
    if (state.source) q.set("source", state.source);
    if (state.news) q.set("state", "new");
    return "/api/changes?" + q.toString();
  }

  async function ack(key, ids) {
    try { await api.post("/api/changes/ack", { space: key, ids }); DA.changesCount.forget(key); } catch (err) { /* the link still opens */ }
  }

  function select(label, value, options, onchange) {
    const node = el("select", { "aria-label": label }, options.map(([v, text]) => el("option", { value: v, selected: v === value }, text)));
    node.addEventListener("change", () => onchange(node.value));
    return el("label", { class: "chg-filter" }, el("span", { class: "muted" }, label), node);
  }

  function filters(data, key, redraw) {
    const since = [["visit", data.seen_at ? "Depuis ma dernière visite" : "Les 7 derniers jours"], ["7", "7 jours"], ["30", "30 jours"],
      ["90", "90 jours"], ["all", "Depuis le début"]].concat((data.revisions || []).map((r) => [r, "Depuis la révision " + r]));
    const set = (name) => (v) => { state[name] = v; redraw(); };
    const news = el("input", { type: "checkbox", checked: state.news, "aria-label": "Seulement les nouveautés" });
    news.addEventListener("change", () => { state.news = news.checked; redraw(); });
    return el("div", { class: "chg-filters", "data-new": "0.60.120-changes-filters" },
      select("Période", state.since, since, set("since")),
      select("Onglet", state.tab, [["", "Tous"]].concat(data.tabs.map((t) => [t.key, t.label])), set("tab")),
      select("Qui", state.who, [["", "Tout le monde"]].concat(data.people.map((p) => [p, p])), set("who")),
      select("Source", state.source, [["", "Toutes"], ["manual", "À la main"], ["ai", "IA"], ["import", "Fichier"]], set("source")),
      el("label", { class: "chg-filter chg-check" }, news, el("span", null, "Seulement les nouveautés")));
  }

  function row(ln, key, redraw) {
    const [srcText, srcKind] = SOURCES[ln.source] || SOURCES[""];
    const label = [ln.code, ln.title].filter(Boolean).join(" · ") || ln.tab_label;
    const link = el("a", { href: ln.href, class: "chg-item", onclick: (ev) => {
      if (!ln.new) return;
      ev.preventDefault();
      ack(key, ln.ids).then(() => { location.href = ln.href; });
    } }, label);
    const seen = ln.new ? el("button", { type: "button", class: "btn btn-small", "data-tip": "Marquer cette ligne vue",
      onclick: async () => {
        await ack(key, ln.ids);
        redraw();
      } }, "Vu") : null;
    return el("tr", { class: ln.new ? "chg-new" : null },
      el("td", { class: "chg-when" }, when(ln.ts)),
      el("td", null, el("span", { class: "chg-who", "data-tip": ln.user || ln.initials }, ln.initials)),
      el("td", null, DA.badge(srcText, srcKind)),
      el("td", null, ln.tab_label),
      el("td", null, link, ln.gone ? el("span", { class: "muted" }, " (retiré)") : null),
      el("td", null, ln.verb + (ln.count > 1 ? " ×" + ln.count : ""),
        ln.fields.length ? el("div", { class: "muted chg-fields" }, "Champs : " + ln.fields.join(", ")) : null),
      el("td", { class: "chg-state" }, ln.new ? DA.badge("New", "warn") : el("span", { class: "muted" }, ln.seen ? "Vu" : "—"), seen));
  }

  async function draw(page, key) {
    let data;
    try { data = await api.get(query(key)); } catch (err) { clear(page); page.append(el("p", { class: "form-error" }, err.message)); return; }
    const redraw = () => draw(page, key);
    clear(page);
    const allSeen = el("button", { type: "button", class: "btn btn-primary", "data-new": "0.60.120-changes-seen",
      onclick: async () => {
        try { await api.post("/api/changes/seen", { space: key }); toast("Tout est marqué vu pour " + key + ".", "success"); DA.changesCount.forget(key); redraw(); }
        catch (err) { toast(err.message, "error"); }
      } }, "Tout marquer vu");
    page.append(el("div", { class: "page-head chg-head" },
      el("div", null,
        el("h1", { "data-new": "0.60.120-changes" }, "Changements · " + data.space.key),
        el("p", { class: "muted" }, "Tout ce qui a changé dans " + data.space.name + ", à la main ou par une IA, " + data.since
          + " : où (le lien ouvre la page et montre l'élément), qui (les 3 lettres) et quoi. « New » : fait par quelqu'un d'autre "
          + "depuis votre dernière visite.")),
      el("div", { class: "chg-actions" }, allSeen)),
    filters(data, key, redraw));
    if (!data.lines.length) {
      page.append(el("div", { class: "empty" }, el("p", null, state.news || state.tab || state.who || state.source
        ? "Aucun changement avec ces filtres. Élargissez la période ou retirez un filtre."
        : "Aucun changement " + data.since + ". Choisissez une période plus longue pour voir l'historique."),
      el("button", { type: "button", class: "btn", onclick: () => { Object.assign(state, { since: "30", tab: "", who: "", source: "", news: false }); redraw(); } },
        "Voir les 30 derniers jours")));
      return;
    }
    page.append(el("p", { class: "muted chg-count" }, data.total + " ligne" + (data.total > 1 ? "s" : "") + " · " + data.new + " nouveauté"
      + (data.new > 1 ? "s" : "") + (data.more ? " · les " + data.lines.length + " plus récentes affichées" : "")),
    el("table", { class: "data chg-table" },
      el("thead", null, el("tr", null, ["Date", "Qui", "Source", "Onglet", "Élément", "Changement", "État"].map((h) => el("th", null, h)))),
      el("tbody", null, data.lines.map((ln) => row(ln, key, redraw)))));
  }

  function render(main, parts) {
    const key = String(parts[0] || "").toUpperCase() || (DA.spaces && DA.spaces.workKey()) || "";
    const projects = (DA.session && DA.session.projects) || [];
    if (!parts[0] && key) { location.replace("#/changes/" + key); return; }
    const page = DA.moduleLayout(main, { label: "Changements", picker: key ? DA.spaces.picker(key, (k) => "#/changes/" + k) : null,
      nav: [[key ? "#/changes/" + key : "#/changes", "Changements", true], ["#/dashboard", "Dashboard", false]] });
    if (!key) {
      page.append(el("div", { class: "page-head" }, el("h1", null, "Changements"),
        el("p", { class: "muted" }, "Choisissez un Space pour voir ce qui y a changé.")),
      el("ul", { class: "chg-spaces" }, projects.map((p) => el("li", null, el("a", { href: "#/changes/" + p.key }, p.key + " · " + p.name)))));
      return;
    }
    draw(page, key);
  }

  DA.coreViews = DA.coreViews || {};
  DA.coreViews.changes = render;
})();
