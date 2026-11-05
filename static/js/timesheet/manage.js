/* Timesheet - administrator screens (D-B-023): approval of submitted weeks,
   Excel export per funding organism, projects <-> organisms. Loaded before
   timesheet.js, which routes to these views. */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field } = DA;
  const TS = (DA.timesheet = DA.timesheet || {});
  const fmtH = (h) => (TS.hours ? TS.hours(h) : h + " h");
  const iso = (d) => d.toISOString().slice(0, 10);

  /* ---------- Absences (D-B-031): bank and leave of a week ---------- */
  TS.leaveBanner = function (leave, forApprover) {
    if (!leave) return null;
    const parts = [];
    if (leave.remaining == null) {
      parts.push(forApprover ? "Banque de vacances non renseignée." : "Banque de vacances non renseignée : indiquez-la dans menu à votre nom → Paramètres.");
    } else {
      parts.push(el("strong", null, "Banque de vacances : " + fmtH(leave.remaining) + " restantes"),
        " (" + fmtH(leave.bank) + " au " + leave.since + ", " + fmtH(leave.used) + " prises depuis)");
    }
    if (leave.vacation_week) parts.push(" · Vacances cette semaine : " + fmtH(leave.vacation_week) + " (déduites)");
    if (leave.health_week) parts.push(" · ", el("strong", null, "Congé santé : " + fmtH(leave.health_week)), " (sous approbation, non déduit de la banque)");
    if (!forApprover) {
      parts.push(" · Approbateur : " + (leave.manager ? leave.manager.display_name : "aucun — choisissez-le dans menu à votre nom → Paramètres"));
    }
    const tone = leave.overdrawn ? " tt-banner-warn" : leave.health_week ? " tt-banner-health" : "";
    return el("div", { class: "tt-banner tt-leave" + tone }, parts,
      leave.overdrawn ? el("div", null, el("strong", null, "Banque dépassée de " + fmtH(-leave.remaining) + ".")) : null,
      forApprover ? null : el("div", { class: "muted tt-small" }, "Dans chaque Space : INT-VAC · Vacances (déduites de la banque), "
        + "INT-SAN · Congé santé (sous approbation, jamais déduit) — ni l'un ni l'autre n'est réclamé à un organisme."),
      forApprover ? null : el("a", { href: "#/settings", class: "tt-small" }, "Modifier ma banque ou mon approbateur"));
  };

  /* ---------- Approval ---------- */
  TS.approvalView = async function (page, reload) {
    const filter = el("select", { "aria-label": "Status" },
      [["submitted", "À approuver (soumises)"], ["returned", "Renvoyées"], ["approved", "Approuvées"], ["all", "Toutes"]]
        .map(([v, l]) => el("option", { value: v }, l)));
    const holder = el("div", { class: "tt-approvals" });
    page.append(el("div", { class: "page-head" }, el("h1", null, "Approbation des feuilles de temps"),
      el("p", { class: "muted" }, "Vérifiez les plages, leurs descriptions et les absences (banque de vacances, congé santé), "
        + "puis approuvez ou renvoyez avec une note. Vous voyez les personnes qui vous ont choisi comme gestionnaire.")),
    el("div", { class: "tt-toolbar" }, filter), holder);

    async function draw() {
      clear(holder);
      let data;
      try { data = await api.get("/api/timesheet/approvals?status=" + filter.value); }
      catch (err) { holder.append(el("div", { class: "empty" }, el("p", null, err.message))); return; }
      if (!data.weeks.length) { holder.append(el("div", { class: "empty" }, el("p", null, "Aucune feuille dans cet état."))); return; }
      data.weeks.forEach((w) => holder.append(weekCard(w, draw)));
    }
    filter.addEventListener("change", draw);
    await draw();
  };

  function weekCard(w, redraw) {
    const byProject = {};
    w.entries.forEach((e) => { byProject[e.project_key] = (byProject[e.project_key] || 0) + e.hours; });
    async function decide(action, note) {
      try {
        await api.post("/api/timesheet/weeks/" + w.id + "/decision", { action, note: note || "" });
        toast({ approve: "Feuille approuvée.", return: "Feuille renvoyée.", reopen: "Feuille rouverte." }[action], "success");
        redraw();
      } catch (err) { toast(err.message, "error"); }
    }
    function returnDialog() {
      const note = el("textarea", { rows: 3, maxlength: 500, required: true, placeholder: "Ce qu'il faut corriger…" });
      let close = null;
      const form = el("form", { class: "form", onsubmit: (ev) => { ev.preventDefault(); close(); decide("return", note.value); } },
        field("Note pour " + w.display_name, note),
        el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
          el("button", { type: "submit", class: "btn btn-danger" }, "Renvoyer")));
      close = modal("Renvoyer la semaine du " + w.week_start, form);
    }
    return el("article", { class: "tt-card tt-card-" + w.status },
      el("div", { class: "tt-card-head" },
        el("strong", null, w.display_name), el("span", { class: "muted" }, "Semaine du " + w.week_start),
        el("span", { class: "badge tt-status tt-status-" + w.status }, w.status_label),
        el("span", { class: "tt-card-total" }, fmtH(w.total)),
        el("span", { class: "muted tt-small" }, Object.entries(byProject).map(([k, h]) => k + " " + fmtH(h)).join(" · ")),
        el("span", { class: "tt-spacer" }),
        w.status === "submitted" ? el("button", { type: "button", class: "btn btn-primary btn-small", onclick: () => decide("approve") }, "Approuver") : null,
        ["submitted", "approved"].includes(w.status) ? el("button", { type: "button", class: "btn btn-small", onclick: returnDialog }, "Renvoyer…") : null,
        w.status === "approved" ? el("button", { type: "button", class: "btn btn-small", onclick: () => decide("reopen") }, "Rouvrir") : null),
      w.note ? el("p", { class: "tt-small muted" }, "Note : " + w.note) : null,
      TS.leaveBanner(w.leave, true),
      DA.table(["Jour", "Space", "Budget Line", "Heures", "Description"], w.entries.map((e) => el("tr", null,
        el("td", null, e.day_label), el("td", null, e.project_key), el("td", null, e.task_label),
        el("td", { class: "tt-num" }, fmtH(e.hours)),
        el("td", { class: e.description.trim() ? null : "tt-hint-bad" }, e.description || "(vide)")))));
  }

  /* ---------- Excel export ---------- */
  TS.exportView = async function (page) {
    const data = await api.get("/api/timesheet/projects");
    const today = new Date();
    const from = el("input", { type: "date", value: iso(new Date(Date.UTC(today.getFullYear(), today.getMonth(), 1))) });
    const to = el("input", { type: "date", value: iso(today) });
    const organism = el("select", null, el("option", { value: "" }, "Tous les organismes"),
      data.organisms.map((o) => el("option", { value: o }, o)));
    const status = el("select", null, [["approved", "Approuvées seulement"], ["submitted", "Soumises et approuvées"],
      ["all", "Toutes (brouillons compris)"]].map(([v, l]) => el("option", { value: v }, l)));
    const link = el("a", { class: "btn btn-primary", download: "" }, "Télécharger le fichier Excel");
    const picker = TS.budgetPicker(data, () => update());
    const update = () => {
      const sel = picker.selection();
      link.classList.toggle("tt-disabled", !sel.ok);
      link.setAttribute("aria-disabled", sel.ok ? "false" : "true");
      link.setAttribute("href", "/api/timesheet/export.xlsx?from=" + from.value + "&to=" + to.value
        + "&organism=" + encodeURIComponent(organism.value) + "&status=" + status.value
        + (sel.tasks ? "&tasks=" + encodeURIComponent(sel.tasks) : "") + (sel.projects ? "&projects=" + encodeURIComponent(sel.projects) : ""));
    };
    link.addEventListener("click", (ev) => { if (!picker.selection().ok) { ev.preventDefault(); toast("Cochez au moins une Budget Line et un Space.", "error"); } });
    [from, to, organism, status].forEach((c) => c.addEventListener("change", update));
    /* D-A-042: Word report in the Word template of the tool, same selection, addressed to an organism or a client */
    const report = TS.reportForm(() => {
      const sel = picker.selection();
      return sel.ok ? "/api/timesheet/report.docx?from=" + from.value + "&to=" + to.value + "&organism=" + encodeURIComponent(organism.value)
        + "&status=" + status.value + (sel.tasks ? "&tasks=" + encodeURIComponent(sel.tasks) : "")
        + (sel.projects ? "&projects=" + encodeURIComponent(sel.projects) : "") : null;
    });
    function preset(kind) {
      const y = today.getFullYear(), m = today.getMonth();
      const ranges = {
        month: [new Date(Date.UTC(y, m, 1)), today],
        last: [new Date(Date.UTC(y, m - 1, 1)), new Date(Date.UTC(y, m, 0))],
        quarter: [new Date(Date.UTC(y, Math.floor(m / 3) * 3, 1)), today],
        year: [new Date(Date.UTC(y, 0, 1)), today],
      };
      from.value = iso(ranges[kind][0]); to.value = iso(ranges[kind][1]); update();
    }
    update();
    page.append(el("div", { class: "page-head" }, el("h1", null, "Export Excel et rapport Word des heures"),
      el("p", { class: "muted" }, "Pour les réclamations aux organismes qui financent un projet (subvention, crédit d'impôt, client) : feuille « Sommaire » "
        + "(organisme › Space › employé › task, sous-totaux), « Budget Lines » (heures par Budget Line cochée, puis chaque plage avec sa justification), « Détail » (chaque plage avec sa description) et « Lisez-moi ».")),
    el("div", { class: "tt-presets" }, ["Mois courant", "Mois précédent", "Trimestre", "Année"].map((l, i) =>
      el("button", { type: "button", class: "btn btn-small", onclick: () => preset(["month", "last", "quarter", "year"][i]) }, l))),
    el("div", { class: "tt-export-form" }, field("Du", from), field("Au", to), field("Organisme", organism), field("Semaines", status)),
    picker.node,
    el("div", { class: "form-actions tt-left" }, link), report,
    data.organisms.length ? "" : el("p", { class: "muted" }, "Aucun organisme défini : associez-les aux Spaces dans « Spaces et organismes »."));
  };

  /* ---------- Word report (D-A-042): recipient entered at creation ---------- */
  TS.reportForm = function (baseUrl) {
    const kind = el("select", { "aria-label": "Type de destinataire" }, [["grant", "Organisme de subvention"], ["client", "Client"],
      ["other", "Autre destinataire"]].map(([v, l]) => el("option", { value: v }, l)));
    const input = (ph, max) => el("input", { type: "text", maxlength: max || 160, placeholder: ph });
    const recipient = input("ex. Programme de subvention, nom du client");
    const ref = input("ex. no de programme, de contrat ou de bon de commande");
    const contact = input("ex. nom et courriel du répondant");
    const title = input("par défaut : Timesheet Report — destinataire");
    const docno = input("ex. TS-2026-001", 40);
    const lang = el("select", { "aria-label": "Langue du rapport" }, [["fr", "Français (termes techniques en anglais)"], ["en", "English"]]
      .map(([v, l]) => el("option", { value: v }, l)));
    const button = el("a", { class: "btn btn-primary", download: "" }, "Générer le rapport Word");
    button.addEventListener("click", (ev) => {
      const url = baseUrl();
      if (!url) { ev.preventDefault(); toast("Cochez au moins une Budget Line et un Space.", "error"); return; }
      if (!recipient.value.trim()) { ev.preventDefault(); recipient.focus();
        toast("Destinataire obligatoire : entrez l'organisme de subvention ou le client.", "error"); return; }
      button.setAttribute("href", url + "&recipient_type=" + kind.value + "&recipient=" + encodeURIComponent(recipient.value.trim())
        + "&recipient_ref=" + encodeURIComponent(ref.value.trim()) + "&recipient_contact=" + encodeURIComponent(contact.value.trim())
        + (title.value.trim() ? "&title=" + encodeURIComponent(title.value.trim()) : "")
        + (docno.value.trim() ? "&docno=" + encodeURIComponent(docno.value.trim()) : "") + "&lang=" + lang.value);
    });
    return el("section", { class: "tt-report" }, el("h2", null, "Rapport Word"),
      el("p", { class: "muted" }, "Un extrait des heures des Budget Lines cochées ci-dessus, au gabarit Word de l'outil (le même que Goldmine et Testing) : "
        + "destinataire et périmètre, sommaire par Budget Line, heures par employé, détail des justifications, attestation, "
        + "Definitions et Acronyms. Le destinataire personnalise la page de titre et le texte."),
      el("div", { class: "tt-export-form" }, field("Type de destinataire", kind), field("Destinataire", recipient),
        field("Référence", ref), field("Contact", contact)),
      el("div", { class: "tt-export-form" }, field("Titre du rapport", title), field("No de document", docno), field("Langue", lang)),
      el("div", { class: "form-actions tt-left" }, button));
  };

  /* ---------- Budget lines of a claim (D-B-036): « x » on task codes and projects ---------- */
  TS.budgetPicker = function (data, onChange) {
    const taskBoxes = [];
    const groups = Object.entries(data.meta.task_sets).map(([setKey, set]) => {
      const boxes = set.tasks.map((t) => {
        /* D-B-084: « réclamable » lines are checked by default; a deactivated line stays claimable for its past hours */
        const box = el("input", { type: "checkbox", value: t.key, checked: t.claimable !== false && t.active !== false });
        box.dataset.set = setKey;
        box.dataset.claimable = t.claimable !== false ? "1" : "";
        box.addEventListener("change", () => { sync(); onChange(); });
        taskBoxes.push(box);
        return el("label", { class: "tt-x" + (t.active === false ? " tt-x-off" : ""), title: t.label }, box, el("span", { class: "tt-x-code" }, t.key),
          el("span", { class: "tt-x-label" }, t.label + (t.claimable === false ? " (non réclamable)" : "") + (t.active === false ? " (inactif)" : "")));
      });
      const all = el("input", { type: "checkbox", "aria-label": "Tout " + set.label });
      all.addEventListener("change", () => { boxes.forEach((b) => { b.querySelector("input").checked = all.checked; }); onChange(); });
      return { all, boxes, node: el("fieldset", { class: "tt-x-group" },
        el("legend", null, el("label", { class: "tt-x-all" }, all, set.label)), el("div", { class: "tt-x-grid" }, boxes)) };
    });
    function sync() {
      groups.forEach((g) => {
        const n = g.boxes.filter((b) => b.querySelector("input").checked).length;
        g.all.checked = n === g.boxes.length;
        g.all.indeterminate = n > 0 && n < g.boxes.length;
      });
      count.textContent = taskBoxes.filter((b) => b.checked).length + " Budget Line(s) cochée(s)";
    }
    const projectBoxes = data.projects.filter((p) => !p.is_archived).map((p) => {
      const box = el("input", { type: "checkbox", value: p.key, checked: true });
      box.addEventListener("change", onChange);
      return { box, node: el("label", { class: "tt-x tt-x-proj", title: p.name }, box, el("span", { class: "tt-x-code" }, p.key),
        el("span", { class: "tt-x-label" }, p.name + (p.organism ? " · " + p.organism : ""))) };
    });
    const count = el("span", { class: "muted" });
    const presets = [["Réclamables", (b) => !!b.dataset.claimable], ["Toutes les Budget Lines", () => true], ["Aucun", () => false]]
      .concat(Object.entries(data.meta.task_sets).map(([k, set]) => [set.label + " seulement", (b) => b.dataset.set === k && !!b.dataset.claimable]))
      .map(([label, fn]) => el("button", { type: "button", class: "btn btn-small", onclick: () => {
        taskBoxes.forEach((b) => { b.checked = fn(b); }); sync(); onChange();
      } }, label));
    sync();
    const node = el("div", { class: "tt-budget" },
      el("h2", null, "Budget Lines à réclamer"),
      el("p", { class: "muted" }, "Cochez (« x ») une Budget Line précise ou une combinaison ; seules leurs heures, avec leur justification, "
        + "sont exportées. Seules les Budget Lines « réclamables » sont cochées par défaut (les vacances et congés santé ne le sont pas) ; "
        + "les Funding Spaces et leurs Budget Lines se gèrent dans « Spaces et organismes »."),
      el("div", { class: "tt-presets" }, presets, count), groups.map((g) => g.node),
      el("fieldset", { class: "tt-x-group" }, el("legend", null, "Spaces"), el("div", { class: "tt-x-grid" }, projectBoxes.map((p) => p.node))));
    return {
      node,
      selection() {
        const tasks = taskBoxes.filter((b) => b.checked).map((b) => b.value);
        const projects = projectBoxes.filter((p) => p.box.checked).map((p) => p.box.value);
        return { ok: tasks.length > 0 && projects.length > 0,
          tasks: tasks.length === taskBoxes.length ? "" : tasks.join(","),
          projects: projects.length === projectBoxes.length ? "" : projects.join(",") };
      },
    };
  };

  /* ---------- Projects and organisms ---------- */
  TS.projectsView = async function (page, reload) {
    const data = await api.get("/api/timesheet/projects");
    const list = el("datalist", { id: "tt-organisms" }, data.organisms.map((o) => el("option", { value: o })));
    const rows = data.projects.map((p) => {
      const save = async (changes) => {
        try { await api.put("/api/timesheet/projects/" + p.id, changes); toast(p.key + " enregistré.", "success"); }
        catch (err) { toast(err.message, "error"); reload(); }
      };
      const org = el("input", { type: "text", value: p.organism || null, list: "tt-organisms", maxlength: 80,
        placeholder: "Ex. CNRC-PARI, RS&DE, client…", "aria-label": "Organisme de " + p.key });
      const contract = el("input", { type: "text", value: p.contract_ref || null, maxlength: 80, "aria-label": "Contrat de " + p.key });
      const set = el("select", { "aria-label": "Funding Space de " + p.key }, Object.entries(data.meta.task_sets)
        .filter(([k, v]) => v.active !== false || k === p.task_set).map(([k, v]) =>
          el("option", { value: k, selected: k === p.task_set }, v.label + (v.active === false ? " (désactivé)" : ""))));
      const open = el("input", { type: "checkbox", checked: !!p.open_to_all, "aria-label": "Ouvert à tous" });
      const on = el("input", { type: "checkbox", checked: !!p.enabled, "aria-label": "Actif" });
      org.addEventListener("change", () => save({ organism: org.value }));
      contract.addEventListener("change", () => save({ contract_ref: contract.value }));
      set.addEventListener("change", () => save({ task_set: set.value }));
      open.addEventListener("change", () => save({ open_to_all: open.checked }));
      on.addEventListener("change", () => save({ enabled: on.checked }));
      return el("tr", { class: p.is_archived ? "tt-archived" : null },
        el("td", null, el("strong", null, p.key), el("div", { class: "muted tt-small" }, p.name + (p.is_archived ? " (archivé)" : ""))),
        el("td", null, org), el("td", null, contract), el("td", null, set),
        el("td", { class: "tt-center" }, open), el("td", { class: "tt-center" }, on), el("td", { class: "tt-num" }, fmtH(p.hours)));
    });
    page.append(el("div", { class: "page-head" }, el("h1", null, "Spaces et organismes"),
      el("p", { class: "muted" }, "Chaque Space est rattaché à un organisme financeur, à un numéro de contrat et à un espace "
        + "financier (Funding Space : ses Budget Lines), repris dans l'export Excel et le rapport Word. « Ouvert à tous » : tout "
        + "le monde y saisit des heures sans être membre. Enregistrement automatique à chaque modification.")),
    list, DA.table(["Space", "Organisme", "No de contrat", "Funding Space", "Ouvert à tous", "Actif", "Heures saisies"], rows));
    if (TS.budgetAdmin) await TS.budgetAdmin(page, reload);
  };
})();
