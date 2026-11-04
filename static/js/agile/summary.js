/* Agile - "Synthèse client" block on the ticket page (D-B-001).
   One curated text per ticket, exported with the CSV; the comment thread
   stays the full record. Any comment can be taken over into it. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal } = DA;
  const A = DA.agile;
  const MAX = 4000;

  function counter(area) {
    const out = el("span", { class: "muted ag-summary-count" });
    const update = () => {
      out.textContent = area.value.length + " / " + MAX;
      out.classList.toggle("ag-over", area.value.length > MAX);
    };
    area.addEventListener("input", update);
    update();
    return out;
  }

  async function saveSummary(url, text, fromCommentId, reload) {
    try {
      const result = await api.put(url + "/summary",
        { client_summary: text, from_comment_id: fromCommentId || null });
      toast(result.changed ? "Synthèse client enregistrée." : "Aucun changement.", "success");
      reload();
      return true;
    } catch (err) {
      toast(err.message, "error");
      return false;
    }
  }

  function summaryBlock(ctx, issue, editable, url, reload) {
    const box = el("section", { class: "ag-block ag-summary", "aria-labelledby": "ag-summary-title" });

    function show() {
      clear(box);
      box.append(...[  // DOM append() would print a null as the text "null"
        el("div", { class: "ag-block-head" },
          el("h2", { id: "ag-summary-title" }, "Synthèse client"),
          editable ? el("button", { type: "button", class: "link-btn", onclick: edit },
            issue.client_summary ? "Modifier" : "Rédiger") : null),
        issue.client_summary
          ? el("div", { class: "ag-summary-text" }, issue.client_summary)
          : el("p", { class: "muted" }, "Aucune synthèse. Position à transmettre au client, "
            + "exportée dans le CSV (colonne « client_summary ») sans le fil de commentaires."),
        issue.client_summary_at
          ? el("p", { class: "muted ag-summary-meta" }, "Mise à jour par "
            + (issue.client_summary_by_name || "ancien compte") + " · " + DA.formatDate(issue.client_summary_at))
          : null].filter(Boolean));
    }

    function edit() {
      clear(box);
      const area = el("textarea", { rows: 6, "aria-label": "Synthèse client" });
      area.value = issue.client_summary || "";
      const submit = el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
        submit.disabled = true;
        if (!(await saveSummary(url, area.value, null, reload))) submit.disabled = false;
      } }, "Enregistrer");
      box.append(el("h2", { id: "ag-summary-title" }, "Synthèse client"), area,
        el("div", { class: "form-actions" }, counter(area),
          el("button", { type: "button", class: "btn", onclick: show }, "Annuler"), submit));
      area.focus();
    }

    show();
    return box;
  }

  /* Take a comment over into the summary: replace it or append to it. */
  function promoteComment(issue, comment, url, reload) {
    const area = el("textarea", { rows: 6, "aria-label": "Texte repris du commentaire" });
    area.value = comment.body;
    let close = null;
    async function apply(mode) {
      const current = issue.client_summary || "";
      const text = mode === "append" && current ? current + "\n\n" + area.value : area.value;
      if (await saveSummary(url, text, comment.id, reload)) close();
    }
    close = modal("Reprendre dans la synthèse client", el("div", { class: "ag-form" },
      el("p", { class: "muted" }, "Ajustez le texte au besoin. L'historique du ticket garde "
        + "l'ancienne synthèse et le numéro du commentaire repris."),
      area,
      el("div", { class: "form-actions" }, counter(area),
        el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        issue.client_summary
          ? el("button", { type: "button", class: "btn", onclick: () => apply("append") }, "Ajouter à la fin")
          : null,
        el("button", { type: "button", class: "btn btn-primary", onclick: () => apply("replace") },
          issue.client_summary ? "Remplacer la synthèse" : "Créer la synthèse"))));
  }

  A.summaryBlock = summaryBlock;
  A.promoteComment = promoteComment;
})();
