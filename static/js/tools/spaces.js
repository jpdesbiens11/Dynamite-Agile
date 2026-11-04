/* Spaces in the left panel and the default Space (core lot v0.27, D-B-098).
   - DA.spaces.enter(module, parts, href): on a tab's opening page (#/<module> with nothing after it), goes straight
     to the person's default Space (location.replace: no history trap) and returns true; #/<module>/spaces always
     shows the list.
   - DA.spaces.sidebar(module, href, current): the Space list of the left panel -- one click enters a Space, the box
     marks it « par défaut » (one default Space for every tab), « Réinitialiser le Space par défaut » at the bottom.
   - DA.spaces.allLink(module): « Tous les Spaces » at the bottom of a module's left panel inside a Space.
   - DA.spaces.picker(active, href): the Space drop-down at the top of a module's left panel (core lot v0.28).
   - DA.spaces.startHere(title, text, actions): the guided empty state of a tab in a Space with nothing yet -- what the
     section is for and the first action (core lot v0.34, D-B-134).
   The default is a personal setting (prefs « default_space »), saved at once. */
(function () {
  "use strict";
  const { api, el, toast } = DA;

  const current = () => (DA.session.prefs && DA.session.prefs.default_space) || "";
  const visible = (key) => DA.session.projects.some((p) => p.key === key);
  const rerender = () => window.dispatchEvent(new HashChangeEvent("hashchange"));  // the current view, drawn again

  async function save(key) {
    const res = await api.put("/api/me/prefs", { default_space: key });
    DA.session.prefs = res.prefs || Object.assign(DA.session.prefs || {}, { default_space: key });
  }

  DA.spaces = {
    defaultKey() { const key = current(); return key && visible(key) ? key : ""; },

    enter(module, parts, href) {
      if ((parts || []).filter(Boolean).length) return false;
      const key = this.defaultKey();
      if (!key) return false;
      location.replace(href(key));
      return true;
    },

    sidebar(module, href, active) {
      const def = this.defaultKey();
      const list = el("ul", { class: "sp-list", "aria-label": "Spaces" });
      DA.session.projects.forEach((p) => {
        /* 0.60.19: the Tools wiki exists in Dynamite only -- as the default of every tab it would open nowhere else */
        const wikiOnly = p.key === DA.wikiOnlyKey;
        const box = el("input", { type: "checkbox", checked: p.key === def, disabled: wikiOnly, "aria-label": "Space par défaut : " + p.key,
          "data-tip": wikiOnly ? "Wiki des outils, ouvert depuis Dynamite seulement : il ne peut pas être le Space par défaut"
            : "Space par défaut : chaque onglet s'ouvre directement sur ce Space" });
        box.addEventListener("change", async () => {
          try {
            await save(box.checked ? p.key : "");
            toast(box.checked ? p.key + " devient votre Space par défaut." : "Plus de Space par défaut.", "success");
            const opening = location.hash.replace(/\/$/, "") === "#/" + module;  // stay on the list, do not jump now
            if (opening) location.replace("#/" + module + "/spaces"); else rerender();
          } catch (err) { toast(err.message, "error"); box.checked = !box.checked; }
        });
        list.append(el("li", { class: "sp-item" + (p.key === active ? " active" : "") }, box,
          el("a", { href: href(p.key), class: "sp-link" }, el("span", { class: "sp-key" }, p.key), el("span", { class: "sp-name" }, p.name))));
      });
      return el("div", { class: "sp-panel", "data-new": "0.50.0-default-space" },
        el("div", { class: "sp-title" }, "Spaces", el("span", { class: "muted sp-hint" }, " · ☑ = par défaut")), list,
        el("button", { type: "button", class: "link-btn sp-reset", disabled: !def, onclick: async () => {
          try { await save(""); toast("Space par défaut réinitialisé : chaque onglet s'ouvre sur la liste des Spaces.", "success");
            if (location.hash === "#/" + module + "/spaces") rerender(); else location.replace("#/" + module + "/spaces"); }
          catch (err) { toast(err.message, "error"); }
        } }, "↺ Réinitialiser le Space par défaut"));
    },

    /* core lot v0.28 (D-B-103): the Space drop-down of a module's left panel, the same as Goldmine and Dynamite; it
       stays visible with a default Space, so the panel always says where one is. href(key) -> address in that Space. */
    picker(active, href) {
      return el("select", { class: "ag-project-picker", "aria-label": "Space", "data-new": "0.50.1-space-picker",
        onchange: (ev) => { location.hash = href(ev.target.value); } },
      DA.session.projects.map((p) => el("option", { value: p.key, selected: p.key === active }, p.key + " · " + p.name)));
    },

    allLink(module) {
      return el("a", { class: "sp-all", href: "#/" + module + "/spaces" }, "▤ Tous les Spaces");
    },

    /* actions: [label, href | function, primary?] (null entries skipped) */
    startHere(title, text, actions) {
      return el("section", { class: "empty sp-start", "data-new": "0.50.14-start-here" },
        el("p", { class: "sp-start-kicker" }, "Commencer ici"), el("h2", null, title), el("p", { class: "muted" }, text),
        el("div", { class: "sp-start-actions" }, (actions || []).filter(Boolean).map(([label, go, primary]) => typeof go === "function"
          ? el("button", { type: "button", class: "btn" + (primary ? " btn-primary" : ""), onclick: go }, label)
          : el("a", { class: "btn" + (primary ? " btn-primary" : ""), href: go }, label))));
    },
  };
})();
