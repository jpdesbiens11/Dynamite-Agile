/* 0.60.63 (D-O-072): guest access -- « Entrer en invité » on the sign-in page and the read-only band.
   The server decides everything (core/guest.py): this file only shows the way in and says what a guest can do. */
(function () {
  "use strict";
  const { api, el } = DA;
  const SITE = "https://jpdesbiens11.github.io/Dynamite-Agile/";

  /** The guest entry of the sign-in card: empty until the server says guest access is open (asked each time the
      sign-in page is drawn, so it follows Admin → Accès invité without reloading the page). */
  DA.guestEntry = function (about, onSignedIn) {
    const box = el("div", { class: "guest-entry", "data-new": "0.60.63-guest", hidden: true });
    const error = el("p", { class: "form-error", role: "alert" });
    const button = el("button", { type: "button", class: "btn btn-block guest-enter" }, "Entrer en invité (lecture seule) · Enter as guest");
    button.addEventListener("click", async () => {
      error.textContent = "";
      button.disabled = true;
      try {
        await onSignedIn(await api.post("/api/login/guest"));
      } catch (err) {
        error.textContent = err.message;
      } finally {
        button.disabled = false;
      }
    });
    box.append(el("p", { class: "guest-or" }, el("span", null, "ou")), button,
      el("p", { class: "auth-note" }, "Sans compte ni mot de passe : visitez la démo complète, sans rien pouvoir modifier."), error);
    const show = (open) => { box.hidden = !open; if (about) about.guest = !!open; };
    show(about && about.guest);
    api.get("/api/about").then((fresh) => show(fresh && fresh.guest)).catch(() => { /* keep what we had */ });
    return box;
  };

  /** The band under the top bar while a guest is signed in. */
  DA.guestBanner = function () {
    const user = DA.session && DA.session.user;
    if (!user || !user.is_guest) return null;
    const en = DA.lang() === "en";
    if (DA.guestTour) setTimeout(DA.guestTour.resume, 0);  // 0.60.66 (D-O-074): first visit → the guided tour
    return el("div", { class: "guest-band", role: "note", "data-new": "0.60.63-guest", "data-no-i18n": "" },
      el("strong", null, en ? "Guest mode — read-only. " : "Mode invité — lecture seule. "),
      en ? "You are visiting the demo: everything can be viewed and exported, nothing can be changed. "
        : "Vous visitez la démo : tout se consulte et s'exporte, rien ne se modifie. ",
      DA.guestTour ? el("button", { type: "button", class: "btn btn-small btn-primary guest-tour-btn", "data-new": "0.60.66-guest-tour",
        onclick: () => DA.guestTour.start(0) }, en ? "▶ Guided tour" : "▶ Tour guidé") : null, " ",
      el("a", { href: SITE + (en ? "en/" : "") + "installation.html", target: "_blank", rel: "noopener" },
        en ? "Install Dynamite | Agile for your team (free)" : "Installer Dynamite | Agile pour votre équipe (gratuit)"));
  };
})();
