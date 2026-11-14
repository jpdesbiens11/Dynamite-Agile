/* Diamond · « PFMEA » (0.60.103, D-O-114), #/diamond/KEY/pfmea/<line>: the Process FMEA of one assembly line, as on page
   13 of the presentation -- Op. (PF-30.1), Process Step, product characteristic C-n, process characteristic, Failure Mode,
   effect, cause and its 5M class, prevention, detection, S inherited from the DFMEA and locked (🔒, its DFMEA line), O, D,
   AP, the action and its follow-up. « Copier le prompt pour l'IA » assembles the final DFMEA extract and the line; the
   answer comes back as drafts, accepted or rejected row by row, never straight into the validated PFMEA. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  async function view(page, ctx) {
    const base = D.base(ctx) + "/pfmea";
    const holder = el("div", { class: "dm-page dm-pf-page" });
    page.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "PFMEA")]), holder);
    let data;
    try { data = await api.get(base); } catch (err) { holder.append(DA.spaces.startHere("PFMEA réservé", err.message, [])); return; }
    const state = { ctx, base, holder, editable: A.canEdit(ctx), data, line: Number(ctx.arg) || null, show: "accepted", open: null };
    state.send = async (method, path, body, done) => {
      try {
        state.data = await api[method](base + path, body || {});
        if (done) toast(typeof done === "function" ? done(state.data) : done, "success");
        draw(state);
        return state.data;
      } catch (err) { toast(err.message, "error"); return null; }
    };
    draw(state);
  }

  function draw(state) {
    const holder = state.holder, d = state.data, ctx = state.ctx;
    clear(holder);
    const line = d.lines.find((l) => l.number === state.line) || d.lines[0];
    holder.append(el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.103-pfmea" }, "PFMEA"),
      el("p", { class: "muted" }, "Process FMEA (AIAG-VDA) de la ligne d'assemblage. Il part de l'extrait final du DFMEA et de la ligne réelle ; "
        + "la sévérité vient du DFMEA et ne peut pas être abaissée (🔒). Les lignes proposées par l'IA arrivent en brouillon.")));
    if (!line) {
      holder.append(DA.spaces.startHere("Décrivez d'abord la ligne", "Le PFMEA suit les opérations de Diamond → Procédés.", [["Ouvrir Procédés", A.href(ctx, "process"), true]]));
      return;
    }
    const rows = d.rows.filter((r) => r.line_number === line.number);
    const n = (st) => rows.filter((r) => r.state === st).length;
    const pick = el("select", { "aria-label": "Configuration de ligne" }, d.lines.map((l) => el("option", { value: l.number, selected: l.number === line.number }, l.code + " · " + l.name)));
    pick.addEventListener("change", () => { location.hash = A.href(ctx, "pfmea") + "/" + pick.value; });
    const tab = (key, label) => el("button", { type: "button", class: "btn btn-small", "aria-pressed": String(state.show === key), onclick: () => { state.show = key; draw(state); } },
      label, el("span", { class: "dm-fm-count" }, String(n(key))));
    holder.append(el("div", { class: "dm-actions" }, pick, tab("accepted", "Validées"), tab("draft", "Brouillons"), tab("rejected", "Rejetées"),
      state.editable ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => state.send("post", "/rows", { operation_id: line.operations[0] ? line.operations[0].id : null },
        "Ligne ajoutée.") }, "Nouvelle ligne") : null,
      state.editable && n("draft") ? el("button", { type: "button", class: "btn btn-small", onclick: () => state.send("post", "/accept-all", {}, (r) => r.accepted + " brouillon(s) acceptés.") },
        "Tout accepter (" + n("draft") + ")") : null,
      ...D.aiTools({ base: state.base, title: "PFMEA · " + line.code, exportHref: state.base + "/export.csv", editable: state.editable, drafts: true,  // 0.60.104 (D-O-116)
        modes: ["generate", "interview", "review"], query: () => "line=" + line.number,
        onDone: (res) => { state.data = res.pfmea; state.show = res.applied.new ? "draft" : state.show; draw(state); } })));
    if (d.checks.length) holder.append(el("details", { class: "dm-advice", open: true }, el("summary", null, "Conseils de la méthode (" + d.checks.length + ")"), el("ul", null, d.checks.map((c) => el("li", null, c)))));
    const shown = rows.filter((r) => r.state === state.show);
    holder.append(shown.length ? table(state, shown, line) : el("p", { class: "muted" }, state.show === "draft" ? "Aucun brouillon à revoir." : "Aucune ligne."));
  }

  function table(state, rows, line) {
    const d = state.data;
    const head = ["Op.", "Process Step", "Product Char.", "Process Char.", "Failure Mode", "Failure Effect", "Cause (5M)", "Prevention", "Detection", "S", "O", "D", "AP", "Action", ""];
    const body = [];
    rows.forEach((r) => {
      body.push(el("tr", { class: "dm-fm-row" + (r.class_code ? " dm-fm-cls-" + r.class_code : "") + (r.state === "draft" ? " dm-pf-draft" : "") },
        el("td", { class: "dm-code nowrap" }, r.code), el("td", null, el("span", { class: "dm-code" }, "OP" + (r.op || "?")), " " + r.process_step),
        el("td", null, r.char_code ? el("span", { class: "dm-cls dm-cls-" + (r.class_code || "none") + (r.class_code ? "" : " dm-cls-none"), "data-tip": r.char_label + " · " + r.char_spec },
          r.class_code === "CC" ? el("span", { class: "dm-cls-mark", "aria-hidden": "true" }, "▼") : null, r.char_code) : "—"),
        el("td", null, r.process_char), el("td", null, r.failure_mode), el("td", null, r.effect),
        el("td", null, r.cause, r.cause_5m ? el("div", { class: "muted dm-pf-5m" }, d.labels.causes[r.cause_5m]) : null),
        el("td", null, r.prevention), el("td", null, r.detection_ctrl),
        el("td", { class: "nowrap" }, el("strong", null, r.s ? String(r.s) : "—"), r.inherited_s ? el("span", { class: "dm-pf-lock", "data-tip": "Héritée du DFMEA, verrouillée" }, " 🔒") : null,
          r.dfmea_line ? el("div", { class: "muted dm-pf-5m" }, "L" + r.dfmea_line) : null),
        el("td", null, r.occurrence || "—"), el("td", null, r.detection || "—"), el("td", null, D.apBadge(r.ap, d.labels.ap)),
        el("td", null, r.action || "—", r.ticket ? el("div", null, el("a", { href: r.ticket.href }, "🎫 " + r.ticket.key)) : null,
          r.action_owner_name ? el("div", { class: "muted dm-pf-5m" }, r.action_owner_name + (r.action_due ? " · " + r.action_due : "")) : null),
        el("td", { class: "nowrap" }, rowTools(state, r))));
      if (state.open === r.id) body.push(el("tr", null, el("td", { colspan: head.length }, D.pfmeaEditor(state, r, line))));
    });
    return el("div", { class: "dm-scroll dm-fm-scroll" }, el("table", { class: "data dm-fm dm-pf" },
      el("thead", null, el("tr", null, head.map((h) => el("th", { scope: "col", class: "dm-fm-h" + (h === "Product Char." ? " dm-fm-h-special" : "") }, h)))), el("tbody", null, body)));
  }

  function rowTools(state, r) {
    if (!state.editable) return null;
    const review = (st, done) => state.send("post", "/rows/" + r.id + "/review", { state: st }, done);
    if (r.state === "draft") {
      return el("div", { class: "dm-actions" }, el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => review("accepted", r.code + " acceptée.") }, "Accepter"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => review("rejected", r.code + " rejetée.") }, "Rejeter"),
        el("button", { type: "button", class: "link-btn", onclick: () => { state.open = state.open === r.id ? null : r.id; draw(state); } }, "modifier"));
    }
    if (r.state === "rejected") return el("button", { type: "button", class: "btn btn-small", onclick: () => review("draft", r.code + " remise en brouillon.") }, "Rétablir");
    return el("div", { class: "dm-actions" }, el("button", { type: "button", class: "link-btn", onclick: () => { state.open = state.open === r.id ? null : r.id; draw(state); } }, "modifier"),
      r.action && !r.ticket ? el("button", { type: "button", class: "link-btn", onclick: () => state.send("post", "/rows/" + r.id + "/track", {}, (x) => "Ticket " + x.tracked + " créé.") },
        "Suivre dans Agile") : null,
      el("button", { type: "button", class: "link-btn", onclick: () => { if (window.confirm("Retirer " + r.code + " du PFMEA ? Elle reste dans « Rejetées ».")) review("rejected", r.code + " retirée."); } }, "retirer"));
  }

  A.views.pfmea = view;
})();
