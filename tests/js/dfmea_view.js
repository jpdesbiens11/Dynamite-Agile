/* 0.60.110 (D-O-123): reading the DFMEA -- the fold state kept per viewer and the place of the magnifier's card.
     node tests/js/dfmea_view.js   (prints "dfmea_view OK" or the failures) */
const fs = require("fs"), vm = require("vm"), path = require("path");

const store = {};
let broken = false;
const sandbox = { console, DA: { el: () => ({}), diamond: { DFMEA_COLS: [] } },
  localStorage: {
    getItem: (k) => { if (broken) throw new Error("private window"); return k in store ? store[k] : null; },
    setItem: (k, v) => { if (broken) throw new Error("private window"); store[k] = v; },
  } };
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "static/js/diamond/fm_view.js"), "utf8"), sandbox);
const D = sandbox.DA.diamond, F = D.fmFold;
const failures = [];
const check = (name, ok, got) => { if (!ok) failures.push(name + " -> " + JSON.stringify(got)); };

// 1. compact by default: nothing stored, every row folded
let s = F.foldState("DEMO");
check("folded by default", !s.all && s.ids.length === 0 && !F.isOpen(s, 7), s);
check("exported", typeof D.fmView === "function" && typeof D.fmPlace === "function", Object.keys(D));

// 2. one row unfolded, kept per Space, folded back
s = F.setOpen("DEMO", s, "7", true);
check("one open", F.isOpen(s, 7) && !F.isOpen(s, 8), s);
check("stored per Space", store["diamond.dfmea.fold.DEMO"] === '{"all":false,"ids":[7]}' && !("diamond.dfmea.fold.OTHER" in store), store);
check("read back", F.isOpen(F.foldState("DEMO"), 7) && !F.isOpen(F.foldState("OTHER"), 7), store);
s = F.setOpen("DEMO", s, 7, false);
check("folded back", !F.isOpen(s, 7) && s.ids.length === 0, s);

// 3. « Tout déplier »: every row, the new ones too; one row folded is the exception; « Tout replier » clears
s = F.setAll("DEMO", true);
check("all open", F.isOpen(s, 1) && F.isOpen(s, 999), s);
s = F.setOpen("DEMO", s, 3, false);
check("one closed among all", !F.isOpen(s, 3) && F.isOpen(s, 4) && F.foldState("DEMO").all, s);
s = F.setAll("DEMO", false);
check("all folded", !F.isOpen(s, 3) && !F.isOpen(s, 4) && store["diamond.dfmea.fold.DEMO"] === '{"all":false,"ids":[]}', s);

// 4. a damaged value or a private window: back to the default, never an error
store["diamond.dfmea.fold.BAD"] = "{not json";
check("damaged value", !F.foldState("BAD").all && F.foldState("BAD").ids.length === 0, F.foldState("BAD"));
broken = true;
let threw = false;
try { s = F.foldState("DEMO"); s = F.setOpen("DEMO", s, 5, true); F.setAll("DEMO", true); } catch (err) { threw = true; }
check("private window", !threw && F.isOpen(s, 5), s);
broken = false;

// 5. the magnifier's card: right of / below the pointer, flipped near the edges, always inside the window
let p = D.fmPlace(100, 100, 300, 200, 1440, 900);
check("right below", p.left === 118 && p.top === 118, p);
p = D.fmPlace(1400, 850, 300, 200, 1440, 900);
check("flipped", p.left === 1400 - 18 - 300 && p.top === 850 - 18 - 200, p);
p = D.fmPlace(50, 50, 2000, 1200, 1440, 900);
check("clamped", p.left === 8 && p.top === 8, p);
p = D.fmPlace(200, 880, 300, 900, 1440, 900);
check("tall card stays in", p.top >= 8 && p.top + 900 <= 900 || p.top === 8, p);

console.log(failures.length ? "FAILURES\n" + failures.join("\n") : "dfmea_view OK");
process.exit(failures.length ? 1 : 0);
