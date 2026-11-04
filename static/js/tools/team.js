/* « Mon équipe » #/team[/<year>] (core lot v0.31, D-B-112): for a manager, the people who chose him in their Settings.
   One card per person: title and level (or intern), the 3 steps of the year with who signed, and what is expected from
   the manager now (« À vous : relire et signer "Début d'année" »), first in the list. Links to the evaluation, the
   profile and the training plan. Reached from the account menu (« Mon équipe (n) · k à traiter »). el() only. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;

  DA.teamLabel = (t) => "Mon équipe (" + t.size + ")" + (t.pending ? " · " + t.pending + " à traiter" : "");

  function steps(p) {
    return el("ol", { class: "tm-steps", "aria-label": "Étapes" }, ["start", "mid", "end"].map((k) => {
      const s = p.phases[k];
      const both = s.employee && s.manager;
      const state = both ? "done" : (p.current === k ? "now" : "later");
      return el("li", { class: "tm-step rv-" + state, "data-tip": p.labels[k] + " : " + (both ? "signée par les deux"
        : (s.employee ? "signée par l'employé" : s.manager ? "signée par vous" : "pas encore signée")) },
      el("span", { class: "rv-num" }, both ? "✓" : String(["start", "mid", "end"].indexOf(k) + 1)),
      el("span", { class: "tm-step-name" }, p.labels[k]),
      el("span", { class: "tm-sig" }, (s.employee ? "● " : "○ ") + "employé · " + (s.manager ? "● " : "○ ") + "vous"));
    }));
  }

  function card(p, year) {
    const pr = p.profile;
    const intern = pr.kind === "intern";
    const where = p.current === "done" ? "end" : p.current;
    return el("article", { class: "ob-card tm-card" + (p.mine ? " tm-mine" : "") },
      el("div", { class: "ob-card-head" },
        el("strong", { class: "rv-name" }, pr.name),
        el("span", { class: "rv-title" }, pr.job_title || (intern ? "Stage" : "Titre à préciser")),
        intern ? el("span", { class: "badge badge-info" }, "Stagiaire") : (pr.level_label ? el("span", { class: "badge badge-neutral" }, pr.level_label) : null),
        el("span", { class: "qa-spacer" }),
        p.mine ? el("span", { class: "badge badge-warn" }, "À vous") : null),
      steps(p),
      el("p", { class: "tm-todo" + (p.mine ? " tm-todo-mine" : "") }, p.todo),
      el("div", { class: "form-actions tm-actions" },
        el("a", { class: "btn btn-small" + (p.mine ? " btn-primary" : ""), href: "#/objectives/" + p.id + "/" + year + "/" + where },
          intern ? "Ouvrir l'évaluation de stage" : "Ouvrir l'évaluation"),
        el("a", { class: "btn btn-small", href: "#/profile/" + p.id }, "Profil et parcours"),
        el("a", { class: "btn btn-small", href: "#/training/plan/" + p.id }, "Plan de formation")));
  }

  async function render(main, parts) {
    const year = Number(parts[0]) || new Date().getFullYear();
    let data;
    try { data = await api.get("/api/team?year=" + year); } catch (err) { toast(err.message, "error"); return; }
    clear(main);
    const yearSel = el("select", { "aria-label": "Année" }, [year - 1, year, year + 1].map((y) => el("option", { value: y, selected: y === year }, String(y))));
    yearSel.addEventListener("change", () => { location.hash = "#/team/" + yearSel.value; });
    if (DA.session && DA.session.team && year === new Date().getFullYear()) DA.session.team.pending = data.pending;
    main.append(el("div", { class: "page-head ob-head" },
      el("div", null, el("h1", { "data-new": "0.50.6-team" }, "Mon équipe " + year),
        el("p", { class: "muted" }, "Les personnes qui vous ont choisi comme gestionnaire (menu à leur nom → Paramètres). "
          + "Vous recevez un message dans le Dashboard quand l'une d'elles signe une étape.")),
      el("div", { class: "ob-selectors" }, yearSel)));
    if (!data.people.length) {
      main.append(el("div", { class: "empty" }, el("p", null, "Personne ne vous a encore choisi comme gestionnaire. Chaque employé le fait "
        + "dans menu à son nom → Paramètres → Gestionnaire.")));
      return;
    }
    const mine = data.people.filter((p) => p.mine);
    const rest = data.people.filter((p) => !p.mine);
    main.append(el("p", { class: data.pending ? "db-audit-banner" : "muted", role: "status" },
      data.pending ? el("strong", null, data.pending + " personne(s) attendent votre action. ") : "Rien ne vous attend pour l'instant. ",
      data.people.length + " personne(s) dans votre équipe."));
    const list = el("div", { class: "tm-list" });
    mine.concat(rest).forEach((p) => list.append(card(p, year)));
    main.append(list);
  }

  DA.coreViews = DA.coreViews || {};
  DA.coreViews.team = render;
})();
