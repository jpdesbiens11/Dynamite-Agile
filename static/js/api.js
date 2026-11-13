/* Dynamite | Agile - shared helpers: API client, DOM builder, dialogs.
   Every element is built with textContent, never innerHTML, so user data
   can never be interpreted as HTML (protection against script injection). */
(function () {
  "use strict";

  const state = { csrf: null };

  class ApiError extends Error {
    constructor(status, message) {
      super(message);
      this.status = status;
    }
  }

  async function request(method, url, body, file) {
    const options = { method, headers: {}, credentials: "same-origin" };
    if (file) {  // raw file upload (core lot v0.4): bytes as the body, name in a header
      options.headers["Content-Type"] = file.type || "application/octet-stream";
      options.headers["X-File-Name"] = encodeURIComponent(file.name || "");
      options.body = file;
    } else if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    if (method !== "GET" && state.csrf) options.headers["X-CSRF-Token"] = state.csrf;
    if (DA.needsInitials && DA.needsInitials(method, url)) {  // D-B-058: no write without the 3-letter key
      if (DA.onInitialsMissing) DA.onInitialsMissing();
      throw new ApiError(428, "Initiales requises : définissez vos 3 lettres dans les Paramètres, puis refaites l'action.");
    }

    let response;
    try {
      response = await fetch(url, options);
    } catch (err) {
      throw new ApiError(0, "Serveur injoignable. Vérifiez votre connexion VPN.");
    }
    const text = await response.text();
    let data = null;
    if (text) {
      try { data = JSON.parse(text); } catch (err) { data = null; }
    }
    if (!response.ok) {
      const message = (data && data.error) || "Erreur " + response.status + ".";
      if (response.status === 401 && url !== "/api/login" && typeof DA.onUnauthorized === "function") {
        DA.onUnauthorized();
      }
      if (response.status === 428 && DA.onInitialsMissing) {
        DA.onInitialsMissing();
        throw new ApiError(428, "Initiales requises : définissez vos 3 lettres dans les Paramètres, puis refaites l'action.");
      }
      throw new ApiError(response.status, message);
    }
    /* D-A-046: who received the @mention, who did not and why -- for every page, comment and Q&A at once */
    if (data && data.mentions_notice && DA.toast) {
      DA.toast(data.mentions_notice, /Non notifié/.test(data.mentions_notice) ? "error" : "success");
      if (DA.refreshMentions) DA.refreshMentions();
    }
    return data;
  }

  /* 0.60.62 (D-O-071): POST a JSON body and save the file the server sends back (exports built from browser data). */
  async function download(url, body) {
    const headers = { "Content-Type": "application/json" };
    if (state.csrf) headers["X-CSRF-Token"] = state.csrf;
    let response;
    try {
      response = await fetch(url, { method: "POST", credentials: "same-origin", headers, body: JSON.stringify(body || {}) });
    } catch (err) {
      throw new ApiError(0, "Serveur injoignable. Vérifiez votre connexion VPN.");
    }
    if (!response.ok) {
      let message = "Erreur " + response.status + ".";
      try { message = (await response.json()).error || message; } catch (err) { /* not JSON */ }
      throw new ApiError(response.status, message);
    }
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = /filename="([^"]+)"/.exec(disposition);
    const blob = await response.blob();
    const link = URL.createObjectURL(blob);
    const a = el("a", { href: link, download: match ? match[1] : "export" });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(link), 30000);
  }

  /* el("button", {class: "btn", onclick: fn}, "Label", childNode, ...) */
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [name, value] of Object.entries(attrs)) {
        if (value === null || value === undefined || value === false) continue;
        if (name === "class") node.className = value;
        else if (name.startsWith("on") && typeof value === "function") node.addEventListener(name.slice(2), value);
        else if (value === true) node.setAttribute(name, "");
        else node.setAttribute(name, String(value));
      }
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : String(child));
    }
    return node;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function field(label, input, hint) {
    return el("label", { class: "field" },
      el("span", { class: "field-label" }, label),
      input,
      hint ? el("span", { class: "field-hint" }, hint) : null);
  }

  const ROLE_LABELS = { admin: "Admin", manager: "Admin du Space", editor: "Éditeur", reader: "Lecteur" };

  function badge(text, kind) {
    return el("span", { class: "badge badge-" + (kind || "neutral") }, text);
  }

  function roleBadge(role) {
    return badge(ROLE_LABELS[role] || role, role);
  }

  function table(headers, rows) {
    const body = rows.length
      ? rows
      : [el("tr", null, el("td", { colspan: headers.length, class: "muted" }, "Aucune donnée."))];
    return el("div", { class: "table-wrap" },
      el("table", { class: "data" },
        el("thead", null, el("tr", null, headers.map((h) => el("th", null, h)))),
        el("tbody", null, body)));
  }

  function toast(message, kind) {
    let box = document.getElementById("toasts");
    if (!box) {
      box = el("div", { id: "toasts", class: "toasts", "aria-live": "polite" });
      document.body.append(box);
    }
    const item = el("div", { class: "toast toast-" + (kind || "info") }, message);
    box.append(item);
    setTimeout(() => item.remove(), 4500);
  }

  /* Opens a dialog and returns a function that closes it. */
  function modal(title, content) {
    const previous = document.activeElement;
    const closeButton = el("button", { class: "icon-btn", type: "button", "aria-label": "Fermer", onclick: close }, "×");
    const dialog = el("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": title },
      el("div", { class: "modal-head" }, el("h2", null, title), closeButton),
      el("div", { class: "modal-body" }, content));
    const backdrop = el("div", { class: "modal-backdrop" }, dialog);
    backdrop.addEventListener("mousedown", (ev) => { if (ev.target === backdrop) close(); });

    function onKey(ev) { if (ev.key === "Escape") close(); }
    function close() {
      document.removeEventListener("keydown", onKey);
      backdrop.remove();
      if (previous && typeof previous.focus === "function") previous.focus();
    }

    document.addEventListener("keydown", onKey);
    document.body.append(backdrop);
    const first = dialog.querySelector(".modal-body input, .modal-body select, .modal-body textarea, .modal-body button");
    (first || closeButton).focus();
    return close;
  }

  function formatDate(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (isNaN(date.getTime())) return iso;
    return date.toLocaleString("fr-CA", { dateStyle: "short", timeStyle: "short" });
  }

  function initials(name) {
    return (name || "?").split(/[\s.\-_]+/).filter(Boolean).slice(0, 2)
      .map((part) => part[0].toUpperCase()).join("");
  }

  /* ---------- Module screens (core v0.2) ----------
     Each module script calls DA.registerModule(key, render). render(main,
     parts) receives the empty <main> of the shell and the URL hash parts
     after the module key (#/agile/EQP/board -> ["EQP", "board"]). */
  const views = {};
  const loadedAssets = new Map();  // url -> its load: a second caller waits for the same one, even while it is still loading

  function registerModule(key, render) { views[key] = render; }

  function loadAsset(url, isStyle) {
    if (loadedAssets.has(url)) return loadedAssets.get(url);
    const job = new Promise((resolve) => {
      const node = isStyle
        ? el("link", { rel: "stylesheet", href: url })
        : el("script", { src: url });
      if (!isStyle) node.async = false;  // keep declaration order
      node.addEventListener("load", resolve);
      node.addEventListener("error", () => { console.error("Asset not loaded: " + url); resolve(); });
      document.head.append(node);
    });
    loadedAssets.set(url, job);
    return job;
  }

  /* 0.60.100 (D-O-107): the scripts of the module being opened and of the ones it requires (theirs first), no longer
     the ~110 files of every module at once; the styles of every module (small, and shared by the left panels). Each
     file is asked for at its versioned address (url?v=token), which the browser keeps until the file changes. */
  const pinned = (m, url) => (m.v && m.v[url] ? url + "?v=" + m.v[url] : url);

  function withRequired(modules, key) {
    const byKey = new Map(modules.filter((m) => m.available).map((m) => [m.key, m]));
    const out = [];
    (function add(k) {
      const m = byKey.get(k);
      if (!m || out.includes(m)) return;
      (m.requires || []).forEach(add);
      out.push(m);
    })(key);
    return out;
  }

  function loadModuleAssets(modules, key) {
    const all = (modules || []).filter((m) => m.available);
    const wanted = key === undefined ? all.flatMap((m) => withRequired(all, m.key)) : withRequired(all, key);
    const jobs = [];
    for (const m of all) (m.styles || []).forEach((url) => jobs.push(loadAsset(pinned(m, url), true)));
    for (const m of new Set(wanted)) (m.scripts || []).forEach((url) => jobs.push(loadAsset(pinned(m, url), false)));
    return Promise.all(jobs);
  }

  /* the other modules, once the page has been drawn and the browser is idle: the next tab opens at once */
  let prefetching = false;
  function prefetchModuleAssets(modules) {
    if (prefetching) return;
    prefetching = true;
    const run = () => loadModuleAssets(modules);
    if (window.requestIdleCallback) requestIdleCallback(run, { timeout: 3000 }); else setTimeout(run, 1200);
  }

  window.DA = {
    api: {
      get: (url) => request("GET", url),
      post: (url, body) => request("POST", url, body || {}),
      put: (url, body) => request("PUT", url, body || {}),
      patch: (url, body) => request("PATCH", url, body || {}),
      del: (url) => request("DELETE", url),
      upload: (url, file) => request("POST", url, undefined, file),
      download,
    },
    setCsrf(token) { state.csrf = token; },
    onUnauthorized: null,
    ApiError, el, clear, field, badge, roleBadge, table, toast, modal, formatDate, initials,
    registerModule, loadModuleAssets, prefetchModuleAssets, views,
  };
})();
