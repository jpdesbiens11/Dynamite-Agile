/* D-B-018: Markdown written by an AI agent -> Dynamite page JSON.
     node tests/js/ai_markdown.js   (prints "ai markdown OK" or the failures) */
const fs = require("fs"), vm = require("vm"), path = require("path");
const sandbox = { window: {}, document: { createTextNode: () => ({}) }, console, atob: (s) => Buffer.from(s, "base64").toString("binary"),
  DA: { dynamite: {}, api: {}, el: () => ({}), clear: () => {}, toast: () => {} } };
sandbox.window = sandbox; vm.createContext(sandbox);
for (const f of ["editor.js", "ai_import.js"]) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "static/js/dynamite", f), "utf8"), sandbox);
}
const DY = sandbox.DA.dynamite;
const failures = [];
const check = (name, ok, got) => { if (!ok) failures.push(name + " -> " + JSON.stringify(got)); };

const md = [
  "## Architecture du firmware",
  "",
  "#### Détail niveau 4",
  "Le module utilise un __thermistor__ et un _contrôleur_ dédié ; voir https://example.org/doc.",
  "",
  "* point un avec `snake_case_name`",
  "+ point deux",
  "- [ ] à faire",
  "- [x] fait",
  "",
  "1) premier",
  "2) second",
  "",
  "| Paramètre | Valeur | Réf. |",
  "|:---|---:|:---:|",
  "| Tension | 120 V | [IEC 60335](https://example.org/iec60335) |",
  "",
  "> [!WARNING]",
  "> Ne jamais **court-circuiter** la buse.",
  "",
  "~~~python",
  "print('a_b_c')",
  "~~~",
  "",
  "![Schéma](https://example.org/schema.png)",
  "",
  "Texte avant ![Capture](data:image/png;base64,iVBORw0KGgo=) texte après.",
  "",
  "***",
].join("\n");

const images = [];
const raw = DY.parse(DY.aiImport.markdownToShort(md, images));
const doc = DY.aiImport.expand(raw, images, { 1: 42 });
const c = doc.content;
const text = (nodes) => (nodes || []).map((n) => n.text || "").join("");

check("h2", c[0].type === "heading" && c[0].level === 2 && text(c[0].content) === "Architecture du firmware", c[0]);
check("h4 -> h3", c[1].type === "heading" && c[1].level === 3, c[1]);
const p = c[2].content;
check("__bold__", p.some((n) => n.text === "thermistor" && n.marks.includes("bold")), p);
check("_italic_", p.some((n) => n.text === "contrôleur" && n.marks.includes("italic")), p);
check("bare url", p.some((n) => n.marks && n.marks.some((m) => m.href === "https://example.org/doc")), p);
const bullets = c[3];
check("bullets merged", bullets.type === "bullet_list" && bullets.items.length === 4, bullets);
check("snake_case kept in code", text(bullets.items[0][0].content).includes("snake_case_name"), bullets.items[0]);
check("task list", text(bullets.items[2][0].content).startsWith("☐") && text(bullets.items[3][0].content).startsWith("☑"), bullets.items);
check("ordered 1)", c[4].type === "ordered_list" && c[4].items.length === 2, c[4]);
const table = c[5];
check("gfm table", table.type === "table" && table.header && table.rows.length === 2 && table.rows[0].length === 3, table);
check("link in cell", table.rows[1][2][0].marks[0].href === "https://example.org/iec60335", table.rows[1][2]);
check("callout -> panel", c[6].type === "panel" && c[6].kind === "warning"
  && c[6].content[0].content.some((n) => n.text === "court-circuiter" && n.marks.includes("bold")), c[6]);
check("~~~ fence", c[7].type === "code" && c[7].lang === "python" && c[7].text === "print('a_b_c')", c[7]);
check("external image -> link", c[8].type === "paragraph" && c[8].content[0].marks[0].href === "https://example.org/schema.png", c[8]);
check("data image split", c[9].type === "paragraph" && c[10].type === "image" && c[10].id === 42
  && c[10].alt === "Capture" && c[11].type === "paragraph", c.slice(9, 12));
check("rule", c[12].type === "rule", c[12]);
check("images collected", images.length === 2 && images[1].src.startsWith("data:image/png"), images);

check("detect markdown", DY.looksLikeMarkdown("## Titre\ntexte") && DY.looksLikeMarkdown("- a\n- **b**"), null);
check("plain text not markdown", !DY.looksLikeMarkdown("Bonjour,\nvoici la réponse - merci."), null);
check("no marker left", !JSON.stringify(doc).includes(""), doc);

console.log(failures.length ? "AI MARKDOWN FAILURES\n" + failures.join("\n") : "ai markdown OK");
process.exitCode = failures.length ? 1 : 0;
