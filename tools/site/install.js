/* Installation page (D-O-015): choice of destination, fields that fill the commands, the message for an AI assistant,
   steps ticked off. Everything stays in the page (localStorage for this visitor only, wrapped in try/catch). */
(function () {
  "use strict";
  const SITE = document.body.dataset.site;
  const KEY = "da.install";
  const store = {
    read() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (err) { return {}; } },
    write(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (err) { /* private window: fine */ } },
  };
  const state = Object.assign({ dest: "serveur", os: "", domain: "", email: "", ip: "", done: {} }, store.read());
  const save = () => store.write(state);
  const $ = (s, root) => (root || document).querySelector(s);
  const $$ = (s, root) => Array.from((root || document).querySelectorAll(s));
  const DEFAULTS = { domain: "atelier.mon-domaine.ca", email: "moi@exemple.ca", ip: "203.0.113.10" };
  const value = (k) => (state[k] || "").trim() || DEFAULTS[k];

  /* ---------- destination ---------- */
  const DESTS = ["serveur", "essai", "local"];
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
  function fill() {
    $$("span[data-v], code[data-v]").forEach((n) => { n.textContent = value(n.dataset.v); n.classList.toggle("ph", !state[n.dataset.v]); });
    $$("a.live").forEach((a) => { a.href = a.dataset.href.replace("{domain}", value("domain")); });
    $("#agent-text").textContent = prompt();
  }
  function prompt() {
    const page = SITE + "/installation.html#" + state.dest;
    const guide = SITE + "/installer.md";
    const where = {
      serveur: "sur un serveur en ligne (VPS Linux) avec le nom de domaine " + value("domain"),
      essai: "sur un serveur Linux, en essai privé sans domaine (tunnel SSH)",
      local: "sur mon ordinateur (" + ({ windows: "Windows", mac: "macOS", linux: "Linux" }[state.os || guess]) + "), pour l'essayer",
    }[state.dest];
    return ["Bonjour ! Je débute avec Linux et le terminal. Je veux installer Dynamite | Agile " + where + ".",
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
      ? "Toutes les étapes sont faites ✓" : "Étapes faites : " + done + " / " + steps.length;
  }

  /* ---------- the « where » label on every command block ---------- */
  $$("pre.cmd[data-where]").forEach((pre) => {
    const pc = pre.dataset.where === "pc";
    const tag = document.createElement("span");
    tag.className = "where " + (pc ? "pc" : "srv");
    tag.textContent = pc ? "sur votre ordinateur" : "sur le serveur";
    pre.prepend(tag);
  });

  setOs(state.os || guess);
  const start = (location.hash || "").slice(1);
  setDest(DESTS.includes(start) ? start : state.dest, DESTS.includes(start));
  addEventListener("hashchange", () => { const h = location.hash.slice(1); if (DESTS.includes(h)) setDest(h, true); });
})();
