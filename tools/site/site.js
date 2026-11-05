/* Website of Dynamite | Agile (D-O-015): reveal on scroll, copy buttons, the descent into the mine and the terminal
   that types the three installation commands. No external resource; motion off with prefers-reduced-motion. */
(function () {
  "use strict";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const EN = document.documentElement.lang === "en";  // D-O-017: the English pages live in site/en/
  const COPY = EN ? ["Copy", "Copied ✓"] : ["Copier", "Copié ✓"];

  /* ---------- reveal (pages without the vitrine script) ---------- */
  if (!document.getElementById("screen")) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { threshold: .15 });
    document.querySelectorAll(".reveal").forEach((n) => io.observe(n));
  }

  /* ---------- copy buttons on every command block ---------- */
  document.querySelectorAll("pre.cmd").forEach((pre) => {
    const button = document.createElement("button");
    button.type = "button"; button.className = "copy"; button.textContent = COPY[0];
    button.addEventListener("click", () => {
      const text = Array.from(pre.querySelectorAll("code")).map((c) => c.textContent).join("\n");
      const done = () => { button.textContent = COPY[1]; setTimeout(() => { button.textContent = COPY[0]; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => {}); else done();
    });
    pre.append(button);
  });

  /* ---------- the descent: each level reached deepens the shaft ---------- */
  const levels = Array.from(document.querySelectorAll(".level"));
  const rope = document.querySelector(".shaft .rope");
  const depth = document.querySelector(".shaft .depth");
  if (levels.length && rope && depth) {
    const shaftSection = document.getElementById("descente");
    function goTo(meters, ratio) {
      rope.style.setProperty("--depth", (ratio * 100).toFixed(1) + "%");
      if (shaftSection) shaftSection.style.setProperty("--deep", ratio.toFixed(3));  // 0.60.40: the rock darkens as you go down
      const from = Number(depth.dataset.m || 0), start = performance.now();
      depth.dataset.m = meters;
      if (reduce) { depth.textContent = meters + " m"; return; }
      (function tick(now) {
        const k = Math.min(1, (now - start) / 700);
        depth.textContent = Math.round(from + (meters - from) * (1 - Math.pow(1 - k, 3))) + " m";
        if (k < 1) requestAnimationFrame(tick);
      })(start);
    }
    const lo = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("in");
      const i = levels.indexOf(e.target);  // scrolling back up rises again
      goTo(Number(e.target.dataset.depth), (i + 1) / levels.length);
    }), { rootMargin: "-40% 0px -40% 0px" });
    levels.forEach((l) => lo.observe(l));
    const reveal = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) e.target.classList.add("in");
    }), { threshold: .3 });
    levels.forEach((l) => reveal.observe(l));
  }

  /* ---------- the terminal types the three commands when it comes into view ---------- */
  const term = document.getElementById("term");
  if (term) {
    const lines = JSON.parse(term.dataset.lines);
    let started = false;
    const to = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting || started) return;
      started = true;
      if (reduce) { term.textContent = lines.join("\n"); return; }
      let li = 0, ci = 0;
      (function type() {
        if (li >= lines.length) return;
        const line = lines[li];
        if (ci <= line.length) {
          term.textContent = lines.slice(0, li).join("\n") + (li ? "\n" : "") + line.slice(0, ci);
          ci += 1;
          setTimeout(type, /^(✓|==)/.test(line) ? 6 : 22);
        } else { li += 1; ci = 0; setTimeout(type, 420); }
      })();
    }), { threshold: .5 });
    to.observe(term);
  }
})();

/* 0.60.47 (D-O-056): « Partager » in the top bar -- the page being read, with its anchor (#local, #exemple…). On a phone,
   the system share sheet; elsewhere a small menu: copy the link, email, text message, WhatsApp, LinkedIn, Facebook, X
   (Messenger through the phone's sheet). Plain links: nothing is loaded from those sites until the person clicks. */
(function () {
  "use strict";
  const button = document.querySelector(".share-btn");
  if (!button) return;
  const [label, title, copy, copied, email, sms, message] = JSON.parse(button.dataset.t);
  const url = () => location.href;
  const enc = encodeURIComponent;
  const menu = document.createElement("div");
  menu.className = "share-menu"; menu.hidden = true; menu.setAttribute("role", "menu"); menu.setAttribute("aria-label", title);
  function item(text, href) {
    const a = document.createElement(href ? "a" : "button");
    a.className = "share-item"; a.textContent = text; a.setAttribute("role", "menuitem");
    if (href) { a.target = "_blank"; a.rel = "noopener"; a.addEventListener("click", () => { a.href = href(); close(); }); }
    else a.type = "button";
    menu.append(a);
    return a;
  }
  const copyItem = item(copy);
  copyItem.addEventListener("click", () => {
    const done = () => { copyItem.textContent = copied; setTimeout(() => { copyItem.textContent = copy; close(); }, 1200); };
    if (navigator.clipboard) navigator.clipboard.writeText(url()).then(done, done); else done();
  });
  item(email, () => "mailto:?subject=" + enc(document.title) + "&body=" + enc(message + " " + url()));
  item(sms, () => "sms:?&body=" + enc(message + " " + url()));
  item("WhatsApp", () => "https://wa.me/?text=" + enc(message + " " + url()));
  item("LinkedIn", () => "https://www.linkedin.com/sharing/share-offsite/?url=" + enc(url()));
  item("Facebook", () => "https://www.facebook.com/sharer/sharer.php?u=" + enc(url()));
  item("X", () => "https://x.com/intent/post?text=" + enc(message) + "&url=" + enc(url()));
  button.after(menu);
  function close() { menu.hidden = true; button.setAttribute("aria-expanded", "false"); }
  function open() { menu.hidden = false; button.setAttribute("aria-expanded", "true"); menu.querySelector(".share-item").focus(); }
  button.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    const phone = window.matchMedia("(pointer: coarse)").matches;
    if (phone && navigator.share) {
      try { await navigator.share({ title: document.title, text: message, url: url() }); return; } catch (err) { if (err && err.name === "AbortError") return; }
    }
    if (menu.hidden) open(); else close();
  });
  document.addEventListener("click", (ev) => { if (!menu.hidden && !menu.contains(ev.target)) close(); });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !menu.hidden) { close(); button.focus(); } });
  button.title = title;
})();
