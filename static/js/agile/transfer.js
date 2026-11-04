/* Agile - "Import / Export" screen: every CSV exchange of the project in one
   place (tickets, client Q&A, Change Management; in the Goldmine tab: requirements), so
   the function is found from the left menu instead of hunting for buttons. */
(function () {
  "use strict";

  const { el } = DA;
  const A = DA.agile;

  function card(title, text, columns, exportKind, exportLabel, importKind, importLabel, ctx, extra) {
    return el("section", { class: "ag-transfer-card" },
      el("h2", null, title),
      el("p", null, text),
      columns ? el("p", { class: "muted ag-transfer-cols" }, "Colonnes : ", el("code", null, columns)) : null,
      extra || null,
      el("div", { class: "ag-transfer-actions" },
        el("button", { type: "button", class: "btn btn-primary", onclick: () => A.triggerDownload(ctx, exportKind) }, exportLabel),
        !A.canEdit(ctx) ? null : importKind === "requirements" ? A.goldmineImportButton(ctx, importLabel, null)  // D-B-070
          : A.csvImportButton(ctx, importKind, importLabel, null),
        A.canEdit(ctx) ? null
          : el("span", { class: "muted" }, "Import réservé aux éditeurs du projet.")));
  }

  function transferView(page, ctx) {
    page.append(A.pageHead(ctx, [el("span", null, "Import / Export")]));
    page.append(el("p", { class: "muted ag-transfer-intro" },
      "Fichiers CSV lisibles par Excel (séparateur « , » ou « ; », UTF-8 ou Windows-1252). ",
      "Partez toujours d'un export : modifiez-le dans Excel, puis réimportez-le. Chaque ligne refusée ",
      "est listée avec son numéro de ligne Excel et le correctif ; rien n'est écrit pour une ligne refusée."));
    const goldmine = ctx.module === "goldmine";  // D-B-011: requirements in their own tab
    page.append(el("div", { class: "ag-transfer" },
      goldmine ? null : card("Tickets", "Tous les tickets du projet. Key vide = création ; clé existante (ex. " + ctx.key + "-12) = mise à jour ; "
        + "clé pas encore utilisée = création avec cette clé. Réimporter le même fichier ne change rien (lignes « inchangée »). "
        + "Le status doit être atteignable par le workflow. La colonne client_summary porte la synthèse client "
        + "(sans le fil de commentaires).",
      "key, parent_key, type, title, description, priority, status, assignee, labels, sprint, version, points, due_date, updated_at, implements, client_summary",
      "tickets", "Exporter les tickets", "tickets", "Importer des tickets", ctx),
      goldmine ? null : card("Q&A client", "Les commentaires marqués « Question » et leurs réponses, pour les échanger "
        + "avec un client. L'import ajoute des réponses ; il ne modifie ni ne supprime jamais rien.",
      "issue_key, comment_id, parent_comment_id, requirement_ref, author, is_question, body, created_at",
      "questions", "Exporter les questions", "questions", "Importer des réponses", ctx),
      !goldmine ? null : card("Requirements", "Requirements d'ingénierie avec leurs attributs (criticité, méthode IADT, acceptance criteria…). "
        + "L'import accepte une spec client telle quelle : seules les colonnes Statement et ID (ou clé) sont requises. "
        + "Ce bouton exporte tout ; pour un petit lot, filtrez l'écran Requirements puis « Exporter la sélection ». "
        + "À la réimportation, un aperçu liste tous les champs qui remplaceraient une valeur de Goldmine : "
        + "décochez ceux à garder, puis confirmez deux fois. Les requirements absentes du fichier ne sont pas touchées.",
      null, "requirements", "Exporter les requirements", "requirements", "Importer une spec / des requirements", ctx,
      el("p", { class: "muted" }, "Goldmine doit être activé sur le projet (bouton « Activer Goldmine »).")),
      goldmine ? null : el("section", { class: "ag-transfer-card" },
        el("h2", null, "Change Management"),
        el("p", null, "PR, bugs et ECN avec leurs champs de gestion du changement, les articles touchés "
          + "(numéro, révision actuelle → nouvelle, disposition) et les liens « traite ». Export seulement ; "
          + "la saisie se fait dans la fiche pour garder les contrôles du CCB."),
        el("div", { class: "ag-transfer-actions" },
          el("button", { type: "button", class: "btn btn-primary", onclick: () => A.triggerDownload(ctx, "changes") },
            "Exporter les changements")))));
  }

  A.views.csv = transferView;
})();
