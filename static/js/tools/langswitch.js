/* FR | EN in the top bar (0.60.48, D-O-057): one click switches the interface language, like the website -- no detour
   through Paramètres. The choice is saved in the account's settings (all devices) and the page is drawn again in place.
   The frame of the tool (top bar, menus, Dashboard, Paramètres, members) is translated; module screens follow (D-O-017). */
(function () {
  "use strict";
  const { el } = DA;

  function button() {
    const other = DA.lang() === "en" ? "fr" : "en";
    return el("button", { type: "button", class: "tb-lang", lang: other, "data-new": "0.60.48-lang-switch",
      "aria-label": other === "en" ? "Switch to English" : "Passer au français",
      "data-tip": other === "en" ? "English interface" : "Interface en français",
      onclick: async (ev) => {
        ev.stopPropagation();
        try {
          await DA.savePrefs({ language: other });
          window.dispatchEvent(new HashChangeEvent("hashchange"));  // the same page, drawn again in the new language
        } catch (err) { DA.toast(err.message, "error"); }
      } }, other.toUpperCase());
  }

  button.order = 44;  // just before « Partager »
  DA.topbarTools = DA.topbarTools || [];
  DA.topbarTools.push(button);
})();
