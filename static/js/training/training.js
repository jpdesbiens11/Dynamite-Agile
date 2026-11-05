/* « Training » (D-A-045), right after Tools in the top bar.
   #/training                -> my training plan of the year (items from the topics, workflow, test, manager evaluation)
   #/training/plan/<uid>     -> the plan of one of my people (manager: evaluation and « Achieved »)
   #/training/test/<iid>     -> the test of one of my items, with circle-back of the missed questions (quiz.js)
   #/training/topics         -> the topics and sub-topics: content, reference (wiki / Help), test
   #/training/admin          -> administrators: create / edit topics and their Markdown test
   #/training/workflow       -> administrators: which role may do each transition
   Mid-year and year-end reviews stay in « Mes objectifs » (link in the left panel). */
(function () {
  "use strict";
  const { api, el, clear, field, toast, modal } = DA;
  const TR = (DA.training = DA.training || {});
  // 0.50.10 (D-B-128): Completed = green (test passed), Achieved = green filled (evaluated by the manager).
  const STATUS_CLASS = { todo: "neutral", in_progress: "warn", completed: "ok", achieved: "ok tr-badge-achieved" };
  let YEAR = new Date().getFullYear();

  const badge = (code, label) => el("span", { class: "badge badge-" + (STATUS_CLASS[code] || "neutral") },
    (code === "completed" || code === "achieved" ? "✓ " : "") + label);
  const refLink = (t) => (t.reference ? el("a", { href: t.reference, class: "tr-ref", target: t.reference.startsWith("#") ? null : "_blank",
    rel: "noopener" }, t.ref_label || t.reference) : null);

  function layout(shell, view, people) {
    const nav = [["#/training", "Mon plan", view === "plan"], ["#/training/topics", "Topics", view === "topics"],
      ["#/objectives", "Objectifs (mi-année, fin d'année)", false]];
    (people || []).filter((p) => p.id !== people.me).forEach((p) => nav.push(["#/training/plan/" + p.id, "Plan · " + p.display_name,
      view === "plan-" + p.id]));
    return DA.moduleLayout(shell, { label: "Training", mark: DA.mark("training"), nav,
      admin: [["#/training/admin", "Gérer les topics et les tests", view === "admin"], ["#/training/workflow", "Workflow", view === "workflow"]] });
  }

  /* ---------- plan ---------- */
  async function planView(main, uid, reload) {
    const [data, topics] = await Promise.all([api.get("/api/training/plan/" + uid + "?year=" + YEAR), api.get("/api/training/topics")]);
    const self = data.relation === "self";
    const year = el("select", { "aria-label": "Année" }, data.years.map((y) => el("option", { value: y, selected: y === data.year }, y)));
    year.addEventListener("change", () => { YEAR = Number(year.value); reload(); });
    const inPlan = new Set(data.items.map((i) => i.topic_id));
    const pick = el("select", { "aria-label": "Topic à ajouter" }, el("option", { value: "" }, "Ajouter un topic au plan…"),
      topics.topics.filter((t) => !inPlan.has(t.id)).map((t) => el("option", { value: t.id }, (t.parent_id ? "   " : "") + t.code + " · " + t.title)));
    pick.addEventListener("change", async () => {
      if (!pick.value) return;
      try { await api.post("/api/training/plan/" + uid + "/items?year=" + YEAR, { topic_id: Number(pick.value) }); reload(); }
      catch (err) { toast(err.message, "error"); pick.value = ""; }
    });
    const counts = Object.keys(data.statuses).map((s) => el("span", { class: "tr-count" }, badge(s, data.statuses[s]),
      " " + data.items.filter((i) => i.status === s).length));
    main.append(el("div", { class: "page-head" }, el("h1", null, self ? "Mon plan de formation" : "Plan de " + data.person.display_name),
      el("p", { class: "muted" }, self ? "Vos topics de l'année : lisez la référence, passez le test (note à la fin ; sous 80 %, les questions "
        + "manquées reviennent jusqu'à ce que chacune soit réussie). Test réussi = « Completed » en vert ; votre gestionnaire évalue et coche "
        + "« Achieved »." : "Évaluez chaque item complété (test réussi), puis cochez « Achieved ».")),
    el("div", { class: "tr-toolbar" }, field("Année", year), pick, el("span", { class: "tr-counts" }, counts)));
    if (!data.items.length) {
      main.append(el("div", { class: "empty" }, el("p", null, "Aucun topic dans ce plan. Choisissez-en un ci-dessus, par exemple les "
        + "sections DEMO.")));
      return;
    }
    main.append(el("div", { class: "tr-items" }, data.items.map((it) => itemCard(it, data, self, reload))));
  }

  function itemCard(it, data, self, reload) {
    const act = async (to) => {
      try { await api.patch("/api/training/items/" + it.id, { status: to }); toast("« " + it.title + " » : " + data.statuses[to] + ".", "success"); reload(); }
      catch (err) { toast(err.message, "error"); }
    };
    const evalBox = !self ? el("textarea", { rows: 2, maxlength: 3000, placeholder: "Votre évaluation (obligatoire avant « Achieved »)" }) : null;
    if (evalBox) evalBox.value = it.manager_eval || "";
    const saveEval = evalBox ? el("button", { type: "button", class: "btn btn-small", onclick: async () => {
      try { await api.patch("/api/training/items/" + it.id, { manager_eval: evalBox.value }); toast("Évaluation enregistrée.", "success"); }
      catch (err) { toast(err.message, "error"); }
    } }, "Enregistrer l'évaluation") : null;
    const quizInfo = !it.has_quiz ? "Pas de test pour ce topic"
      : it.quiz_passed ? "✓ Test réussi · note " + it.quiz_score + " %" + (it.quiz_attempts > 1 ? " · " + it.quiz_attempts + " essais" : "")
        : it.quiz_remaining ? "Reprise en cours : " + it.quiz_remaining + " question(s) manquée(s) à refaire · note " + it.quiz_first + " %"
          : it.quiz_attempts ? "Test pas encore réussi · " + it.quiz_attempts + " essai(s)" : "Test à passer (" + it.quiz_questions + " questions)";
    const canTest = self && it.has_quiz && it.status !== "achieved";
    const testLabel = it.quiz_remaining ? "Reprendre les " + it.quiz_remaining + " question(s) manquée(s)"
      : it.quiz_passed ? "Repasser le test" : "Passer le test";
    // A topic with a test becomes Completed by passing it: the manual button is hidden until then (plan.api_update).
    const actions = it.actions.filter((a) => !(a.to === "completed" && it.has_quiz && !it.quiz_passed));
    return el("article", { class: "tr-item tr-" + it.status },
      el("div", { class: "tr-item-head" }, el("strong", null, it.code + " · " + it.title), badge(it.status, data.statuses[it.status])),
      it.content ? el("p", { class: "tr-content" }, it.content) : null,
      el("p", { class: "tr-meta" }, refLink(it), el("span", { class: it.quiz_passed ? "tr-quiz-ok" : "muted" }, " · " + quizInfo)),
      !self && it.manager_eval === "" && it.status === "completed" ? el("p", { class: "tr-hint" }, "À évaluer.") : null,
      self && it.manager_eval ? el("p", { class: "tr-eval" }, "Évaluation du gestionnaire : " + it.manager_eval) : null,
      evalBox ? el("div", { class: "tr-eval-edit" }, evalBox, saveEval) : null,
      el("div", { class: "tr-actions" },
        canTest ? el("a", { class: "btn btn-small" + (it.quiz_passed ? "" : " btn-primary"), href: "#/training/test/" + it.id,
          "data-new": "0.50.10-training-circle" }, testLabel) : null,
        actions.map((a) => el("button", { type: "button", class: "btn btn-small" + (a.to === "achieved" || a.to === "completed" ? " btn-primary" : ""),
          onclick: () => act(a.to) }, a.label)),
        (self && it.status === "todo") || !self ? el("button", { type: "button", class: "link-btn", onclick: async () => {
          if (!confirm("Retirer « " + it.title + " » du plan ?")) return;
          try { await api.del("/api/training/items/" + it.id); reload(); } catch (err) { toast(err.message, "error"); }
        } }, "Retirer") : null));
  }

  /* ---------- topics ---------- */
  function tree(topics) {
    const roots = topics.filter((t) => !t.parent_id);
    return roots.map((r) => ({ root: r, children: topics.filter((t) => t.parent_id === r.id) }));
  }

  async function topicsView(main) {
    const [data, mine] = await Promise.all([api.get("/api/training/topics"),
      api.get("/api/training/plan/" + DA.session.user.id + "?year=" + YEAR).catch(() => ({ items: [], statuses: {} }))]);
    const myStatus = new Map(mine.items.map((i) => [i.topic_id, i.status]));
    const mark = (t) => (myStatus.has(t.id) ? badge(myStatus.get(t.id), (mine.statuses || {})[myStatus.get(t.id)] || myStatus.get(t.id)) : null);
    main.append(el("div", { class: "page-head" }, el("h1", null, "Topics de formation"),
      el("p", { class: "muted" }, "Chaque topic a un contenu, une référence (page du wiki Dynamite ou chapitre Help) et, s'il y a lieu, un "
        + "test à choix de réponse. Ajoutez un topic à votre plan depuis « Mon plan ».")));
    tree(data.topics).forEach(({ root, children }) => main.append(el("section", { class: "tr-group" },
      el("h2", null, root.code + " · " + root.title), root.content ? el("p", { class: "muted" }, root.content) : null,
      el("ul", { class: "tr-topics" }, children.map((t) => el("li", null, el("strong", null, t.code + " "), t.title, " — ", refLink(t),
        t.has_quiz ? el("span", { class: "badge badge-info tr-quiz-badge" }, "Test · " + t.quiz_questions + " q.") : null,
        mark(t) ? el("span", { class: "tr-quiz-badge", "data-new": "0.50.10-training-mine" }, mark(t)) : null))))));
  }

  /* ---------- administrators: topics and tests ---------- */
  async function adminView(main, reload) {
    const data = await api.get("/api/training/topics");
    if (!data.can_manage) { main.append(el("p", null, "Réservé aux administrateurs et aux Admin du Space TRAINING.")); return; }
    main.append(el("div", { class: "page-head" }, el("h1", null, "Gérer les topics et les tests"),
      el("p", { class: "muted" }, "Un topic principal regroupe des sous-topics (un niveau). Le test s'écrit en Markdown simple : "
        + "« ## » une question, « - [x] » une bonne réponse, « - [ ] » une mauvaise, « > » l'explication, « pass: 80 » le seuil. "
        + "20 questions sont recommandées.")),
    el("div", { class: "form-actions tt-left" }, el("button", { type: "button", class: "btn btn-primary", onclick: () => edit(null, data, reload) }, "+ Nouveau topic")));
    main.append(DA.table(["Code", "Titre", "Parent", "Référence", "Test", "État", ""], data.topics.map((t) => el("tr", null,
      el("td", null, el("strong", null, t.code)), el("td", null, t.title),
      el("td", null, (data.topics.find((p) => p.id === t.parent_id) || {}).code || "—"), el("td", null, refLink(t)),
      el("td", null, t.quiz_questions ? t.quiz_questions + " q." + (t.has_quiz ? "" : " ⚠") : "—"),
      el("td", null, t.active ? badge("achieved", "Active") : badge("todo", "Inactive")),
      el("td", null, el("button", { type: "button", class: "link-btn", onclick: () => edit(t, data, reload) }, "Modifier"))))));
  }

  function edit(t, data, reload) {
    t = t || { code: "", title: "", content: "", reference: "", ref_label: "", quiz_md: "", parent_id: null, active: 1 };
    const f = {
      code: el("input", { type: "text", maxlength: 20, value: t.code, placeholder: "ex. AF-01" }),
      title: el("input", { type: "text", maxlength: 200, value: t.title, required: true }),
      parent_id: el("select", null, el("option", { value: "" }, "— topic principal —"),
        data.topics.filter((p) => !p.parent_id && p.id !== t.id).map((p) => el("option", { value: p.id, selected: p.id === t.parent_id }, p.code + " · " + p.title))),
      content: el("textarea", { rows: 3, maxlength: 6000 }), reference: el("input", { type: "text", maxlength: 400, value: t.reference,
        placeholder: "ex. #/dynamite/DEMO/page/12 ou #/help/timesheet" }),
      ref_label: el("input", { type: "text", maxlength: 200, value: t.ref_label, placeholder: "Texte du lien" }),
      quiz_md: el("textarea", { rows: 12, maxlength: 60000, class: "tr-md", placeholder: data.example_quiz || "" }),
      active: el("input", { type: "checkbox", checked: !!t.active }),
    };
    f.content.value = t.content || "";
    f.quiz_md.value = t.quiz_md || "";
    const check = el("p", { class: "muted", role: "status" });
    const runCheck = async () => {
      if (!f.quiz_md.value.trim()) { check.textContent = "Pas de test."; return; }
      const r = await api.post("/api/training/quiz-check", { quiz_md: f.quiz_md.value });
      check.textContent = r.problems.length ? "⚠ " + r.problems.join(" | ") : "✓ " + r.questions + " question(s), seuil " + r.pass + " %. "
        + r.notes.join(" ");
    };
    f.quiz_md.addEventListener("change", runCheck);
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { class: "ag-form", onsubmit: async (ev) => {
      ev.preventDefault();
      const body = { code: f.code.value, title: f.title.value, parent_id: f.parent_id.value ? Number(f.parent_id.value) : null,
        content: f.content.value, reference: f.reference.value, ref_label: f.ref_label.value, quiz_md: f.quiz_md.value, active: f.active.checked };
      try {
        if (t.id) await api.patch("/api/training/topics/" + t.id, body); else await api.post("/api/training/topics", body);
        close(); toast("Topic enregistré.", "success"); reload();
      } catch (err) { error.textContent = err.message; }
    } }, el("div", { class: "form-row" }, field("Code", f.code), field("Titre", f.title)), field("Topic parent", f.parent_id),
    field("Contenu", f.content), el("div", { class: "form-row" }, field("Référence (lien)", f.reference), field("Texte du lien", f.ref_label)),
    field("Test (Markdown)", f.quiz_md), check,
    el("div", { class: "form-row" }, el("button", { type: "button", class: "btn btn-small", onclick: () => {
      if (!f.quiz_md.value.trim()) { f.quiz_md.value = data.example_quiz || ""; runCheck(); }
    } }, "Partir de l'exemple"), el("label", { class: "check" }, f.active, "Actif")), error,
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Enregistrer")));
    close = modal(t.id ? "Modifier le topic " + t.code : "Nouveau topic", form);
    if (t.quiz_md) runCheck();
  }

  /* ---------- administrators: workflow ---------- */
  async function workflowView(main, reload) {
    const data = await api.get("/api/training/workflow");
    main.append(el("div", { class: "page-head" }, el("h1", null, "Workflow Training"),
      el("p", { class: "muted" }, "Qui peut faire chaque passage. « Achieved » exige toujours le test réussi (si le topic en a un) et "
        + "l'évaluation écrite du gestionnaire.")));
    const rows = data.rules.map((r) => ({ r, boxes: Object.keys(data.roles).map((role) =>
      el("input", { type: "checkbox", checked: r[3].includes(role), disabled: !data.can_edit, "aria-label": data.roles[role] + " : " + r[2] })) }));
    main.append(DA.table(["De", "Vers", "Bouton"].concat(Object.values(data.roles)), rows.map(({ r, boxes }) => el("tr", null,
      el("td", null, badge(r[0], data.statuses[r[0]])), el("td", null, badge(r[1], data.statuses[r[1]])), el("td", null, r[2]),
      boxes.map((b) => el("td", null, b))))));
    if (data.can_edit) main.append(el("div", { class: "form-actions tt-left" }, el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
      const rules = rows.map(({ r, boxes }) => [r[0], r[1], r[2], Object.keys(data.roles).filter((_, i) => boxes[i].checked)]);
      try { await api.put("/api/training/workflow", { rules }); toast("Workflow enregistré.", "success"); reload(); } catch (err) { toast(err.message, "error"); }
    } }, "Enregistrer le workflow")));
  }

  DA.registerModule("training", async (shell, parts) => {
    const reload = () => DA.registerModule && location.hash && window.dispatchEvent(new HashChangeEvent("hashchange"));
    let people = [];
    try { const p = await api.get("/api/training/people"); people = p.people; people.me = p.me; } catch (err) { /* shown below */ }
    const view = parts[0] === "plan" && parts[1] ? "plan-" + parts[1] : parts[0] === "test" ? "plan" : parts[0] || "plan";
    const main = layout(shell, view, people);
    try {
      if (parts[0] === "test" && parts[1]) await TR.testView(main, Number(parts[1]));
      else if (parts[0] === "topics") await topicsView(main);
      else if (parts[0] === "admin") await adminView(main, reload);
      else if (parts[0] === "workflow") await workflowView(main, reload);
      else await planView(main, parts[0] === "plan" && parts[1] ? Number(parts[1]) : DA.session.user.id, reload);
    } catch (err) {
      clear(main);
      main.append(el("div", { class: "empty" }, el("p", null, err.message)));
    }
  });
})();
