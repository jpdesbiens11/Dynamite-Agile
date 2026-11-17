/* Diamond · wide FMEA tables (0.60.110, D-O-123): the pieces shared by the DFMEA, the PFMEA and the control plans.
   - fmScroller(box): wraps a scroll box (.dm-fm-scroll) with a thin horizontal scroll bar pinned to the bottom of the
     window (position: sticky) while the table is on screen and the box's own bar is not; Shift + wheel scrolls sideways.
   - fmStick(wrap, keys): the tools column and the given columns stay on the left while the table scrolls sideways.
   - fmFull(holder, button): the page alone in the window (Fullscreen API on the document, CSS class as the fallback),
     Esc to leave. Nothing here goes to the server. */
(function () {
  "use strict";

  const { el } = DA;
  const updaters = new WeakMap();  // wrap -> function that resizes its bar and its sticky columns

  /* one observer and one scroll listener for every wide table of the page (no listener left behind by a redraw) */
  const resized = typeof ResizeObserver === "function" ? new ResizeObserver((entries) => entries.forEach((e) => {
    if (!e.target.isConnected) { resized.unobserve(e.target); return; }
    const wrap = e.target.closest(".dm-fv-wrap");
    if (wrap && updaters.has(wrap)) updaters.get(wrap)();
  })) : null;
  let ticking = false;
  function idleAll() {
    ticking = false;
    document.querySelectorAll(".dm-fv-wrap").forEach(idle);
  }
  const later = () => { if (!ticking) { ticking = true; requestAnimationFrame(idleAll); } };
  if (typeof document !== "undefined" && document.addEventListener) {
    document.addEventListener("scroll", later, { passive: true, capture: true });
    window.addEventListener("resize", later, { passive: true });
  }

  /* the pinned bar is useless while the box's own bar is in view (its bottom edge is on screen) */
  function idle(wrap) {
    const box = wrap.querySelector(".dm-fm-scroll"), bar = wrap.querySelector(".dm-fv-hbar");
    if (!box || !bar) return;
    const r = box.getBoundingClientRect();
    bar.classList.toggle("dm-fv-idle", r.bottom <= window.innerHeight || r.top >= window.innerHeight);
  }

  /* Shift + wheel: sideways, for the mice that only have a vertical wheel */
  function sideways(target, box) {
    target.addEventListener("wheel", (ev) => {
      if (!ev.shiftKey || Math.abs(ev.deltaX) > 0.5 || !ev.deltaY || box.scrollWidth <= box.clientWidth) return;
      box.scrollLeft += ev.deltaY;
      ev.preventDefault();
    }, { passive: false });
  }

  function fmScroller(box) {
    const inner = el("div", { class: "dm-fv-hbar-in" });
    const bar = el("div", { class: "dm-fv-hbar", "aria-hidden": "true" }, inner);
    const wrap = el("div", { class: "dm-fv-wrap" }, box, bar);
    let lock = false;
    const sync = (from, to) => () => {
      if (lock) { lock = false; return; }
      if (Math.abs(to.scrollLeft - from.scrollLeft) < 1) return;
      lock = true;
      to.scrollLeft = from.scrollLeft;
    };
    box.addEventListener("scroll", sync(box, bar), { passive: true });
    bar.addEventListener("scroll", sync(bar, box), { passive: true });
    sideways(box, box);
    sideways(bar, box);
    const update = () => {
      inner.style.width = box.scrollWidth + "px";
      bar.hidden = box.scrollWidth <= box.clientWidth + 1;
      bar.scrollLeft = box.scrollLeft;
      const stick = updaters.get(wrap.querySelector("table") || wrap);
      if (stick) stick();
      idle(wrap);
    };
    updaters.set(wrap, update);
    if (resized) { resized.observe(box); const t = box.querySelector("table"); if (t) resized.observe(t); }
    requestAnimationFrame(update);
    return wrap;
  }

  /* the left columns: the first cell of each row (tools) and the cells of `keys` (class dm-fm-k-<key>), in order, as
     long as they take less than half of the box -- on a narrow window only the tools stay */
  function fmStick(wrap, keys) {
    const box = wrap.querySelector(".dm-fm-scroll"), table = wrap.querySelector("table");
    if (!box || !table) return;
    const head = table.tHead && table.tHead.rows[0];
    const first = table.tBodies[0] && table.tBodies[0].rows[0];
    const stick = () => {
      table.querySelectorAll(".dm-fv-stick").forEach((n) => { n.classList.remove("dm-fv-stick", "dm-fv-stick-last"); n.style.left = ""; });
      if (!head || !first) return;
      const cols = [0];
      keys.forEach((k) => { const td = first.querySelector(".dm-fm-k-" + k); if (td) cols.push(td.cellIndex); });
      let left = 0, n = 0;
      const lefts = [];
      cols.forEach((i, c) => {  // as many as fit in half of the box, in order; the tools always
        const w = head.cells[i] ? head.cells[i].offsetWidth : 0;
        if (c > 0 && (n < c || left + w > box.clientWidth * 0.5)) return;
        lefts.push(left);
        left += w;
        n = c + 1;
      });
      for (let c = 0; c < n; c += 1) {
        const i = cols[c];
        [head.cells[i]].concat([...table.tBodies[0].rows].map((tr) => tr.cells.length > i ? tr.cells[i] : null)).forEach((cell) => {
          if (!cell || cell.colSpan > 1) return;
          cell.classList.add("dm-fv-stick");
          if (c === n - 1) cell.classList.add("dm-fv-stick-last");
          cell.style.left = lefts[c] + "px";
        });
      }
    };
    updaters.set(table, stick);
    requestAnimationFrame(stick);
  }

  /* full screen: the class shows the page alone over the whole window; the Fullscreen API also hides the browser's own
     bars when it is allowed. The document (not the page) goes full screen, so dialogs and toasts stay visible. */
  function label(holder) {
    const on = holder.classList.contains("dm-fv-full");
    holder.querySelectorAll(".dm-fv-full-btn").forEach((b) => {
      b.setAttribute("aria-pressed", String(on));
      const text = b.querySelector(".dm-fv-full-label") || b;  // its own span: the [new] badge beside it stays
      text.textContent = on ? "Quitter le plein écran" : "Plein écran";
      b.setAttribute("data-tip", on ? "Revenir à la page (Esc)" : "Le tableau seul dans la fenêtre ; Esc pour revenir");
    });
  }
  function fmFull(holder, button) {
    button.classList.add("dm-fv-full-btn");
    button.addEventListener("click", () => {
      if (holder._fvLeave) { holder._fvLeave(); return; }
      const onChange = () => { if (!document.fullscreenElement && holder._fvLeave) holder._fvLeave(); };
      const onKey = (ev) => {
        if (ev.key !== "Escape" || document.querySelector(".modal-backdrop") || document.querySelector(".dm-fv-loupe:not([hidden])")) return;
        ev.preventDefault();
        if (holder._fvLeave) holder._fvLeave();
      };
      const leave = () => {
        holder._fvLeave = null;
        holder.classList.remove("dm-fv-full");
        document.documentElement.classList.remove("dm-fv-lock");
        document.removeEventListener("keydown", onKey, true);
        document.removeEventListener("fullscreenchange", onChange);
        window.removeEventListener("hashchange", leave);
        if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {});
        label(holder);
      };
      holder._fvLeave = leave;
      holder.classList.add("dm-fv-full");
      document.documentElement.classList.add("dm-fv-lock");
      document.addEventListener("keydown", onKey, true);
      document.addEventListener("fullscreenchange", onChange);
      window.addEventListener("hashchange", leave);
      const root = document.documentElement;
      if (root.requestFullscreen && !document.fullscreenElement) root.requestFullscreen().catch(() => { /* CSS fallback only */ });
      label(holder);
    });
    requestAnimationFrame(() => label(holder));
  }

  DA.diamond = Object.assign(DA.diamond || {}, { fmScroller, fmStick, fmFull });
})();
