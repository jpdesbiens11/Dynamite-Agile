/* Exploration - Import / Export screen (D-B-019): export to Excel (Gantt +
   « Lisez-moi » for people and AI agents) or CSV, then import the reviewed
   file: « Vérifier » writes nothing and lists every change, « Appliquer »
   is possible only when no row is refused. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const EX = DA.exploration;

  const ACTION_BADGE = { "créée": "badge-ok", "mise à jour": "badge-info", "inchangée": "badge-neutral",
    "supprimée": "badge-warn", "refusée": "badge-off" };

  function aiPrompt(ctx) {
    const names = ctx.data.members.map((m) => m.display_name + " (" + m.username + ")").join(", ");
    return "Tu prépares le plan d'exploration du projet " + ctx.project.name + " (" + ctx.key + ") : un Gantt "
      + "abstrait sur plusieurs mois, pas des tickets.\n"
      + "Réponds par un fichier Excel .xlsx (ou un CSV) dont la feuille « Plan » a exactement ces en-têtes : "
      + "ID, Phase, Task, Description, Owner, Predecessors, Duration (wk), Start No Earlier Than, Status, "
      + "Progress (%), Status Note.\n"
      + "Règles : une task par ligne ; ID courts et uniques (T1, T2…) ; Predecessors = ID séparés par des virgules "
      + "(finish → start, sans boucle) ; Duration en semaines (0 = milestone) ; dates AAAA-MM-JJ ; Status parmi To Do, "
      + "In Progress, Done, Blocked ; Owner parmi : " + (names || "(aucun membre)") + ".\n"
      + "Pars du fichier exporté joint et conserve les ID existants. Plan Start : " + ctx.data.start_date + ".";
  }

  function reportView(result) {
    const s = result.summary;
    const box = el("div", { class: "ex-report" });
    const blocked = s["refusée"] || result.problems.length;
    box.append(el("p", { class: blocked ? "rules-bad" : "rules-good" },
      (result.applied ? "Plan importé : " : "Vérification : ") + s["créée"] + " créée(s), " + s["mise à jour"]
      + " mise(s) à jour, " + s["inchangée"] + " inchangée(s), " + s["supprimée"] + " retirée(s), " + s["refusée"]
      + " refusée(s)." + (blocked ? " Corrigez le fichier puis vérifiez de nouveau." : (result.applied ? "" : " Vous pouvez appliquer."))));
    result.problems.forEach((p) => box.append(el("p", { class: "form-error" }, p)));
    if (result.start_date) box.append(el("p", { class: "muted" }, "Plan Start lu dans « Lisez-moi » : " + result.start_date + "."));
    box.append(DA.table(["Ligne", "ID", "Task", "Résultat", "Détail"], result.report.map((r) =>
      el("tr", { class: r.action === "refusée" ? "rules-row-bad" : null },
        el("td", { class: "muted" }, String(r.line)), el("td", null, el("code", null, r.code)), el("td", null, r.title),
        el("td", null, el("span", { class: "badge " + (ACTION_BADGE[r.action] || "badge-neutral") }, r.action)),
        el("td", null, r.detail)))));
    return box;
  }

  function transferView(page, ctx, reload) {
    const base = EX.base(ctx);
    page.append(el("div", { class: "page-head" }, el("h1", null, "Import / Export — " + ctx.project.name),
      el("p", { class: "muted" }, "Le plan se prépare et se revoit en équipe dans Excel (souvent avec un agent IA), "
        + "se charge ici, puis chacun suit ses tasks dans l'interface.")));
    page.append(el("ol", { class: "ex-steps" },
      el("li", null, el("strong", null, "Exporter"), " le plan actuel (même vide : il sert de modèle)."),
      el("li", null, el("strong", null, "Retravailler"), " le fichier avec l'équipe ou un agent IA (prompt ci-dessous)."),
      el("li", null, el("strong", null, "Vérifier"), " le fichier revu : rien n'est écrit, chaque changement est listé."),
      el("li", null, el("strong", null, "Appliquer"), " : le fichier devient le plan (les tasks absentes sont retirées).")));

    page.append(el("section", { class: "ex-card" }, el("h2", null, "Exporter"),
      el("div", { class: "ex-actions" },
        el("a", { class: "btn btn-primary", href: base + "/export.xlsx", download: "" }, "Excel (.xlsx) avec Gantt"),
        el("a", { class: "btn", href: base + "/export.csv", download: "" }, "CSV")),
      el("p", { class: "muted" }, "Le classeur contient la feuille « Plan » (Début et Fin calculés par formules, barres du "
        + "Gantt par semaine, listes déroulantes Status et Assignee) et la feuille « Lisez-moi » (règles, "
        + "responsables possibles, début du plan).")));

    const prompt = el("textarea", { class: "ex-prompt", rows: 7, readonly: true, "aria-label": "Consigne pour l'agent IA" }, aiPrompt(ctx));
    page.append(el("section", { class: "ex-card" }, el("h2", null, "Consigne pour un agent IA"),
      el("p", { class: "muted" }, "À coller dans l'outil IA avec le fichier exporté."), prompt,
      el("div", { class: "ex-actions" }, el("button", { type: "button", class: "btn", onclick: async () => {
        try { await navigator.clipboard.writeText(prompt.value); toast("Consigne copiée.", "success"); }
        catch (err) { prompt.select(); toast("Sélectionnée : faites Ctrl+C.", "info"); }
      } }, "Copier la consigne"))));

    if (!ctx.data.can_admin) {
      page.append(el("section", { class: "ex-card" }, el("h2", null, "Importer"),
        el("p", { class: "muted" }, "Réservé aux administrateurs : transmettez-leur le fichier revu.")));
      return;
    }
    let file = null;
    const out = el("div");
    const name = el("span", { class: "muted" }, "Aucun fichier choisi.");
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: true, onclick: () => send(false) }, "Appliquer");
    const input = el("input", { type: "file", accept: ".xlsx,.csv", hidden: true, onchange: () => {
      file = input.files[0] || null;
      input.value = "";
      name.textContent = file ? file.name + " (" + Math.round(file.size / 1024) + " Ko)" : "Aucun fichier choisi.";
      apply.disabled = true;
      clear(out);
      if (file) send(true);
    } });
    async function send(dry) {
      if (!file) { toast("Choisissez d'abord un fichier .xlsx ou .csv.", "error"); return; }
      try {
        const result = await api.upload(base + "/import?dry_run=" + (dry ? "1" : "0"), file);
        clear(out);
        out.append(reportView(result));
        apply.disabled = !dry || !!(result.summary["refusée"] || result.problems.length);
        if (result.applied) {
          toast("Plan importé.", "success");
          location.hash = "#/exploration/" + ctx.key + "/plan";
        }
      } catch (err) { toast(err.message, "error"); }
    }
    page.append(el("section", { class: "ex-card" }, el("h2", null, "Importer"),
      el("div", { class: "ex-actions" },
        el("button", { type: "button", class: "btn", onclick: () => input.click() }, "Choisir un fichier…"), input, name,
        el("button", { type: "button", class: "btn", onclick: () => send(true) }, "Vérifier (rien n'est écrit)"), apply),
      out));
  }

  EX.transferView = transferView;
})();
