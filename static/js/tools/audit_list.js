/* « Liste Audit » (D-B-025): the button left of « Audit » in the top bar
   (with the number of open observations) and the #/audit screen where the
   observations are sorted, filtered and planned into the next revisions.
   - Liste : filters (text, status, type, priority, tool, revision, owner),
     sort, bulk planning for administrators, CSV export;
   - Plan de révisions : one column per target revision, « Non planifié » first;
   - detail of an observation (#/audit/<id>) : capture, description, planning.
   Everyone reads; administrators plan (status, type, priority, revision,
   owner, answer). Loaded before audit.js (the capture dialog). */
(function () {
  "use strict";

  const { api, el, clear, toast, modal, field, formatDate } = DA;
  const OPEN = ["new", "planned", "doing"];
  const PRIO = { high: 0, normal: 1, low: 2 };
  const STATUS_ORDER = { doing: 0, planned: 1, new: 2, done: 3, rejected: 4 };
  const NONE = "__none__";
  const AU = (DA.audit = DA.audit || {});
  let countCache = { at: 0, open: null };

  /* ---------- Top-bar button with the open count ---------- */
  AU.refreshCount = async function (force) {
    if (force !== false || Date.now() - countCache.at > 30000) {
      try { countCache = { at: Date.now(), open: (await api.get("/api/ui-audit/count")).open }; } catch (err) { return; }
    }
    document.querySelectorAll(".tb-audit-count").forEach((b) => {
      b.textContent = countCache.open ? String(countCache.open) : "";
      b.hidden = !countCache.open;
    });
  };

  function listButton(active) {
    const badge = el("span", { class: "tb-audit-count", "aria-label": "observations ouvertes", hidden: true });
    setTimeout(() => AU.refreshCount(false), 0);
    return el("a", { class: "tb-audit-list" + (active === "audit" ? " active" : ""), href: "#/audit",
      title: "Voir et planifier les observations Audit" }, "Liste Audit", badge);
  }

  /* ---------- Helpers ---------- */
  const firstLine = (text) => String(text || "").split(/\n/)[0].slice(0, 140);
  const thumb = (item, cls) => (item.has_image
    ? el("img", { src: "/api/ui-audit/" + item.id + "/image", alt: "", class: cls, loading: "lazy" })
    : el("span", { class: cls + " au-noshot muted" }, "—"));
  const statusBadge = (i) => el("span", { class: "badge au-status au-status-" + i.status }, i.status_label);

  async function patch(ids, changes) {
    if (ids.length === 1) return [(await api.patch("/api/ui-audit/" + ids[0], changes)).item];
    return (await api.post("/api/ui-audit/bulk", { ids, changes })).items;
  }

  /* ---------- Detail ---------- */
  function detail(item, m, after) {
    const releaseList = el("datalist", { id: "au-releases-d" }, m.releases.map((r) => el("option", { value: r })));
    const body = el("div", { class: "au-detail" },
      item.has_image ? el("a", { href: "/api/ui-audit/" + item.id + "/image", target: "_blank", rel: "noopener",
        title: "Ouvrir la capture en grand" }, thumb(item, "au-detail-shot")) : el("p", { class: "muted" }, "Sans capture."),
      el("div", { class: "au-meta" }, el("span", { class: "badge au-kind-" + item.kind }, item.kind_label),
        el("span", { class: "badge au-prio-" + item.priority }, item.priority_label), statusBadge(item),
        el("span", { class: "muted" }, "Par " + (item.created_by_name || "—") + " · " + formatDate(item.created_at))),
      el("p", { class: "au-desc" }, item.description),
      el("p", { class: "muted au-where" }, "Outil : " + (item.module || "—") + " · Page : ",
        /^#\//.test(item.page_url) ? el("a", { href: item.page_url }, item.page_url) : "adresse inconnue"));
    let close = null;
    if (m.can_manage) {
      const sel = (name, options, value) => el("select", { "aria-label": name }, options.map(([k, v]) => el("option", { value: k, selected: k === value }, v)));
      const status = sel("Status", Object.entries(m.statuses), item.status);
      const kind = sel("Type", Object.entries(m.kinds), item.kind);
      const prio = sel("Priority", Object.entries(m.priorities), item.priority);
      const owner = sel("Assignee", [["", "— personne —"]].concat(m.users.map((u) => [String(u.id), u.display_name])),
        item.assignee_id ? String(item.assignee_id) : "");
      const release = el("input", { type: "text", maxlength: 30, list: "au-releases-d", value: item.target_release || null, placeholder: "ex. 0.15.0" });
      const note = el("textarea", { rows: 3, maxlength: 2000, placeholder: "Réponse / suivi (visible par tous)" });
      note.value = item.admin_note || "";
      body.append(releaseList, el("div", { class: "au-plan-form" }, field("Status", status), field("Type", kind), field("Priority", prio),
        field("Revision cible", release, "Donner une révision passe l'observation à « Planifié »."), field("Assignee", owner)),
      field("Réponse / suivi", note),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Fermer"),
        el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
          try {
            await patch([item.id], { status: status.value, kind: kind.value, priority: prio.value, target_release: release.value.trim(),
              assignee_id: owner.value ? Number(owner.value) : null, admin_note: note.value });
            close(); toast("Observation #" + item.id + " enregistrée.", "success"); AU.refreshCount(); after();
          } catch (err) { toast(err.message, "error"); }
        } }, "Enregistrer")));
    } else {
      body.append(el("p", null, el("strong", null, "Revision cible : "), item.target_release || "non planifiée", " · ",
        el("strong", null, "Assignee : "), item.assignee_name || "—"),
      item.admin_note ? el("p", { class: "au-answer" }, "Suivi : " + item.admin_note) : null);
    }
    close = modal("Observation #" + item.id, body);
    const dialog = body.closest(".modal");
    if (dialog) dialog.classList.add("au-modal");
  }

  /* ---------- Screen ---------- */
  async function render(main, parts) {
    const view = parts[0] === "plan" ? "plan" : "liste";
    const openId = /^\d+$/.test(parts[0] || "") ? Number(parts[0]) : null;
    const head = el("div", { class: "page-head au-head" },
      el("div", null, el("h1", null, "Audit de l'interface"),
        el("p", { class: "muted" }, "Observations sur les écrans de la plateforme, à planifier dans les prochaines révisions.")),
      el("div", { class: "au-head-actions" },
        el("a", { class: "btn", href: "/api/ui-audit/export.csv", download: "" }, "Exporter CSV"),
        el("button", { type: "button", class: "btn btn-primary", onclick: () => AU.start && AU.start() }, "+ Nouvelle observation")));
    const holder = el("div");
    main.append(head, holder);
    let m;
    try { m = await api.get("/api/ui-audit"); } catch (err) { holder.append(el("div", { class: "empty" }, el("p", null, err.message))); return; }
    const reload = () => { clear(main); render(main, parts); };

    const counts = {};
    m.items.forEach((i) => { counts[i.status] = (counts[i.status] || 0) + 1; });
    const state = { q: "", status: "open", kind: "", priority: "", module: "", release: "", owner: "", sort: "status" };
    const chips = el("div", { class: "au-chips" }, Object.entries(m.statuses).map(([k, v]) =>
      el("button", { type: "button", class: "au-chip au-status-" + k, onclick: () => { state.status = k; statusSel.value = k; draw(); } },
        v + " ", el("strong", null, String(counts[k] || 0)))));
    const tabs = el("nav", { class: "subtabs au-tabs", "aria-label": "Vues Audit" },
      el("a", { class: "subtab" + (view === "liste" ? " active" : ""), href: "#/audit" }, "Liste"),
      el("a", { class: "subtab" + (view === "plan" ? " active" : ""), href: "#/audit/plan" }, "Plan de révisions"));

    const opt = (pairs) => pairs.map(([k, v]) => el("option", { value: k }, v));
    const search = el("input", { type: "search", placeholder: "Chercher (description, page, suivi…)", class: "au-search", "aria-label": "Chercher" });
    const statusSel = el("select", { "aria-label": "Status" }, opt([["open", "Ouvertes"], ["", "All Statuses"]].concat(Object.entries(m.statuses))));
    const kindSel = el("select", { "aria-label": "Type" }, opt([["", "Tous les types"]].concat(Object.entries(m.kinds))));
    const prioSel = el("select", { "aria-label": "Priority" }, opt([["", "All Priorities"]].concat(Object.entries(m.priorities))));
    const modules = Array.from(new Set(m.items.map((i) => i.module).filter(Boolean))).sort();
    const modSel = el("select", { "aria-label": "Outil" }, opt([["", "Tous les outils"]].concat(modules.map((x) => [x, x]))));
    const relSel = el("select", { "aria-label": "Revision" }, opt([["", "Toutes révisions"], [NONE, "Non planifiées"]].concat(m.releases.map((r) => [r, r]))));
    const ownerSel = el("select", { "aria-label": "Assignee" }, opt([["", "All Assignees"], [NONE, "No Assignee"]].concat(m.users.map((u) => [String(u.id), u.display_name]))));
    const sortSel = el("select", { "aria-label": "Trier" }, opt([["status", "Tri : status puis priority"], ["priority", "Tri : priority"], ["recent", "Tri : plus récentes"], ["release", "Tri : révision"]]));
    const bind = (ctl, key) => ctl.addEventListener(ctl.tagName === "INPUT" ? "input" : "change", () => { state[key] = ctl.value; draw(); });
    [[search, "q"], [statusSel, "status"], [kindSel, "kind"], [prioSel, "priority"], [modSel, "module"], [relSel, "release"], [ownerSel, "owner"], [sortSel, "sort"]].forEach(([c, k]) => bind(c, k));
    const filters = el("div", { class: "au-filters" }, search, statusSel, kindSel, prioSel, modSel, relSel, ownerSel, view === "liste" ? sortSel : null);
    const bulk = el("div", { class: "au-bulk", hidden: true });
    const content = el("div");
    holder.append(chips, tabs, filters, bulk, content);

    function visible() {
      const q = state.q.trim().toLowerCase();
      const items = m.items.filter((i) => (!state.status || (state.status === "open" ? OPEN.includes(i.status) : i.status === state.status))
        && (!state.kind || i.kind === state.kind) && (!state.priority || i.priority === state.priority)
        && (!state.module || i.module === state.module)
        && (!state.release || (state.release === NONE ? !i.target_release : i.target_release === state.release))
        && (!state.owner || (state.owner === NONE ? !i.assignee_id : String(i.assignee_id) === state.owner))
        && (!q || [i.description, i.page_url, i.admin_note, i.module, i.created_by_name, "#" + i.id].join(" ").toLowerCase().includes(q)));
      const by = {
        status: (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || PRIO[a.priority] - PRIO[b.priority] || b.id - a.id,
        priority: (a, b) => PRIO[a.priority] - PRIO[b.priority] || b.id - a.id,
        recent: (a, b) => b.id - a.id,
        release: (a, b) => (a.target_release || "~").localeCompare(b.target_release || "~", "fr", { numeric: true }) || PRIO[a.priority] - PRIO[b.priority],
      };
      return items.sort(by[state.sort] || by.status);
    }

    const selected = new Set();
    function drawBulk() {
      clear(bulk);
      bulk.hidden = !m.can_manage || !selected.size;
      if (bulk.hidden) return;
      const rel = el("input", { type: "text", maxlength: 30, list: "au-releases", placeholder: "ex. 0.15.0", "aria-label": "Revision cible" });
      const st = el("select", { "aria-label": "Status" }, opt([["", "Status…"]].concat(Object.entries(m.statuses))));
      const who = el("select", { "aria-label": "Assignee" }, opt([["", "Assignee…"], [NONE, "— personne —"]].concat(m.users.map((u) => [String(u.id), u.display_name]))));
      const apply = async (changes) => {
        try { await patch(Array.from(selected), changes); toast(selected.size + " observation(s) mise(s) à jour.", "success"); AU.refreshCount(); reload(); }
        catch (err) { toast(err.message, "error"); }
      };
      bulk.append(el("strong", null, selected.size + " sélectionnée(s)"),
        el("datalist", { id: "au-releases" }, m.releases.map((r) => el("option", { value: r }))),
        rel, el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => apply({ target_release: rel.value.trim() }) }, "Planifier dans cette révision"),
        st, el("button", { type: "button", class: "btn btn-small", onclick: () => st.value && apply({ status: st.value }) }, "Changer le status"),
        who, el("button", { type: "button", class: "btn btn-small", onclick: () => who.value && apply({ assignee_id: who.value === NONE ? null : Number(who.value) }) }, "Attribuer"),
        el("button", { type: "button", class: "btn btn-small", onclick: () => { selected.clear(); draw(); } }, "Désélectionner"));
    }

    function listView(items) {
      const all = el("input", { type: "checkbox", "aria-label": "Tout sélectionner", checked: items.length > 0 && items.every((i) => selected.has(i.id)) });
      all.addEventListener("change", () => { items.forEach((i) => (all.checked ? selected.add(i.id) : selected.delete(i.id))); draw(); });
      const rows = items.map((i) => {
        const box = el("input", { type: "checkbox", "aria-label": "Sélectionner #" + i.id, checked: selected.has(i.id) });
        box.addEventListener("click", (ev) => ev.stopPropagation());
        box.addEventListener("change", () => { if (box.checked) selected.add(i.id); else selected.delete(i.id); drawBulk(); });
        return el("tr", { class: "au-line au-line-" + i.status, tabindex: "0", onclick: () => detail(i, m, reload),
          onkeydown: (ev) => { if (ev.key === "Enter") detail(i, m, reload); } },
        m.can_manage ? el("td", null, box) : null,
        el("td", { class: "au-id" }, "#" + i.id), el("td", null, thumb(i, "au-mini")),
        el("td", { class: "au-desc-cell" }, el("strong", null, firstLine(i.description)),
          el("div", { class: "muted au-small" }, (i.module || "—") + " · " + (i.page_url || "")),
          i.admin_note ? el("div", { class: "au-small au-note-line" }, "Suivi : " + firstLine(i.admin_note)) : null),
        el("td", null, el("span", { class: "badge au-kind-" + i.kind }, i.kind_label)),
        el("td", null, el("span", { class: "badge au-prio-" + i.priority }, i.priority_label)),
        el("td", null, statusBadge(i)),
        el("td", { class: "au-rel" }, i.target_release || el("span", { class: "muted" }, "—")),
        el("td", null, i.assignee_name || el("span", { class: "muted" }, "—")),
        el("td", { class: "au-small" }, (i.created_by_name || "—"), el("br"), formatDate(i.created_at)));
      });
      return DA.table([m.can_manage ? all : null, "#", "Capture", "Observation", "Type", "Priority", "Status", "Revision", "Assignee", "Auteur"].filter((h) => h !== null),
        rows);
    }

    function planView(items) {
      const groups = [[NONE, "Non planifié"]].concat(m.releases.map((r) => [r, "Revision " + r]));
      return el("div", { class: "au-board" }, groups.map(([key, label]) => {
        const col = items.filter((i) => (key === NONE ? !i.target_release : i.target_release === key))
          .sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || PRIO[a.priority] - PRIO[b.priority]);
        const all = m.items.filter((i) => (key === NONE ? !i.target_release : i.target_release === key));
        const doneCount = all.filter((i) => i.status === "done" || i.status === "rejected").length;
        return el("section", { class: "au-col" },
          el("div", { class: "au-col-head" }, el("strong", null, label), el("span", { class: "muted" }, key === NONE ? col.length + " à planifier"
            : doneCount + " / " + all.length + " terminées")),
          col.length ? col.map((i) => el("button", { type: "button", class: "au-tile au-tile-" + i.status, onclick: () => detail(i, m, reload) },
            el("span", { class: "au-tile-top" }, el("span", null, "#" + i.id), el("span", { class: "badge au-prio-" + i.priority }, i.priority_label), statusBadge(i)),
            el("span", { class: "au-tile-text" }, firstLine(i.description)),
            el("span", { class: "muted au-small" }, (i.module || "—") + (i.assignee_name ? " · " + i.assignee_name : ""))))
            : el("p", { class: "muted au-small" }, "Rien ici avec ces filtres."));
      }));
    }

    function draw() {
      clear(content);
      const items = visible();
      if (!m.items.length) {
        content.append(el("div", { class: "empty" }, el("p", null, "Aucune observation pour l'instant. Sur n'importe quel écran, cliquez « Audit »."))); drawBulk(); return;
      }
      content.append(view === "plan" ? planView(items) : (items.length ? listView(items)
        : el("div", { class: "empty" }, el("p", null, "Aucune observation avec ces filtres."))));
      if (!m.can_manage && view === "plan") content.prepend(el("p", { class: "muted" }, "Les administrateurs planifient les révisions ; cliquez une observation pour la lire."));
      drawBulk();
    }
    draw();
    if (openId) {
      const item = m.items.find((i) => i.id === openId);
      if (item) detail(item, m, reload); else toast("Observation #" + openId + " introuvable.", "error");
    }
  }

  DA.topbarTools = DA.topbarTools || [];
  listButton.order = 30;
  DA.topbarTools.push(listButton);
  DA.coreViews = DA.coreViews || {};
  DA.coreViews.audit = render;
})();
