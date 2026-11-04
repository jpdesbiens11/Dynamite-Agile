/* Diamond · Structure fonctionnelle: the panel beside the diagram (0.60.13). Nothing selected: add an input or an
   output. A box selected: its flows in this view, a new flow from it (to a chosen target, or « Relier en cliquant la
   cible »), and for an input / output its name, kind or removal. A flow selected: its kind, label, removal. */
(function () {
  "use strict";

  const { el, field } = DA;
  const D = DA.diamond;

  function select(options, value) {
    return el("select", null, Object.entries(options).map(([k, label]) => el("option", { value: k, selected: k === value }, label)));
  }

  const name = (data, type, id) => {
    if (type === "port") { const p = data.ports.find((x) => x.id === id); return p ? p.label : "?"; }
    const f = [...data.views.general, ...data.views.detail].find((x) => x.id === id);
    return f ? "F" + f.number + " " + f.text : "?";
  };
  const endName = (data, fl, side) => fl[side + "_port_id"] ? name(data, "port", fl[side + "_port_id"]) : name(data, "function", fl[side + "_function_id"]);

  function idle(state, run, editable) {
    const kinds = state.data.labels.kinds;
    const box = el("aside", { class: "dm-panel dm-panel-idle" },
      el("p", { class: "muted" }, "Cliquez un bloc pour voir ses flux ou en tracer un nouveau ; cliquez un flux pour le modifier. "
        + "Glissez les blocs pour les placer (Alt + flèches au clavier)."));
    if (!editable) return box;
    const adder = (side, title, hint) => {
      const label = el("input", { type: "text", maxlength: 80, placeholder: hint });
      const kind = select(kinds, side === "in" ? "energy" : "energy");
      return el("form", { class: "ag-form dm-form dm-add", "data-new": "0.60.13-port-" + side, onsubmit: (ev) => {
        ev.preventDefault();
        run("/ports", { side, label: label.value, kind: kind.value });
      } }, el("h3", null, title), label, el("div", { class: "dm-row" }, field("Type de flux", kind)),
      el("div", { class: "dm-actions" }, el("button", { type: "submit", class: "btn btn-small btn-primary" }, "Ajouter")));
    };
    box.append(adder("in", "Ajouter une entrée du système", "ex. Alimentation électrique 120 V"),
      adder("out", "Ajouter une sortie du système", "ex. Colle liquide appliquée"));
    return box;
  }

  function nodePanel(state, sel, run, editable, startLink) {
    const data = state.data, view = state.view, kinds = data.labels.kinds;
    const k = D.structureKey(sel.type, sel.id);
    const mine = data.flows.filter((fl) => fl.view === view && D.flowEnds(fl).includes(k));
    const port = sel.type === "port" ? data.ports.find((p) => p.id === sel.id) : null;
    const box = el("aside", { class: "dm-panel", "aria-label": name(data, sel.type, sel.id) },
      el("div", { class: "dm-panel-head" }, el("strong", null, name(data, sel.type, sel.id)),
        el("span", { class: "badge badge-neutral" }, port ? data.labels.sides[port.side] : view === "general" ? "Sous-système" : "Fonction")));
    box.append(el("div", { class: "dm-reading" }, el("p", null, el("strong", null, "Flux de ce bloc (" + mine.length + ")")),
      mine.length ? el("ul", { class: "dm-flow-list" }, mine.map((fl) => el("li", null,
        el("span", { class: "dm-key dm-key-" + fl.kind }, kinds[fl.kind]), " ", endName(data, fl, "src") + " → " + endName(data, fl, "dst")
          + (fl.label ? " (" + fl.label + ")" : "")))) : el("p", { class: "muted" }, "Aucun flux dans cette vue.")));
    if (!editable) return box;
    const targets = { "": "— choisir la cible —" };
    const candidates = data.views[view].map((f) => ["function:" + f.id, "F" + f.number + " " + f.text])
      .concat(data.ports.filter((p) => p.side === "out").map((p) => ["port:" + p.id, "Sortie · " + p.label]));
    candidates.filter(([key]) => key !== k).forEach(([key, label]) => { targets[key] = label; });
    const target = select(port && port.side === "out" ? { "": "Une sortie reçoit les flux : partez d'une fonction" } : targets, "");
    const kind = select(kinds, port ? port.kind : "energy");
    const label = el("input", { type: "text", maxlength: 60, placeholder: "ex. courant, chaleur, consigne" });
    const body = () => ({ view, kind: kind.value, label: label.value, src: { type: sel.type, id: sel.id } });
    if (!(port && port.side === "out")) {
      box.append(el("form", { class: "ag-form dm-form dm-add", "data-new": "0.60.13-flow", onsubmit: (ev) => {
        ev.preventDefault();
        if (!target.value) { DA.toast("Choisissez la cible du flux, ou « Relier en cliquant la cible ».", "error"); return; }
        const [type, id] = target.value.split(":");
        run("/flows", Object.assign(body(), { dst: { type, id: Number(id) } }));
      } }, el("h3", null, "Nouveau flux depuis ce bloc"), field("Vers", target),
      el("div", { class: "dm-row" }, field("Type", kind), field("Libellé", label)),
      el("div", { class: "dm-actions" }, el("button", { type: "submit", class: "btn btn-small btn-primary" }, "Ajouter le flux"),
        el("button", { type: "button", class: "btn btn-small", "data-tip": "Puis cliquez le bloc d'arrivée dans le schéma",
          onclick: () => startLink(body()) }, "Relier en cliquant la cible"))));
    }
    if (port) {
      const plabel = el("input", { type: "text", maxlength: 80, value: port.label });
      const pkind = select(kinds, port.kind);
      box.append(el("form", { class: "ag-form dm-form dm-move", onsubmit: (ev) => {
        ev.preventDefault();
        run("/ports/" + port.id, { label: plabel.value, kind: pkind.value }, "patch");
      } }, el("h3", null, port.side === "in" ? "Cette entrée" : "Cette sortie"), field("Nom", plabel), field("Type de flux", pkind),
      el("div", { class: "dm-actions" }, el("button", { type: "submit", class: "btn btn-small" }, "Enregistrer"),
        el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => {
          if (window.confirm("Effacer « " + port.label + " » et ses " + mine.length + " flux (dans les deux vues) ? L'action est journalisée.")) {
            run("/ports/" + port.id + "/delete", {});
          }
        } }, "Effacer"))));
    }
    return box;
  }

  function flowPanel(state, flow, run, editable) {
    const data = state.data, kinds = data.labels.kinds;
    const box = el("aside", { class: "dm-panel" }, el("div", { class: "dm-panel-head" }, el("strong", null, "Flux"),
      el("span", { class: "dm-key dm-key-" + flow.kind }, kinds[flow.kind])),
    el("p", { class: "dm-reading" }, endName(data, flow, "src") + " → " + endName(data, flow, "dst")));
    if (!editable) return box;
    const kind = select(kinds, flow.kind);
    const label = el("input", { type: "text", maxlength: 60, value: flow.label || "" });
    box.append(el("form", { class: "ag-form dm-form", onsubmit: (ev) => {
      ev.preventDefault();
      run("/flows/" + flow.id, { kind: kind.value, label: label.value }, "patch");
    } }, el("div", { class: "dm-row" }, field("Type", kind), field("Libellé", label)),
    el("div", { class: "dm-actions" }, el("button", { type: "submit", class: "btn btn-small btn-primary" }, "Enregistrer"),
      el("button", { type: "button", class: "btn btn-small btn-danger", onclick: () => run("/flows/" + flow.id + "/delete", {}) }, "Effacer le flux"))));
    return box;
  }

  function panel(state, run, editable, startLink) {
    const sel = state.selected;
    if (!sel) return idle(state, run, editable);
    if (sel.type === "flow") {
      const flow = state.data.flows.find((f) => f.id === sel.id);
      return flow ? flowPanel(state, flow, run, editable) : idle(state, run, editable);
    }
    return nodePanel(state, sel, run, editable, startLink);
  }

  DA.diamond = Object.assign(DA.diamond || {}, { structurePanel: panel });
})();
