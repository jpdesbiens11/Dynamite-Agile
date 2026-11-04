/* [new] tags (core lot v0.21, D-A-049). An update marks what it adds with data-new="<version>-<key>":
   - a field (input, select, textarea): « [new] » next to it while it is empty, to make people fill it;
   - a function (button, link, tab, section): « [new] » until the person uses it once (kept per account).
   No module code: this file watches the page. */
(function () {
  "use strict";
  let seen = null;
  const isField = (n) => n.matches("input, select, textarea");

  function tag(n) {
    let badge = n._newBadge;
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "new-tag";
      badge.textContent = "[new]";
      badge.title = isField(n) ? "Nouveau champ : à remplir" : "Nouvelle fonction";
      n._newBadge = badge;
      if (isField(n)) {
        const label = n.closest("label") || n.parentElement;
        const host = label && label.firstChild && label.firstChild.nodeType === 3 ? label : n.parentElement;
        (host.querySelector(":scope > .field-label, :scope > span") || host).append(badge);
        n.addEventListener("input", () => update(n));
        n.addEventListener("change", () => update(n));
      } else {
        n.append(badge);
        n.addEventListener("click", () => {
          const id = n.getAttribute("data-new");
          if (seen && !seen.has(id)) { seen.add(id); DA.api.post("/api/new/seen", { id }).catch(() => {}); }
          update(n);
        });
      }
    }
    update(n);
  }
  function update(n) {
    const badge = n._newBadge;
    if (!badge) return;
    const id = n.getAttribute("data-new");
    badge.hidden = isField(n) ? String(n.value || "").trim() !== "" : !!(seen && seen.has(id));
    n.classList.toggle("is-new", !badge.hidden);
  }
  function scan(root) {
    if (!seen || !(root instanceof Element)) return;
    if (root.hasAttribute("data-new")) tag(root);
    root.querySelectorAll("[data-new]").forEach(tag);
  }
  async function load() {
    if (seen || !window.DA || !DA.session || !DA.session.user) return;
    try { seen = new Set((await DA.api.get("/api/new/seen")).seen); } catch (err) { return; }
    scan(document.body);
  }
  new MutationObserver((records) => {
    if (!seen) { load(); return; }
    records.forEach((r) => r.addedNodes.forEach(scan));
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
