/* 0.60.96 (D-O-102): the eye button of a password field (static/js/tools/password_toggle.js), run on a tiny fake DOM.
     node tests/js/password_toggle.js   (prints "password_toggle OK" or the failures) */
const fs = require("fs"), vm = require("vm"), path = require("path");

class Node {
  constructor(tag) {
    this.tagName = tag.toUpperCase(); this.attrs = {}; this.children = []; this.parentNode = null;
    this.dataset = {}; this.listeners = {}; this.classList = { contains: (c) => (this.attrs.class || "").split(" ").includes(c) };
  }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === "id") this.id = String(v); if (k === "type") this._type = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  get type() { return this._type; }
  set type(v) { this._type = v; this.attrs.type = v; }
  get firstChild() { return this.children[0] || null; }
  _adopt(n) { if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; return n; }
  append(...ns) { ns.forEach((n) => this.children.push(this._adopt(n))); }
  prepend(n) { this.children.unshift(this._adopt(n)); }
  removeChild(n) { this.children.splice(this.children.indexOf(n), 1); n.parentNode = null; }
  insertBefore(n, ref) { this._adopt(n); this.children.splice(this.children.indexOf(ref), 0, n); }
  replaceChild(n, old) { this._adopt(n); this.children[this.children.indexOf(old)] = n; old.parentNode = null; }
  all() { return this.children.flatMap((c) => [c, ...c.all()]); }
  matches(sel) {  // the few selectors the helper uses
    if (sel === "svg.pw-icon") return this.tagName === "SVG" && this.classList.contains("pw-icon");
    if (sel === ":scope > .field-label") return this.classList.contains("field-label");
    if (sel === "input[data-pw-shown='1']") return this.tagName === "INPUT" && this.dataset.pwShown === "1";
    return false;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  querySelectorAll(sel) {
    return sel.startsWith(":scope") ? this.children.filter((c) => c.matches(sel)) : this.all().filter((c) => c.matches(sel));
  }
  closest(tag) { let n = this; while (n && n.tagName !== tag.toUpperCase()) n = n.parentNode; return n; }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  fire(type, ev) { (this.listeners[type] || []).forEach((fn) => fn(Object.assign({ target: this, preventDefault() { ev && (ev.prevented = true); } }, ev))); }
  focus() { doc.activeElement = this; }
  setSelectionRange(a, b) { this.selectionStart = a; this.selectionEnd = b; }
}
const doc = new Node("document");
doc.createElementNS = (ns, tag) => new Node(tag);
doc.activeElement = null;
const el = (tag, attrs, ...kids) => {
  const n = new Node(tag);
  Object.keys(attrs || {}).forEach((k) => n.setAttribute(k, attrs[k]));
  kids.flat().forEach((k) => { if (typeof k === "string") n.textContent = k; else if (k) n.append(k); });
  return n;
};
const sandbox = { console, document: doc, queueMicrotask, DA: { el } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "static/js/tools/password_toggle.js"), "utf8"), sandbox);

const failures = [];
const check = (name, ok, got) => { if (!ok) failures.push(name + " -> " + JSON.stringify(got)); };
const iconOf = (b) => b.querySelector("svg.pw-icon").attrs.class;

(async () => {
  // 1. the login field: wrapped, the button names its field, hidden by default with the eye
  const input = el("input", { type: "password", autocomplete: "current-password" });
  input.value = "s3cret";
  const wrap = sandbox.DA.passwordToggle(input);
  const form = el("form", null, el("label", { class: "field" }, el("span", { class: "field-label" }, "Mot de passe"), wrap));
  const button = wrap.children[1];
  check("wrap", wrap.attrs.class === "pw-wrap" && wrap.children[0] === input, wrap.attrs);
  check("button type", button.attrs.type === "button", button.attrs);
  check("aria-controls", button.attrs["aria-controls"] === input.id && input.id, [button.attrs, input.id]);
  check("hidden first", input.type === "password" && button.attrs["aria-pressed"] === "false"
    && button.attrs["aria-label"] === "Afficher le mot de passe" && iconOf(button).includes("pw-icon-eye"), button.attrs);
  check("data-new", button.attrs["data-new"] === "0.60.96-password-toggle", button.attrs);
  check("svg decorative", button.querySelector("svg.pw-icon").attrs["aria-hidden"] === "true", button.children[0].attrs);
  await null;
  check("input named by its label only", input.attrs["aria-labelledby"] === input.id + "-label", input.attrs);

  // 2. click: shown with the crossed-out eye, value, caret and autocomplete kept
  input.focus(); input.setSelectionRange(2, 4);
  button.fire("click");
  check("shown", input.type === "text" && button.attrs["aria-pressed"] === "true"
    && button.attrs["aria-label"] === "Masquer le mot de passe" && iconOf(button).includes("pw-icon-off"), button.attrs);
  check("value kept", input.value === "s3cret", input.value);
  check("caret kept", input.selectionStart === 2 && input.selectionEnd === 4, [input.selectionStart, input.selectionEnd]);
  check("autocomplete kept", input.attrs.autocomplete === "current-password", input.attrs);
  check("one icon", button.children.filter((c) => c.tagName === "SVG").length === 1, button.children.length);

  // 3. a [new] tag added by newtags.js stays when the icon changes
  const tag = el("span", { class: "new-tag" }); button.append(tag);
  button.fire("click");
  check("tag kept", button.children.includes(tag) && input.type === "password", button.children.map((c) => c.tagName));

  // 4. a mouse press keeps the caret in the field
  const ev = {}; input.focus(); button.fire("mousedown", ev);
  check("mousedown keeps focus", ev.prevented === true, ev);

  // 5. submitting the form hides every password shown
  button.fire("click");
  check("shown before submit", input.type === "text", input.type);
  doc.fire("submit", { target: form });
  check("hidden on submit", input.type === "password" && button.attrs["aria-pressed"] === "false", input.type);

  // 6. wrapping twice is harmless; an input already in the page is wrapped in place
  check("idempotent", sandbox.DA.passwordToggle(input) === wrap, null);
  const host = el("div"); const lone = el("input", { type: "password", "aria-label": "Phrase secrète" }); host.append(lone);
  const w2 = sandbox.DA.passwordToggle(lone);
  await null;
  check("in place", host.children[0] === w2 && w2.children[0] === lone, host.children.map((c) => c.attrs.class));
  check("own aria-label kept", lone.attrs["aria-label"] === "Phrase secrète" && !lone.attrs["aria-labelledby"], lone.attrs);

  if (failures.length) { console.log("password_toggle FAILED\n  " + failures.join("\n  ")); process.exit(1); }
  console.log("password_toggle OK");
})();
