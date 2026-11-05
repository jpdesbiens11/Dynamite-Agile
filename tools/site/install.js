/* Installation page (D-O-048, 0.60.44 D-O-053): 5 steps from top to bottom. Step 1 says where the tool runs (an online
   Linux VPS, a local Linux server, a Windows PC of the team) and which computer the person types on (Windows, macOS,
   Linux): every command « on your computer » follows it. For a VPS, the host (Hostinger, Oracle Cloud Always Free,
   DigitalOcean) adapts the hints and the SSH command. The fields fill the commands and the message for an AI assistant;
   everything stays in the page (localStorage for this visitor only, wrapped in try/catch). */
(function () {
  "use strict";
  const SITE = document.body.dataset.site;
  const EN = document.documentElement.lang === "en";  // D-O-017: same script, English page in site/en/
  const BASE = SITE + (EN ? "/en" : "");
  const KEY = "da.install3";
  const store = {
    read() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (err) { return {}; } },
    write(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (err) { /* private window: fine */ } },
  };
  const guessPc = /Win/i.test(navigator.platform) ? "win" : /Mac/i.test(navigator.platform) ? "mac" : "linux";
  const state = Object.assign({ dest: "online", pc: guessPc, vps: "hostinger", domain: "", email: "", ip: "", lip: "", luser: "", done: {} },
    store.read());
  const save = () => store.write(state);
  const $ = (s, root) => (root || document).querySelector(s);
  const $$ = (s, root) => Array.from((root || document).querySelectorAll(s));
  const DEFAULTS = EN ? { domain: "workshop.my-domain.com", email: "me@example.com", ip: "203.0.113.10", lip: "192.168.1.20", luser: "your-name" }
    : { domain: "atelier.mon-domaine.ca", email: "moi@exemple.ca", ip: "203.0.113.10", lip: "192.168.1.20", luser: "votre-nom" };
  const value = (k) => (state[k] || "").trim() || DEFAULTS[k];
  const DESTS = ["online", "local", "windows"];
  const VPS_NAMES = { hostinger: "Hostinger", oracle: "Oracle Cloud (Always Free)", digitalocean: "DigitalOcean" };
  const OPEN = EN
    ? { win: "Windows: Win + X → Terminal", mac: "macOS: Cmd + Space, type « Terminal »", linux: "Linux: Ctrl + Alt + T" }
    : { win: "Windows : Win + X → Terminal", mac: "macOS : Cmd + Espace, tapez « Terminal »", linux: "Linux : Ctrl + Alt + T" };
  const PC_NAMES = { win: "Windows", mac: "macOS", linux: "Linux" };

  function pick(name, val) {
    $$('input[name="' + name + '"]').forEach((r) => { r.checked = r.value === val; r.closest("label").classList.toggle("on", r.checked); });
  }

  function setDest(dest) {
    if (!DESTS.includes(dest)) dest = "online";
    state.dest = dest; save(); pick("dest", dest);
    $$(".wiz-step[data-dest]").forEach((li) => { li.hidden = li.dataset.dest !== dest; });
    if (location.hash.slice(1) !== dest) history.replaceState(null, "", "#" + dest);
    fill(); progress();
  }
  function setPc(pc) {
    if (!PC_NAMES[pc]) pc = guessPc;
    state.pc = pc; save(); pick("pc", pc);
    $$("[data-pc]").forEach((n) => {
      const want = n.dataset.pc;
      n.hidden = !(want === pc || (want === "unix" && pc !== "win"));
    });
    $$('[data-pc-text="open"]').forEach((n) => { n.textContent = OPEN[pc]; });
    fill();
  }
  function setVps(vps) {
    if (!VPS_NAMES[vps]) vps = "hostinger";
    state.vps = vps; save(); pick("vps", vps);
    $$(".vps-how").forEach((d) => { d.hidden = d.dataset.vps !== vps; });
    $$("[data-vps-cmd]").forEach((p) => { p.hidden = (p.dataset.vpsCmd === "key") !== (vps === "oracle"); });
    fill();
  }
  $$('input[name="dest"]').forEach((r) => r.addEventListener("change", () => setDest(r.value)));
  $$('input[name="pc"]').forEach((r) => r.addEventListener("change", () => setPc(r.value)));
  $$('input[name="vps"]').forEach((r) => r.addEventListener("change", () => setVps(r.value)));

  ["domain", "email", "ip", "lip", "luser"].forEach((k) => {
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
    const page = BASE + "/installation.html#" + state.dest;
    const guide = BASE + "/installer.md";
    const pc = PC_NAMES[state.pc];
    if (EN) {
      const where = { online: "on an empty Ubuntu 24.04 VPS at " + VPS_NAMES[state.vps] + ", with the web address " + value("domain"),
        local: "on a local Linux server (Ubuntu 24.04) on my team's network, which may stay without Internet afterwards (--local)",
        windows: "on a Windows PC that hosts it for my team on our local network (PowerShell)" }[state.dest];
      return ["Hello! I'm not a technical person. I want to install DynamiteAgile " + where + ". My own computer runs " + pc + ".",
        "First read the procedure: " + page, "and the guide written for assistants: " + guide,
        "Guide me one step at a time: tell me where to type each command (on my computer or on the server) and what I should " +
        "see, then wait until I paste what the screen shows. If a message is in red, explain it simply and suggest the fix. " +
        "If my server is not empty (other applications, Docker…), adapt the procedure. Never ask me for a password or a private key."].join("\n");
    }
    const where = { online: "sur un VPS Ubuntu 24.04 vide chez " + VPS_NAMES[state.vps] + ", avec l'adresse web " + value("domain"),
      local: "sur un serveur Linux local (Ubuntu 24.04) du réseau de mon équipe, qui pourra ensuite rester sans Internet (--local)",
      windows: "sur un PC Windows qui l'héberge pour mon équipe sur notre réseau local (PowerShell)" }[state.dest];
    return ["Bonjour ! Je ne suis pas technicien. Je veux installer DynamiteAgile " + where + ". Mon ordinateur est sous " + pc + ".",
      "Lis d'abord la procédure : " + page, "et le guide écrit pour les assistants : " + guide,
      "Guide-moi une étape à la fois : dis-moi où taper chaque commande (sur mon ordinateur ou sur le serveur) et ce que je " +
      "devrais voir, puis attends que je te colle ce que l'écran affiche. Si un message est en rouge, explique-le simplement et " +
      "propose le correctif. Si mon serveur n'est pas vide (d'autres applications, Docker…), adapte la procédure. Ne me demande " +
      "jamais un mot de passe ni une clé privée."].join("\n");
  }

  /* ---------- steps ticked off and the progress bar ---------- */
  $$(".wiz-step").forEach((li) => {
    const box = $(".done input", li);
    if (!box) return;
    box.checked = !!state.done[li.dataset.step];
    li.classList.toggle("ok", box.checked);
    box.addEventListener("change", () => {
      state.done[li.dataset.step] = box.checked; save();
      li.classList.toggle("ok", box.checked); progress();
      if (box.checked) {
        const next = $$(".wiz-step").find((n) => !n.hidden && !$(".done input", n).checked);
        if (next) next.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
  function progress() {
    const steps = $$(".wiz-step").filter((li) => !li.hidden);
    const done = steps.filter((li) => $(".done input", li).checked).length;
    $(".progress-bar .track i").style.width = (100 * done / steps.length) + "%";
    $("#progress-text").textContent = done === steps.length
      ? (EN ? "Installed ✓ — welcome!" : "C'est installé ✓ — bienvenue !")
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

  setVps(state.vps);
  setPc(state.pc);
  const start = location.hash.slice(1);
  const legacy = { linux: "online", serveur: "online" }[start];  // addresses of 0.60.39 (#linux) and before (#serveur)
  setDest(DESTS.includes(start) ? start : legacy || state.dest);
  addEventListener("hashchange", () => { const h = location.hash.slice(1); if (DESTS.includes(h)) setDest(h); });
})();
