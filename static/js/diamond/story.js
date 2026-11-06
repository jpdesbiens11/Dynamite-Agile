/* Diamond · « Storyline » (0.60.51, D-O-060): #/diamond/KEY/story. The use of the product told scene by scene, before
   the functional tree: who, where, with what, what happens, what one feels. A free team exercise in divergence -- no
   link to the functions; an AI assistant reads it later to propose the tree (« Copier pour l'IA », 0.60.52).
   The board (one card per scene, in order) above the scene being edited: its stage (story_stage.js), its title, what
   happens, loose notes, and the pictogram palette (story_pictos.js). Pictograms are saved when dropped. */
(function () {
  "use strict";

  const { api, el, clear, toast } = DA;
  const A = DA.agile;
  const D = DA.diamond;

  async function view(page, ctx) {
    const state = { data: await api.get(D.base(ctx) + "/story"), current: null, selected: null, timer: null };
    const holder = el("div", { class: "dm-page dm-story" });
    page.append(holder);
    state.run = async (path, body) => {
      try {
        const data = await api.post(D.base(ctx) + path, body || {});
        state.data = data;
        if (data.created) state.current = data.created;
      } catch (err) { toast(err.message, "error"); }
      state.selected = null;
      D.later(() => draw(holder, ctx, state));
    };
    draw(holder, ctx, state);
  }

  function scenes(state) { return state.data.scenes; }

  function draw(holder, ctx, state) {
    clear(holder);
    const editable = A.canEdit(ctx);
    const list = scenes(state);
    if (!list.some((s) => s.id === state.current)) state.current = list.length ? list[0].id : null;
    holder.append(A.pageHead(ctx, [el("span", null, "Diamond"), el("span", null, "Storyline")],
      editable && list.length ? el("button", { type: "button", class: "btn btn-primary btn-small", "data-new": "0.60.51-story-new",
        onclick: () => state.run("/story/scenes", {}) }, "Nouvelle scène") : null),
      el("div", { class: "page-head dm-intro" }, el("h1", { "data-new": "0.60.51-story" }, "Storyline"),
        el("p", { class: "muted" }, "Racontez l'utilisation du produit, scène par scène : qui, où, avec quoi, ce qui se passe et ce "
          + "qu'on ressent. On diverge en équipe, sans bonne ni mauvaise réponse, avant l'arbre fonctionnel. Un assistant IA s'en "
          + "servira ensuite pour proposer l'arbre et le reste de Diamond.")));
    if (!list.length) {
      holder.append(DA.spaces.startHere("La Storyline de " + ctx.meta.project.name,
        "Prenez 30 minutes en équipe. Suivez une personne du jour où elle découvre le produit jusqu'au jour où elle s'en "
        + "débarrasse : la boîte, la première utilisation, l'usage de tous les jours, le pépin, l'entretien, le rangement. "
        + "Une scène par moment, des pictogrammes pour la montrer, quelques mots pour la raconter.",
        editable ? [["Première scène", () => state.run("/story/scenes", { title: "La découverte" }), true]] : []));
      return;
    }
    const board = el("ol", { class: "dm-story-board", "aria-label": "Les scènes, dans l'ordre" });
    const work = el("div", { class: "dm-story-work" });
    holder.append(board, work);
    drawBoard(board, ctx, state);
    drawScene(work, board, ctx, state, editable);
  }

  function drawBoard(board, ctx, state) {
    clear(board);
    scenes(state).forEach((s, i) => board.append(el("li", null, el("button", {
      type: "button", class: "dm-story-card" + (s.id === state.current ? " is-current" : ""), "aria-current": s.id === state.current ? "true" : null,
      onclick: () => { state.current = s.id; state.selected = null; D.later(() => draw(board.parentNode, ctx, state)); },
    }, el("span", { class: "dm-story-num" }, String(i + 1)), D.storyStage(s.items, { mini: true }),
    el("span", { class: "dm-story-title" }, s.title)))));
  }

  function drawScene(work, board, ctx, state, editable) {
    const list = scenes(state);
    const index = list.findIndex((s) => s.id === state.current);
    const scene = list[index];
    const items = scene.items;
    const base = "/story/scenes/" + scene.id;
    const stageBox = el("div", { class: "dm-story-stagebox" });
    const toolsBox = el("div", { class: "dm-story-toolsbox" });
    const save = () => {
      clearTimeout(state.timer);
      state.timer = setTimeout(async () => {
        try {
          state.data = await api.patch(D.base(ctx) + base, { items });
          const fresh = scenes(state).find((s) => s.id === scene.id);
          if (fresh) fresh.items = items;
          drawBoard(board, ctx, state);
        } catch (err) { toast(err.message, "error"); }
      }, 400);
    };
    const redraw = () => {
      clear(stageBox);
      clear(toolsBox);
      stageBox.append(D.storyStage(items, {
        editable, selected: state.selected,
        onSelect: (i) => { state.selected = i; redraw(); focus(i); },
        onChange: (i) => { state.selected = i; save(); redraw(); focus(i); },
        onRemove: (i) => remove(i),
      }));
      const item = items[state.selected];
      if (editable && item) toolsBox.append(D.storyTools(item, () => { save(); redraw(); }, () => remove(state.selected)));
      else if (editable) toolsBox.append(el("p", { class: "muted dm-story-hint" }, items.length
        ? "Cliquez un pictogramme pour lui donner une étiquette, le grossir ou le retourner. Alt + flèches pour le déplacer au clavier."
        : "Ajoutez des pictogrammes depuis la palette : la personne, le lieu, le produit, ce qui l'entoure, ce qu'elle ressent."));
    };
    const focus = (i) => { const node = stageBox.querySelectorAll(".dm-story-item")[i]; if (node) node.focus(); };
    const remove = (i) => { items.splice(i, 1); state.selected = null; save(); redraw(); };
    const add = (key) => {
      if (items.length >= state.data.limits.items) { toast(state.data.limits.items + " pictogrammes au maximum par scène.", "error"); return; }
      // the first free spot of a 5 x 3 grid, from the middle out, so a new pictogram never hides another
      const spots = [[50, 50], [30, 50], [70, 50], [50, 25], [50, 75], [30, 25], [70, 25], [30, 75], [70, 75], [12, 50], [88, 50],
        [12, 25], [88, 25], [12, 75], [88, 75]];
      const free = spots.find(([x, y]) => items.every((it) => Math.abs(it.x - x) > 9 || Math.abs(it.y - y) > 14)) || [50, 50];
      items.push({ p: key, x: free[0], y: free[1], s: 2, f: 0, t: "" });
      state.selected = items.length - 1;
      save();
      redraw();
    };
    const text = (name, label, rows, hint) => {
      const input = el(rows ? "textarea" : "input", { type: rows ? null : "text", rows: rows || null, maxlength: String(state.data.limits[name]),
        disabled: editable ? null : "", placeholder: hint });
      input.value = scene[name] || "";
      input.addEventListener("change", async () => {
        try {
          state.data = await api.patch(D.base(ctx) + base, { [name]: input.value });
          drawBoard(board, ctx, state);
        } catch (err) { toast(err.message, "error"); }
      });
      return DA.field(label, input);
    };
    redraw();
    work.append(el("section", { class: "dm-story-main", "aria-label": "Scène " + (index + 1) },
      el("div", { class: "dm-story-head" }, el("span", { class: "dm-story-count" }, "Scène " + (index + 1) + " sur " + list.length),
        editable ? el("div", { class: "dm-actions" },
          el("button", { type: "button", class: "btn btn-small", disabled: index === 0 ? "" : null, "aria-label": "Déplacer avant",
            onclick: () => state.run(base + "/move", { to: index - 1 }) }, "← Avant"),
          el("button", { type: "button", class: "btn btn-small", disabled: index === list.length - 1 ? "" : null, "aria-label": "Déplacer après",
            onclick: () => state.run(base + "/move", { to: index + 1 }) }, "Après →"),
          el("button", { type: "button", class: "btn btn-small", onclick: () => state.run(base + "/duplicate") }, "Dupliquer"),
          el("button", { type: "button", class: "btn btn-small", onclick: () => {
            if (window.confirm("Retirer la scène « " + scene.title + " » ?")) state.run(base + "/delete");
          } }, "Retirer")) : null),
      text("title", "Titre de la scène", 0, "ex. Le premier essai dans la cour"),
      stageBox, toolsBox,
      el("div", { class: "dm-story-texts" },
        text("caption", "Ce qui se passe", 3, "ex. Léa sort le robot de la boîte et cherche comment l'allumer."),
        text("notes", "Idées, irritants, questions", 3, "En vrac : tout ce que la scène fait penser, sans filtrer."))),
    editable ? D.storyPalette(add) : null);
  }

  A.views.story = view;
})();
