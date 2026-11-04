/* « Terminal R&D » theme (D-B-088): the prompt line under the top bar and the boot sequence after sign-in.
   Pure presentation: both appear only when <html data-term> is set, read only what the page already knows (session,
   address) and never block -- a click or a key skips the boot. Built with textContent only. */
(function () {
  "use strict";

  const { el } = DA;
  const on = () => document.documentElement.hasAttribute("data-term");
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const COMMANDS = {  // what the prompt « types » on each screen
    dashboard: "status --all --mine", home: "ls ~/spaces", goldmine: "goldmine ls --needs --requirements",
    exploration: "gantt --plan", agile: "agile board --sprint current", dynamite: "wiki open", testing: "testbase ls --standards",
    tools: "tools --list", training: "training plan --year", timesheet: "timesheet week --submit", help: "man dynamite",
    admin: "sudo admin", search: "grep -r", settings: "config --user", objectives: "objectives ls", audit: "audit ls",
  };

  let typing = null;
  function prompt(bar) {
    const user = DA.session && DA.session.user ? DA.session.user.username : "user";
    const parts = (location.hash || "#/").replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean);
    const path = "~/" + parts.slice(0, 2).map((p) => decodeURIComponent(p).toLowerCase()).join("/");
    const cmd = el("span", { class: "c" });
    const line = el("div", { class: "term-prompt", "aria-hidden": "true" },
      el("span", { class: "u" }, user), el("span", { class: "h" }, "@dynamite"), ":", el("span", { class: "p" }, path), "$", cmd,
      el("span", { class: "caret" }));
    bar.after(line);
    const text = COMMANDS[parts[0] || "dashboard"] || "open " + (parts[0] || "");
    clearTimeout(typing);
    if (reduce()) { cmd.textContent = text; return; }
    let k = 0;
    (function type() {
      cmd.textContent = text.slice(0, ++k);
      if (k < text.length) typing = setTimeout(type, 22 + Math.random() * 30);
    })();
  }

  /* a prompt line under every new top bar (the shell re-renders it on each screen) */
  const root = document.getElementById("app");
  if (root) {
    new MutationObserver(() => {
      if (!on()) return;
      const bar = root.querySelector(":scope > .topbar");
      if (bar && !(bar.nextElementSibling && bar.nextElementSibling.classList.contains("term-prompt"))) prompt(bar);
    }).observe(root, { childList: true });
  }

  /* boot sequence after sign-in: a short log of what is being loaded; resolves when done or skipped */
  DA.bootSequence = function (session) {
    if (!on() || reduce()) return Promise.resolve();
    return new Promise((resolve) => {
      const pre = el("pre");
      const box = el("div", { class: "term-boot", role: "status", "aria-label": "Démarrage" }, pre,
        el("span", { class: "skip" }, "clic ou touche pour passer"));
      const mods = (session.modules || []).filter((m) => m.available);
      const lines = [
        ["hi", "Dynamite | Agile — version " + ((session.about && session.about.version) || "")],
        ["dim", "serveur de l'équipe · aucune ressource externe"],
        ["ok", "[  OK  ] VPN link · session " + (session.user ? session.user.username : "")],
        ["ok", "[  OK  ] CSRF token · audit_log"],
      ].concat(mods.map((m) => ["ok", "[  OK  ] mount /" + m.key + "  (" + m.label + ")"]))
        .concat([["ok", "[  OK  ] " + (session.projects || []).length + " Space(s) accessible(s)"],
          ["warn", "[ INFO ] Ctrl+K : palette de commandes"], ["hi", "ready_"]]);
      let i = 0, timer = null, done = false;
      function finish() {
        if (done) return;
        done = true;
        clearTimeout(timer);
        document.removeEventListener("keydown", finish, true);
        box.remove();
        resolve();
      }
      function next() {
        if (i >= lines.length) { timer = setTimeout(finish, 450); return; }
        const [cls, text] = lines[i++];
        pre.append(el("span", { class: cls }, text), "\n");
        timer = setTimeout(next, 55);
      }
      box.addEventListener("click", finish);
      document.addEventListener("keydown", finish, true);
      document.body.append(box);
      next();
    });
  };
})();
