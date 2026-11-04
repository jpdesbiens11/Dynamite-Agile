/* Goldmine - maturity of a need (D-B-086, generic since 0.60.01): Need Status (Assumption / Customer Confirmed /
   Contractual). Form controls, list filters and record rows used by goldmine.js. */
(function () {
  "use strict";

  const { el, field } = DA;
  const A = DA.agile;

  const NEED_STATUS = { assumption: "Assumption", confirmed: "Customer Confirmed", contractual: "Contractual" };
  const NEW = "0.43.0-";  // D-A-049: [new] tags on what this version added

  /* Form controls; v = current values, kindSelect = the « Nature » select of the form */
  function controls(v, kindSelect) {
    const values = v || {};
    const status = el("select", { "data-new": NEW + "need-status" },
      A.options(Object.entries(NEED_STATUS), values.need_status || (values.kind === "need" ? "assumption" : ""), "—"));
    const statusField = field("Need Status", status, "Assumption = hypothèse de l'équipe ; Customer Confirmed / Contractual = besoin ferme du client");
    const sync = () => { statusField.hidden = kindSelect && kindSelect.value !== "need"; };
    if (kindSelect) kindSelect.addEventListener("change", () => {
      if (kindSelect.value === "need" && !status.value) status.value = "assumption";
      sync();
    });
    sync();
    return {
      layout: () => [el("div", { class: "form-row" }, statusField)],
      values: () => ({ need_status: kindSelect && kindSelect.value !== "need" ? "" : status.value }),
    };
  }

  /* List filters: { byName: {...}, test(r) } */
  function filters() {
    const status = el("select", { "aria-label": "Need Status" },
      A.options(Object.entries(NEED_STATUS), "", "All Need Statuses"));
    return {
      byName: { needStatus: status },
      test: (r) => !status.value || (r.kind === "need" && r.need_status === status.value),
    };
  }

  /* Small chip under the statement of a need in the list */
  function chips(r) {
    return r.kind === "need" && r.need_status
      ? el("div", { class: "gm-need-chips" }, el("span", { class: "badge gm-ns gm-ns-" + r.need_status }, NEED_STATUS[r.need_status]))
      : null;
  }

  function rows(r, row) {
    return [r.kind === "need" ? row("Need Status", NEED_STATUS[r.need_status] || "") : null];
  }

  A.needFields = { controls, filters, chips, rows, NEED_STATUS };
})();
