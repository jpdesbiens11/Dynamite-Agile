/* « Changements (n) » in the left panel of every tab (core lot v0.39, 0.60.120, D-O-133): under the Space drop-down of a
   module (any select[aria-label="Space"] of a left panel), a link to #/changes/<KEY> with what is new for me there. The
   count is asked once a minute per Space at most; « Tout marquer vu » forgets it. No module has to know about it. */
(function () {
  "use strict";

  const { api, el } = DA;
  const cache = {};
  const TTL = 60000;

  DA.changesCount = {
    async get(key) {
      const hit = cache[key];
      if (hit && Date.now() - hit.at < TTL) return hit.value;
      const value = api.get("/api/changes/count?space=" + encodeURIComponent(key)).then((r) => r.new).catch(() => 0);
      cache[key] = { at: Date.now(), value };
      return value;
    },
    forget(key) { delete cache[key]; },
  };

  function place(select) {
    const key = select.value;
    const anchor = select.closest(".sp-picker-row") || select;
    const next = anchor.nextElementSibling;
    if (next && next.classList.contains("chg-side")) {
      if (next.dataset.key === key) return;
      next.remove();
    }
    if (!key || location.hash.startsWith("#/changes")) return;
    const count = el("span", { class: "badge badge-warn chg-side-count", hidden: true });
    const link = el("a", { class: "chg-side", href: "#/changes/" + key, "data-key": key, "data-new": "0.60.120-changes-link",
      "data-tip": "Ce qui a changé dans " + key + " depuis votre dernière visite" }, "Changements", count);
    anchor.after(link);
    DA.changesCount.get(key).then((n) => {
      if (n) { count.textContent = String(n); count.hidden = false; }
    });
  }

  let timer = null;
  function scan() {
    timer = null;
    document.querySelectorAll(':is(.ag-sidebar, .dy-sidebar) select[aria-label="Space"]').forEach(place);
  }

  function start() {
    const main = document.getElementById("main") || document.body;
    new MutationObserver(() => { if (!timer) timer = setTimeout(scan, 120); }).observe(main, { childList: true, subtree: true });
    document.addEventListener("change", (ev) => { if (ev.target.matches && ev.target.matches('select[aria-label="Space"]')) scan(); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
