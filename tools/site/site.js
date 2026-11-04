/* Website of Dynamite | Agile (D-O-015): reveal on scroll, copy buttons, the descent into the mine and the terminal
   that types the three installation commands. No external resource; motion off with prefers-reduced-motion. */
(function () {
  "use strict";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
    button.type = "button"; button.className = "copy"; button.textContent = "Copier";
    button.addEventListener("click", () => {
      const text = Array.from(pre.querySelectorAll("code")).map((c) => c.textContent).join("\n");
      const done = () => { button.textContent = "Copié ✓"; setTimeout(() => { button.textContent = "Copier"; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => {}); else done();
    });
    pre.append(button);
  });

  /* ---------- the descent: each level reached deepens the shaft ---------- */
  const levels = Array.from(document.querySelectorAll(".level"));
  const rope = document.querySelector(".shaft .rope");
  const depth = document.querySelector(".shaft .depth");
  if (levels.length && rope && depth) {
    function goTo(meters, ratio) {
      rope.style.setProperty("--depth", (ratio * 100).toFixed(1) + "%");
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
