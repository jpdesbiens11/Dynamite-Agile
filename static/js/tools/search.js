/* Platform search (core lot v0.7, D-B-022; everywhere + advanced, lot v0.16, D-B-076).
   Top bar: type -> the best matches appear at once (pages, tickets, requirements, needs, changes, comments, Q&A,
   plan tasks, ideas, analyses, references, people, Audit); Enter -> the results page; recent searches on focus.
   Results page #/search/<words>?spaces=..&types=..&in=title&since=..&until=..&open=1&sort=date: search box, advanced
   search (where to look, which results), counts per type (click to filter), words highlighted in the extracts.
   Server: core/search.py + each module's search() hook, limited to the Spaces the user can see. */
(function () {
  "use strict";

  const { api, el, clear, formatDate } = DA;
  const MAX_RECENT = 8;
  const SUGGEST = 8;
  const recentKey = () => "da.search.recent." + ((DA.session && DA.session.user && DA.session.user.id) || "");
  const ADV = ["spaces", "types", "in", "since", "until", "open", "sort"];

  function recent() {
    try { const v = JSON.parse(localStorage.getItem(recentKey()) || "[]"); return Array.isArray(v) ? v : []; }
    catch (err) { return []; }
  }
  function remember(query) {
    const list = [query].concat(recent().filter((q) => q.toLowerCase() !== query.toLowerCase())).slice(0, MAX_RECENT);
    try { localStorage.setItem(recentKey(), JSON.stringify(list)); } catch (err) { /* private window */ }
  }
  function forget() { try { localStorage.removeItem(recentKey()); } catch (err) { /* ignore */ } }

  function hashFor(query, opts) {
    const params = new URLSearchParams();
    ADV.forEach((k) => { if (opts && opts[k]) params.set(k, opts[k]); });
    const tail = params.toString();
    return "#/search/" + encodeURIComponent(query) + (tail ? "?" + tail : "");
  }
  function go(query, opts) {
    query = String(query || "").trim();
    if (!query) return;
    remember(query);
    location.hash = hashFor(query, opts);
  }
  function apiUrl(query, opts) {
    const params = new URLSearchParams({ q: query });
    ADV.forEach((k) => { if (opts && opts[k]) params.set(k, opts[k]); });
    return "/api/search?" + params.toString();
  }

  /* Words of the query, folded like the server (accents and case ignored), without « -excluded » ones */
  const foldChar = (c) => c.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  function queryWords(query) {
    const out = [];
    String(query || "").replace(/(-?)(?:"([^"]+)"|(\S+))/g, (m, neg, phrase, word) => {
      const w = Array.from(phrase || word).map(foldChar).join("");
      if (!neg && w.length >= 2) out.push(w);
      return m;
    });
    return out;
  }
  /* Text with the searched words wrapped in <mark> -- built with text nodes, never HTML */
  function highlight(text, words) {
    const chars = Array.from(String(text || ""));
    const folded = [];
    const owner = [];
    chars.forEach((c, i) => { Array.from(foldChar(c)).forEach((f) => { folded.push(f); owner.push(i); }); });
    const low = folded.join("");
    const on = new Array(chars.length).fill(false);
    words.forEach((w) => {
      let pos = low.indexOf(w);
      while (pos >= 0 && w) {
        for (let k = pos; k < pos + w.length; k++) on[owner[k]] = true;
        pos = low.indexOf(w, pos + w.length);
      }
    });
    const frag = document.createDocumentFragment();
    let buf = "", state = false;
    const flush = () => { if (buf) frag.append(state ? el("mark", null, buf) : document.createTextNode(buf)); buf = ""; };
    chars.forEach((c, i) => { if (on[i] !== state) { flush(); state = on[i]; } buf += c; });
    flush();
    return frag;
  }

  /* ---------- Top-bar box: recent searches, then live suggestions ---------- */
  function searchBox(active) {
    const current = active === "search" ? decodeURIComponent(((location.hash.split("/")[2] || "").split("?")[0])) : "";
    const input = el("input", { type: "search", class: "ts-input", placeholder: "Recherche", maxlength: 200,
      "aria-label": "Rechercher dans toute la plateforme", autocomplete: "off", value: current || null });
    const list = el("div", { class: "menu ts-recent", role: "listbox", hidden: true, "aria-label": "Suggestions" });
    let timer = null, seq = 0;

    function open() {
      document.querySelectorAll(".menu").forEach((m) => { if (m !== list) m.hidden = true; });
      list.hidden = false;
    }
    function showRecent() {
      clear(list);
      const items = recent();
      list.append(items.length
        ? [el("div", { class: "ts-recent-head" }, "Recherches récentes"),
          ...items.map((q) => el("button", { type: "button", class: "menu-item ts-recent-item", role: "option",
            onclick: (ev) => { ev.stopPropagation(); list.hidden = true; input.value = q; go(q); } }, "↺ " + q)),
          el("hr"), el("button", { type: "button", class: "menu-item ts-recent-clear",
            onclick: (ev) => { ev.stopPropagation(); forget(); showRecent(); } }, "Effacer l'historique")]
        : [el("p", { class: "ts-recent-empty" }, "Cherche partout : pages et commentaires, tickets, requirements, needs, tests, PR / ECN, "
          + "questions client, tasks, idées, analyses, références, personnes.")]);
      list.append(el("button", { type: "button", class: "menu-item ts-adv-link",
        onclick: (ev) => { ev.stopPropagation(); list.hidden = true; location.hash = "#/search/?adv=1"; } }, "⚙ Recherche avancée…"));
      open();
    }
    async function suggest() {
      const query = input.value.trim();
      if (queryWords(query).length === 0) { showRecent(); return; }
      const mine = ++seq;
      let data;
      try { data = await api.get(apiUrl(query)); } catch (err) { return; }
      if (mine !== seq) return;  // a newer keystroke won
      clear(list);
      const words = queryWords(query);
      if (!data.results.length) list.append(el("p", { class: "ts-recent-empty" }, "Aucun résultat pour « " + query + " »."));
      data.results.slice(0, SUGGEST).forEach((r) => list.append(el("a", { class: "menu-item ts-suggest", role: "option", href: r.href,
        onclick: () => { list.hidden = true; remember(query); } },
      el("span", { class: "badge ts-kind ts-t-" + r.type }, r.kind), r.project ? el("span", { class: "key" }, r.project) : null,
      el("span", { class: "ts-suggest-title" }, highlight(r.title, words)))));
      list.append(el("hr"), el("button", { type: "button", class: "menu-item ts-all", onclick: (ev) => { ev.stopPropagation(); list.hidden = true; go(query); } },
        "Voir tous les résultats (" + data.total + ") ↵"),
      el("button", { type: "button", class: "menu-item ts-adv-link",
        onclick: (ev) => { ev.stopPropagation(); list.hidden = true; location.hash = hashFor(query) + "?adv=1"; } },
      "⚙ Recherche avancée…"));
      open();
    }

    input.addEventListener("focus", () => (input.value.trim() ? suggest() : showRecent()));
    input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(suggest, 250); });
    input.addEventListener("click", (ev) => ev.stopPropagation());
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") { ev.preventDefault(); list.hidden = true; go(input.value); }
      else if (ev.key === "Escape") { list.hidden = true; input.blur(); }
      else if (ev.key === "ArrowDown") {
        const first = list.querySelector("a, button");
        if (first) { ev.preventDefault(); first.focus(); }
      }
    });
    list.addEventListener("keydown", (ev) => {
      const items = Array.from(list.querySelectorAll("a, button"));
      const i = items.indexOf(document.activeElement);
      if (ev.key === "ArrowDown" && i < items.length - 1) { ev.preventDefault(); items[i + 1].focus(); }
      if (ev.key === "ArrowUp") { ev.preventDefault(); (i > 0 ? items[i - 1] : input).focus(); }
      if (ev.key === "Escape") { list.hidden = true; input.focus(); }
    });
    return el("div", { class: "ts-box", role: "search" }, magnifier("ts-icon"), input, list);
  }

  /* Simple magnifier in Atlassian blue (0.22.0, D-B-054). */
  function magnifier(cls) {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", cls);
    svg.setAttribute("aria-hidden", "true");
    const ring = document.createElementNS(NS, "circle");
    ring.setAttribute("cx", "10"); ring.setAttribute("cy", "10"); ring.setAttribute("r", "6.5");
    const handle = document.createElementNS(NS, "path");
    handle.setAttribute("d", "M15 15l6 6");
    [ring, handle].forEach((n) => { n.setAttribute("fill", "none"); n.setAttribute("stroke", "currentColor");
      n.setAttribute("stroke-width", "2.4"); n.setAttribute("stroke-linecap", "round"); });
    svg.append(ring, handle);
    return svg;
  }

  DA.search = { searchBox, magnifier, highlight, queryWords, hashFor, go, apiUrl, remember };
  DA.topbarTools = DA.topbarTools || [];
  searchBox.order = 10;  // D-B-087: first tool of the top bar
  DA.topbarTools.push(searchBox);
})();
