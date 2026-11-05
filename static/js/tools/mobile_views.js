/* 0.60.27 (D-O-036): what a phone is for. The big screens (Diamond, Exploration's Gantt, Tools) stay on the computer: on a
   phone they show a short note and a link back. Goldmine, Testing and the Timesheet become a list of cards, one item
   under the other (each table row a card, with its column names), the long filters folded behind « Filtres ». Dynamite
   gets a bar at the bottom of the screen: « + Page », « ✨ Page avec l'IA » and « Partager » (share.js: the phone's share sheet,
   or the link copied). Everything here runs only with html.da-phone (js/tools/mobile.js); the computer is unchanged. */
(function () {
  "use strict";

  const { el } = DA;
  const PC_ONLY = { diamond: "Diamond", exploration: "Exploration (Gantt)", tools: "Tools" };
  const CARDS = ["goldmine", "testing", "timesheet"];
  let wantAi = false;

  const phone = () => document.documentElement.classList.contains("da-phone");
  const moduleKey = () => document.documentElement.getAttribute("data-module") || "";

  /* ---------- the big screens: a note instead ---------- */
  function pcOnly() {
    const key = moduleKey();
    const on = phone() && !!PC_ONLY[key];
    document.documentElement.classList.toggle("pc-only", on);
    const app = document.getElementById("app");
    const note = app && app.querySelector(":scope > .pc-only-note");
    if (!on) { if (note) note.remove(); return; }
    if (note || !app) return;
    const bar = app.querySelector(":scope > header");
    const box = el("section", { class: "pc-only-note", "data-new": "0.60.27-pc-only" },
      el("p", { class: "pc-only-icon", "aria-hidden": "true" }, "💻"),
      el("h1", null, PC_ONLY[key] + " : sur un ordinateur"),
      el("p", null, "Cet écran est fait pour un grand écran (schémas, tableaux larges, Gantt). Ouvrez-le sur un ordinateur ; "
        + "sur le téléphone, gardez Goldmine, Testing, la feuille de temps et les pages Dynamite."),
      el("div", { class: "actions" }, el("a", { class: "btn btn-primary", href: "#/dynamite" }, "Pages Dynamite"),
        el("a", { class: "btn", href: "#/goldmine" }, "Goldmine"), el("a", { class: "btn", href: "#/timesheet" }, "Feuille de temps")));
    if (bar) bar.after(box); else app.prepend(box);
  }

  /* the drawer says which tabs are for the computer */
  function markDrawer() {
    document.querySelectorAll("body > .nav-drawer .tab[data-key]").forEach((tab) => {
      if (PC_ONLY[tab.dataset.key] && !tab.querySelector(".tab-pc")) {
        tab.append(el("span", { class: "tab-pc", "aria-label": "sur ordinateur" }, "💻 ordinateur"));
      }
    });
  }

  /* ---------- tables as cards: every cell carries its column name ---------- */
  function cards() {
    if (!phone() || !CARDS.includes(moduleKey())) return;
    document.querySelectorAll("#main table.data:not([data-cards])").forEach((table) => {
      const heads = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim());
      if (!heads.length) return;
      table.setAttribute("data-cards", "1");
      table.querySelectorAll("tbody tr").forEach((tr) => {
        [...tr.children].forEach((td, i) => { if (heads[i]) td.setAttribute("data-label", heads[i]); });
      });
    });
    document.querySelectorAll("#main .ag-filters:not([data-folded])").forEach((box) => {
      box.setAttribute("data-folded", "1");
      const n = box.querySelectorAll("select").length;
      if (!n) return;
      const toggle = el("button", { type: "button", class: "btn btn-small filters-toggle", "aria-expanded": "false",
        onclick: () => { const open = box.classList.toggle("filters-open"); toggle.setAttribute("aria-expanded", open ? "true" : "false"); } },
      "Filtres (" + n + ")");
      box.prepend(toggle);
    });
  }

  /* ---------- Dynamite: create, with the AI, share ---------- */
  function spaceKey() {
    const m = /^#\/dynamite\/([A-Z][A-Z0-9]{1,9})/.exec(location.hash);
    return m ? m[1] : "";
  }

  const share = () => DA.share({ direct: true });  // 0.60.29: the shared « Partager » of the platform (share.js)

  function dynamiteBar() {
    const old = document.querySelector("body > .dy-fab");
    const key = spaceKey();
    const editing = /\/(new|edit)(\/|$)/.test(location.hash) || location.hash.indexOf("/edit") > 0;
    if (!phone() || moduleKey() !== "dynamite" || !key || editing || !document.querySelector("#main .dy-new")) {
      if (old) old.remove();
      return;
    }
    if (old && old.dataset.key === key) return;
    if (old) old.remove();
    const bar = el("nav", { class: "dy-fab", "aria-label": "Actions rapides", "data-new": "0.60.27-dy-fab" },
      el("a", { class: "btn btn-primary", href: "#/dynamite/" + key + "/new" }, "+ Page"),
      el("a", { class: "btn", href: "#/dynamite/" + key + "/new", onclick: () => { wantAi = true; } }, "✨ Avec l'IA"),
      el("button", { type: "button", class: "btn", onclick: share }, "Partager"));
    bar.dataset.key = key;
    document.body.append(bar);
  }

  function openAiWhenReady() {
    if (!wantAi) return;
    const button = document.querySelector("#main .dy-ai-btn");
    if (button) { wantAi = false; button.click(); }
  }

  /* ---------- run after each drawing of the content ---------- */
  let queued = false;
  function update() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      pcOnly();
      markDrawer();
      cards();
      dynamiteBar();
      openAiWhenReady();
    });
  }
  document.addEventListener("DOMContentLoaded", () => {
    const app = document.getElementById("app");
    if (app) new MutationObserver(update).observe(app, { childList: true, subtree: true });
    update();
  });
  window.addEventListener("hashchange", update);
  DA.phoneShare = share;
})();
