/* 0.60.107 (D-O-119): the Budget Lines of a Funding Space fold by sub-project (the label before « · »).
     node tests/js/timesheet_fold.js   (prints "timesheet_fold OK" or the failures) */
const fs = require("fs"), vm = require("vm"), path = require("path");

const el = (tag, attrs, ...kids) => ({ tag, attrs: attrs || {}, kids: kids.flat(), hidden: false,
  listeners: {}, setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
  addEventListener(type, fn) { this.listeners[type] = fn; } });
const store = {};
const sandbox = { console, DA: { el }, localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = v; } } };
sandbox.window = sandbox; vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "static/js/timesheet/fold.js"), "utf8"), sandbox);
const TS = sandbox.DA.timesheet;
const failures = [];
const check = (name, ok, got) => { if (!ok) failures.push(name + " -> " + JSON.stringify(got)); };

// 1. a label cut at its first « · »; no prefix -> ""
check("split", JSON.stringify(TS.splitLabel("4. Conception détaillée · Gestion thermique · plaque")) === '["4. Conception détaillée","Gestion thermique · plaque"]', TS.splitLabel("4. Conception détaillée · Gestion thermique · plaque"));
check("split none", JSON.stringify(TS.splitLabel("Réunions")) === '["","Réunions"]', TS.splitLabel("Réunions"));

// 2. groups in order of first appearance; a line added at the end joins its sub-project
const tasks = [{ key: "PR-PM1", label: "1. Gestion · Suivi" }, { key: "PR-MEC", label: "4. Conception · Mécanique" },
  { key: "PR-PM2", label: "1. Gestion · Revues" }, { key: "INT-VAC", label: "Vacation" }];
const groups = TS.groupTasks(tasks);
check("group names", groups.map((g) => g.name).join("|") === "1. Gestion|4. Conception|", groups.map((g) => g.name));
check("late line joins", groups[0].tasks.map((t) => t.key).join(",") === "PR-PM1,PR-PM2", groups[0].tasks);

// 3. the chevron: open by default, folds its targets, remembers per key, [new] badge on the Funding Space only
const target = { hidden: false };
const btn = TS.foldButton("x.starter-demo", "DEMO", [target]);
btn.init();
check("open by default", btn.attrs["aria-expanded"] === "true" && !target.hidden, btn.attrs);
check("set badge", btn.attrs["data-new"] === "0.60.107-ts-fold", btn.attrs);
btn.listeners.click({ preventDefault() {} });
check("folded", btn.attrs["aria-expanded"] === "false" && target.hidden && btn.attrs["aria-label"] === "Déplier DEMO", btn.attrs);
check("remembered", store["da.timesheet.fold.x.starter-demo"] === "0", store);
const again = TS.foldButton("x.starter-demo", "DEMO", [{ hidden: false }]);
again.init();
check("restored folded", again.attrs["aria-expanded"] === "false", again.attrs);
const sub = TS.foldButton("x.starter-demo.4. Conception", "4. Conception", []);
check("no badge on a sub-project", !sub.attrs["data-new"], sub.attrs);

// 4. the week view's <select>: one <optgroup> per sub-project, the lines without a prefix stay plain options
const opts = TS.taskOptions(tasks, (t, text) => el("option", { value: t.key }, text)).flat();
check("optgroups", opts.filter((o) => o.tag === "optgroup").map((o) => o.attrs.label).join("|") === "1. Gestion|4. Conception", opts);
check("plain leave", opts.some((o) => o.tag === "option" && o.attrs.value === "INT-VAC"), opts);
check("text without prefix", opts[0].kids[0].kids[0] === "Suivi", opts[0]);

console.log(failures.length ? "FAILURES\n" + failures.join("\n") : "timesheet_fold OK");
process.exit(failures.length ? 1 : 0);
