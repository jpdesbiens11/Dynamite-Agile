/* Annual review (core lot v0.30, D-B-111): the mid-year and year-end steps, item by item.
   Mid: a comment from each side on EVERY item (objectives and training plan). End: each item gets the employee's
   self-assessment and the manager's verdict with their comments; overall comments; for an intern, the competency
   grid (1 to 4) and the recommendation. Each field is saved when it changes; the blocking points are refreshed. */
(function () {
  "use strict";

  const { api, el, toast } = DA;
  const GROUPS = { annual: "Objectif annuel", development: "Objectif de développement", training: "Formation (Training)" };

  function saverFor(uid, review, onSaved) {
    return (path, body) => async () => {
      try {
        await api.put("/api/reviews/" + uid + "/" + review.year + path, body());
        if (onSaved) onSaved();
      } catch (err) { toast(err.message, "error"); }
    };
  }

  function textArea(value, editable, placeholder, onChange) {
    if (!editable) return value ? el("p", { class: "ob-text" }, value) : el("p", { class: "muted" }, "—");
    const t = el("textarea", { rows: 2, maxlength: 4000, placeholder });
    t.value = value || "";
    t.addEventListener("change", () => onChange(t));
    return t;
  }

  function verdictSelect(review, value, editable, label, onChange) {
    const s = el("select", { disabled: !editable, "aria-label": label }, el("option", { value: "" }, "— à évaluer —"),
      Object.entries(review.verdicts).map(([k, v]) => el("option", { value: k, selected: k === value }, v)));
    s.addEventListener("change", () => onChange(s));
    return s;
  }

  function itemCard(review, item, phase, uid, open, refresh, extra) {
    const self = review.relation === "self";
    const key = item.type + ":" + item.id;
    const r = (review.reviews[key] || {})[phase] || {};
    const save = saverFor(uid, review, refresh);
    const put = (name, read) => save("/item", () => ({ phase, item_type: item.type, item_id: item.id, [name]: read() }))();
    const who = review.profile.kind === "intern" ? "Stagiaire" : "Employé";
    const side = (title, mine, comment, verdictName, verdictValue, placeholder) => el("div", { class: "rv-side" + (mine ? " rv-mine" : "") },
      el("strong", null, title),
      phase === "end" ? verdictSelect(review, verdictValue, open && mine, title + " : verdict", (s) => put(verdictName, () => s.value)) : null,
      textArea(comment, open && mine, placeholder, (t) => put(mine && self ? "employee_comment" : "manager_comment", () => t.value)));
    const fresh = !r.employee_comment && !r.manager_comment && !(phase === "end" && r.verdict);
    return el("article", { class: "ob-card rv-item" + (fresh ? " rv-fresh" : "") },
      el("div", { class: "ob-card-head" }, el("span", { class: "badge badge-" + (item.type === "objective" ? (item.group === "development" ? "warn" : "editor") : "info") },
        GROUPS[item.group] || item.group), el("strong", { class: "rv-item-title" }, item.title),
      el("span", { class: "qa-spacer" }), extra || null, item.status ? el("span", { class: "muted" }, item.status) : null),
      el("div", { class: "rv-sides" },
        side(phase === "end" ? who + " · auto-évaluation" : who, self, r.employee_comment, "employee_verdict", r.employee_verdict,
          phase === "end" ? "Ce qui a été atteint, avec des faits…" : "Où j'en suis, ce qui aide, ce qui bloque…"),
        side(phase === "end" ? "Gestionnaire · verdict" : "Gestionnaire", !self, r.manager_comment, "verdict", r.verdict,
          phase === "end" ? "Le verdict expliqué, avec des faits…" : "Retour du gestionnaire à mi-parcours…")));
  }

  function overall(review, uid, open, refresh) {
    const self = review.relation === "self";
    const ph = review.phases.end;
    const save = saverFor(uid, review, refresh);
    const put = (name, read) => save("/phase/end", () => ({ [name]: read() }))();
    const blocks = [el("h2", null, "Appréciation globale"),
      el("div", { class: "rv-sides" },
        el("div", { class: "rv-side" + (self ? " rv-mine" : "") }, el("strong", null, review.profile.kind === "intern" ? "Stagiaire" : "Employé"),
          textArea(ph.employee_comment, open && self, "Mon bilan de l'année, ce dont je suis fier, ce que je veux pour la suite…",
            (t) => put("employee_comment", () => t.value))),
        el("div", { class: "rv-side" + (!self ? " rv-mine" : "") }, el("strong", null, "Gestionnaire"),
          textArea(ph.manager_comment, open && !self, "Bilan d'ensemble, points forts, axes de progrès…",
            (t) => put("manager_comment", () => t.value))))];
    if (review.profile.kind === "intern") {
      const rec = el("select", { disabled: !open || self, "aria-label": "Recommandation" }, el("option", { value: "" }, "— à choisir —"),
        Object.entries(review.recommendations).map(([k, v]) => el("option", { value: k, selected: k === ph.recommendation }, v)));
      rec.addEventListener("change", () => put("recommendation", () => rec.value));
      blocks.push(DA.field("Recommandation de fin de stage", rec));
    }
    return el("section", { class: "panel rv-overall" }, blocks);
  }

  function grid(review, uid, open, refresh) {
    const self = review.relation === "self";
    const save = saverFor(uid, review, refresh);
    const rows = Object.entries(review.criteria).map(([k, label]) => {
      const cur = review.ratings[k] || {};
      const score = el("select", { disabled: !open || self, "aria-label": label }, el("option", { value: "" }, "—"),
        Object.entries(review.scores).map(([s, v]) => el("option", { value: s, selected: String(cur.score) === s }, v)));
      score.addEventListener("change", () => save("/rating", () => ({ criterion: k, score: score.value }))());
      const note = el("input", { type: "text", maxlength: 2000, disabled: !open || self, placeholder: "Un exemple concret…" });
      note.value = cur.comment || "";
      note.addEventListener("change", () => save("/rating", () => ({ criterion: k, comment: note.value }))());
      return el("tr", null, el("td", null, label), el("td", null, score), el("td", null, note));
    });
    return el("section", { class: "panel rv-grid", "data-new": "0.50.5-intern-grid" }, el("h2", null, "Grille de compétences du stage"),
      el("p", { class: "muted" }, "Remplie par le gestionnaire (tuteur) à l'évaluation finale, de 1 (à améliorer) à 4 (excellent)."),
      DA.table(["Compétence", "Note", "Commentaire"], rows));
  }

  /* the mid or end step: items, then (end) grid and overall comments */
  DA.reviewPhase = function (box, review, objectives, uid, phase, refresh) {
    const open = DA.reviewParts.editable(review, phase);
    const progress = Object.fromEntries(objectives.map((o) => [o.id, o.progress]));
    box.append(el("p", { class: "muted rv-hint" }, phase === "mid"
      ? "Sur chaque item, un commentaire de chacun : où on en est, ce qui aide, ce qui bloque, ce qu'on ajuste."
      : "Chaque item fixé en début d'année reçoit un verdict du gestionnaire, après l'auto-évaluation de l'employé."));
    if (!open && !review.phases[phase].signed) box.append(el("p", { class: "db-audit-banner" }, "Étape pas encore ouverte : la précédente doit être signée par les deux."));
    if (!review.items.length) box.append(el("div", { class: "empty" }, el("p", null, "Aucun item : les objectifs se fixent à l'étape « " + review.labels.start + " ».")));
    review.items.forEach((item) => {
      const pct = item.type === "objective" && progress[item.id] != null ? el("span", { class: "ob-pct" }, progress[item.id] + " %") : null;
      box.append(itemCard(review, item, phase, uid, open, refresh, pct));
    });
    if (phase === "end") {
      if (review.profile.kind === "intern") box.append(grid(review, uid, open, refresh));
      box.append(overall(review, uid, open, refresh));
    }
  };

  /* start step: the training plan of the year, next to the objectives */
  DA.reviewTraining = function (review, uid, self) {
    const list = review.items.filter((i) => i.type === "training");
    return el("section", { class: "rv-training" },
      el("div", { class: "ob-section-head" }, el("h2", null, "Objectifs de formation (" + list.length + ")"),
        el("a", { class: "btn btn-small", href: self ? "#/training" : "#/training/plan/" + uid }, "Plan de formation →")),
      list.length ? el("ul", { class: "rv-train-list" }, list.map((i) => el("li", null, el("strong", null, i.title), " · ",
        el("span", { class: "muted" }, i.status || ""))))
        : el("p", { class: "muted" }, "Aucun topic dans le plan de formation de cette année : ajoutez-les dans Training, ils seront revus ici."));
  };
})();
