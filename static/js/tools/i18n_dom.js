/* FR | EN everywhere (0.60.66, D-O-073): the display dictionary. The frame of the tool is translated with DA.t()
   keys (i18n.js); the screens of the modules are written in French, so in English this file translates on screen the
   French labels it knows -- text nodes and the placeholder / title / aria-label / alt / data-tip attributes -- from the
   dictionary static/i18n/en_*.json (built by tools/i18n_build.py from the strings of static/js). Loaded only when the
   language is English; nothing changes for a French interface. Back to French: every node translated is restored.
   Never touched: what people type or wrote (inputs, textarea, contenteditable, code, the wiki page body), and anything
   inside [data-no-i18n]. A label not in the dictionary stays in French until the dictionary learns it. */
(function () {
  "use strict";
  const FILES = 6;
  const ATTRS = ["placeholder", "title", "aria-label", "alt", "data-tip"];
  /* 0.60.67: the content shown in reading (wiki pages, tickets, Diamond…) is translated too when the dictionary knows it
     exactly -- the demo Rover is in static/i18n/demo_en_*.json; what is being edited (contenteditable) never is. */
  const SKIP = "script, style, textarea, code, pre, input, select option[data-raw], [contenteditable], [data-no-i18n]";
  const SKIP_ATTR = "[contenteditable], [data-no-i18n]";  // a field's placeholder is a label
  const DEMO_FILES = 6;
  const guest = () => !!(DA.session && DA.session.user && DA.session.user.is_guest);
  const norm = (s) => s.replace(/\s+/g, " ").trim();
  let dict = null, heads = [], loading = null, observer = null, on = false;
  const done = new Map();  // text node -> [French original, English shown]
  const doneAttr = [];     // [element, attribute, French original]

  function load() {
    if (dict) return Promise.resolve(dict);
    if (!loading) {
      const parts = [];
      const get = (name) => fetch("/i18n/" + name, { credentials: "same-origin" }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
      for (let n = 1; n <= FILES; n += 1) parts.push(get("en_" + n + ".json"));
      for (let n = 1; n <= DEMO_FILES; n += 1) parts.push(get("demo_en_" + n + ".json"));
      loading = Promise.all(parts).then((list) => {
        dict = new Map();
        list.forEach((part) => Object.keys(part).forEach((fr) => { if (part[fr] && norm(fr)) dict.set(norm(fr), part[fr]); }));
        /* a label followed by a value in the same text node (« Semaine du 2 novembre ») is matched by its head */
        heads = Array.from(dict.keys()).filter((k) => k.length >= 4 && /[:—·]$|\s(du|de|des|le|la|les|au|à|pour|par|sur)$/i.test(k))
          .sort((a, b) => b.length - a.length);
        return dict;
      });
    }
    return loading;
  }

  function translate(text) {
    const key = norm(text);
    if (!key || !/[A-Za-zÀ-ÿ]/.test(key)) return null;
    const lead = text.match(/^\s*/)[0], trail = text.match(/\s*$/)[0];
    const hit = dict.get(key);
    if (hit) return lead + norm(hit) + trail;
    /* « ▤ Tous les Spaces », « Exporter ▾ », « ⇩ Exporter… »: a symbol before, an ellipsis or arrow after */
    const parts = key.match(/^([^A-Za-zÀ-ÿ0-9«“]*)(.+?)(\s*[▾›»:…]*)$/);
    if (parts && (parts[1] || parts[3])) {
      const core = dict.get(norm(parts[2])) || dict.get(norm(parts[2] + parts[3]));
      if (core) return lead + parts[1] + norm(core) + (dict.get(norm(parts[2])) ? parts[3] : "") + trail;
    }
    for (const head of heads) {
      if (key.startsWith(head + " ") || (key.startsWith(head) && key.length > head.length && /\s/.test(key[head.length]))) {
        return lead + norm(dict.get(head)) + key.slice(head.length) + trail;
      }
    }
    return null;
  }

  function skipped(node) {
    const host = node.nodeType === 1 ? node : node.parentElement;
    return !host || !!host.closest(SKIP);
  }

  function textNode(node) {
    if (done.has(node) || skipped(node)) return;
    const english = translate(node.nodeValue);
    if (english !== null && english !== node.nodeValue) { done.set(node, [node.nodeValue, english]); node.nodeValue = english; }
  }

  function element(node) {
    if (node.closest(SKIP_ATTR)) return;
    /* a guest only reads: the demo's fields show their English text too (nothing he sees can be saved) */
    if ((node.tagName === "INPUT" && /^(text|search|)$/.test(node.type || "")) || node.tagName === "TEXTAREA") {
      if (guest() && node.value && !node.hasAttribute("data-i18n-value")) {
        const english = translate(node.value);
        if (english !== null && english !== node.value) {
          doneAttr.push([node, "value", node.value]);
          node.setAttribute("data-i18n-value", "");
          node.value = english;
        }
      }
    }
    ATTRS.forEach((name) => {
      const value = node.getAttribute(name);
      if (!value || node.hasAttribute("data-i18n-" + name)) return;
      const english = translate(value);
      if (english === null || english === value) return;
      doneAttr.push([node, name, value]);
      node.setAttribute("data-i18n-" + name, "");
      node.setAttribute(name, english);
    });
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { textNode(root); return; }
    if (root.nodeType !== 1) return;
    element(root);
    const it = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    for (let n = it.nextNode(); n; n = it.nextNode()) { if (n.nodeType === 3) textNode(n); else element(n); }
  }

  function start() {
    walk(document.body);
    if (observer) return;
    observer = new MutationObserver((records) => {
      if (!on) return;
      records.forEach((r) => {
        if (r.type === "characterData") {
          const seen = done.get(r.target);
          if (seen && seen[1] === r.target.nodeValue) return;  // our own change
          done.delete(r.target); textNode(r.target);
        }
        else r.addedNodes.forEach(walk);
      });
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  function stop() {
    if (observer) { observer.disconnect(); observer = null; }
    done.forEach(([fr, en], node) => { if (node.nodeValue === en) node.nodeValue = fr; });
    done.clear();
    doneAttr.splice(0).forEach(([node, name, fr]) => {
      if (name === "value") node.value = fr; else node.setAttribute(name, fr);
      node.removeAttribute("data-i18n-" + name);
    });
  }

  /** Called by DA.setLanguage (i18n.js) every time the language is applied. */
  DA.domLanguage = function (lang) {
    on = lang === "en";
    if (!on) { stop(); return; }
    load().then(() => { if (on && document.body) start(); });
  };
  DA.translateText = (text) => (dict && on ? translate(text) || text : text);  // for a script that builds text itself
})();
