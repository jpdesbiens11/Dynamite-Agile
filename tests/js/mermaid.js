/* 0.60.60 (D-O-069): the Mermaid engine of Dynamite -- parse, layout and drawing of the diagrams AI assistants write.
     node tests/js/mermaid.js   (prints "mermaid OK" or the failures) */
const fs = require("fs"), vm = require("vm"), path = require("path");

function fakeNode(tag) {
  return { tag, attrs: {}, kids: [], textContent: "", hidden: false,
    setAttribute(k, v) { this.attrs[k] = v; }, getAttribute(k) { return this.attrs[k]; },
    appendChild(k) { this.kids.push(k); return k; }, append(...k) { this.kids.push(...k); }, addEventListener() {} };
}
const document = { createElementNS: (ns, tag) => fakeNode(tag), createElement: (tag) => fakeNode(tag), body: {} };
const el = (tag, attrs, ...kids) => { const n = fakeNode(tag); Object.assign(n.attrs, attrs || {}); kids.flat().forEach((k) => k && n.kids.push(k)); return n; };
const sandbox = { window: {}, document, console, getComputedStyle: () => ({}), DA: { dynamite: {}, el } };
sandbox.window = sandbox; vm.createContext(sandbox);
for (const f of ["mermaid_parse.js", "mermaid_layout.js", "mermaid_svg.js", "mermaid_seq.js"]) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "static/js/dynamite", f), "utf8"), sandbox);
}
const MM = sandbox.DA.dynamite.mermaid;
const failures = [];
const check = (name, ok, got) => { if (!ok) failures.push(name + " -> " + JSON.stringify(got)); };
const count = (node, tag) => (node.tag === tag ? 1 : 0) + (node.kids || []).reduce((s, k) => s + (k && k.tag ? count(k, tag) : 0), 0);
const texts = (node) => (node.tag === "tspan" ? [node.textContent] : []).concat(...(node.kids || []).map((k) => (k && k.tag ? texts(k) : [])));

// 1. a flowchart as an AI writes it to explain a module
const flow = `flowchart TD
    %% request path
    A[Client HTTP] -->|POST /api/login| B{CSRF valide ?}
    B -- non --> C[403 Forbidden]
    B -- oui --> D(Vérifier le mot de passe)
    D --> E[(SQLite users)]
    D -.-> F[["audit.log_action()"]]
    E --> G([Session créée]) & H>Cookie HttpOnly]
    subgraph Serveur [Serveur Python]
      D
      E
    end
    classDef danger fill:#fdd,stroke:#c00
    class C danger
    G --> A`;
const g = MM.parse(flow);
check("flow kind", g.kind === "flow" && g.dir === "TB", g.dir);
check("flow nodes", g.nodes.length === 8, g.nodes.map((n) => n.id));
check("flow shapes", ["diamond", "round", "cylinder", "subroutine", "stadium", "flag"].every((sh) => g.nodes.some((n) => n.shape === sh)), g.nodes.map((n) => n.shape));
check("flow labels", g.edges.find((e) => e.from === "A").text === "POST /api/login" && g.edges.find((e) => e.to === "C").text === "non", g.edges);
check("flow dotted", g.edges.find((e) => e.to === "F").style === "dotted", g.edges.find((e) => e.to === "F"));
check("flow &", g.edges.filter((e) => e.from === "E").length === 2, g.edges);
check("flow class", g.nodes.find((n) => n.id === "C").cls === "danger" && g.classes.danger.fill === "#fdd", g.classes);
check("flow subgraph", g.groups.length === 1 && g.groups[0].title === "Serveur Python", g.groups);
const L = MM.layout(g, (t) => ({ w: String(t).length * 7, h: t ? 17 : 0 }));
check("layout all nodes", L.nodes.length === 8 && L.nodes.every((n) => isFinite(n.x) && isFinite(n.y)), L.nodes);
const at = (id) => L.nodes.find((n) => n.id === id);
check("layout top-down", at("A").y < at("B").y && at("B").y < at("D").y && at("D").y < at("E").y, [at("A").y, at("B").y, at("D").y]);
const overlap = L.nodes.some((a, i) => L.nodes.some((b, j) => j > i && Math.abs(a.x - b.x) < (a.w + b.w) / 2 && Math.abs(a.y - b.y) < (a.h + b.h) / 2));
check("layout no overlap", !overlap, L.nodes.map((n) => [n.id, n.x, n.y]));
check("layout cycle kept", L.edges.some((e) => e.from === "G" && e.to === "A" && e.points.length >= 2), L.edges.length);
check("layout group box", L.groups.length === 1 && L.groups[0].w > 0, L.groups);
const svg = MM.draw(flow);
check("draw flow", svg.tag === "svg" && count(svg, "path") >= 8 && texts(svg).includes("Client HTTP"), texts(svg));

