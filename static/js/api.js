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
  const loadedAssets = new Set();

  function registerModule(key, render) { views[key] = render; }

  function loadAsset(url, isStyle) {
    if (loadedAssets.has(url)) return Promise.resolve();
    loadedAssets.add(url);
    return new Promise((resolve) => {
      const node = isStyle
        ? el("link", { rel: "stylesheet", href: url })
        : el("script", { src: url });
      if (!isStyle) node.async = false;  // keep declaration order
      node.addEventListener("load", resolve);
      node.addEventListener("error", () => { console.error("Asset not loaded: " + url); resolve(); });
      document.head.append(node);
    });
  }

  function loadModuleAssets(modules) {
    const jobs = [];
    for (const m of modules || []) {
      if (!m.available) continue;
      (m.styles || []).forEach((url) => jobs.push(loadAsset(url, true)));
      (m.scripts || []).forEach((url) => jobs.push(loadAsset(url, false)));
    }
    return Promise.all(jobs);
  }

  window.DA = {
    api: {
      get: (url) => request("GET", url),
      post: (url, body) => request("POST", url, body || {}),
      put: (url, body) => request("PUT", url, body || {}),
      patch: (url, body) => request("PATCH", url, body || {}),
      del: (url) => request("DELETE", url),
      upload: (url, file) => request("POST", url, undefined, file),
    },
    setCsrf(token) { state.csrf = token; },
    onUnauthorized: null,
    ApiError, el, clear, field, badge, roleBadge, table, toast, modal, formatDate, initials,
    registerModule, loadModuleAssets, views,
  };
})();
