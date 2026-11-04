/* Goldmine Q&A dialogs (D-B-037): new question, reopen with a reason, and
   the import of the client's returned Excel file (dry run, then apply). */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field } = DA;
  const A = DA.agile;
  const base = (ctx) => "/api/agile/p/" + ctx.pid;
  const ACTIONS = { create: ["Nouvelle question client", "warn"], answer: ["Réponse du client", "ok"], status: ["Status changé", "warn"],
    comment: ["Commentaire", "neutral"], unchanged: ["Inchangé", "neutral"], refused: ["Refusé", "off"] };

  /* ---------- New question ---------- */
  A.qaNewDialog = async function (ctx, issue, done) {
    let requirement = null;
    if (!issue) {
      try {
        const data = await api.get(base(ctx) + "/goldmine");
        requirement = el("select", { required: true }, el("option", { value: "" }, "— choisir le requirement —"),
          data.requirements.map((r) => el("option", { value: r.number }, r.key + " · " + r.title)));
      } catch (err) { toast(err.message, "error"); return; }
    }
    const direction = el("select", null, A.options([["team", "Qteam — question de l'équipe au client"],
      ["cust", "Qcust — question ou préoccupation du client (reçue par courriel, réunion…)"]], "team"));
    const text = el("textarea", { rows: 4, maxlength: 4000, required: true,
      placeholder: "Astuce : proposez une valeur que le client n'a qu'à confirmer, ex. « 180 °C ± 10 °C à la buse ? »" });
    const client = el("input", { type: "text", maxlength: 80, placeholder: "Nom ou initiales du client" });
    const clientField = field("Posée par (client)", client);
    clientField.hidden = true;
    direction.addEventListener("change", () => { clientField.hidden = direction.value !== "cust"; });
    const due = el("input", { type: "date" });
    const blocking = el("input", { type: "checkbox" });
    let close = null;
    const form = el("form", { class: "form", onsubmit: async (ev) => {
      ev.preventDefault();
      const number = issue ? issue.number : requirement.value;
      if (!number) { toast("Choisissez le requirement.", "error"); return; }
      try {
        const q = await api.post(base(ctx) + "/issues/" + number + "/qa", { direction: direction.value, question: text.value,
          external_name: client.value, due_date: due.value || null, blocking: blocking.checked });
        close();
        toast(q.full_ref + " créée (" + q.asked_stamp + ").", "success");
        done(q.id);
      } catch (err) { toast(err.message, "error"); }
    } },
    requirement ? field("Requirement", requirement) : el("p", null, el("strong", null, issue.key), " · " + issue.title),
    field("Sens", direction), clientField, field("Question", text),
    el("div", { class: "form-row" }, field("Due Date (optionnel)", due), el("label", { class: "check" }, blocking, "Blocking")),
    el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
      el("button", { type: "submit", class: "btn btn-primary" }, "Créer la question")));
    text.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); form.requestSubmit(); } });
    close = modal("Nouvelle question", form);
    (requirement || text).focus();
  };

  /* ---------- Reopen with a reason ---------- */
  A.qaReopenDialog = function (q, done, cancelling) {
    const note = el("textarea", { rows: 3, maxlength: 4000, placeholder: cancelling ? "Pourquoi la question n'a plus lieu d'être…" : "Ce qui manque ou ce qui ne convient pas…" });
    let close = null;
    const form = el("form", { class: "form", onsubmit: (ev) => { ev.preventDefault(); close(); done(note.value); } },
      el("p", { class: "muted" }, "La raison est gardée dans l'historique signé de " + q.ref + "."),
      field("Raison", note),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: cancelling ? "btn btn-danger" : "btn btn-primary" }, cancelling ? "Annuler la question" : "Rouvrir")));
    close = modal((cancelling ? "Annuler " : "Rouvrir ") + q.full_ref, form);
    note.focus();
  };

  /* ---------- Archives of the exchanged workbooks ---------- */
  A.qaArchivesDialog = async function (ctx) {
    let data;
    try { data = await api.get(base(ctx) + "/qa/archives"); } catch (err) { toast(err.message, "error"); return; }
    const size = (n) => Math.max(1, Math.round(n / 1024)) + " Ko";
    modal("Archives des échanges Q&R", el("div", null,
      el("p", { class: "muted" }, "Chaque export, import appliqué et registre est gardé ici (date et heure dans le nom)."),
      DA.table(["Fichier", "Type", "Taille"], data.archives.map((a) => el("tr", null,
        el("td", null, el("a", { href: base(ctx) + "/qa/archives/" + encodeURIComponent(a.name), download: "" }, a.name)),
        el("td", null, a.kind), el("td", { class: "num" }, size(a.size)))))));
  };

  /* ---------- Import of the client's file ---------- */
  A.qaImportDialog = function (ctx, done) {
    const file = el("input", { type: "file", accept: ".xlsx" });
    const out = el("div", { class: "qa-import-out" });
    const apply = el("button", { type: "button", class: "btn btn-primary", disabled: true }, "Appliquer");
    let close = null;
    async function run(dry) {
      if (!file.files[0]) { toast("Choisissez le fichier renvoyé par le client.", "error"); return; }
      apply.disabled = true;
      try {
        const res = await api.upload(base(ctx) + "/qa/import?dry_run=" + (dry ? "1" : "0"), file.files[0]);
        show(res);
        if (dry) apply.disabled = !res.lines.some((l) => ["create", "answer", "status", "comment"].includes(l.action));
        else { toast("Retour du client appliqué.", "success"); close(); done(); }
      } catch (err) { toast(err.message, "error"); }
    }
    function show(res) {
      clear(out);
      out.append(el("div", { class: "qa-chips" }, Object.entries(res.summary).map(([k, n]) =>
        el("span", { class: "badge badge-" + (ACTIONS[k] || ["", "neutral"])[1] }, (ACTIONS[k] || [k])[0] + " : " + n))),
      res.lines.length ? DA.table(["Feuille", "Ligne", "Réf.", "Action", "Détail"], res.lines.map((l) => el("tr", null,
        el("td", null, l.sheet), el("td", { class: "num" }, String(l.line)), el("td", { class: "nowrap" }, l.ref),
        el("td", null, DA.badge((ACTIONS[l.action] || [l.action])[0], (ACTIONS[l.action] || ["", "neutral"])[1])),
        el("td", null, l.message)))) : el("p", { class: "muted" }, "Le fichier ne contient aucune réponse ni question."),
      res.dry_run ? el("p", { class: "muted" }, "Vérification à blanc : rien n'est encore enregistré. Chaque ligne appliquée sera datée "
        + "et signée (initiales du client, ou « Client »).") : null);
    }
    file.addEventListener("change", () => run(true));
    apply.addEventListener("click", () => run(false));
    const body = el("div", { class: "form" },
      el("p", null, "Choisissez le fichier « Q&R » (.xlsx) renvoyé par le client : chaque ligne est comparée au registre "
        + "(nouvelle question, réponse, status, commentaire). Un même fichier importé deux fois ne change rien ; "
        + "il est archivé à l'application."),
      field("Fichier du client", file), out,
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Fermer"), apply));
    close = modal("Importer le retour du client", body);
    const dialog = body.closest(".modal");
    if (dialog) dialog.classList.add("qa-import-modal");
  };
})();
