/* Agile - « Change Management » (D-B-010, D-B-011): problem reports, software
   bugs and ECN, apart from the Agile work. Shows where each item is in the
   change process and what the next step needs. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;

  function base(ctx) { return "/api/agile/p/" + ctx.pid; }


  function keyLinks(ctx, keys) {
    if (!keys || !keys.length) return el("span", { class: "muted" }, "—");
    return el("span", { class: "gm-keys" }, keys.map((k) => el("a", { class: "ag-key",
      href: "#/agile/" + k.split("-")[0] + "/issue/" + k.split("-").pop() }, k)));
  }

  function row(ctx, it, labels) {
    const detail = it.change_role === "ecn"
      ? [it.change_class ? labels.classes[it.change_class] : "classe ?", it.items.length + " article(s)",
        it.tasks.total ? it.tasks.done + "/" + it.tasks.total + " sub-task(s)" : null].filter(Boolean).join(" · ")
      : (it.severity ? labels.severities[it.severity] : "sévérité ?");
    return el("tr", null,
      el("td", null, A.typeIcon(it.icon_key, it.type_name)),
      el("td", { class: "nowrap" }, el("a", { class: "ag-key", href: "#/agile/" + ctx.key + "/issue/" + it.number }, it.key)),
      el("td", null, el("a", { href: "#/agile/" + ctx.key + "/issue/" + it.number }, it.title)),
      el("td", null, A.statusBadge(it.status_name, it.status_category)),
      el("td", { class: "muted" }, detail),
      el("td", null, keyLinks(ctx, it.change_role === "ecn" ? it.treats : it.treated_by)),
      el("td", { class: "muted" }, it.assignee_name || "—"),
      el("td", { class: "muted nowrap" }, A.relativeDate(it.updated_at)));
  }

  function section(title, hint, headers, items, ctx, labels) {
    return el("section", { class: "gm-section" },
      el("div", { class: "gm-section-head" }, el("h2", null, title + " (" + items.length + ")"),
        el("span", { class: "muted" }, hint)),
      items.length
        ? el("div", { class: "table-wrap" }, DA.table(headers, items.map((it) => row(ctx, it, labels))))
        : el("p", { class: "muted" }, "Rien ici avec ces filtres."));
  }

  function counters(items) {
    const n = (fn) => items.filter(fn).length;
    const open = (it) => it.status_category !== "done";
    const tiles = [
      ["Problèmes ouverts", n((it) => ["pr", "bug"].includes(it.change_role) && open(it) && it.status_name !== "Derived to ECN")],
      ["Dérivés, en attente d'ECN fermé", n((it) => it.status_name === "Derived to ECN")],
      ["ECN au CCB", n((it) => it.change_role === "ecn" && ["Submitted", "CCB Review"].includes(it.status_name))],
      ["ECN en implantation", n((it) => it.change_role === "ecn" && ["Approved", "In Implementation", "In Verification"]
        .includes(it.status_name))],
    ];
    return el("div", { class: "gm-counters" }, tiles.map(([label, value]) =>
      el("div", { class: "gm-counter" }, el("strong", null, String(value)), el("span", null, label))));
  }

  async function changesView(page, ctx) {
    const data = await api.get(base(ctx) + "/changes");
    const reload = () => { clear(page); changesView(page, ctx); };
    const create = (role) => A.openCreate(ctx, { typeId: data.types[role].id, types: [data.types[role].id],
      onCreated: (made) => { location.hash = "#/agile/" + ctx.key + "/issue/" + made.number; } });
    page.append(A.pageHead(ctx, [el("span", null, "Change Management")],
      data.enabled && A.canEdit(ctx) ? el("span", { class: "gm-create" },
        el("button", { type: "button", class: "btn", onclick: () => create("pr") }, "Signaler un problème (PR)"),
        el("button", { type: "button", class: "btn", onclick: () => create("bug") }, "Signaler un bug"),
        el("button", { type: "button", class: "btn", onclick: () => create("ecn") }, "Nouvel ECN")) : null));
    if (!data.enabled) {
      page.append(el("div", { class: "empty" },
        el("h2", null, "Change Management n'est pas activé sur ce projet"),
        el("p", { class: "muted" }, "L'activation crée les types PR, Bug, ECN et Task ECN, avec deux workflows : "
          + "Problème (Ouvert → En analyse → Dérivé en ECN → Fermé, ou Rejeté) et ECN (Brouillon → Soumis → "
          + "En revue CCB → Approuvé → En implantation → En vérification → Fermé). Les ECN et bugs existants "
          + "quittent les tickets Agile et passent ici, avec leur historique."),
        A.isAdmin(ctx) ? el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
          try {
            const res = await api.post(base(ctx) + "/changes/setup");
            toast("Change Management activé : " + res.types.join(", ") + ".", "success");
            ctx.refresh();
          } catch (err) { toast(err.message, "error"); }
        } }, "Activer Change Management") : el("p", null, "Demandez à un administrateur de l'activer.")));
      return;
    }
    page.append(el("div", { class: "ag-csv-toolbar" },
      el("button", { type: "button", class: "btn btn-small", onclick: () => A.triggerDownload(ctx, "changes") },
        "Exporter les changements (CSV)")));
    if (!data.items.length && A.canEdit(ctx)) {  // D-B-134
      page.append(DA.spaces.startHere("Aucun changement pour l'instant",
        "Un problème constaté devient une PR (ou un Bug) ; une modification de conception validée devient un ECN, revu en CCB.",
        [["Signaler un problème (PR)", () => create("pr"), true], ["Nouvel ECN", () => create("ecn")]]));
    }
    page.append(counters(data.items));

    const q = el("input", { type: "search", placeholder: "Filtrer (clé, titre)…", "aria-label": "Filtrer" });
    const state = el("select", { "aria-label": "État" }, A.options([["open", "Ouverts"], ["done", "Fermés / rejetés"]], "open", "Tous"));
    const kind = el("select", { "aria-label": "Type" }, A.options([["pr", "PR"], ["bug", "Bugs"]], "", "PR et bugs"));
    const out = el("div");
    page.append((DA.mineBanner && DA.mineBanner()) || "", el("div", { class: "ag-filters" }, q, state, kind), out);
    function draw() {
      clear(out);
      const text = q.value.trim().toLowerCase();
      const mine = DA.myItems && DA.myItems();  // « Mes éléments » (D-B-033)
      const keep = (it) => (!mine || it.assignee_id === DA.session.user.id) && (!text || (it.key + " " + it.title).toLowerCase().includes(text))
        && (!state.value || (state.value === "done") === (it.status_category === "done"));
      const problems = data.items.filter((it) => ["pr", "bug"].includes(it.change_role) && keep(it) && (!kind.value || it.change_role === kind.value));
      const ecns = data.items.filter((it) => it.change_role === "ecn" && keep(it));
      out.append(
        section("Problèmes signalés", "Un PR ou un bug se ferme avec sa cause racine, ou se dérive en ECN.",
          ["", "Key", "Title", "Status", "Severity", "Handled By", "Assignee", "Modifié"], problems, ctx, data.labels),
        section("ECN", "Approbation CCB, implantation par sub-tasks, vérification, fermeture.",
          ["", "Key", "Title", "Status", "Class · Items · Sub-tasks", "Handles", "Assignee", "Modifié"], ecns, ctx, data.labels));
    }
    [q, state, kind].forEach((c) => c.addEventListener("input", draw));
    draw();
  }

  A.views.changes = changesView;
})();
