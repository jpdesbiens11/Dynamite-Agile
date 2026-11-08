/* The day with the team (vitrine D-B-087, website D-O-015): the step being read drives the mock-up screen, and a
   cursor plays each tool's gesture there, so every change on screen has a cause (the stageshow method, written for
   the platform: native JS, no library). Wide screens: one scene per step, played when its step reaches the middle of
   the window. Narrow screens: the screen sits above the steps and plays the day on its own while it is in view.
   Reduced motion: no cursor, each scene shows its result. The words come from the markup (data-to), so the French
   and English pages share this script; tools/build_site.py swaps the typed line. */
(function () {
  "use strict";
  const screen = document.getElementById("screen");
  if (!screen) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const narrow = window.matchMedia("(max-width: 900px)");
  const steps = Array.from(document.querySelectorAll(".step"));
  const scenes = Array.from(screen.querySelectorAll(".scene"));
  const tabs = Array.from(screen.querySelectorAll(".bar .tab"));
  const cur = screen.querySelector(".jc");
  const TYPED = "Objectif : vérifier que le pistolet chaud tombé d'un mètre reste sûr et fonctionnel.";
  const SHIFT = 8;  // Exploration: Concept grows by 8 % of the six months (two weeks)
  const STOP = new Error("journey: replaced by a newer run");
  const TRAVEL = (t) => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const q = (root, sel) => root.querySelector(sel);
  const all = (root, sel) => Array.from(root.querySelectorAll(sel));
  let gen = 0, current = -1, pos = { x: 0, y: 0 }, idleTimer = 0;
  const state = scenes.map(() => "reset");  // reset | playing | done

  /* ---------- clock: every wait belongs to one run and stops with it ---------- */
  function wait(ms, g) {
    return new Promise((res, rej) => setTimeout(() => (g === gen ? res() : rej(STOP)), ms));
  }
  function tween(ms, g, fn) {
    return new Promise((res, rej) => {
      const t0 = performance.now();
      (function frame(now) {
        if (g !== gen) { rej(STOP); return; }
        const t = Math.min(1, Math.max(0, (now - t0) / ms));
        fn(t);
        if (t < 1) requestAnimationFrame(frame); else res();
      })(t0);
    });
  }
  function later(ms, g, fn) { setTimeout(() => { if (g === gen) fn(); }, ms); }
  const quiet = (e) => { if (e !== STOP) throw e; };

  /* ---------- the cursor: a hand that travels in a shallow arc, presses, and rests off what it changed ---------- */
  function at(el, fx, fy) {
    const s = screen.getBoundingClientRect(), r = el.getBoundingClientRect();
    return { x: r.left - s.left - screen.clientLeft + r.width * (fx == null ? .86 : fx),
             y: r.top - s.top - screen.clientTop + r.height * (fy == null ? .8 : fy) };
  }
  function place(p) {
    pos = { x: p.x, y: p.y };
    cur.style.transform = "translate(" + p.x.toFixed(1) + "px, " + p.y.toFixed(1) + "px)";
  }
  function wake() { clearTimeout(idleTimer); cur.classList.remove("idle"); }
  function rest() { clearTimeout(idleTimer); idleTimer = setTimeout(() => cur.classList.add("idle"), 4000); }
  function restPoint() { return { x: screen.clientWidth * .84, y: screen.clientHeight - 22 }; }

  async function move(to, g, opts) {
    opts = opts || {};
    wake();
    const from = pos, dist = Math.hypot(to.x - from.x, to.y - from.y);
    if (dist > .5) {
      const ms = opts.ms || clamp(300 + dist, 340, 760);
      const bow = opts.straight ? 0 : Math.min(dist * .08, 24);
      const nx = -(to.y - from.y) / dist, ny = (to.x - from.x) / dist;
      let switched = !opts.kind;
      await tween(ms, g, (t) => {
        const e = TRAVEL(t), lift = Math.sin(Math.PI * e) * bow;
        place({ x: from.x + (to.x - from.x) * e + nx * lift, y: from.y + (to.y - from.y) * e + ny * lift });
        if (!switched && e > .7) { switched = true; cur.dataset.kind = opts.kind; }  // the kind changes as it reaches the target
        if (opts.onMove) opts.onMove(pos, e);
      });
    }
    if (opts.kind) cur.dataset.kind = opts.kind;
    rest();
  }
  async function press(el, g) {
    wake();
    cur.setAttribute("data-pressed", "");
    if (el) el.setAttribute("data-pressed", "");
    try { await wait(110, g); } finally {
      cur.removeAttribute("data-pressed");
      if (el) el.removeAttribute("data-pressed");
    }
    rest();
  }
  async function click(el, g, fx, fy) {
    await move(at(el, fx, fy), g, { kind: "arrow" });
    await wait(120, g);
    await press(el, g);
  }
  function aside(g, dx, dy) {  // after the press, the hand leaves the words it changed
    return move({ x: clamp(pos.x + (dx || 34), 12, screen.clientWidth - 26), y: clamp(pos.y + (dy || 30), 52, screen.clientHeight - 26) },
                g, { ms: 420, kind: "arrow" });
  }
  function settle(s, g) {  // or rests in the empty band under the scene's content
    let bottom = 0;
    Array.from(s.children).forEach((n) => { if (getComputedStyle(n).position !== "absolute") bottom = Math.max(bottom, at(n, 0, 1).y); });
    return move({ x: clamp(pos.x - 24, 24, screen.clientWidth - 40), y: clamp(bottom + 34, 60, screen.clientHeight - 24) }, g, { ms: 480, kind: "arrow" });
  }

  /* ---------- words that change on themselves (data-to), never swapped in one frame ---------- */
  function roll(el, text) {
    if (el.textContent === text) return;
    if (reduce) { el.textContent = text; return; }
    const box = document.createElement("span"), out = document.createElement("span"), inn = document.createElement("span");
    box.className = "roll"; out.textContent = el.textContent; inn.textContent = text;
    el.textContent = ""; box.append(out, inn); el.append(box);
    box.style.width = out.offsetWidth + "px";
    out.className = "ro-out"; inn.className = "ro-in";
    void box.offsetWidth;
    box.style.width = inn.offsetWidth + "px";
    setTimeout(() => { if (box.parentNode === el) el.textContent = text; }, 380);
  }
  function back(s) { all(s, "[data-to]").forEach((el) => { el.textContent = el.dataset.from; }); }
  function forth(s) { all(s, "[data-to]").forEach((el) => { el.textContent = el.dataset.to; }); }
  function snap(s, fn) {  // a state set while hidden, with no transition to watch
    s.classList.add("snap");
    fn(s);
    void s.offsetWidth;
    s.classList.remove("snap");
  }

  /* ---------- board geometry: columns, slots and the card carried between them ---------- */
  function slot(s, where) {
    const [c, k] = where.split(" ").map(Number), col = all(s, ".col")[c], h4 = q(col, "h4");
    return { left: col.offsetLeft + 8, top: col.offsetTop + h4.offsetTop + h4.offsetHeight + 6 + k * s._pitch };
  }
  function layout(s) {
    const cards = all(s, ".card"), col = q(s, ".col");
    cards.forEach((c) => { c.style.width = (col.offsetWidth - 16) + "px"; c.style.transform = "none"; });
    s._pitch = Math.max.apply(null, cards.map((c) => c.offsetHeight)) + 8;
    cards.forEach((c) => {
      c._base = slot(s, c.dataset.at);
      c.style.left = c._base.left + "px"; c.style.top = c._base.top + "px";
    });
  }
  function put(s, c, where, lift) {
    const to = slot(s, where);
    c.style.transform = "translate(" + (to.left - c._base.left) + "px, " + (to.top - c._base.top) + "px)" + (lift || "");
  }

  /* ---------- the nine gestures: reset (hidden), done (the result, also the reduced-motion still), play ---------- */
  const SCENES = {
    dash: {
      reset(s) { back(s); q(s, ".msg").classList.remove("in", "ok"); q(s, ".msg .btn").classList.remove("is-done"); },
      done(s) { forth(s); q(s, ".msg").classList.add("in", "ok"); q(s, ".msg .btn").classList.add("is-done"); },
      async play(s, g) {
        const msg = q(s, ".msg"), b = q(s, ".msg .btn"), dot = q(s, ".dot");
        await wait(500, g); msg.classList.add("in");  // Nina's @lea arrives
        await wait(1100, g); await click(b, g);
        roll(b, b.dataset.to); b.classList.add("is-done");
        await wait(160, g); roll(dot, dot.dataset.to); msg.classList.add("ok");
        await settle(s, g);
      },
    },
    need: {
      reset(s) {
        back(s); q(s, "#nstatus").className = "chip y"; q(s, ".pop").classList.remove("open");
        all(s, ".pop [data-hover]").forEach((n) => n.removeAttribute("data-hover")); q(s, ".trace").classList.remove("on");
      },
      done(s) { forth(s); q(s, "#nstatus").className = "chip g"; q(s, ".trace").classList.add("on"); },
      async play(s, g) {
        const chip = q(s, "#nstatus"), pop = q(s, ".pop"), pick = q(s, ".pop .pick");
        await wait(600, g); await click(chip, g, .82, .7);
        const sr = s.getBoundingClientRect(), cr = chip.getBoundingClientRect();  // the menu opens under the chip, right edges aligned
        pop.style.top = (cr.bottom - sr.top + 6) + "px";
        pop.style.left = Math.max(8, cr.right - sr.left - pop.offsetWidth) + "px";
        pop.classList.add("open");
        await wait(380, g); await move(at(pick, .84, .62), g);
        pick.setAttribute("data-hover", "");
        await wait(160, g); await press(pick, g);
        pop.classList.remove("open");
        roll(chip, chip.dataset.to); chip.className = "chip g";
        await wait(260, g); q(s, ".trace").classList.add("on");  // the need now justifies the requirement: the trace draws on
        await aside(g, 30, 44);
      },
    },
    tree: {
      reset(s) { q(s, ".ftree").classList.remove("grown"); q(s, ".crit").classList.remove("sel"); all(s, ".dfm").forEach((d) => d.classList.remove("in")); },
      done(s) { q(s, ".ftree").classList.add("grown"); q(s, ".crit").classList.add("sel"); all(s, ".dfm").forEach((d) => d.classList.add("in")); },
      async play(s, g) {
        await wait(250, g); q(s, ".ftree").classList.add("grown");  // the branches, one after the other (--k)
        await wait(1900, g);
        const f3 = q(s, ".crit"), rows = all(s, ".dfm");
        await click(f3, g, .9, .62);
        f3.classList.add("sel");
        await wait(220, g); rows[0].classList.add("in");
        await wait(140, g); rows[1].classList.add("in");
        await wait(300, g); await settle(s, g);
      },
    },
    plan: {
      reset(s) {
        back(s);
        all(s, "[data-x]").forEach((b) => { b.style.left = b.dataset.x + "%"; if (b.dataset.w) b.style.width = "0"; });
      },
      done(s) {
        forth(s);
        all(s, "[data-x]").forEach((b) => {
          b.style.left = (+b.dataset.x + ("dep" in b.dataset ? SHIFT : 0)) + "%";
          if (b.dataset.w) b.style.width = (+b.dataset.w + ("grip" in b.dataset ? SHIFT : 0)) + "%";
        });
      },
      async play(s, g) {
        all(s, "[data-w]").forEach((b, k) => later(150 + k * 110, g, () => { b.style.width = b.dataset.w + "%"; }));
        await wait(1500, g);
        const grip = q(s, "[data-grip]"), deps = all(s, "[data-dep]"), date = q(s, ".g-sum [data-to]");
        const tw = grip.parentNode.getBoundingClientRect().width, w0 = +grip.dataset.w;
        const start = at(grip, 1, .5); start.x -= 2;
        await move(start, g, { kind: "ew" });  // the end of Concept: a resize handle
        await wait(140, g);
        wake(); cur.setAttribute("data-pressed", ""); grip.classList.add("drag");
        try {
          await wait(100, g);
          await move({ x: start.x + tw * SHIFT / 100, y: start.y }, g, { ms: 950, straight: true, onMove: (p) => {
            const d = clamp((p.x - start.x) / tw * 100, 0, SHIFT);
            grip.style.width = (w0 + d) + "%";
            deps.forEach((b) => { b.style.left = (+b.dataset.x + d) + "%"; });  // the phases that follow it move with it
          } });
        } finally { cur.removeAttribute("data-pressed"); grip.classList.remove("drag"); }
        await wait(280, g); roll(date, date.dataset.to);
        await settle(s, g);
      },
    },
    board: {
      reset(s) { layout(s); all(s, ".card").forEach((c) => { c.classList.remove("held"); put(s, c, c.dataset.at); }); },
      done(s) { layout(s); all(s, ".card").forEach((c) => put(s, c, c.dataset.end || c.dataset.at)); },
      async play(s, g) {
        const card = q(s, ".card[data-end][data-carry]"), next = all(s, ".card[data-end]:not([data-carry])");
        await wait(500, g);
        const grab = at(card, .8, .55);
        await move(grab, g);
        await wait(140, g);
        const sr = screen.getBoundingClientRect(), cr = card.getBoundingClientRect();
        const off = { x: grab.x - (cr.left - sr.left - screen.clientLeft), y: grab.y - (cr.top - sr.top - screen.clientTop) };
        const base = { x: grab.x - off.x, y: grab.y - off.y }, to = slot(s, card.dataset.end);
        const target = { x: base.x + to.left - card._base.left + off.x, y: base.y + to.top - card._base.top + off.y };
        const LIFT = " rotate(2deg) scale(1.03)";
        wake(); cur.setAttribute("data-pressed", "");
        card.style.transition = "transform .12s ease-out, box-shadow .2s ease";  // picked up on the press
        card.classList.add("held"); card.style.transform = "translate(0px, 0px)" + LIFT;
        later(160, g, () => next.forEach((c) => put(s, c, c.dataset.end)));  // the column closes behind it
        try {
          await wait(130, g);
          card.style.transition = "";  // from here it rides with the hand exactly
          await move(target, g, { ms: 980, onMove: (p) => {
            card.style.transform = "translate(" + (p.x - off.x - base.x).toFixed(1) + "px, " + (p.y - off.y - base.y).toFixed(1) + "px)" + LIFT;
          } });
        } finally { cur.removeAttribute("data-pressed"); }
        card.classList.remove("held"); put(s, card, card.dataset.end);  // set down flat in its slot
        rest();
        await wait(420, g); await aside(g, 30, 50);
      },
    },
    wiki: {
      reset(s) { back(s); const t = q(s, ".typed"); t.textContent = ""; t.classList.remove("caret"); q(s, ".exp .btn").classList.remove("is-done"); },
      done(s) { forth(s); const t = q(s, ".typed"); t.textContent = TYPED; t.classList.remove("caret"); q(s, ".exp .btn").classList.add("is-done"); },
      async play(s, g) {
        const t = q(s, ".typed"), b = q(s, ".exp .btn");
        await wait(400, g);
        await move(at(t, .03, .28), g, { kind: "ibeam" });
        await wait(100, g); await press(null, g);
        t.classList.add("caret");
        const ph = at(q(s, ".ph"), 1, .5);  // out of the line about to be typed, beside the page's next lines
        await move({ x: Math.min(ph.x + 48, screen.clientWidth - 40), y: ph.y + 4 }, g, { ms: 480, kind: "arrow" });
        for (let k = 1; k <= TYPED.length; k++) { t.textContent = TYPED.slice(0, k); await wait(26, g); }
        await wait(350, g); await click(b, g);
        t.classList.remove("caret");
        roll(b, b.dataset.to); b.classList.add("is-done");
        await aside(g);
      },
    },
    test: {
      reset(s) { back(s); q(s, ".scope").classList.remove("run"); q(s, "#verified").className = "chip b"; q(s, ".scope .btn").classList.remove("is-done"); },
      done(s) { forth(s); q(s, ".scope").classList.add("run"); q(s, "#verified").className = "chip g"; q(s, ".scope .btn").classList.add("is-done"); },
      async play(s, g) {
        q(s, ".scope").classList.add("run");
        await wait(1700, g);
        const b = q(s, ".scope .btn"), v = q(s, "#verified");
        await click(b, g);
        roll(b, b.dataset.to); b.classList.add("is-done");
        await wait(450, g); roll(v, v.dataset.to); v.className = "chip g";  // the PDF closes the loop
        await aside(g, 26, 38);
      },
    },
    hours: {
      reset(s) {
        back(s); q(s, ".btn-primary").classList.remove("is-done");
        all(s, ".hcol").forEach((c) => { c.classList.remove("filled"); c.firstElementChild.style.height = "0"; });
      },
      done(s) {
        forth(s); q(s, ".btn-primary").classList.add("is-done");
        all(s, ".hcol").forEach((c) => { c.classList.add("filled"); c.firstElementChild.style.height = c.dataset.h + "%"; });
      },
      async play(s, g) {
        const cols = all(s, ".hcol"), fri = cols[cols.length - 1];
        cols.slice(0, -1).forEach((c, k) => later(120 + k * 90, g, () => { c.firstElementChild.style.height = c.dataset.h + "%"; }));
        await wait(1300, g);
        const copy = q(s, "[data-copy]"), sub = q(s, ".btn-primary"), total = q(s, ".mini-h [data-to]");
        await click(copy, g);
        fri.classList.add("filled"); fri.firstElementChild.style.height = fri.dataset.h + "%";
        await wait(320, g); roll(total, total.dataset.to);
        await wait(900, g); await click(sub, g);
        roll(sub, sub.dataset.to); sub.classList.add("is-done");
        const right = at(sub, 1, .5);  // beside the buttons, on the empty end of their line
        await move({ x: Math.min(right.x + 70, screen.clientWidth - 30), y: right.y + 6 }, g, { ms: 460, kind: "arrow" });
      },
    },
    train: {
      reset(s) {
        back(s); q(s, ".tl .chip").className = "chip y"; q(s, ".rows .btn").classList.remove("is-done");
        const p = q(s, ".progress"); p.classList.remove("full"); p.firstElementChild.style.width = "0";
      },
      done(s) {
        forth(s); q(s, ".tl .chip").className = "chip g"; q(s, ".rows .btn").classList.add("is-done");
        const p = q(s, ".progress"); p.classList.add("full"); p.firstElementChild.style.width = "100%";
      },
      async play(s, g) {
        const bar = q(s, ".progress"), b = q(s, ".rows .btn"), chip = q(s, ".tl .chip");
        await wait(150, g); bar.firstElementChild.style.width = "72%";
        await wait(1300, g); await click(b, g);
        roll(b, b.dataset.to); b.classList.add("is-done");
        await wait(450, g); roll(chip, chip.dataset.to); chip.className = "chip g";  // the topic is Completed
        bar.classList.add("full"); bar.firstElementChild.style.width = "100%";
        await settle(s, g);
      },
    },
  };
  const sceneOf = (i) => SCENES[scenes[i].dataset.play];

  /* ---------- the run: the hand opens the tool's tab, the page swaps, the gesture plays ---------- */
  function swap(i) {
    if (i === current) return;
    snap(scenes[i], sceneOf(i).reset); state[i] = "reset";
    scenes.forEach((n, k) => n.classList.toggle("on", k === i));
    tabs.forEach((t) => t.classList.toggle("on", Number(t.dataset.t) === i));
    const step = steps.find((n) => Number(n.dataset.scene) === i);
    if (step) screen.style.setProperty("--acc", step.getAttribute("data-acc"));
    current = i;
  }
  function finish(i) { swap(i); snap(scenes[i], sceneOf(i).done); state[i] = "done"; }
  async function go(i, g) {
    if (!cur.classList.contains("live")) { place(restPoint()); cur.classList.add("live"); await wait(300, g); }
    if (i !== current) {
      await click(tabs.find((t) => Number(t.dataset.t) === i), g, .7, .8);
      swap(i);
      await wait(240, g);
    } else if (state[i] !== "reset") { finish(i); return; }  // its result is already on screen: it never plays backwards
    state[i] = "playing";
    await sceneOf(i).play(scenes[i], g);
    state[i] = "done";
  }
  function start(i) {
    const g = ++gen;
    if (reduce || !cur) { finish(i); return; }
    go(i, g).catch(quiet);
  }
  async function tour(g) {  // narrow screens: the whole day, tab after tab, while the screen is in view
    if (state[current] === "playing") finish(current);  // interrupted when it left the view: its result
    if (state[current] === "reset") await go(current, g);
    for (;;) {
      await wait(2400, g);
      await go((current + 1) % scenes.length, g);
    }
  }

  all(screen, "[data-to]").forEach((el) => { el.dataset.from = el.textContent; });
  if (reduce || !cur) finish(0); else { swap(0); place(restPoint()); }

  const so = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!e.isIntersecting || narrow.matches) return;
    const i = Number(e.target.dataset.scene);
    steps.forEach((n) => n.classList.toggle("on", n === e.target));
    start(i);
  }), { rootMargin: "-45% 0px -45% 0px" });
  const vo = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!narrow.matches) return;
    if (!e.isIntersecting) { gen++; return; }  // out of view: the day pauses
    const g = ++gen;
    if (reduce || !cur) finish(current); else tour(g).catch(quiet);
  }), { threshold: .45 });
  function watch() {
    gen++;
    so.disconnect(); vo.disconnect();
    steps.forEach((n) => so.observe(n));
    vo.observe(screen);
  }
  watch();
  narrow.addEventListener("change", watch);
})();
