/* « Partager » (0.60.29, D-O-038; 0.60.30: solid on a computer): share the page one is looking at with a classmate,
   outside the tool too -- the @mention points a member to something inside Dynamite | Agile; this sends the link where
   people already talk.
   - On a phone (and every browser that has it), the system share sheet: texto, Messenger, WhatsApp, courriel, Teams…
     all the apps of the device, with the page title and, if some text is selected, that text as a quote.
   - Elsewhere, a dialog. The link is copied first, on every choice: if an app does not open (a computer without an
     app for texto, Messenger in a browser…), it is ready to paste. Courriel: the default mail app (mailto:), Gmail,
     Outlook on the web. Messages: WhatsApp, Telegram, Teams (their web pages work on any computer); Messenger: the app
     on a phone, messenger.com on a computer; Texto: the phone app, on a computer the QR code. The QR code carries the
     page to the phone (scan, then share from the phone); « Autres applications » when the system has its sheet.
   Nothing leaves the page by itself: each choice opens the person's own app or site, nothing is sent from here.
   The link opens for a member of the Space only (an account is needed). Button in the top bar (topbarTools) and, on a
   phone, beside the ☰ menu (mobile.js). */
(function () {
  "use strict";
  const { el, toast } = DA;

  function what() {
    // the page's own name: its title, else its breadcrumb (« Projet d'équipe / Requirements et needs »), else the tab
    const clean = (node) => (node ? node.textContent : "").replace(/\[new\]/g, "").replace(/\s+/g, " ").trim();
    const crumbs = document.querySelector("#main .ag-crumbs");
    const title = clean(document.querySelector("#main .dy-page-title, #main h1")) || clean(crumbs).replace(/\s*\/\s*/g, " / ")
      || clean(document.querySelector(".tab.active")) || "Dynamite | Agile";
    const picked = String(window.getSelection ? window.getSelection() : "").trim().slice(0, 400);
    const text = (picked ? "« " + picked + " »\n" : "") + title + " — Dynamite | Agile";
    // 0.60.35 (D-O-043): a selected passage becomes the point of interest -- the link opens the page and shows it
    const url = picked && DA.pointLink ? DA.pointLink(picked.slice(0, 120)) : location.href;
    return { title, text, url, subject: title + " — Dynamite | Agile" };
  }

  const enc = encodeURIComponent;
  const onPhone = () => (DA.phone && DA.phone()) || window.matchMedia("(pointer: coarse)").matches;

  /* [group, label, address(w, phone) -> url, or null for « show the QR code »] */
  const WAYS = [
    ["Courriel", "Application de courriel", (w) => "mailto:?subject=" + enc(w.subject) + "&body=" + enc(w.text + "\n\n" + w.url)],
    ["Courriel", "Gmail", (w) => "https://mail.google.com/mail/?view=cm&fs=1&su=" + enc(w.subject) + "&body=" + enc(w.text + "\n\n" + w.url)],
    ["Courriel", "Outlook (web)", (w) => "https://outlook.office.com/mail/deeplink/compose?subject=" + enc(w.subject) + "&body=" + enc(w.text + "\n\n" + w.url)],
    ["Messages", "Texto", (w, phone) => (phone ? "sms:?&body=" + enc(w.text + " " + w.url) : null)],
    ["Messages", "Messenger", (w, phone) => (phone ? "fb-messenger://share/?link=" + enc(w.url) : "https://www.messenger.com/")],
    ["Messages", "WhatsApp", (w) => "https://wa.me/?text=" + enc(w.text + " " + w.url)],
    ["Messages", "Telegram", (w) => "https://t.me/share/url?url=" + enc(w.url) + "&text=" + enc(w.text)],
    ["Messages", "Teams", (w) => "https://teams.microsoft.com/share?href=" + enc(w.url) + "&msgText=" + enc(w.text)],
  ];

  /* the link in the clipboard, quietly: the Clipboard API (https), else the old copy of a selected field (plain http) */
  async function copy(url) {
    try {
      await navigator.clipboard.writeText(url);
      return true;
    } catch (err) {
      const field = el("textarea", { class: "sh-hidden", readonly: true }, url);
      document.body.append(field);
      field.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      field.remove();
      return ok;
    }
  }

  async function system(w) {
    try { await navigator.share({ title: w.title, text: w.text, url: w.url }); return true; } catch (err) { return err && err.name === "AbortError"; }
  }

  function open(url) {
    if (/^https:/.test(url)) window.open(url, "_blank", "noopener");
    else window.location.href = url;  // mailto:, sms:, fb-messenger: -- the app of the device, the page stays
  }

  function qrBox(w) {
    const box = el("div", { class: "sh-qr", "data-new": "0.60.30-share-qr" });
    try {
      box.append(DA.qrCanvas(w.url, 180));
    } catch (err) {
      box.append(el("p", { class: "muted" }, "Lien trop long pour un code QR : copiez-le."));
    }
    box.append(el("p", { class: "muted sh-qr-note" }, "Vers mon téléphone : visez ce code avec l'appareil photo, ouvrez le "
      + "lien, puis touchez Partager (texto, Messenger…)."));
    return box;
  }

  function dialog(w) {
    const phone = onPhone();
    const field = el("input", { type: "text", readonly: true, value: w.url, class: "sh-url", "aria-label": "Lien de la page",
      onfocus: (ev) => ev.target.select() });
    let close = null;
    const qr = phone ? null : qrBox(w);  // on a computer, always beside the choices: the way to the phone
    const showQr = () => { if (!qr) return; qr.classList.remove("sh-qr-flash"); void qr.offsetWidth; qr.classList.add("sh-qr-flash"); };
    const choose = async (label, url) => {
      const copied = await copy(w.url);
      if (url === null) {
        showQr();
        toast((copied ? "Lien copié. " : "") + "Un ordinateur n'envoie pas de texto : scannez le code QR à droite avec votre téléphone.", "info");
        return;
      }
      open(url);
      toast(copied ? "Lien copié aussi : si " + label + " ne s'ouvre pas, collez-le (Ctrl+V) dans le message."
        : label + " s'ouvre ; sinon, copiez le lien ci-dessus.", "success");
      if (!/^https:/.test(url)) setTimeout(() => close && close(), 300);
    };
    const groups = [...new Set(WAYS.map((x) => x[0]))];
    const ways = el("div", { class: "sh-groups" }, groups.map((g) => el("div", { class: "sh-group" },
      el("p", { class: "sh-group-name" }, g),
      el("div", { class: "sh-ways", role: "group", "aria-label": g },
        WAYS.filter((x) => x[0] === g).map(([, label, address]) => el("button", { type: "button", class: "btn sh-way",
          "data-tip": address(w, phone) === null ? "Sur un ordinateur : le code QR passe la page au téléphone" : null,
          onclick: () => choose(label, address(w, phone)) }, label))))));
    const others = el("div", { class: "sh-ways" },
      navigator.share ? el("button", { type: "button", class: "btn sh-way", onclick: async () => { if (await system(w)) close(); } },
        "Autres applications…") : null);
    const body = el("div", { class: "sh-box", "data-new": "0.60.29-share" },
      el("p", { class: "sh-title" }, w.title),
      el("div", { class: "sh-row" }, field, el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
        if (await copy(w.url)) {
          toast("Lien copié : collez-le où vous voulez (il faut un compte du Space pour l'ouvrir).", "success");
          close();
        } else { field.focus(); field.select(); toast("Copiez le lien avec Ctrl+C.", "info"); }
      } }, "Copier le lien")),
      el("div", { class: "sh-cols" }, el("div", null, ways, others), qr),
      el("p", { class: "muted sh-note" }, "Chaque choix copie aussi le lien : si une application ne s'ouvre pas sur cet appareil, "
        + "collez-le. Le lien ouvre la page pour un membre du Space (un compte est nécessaire) ; dans l'outil même, écrivez "
        + "@son nom dans un commentaire ou une page."));
    close = DA.modal("Partager cette page", body);
    const box = body.closest(".modal");
    if (box) box.classList.add("sh-modal");
    field.focus();
    field.select();
  }

  /* opts.direct: go straight to the system sheet when there is one (phones) */
  async function share(opts) {
    const w = what();
    if ((opts || {}).direct && navigator.share && await system(w)) return;
    dialog(w);
  }

  function button(where) {
    const phone = where === "phone";
    return el("button", { type: "button", class: phone ? "tb-share tb-share-phone" : "tb-share", "data-new": "0.60.29-share",
      "aria-label": "Partager cette page", "data-tip": "Partager cette page : lien, courriel, texto, Messenger, code QR…",
      onclick: (ev) => { ev.stopPropagation(); share({ direct: phone || (DA.phone && DA.phone()) }); } },
    DA.icon ? DA.icon("share") : null, el("span", { class: "tb-share-label" }, "Partager"));
  }

  const topbarButton = () => button("bar");
  topbarButton.order = 45;
  DA.topbarTools = DA.topbarTools || [];
  DA.topbarTools.push(topbarButton);
  DA.share = share;
  DA.shareButton = button;
  DA.shareWays = WAYS;
})();
