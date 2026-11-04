/* Annual review (core lot v0.30, D-B-111): shared parts of the evaluation pages --
   the context banner (name, job title, level, seniority, manager; school and dates for an intern), the 3-step
   stepper (start, mid, end) and the signature bar of a step. Built with el() / textContent only. */
(function () {
  "use strict";

  const { api, el, toast } = DA;

  /* « Léa · Étudiante en génie électrique · 2e année · Gestionnaire : Marc » */
  function banner(p, uid, self, onProfile) {
    const bits = [];
    if (p.kind === "intern") {
      bits.push(el("span", { class: "badge badge-info" }, "Stagiaire"));
      if (p.school || p.program) bits.push(el("span", null, [p.school, p.program].filter(Boolean).join(", ")));
      if (p.start_date || p.end_date) bits.push(el("span", null, "Stage du " + (p.start_date || "?") + " au " + (p.end_date || "?")
        + (p.months ? " (" + p.months + " mois)" : "")));
      if (p.tutor) bits.push(el("span", null, "Tuteur : " + p.tutor));
    } else {
      if (p.level_label) bits.push(el("span", { class: "badge badge-neutral" }, p.level_label));
      if (p.seniority) bits.push(el("span", null, p.seniority + " dans l'équipe"));
    }
    bits.push(el("span", null, "Gestionnaire : " + (p.manager || "à choisir dans Paramètres")));
    const missing = !p.job_title && p.kind !== "intern";
    return el("section", { class: "rv-banner panel", "data-new": "0.50.5-review-banner" },
      el("div", { class: "rv-banner-main" },
        el("strong", { class: "rv-name" }, p.name),
        el("span", { class: "rv-title" }, p.job_title || (p.kind === "intern" ? "Stage" : "Titre du poste à préciser")),
        el("div", { class: "rv-bits" }, bits)),
      el("div", { class: "rv-banner-side" },
        missing ? el("p", { class: "muted" }, self ? "Votre gestionnaire n'a pas encore indiqué votre titre et votre niveau."
          : "Indiquez le titre et le niveau dans le profil : ils donnent le contexte des commentaires.") : null,
        onProfile ? null : el("a", { class: "btn btn-small", href: "#/profile/" + uid }, "Profil et parcours →")));
  }

  /* three steps; a click shows that step, the current one is highlighted */
  function stepper(review, shown, href) {
    return el("ol", { class: "rv-steps", "aria-label": "Étapes de l'évaluation" }, ["start", "mid", "end"].map((p, i) => {
      const ph = review.phases[p];
      const state = ph.signed ? "done" : (review.current === p ? "now" : "later");
      const label = { done: "✓ Signé par les deux", now: "En cours", later: "À venir" }[state];
      return el("li", { class: "rv-step rv-" + state + (p === shown ? " rv-shown" : "") },
        el("a", { href: href(p), "aria-current": p === shown ? "step" : null },
          el("span", { class: "rv-num" }, String(i + 1)),
          el("span", { class: "rv-step-name" }, review.labels[p]),
          el("span", { class: "rv-step-state" }, label)));
    }));
  }

  /* who signed, the blocking points of my side, Sign / Reopen */
  function signBar(review, uid, phase, reload) {
    const ph = review.phases[phase];
    const self = review.relation === "self";
    const mine = self ? ph.employee_signed_at : ph.manager_signed_at;
    const fmt = (d) => (d ? "signé le " + DA.formatDate(d) : "pas encore signé");
    const blockers = review.blockers[phase] || [];
    const sign = async () => {
      try { await api.post("/api/reviews/" + uid + "/" + review.year + "/sign/" + phase, {}); toast("Étape « " + review.labels[phase] + " » signée.", "success"); reload(); }
      catch (err) { toast(err.message, "error"); }
    };
    const reopen = async () => {
      try { await api.post("/api/reviews/" + uid + "/" + review.year + "/reopen/" + phase, {}); reload(); }
      catch (err) { toast(err.message, "error"); }
    };
    return el("section", { class: "rv-sign panel" },
      el("h2", null, "Signatures · " + review.labels[phase]),
      el("ul", { class: "rv-sigs" },
        el("li", { class: ph.employee_signed_at ? "rv-ok" : "" }, (review.profile.kind === "intern" ? "Stagiaire : " : "Employé : ") + fmt(ph.employee_signed_at)),
        el("li", { class: ph.manager_signed_at ? "rv-ok" : "" }, "Gestionnaire : " + fmt(ph.manager_signed_at))),
      !ph.signed && !mine && blockers.length ? el("div", { class: "db-audit-banner rv-blockers", role: "status" },
        el("strong", null, "Avant de signer : "), el("ul", null, blockers.map((b) => el("li", null, b)))) : null,
      el("div", { class: "form-actions" },
        !ph.signed && !mine && !review.archived ? el("button", { type: "button", class: "btn btn-primary", disabled: blockers.length > 0,
          onclick: sign, "data-new": "0.50.5-review-sign" }, "Signer « " + review.labels[phase] + " »") : null,
        !self && (ph.employee_signed_at || ph.manager_signed_at) && !review.archived
          ? el("button", { type: "button", class: "btn", onclick: reopen }, "Rouvrir cette étape") : null));
  }

  /* a phase that is signed, or not open yet, is read-only */
  function editable(review, phase) {
    if (review.archived || review.phases[phase].signed) return false;
    const i = ["start", "mid", "end"].indexOf(phase);
    return i === 0 || review.phases[["start", "mid", "end"][i - 1]].signed;
  }

  DA.reviewParts = { banner, stepper, signBar, editable };
})();
