/* « Tools » (D-B-065, sections D-B-073): the toolbox tab, in place of Generator in the top bar.
   #/tools, #/tools/design   -> Design: divergent and convergent methods, each with « Ouvrir l'outil »,
                                « La méthode » and « FAQ » (wiki pages of the TOOLS space)
   #/tools/generator          -> Generator: document references (#/codex/KEY, its own screen)
   #/tools/KEY/<tool>[/id]    -> a Design tool for a Space, in the Agile shell (Space picker, sidebar):
                                ideation (brainstorming, brainwriting, storytelling, mind map), pugh, kt. */
(function () {
  "use strict";

  const { api, el, clear } = DA;
  const A = DA.agile;
  const LAST = "tools.space";
  const SECTIONS = [["design", "Design"], ["generator", "Generator"]];

  const mark = () => el("img", { src: DA.mark("tools"), alt: "", class: "tl-mark-img" });

  const TOOLS_SHELL = {
    module: "tools", title: "Tools · Design", home: "ideation", issueNav: "ideation", noCreate: true, mark,
    nav: [["hub", "← Tools · Design"], ["ideation", "Idéation (divergent)"], ["pugh", "Pugh Matrix"],
      ["kt", "Kepner-Tregoe"]],
  };
  const TOOL_VIEW = { ideation: "ideation", pugh: "pugh", kt: "kt" };
  const OPEN_LABEL = { ideation: "Ouvrir l'idéation", pugh: "Ouvrir la matrice", kt: "Ouvrir l'analyse", codex: "Ouvrir Generator" };
  const BADGE = { divergent: "Divergent", convergent: "Convergent", reference: "Référence" };

  function remembered() {
    try { return localStorage.getItem(LAST) || ""; } catch (err) { return ""; }
  }
  function remember(key) {
    try { localStorage.setItem(LAST, key); } catch (err) { /* private window */ }
  }

  function workSpaces() {
    return DA.session.projects.filter((p) => p.key !== "TOOLS");
  }

  /* Design | Generator */
  function sectionTabs(active) {
    return el("nav", { class: "tl-sections", "aria-label": "Sections de Tools" }, SECTIONS.map(([key, label]) =>
      el("a", { href: "#/tools/" + key, class: "tl-section" + (key === active ? " active" : ""),
        "aria-current": key === active ? "page" : null}, label)));
  }

  function spacePicker() {
    const spaces = workSpaces();
    const current = spaces.find((p) => p.key === DA.spaces.defaultKey()) || spaces.find((p) => p.key === remembered())
      || spaces.find((p) => p.key !== "HEADLAMP") || spaces[0];  // D-B-134: the default Space first
    const picker = el("select", { class: "tl-space", "aria-label": "Space de travail" },
      spaces.map((p) => el("option", { value: p.key, selected: current && p.key === current.key }, p.key + " · " + p.name)));
    picker.addEventListener("change", () => remember(picker.value));
    return picker;
  }

  function head(title, text) {
    return el("div", { class: "tl-head" }, mark(), el("div", null, el("h1", null, title), el("p", { class: "muted" }, text)));
  }

  async function catalogue() {
    return api.get("/api/tools/catalog");
  }

  async function section(main, key) {
    clear(main);
    main.classList.remove("ag-main");
    let data;
    try { data = await catalogue(); } catch (err) { main.append(el("p", { class: "form-error" }, err.message)); return; }
    main.append(sectionTabs(key));
    const picker = spacePicker();
    const grid = el("div");
    const families = data.sections[key].families;
    const draw = () => {
      remember(picker.value);
      clear(grid);
      families.forEach((family) => {
        const list = data.methods.filter((m) => m.family === family);
        grid.append(el("h2", { class: "tl-family tl-" + family }, data.families[family]),
          el("div", { class: "tl-grid" }, list.map((m) => card(m, picker.value))));
      });
    };
    picker.addEventListener("change", draw);
    main.append(key === "design"
      ? head("Tools · Design", "Diverger d'abord (beaucoup d'idées, sans juger), puis converger (évaluer et choisir avec les "
        + "needs et requirements Goldmine). Chaque méthode a sa page et sa FAQ, modifiables comme un wiki.")
      : head("Tools · Generator", "Références documentaires : numéroter et classer les documents du PDP (Lean "
        + "Canvas, Concept Review, CdCF, PDR / CDR, Validation Report…). Le registre est tenu par Space."),
    el("div", { class: "tl-bar" }, el("label", null, "Space de travail ", picker),
      data.hub_page ? el("a", { class: "btn btn-small", href: "#/dynamite/TOOLS/page/" + data.hub_page }, "Wiki Tools") : null),
    grid);
    draw();
  }

  function card(m, space) {
    const toolHref = m.tool === "codex" ? "#/codex/" + space
      : "#/tools/" + space + "/" + TOOL_VIEW[m.tool] + (m.tool === "ideation" ? "/new-" + m.key : "");
    return el("article", { class: "tl-card tl-card-" + m.family },
      el("div", { class: "tl-card-top" }, el("h3", null, m.name), el("span", { class: "badge tl-badge-" + m.family }, BADGE[m.family])),
      el("p", { class: "muted" }, m.tagline),
      el("div", { class: "tl-actions" },
        m.tool ? el("a", { class: "btn btn-small btn-primary", href: toolHref }, OPEN_LABEL[m.tool]) : null,
        m.page_id ? el("a", { class: "btn btn-small", href: "#/dynamite/TOOLS/page/" + m.page_id }, "La méthode") : null,
        m.faq_id ? el("a", { class: "btn btn-small", href: "#/dynamite/TOOLS/page/" + m.faq_id }, "FAQ") : null));
  }

  function render(main, parts) {
    const first = parts[0] || "design";
    if (SECTIONS.some(([key]) => key === first)) { section(main, first); return; }
    remember(first.toUpperCase());
    A.render(main, parts, TOOLS_SHELL);
  }

  DA.tools = DA.tools || {};
  DA.tools.sectionTabs = sectionTabs;
  A.views.hub = () => { location.hash = "#/tools/design"; };
  A.views.codex = (page, ctx) => { location.hash = "#/codex/" + ctx.key; };
  DA.registerModule("tools", render);
})();
