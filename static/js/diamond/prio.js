/* Diamond · « Prioriser » (0.60.103, D-O-115), #/diamond/KEY/prio: the key rows of the DFMEA and of the PFMEA together, as on
   page 16 of the presentation -- filters (AP High, CC · SC, Cpk under the required one, S ≥ 9, no detection control,
   overdue, mine) and the actions placed in waves tied to the milestones, each with a date. A card is dragged from one wave
   to another (or moved with its list, from the keyboard): its due date and the one of its Agile ticket follow the wave. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;
  const FILTERS = [["ap", "AP High", (r) => r.ap === "H"], ["cls", "CC · SC", (r) => !!r.class_code], ["cpk", "Cpk sous l'exigé", (r) => r.cpk_below],
    ["s9", "S ≥ 9", (r) => (r.s || 0) >= 9], ["nodet", "Sans contrôle de détection", (r) => r.no_detection], ["late", "Échéance dépassée", (r) => r.late],
    ["mine", "Mes actions", (r) => r.mine]];

  async function view(page, ctx) {
    const base = D.base(ctx) + "/prio";
    const holder = el("div", { class: "dm-page dm-pz-page" });
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Prioriser")]), holder);
    const state = { ctx, base, holder, editable: A.canEdit(ctx), data: await api.get(base), on: new Set() };
    state.send = async (method, path, body, done) => {
      try { state.data = await api[method](base + path, body || {}); if (done) toast(done, "success"); draw(state); } catch (err) { toast(err.message, "error"); }
    };
    draw(state);
  }

  function draw(state) {
    const holder = state.holder, d = state.data;
    clear(holder);
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.103-prio" }, "Prioriser"),
      el("p", { class: "muted" }, "On ne peut pas tout faire en même temps : les lignes clés du DFMEA" + (d.pfmea ? " et du PFMEA" : "") + ", puis leurs actions "
        + "rangées en vagues attachées aux jalons du projet. L'échéance d'une action, et celle de son ticket Agile, suivent sa vague.")));
    const rows = d.rows.filter((r) => [...state.on].every((k) => FILTERS.find((f) => f[0] === k)[2](r)));
    holder.append(el("div", { class: "dm-fm-filters", role: "group", "aria-label": "Filtres" }, el("span", { class: "dm-fm-filters-h" }, "Filtres"),
      FILTERS.map(([k, label, test]) => el("button", { type: "button", class: "btn btn-small", "aria-pressed": String(state.on.has(k)),
        onclick: () => { if (state.on.has(k)) state.on.delete(k); else state.on.add(k); draw(state); } }, label, el("span", { class: "dm-fm-count" }, String(d.rows.filter(test).length))))));
    if (!d.waves.length) {
      holder.append(DA.spaces.startHere("Aucune vague", "Trois vagues de départ : avant le prototype, avant la pré-série, avant la production ; datez-les ensuite.",
        state.editable ? [["Créer les vagues de départ", () => state.send("post", "/waves/init", {}, "Vagues créées."), true]] : []));
    }
    const columns = [{ id: null, name: "Sans vague", due_date: "" }].concat(d.waves);
    holder.append(el("div", { class: "dm-pz-board" }, columns.map((w) => column(state, w, rows.filter((r) => (r.wave_id || null) === w.id), columns))));
  }

  function column(state, w, rows, columns) {
    const col = el("section", { class: "dm-pz-col", "aria-label": w.name });
    if (state.editable) {
      col.addEventListener("dragover", (ev) => { ev.preventDefault(); col.classList.add("dm-pz-over"); });
      col.addEventListener("dragleave", () => col.classList.remove("dm-pz-over"));
      col.addEventListener("drop", (ev) => {
        ev.preventDefault();
        col.classList.remove("dm-pz-over");
        const [kind, id] = (ev.dataTransfer.getData("text/plain") || "").split(":");
        if (kind && id) state.send("post", "/move", { kind, id: Number(id), wave_id: w.id }, "Action déplacée dans « " + w.name + " ».");
      });
    }
    const date = w.id && state.editable ? el("input", { type: "date", value: w.due_date || "", "aria-label": "Date de " + w.name }) : null;
    if (date) date.addEventListener("change", () => state.send("patch", "/waves/" + w.id, { due_date: date.value }, "Date de la vague enregistrée : les échéances suivent."));
    col.append(el("h2", null, w.name), w.id ? el("p", { class: "muted dm-pz-date" }, date || (w.due_date || "sans date")) : null,
      rows.length ? rows.map((r) => card(state, r, columns)) : el("p", { class: "muted" }, "—"));
    return col;
  }

  function card(state, r, columns) {
    const box = el("article", { class: "dm-pz-card" + (r.class_code ? " dm-pz-" + r.class_code : ""), draggable: state.editable ? "true" : null },
      el("div", { class: "dm-pz-top" }, el("span", { class: "dm-code" }, (r.kind === "pfmea" ? "PFMEA " : "DFMEA ") + r.code),
        r.class_code ? el("span", { class: "dm-cls dm-cls-" + r.class_code }, r.class_code) : null, D.apBadge(r.ap, { H: "High", M: "Medium", L: "Low" }),
        r.s ? el("span", { class: "muted" }, "S " + r.s) : null, r.cpk_below ? el("span", { class: "dm-ch-miss" }, "Cpk < exigé") : null),
      el("p", { class: "dm-pz-what" }, r.where ? r.where + " — " : "", r.failure_mode),
      el("p", null, r.action ? r.action : el("span", { class: "dm-ch-miss" }, "aucune action")),
      el("p", { class: "muted dm-pz-meta" }, [r.owner, r.due ? (r.late ? "en retard · " : "") + r.due : "", r.ticket ? "🎫 " + r.ticket.key : ""].filter(Boolean).join(" · ")));
    if (state.editable) {
      box.addEventListener("dragstart", (ev) => ev.dataTransfer.setData("text/plain", r.kind + ":" + r.id));
      const move = el("select", { "aria-label": "Vague de " + r.code }, columns.map((w) => el("option", { value: w.id || "", selected: (r.wave_id || null) === w.id }, w.name)));
      move.addEventListener("change", () => state.send("post", "/move", { kind: r.kind, id: r.id, wave_id: move.value ? Number(move.value) : null }, "Action déplacée."));
      box.append(move);
    }
    return box;
  }

  A.views.prio = view;
})();