// 2. left to right, chains, quoted labels with brackets, <br>
const lr = MM.parse('graph LR\n  a["Lire (config)"] --> b["Valider<br/>schéma"] --> c[OK]\n  a ==> c');
check("lr chain", lr.dir === "LR" && lr.edges.length === 3 && lr.nodes[0].text === "Lire (config)" && lr.nodes[1].text === "Valider\nschéma", lr);
check("lr thick", lr.edges[2].style === "thick", lr.edges[2]);
const LL = MM.layout(lr, (t) => ({ w: 60, h: 17 }));
check("lr left to right", LL.nodes[0].x < LL.nodes[1].x && LL.nodes[1].x < LL.nodes[2].x, LL.nodes.map((n) => n.x));

// 3. sequence diagram
const seq = `sequenceDiagram
    autonumber
    actor U as Utilisateur
    participant W as Navigateur
    participant S as Serveur
    U->>W: Clique « Enregistrer »
    W->>+S: PUT /api/page (CSRF)
    alt jeton valide
        S-->>W: 200 OK
    else jeton absent
        S--xW: 403
    end
    loop toutes les 30 s
        W-)S: ping
    end
    Note over W,S: HTTPS TLS 1.3
    S->>S: journal d'audit`;
const d = MM.parse(seq);
check("seq actors", d.actors.map((a) => a.text).join("|") === "Utilisateur|Navigateur|Serveur" && d.actors[0].kind === "actor", d.actors);
check("seq items", d.items.filter((i) => i.type === "message").length === 6 && d.items.some((i) => i.type === "section"), d.items);
check("seq arrows", d.items.find((i) => i.text === "403").arrow === "--x", d.items);
const sq = MM.draw(seq);
check("draw seq", sq.tag === "svg" && texts(sq).includes("PUT /api/page (CSRF)") && texts(sq).includes("[jeton valide]"), texts(sq));

// 4. state diagram
const st = `stateDiagram-v2
    [*] --> Brouillon
    Brouillon --> Revue : soumettre
    state Revue {
      [*] --> Lecture
      Lecture --> Commentaires
    }
    Revue --> Publié : approuver
    state choix <<choice>>
    Publié --> choix
    choix --> Archivé : si obsolète
    Archivé --> [*]`;
const sg = MM.parse(st);
check("state nodes", sg.nodes.some((n) => n.shape === "start") && sg.nodes.some((n) => n.shape === "end") && sg.nodes.some((n) => n.shape === "diamond"), sg.nodes);
check("state composite", sg.groups.length === 1 && sg.groups[0].nodes.includes("Lecture"), sg.groups);
check("state into composite", sg.edges.some((e) => e.from === "Brouillon" && e.text === "soumettre" && e.to.startsWith("[*]start@Revue")), sg.edges);
check("draw state", MM.draw(st).tag === "svg", "");

// 5. errors name the line; other types say so
const err = (src) => { try { MM.parse(src); return null; } catch (e) { return e; } };
const e1 = err("flowchart TD\n  A --> B\n  C -=> D");
check("error line", e1 && e1.mermaid && e1.line === 3, e1 && [e1.line, e1.message]);
const e2 = err("classDiagram\n  class A");
check("unsupported type", e2 && /classes/.test(e2.message), e2 && e2.message);
const e3 = err("flowchart TD\n  subgraph X\n  A --> B");
check("missing end", e3 && /sans « end »/.test(e3.message), e3 && e3.message);
check("looks", MM.looks("graph TD\nA-->B") && MM.looks("sequenceDiagram\nA->>B: x") && !MM.looks("print('graph TD')"), "");

// 6. the figure: drawing + code, or the reason + code
const fig = MM.figure("flowchart LR\n A --> B");
check("figure ok", fig.attrs.class === "dy-mm" && count(fig, "svg") === 1 && count(fig, "pre") === 1, fig.attrs);
const bad = MM.figure("flowchart LR\n A --> B[");
check("figure failed", bad.attrs.class === "dy-mm dy-mm-failed" && JSON.stringify(bad).includes("Ligne 2"), JSON.stringify(bad).slice(0, 200));

if (failures.length) { console.log(failures.join("\n")); process.exit(1); }
console.log("mermaid OK");
