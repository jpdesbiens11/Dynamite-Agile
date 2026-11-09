/* 0.60.96 (D-O-102): « show / hide password » button inside a password field, as on most sign-in pages.
   DA.passwordToggle(input) wraps the input with an eye button on its right: the eye while the password is hidden,
   the crossed-out eye while it is shown. type="button" (never submits), aria-label + aria-pressed + aria-controls,
   keyboard reachable with a visible focus; the value, the caret and the selection are kept; every password shown
   is hidden again when its form is submitted; autocomplete is never touched. Icons: constant inline SVG drawn in
   currentColor (no file, no data from the server), so they follow every theme through the CSS tokens. */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const SHOW = "Afficher le mot de passe";
  const HIDE = "Masquer le mot de passe";
  const EYE = [
    ["path", { d: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" }],
    ["circle", { cx: "12", cy: "12", r: "3" }],
  ];
  const EYE_OFF = [
    ["path", { d: "M10.6 5.1A10.6 10.6 0 0 1 12 5c6.4 0 10 7 10 7a17.8 17.8 0 0 1-3.1 4.1" }],
    ["path", { d: "M6.6 6.6C3.9 8.4 2 12 2 12s3.6 7 10 7a9.8 9.8 0 0 0 5.4-1.6" }],
    ["path", { d: "M9.9 9.9a3 3 0 0 0 4.2 4.2" }],
    ["path", { d: "M3 3l18 18" }],
  ];
  let seq = 0;

  function icon(shapes, name) {
    const svg = document.createElementNS(NS, "svg");
    const attrs = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8",
      "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", focusable: "false" };
    Object.keys(attrs).forEach((k) => svg.setAttribute(k, attrs[k]));
    svg.setAttribute("class", "pw-icon pw-icon-" + name);
    shapes.forEach(([tag, a]) => {
      const node = document.createElementNS(NS, tag);
      Object.keys(a).forEach((k) => node.setAttribute(k, a[k]));
      svg.append(node);
    });
    return svg;
  }

  /* Show (true) or hide (false) the password, keeping the caret, the selection and the focus where they were. */
  function setShown(input, button, shown) {
    const focused = document.activeElement === input;
    let start = null;
    let end = null;
    try { start = input.selectionStart; end = input.selectionEnd; } catch (err) { /* not a text input */ }
    input.type = shown ? "text" : "password";
    input.dataset.pwShown = shown ? "1" : "";
    if (focused && start !== null) { try { input.setSelectionRange(start, end); } catch (err) { /* ignored */ } }
    const label = shown ? HIDE : SHOW;
    button.setAttribute("aria-pressed", shown ? "true" : "false");
    button.setAttribute("aria-label", label);
    button.dataset.tip = label;
    const next = shown ? icon(EYE_OFF, "off") : icon(EYE, "eye");
    const old = button.querySelector("svg.pw-icon");  // only the icon: a [new] tag (newtags.js) stays
    if (old) button.replaceChild(next, old); else button.prepend(next);
  }

  DA.passwordToggle = function (input) {
    if (input.parentNode && input.parentNode.classList && input.parentNode.classList.contains("pw-wrap")) {
      return input.parentNode;  // already wrapped
    }
    if (!input.id) { seq += 1; input.id = "da-pw-" + seq; }
    const button = DA.el("button", { type: "button", class: "pw-toggle", "aria-controls": input.id,
      "data-new": "0.60.96-password-toggle" });
    const wrap = DA.el("span", { class: "pw-wrap" });
    if (input.parentNode) input.parentNode.insertBefore(wrap, input);
    wrap.append(input, button);
    /* a mouse click keeps the caret in the field (the keyboard path keeps the focus on the button) */
    button.addEventListener("mousedown", (ev) => { if (document.activeElement === input) ev.preventDefault(); });
    button.addEventListener("click", () => setShown(input, button, input.type === "password"));
    input._pwToggle = (shown) => setShown(input, button, shown);
    setShown(input, button, false);
    /* once field() has put the wrap in its <label>: name the input by the label text only, so that screen readers
       do not read the button's « Afficher le mot de passe » as part of the field's name */
    queueMicrotask(() => {
      const text = wrap.closest("label") && wrap.closest("label").querySelector(":scope > .field-label");
      if (!text || input.hasAttribute("aria-label") || input.hasAttribute("aria-labelledby")) return;
      if (!text.id) text.id = input.id + "-label";
      input.setAttribute("aria-labelledby", text.id);
    });
    return wrap;
  };

  /* Every password shown is hidden again when its form is submitted (capture: before the form's own handler). */
  document.addEventListener("submit", (ev) => {
    const form = ev.target;
    if (!form || !form.querySelectorAll) return;
    form.querySelectorAll("input[data-pw-shown='1']").forEach((input) => input._pwToggle && input._pwToggle(false));
  }, true);
})();
