/* 0.60.124 (D-O-137): Golden Nuggets -- the guide of each part and the document of one part or of the four (D.nuggetBlocks),
   the blocks the PDF and Word exports send to the server.
     node tests/js/nuggets_export.js              (prints "nuggets export OK" or the failures)
     node tests/js/nuggets_export.js --dump out.json   (also writes {one: blocks, all: blocks} for tests/test_diamond_nuggets_export.py) */
const fs = require("fs"), vm = require("vm"), path = require("path");

const el = (tag, attrs, ...kids) => ({ tag, attrs: attrs || {}, kids: kids.flat() });
const sandbox = { console, DA: { el, api: {}, clear() {}, modal() {}, toast() {}, agile: { views: {} } } };
sandbox.window = sandbox; vm.createContext(sandbox);
for (const f of ["nuggets_content.js", "nuggets_disruption.js", "nuggets_guide.js", "nuggets.js", "nuggets_export.js"]) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "static/js/diamond", f), "utf8"), sandbox);
}
const D = sandbox.DA.diamond;
const failures = [];
const check = (name, ok, got) => { if (!ok) failures.push(name + " -> " + JSON.stringify(got)); };
const heads = (blocks, level) => blocks.filter((b) => b.type === "h" && b.level === level).map((b) => b.text);
const cards = (blocks) => blocks.filter((b) => b.type === "card");

// 1. the guide: the collection and each part, the five headings, none empty
const keys = D.NUGGETS.GUIDE_HEADS.map(([k]) => k);
check("five headings", JSON.stringify(keys) === '["context","problem","scope","use","cards"]', keys);
for (const part of ["intro", "principles", "algorithm", "rules", "disruption"]) {
  const g = D.NUGGETS.GUIDE[part];
  check(part + " guide", g && keys.every((k) => (Array.isArray(g[k]) ? g[k].length >= 3 && g[k].every((t) => t.length > 20) : (g[k] || "").length > 80)),
    part);
}

// 2. one part: its title, its guide, its cards only -- no intro of the collection
const one = D.nuggetBlocks(["algorithm"]);
check("one part: one chapter", JSON.stringify(heads(one, 1)) === JSON.stringify(["L'algorithme de conception en 5 étapes"]), heads(one, 1));
check("one part: its guide", heads(one, 3).join("|") === D.NUGGETS.GUIDE_HEADS.map(([, l]) => l).join("|"), heads(one, 3));
check("one part: its 5 cards", JSON.stringify(cards(one).map((c) => c.code)) === '["A1","A2","A3","A4","A5"]', cards(one).map((c) => c.code));
const steps = one.filter((b) => b.type === "ol");
check("use is numbered", steps.length === 1 && steps[0].items.length === 6, steps);
check("one part opens on its chapter", one[0].type === "h" && one[0].level === 1, one[0]);
check("no guide, four parts: opens on a heading", D.nuggetBlocks([], { guide: false })[0].type === "h", D.nuggetBlocks([], { guide: false })[0]);

// 3. the four parts: the intro of the collection, then the four in the order of the tabs, the book and the 12 cases
const all = D.nuggetBlocks(["principles", "algorithm", "rules", "disruption"]);
check("all: intro then four parts", heads(all, 1).length === 5 && heads(all, 1)[0] === "Pourquoi Golden Nuggets", heads(all, 1));
check("all: 20 + 5 + 5 + 20 + 12 cards", cards(all).length === 62, cards(all).length);
check("all: the book", heads(all, 2).includes("Le livre et ses suites"), heads(all, 2));
check("empty choice = all", D.nuggetBlocks([]).length === all.length, D.nuggetBlocks([]).length);

// 4. without the guides: the cards and the lead of each part only
const bare = D.nuggetBlocks(["principles"], { guide: false });
check("no guide", !heads(bare, 3).includes("Contexte") && cards(bare).length === 20, heads(bare, 3));
check("pdf builder of 0.60.123 = the four parts", D.pdfBuilders.nuggets().length === all.length, D.pdfBuilders.nuggets().length);
check("dialog registered", typeof D.docExporters.nuggets === "function", Object.keys(D.docExporters));

const at = process.argv.indexOf("--dump");
if (at > 0) fs.writeFileSync(process.argv[at + 1], JSON.stringify({ one, all }));
if (failures.length) { console.log(failures.join("\n")); process.exit(1); }
console.log("nuggets export OK");
