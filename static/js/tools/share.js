/* « Partager » (0.60.29, D-O-038): share the page one is looking at with a classmate, outside the tool too -- the
   @mention points a member to something inside Dynamite | Agile; this sends the link where people already talk.
   - On a phone (and every browser that has it), the system share sheet: texto, Messenger, WhatsApp, courriel, Teams…
     all the apps of the device, with the page title and, if some text is selected, that text as a quote.
   - Elsewhere, a small dialog: copy the link, courriel (mailto:), texto (sms:), Messenger, WhatsApp, Teams, and
     « Autres applications » when the system sheet exists.
   Nothing leaves the page by itself: each choice opens the person's own app with the link, nothing is sent from here.
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
    return { title, text, url: location.href };
  }

  const enc = encodeURIComponent;
  /* the usual ways of sharing; each opens the person's own app (no request from this page) */
  const WAYS = [
    ["Courriel", (w) => "mailto:?subject=" + enc(w.title + " — Dynamite | Agile") + "&body=" + enc(w.text + "\n\n" + w.url)],
    ["Texto", (w) => "sms:?&body=" + enc(w.text + " " + w.url)],
    ["Messenger", (w) => "fb-messenger://share/?link=" + enc(w.url)],
    ["WhatsApp", (w) => "https://wa.me/?text=" + enc(w.text + " " + w.url)],
    ["Teams", (w) => "https://teams.microsoft.com/share?href=" + enc(w.url) + "&msgText=" + enc(w.text)],
  ];

  async function copy(url) {
    try {
      await navigator.clipboard.writeText(url);
    } catch (err) {  // no clipboard (plain http, old browser): the field stays selected for Ctrl+C
      return false;
    }
    toast("Lien copié : collez-le où vous voulez (il faut un compte du Space pour l'ouvrir).", "success");
    return true;
  }

  async function system(w) {
    try { await navigator.share({ title: w.title, text: w.text, url: w.url }); return true; } catch (err) { return err && err.name === "AbortError"; }
  }

  function dialog(w) {
    const field = el("input", { type: "text", readonly: true, value: w.url, class: "sh-url", "aria-label": "Lien de la page",
      onfocus: (ev) => ev.target.select() });
    let close = null;
    const body = el("div", { class: "sh-box", "data-new": "0.60.29-share" },
      el("p", { class: "sh-title" }, w.title),
      el("div", { class: "sh-row" }, field, el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
        if (await copy(w.url)) close(); else { field.focus(); field.select(); toast("Copiez le lien avec Ctrl+C.", "info"); }
      } }, "Copier le lien")),
      el("div", { class: "sh-ways", role: "group", "aria-label": "Partager avec" },
        WAYS.map(([label, href]) => el("a", { class: "btn sh-way", href: href(w), target: /^https:/.test(href(w)) ? "_blank" : null,
          rel: "noopener noreferrer", onclick: () => setTimeout(() => close && close(), 50) }, label)),
        navigator.share ? el("button", { type: "button", class: "btn sh-way", onclick: async () => { if (await system(w)) close(); } },
          "Autres applications…") : null),
      el("p", { class: "muted sh-note" }, "Le lien ouvre cette page pour un membre du Space (un compte est nécessaire). Pour "
        + "pointer un coéquipier dans l'outil même, écrivez @son nom dans un commentaire ou une page."));
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
      "aria-label": "Partager cette page", "data-tip": "Partager cette page : lien, courriel, texto, Messenger…",
      onclick: (ev) => { ev.stopPropagation(); share({ direct: phone || (DA.phone && DA.phone()) }); } },
    DA.icon ? DA.icon("share") : null, el("span", { class: "tb-share-label" }, "Partager"));
  }

  const topbarButton = () => button("bar");
  topbarButton.order = 45;
  DA.topbarTools = DA.topbarTools || [];
  DA.topbarTools.push(topbarButton);
  DA.share = share;
  DA.shareButton = button;
})();
