/* « Profil et parcours » #/profile[/<user>] (core lot v0.30, D-B-111): the context of every evaluation.
   - Poste (set by the manager): employee or intern, job title, experience level, hire date; for an intern, internship
     dates (4 to 8 months), school, program, tutor. The employee reads it.
   - Parcours (written by the employee): education, experience, certifications, skills, languages. The manager reads it.
   Private like « Mes objectifs ». Saved as typed; built with el() / textContent only. */
(function () {
  "use strict";

  const { api, el, clear, toast, field, modal } = DA;

  function posteSection(data, uid, reload) {
    const p = data.profile;
    const manager = data.relation === "manager";
    const status = el("span", { class: "ob-saved", role: "status" });
    const save = async (body) => {
      try {
        const res = await api.patch("/api/profile/" + uid, body);
        status.textContent = "Enregistré.";
        setTimeout(() => { status.textContent = ""; }, 1800);
        if (res.warning) toast(res.warning, "info");
        if ("kind" in body) reload();
      } catch (err) { toast(err.message, "error"); }
    };
    const input = (name, type, label, hint) => {
      const i = el("input", { type, value: p[name] || "", disabled: !manager, maxlength: 160 });
      i.addEventListener("change", () => save({ [name]: i.value }));
      return field(label, i, hint);
    };
    const kind = el("select", { disabled: !manager }, Object.entries(data.kinds).map(([k, v]) => el("option", { value: k, selected: k === p.kind }, v)));
    kind.addEventListener("change", () => save({ kind: kind.value }));
    const level = el("select", { disabled: !manager }, el("option", { value: "" }, "— à préciser —"),
      Object.entries(data.levels).map(([k, v]) => el("option", { value: k, selected: k === p.level }, v)));
    level.addEventListener("change", () => save({ level: level.value }));
    const intern = p.kind === "intern";
    return el("section", { class: "panel pf-poste", "data-new": "0.50.5-profile-poste" },
      el("div", { class: "ob-section-head" }, el("h2", null, "Poste"), status),
      el("p", { class: "muted" }, manager ? "Vous fixez ces informations ; l'employé les voit en tête de son évaluation."
        : "Fixé par votre gestionnaire : c'est le contexte de vos évaluations. Une erreur ? Parlez-en avec lui."),
      el("div", { class: "pf-grid" },
        field("Type", kind),
        input("job_title", "text", intern ? "Mandat du stage" : "Titre du poste", intern ? "Ex. « Stage en conception mécanique »" : "Ex. « Étudiante en génie mécanique »"),
        intern ? null : field("Niveau d'expérience", level),
        intern ? null : input("hire_date", "date", "Date d'embauche", p.seniority ? "Ancienneté : " + p.seniority : null),
        intern ? input("start_date", "date", "Début du stage") : null,
        intern ? input("end_date", "date", "Fin du stage", p.months ? p.months + " mois (prévu : 4 à 8)" : "Prévu : 4 à 8 mois") : null,
        intern ? input("school", "text", "École") : null,
        intern ? input("program", "text", "Programme") : null,
        intern ? input("tutor", "text", "Tuteur ou tutrice") : null));
  }

  function entryDialog(data, uid, section, entry, reload) {
    const title = el("input", { type: "text", maxlength: 200, required: true, value: entry ? entry.title : "" });
    const org = el("input", { type: "text", maxlength: 200, value: entry ? entry.org : "" });
    const period = el("input", { type: "text", maxlength: 80, value: entry ? entry.period : "", placeholder: "Ex. 2019 – 2023" });
    const details = el("textarea", { rows: 4, maxlength: 2000 });
    details.value = entry ? entry.details : "";
    const labels = { education: ["Diplôme", "Établissement"], experience: ["Poste", "Employeur"], certification: ["Certification", "Organisme"],
      skill: ["Compétence", "Contexte"], language: ["Langue", "Niveau"] }[section];
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      const body = { title: title.value, org: org.value, period: period.value, details: details.value };
      try {
        if (entry) await api.patch("/api/profile/entries/" + entry.id, body);
        else await api.post("/api/profile/" + uid + "/entries", Object.assign({ section }, body));
        close(); reload();
      } catch (err) { toast(err.message, "error"); }
    } }, field(labels[0], title), field(labels[1], org), section === "language" || section === "skill" ? null : field("Période", period),
    field("Détails (réalisations, sujets, projets)", details),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, entry ? "Enregistrer" : "Ajouter")));
    close = modal(data.sections[section], form);
    title.focus();
  }

  function parcoursSection(data, uid, reload) {
    const self = data.relation === "self";
    const out = el("section", { class: "panel pf-parcours", "data-new": "0.50.5-profile-parcours" },
      el("h2", null, "Parcours"),
      el("p", { class: "muted" }, self ? "Votre formation, vos expériences et vos compétences : elles appuient vos évaluations. Vous seul les modifiez."
        : "Rempli par l'employé : l'appui de vos commentaires d'évaluation."));
    Object.entries(data.sections).forEach(([key, label]) => {
      const list = data.entries.filter((e) => e.section === key);
      out.append(el("div", { class: "ob-section-head" }, el("h3", null, label + " (" + list.length + ")"),
        self ? el("button", { type: "button", class: "btn btn-small", onclick: () => entryDialog(data, uid, key, null, reload) }, "+ Ajouter") : null));
      if (!list.length) out.append(el("p", { class: "muted" }, self ? "Rien pour l'instant." : "Non renseigné."));
      list.forEach((e) => out.append(el("article", { class: "ob-card pf-entry" },
        el("div", { class: "ob-card-head" }, el("strong", null, e.title), e.org ? el("span", null, "· " + e.org) : null,
          e.period ? el("span", { class: "muted" }, "· " + e.period) : null, el("span", { class: "qa-spacer" }),
          self ? el("button", { type: "button", class: "btn btn-small", onclick: () => entryDialog(data, uid, key, e, reload) }, "Modifier") : null,
          self ? el("button", { type: "button", class: "btn btn-small btn-danger", onclick: async () => {
            try { await api.del("/api/profile/entries/" + e.id); reload(); } catch (err) { toast(err.message, "error"); }
          } }, "Retirer") : null),
        e.details ? el("p", { class: "ob-text" }, e.details) : null)));
    });
    return out;
  }

  async function render(main, parts) {
    let people;
    try { people = await api.get("/api/objectives/people"); } catch (err) { toast(err.message, "error"); return; }
    const uid = Number(parts[0]) || people.me;
    let data;
    try { data = await api.get("/api/profile/" + uid); } catch (err) {
      clear(main); main.append(el("div", { class: "empty" }, el("p", null, err.message))); return;
    }
    const reload = () => render(main, [String(uid)]);
    clear(main);
    const self = data.relation === "self";
    const personSel = el("select", { "aria-label": "Personne" }, people.people.map((p) =>
      el("option", { value: p.id, selected: p.id === uid }, p.id === people.me ? "Moi (" + p.display_name + ")" : p.display_name)));
    personSel.addEventListener("change", () => { location.hash = "#/profile/" + personSel.value; });
    main.append(el("div", { class: "page-head ob-head" },
      el("div", null, el("h1", null, self ? "Mon profil et mon parcours" : "Profil de " + data.profile.name),
        el("p", { class: "muted" }, "Espace privé : l'employé et son gestionnaire. Les administrateurs n'y ont pas accès.")),
      people.people.length > 1 ? el("div", { class: "ob-selectors" }, personSel) : null),
    DA.reviewParts.banner(data.profile, uid, self, true),
    el("nav", { class: "subtabs ob-subtabs", "aria-label": "Évaluation, profil et formation" },
      el("a", { class: "subtab", href: "#/objectives/" + uid }, data.profile.kind === "intern" ? "Évaluation de stage" : "Objectifs et évaluation"),
      el("a", { class: "subtab active", href: location.hash, "aria-current": "page" }, "Profil et parcours"),
      el("a", { class: "subtab", href: self ? "#/training" : "#/training/plan/" + uid }, "Training (plan de formation)")),
    el("div", { class: "pf-layout" }, posteSection(data, uid, reload), parcoursSection(data, uid, reload)));
  }

  DA.coreViews = DA.coreViews || {};
  DA.coreViews.profile = render;
})();
