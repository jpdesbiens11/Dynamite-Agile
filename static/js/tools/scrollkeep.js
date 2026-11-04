/* 0.60.23: the page stays where the person was looking. A click that redraws a screen (a selection, a check box, a
   change saved) used to rebuild the content: the page shrank for a moment and the browser jumped away from the zone
   of interest. DA.keepScroll(fn) redraws in place: the height of the page is held during the redraw, then the window
   and every scrolled box inside the content (a wide diagram, a panel, a list) are put back where they were.
   DA.holdScroll() / DA.releaseScroll(snapshot) do the same around an asynchronous redraw (the router, same Space). */
(function () {
  "use strict";

  const BOXES = "main [class*='scroll'], main .dm-panel, main .dm-pt-checks, main aside, main .ag-sidebar, main .dy-sidebar";

  function snapshot() {
    const main = document.querySelector("main") || document.body;
    const boxes = [...document.querySelectorAll(BOXES)].map((b, i) => [i, b.scrollLeft, b.scrollTop]).filter(([, l, t]) => l || t);
    main.style.minHeight = main.offsetHeight + "px";  // no collapse while the content is rebuilt
    return { x: window.scrollX, y: window.scrollY, boxes, main };
  }

  function restore(s) {
    if (!s) return;
    const all = [...document.querySelectorAll(BOXES)];
    s.boxes.forEach(([i, l, t]) => { if (all[i]) { all[i].scrollLeft = l; all[i].scrollTop = t; } });
    window.scrollTo(s.x, s.y);
    requestAnimationFrame(() => {  // after the browser laid the new content out
      window.scrollTo(s.x, s.y);
      s.main.style.minHeight = "";
    });
  }

  DA.keepScroll = function (fn) {
    const s = snapshot();
    try { return fn(); } finally { restore(s); }
  };
  DA.holdScroll = snapshot;
  DA.releaseScroll = restore;
})();
