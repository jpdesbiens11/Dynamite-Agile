/* Diamond · Arbre fonctionnel: the panel of the selected function (0.60.11). Reading aid (pourquoi ? comment ?
   quand ?), its fields, and the moves -- earlier / later (quand), one level left / right, out of the tree, archive.
   Alt + arrows on a box do the same moves from the keyboard. */
(function () {
  "use strict";

  const { el, field } = DA;
  const D = DA.diamond;
  const LEVEL_HELP = {
    1: "Fonction primaire : ce que le produit réalise, le plus simplement possible.",
    2: "Fonction secondaire : un « comment » de la primaire ; elle définit un sous-système.",
    3: "Fonction tertiaire : un « comment » de la secondaire.",
    4: "Fonction technique liée à une tertiaire (hors de l'arbre proprement dit).",
  };

  const byId = (items, id) => items.find((f) => f.id === id);
  const code = (f) => "F" + f.number;
  const siblings = (items, f) => D.children(items, f.parent_id);

  /* the moves a function allows: {up, down, left, right} -> body of POST …/move, or null */
  function moves(items, f) {
    if (!f.in_tree || f.is_primary) return {};
    const sibs = siblings(items, f);
    const i = sibs.findIndex((s) => s.id === f.id);
    const parent = byId(items, f.parent_id);
    const out = {};
    if (i > 0) out.up = { parent_id: f.parent_id, index: i - 1 };
    if (i < sibs.length - 1) out.down = { parent_id: f.parent_id, index: i + 1 };
    if (parent && !parent.is_primary) {
      const uncles = siblings(items, parent);
      out.left = { parent_id: parent.parent_id, index: uncles.findIndex((s) => s.id === parent.id) + 1 };
    }
    if (i > 0) out.right = { parent_id: sibs[i - 1].id, index: null };
    return out;
  }

  function reading(items, f) {
    const parent = byId(items, f.parent_id);
    const kids = D.children(items, f.id);
    const sibs = f.in_tree && !f.is_primary ? siblings(items, f) : [];
    const i = sibs.findIndex((s) => s.id === f.id);
    const line = (q, text) => el("p", null, el("strong", null, q + " "), text);
    return el("div", { class: "dm-reading", "data-new": "0.60.11-reading" },
      line("Pourquoi ?", f.is_primary ? "C'est la fonction primaire : la raison d'être du produit."
        : parent && f.in_tree ? "Pour « " + parent.text + " » (" + code(parent) + ")." : "Hors arbre : aucune fonction source."),
      line("Comment ?", kids.length ? kids.map((k) => code(k) + " " + k.text).join(" · ") : "Aucune fonction à droite pour l'instant."),
      f.in_tree && !f.is_primary ? line("Quand ?", (i > 0 ? "après " + code(sibs[i - 1]) : "en premier")
        + (i < sibs.length - 1 ? ", avant " + code(sibs[i + 1]) : ", en dernier") + " dans sa branche.") : null);
  }

  function select(options, value) {
    return el("select", null, Object.entries(options).map(([k, label]) => el("option", { value: k, selected: k === (value || "") }, label)));
  }

  /* run(path, body, method) posts and redraws; ask(text) -> new function text from the add box */
  function panel(state, f, run, editable) {
    const items = state.data.functions;
    const labels = state.data.labels;
    const head = el("div", { class: "dm-panel-head" }, el("span", { class: "dm-code dm-code-big" }, code(f)),
      el("span", { class: "badge badge-neutral" }, f.in_tree ? labels.levels[f.level] : "Hors arbre"));
    const box = el("aside", { class: "dm-panel", "aria-label": "Fonction " + code(f) }, head,
      el("p", { class: "muted dm-help" }, f.in_tree ? LEVEL_HELP[f.level] : "Placez-la dans l'arbre, ou gardez-la pour le CdCF (fonction d'estime)."),
      reading(items, f));
    if (!editable) {
      box.append(el("p", null, f.text), f.notes ? el("p", { class: "muted" }, f.notes) : null);
      return box;
    }
    const text = el("textarea", { rows: 2, maxlength: 160 }, f.text);
    const number = el("input", { type: "number", min: 1, max: 999, value: f.number, class: "dm-number" });
    const ftype = select(labels.types, f.ftype), kano = select(labels.kano, f.kano), importance = select(labels.importance, f.importance);
    const critical = el("input", { type: "checkbox", checked: !!f.critical });
    const feedbackOptions = { "": "— aucune —" };
    items.filter((o) => o.in_tree && o.id !== f.id).forEach((o) => { feedbackOptions[o.id] = code(o) + " " + o.text; });
    const feedback = select(feedbackOptions, f.feedback_to ? String(f.feedback_to) : "");
    const notes = el("textarea", { rows: 2, maxlength: 2000 }, f.notes || "");
    const save = () => run("/functions/" + f.id, { text: text.value, number: Number(number.value), ftype: ftype.value, kano: kano.value,
      importance: importance.value, critical: critical.checked, feedback_to: feedback.value ? Number(feedback.value) : null, notes: notes.value }, "patch");
    box.append(el("form", { class: "ag-form dm-form", onsubmit: (ev) => { ev.preventDefault(); save(); } },
      field("Fonction (verbe + complément)", text),
      el("div", { class: "dm-row" }, field("Numéro", number), field("Type", ftype)),
      el("div", { class: "dm-row" }, field("Kano", kano), field("Importance", importance)),
      el("label", { class: "dm-check", "data-new": "0.60.11-critical" }, critical, " Chemin critique (flèche épaisse)"),
      field("Rétroaction vers (contrôle, flèche pointillée)", feedback),
      field("Notes à la conception", notes),
      el("div", { class: "form-actions" }, el("button", { type: "submit", class: "btn btn-primary btn-small" }, "Enregistrer"))));
    box.append(adder(state, f, run), mover(state, f, run));
    return box;
  }

  function adder(state, f, run) {
    const items = state.data.functions;
    const input = el("input", { type: "text", maxlength: 160, placeholder: "ex. Régler l'intensité", "aria-label": "Nouvelle fonction" });
    const ftype = select(state.data.labels.types, f.level >= 3 ? "technique" : "usage");
    const add = (body) => {
      if (!input.value.trim()) { input.focus(); DA.toast("Écrivez la fonction : un verbe à l'infinitif et son complément.", "error"); return; }
      run("/functions", Object.assign({ text: input.value, ftype: ftype.value }, body), "post");
    };
    const sibs = f.in_tree && !f.is_primary ? siblings(items, f) : [];
    const after = sibs.findIndex((s) => s.id === f.id) + 1;
    return el("div", { class: "dm-add", "data-new": "0.60.11-add" }, el("h3", null, "Ajouter une fonction"), input,
      el("div", { class: "dm-row" }, field("Type", ftype)),
      el("div", { class: "dm-actions" },
        f.in_tree && f.level < 4 ? el("button", { type: "button", class: "btn btn-small btn-primary", "data-tip": "Une réponse à « comment ? »",
          onclick: () => add({ parent_id: f.id }) }, "À droite : comment ? →") : null,
        f.in_tree && !f.is_primary ? el("button", { type: "button", class: "btn btn-small", "data-tip": "La fonction suivante dans le temps, même niveau",
          onclick: () => add({ parent_id: f.parent_id, index: after }) }, "Dessous : ensuite ↓") : null));
  }

  function mover(state, f, run) {
    const items = state.data.functions;
    const m = moves(items, f);
    const btn = (key, label, tip) => el("button", { type: "button", class: "btn btn-small", disabled: !m[key], "data-tip": tip,
      onclick: () => run("/functions/" + f.id + "/move", m[key]) }, label);
    const wrap = el("div", { class: "dm-move", "data-new": "0.60.11-move" }, el("h3", null, "Déplacer"));
    if (f.in_tree && !f.is_primary) {
      wrap.append(el("div", { class: "dm-actions" }, btn("up", "↑ Plus tôt", "Alt + ↑"), btn("down", "↓ Plus tard", "Alt + ↓"),
        btn("left", "← Niveau à gauche", "Alt + ←"), btn("right", "→ Sous la précédente", "Alt + →")),
      el("p", { class: "muted dm-hint" }, "Ou glissez la boîte sur une autre : elle devient l'un de ses « comment »."));
    }
    const tree = items.filter((o) => o.in_tree && o.id !== f.id && o.level < 4);
    if (!f.in_tree) {
      const hasPrimary = items.some((o) => o.is_primary);
      const target = select(Object.fromEntries(tree.map((o) => [String(o.id), code(o) + " " + o.text])), "");
      wrap.append(tree.length ? el("div", { class: "dm-actions" }, target, el("button", { type: "button", class: "btn btn-small btn-primary",
        onclick: () => run("/functions/" + f.id + "/move", { parent_id: Number(target.value) }) }, "Placer à droite de…")) : null,
      !hasPrimary ? el("button", { type: "button", class: "btn btn-small", onclick: () => run("/functions/" + f.id + "/move", { primary: true }) },
        "En faire la fonction primaire") : null);
    }
    wrap.append(el("div", { class: "dm-actions" },
      f.in_tree ? el("button", { type: "button", class: "btn btn-small", "data-tip": "Elle garde ses « comment » et attend hors de l'arbre",
        onclick: () => run("/functions/" + f.id + "/move", { parent_id: null }) }, "Retirer de l'arbre") : null,
      el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => {
        if (window.confirm("Archiver " + code(f) + " « " + f.text + " » ? Ses « comment » prennent sa place ; le numéro "
          + code(f) + " ne sera jamais redonné. L'action est journalisée.")) run("/functions/" + f.id + "/archive", {});
      } }, "Archiver")));
    return wrap;
  }

  DA.diamond = Object.assign(DA.diamond || {}, { panel, moves });
})();
