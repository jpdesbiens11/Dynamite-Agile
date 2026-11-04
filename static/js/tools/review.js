/* Dynamite | Agile - « À vérifier » (0.60.07, D-O-019): a standard named by an AI assistant (Project Starter), confirmed
   by a person. Used by the Goldmine requirement card and the Testing record.
   DA.review.chip(state)                    -> small badge for a list ("" when there is nothing to review)
   DA.review.box({state, checked, standard, editable, url, body, done}) -> the block: badge, what to do, confirm button */
(function () {
  "use strict";

  const { api, el, field, modal, toast } = DA;

  function chip(state) {
    if (state === "to_verify") return el("span", { class: "badge badge-warn", "data-tip": "Norme proposée par un assistant IA : à confirmer" }, "À vérifier");
    return null;
  }

  function confirmDialog(opts) {
    const edition = el("input", { type: "text", maxlength: 80, required: true, placeholder: "ex. IEC 62368-1:2023" });
    const clause = el("input", { type: "text", maxlength: 80, placeholder: "ex. 5.4.2" });
    const error = el("p", { class: "form-error", role: "alert" });
    let close = null;
    const form = el("form", { onsubmit: async (ev) => {
      ev.preventDefault();
      try {
        await api.post(opts.url, Object.assign({ edition: edition.value, clause: clause.value }, opts.body || {}));
        close();
        toast("Norme confirmée.", "success");
        opts.done();
      } catch (err) { error.textContent = err.message; }
    } },
    el("p", null, "Norme proposée : ", el("strong", null, opts.standard || "(non précisée)")),
    el("p", { class: "muted" }, "Vérifiez dans la norme elle-même (bibliothèque, site de l'organisme) l'édition en vigueur pour votre "
      + "marché et la clause qui s'applique. Votre nom et la date seront gardés avec la confirmation."),
    el("div", { class: "form-row" }, field("Édition en vigueur", edition, "Obligatoire"), field("Clause", clause, "Facultatif")),
    error,
    el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary" }, "Confirmer la norme")));
    close = modal("Confirmer la norme", form);
  }

  function box(opts) {
    if (opts.state === "verified") {
      return el("p", { class: "review-line review-ok", "data-new": "0.60.07-review" }, DA.badge("Norme confirmée", "ok"), " ", opts.checked);
    }
    if (opts.state !== "to_verify") return null;
    return el("div", { class: "review-line", role: "note", "data-new": "0.60.07-review" },
      DA.badge("À vérifier", "warn"), " ",
      el("span", null, "Norme proposée par un assistant IA. Elle doit être confirmée avant « " + opts.blocks + " »."), " ",
      opts.editable ? el("button", { type: "button", class: "btn btn-small", onclick: () => confirmDialog(opts) }, "Confirmer la norme") : null);
  }

  DA.review = { chip, box };
})();
