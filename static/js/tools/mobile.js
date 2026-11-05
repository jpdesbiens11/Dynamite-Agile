/* 0.60.25 (D-O-034): phones. Under 760 px wide, the top bar keeps the logo, a ☰ button and the account; the tabs, the
   platform tools (search…), Help and ⚙ Admin move into a drawer that slides from the left -- the usual pattern of a
   phone app (navigation drawer). The drawer closes on a choice, on the backdrop, on Escape or on the next page. The
   layout rules are in css/mobile.css; the desktop top bar is never touched. */
(function () {
  "use strict";

  const PHONE = window.matchMedia("(max-width: 760px)");
  const { el } = DA;
  const MOVED = ["nav.tabs", ".topbar-tools", "nav.tabs-end", ".admin-tab"];

  function close() {
    document.documentElement.classList.remove("nav-open");
    const toggle = document.querySelector(".nav-toggle");
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  }

  function open() {
    document.documentElement.classList.add("nav-open");
    const toggle = document.querySelector(".nav-toggle");
    if (toggle) toggle.setAttribute("aria-expanded", "true");
    const first = document.querySelector(".nav-drawer .tab.active, .nav-drawer a, .nav-drawer button");
    if (first) first.focus({ preventScroll: true });
  }

  function build(bar) {
    bar.dataset.phone = "1";
    document.querySelectorAll("body > .nav-drawer, body > .nav-backdrop").forEach((n) => n.remove());
    const drawer = el("div", { class: "nav-drawer", id: "nav-drawer", "aria-label": "Menu", "data-new": "0.60.25-phone-menu" });
    MOVED.forEach((sel) => { const node = bar.querySelector(sel); if (node) drawer.append(node); });
    drawer.addEventListener("click", (ev) => { if (ev.target.closest("a")) close(); });
    const backdrop = el("div", { class: "nav-backdrop", "aria-hidden": "true", onclick: close });
    const toggle = el("button", { type: "button", class: "nav-toggle", "aria-label": "Menu", "aria-controls": "nav-drawer",
      "aria-expanded": "false", onclick: () => (document.documentElement.classList.contains("nav-open") ? close() : open()) },
    el("span", { class: "nav-toggle-bars", "aria-hidden": "true" }));
    bar.prepend(toggle);
    // 0.60.29 (D-O-038): « Partager » stays in sight on a phone, beside the account
    if (DA.shareButton) bar.insertBefore(DA.shareButton("phone"), bar.querySelector(".user-area"));
    document.body.append(backdrop, drawer);
  }

  function setup() {
    document.documentElement.classList.toggle("da-phone", PHONE.matches);
    if (!PHONE.matches) {
      document.querySelectorAll("body > .nav-drawer, body > .nav-backdrop").forEach((n) => n.remove());
      close();
      return;
    }
    const bar = document.querySelector("#app > header.topbar");
    if (bar && !bar.dataset.phone) build(bar);
  }

  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") close(); });
  window.addEventListener("hashchange", close);
  // the top bar is rebuilt on every page: dress it as soon as it is there; a rotation that crosses the width redraws
  document.addEventListener("DOMContentLoaded", () => {
    const app = document.getElementById("app");
    if (app) new MutationObserver(setup).observe(app, { childList: true });
    setup();
  });
  PHONE.addEventListener("change", () => window.dispatchEvent(new HashChangeEvent("hashchange")));
  DA.phone = () => PHONE.matches;
})();
