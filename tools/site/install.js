/* Installation page (D-O-015): choice of destination, fields that fill the commands, the message for an AI assistant,
   steps ticked off. Everything stays in the page (localStorage for this visitor only, wrapped in try/catch). */
(function () {
  "use strict";
  const SITE = document.body.dataset.site;
  const EN = document.documentElement.lang === "en";  // D-O-017: same script, English page in site/en/
  const BASE = SITE + (EN ? "/en" : "");
  const KEY = "da.install";
  const store = {
    read() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (err) { return {}; } },
    write(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (err) { /* private window: fine */ } },
  };
  const state = Object.assign({ dest: "serveur", os: "", domain: "", email: "", ip: "", traefik: false, done: {} }, store.read());
  const save = () => store.write(state);
  const $ = (s, root) => (root || document).querySelector(s);
  const $$ = (s, root) => Array.from((root || document).querySelectorAll(s));
  const DEFAULTS = EN ? { domain: "workshop.my-domain.com", email: "me@example.com", ip: "203.0.113.10" }
    : { domain: "atelier.mon-domaine.ca", email: "moi@exemple.ca", ip: "203.0.113.10" };
  const value = (k) => (state[k] || "").trim() || DEFAULTS[k];

  /* ---------- destination ---------- */
  const DESTS = ["serveur", "essai", "windows", "local"];  // 0.60.10: Windows team server (D-O-022)
  function setDest(dest, fromHash) {
    if (!DESTS.includes(dest)) dest = state.dest || "serveur";
    state.dest = dest; save();
    $$('input[name="dest"]').forEach((r) => { r.checked = r.value === dest; r.closest(".dest-card").classList.toggle("on", r.checked); });
    $$(".path").forEach((p) => { p.hidden = p.dataset.path !== dest; });
    $$("[data-for]").forEach((n) => { n.hidden = !n.dataset.for.split(" ").includes(dest); });
    if (!fromHash) history.replaceState(null, "", "#" + dest);
    fill(); progress();
  }
  $$('input[name="dest"]').forEach((r) => r.addEventListener("change", () => setDest(r.value)));

  /* ---------- operating system (my computer) ---------- */
  function setOs(os) {
    state.os = os; save();
    $$(".os-tabs [data-os]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.os === os)));
    $$("[data-os-panel]").forEach((p) => { p.hidden = p.dataset.osPanel !== os; });
    progress();
  }
  $$(".os-tabs [data-os]").forEach((b) => b.addEventListener("click", () => setOs(b.dataset.os)));
  const guess = /Mac/i.test(navigator.platform) ? "mac" : /Linux/i.test(navigator.platform) ? "linux" : "windows";

  /* ---------- fields fill the commands and the message ---------- */
  ["domain", "email", "ip"].forEach((k) => {
    const input = $("#f-" + k);
    if (!input) return;
    input.value = state[k] || "";
    input.addEventListener("input", () => { state[k] = input.value.replace(/^https?:\/\//, "").replace(/\/.*$/, "").trim(); save(); fill(); });
  });
  /* 0.60.34: behind Traefik (Docker applications): the command takes --traefik and no email */
  const traefik = $("#f-traefik");
  if (traefik) {
    traefik.checked = !!state.traefik;
    traefik.addEventListener("change", () => { state.traefik = traefik.checked; save(); fill(); });
  }
  function fill() {
    $$("[data-proxy]").forEach((n) => {
      const other = n.dataset.for && !n.dataset.for.split(" ").includes(state.dest);  // the destination decides first
      n.hidden = other || (n.dataset.proxy === "traefik") !== !!state.traefik;
    });
    $$("span[data-v], code[data-v]").forEach((n) => { n.textContent = value(n.dataset.v); n.classList.toggle("ph", !state[n.dataset.v]); });
    $$("a.live").forEach((a) => { a.href = a.dataset.href.replace("{domain}", value("domain")); });
    $("#agent-text").textContent = prompt();
  }
  function prompt() {
    const page = BASE + "/installation.html#" + state.dest;
    const guide = BASE + "/installer.md";
    const os = { windows: "Windows", mac: "macOS", linux: "Linux" }[state.os || guess];
    if (EN) {
      const where = {
        serveur: "on an online server (Linux VPS) with the domain name " + value("domain") + (state.traefik ? ", behind the Traefik of my Docker applications (--traefik)" : ""),
        essai: "on a Linux server, as a private trial without a domain (SSH tunnel)",
        windows: "on a Windows PC that hosts it for my team on our local network (PowerShell)",
        local: "on my computer (" + os + "), to try it",
      }[state.dest];
      return ["Hello! I'm new to " + (state.dest === "windows" ? "PowerShell" : "Linux and the terminal") + ". I want to install Dynamite | Agile " + where + ".",
        "First read the procedure: " + page,
        "and the guide written for assistants: " + guide,
        "Guide me one step at a time: tell me where to type each command (on my computer or on the server) and what I " +
        "should see, then wait until I paste what the terminal shows before going on. If a message is in red, explain it " +
        "simply and suggest the fix. Never ask me for a password or a private key."].join("\n");
    }
    const where = {
      serveur: "sur un serveur en ligne (VPS Linux) avec le nom de domaine " + value("domain") + (state.traefik ? ", derrière le Traefik de mes applications Docker (--traefik)" : ""),
      essai: "sur un serveur Linux, en essai privé sans domaine (tunnel SSH)",
      windows: "sur un PC Windows qui l'héberge pour mon équipe sur notre réseau local (PowerShell)",
      local: "sur mon ordinateur (" + os + "), pour l'essayer",
    }[state.dest];
    return ["Bonjour ! Je débute avec " + (state.dest === "windows" ? "PowerShell" : "Linux et le terminal") + ". Je veux installer Dynamite | Agile " + where + ".",
      "Lis d'abord la procédure : " + page,
      "et le guide écrit pour les assistants : " + guide,
      "Guide-moi une étape à la fois : dis-moi où taper chaque commande (sur mon ordinateur ou sur le serveur) et ce que je " +
      "devrais voir, puis attends que je te colle ce que le terminal affiche avant de passer à la suite. Si un message est en " +
      "rouge, explique-le simplement et propose le correctif. Ne me demande jamais un mot de passe ni une clé privée."].join("\n");
  }

  /* ---------- steps ticked off and the progress bar ---------- */
  $$("[data-step]").forEach((li) => {
    const box = $(".done input", li);
    if (!box) return;
    box.checked = !!state.done[li.dataset.step];
    li.classList.toggle("ok", box.checked);
    box.addEventListener("change", () => {
      state.done[li.dataset.step] = box.checked; save();
      li.classList.toggle("ok", box.checked); progress();
      if (box.checked) {
        const next = $$("[data-step]", li.closest(".stepper")).find((n) => !$(".done input", n).checked);
        if (next) next.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  });
  function progress() {
    const lists = $$(".path:not([hidden]) .stepper:not([hidden]), .stepper.path:not([hidden])");
    const steps = lists.flatMap((l) => $$("[data-step]", l));
    const done = steps.filter((li) => $(".done input", li).checked).length;
    $(".progress-bar .track i").style.width = steps.length ? (100 * done / steps.length) + "%" : "0";
    $("#progress-text").textContent = done === steps.length && steps.length
      ? (EN ? "All steps done ✓" : "Toutes les étapes sont faites ✓")
      : (EN ? "Steps done: " : "Étapes faites : ") + done + " / " + steps.length;
  }

  /* ---------- the « where » label on every command block ---------- */
  $$("pre.cmd[data-where]").forEach((pre) => {
    const pc = pre.dataset.where === "pc";
    const tag = document.createElement("span");
    tag.className = "where " + (pc ? "pc" : "srv");
    tag.textContent = pc ? (EN ? "on your computer" : "sur votre ordinateur") : (EN ? "on the server" : "sur le serveur");
    pre.prepend(tag);
  });

  setOs(state.os || guess);
  const start = (location.hash || "").slice(1);
  setDest(DESTS.includes(start) ? start : state.dest, DESTS.includes(start));
  addEventListener("hashchange", () => { const h = location.hash.slice(1); if (DESTS.includes(h)) setDest(h, true); });
})();
