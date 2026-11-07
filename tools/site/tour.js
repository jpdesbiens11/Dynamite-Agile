/* The guided tour of the installation page (0.60.70, D-O-076): the one link shared with partners
   (installation.html#online) shows everything from there -- what DynamiteAgile is, the preview pages of the site, how
   to install it, then the live demo with its QR code for a phone. A spotlight follows the part of the page each step
   talks about; the card has its own French and English. Opens by itself on the first visit in this browser, then
   « ▶ Tour guidé » restarts it. No external resource: the QR code is drawn in the page (static/js/tools/qr.js). */
(function () {
  "use strict";
  const EN = document.documentElement.lang === "en";
  const SEEN = "da.site.tour.seen", AT = "da.site.tour.at";  // AT: the step, kept when FR | EN switches the page
  const demo = document.body.dataset.demo || "";
  const say = (fr, en) => (EN ? en : fr);
  const store = {
    get() { try { return localStorage.getItem(SEEN); } catch (err) { return "1"; } },
    set() { try { localStorage.setItem(SEEN, "1"); } catch (err) { /* private window */ } },
    at(i) { try { if (i == null) sessionStorage.removeItem(AT); else sessionStorage.setItem(AT, String(i)); } catch (err) { /* ignored */ } },
    step() { try { return sessionStorage.getItem(AT); } catch (err) { return null; } },
  };

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === "class") node.className = v; else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v); else node.setAttribute(k, v);
    });
    kids.flat().forEach((kid) => { if (kid != null) node.append(kid.nodeType ? kid : document.createTextNode(kid)); });
    return node;
  }
  const link = (href, text, blank) => el("a", blank ? { href, target: "_blank", rel: "noopener" } : { href }, text);
  const b = (text) => el("b", {}, text);

  function qr(px) {
    if (!demo || !window.DA || !window.DA.qrCanvas) return null;
    const node = window.DA.qrCanvas(demo, px);
    node.className = "tour-qr-img";
    node.setAttribute("role", "img");
    node.setAttribute("aria-label", say("Code QR de la démo : ", "QR code of the demo: ") + demo);
    return node;
  }

  const STEPS = [
    { title: say("Bienvenue dans DynamiteAgile", "Welcome to DynamiteAgile"),
      body: () => [el("p", {}, say("Une plateforme ", "A free, open-source "), b(say("gratuite et open source", "platform")),
        say(" pour développer un produit de l'idée au lancement : besoins, analyse fonctionnelle, essais, sprints, temps.",
          " to develop a product from the idea to the launch: needs, functional analysis, tests, sprints, time.")),
        el("p", {}, say("Ce seul lien vous montre tout, en 6 étapes :", "This single link shows you everything, in 6 steps:")),
        el("ol", { class: "tour-list" }, el("li", {}, say("les pages d'aperçu", "the preview pages")),
          el("li", {}, say("comment l'installer", "how to install it")),
          el("li", {}, b(say("la démo en ligne", "the live demo")), say(", avec son tour guidé dans l'outil", ", with its guided tour in the tool")))] },
    { target: "header.top nav",
      title: say("Les pages d'aperçu", "The preview pages"),
      body: () => [el("p", {}, say("Le menu du haut mène aux autres pages du site. Elles s'ouvrent dans un nouvel onglet ; ce tour vous attend ici.",
        "The top menu leads to the other pages of the site. They open in a new tab; this tour waits for you here.")),
        el("ul", { class: "tour-list" },
          el("li", {}, link("index.html#besoin", say("Accueil", "Home"), true), say(" : le besoin en 4 scènes et la descente dans la mine", ": the need in 4 scenes and the descent into the mine")),
          el("li", {}, link("index.html#journee", say("Une journée avec l'équipe", "A day with the team"), true), say(" : l'outil en action, heure par heure", ": the tool at work, hour by hour")),
          el("li", {}, link("modules.html", "Modules", true), say(" : chaque module, pourquoi et comment", ": each module, why and how")),
          el("li", {}, link("guide.html", "Guide", true), say(" : de MVP 0 au lancement", ": from MVP 0 to launch")),
          el("li", {}, link("versions.html", "Versions", true), say(" : ce qui change à chaque version", ": what each version changes")))] },
    { target: ".wiz-step[data-step=dest]",
      title: say("Où l'outil va tourner", "Where the tool runs"),
      body: () => [el("p", {}, say("Un ", "An "), b(say("serveur en ligne", "online server")),
        say(" (un VPS Linux loué, un gratuit existe) : toute l'équipe s'y connecte de partout. Ou un ", " (a rented Linux VPS, a free one exists): the whole team connects from anywhere. Or a "),
        b(say("PC Windows de l'équipe", "team Windows PC")), say(", sur le réseau local.", ", on the local network.")),
        el("p", { class: "muted" }, say("Aucune connaissance technique requise : un assistant IA peut vous guider, une commande à la fois.",
          "No technical knowledge needed: an AI assistant can guide you, one command at a time."))] },
    { target: ".progress-bar",
      title: say("Cinq étapes, une commande", "Five steps, one command"),
      body: () => [el("p", {}, say("De haut en bas : un serveur, une adresse web, la connexion, puis ", "Top to bottom: a server, a web address, the connection, then "),
        b(say("une seule commande", "a single command")), say(" qui installe tout, avec le certificat HTTPS. Chaque commande se copie d'un clic.",
          " that installs everything, with the HTTPS certificate. Each command copies in one click.")),
        el("p", { class: "muted" }, say("Cochez chaque étape faite : la barre avance et la page s'en souvient.",
          "Tick each step done: the bar moves on and the page remembers it."))] },
    { target: "#exemple",
      title: say("Le Rover, un projet complet", "The Rover, a complete project"),
      body: () => [el("p", {}, say("Chaque installation contient le Space ", "Every installation holds the "), b("DEMO"),
        say(" : un petit véhicule autonome, rempli dans tous les modules de MVP 0 à MVP 3. C'est lui que la démo en ligne vous fait visiter.",
          " Space: a small autonomous robot, filled in every module from MVP 0 to MVP 3. It is the project the live demo walks you through."))] },
    { target: "#demo", final: true,
      title: say("À vous : la démo en ligne", "Your turn: the live demo"),
      body: () => [el("p", {}, say("Ouvrez la plateforme, puis ", "Open the platform, then "), b(say("« Entrer en invité »", "« Enter as guest »")),
        say(" : sans compte ni mot de passe, en lecture seule. Le tour guidé de l'outil démarre tout seul.",
          ": no account, no password, read-only. The tool's guided tour starts by itself.")),
        el("div", { class: "tour-demo" }, qr(150),
          el("div", {}, el("a", { class: "btn btn-primary", href: demo, target: "_blank", rel: "noopener" }, say("Ouvrir la démo ↗", "Open the demo ↗")),
            el("p", { class: "muted" }, say("Sur un téléphone ? Scannez le code avec l'appareil photo.", "On a phone? Scan the code with the camera."))))] },
  ];

  let index = 0, card = null, spot = null, target = null;

  function place() {
    if (!spot) return;
    if (!target) { spot.hidden = true; return; }
    const r = target.getBoundingClientRect(), pad = 8;
    spot.hidden = false;
    Object.assign(spot.style, { top: (r.top + window.scrollY - pad) + "px", left: (r.left + window.scrollX - pad) + "px",
      width: (r.width + 2 * pad) + "px", height: (r.height + 2 * pad) + "px" });
  }

  function close() {
    store.set();
    store.at(null);
    if (card) card.remove();
    if (spot) spot.remove();
    card = spot = target = null;
    document.body.classList.remove("touring");
    window.removeEventListener("resize", place);
    window.removeEventListener("scroll", place);
    document.removeEventListener("keydown", keys);
  }

  function keys(e) {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight" && index < STEPS.length - 1) show(index + 1);
    else if (e.key === "ArrowLeft" && index > 0) show(index - 1);
  }

  function show(i) {
    index = i;
    store.at(i);
    const step = STEPS[i];
    target = step.target ? document.querySelector(step.target) : null;
    if (target && target.closest("details")) target.closest("details").open = true;
    const behavior = matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    if (target) {  // below the sticky top bar, in the part of the screen the card leaves free
      const bar = document.querySelector("header.top");
      const above = bar && !target.closest("header.top") ? bar.getBoundingClientRect().height + 20 : 12;
      const free = (innerWidth <= 640 ? innerHeight * 0.4 : innerHeight) - above;
      const r = target.getBoundingClientRect();
      const top = r.top + scrollY - above - Math.max(0, (free - r.height) / 2);
      window.scrollTo({ top: Math.max(0, top), behavior });
    } else window.scrollTo({ top: 0 });
    card.classList.toggle("centered", !target);
    card.replaceChildren(
      el("button", { type: "button", class: "tour-x", "aria-label": say("Fermer le tour", "Close the tour"), onclick: close }, "×"),
      el("span", { class: "tour-n" }, say("Étape ", "Step ") + (i + 1) + " / " + STEPS.length),
      el("h3", { id: "tour-title" }, step.title), el("div", { class: "tour-body" }, step.body()),
      el("div", { class: "tour-nav" },
        i > 0 ? el("button", { type: "button", class: "btn", onclick: () => show(i - 1) }, say("← Précédent", "← Back")) : el("span"),
        el("span", { class: "tour-dots", "aria-hidden": "true" }, STEPS.map((_s, k) => el("i", { class: k === i ? "on" : "" }))),
        step.final ? el("button", { type: "button", class: "btn btn-primary", onclick: close }, say("Terminer", "Finish"))
          : el("button", { type: "button", class: "btn btn-primary", onclick: () => show(i + 1) }, i === 0 ? say("Commencer →", "Start →") : say("Suivant →", "Next →"))));
    place();
    setTimeout(place, 450);  // after the smooth scroll
    const next = card.querySelector(".tour-nav .btn-primary");
    if (next) next.focus({ preventScroll: true });
  }

  function start(at) {
    if (card) close();
    spot = el("div", { class: "tour-spot", "aria-hidden": "true" });
    card = el("div", { class: "tour-card", role: "dialog", "aria-modal": "false", "aria-labelledby": "tour-title", "data-new": "0.60.70-site-tour" });
    document.body.append(spot, card);
    document.body.classList.add("touring");
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, { passive: true });
    document.addEventListener("keydown", keys);
    show(Math.min(Math.max(Number(at) || 0, 0), STEPS.length - 1));
  }

  /* the QR code of the permanent « live demo » section at the bottom of the page */
  const box = document.getElementById("demo-qr");
  const code = qr(200);
  if (box && code) box.append(code);

  document.querySelectorAll("[data-tour-start]").forEach((btn) => btn.addEventListener("click", () => start(0)));
  const resume = store.step();  // the FR | EN button reloads the page in the other language: same step there
  if (resume != null) setTimeout(() => start(resume), 400);
  else if (!store.get()) setTimeout(() => start(0), 700);
  window.DASiteTour = { start, close };
})();
