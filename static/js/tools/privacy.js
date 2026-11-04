/* Content protection (core lot v0.10, D-B-029), each measure switched on by
   an administrator (Administration -> Confidentialité):
   - named watermark: display name, login, date-time and IP address tiled
     over every page, so a screenshot or a phone photo names its source;
   - print block: the printed page only says « Impression désactivée »;
   - copy / right-click block on the content (input fields stay usable);
   - blur when the window loses the focus (screen-capture tool opened).
   Every attempt (print, copy, context menu, Print Screen key) goes to the
   audit journal. A web page cannot stop an operating-system screenshot:
   these measures deter and trace, they do not replace IT's workstation
   controls (GPO / MDM). */
(function () {
  "use strict";

  let policy = {};
  let user = null;
  let ip = "";
  let watermark = null;
  let lastEvent = {};
  let wired = false;

  function report(kind) {
    const now = Date.now();
    if (now - (lastEvent[kind] || 0) < 3000) return;  // one entry per burst
    lastEvent[kind] = now;
    DA.api.post("/api/privacy/event", { kind, page: location.hash.slice(0, 300) }).catch(() => {});
  }

  function tile() {
    const canvas = document.createElement("canvas");
    canvas.width = 460;
    canvas.height = 260;
    const ctx = canvas.getContext("2d");
    if (!ctx) return "";
    const dark = getComputedStyle(document.body).color;
    ctx.translate(230, 130);
    ctx.rotate(-Math.PI / 7);
    ctx.textAlign = "center";
    ctx.fillStyle = dark;
    ctx.globalAlpha = 0.09;
    ctx.font = "600 17px Segoe UI, sans-serif";
    const stamp = new Date().toLocaleString("fr-CA", { dateStyle: "short", timeStyle: "short" });
    ctx.fillText(user.display_name + " · " + user.username, 0, -12);
    ctx.font = "14px Segoe UI, sans-serif";
    ctx.fillText(stamp + (ip ? " · " + ip : "") + " · confidentiel", 0, 12);
    return canvas.toDataURL("image/png");
  }

  function drawWatermark() {
    if (!policy.watermark || !user) {
      if (watermark) { watermark.remove(); watermark = null; }
      return;
    }
    if (!watermark) {
      watermark = document.createElement("div");
      watermark.className = "pv-watermark";
      watermark.setAttribute("aria-hidden", "true");
      document.body.append(watermark);
    }
    watermark.style.backgroundImage = "url(" + tile() + ")";  // CSSOM: allowed by the CSP
  }

  function editable(target) {
    return target && target.closest && target.closest("input, textarea, select, [contenteditable='true']");
  }

  function wire() {
    if (wired) return;
    wired = true;
    const note = document.createElement("p");
    note.className = "pv-print-note";
    note.textContent = "Impression désactivée par l'administrateur de l'outil. Cette tentative a été journalisée.";
    document.body.append(note);
    window.addEventListener("beforeprint", () => { if (policy.block_print) report("print"); });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "PrintScreen" && (policy.blur_unfocused || policy.watermark)) report("printscreen");
      if (policy.block_print && (ev.ctrlKey || ev.metaKey) && (ev.key === "p" || ev.key === "P")) {
        ev.preventDefault();
        report("print");
        DA.toast("Impression désactivée par l'administrateur.", "error");
      }
    });
    document.addEventListener("copy", (ev) => {
      if (!policy.block_copy || editable(ev.target)) return;
      ev.preventDefault();
      report("copy");
      DA.toast("Copie désactivée par l'administrateur.", "error");
    });
    document.addEventListener("cut", (ev) => { if (policy.block_copy && !editable(ev.target)) ev.preventDefault(); });
    document.addEventListener("contextmenu", (ev) => {
      if (!policy.block_copy || editable(ev.target)) return;
      ev.preventDefault();
      report("context");
    });
    document.addEventListener("dragstart", (ev) => { if (policy.block_copy && !editable(ev.target)) ev.preventDefault(); });
    /* D-B-043: the blur is immediate (no transition) and STAYS until the person clicks « Afficher » --
       getting the focus back (as a capture tool does after 0.5 s) no longer clears it. Triggers: the
       window loses the focus or is hidden, the Windows key (Win+Maj+S) or Impr. écran is pressed. */
    window.addEventListener("blur", () => hide("focus"));
    document.addEventListener("visibilitychange", () => { if (document.hidden) hide("hidden"); });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Meta" || ev.key === "OS" || ev.key === "PrintScreen") hide(ev.key);
    }, true);
    document.addEventListener("keyup", (ev) => { if (ev.key === "PrintScreen") hide(ev.key); }, true);
    setInterval(drawWatermark, 60000);  // the time in the watermark stays current
  }

  let shield = null;
  function hide(reason) {
    if (!policy.blur_unfocused || !user) return;
    const html = document.documentElement;
    if (html.classList.contains("pv-blurred")) return;
    html.classList.add("pv-blurred");
    if (!shield) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-primary pv-show";
      button.textContent = "Afficher le contenu";
      button.addEventListener("click", reveal);
      const text = document.createElement("p");
      text.textContent = "Contenu masqué (confidentialité) : la fenêtre a perdu le focus ou une capture d'écran a été lancée.";
      shield = document.createElement("div");
      shield.className = "pv-shield";
      shield.setAttribute("role", "dialog");
      shield.setAttribute("aria-label", "Contenu masqué");
      shield.append(text, button);
    }
    document.body.append(shield);
    if (reason === "PrintScreen" || reason === "Meta") report("printscreen");
  }
  function reveal() {
    document.documentElement.classList.remove("pv-blurred");
    if (shield) shield.remove();
  }

  /* Called by app.js with /api/me: policy, user (null when signed out), IP. */
  DA.applyPolicy = function (value, who, clientIp) {
    policy = value || {};
    user = who || null;
    ip = clientIp || "";
    const html = document.documentElement;
    const active = !!user;
    html.classList.toggle("pv-noprint", active && !!policy.block_print);
    html.classList.toggle("pv-nocopy", active && !!policy.block_copy);
    html.classList.toggle("pv-blur", active && !!policy.blur_unfocused);
    if (!active || !policy.blur_unfocused) reveal();
    wire();
    drawWatermark();
  };
})();
