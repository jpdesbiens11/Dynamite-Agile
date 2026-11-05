/* Default theme (« croquis d'ingénieur », D-B-087, core lot v0.22): hand-drawn icons and the accent colour of each tool.
   - DA.icon(name): inline <svg> using the local sprite /img/icons.svg (#i-<name>), stroke = currentColor, so it follows
     the theme and the text colour; decorative (aria-hidden), the label next to it stays real text.
   - DA.NAV: order of the top-bar tabs by order of use, in groups (plan → build → verify, then support tools), with a
     one-line description shown as a tooltip on hover.
   - <html data-module="<key>"> is set by the shell: sketch.css gives each tool its highlighter colour (--acc). */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  /* D-B-088: the « Terminal R&D » theme has its own crisp icons and marks (same names) */
  const term = () => document.documentElement.hasAttribute("data-term");
  const sprite = () => (term() ? "/img/icons-term.svg" : "/img/icons.svg");
  DA.refreshIcons = function () {  // after a theme change: every icon already on screen follows
    document.querySelectorAll("svg.sk-icon use").forEach((u) => {
      u.setAttribute("href", sprite() + "#" + u.getAttribute("href").split("#")[1]);
    });
    document.querySelectorAll("img[data-mark]").forEach((img) => { img.src = DA.mark(img.getAttribute("data-mark")); });
  };

  /* last theme of this browser, so the sign-in page already looks like it (per-viewer convenience, may be empty) */
  try {
    const last = localStorage.getItem("da.theme");
    if (last === "terminal") {
      document.documentElement.setAttribute("data-theme", "dark");
      document.documentElement.setAttribute("data-term", "on");
      document.documentElement.removeAttribute("data-sketch");
    }
  } catch (err) { /* storage blocked: default look */ }
  DA.icon = function (name, cls) {
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "sk-icon" + (cls ? " " + cls : ""));
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    const use = document.createElementNS(NS, "use");
    use.setAttribute("href", sprite() + "#i-" + name);
    svg.append(use);
    return svg;
  };

  /* key -> [icon, tooltip]; groups are separated by a hand-drawn tick in the top bar */
  DA.NAV = {
    groups: [["debuter", "dashboard", "home"], ["goldmine", "diamond", "exploration", "agile", "dynamite", "testing"], ["tools", "training", "timesheet"]],
    items: {
      debuter: ["debuter", "Débuter : démarrer un projet, étape par étape"],  // 0.60.08
      dashboard: ["dashboard", "Tout ce qui vous attend, dans tous vos Spaces"],
      home: ["spaces", "Vos Spaces et qui contacter"],
      goldmine: ["goldmine", "Needs et requirements, traçabilité jusqu'au test"],
      diamond: ["diamond", "Arbre fonctionnel, structure fonctionnelle, risques et DFMEA"],  // 0.60.11
      exploration: ["exploration", "Plan du projet et Gantt"],
      agile: ["agile", "Backlog, Sprints, Board et Change Management"],
      dynamite: ["dynamite", "Wiki : pages, procédures, Base de connaissances"],
      testing: ["testing", "Test Base, Test Plans et listes centrales"],
      tools: ["tools", "Idéation, Pugh, Kepner-Tregoe, Generator"],
      training: ["training", "Topics, plans de formation et tests"],
      timesheet: ["timesheet", "Ma semaine, approbations et exports"],
      help: ["help", "Guide, FAQ et DEMO"],
      about: ["about", "Qui a fait Dynamite | Agile, et comment"],  // 0.60.01
    },
  };

  /* marks of the left panel (colored sketches, static/img/marks/) */
  DA.mark = (key) => (term() ? "/img/marks-term/" : "/img/marks/") + key + ".svg";

  /* one floating note for every [data-tip] element (a CSS tooltip would be clipped by the scrolling tab bar) */
  let tip = null, timer = null;
  function showTip(target) {
    if (!document.documentElement.hasAttribute("data-sketch")) return;
    if (!tip) { tip = document.createElement("div"); tip.className = "sk-tip"; tip.setAttribute("role", "tooltip"); document.body.append(tip); }
    tip.textContent = target.getAttribute("data-tip");
    const r = target.getBoundingClientRect();
    tip.style.left = Math.max(8, Math.min(window.innerWidth - 270, r.left + r.width / 2 - 110)) + "px";
    tip.style.top = (r.bottom + 10) + "px";
    tip.classList.add("on");
  }
  function hideTip() { clearTimeout(timer); if (tip) tip.classList.remove("on"); }
  document.addEventListener("mouseover", (ev) => {
    const target = ev.target.closest && ev.target.closest("[data-tip]");
    clearTimeout(timer);
    if (!target) { hideTip(); return; }
    timer = setTimeout(() => showTip(target), 350);
  });
  document.addEventListener("focusin", (ev) => { const t = ev.target.closest && ev.target.closest("[data-tip]"); if (t) showTip(t); else hideTip(); });
  document.addEventListener("scroll", hideTip, true);
  window.addEventListener("hashchange", hideTip);

  DA.setModuleAccent = function (key) {
    document.documentElement.setAttribute("data-module", key || "home");
  };
})();
