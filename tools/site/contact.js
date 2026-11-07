/* The contact form of the website (0.60.74, D-O-080): it posts to the public demo of the tool (data-demo of <body>),
   which forwards the request by e-mail; the recipient's address is never in the page. A hidden field (« website »)
   catches robots. French and English from the language of the page. */
(function () {
  "use strict";
  const form = document.getElementById("contact-form");
  if (!form) return;
  const EN = document.documentElement.lang === "en";
  const say = (fr, en) => (EN ? en : fr);
  const status = form.querySelector(".contact-status");
  const button = form.querySelector("button[type=submit]");

  function show(text, ok) {
    status.textContent = text;
    status.className = "contact-status note " + (ok ? "ok" : "warn");
    status.hidden = false;
  }

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!form.reportValidity()) return;
    const demo = (document.body.dataset.demo || "").replace(/\/?$/, "/");
    const data = Object.fromEntries(new FormData(form).entries());
    data.lang = EN ? "en" : "fr";
    button.disabled = true;
    button.textContent = say("Envoi…", "Sending…");
    try {
      const res = await fetch(demo + "api/contact", { method: "POST", mode: "cors", credentials: "omit",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || say("Envoi impossible pour l'instant.", "Could not send for now."));
      form.reset();
      show(body.message, true);
    } catch (err) {
      show((err && err.message && err.message !== "Failed to fetch" ? err.message
        : say("Le serveur ne répond pas.", "The server does not answer.")) + " " +
        say("Réessayez plus tard.", "Try again later."), false);
    } finally {
      button.disabled = false;
      button.textContent = say("Envoyer la demande", "Send the request");
    }
  });
})();
