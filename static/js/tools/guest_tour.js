/* The guest's guided tour (0.60.66, D-O-074): a card at the bottom right that walks a visitor through the Rover
   project, one step per artefact (steps in guest_tour_steps.js). Each step opens its page and points at the artefact
   with « le pointeur » (DA.pointTo). First step: choose Français | English (kept in this browser, prefs.js).
   Starts by itself the first time a guest enters in this browser; « ▶ Tour guidé » in the guest band restarts it.
   The card is never translated by the display dictionary (data-no-i18n): it carries its own French and English. */
(function () {
  "use strict";
  const { el } = DA;
  const SEEN = "da.tour.seen", AT = "da.tour.step";
  const SITE = "https://jpdesbiens11.github.io/Dynamite-Agile/";  // the project's website (a link to open, not a resource)
  const store = {
    get(k) { try { return sessionStorage.getItem(k) || localStorage.getItem(k); } catch (err) { return null; } },
    set(k, v, local) { try { (local ? localStorage : sessionStorage).setItem(k, v); } catch (err) { /* private window */ } },
    del(k) { try { sessionStorage.removeItem(k); } catch (err) { /* ignored */ } },
  };
  let card = null, index = 0;

  const steps = () => DA.guestTourSteps || [];
  const en = () => DA.lang && DA.lang() === "en";
  const say = (fr, english) => (en() ? english : fr);

  function close() {
    if (card) card.remove();
    card = null;
    store.del(AT);
    if (DA.pointer) DA.pointer.close();
  }

  async function language(value) {
    if (DA.lang() !== value) await DA.savePrefs({ language: value });
    draw();
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }

  function go(i) {
    const list = steps();
    index = Math.max(0, Math.min(list.length - 1, i));
    store.set(AT, String(index));
    const step = list[index];
    draw();
    if (DA.pointer) DA.pointer.close();
    if (step.hash && location.hash !== step.hash) location.hash = step.hash;
    if (step.focus && DA.pointTo) setTimeout(() => { if (card && index === list.indexOf(step)) DA.pointTo(step.focus); }, 700);
  }

  function draw() {
    const list = steps();
    const step = list[index];
    if (!step) return;
    const [title, text] = en() ? step.en : step.fr;
    const last = index === list.length - 1;
    const body = el("div", { class: "gt-card", role: "dialog", "aria-live": "polite", "data-no-i18n": "",
      "aria-label": say("Tour guidé", "Guided tour"), "data-new": "0.60.66-guest-tour" },
      el("div", { class: "gt-head" },
        el("span", { class: "gt-count" }, say("Tour guidé", "Guided tour") + " · " + (index + 1) + " / " + list.length),
        el("button", { type: "button", class: "gt-close", "aria-label": say("Fermer le tour", "Close the tour"), onclick: close }, "×")),
      el("div", { class: "gt-bar" }, el("i", { class: "gt-fill" })),
      el("h2", { class: "gt-title" }, title),
      el("p", { class: "gt-text" }, text),
      index === 0 ? el("div", { class: "gt-lang", role: "group", "aria-label": "Langue · Language" },
        el("button", { type: "button", class: "btn btn-small" + (en() ? "" : " btn-primary"), lang: "fr", onclick: () => language("fr") }, "Français"),
        el("button", { type: "button", class: "btn btn-small" + (en() ? " btn-primary" : ""), lang: "en", onclick: () => language("en") }, "English")) : null,
      last ? el("div", { class: "gt-links" },
        el("a", { class: "btn btn-small btn-primary", href: SITE + (en() ? "en/" : "") + "installation.html",
          target: "_blank", rel: "noopener" }, say("Installer pour mon équipe", "Install for my team")),
        el("a", { class: "btn btn-small", href: "/apps/vitrine/index.html", target: "_blank", rel: "noopener" }, say("La vitrine", "The showcase"))) : null,
      el("div", { class: "gt-nav" },
        el("button", { type: "button", class: "btn btn-small", disabled: index === 0, onclick: () => go(index - 1) }, say("◀ Précédent", "◀ Back")),
        el("button", { type: "button", class: "btn btn-small", onclick: () => go(index) }, say("Montrer", "Show me")),
        last ? el("button", { type: "button", class: "btn btn-small btn-primary", onclick: close }, say("Terminer", "Finish"))
          : el("button", { type: "button", class: "btn btn-small btn-primary", onclick: () => go(index + 1) }, say("Suivant ▶", "Next ▶"))));
    body.querySelector(".gt-fill").style.width = Math.round(((index + 1) / list.length) * 100) + "%";
    if (card) card.replaceWith(body); else document.body.append(body);
    card = body;
  }

  window.addEventListener("da:language", () => { if (card) draw(); });  // 0.60.67: the top bar FR | EN switches the card too

  DA.guestTour = {
    start(i) { store.set(SEEN, "1", true); go(i || 0); },
    close,
    /** called with the guest band: first visit in this browser → the tour starts; a reload keeps the current step */
    resume() {
      if (card || !DA.session || !DA.session.user || !DA.session.user.is_guest) return;
      const at = store.get(AT);
      if (at !== null && sessionStorage.getItem(AT) !== null) { index = Number(at) || 0; draw(); return; }
      if (!store.get(SEEN)) setTimeout(() => DA.guestTour.start(0), 600);
    },
  };
})();
