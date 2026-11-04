/* « Mes objectifs » #/objectives[/<user>[/<year>[/<step>]]] (core lot v0.11, D-B-048; review cycle core lot v0.30, D-B-111):
   private space of an employee and his manager. Context banner (title, level, seniority -- review_parts.js), then the
   3 steps of the year, each signed by both: start (annual, development and training objectives agreed), mid (a comment
   from each side on every item), end (every item gets a verdict; intern: competency grid -- objectives_review.js).
   The year closes once the end step is signed; the chosen development objectives carry on. Saved as typed. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field } = DA;

  function saver(id, name, status) {
    return async (value) => {
      try {
        await api.patch("/api/objectives/item/" + id, { [name]: value });
        status.textContent = "Enregistré.";
        setTimeout(() => { status.textContent = ""; }, 1800);
      } catch (err) { toast(err.message, "error"); }
    };
  }

  function objectiveCard(o, data, reload, startOpen) {
    const self = data.relation === "self";
    const locked = data.archived;
    const fixed = locked || !startOpen;  // D-B-111: title, description and expectations are agreed at the start step
    const status = el("span", { class: "ob-saved", role: "status" });
    const save = (name) => saver(o.id, name, status);
    const textInput = (name, value, rows, editable, placeholder) => {
      if (!editable) return value ? el("p", { class: "ob-text" }, value) : el("p", { class: "muted" }, "—");
      const input = rows ? el("textarea", { rows, maxlength: 4000, placeholder }) : el("input", { type: "text", maxlength: 200, placeholder });
      input.value = value || "";
      input.addEventListener("change", () => save(name)(input.value));
      return input;
    };
    const progress = el("input", { type: "range", min: 0, max: 100, step: 5, value: o.progress, disabled: !self || locked,
      "aria-label": "Avancement" });
    const pct = el("span", { class: "ob-pct" }, o.progress + " %");
    progress.addEventListener("input", () => { pct.textContent = progress.value + " %"; });
    progress.addEventListener("change", () => save("progress")(Number(progress.value)));
    const state = el("select", { disabled: locked, "aria-label": "Status" },
      Object.entries(data.statuses).map(([k, v]) => el("option", { value: k, selected: k === o.status }, v)));
    state.addEventListener("change", () => save("status")(state.value));
    const level = el("select", { disabled: self || fixed, "aria-label": "Level visé" }, el("option", { value: "" }, "— à définir —"),
      Object.entries(data.levels).map(([k, v]) => el("option", { value: k, selected: String(o.target_level) === k }, v)));
    level.addEventListener("change", () => save("target_level")(level.value || null));
    return el("article", { class: "ob-card ob-" + o.kind + " ob-st-" + o.status },
      el("div", { class: "ob-card-head" }, el("span", { class: "badge badge-" + (o.kind === "development" ? "warn" : "editor") }, data.kinds[o.kind]),
        o.carried_from ? el("span", { class: "muted ob-carried" }, "poursuivi depuis " + o.carried_year) : null,
        el("span", { class: "qa-spacer" }), state, status),
      textInput("title", o.title, 0, self && !fixed, "Objectif clair et mesurable"),
      textInput("description", o.description, 2, self && !fixed, "Comment le mesurer, pour quand, avec quelles ressources…"),
      el("div", { class: "ob-row" }, el("label", { class: "ob-inline" }, "Avancement ", progress, pct),
        o.kind === "development" ? el("label", { class: "ob-inline" }, "Level visé ", level) : null),
      el("div", { class: "ob-expect" }, el("strong", null, "Attentes du gestionnaire"),
        textInput("expectation", o.expectation, 2, !self && !fixed, "Ce que « réussi » veut dire cette année…")));
  }

  function newDialog(data, kind, reload) {
    const title = el("input", { type: "text", maxlength: 200, required: true });
    const desc = el("textarea", { rows: 3, maxlength: 4000 });
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      const body = { kind, title: title.value, description: desc.value };
      try { await api.post("/api/objectives/" + data.person.id + "/" + data.year, body); close(); reload(); }
      catch (err) { toast(err.message, "error"); }
    } }, field("Objectif", title, kind === "development" ? "Ex. « Maîtriser l'analyse fonctionnelle d'un produit »" : "Ex. « Remettre le RCS de l'équipe d'ici décembre »"),
    field("Description (optionnel)", desc),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Ajouter")));
    close = modal(data.kinds[kind] + " " + data.year, form);
    title.focus();
  }

  function archiveDialog(data, reload) {
    const boxes = data.objectives.filter((o) => o.kind === "development" && o.status !== "dropped").map((o) => ({ o,
      box: el("input", { type: "checkbox", checked: o.status !== "done" }) }));
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        const res = await api.post("/api/objectives/" + data.person.id + "/" + data.year + "/archive",
          { carry: boxes.filter((b) => b.box.checked).map((b) => b.o.id) });
        close();
        toast("Année " + res.archived + " archivée ; " + res.carried + " objectif(s) poursuivi(s) en " + res.next_year + ".", "success");
        location.hash = "#/objectives/" + data.person.id + "/" + res.next_year;
      } catch (err) { toast(err.message, "error"); }
    } },
    el("p", null, "L'année " + data.year + " passera en lecture seule (objectifs et commentaires gardés). Cochez les objectifs de "
      + "développement à poursuivre en " + (data.year + 1) + " : le gestionnaire pourra y monter le niveau visé et ses attentes."),
    boxes.length ? el("div", { class: "ob-carry" }, boxes.map((b) => el("label", { class: "check" }, b.box, b.o.title)))
      : el("p", { class: "muted" }, "Aucun objectif de développement à poursuivre."),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Archiver l'année " + data.year)));
    close = modal("Clore l'année " + data.year, form);
  }

  async function render(main, parts) {
    let people;
    try { people = await api.get("/api/objectives/people"); } catch (err) { toast(err.message, "error"); return; }
    const who = Number(parts[0]) || people.me;
    const year = Number(parts[1]) || new Date().getFullYear();
    let data, review;
    try {
      [data, review] = await Promise.all([api.get("/api/objectives/" + who + "?year=" + year), api.get("/api/reviews/" + who + "?year=" + year)]);
    } catch (err) {
      clear(main); main.append(el("div", { class: "empty" }, el("p", null, err.message))); return;
    }
    const step = ["start", "mid", "end"].includes(parts[2]) ? parts[2] : (review.current === "done" ? "end" : review.current);
    const href = (p) => "#/objectives/" + who + "/" + data.year + "/" + p;
    const reload = () => render(main, [String(who), String(data.year), step]);
    clear(main);
    const personSel = el("select", { "aria-label": "Personne" }, people.people.map((p) =>
      el("option", { value: p.id, selected: p.id === who }, p.id === people.me ? "Moi (" + p.display_name + ")" : p.display_name)));
    personSel.addEventListener("change", () => { location.hash = "#/objectives/" + personSel.value + "/" + data.year; });
    const yearSel = el("select", { "aria-label": "Année" }, data.years.map((y) => el("option", { value: y, selected: y === data.year }, String(y))));
    yearSel.addEventListener("change", () => { location.hash = "#/objectives/" + who + "/" + yearSel.value; });
    const self = data.relation === "self";
    const intern = review.profile.kind === "intern";
    main.append(el("div", { class: "page-head ob-head" },
      el("div", null, el("h1", null, (intern ? (self ? "Mon évaluation de stage " : "Évaluation de stage de " + data.person.display_name + " ")
        : (self ? "Mes objectifs " : "Objectifs de " + data.person.display_name + " ")) + data.year),
        el("p", { class: "muted" }, "Espace privé : " + (self ? "vous et votre gestionnaire" + (data.manager ? " (" + data.manager + ")" : " — choisissez-le dans menu à votre nom → Paramètres")
          : "l'employé et vous, son gestionnaire") + ". Les administrateurs n'y ont pas accès.")),
      el("div", { class: "ob-selectors" }, people.people.length > 1 ? personSel : null, yearSel)),
    DA.reviewParts.banner(review.profile, who, self),
    data.archived ? el("p", { class: "db-audit-banner" }, el("strong", null, "Année archivée — lecture seule.")) : "",
    /* D-A-045: sub-menu -- the review, the profile and the training plan of the same person */
    el("nav", { class: "subtabs ob-subtabs", "aria-label": "Évaluation, profil et formation" },
      el("a", { class: "subtab active", href: location.hash, "aria-current": "page" }, intern ? "Évaluation de stage" : "Objectifs et évaluation"),
      el("a", { class: "subtab", href: "#/profile/" + who, "data-new": "0.50.5-profile" }, "Profil et parcours"),
      el("a", { class: "subtab", href: self ? "#/training" : "#/training/plan/" + data.person.id }, "Training (plan de formation)")),
    DA.reviewParts.stepper(review, step, href));
    const cards = el("div", { class: "ob-list" });
    if (step === "start") {
      const startOpen = DA.reviewParts.editable(review, "start");
      cards.append(el("p", { class: "muted rv-hint" }, intern
        ? "Accueil : le mandat du stage et ses objectifs, convenus ensemble, puis signés par les deux."
        : "Début d'année : objectifs annuels, de développement et de formation, convenus ensemble, puis signés par les deux."));
      ["annual", "development"].forEach((kind) => {
        const list = data.objectives.filter((o) => o.kind === kind);
        cards.append(el("div", { class: "ob-section-head" }, el("h2", null, (kind === "annual" ? (intern ? "Objectifs du stage" : "Objectifs annuels")
          : "Objectifs de développement") + " (" + list.length + ")"),
          startOpen ? el("button", { type: "button", class: "btn btn-small", onclick: () => newDialog(data, kind, reload) }, "+ Ajouter") : null));
        if (!list.length) cards.append(el("p", { class: "muted" }, kind === "annual" ? "Aucun objectif : alignez les attentes dès le départ."
          : "Aucun objectif de développement : une compétence à faire grandir ?"));
        list.forEach((o) => cards.append(objectiveCard(o, data, reload, startOpen)));
      });
      cards.append(DA.reviewTraining(review, who, self));
      if (!startOpen && !data.archived) cards.append(el("p", { class: "muted" }, "Objectifs convenus et signés. Pour en ajouter ou en modifier un, "
        + "le gestionnaire rouvre l'étape « " + review.labels.start + " ». L'avancement se met à jour à tout moment."));
    }
    /* the signature bar follows what is typed: its blocking points are refreshed after each save */
    const signBox = el("div", { class: "rv-sign-box" }, DA.reviewParts.signBar(review, who, step, reload));
    const refresh = async () => {
      try {
        const fresh = await api.get("/api/reviews/" + who + "?year=" + data.year);
        signBox.replaceChildren(DA.reviewParts.signBar(fresh, who, step, reload));
      } catch (err) { /* the next save or reload will tell */ }
    };
    if (step !== "start") DA.reviewPhase(cards, review, data.objectives, who, step, refresh);
    cards.append(signBox);
    const text = el("textarea", { rows: 3, maxlength: 4000, placeholder: "Un fait, un progrès, une question, un retour… (visible par vous deux)" });
    const context = el("select", { "aria-label": "Contexte" }, Object.entries(data.contexts).map(([k, v]) => el("option", { value: k }, v)));
    const target = el("select", { "aria-label": "Objectif concerné" }, el("option", { value: "" }, "— général —"),
      data.objectives.map((o) => el("option", { value: o.id }, o.title)));
    const thread = el("section", { class: "ob-thread panel" }, el("h2", null, "Échanges (" + data.comments.length + ")"),
      data.comments.length ? el("ol", { class: "ob-comments" }, data.comments.map((m) => el("li", { class: "ob-comment ob-ctx-" + m.context },
        el("div", { class: "qa-who" }, el("strong", null, m.author || "—"), " · ", DA.formatDate(m.created_at), " · ",
          el("span", { class: "badge badge-neutral" }, data.contexts[m.context]),
          m.objective_id ? el("span", { class: "muted" }, " · " + ((data.objectives.find((o) => o.id === m.objective_id) || {}).title || "")) : null),
        el("p", { class: "ob-text" }, m.body)))) : el("p", { class: "muted" }, "Aucun échange pour l'instant."),
      data.archived ? null : el("form", { class: "form", onsubmit: async (ev) => {
        ev.preventDefault();
        try {
          await api.post("/api/objectives/" + who + "/" + data.year + "/comments", { body: text.value, context: context.value, objective_id: target.value || null });
          reload();
        } catch (err) { toast(err.message, "error"); }
      } }, text, el("div", { class: "form-row" }, field("Contexte", context), field("Objectif", target),
        el("button", { type: "submit", class: "btn btn-primary" }, "Publier"))));
    main.append(el("div", { class: "ob-layout" }, cards, thread),
      data.archived || step !== "end" ? "" : el("div", { class: "form-actions ob-close" },
        el("button", { type: "button", class: "btn" + (review.phases.end.signed ? " btn-primary" : ""), disabled: !review.phases.end.signed,
          title: review.phases.end.signed ? null : "Possible une fois « " + review.labels.end + " » signée par les deux",
          onclick: () => archiveDialog(data, reload) }, "Clore l'année " + data.year + " et archiver…")));
  }

  DA.coreViews = DA.coreViews || {};
  DA.coreViews.objectives = render;
})();
