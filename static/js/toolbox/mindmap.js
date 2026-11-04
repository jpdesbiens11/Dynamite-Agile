/* Tools · Design - Mind Map (D-B-073): the session question is the centre;
   cards are placed freely on a large surface (drag to move, position saved for
   everybody), lines link cards together or to the centre (« Lier », then click
   the other card; click a line to remove it). Double-click on the surface adds a
   card there, linked to the selected card (or the centre). Refreshes itself
   every few seconds, never while a card is being moved. */
(function () {
  "use strict";

  const { el, clear, field, modal } = DA;
  const A = DA.agile;
  const SVG = "http://www.w3.org/2000/svg";
  const svg = (tag, attrs) => {
    const node = document.createElementNS(SVG, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, String(v)));
    return node;
  };

  function view(page, ctx, data) {
    const I = DA.tools.ideation;
    const state = { ctx, data, selected: new Set(), parent: null, linkFrom: null, focusCard: null, busy: false };
    const top = el("div");
    const bar = el("div", { class: "tl-map-bar" });
    const scroller = el("div", { class: "tl-map-scroll", tabindex: "0", "aria-label": "Surface de la mind map" });
    const surface = el("div", { class: "tl-map" });
    const lines = svg("svg", { class: "tl-map-lines" });
    surface.append(lines);
    scroller.append(surface);
    page.append(top, bar, scroller);
    let centred = false;

    const canWrite = () => A.canEdit(ctx) && state.data.session.status !== "closed";
    const sizeOf = () => state.data.surface || { width: 3000, height: 2000 };

    function addCard(x, y) {
      const text = el("textarea", { rows: 3, maxlength: 1000, placeholder: "Un mot-clé ou une courte phrase" });
      const cards = state.data.ideas;
      const to = el("select", null, el("option", { value: "centre" }, "Le centre : " + (state.data.session.prompt || "sujet").slice(0, 40)),
        el("option", { value: "" }, "— aucune ligne —"),
        cards.map((c) => el("option", { value: c.id, selected: state.focusCard === c.id }, c.text.slice(0, 50))));
      let close = null;
      const form = el("form", { class: "ag-form", onsubmit: (ev) => {
        ev.preventDefault();
        if (!text.value.trim()) { text.focus(); return; }
        close();
        const body = { text: text.value, link_to: to.value };
        if (x !== undefined) Object.assign(body, { x: Math.round(x), y: Math.round(y) });
        I.act(state, "post", "/ideas", body);
      } }, field("Carte", text), field("Relier à", to),
      el("div", { class: "form-actions" }, el("button", { type: "button", class: "btn", onclick: () => close() }, "Annuler"),
        el("button", { type: "submit", class: "btn btn-primary" }, "Ajouter")));
      close = modal("Nouvelle carte", form);
      text.focus();
    }

    function link(targetId) {
      const from = state.linkFrom;
      state.linkFrom = null;
      if (from === null || from === targetId) { state.redraw(); return; }
      const [a, b] = from === "centre" ? [targetId, "centre"] : [from, targetId];
      I.act(state, "post", "/links", { a_id: a, b_id: b });
    }

    function drag(node, idea) {
      node.addEventListener("pointerdown", (ev) => {
        if (!canWrite() || ev.button !== 0 || ev.target.closest("button, input, a")) return;
        ev.preventDefault();
        state.busy = true;
        node.setPointerCapture(ev.pointerId);
        node.classList.add("dragging");
        const startX = ev.clientX, startY = ev.clientY;
        const x0 = idea.pos_x || 0, y0 = idea.pos_y || 0;
        let moved = false;
        const move = (e) => {
          const dx = e.clientX - startX, dy = e.clientY - startY;
          if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
          idea.pos_x = Math.max(0, Math.min(sizeOf().width - 60, x0 + dx));
          idea.pos_y = Math.max(0, Math.min(sizeOf().height - 40, y0 + dy));
          node.style.left = idea.pos_x + "px";
          node.style.top = idea.pos_y + "px";
          drawLines();
        };
        const up = () => {
          node.removeEventListener("pointermove", move);
          node.removeEventListener("pointerup", up);
          node.classList.remove("dragging");
          state.busy = false;
          if (moved) I.act(state, "patch", "/ideas/" + idea.id, { x: Math.round(idea.pos_x), y: Math.round(idea.pos_y) });
          else { state.focusCard = idea.id; if (state.linkFrom !== null) link(idea.id); else markFocus(); }
        };
        node.addEventListener("pointermove", move);
        node.addEventListener("pointerup", up);
      });
    }

    function markFocus() {
      surface.querySelectorAll(".tl-node").forEach((n) => n.classList.toggle("focus", Number(n.dataset.id) === state.focusCard));
    }

    function centreOf(id) {
      const node = surface.querySelector(id === null ? ".tl-map-centre" : '.tl-node[data-id="' + id + '"]');
      if (!node) return null;
      return [node.offsetLeft + node.offsetWidth / 2, node.offsetTop + node.offsetHeight / 2];
    }

    function drawLines() {
      while (lines.firstChild) lines.removeChild(lines.firstChild);
      (state.data.links || []).forEach((l) => {
        const a = centreOf(l.a_id), b = centreOf(l.b_id);
        if (!a || !b) return;
        const g = svg("g", { class: "tl-link" });
        const title = svg("title");
        title.textContent = canWrite() ? "Cliquer pour retirer la ligne" : "Lien";
        g.append(title, svg("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: "tl-link-hit" }),
          svg("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: "tl-link-line" + (l.b_id === null ? " tl-link-main" : "") }));
        if (canWrite()) {
          g.addEventListener("click", () => {
            if (window.confirm("Retirer cette ligne ?")) I.act(state, "del", "/links/" + l.id);
          });
        }
        lines.append(g);
      });
    }

    function node(idea) {
      const n = I.card(state, idea, { rebound: false });
      n.classList.add("tl-node");
      if (state.focusCard === idea.id) n.classList.add("focus");
      if (state.linkFrom === idea.id) n.classList.add("linking");
      n.style.left = (idea.pos_x || 0) + "px";
      n.style.top = (idea.pos_y || 0) + "px";
      if (canWrite()) {
        n.querySelector(".tl-idea-actions").prepend(el("button", { type: "button", class: "btn btn-small",
          title: "Relier cette carte à une autre", onclick: () => { state.linkFrom = idea.id; state.redraw(); } }, "Lier"));
      }
      drag(n, idea);
      return n;
    }

    state.redraw = () => {
      clear(top);
      clear(bar);
      const { session: s, ideas } = state.data;
      const size = sizeOf();
      surface.style.width = size.width + "px";
      surface.style.height = size.height + "px";
      lines.setAttribute("width", size.width);
      lines.setAttribute("height", size.height);
      top.append(...I.header(ctx, state).filter(Boolean));
      bar.append(...[canWrite() ? el("button", { type: "button", class: "btn btn-primary btn-small", onclick: () => addCard() }, "Ajouter une carte") : null,
        state.linkFrom !== null
          ? el("span", { class: "tl-map-hint" }, "Cliquez la carte à relier (ou le centre) — ",
            el("button", { type: "button", class: "link-btn", onclick: () => { state.linkFrom = null; state.redraw(); } }, "annuler"))
          : el("span", { class: "muted" }, canWrite() ? "Double-clic sur la surface : carte à cet endroit · glisser pour déplacer · « Lier » puis "
            + "une autre carte · clic sur une ligne pour la retirer." : "Lecture seule."),
        el("span", { class: "muted" }, ideas.length + " carte(s) · " + (state.data.links || []).length + " ligne(s)"),
        state.selected.size ? el("button", { type: "button", class: "btn btn-small", onclick: () => I.toPugh(state) },
          "Envoyer " + state.selected.size + " carte(s) vers une Pugh matrix") : null].filter(Boolean));
      Array.from(surface.querySelectorAll(".tl-node, .tl-map-centre")).forEach((n) => n.remove());
      const centre = el("div", { class: "tl-map-centre" + (state.linkFrom !== null ? " target" : ""), title: "Centre de la carte" }, s.prompt || s.title);
      centre.style.left = size.width / 2 + "px";
      centre.style.top = size.height / 2 + "px";
      centre.addEventListener("click", () => { if (state.linkFrom !== null && state.linkFrom !== "centre") link("centre"); });
      surface.append(centre);
      ideas.forEach((i) => surface.append(node(i)));
      drawLines();
      if (!centred) {
        centred = true;
        requestAnimationFrame(() => {
          scroller.scrollLeft = size.width / 2 - scroller.clientWidth / 2;
          scroller.scrollTop = size.height / 2 - scroller.clientHeight / 2;
        });
      }
    };
    surface.addEventListener("dblclick", (ev) => {
      if (!canWrite() || ev.target !== surface && ev.target !== lines) return;
      const box = surface.getBoundingClientRect();
      addCard(ev.clientX - box.left - 90, ev.clientY - box.top - 20);
    });
    document.addEventListener("keydown", function esc(ev) {
      if (!page.isConnected) { document.removeEventListener("keydown", esc); return; }
      if (ev.key === "Escape" && state.linkFrom !== null) { state.linkFrom = null; state.redraw(); }
    });
    state.redraw();
    I.poll(state, page);
  }

  DA.tools = DA.tools || {};
  DA.tools.mindmap = view;
})();
