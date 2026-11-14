/* Diamond · PFMEA: the editor of one row (0.60.103, D-O-114), unfolded under it in the table (a form this size would not fit
   in a dialog without a scroll bar, D-B-118). S: empty = inherited from the DFMEA through the characteristic; a lower value
   is refused by the server (the process cannot make an effect less severe). */
(function () {
  "use strict";

  const { el } = DA;
  const D = DA.diamond;

  function editor(state, r, line) {
    const d = state.data;
    const opt = (pairs, value, label) => el("select", { "aria-label": label }, pairs.map(([v, text]) => el("option", { value: v, selected: String(value == null ? "" : value) === String(v) }, text)));
    const text = (k, rows) => (rows ? el("textarea", { rows, "aria-label": d.labels.texts[k] }, r[k] || "") : el("input", { type: "text", value: r[k] || "", "aria-label": d.labels.texts[k] }));
    const rating = (k, label) => opt([["", "—"]].concat([...Array(10)].map((_, i) => [i + 1, String(i + 1)])), r[k], label);
    const f = {
      operation_id: opt(line.operations.map((o) => [o.id, "OP" + o.op + " · " + o.name]), r.operation_id, "Opération"),
      process_step: text("process_step"), characteristic_id: opt([["", "— caractéristique de procédé, sans C-n —"]].concat(d.characteristics.map((c) =>
        [c.id, c.code + (c.class_code ? " " + c.class_symbol : "") + " · " + c.label])), r.characteristic_id, "Caractéristique produit"),
      process_char: text("process_char"), failure_mode: text("failure_mode", 2), effect: text("effect", 2), cause: text("cause", 2),
      cause_5m: opt([["", "— 5M —"]].concat(Object.entries(d.labels.causes)), r.cause_5m, "Cause 5M"), prevention: text("prevention", 2),
      detection_ctrl: text("detection_ctrl", 2), severity: rating("severity", "S"), occurrence: rating("occurrence", "O"), detection: rating("detection", "D"),
      action: text("action", 2), action_owner_id: opt([["", "— personne —"]].concat(d.members.map((m) => [m.id, m.display_name])), r.action_owner_id, "Responsable"),
      action_due: el("input", { type: "date", value: r.action_due || "", "aria-label": "Échéance" }),
      action_status: opt(Object.entries(d.labels.statuses), r.action_status, "Status de l'action"),
    };
    const save = () => {
      const body = {};
      Object.entries(f).forEach(([k, input]) => { body[k] = input.value; });
      state.open = null;
      state.send("patch", "/rows/" + r.id, body, r.code + " enregistrée.");
    };
    return el("div", { class: "dm-pf-edit" },
      el("div", { class: "dm-ch-grid" },
        el("fieldset", null, el("legend", null, "Étape"), DA.field("Opération", f.operation_id), DA.field("Process Step", f.process_step),
          DA.field("Product Characteristic", f.characteristic_id), DA.field("Process Characteristic", f.process_char)),
        el("fieldset", null, el("legend", null, "Chaîne de défaillance"), DA.field("Failure Mode", f.failure_mode), DA.field("Failure Effect", f.effect),
          DA.field("Failure Cause", f.cause), DA.field("Cause (5M)", f.cause_5m)),
        el("fieldset", null, el("legend", null, "Contrôles et cotation"), DA.field("Prevention Controls", f.prevention), DA.field("Detection Controls", f.detection_ctrl),
          el("div", { class: "dm-ch-row-f" }, DA.field("S" + (r.inherited_s ? " (≥ " + r.inherited_s + ", DFMEA L" + r.dfmea_line + ")" : ""), f.severity),
            DA.field("O", f.occurrence), DA.field("D", f.detection))),
        el("fieldset", null, el("legend", null, "Action"), DA.field("Actions", f.action), DA.field("Responsable", f.action_owner_id),
          el("div", { class: "dm-ch-row-f" }, DA.field("Échéance", f.action_due), DA.field("Status", f.action_status)))),
      el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-primary", onclick: save }, "Enregistrer"),
        el("button", { type: "button", class: "btn", onclick: () => { state.open = null; state.send("get", "", null, null); } }, "Fermer")));
  }

  D.pfmeaEditor = editor;
})();
