/* Personal settings (core lot v0.10, D-B-028): applied on every page load
   and as soon as a value changes (auto-save, no « Enregistrer » button),
   stored on the server so they follow the person on every computer.
   Also the « Mes éléments » switch of the top bar (D-B-033). */
(function () {
  "use strict";

  const { api, el, clear, toast, field } = DA;
  let current = {};

  /* ---------- Apply ---------- */
  /* 0.60.66: the guest account is shared and read-only -- its language lives in this browser only (FR | EN works) */
  const GUEST_LANG = "da.guest.lang";
  const isGuest = () => !!(DA.session && DA.session.user && DA.session.user.is_guest);
  DA.applyPrefs = function (prefs) {
    current = Object.assign({}, prefs || {});
    if (isGuest()) {
      try { current.language = localStorage.getItem(GUEST_LANG) || current.language; } catch (err) { /* private window */ }
    }
    const html = document.documentElement;
    const set = (name, value, neutral) => {
      if (!value || value === neutral) html.removeAttribute(name); else html.setAttribute(name, value);
    };
    /* D-B-087: the default theme (key « carnet ») = the Atlassian base + the hand-drawn layer of sketch.css */
    const carnet = current.theme === "carnet";
    const terminal = current.theme === "terminal";  // D-B-088: « Terminal R&D » = the dark base + terminal.css
    set("data-theme", carnet ? "atlassian" : terminal ? "dark" : current.theme, "system");
    set("data-sketch", carnet ? "carnet" : "", "");
    set("data-term", terminal ? "on" : "", "");
    try { localStorage.setItem("da.theme", current.theme || ""); } catch (err) { /* private window: ignored */ }
    if (DA.refreshIcons) DA.refreshIcons();
    set("data-font", current.font, "system");
    set("data-size", current.font_size, "100");
    set("data-density", current.density, "comfortable");
    DA.setLanguage(current.language || "fr");  // 0.60.48 (D-O-057): FR | EN in the top bar (langswitch.js)
  };
  DA.prefs = () => current;

  async function save(changes) {
    if (isGuest()) {  // 0.60.66: nothing is written on the server for a guest; the language stays in the browser
      if (changes.language) { try { localStorage.setItem(GUEST_LANG, changes.language); } catch (err) { /* ignored */ } }
      DA.applyPrefs(Object.assign({}, current, changes));
      return current;
    }
    const res = await api.put("/api/me/prefs", changes);
    DA.applyPrefs(res.prefs);
    if (DA.session) DA.session.prefs = res.prefs;
    return res.prefs;
  }
  DA.savePrefs = save;

  /* ---------- « Mes éléments »: only my tickets and tasks, everywhere ---------- */
  DA.myItems = () => !!current.my_items;
  DA.setMyItems = async function (value) {
    try {
      await save({ my_items: !!value });
      window.dispatchEvent(new Event("hashchange"));  // re-render the current screen with the filter
    } catch (err) { toast(err.message, "error"); }
  };
  /* Small reminder a filtered list shows at its top. */
  DA.mineBanner = function () {
    if (!DA.myItems()) return null;
    return el("p", { class: "mine-banner", role: "status" }, DA.t("tools.mineOn"),
      el("button", { type: "button", class: "link-btn", onclick: () => DA.setMyItems(false) }, DA.t("dash.all")));
  };

  function mineToggle() {
    const on = DA.myItems();
    return el("button", { type: "button", class: "tb-mine", "aria-pressed": on ? "true" : "false",
      title: on ? DA.t("tools.mineOn") : DA.t("tools.mineOff"), onclick: () => DA.setMyItems(!on) },
    el("span", { class: "tb-mine-dot", "aria-hidden": "true" }), el("span", { class: "tb-mine-label" }, DA.t("tools.mine")));
  }

  /* ---------- Settings screen #/settings ---------- */
  function select(name, options, labelOf, value, onChange) {
    const sel = el("select", { name }, options.map((o) => el("option", { value: o, selected: String(value) === String(o) }, labelOf(o))));
    sel.addEventListener("change", () => onChange(sel.value, sel));
    return sel;
  }

  async function render(main, parts) {
    let data;
    try { data = await api.get("/api/me/prefs"); } catch (err) { toast(err.message, "error"); return; }
    clear(main);
    const t = DA.t;
    const status = el("p", { class: "set-status", role: "status", "aria-live": "polite" });
    let timer = null;
    const done = () => {
      status.textContent = t("set.saved");
      clearTimeout(timer);
      timer = setTimeout(() => { status.textContent = ""; }, 2500);
    };
    const auto = (key, rerender) => async (value, input) => {  // resolves once saved (or refused)
      try {
        await save({ [key]: value });
        done();
        if (rerender) render(main);  // language changes the labels of this page
        if (key === "vacation_bank_hours" || key === "vacation_bank_date") loadBalance();
      } catch (err) { toast(err.message, "error"); if (input) input.value = current[key] == null ? "" : current[key]; }
    };
    const p = data.prefs;
    const c = data.choices;
    const sizes = { 90: "90 %", 100: "100 %", 112: "112 %", 125: "125 %" };

    const display = el("section", { class: "panel" }, el("h2", null, t("set.display")),
      el("p", { class: "muted set-translate" }, DA.lang() === "en"
        ? "Language: FR | EN at the top of every page. The tool's frame is in English; the screens of the modules are being "
          + "translated one by one. For any other language, use your browser's translation (right-click → « Translate to … »)."
        : "Langue : FR | EN en haut de chaque page. Pour une autre langue, utilisez la traduction de votre navigateur "
          + "(clic droit → « Traduire en … ») : elle traduit tout, contenu des tickets et des pages compris."),
      field(t("set.theme"), select("theme", c.theme, (o) => t("theme." + o), p.theme, auto("theme"))),
      field(t("set.font"), select("font", c.font, (o) => t("font." + o), p.font, auto("font"))),
      field(t("set.size"), select("font_size", c.font_size, (o) => sizes[o], p.font_size, auto("font_size"))),
      field(t("set.density"), select("density", c.density, (o) => t("density." + o), p.density, auto("density"))),
      field(t("set.landing"), select("landing", c.landing, (o) => t("landing." + o), p.landing, auto("landing"))));

    const mine = el("input", { type: "checkbox", checked: !!p.my_items });
    mine.addEventListener("change", () => auto("my_items")(mine.checked));
    const initials = el("input", { type: "text", maxlength: 3, minlength: 3, value: p.initials || "", placeholder: "JDE",
      autocomplete: "off", id: "set-initials", pattern: "[A-Za-z]{3}", "aria-describedby": "set-initials-warn" });
    initials.addEventListener("change", () => {
      initials.value = initials.value.toUpperCase();
      auto("initials")(initials.value, initials).then(() => DA.initialsChanged && DA.initialsChanged());
    });
    const sandbox = el("input", { type: "checkbox", checked: !!p.hide_sandbox });
    sandbox.addEventListener("change", () => auto("hide_sandbox")(sandbox.checked));
    const work = el("section", { class: "panel" }, el("h2", null, t("set.work")),
      el("label", { class: "check" }, mine, t("set.mine")),
      el("label", { class: "check" }, sandbox, "Cacher le Space DEMO"),
      el("p", { class: "muted" }, "Projet de test et ressources pédagogiques. Son wiki reste toujours visible dans Dynamite et depuis Help : c'est l'aide des utilisateurs."),
      field(t("set.initials"), initials, t("set.initialsHelp")),
      el("p", { class: "muted" }, t("tools.mineOff")));

    const manager = select("manager_id", [""].concat(data.people.map((u) => String(u.id))),
      (o) => (o ? data.people.find((u) => String(u.id) === o).display_name : t("set.none")), p.manager_id || "", auto("manager_id"));
    const bank = el("input", { type: "number", min: 0, max: 2000, step: 0.5, value: p.vacation_bank_hours == null ? "" : p.vacation_bank_hours });
    bank.addEventListener("change", () => auto("vacation_bank_hours")(bank.value, bank));
    const since = el("input", { type: "date", value: p.vacation_bank_date || "" });
    since.addEventListener("change", () => auto("vacation_bank_date")(since.value, since));
    const balance = el("p", { class: "set-balance", hidden: true });
    async function loadBalance() {
      try {
        const b = await api.get("/api/timesheet/leave");
        since.value = b.since || since.value;
        balance.hidden = b.remaining == null;
        balance.textContent = b.remaining == null ? "" : (DA.lang() === "en"
          ? b.remaining + " h left (" + b.bank + " h as of " + b.since + ", " + b.used + " h entered as INT-VAC since)"
          : b.remaining + " h restantes (" + b.bank + " h au " + b.since + ", " + b.used + " h saisies en INT-VAC depuis)");
      } catch (err) { balance.hidden = true; }
    }
    const hr = el("section", { class: "panel" }, el("h2", null, t("set.hr")),
      field(t("set.manager"), manager), el("p", { class: "muted" }, t("set.managerHelp")),
      el("div", { class: "set-bank" }, field(t("set.bank"), bank), field(t("set.bankDate"), since)),
      el("p", { class: "muted" }, t("set.bankHelp")), balance);

    /* D-B-058: the 3-letter key comes first while it is missing; #/settings/initials focuses it. */
    const missing = !/^[A-Z]{3}$/.test(p.initials || "");
    const warn = missing ? el("div", { class: "set-initials-warn", id: "set-initials-warn", role: "alert" },
      el("strong", null, "Key de traçabilité requise. "),
      "Saisissez vos initiales (3 lettres) dans « Travail » ci-dessous : aucune modification n'est acceptée sans elles. "
        + "Elles signent vos changements (ex. 28092026-JDE).") : "";  // "" -- a null would print « null »
    main.append(el("div", { class: "page-head" }, el("h1", null, t("set.title")), el("p", { class: "muted" }, t("set.sub")), status),
      warn, el("div", { class: "set-grid" }, display, work, hr));
    if (missing || (parts && parts[0] === "initials")) {
      initials.closest(".field") && initials.closest(".field").classList.add("set-required");
      if (parts && parts[0] === "initials") { initials.scrollIntoView({ block: "center" }); initials.focus(); }
    }
    loadBalance();
  }

  DA.topbarTools = DA.topbarTools || [];
  mineToggle.order = 20;
  DA.topbarTools.push(mineToggle);  // first tool: left of the search box
  DA.coreViews = DA.coreViews || {};
  DA.coreViews.settings = render;
})();
