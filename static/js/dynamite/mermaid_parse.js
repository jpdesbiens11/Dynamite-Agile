/* Dynamite - Mermaid diagrams, part 1: the parser (0.60.60, D-O-069).
   AI assistants explain code with ```mermaid blocks. The platform loads no third-party library (FONDATIONS), so the
   diagrams are drawn by its own engine: this file reads the text, mermaid_layout.js places the boxes, mermaid_svg.js
   draws them with createElementNS / textContent (no HTML string is ever parsed).

   Supported: flowchart / graph (TB, TD, BT, LR, RL; the usual shapes, links, labels, chains, &, subgraphs, classDef /
   class / style colours), sequenceDiagram (participants, actors, messages, notes, autonumber, loop / alt / opt / par /
   critical / break / rect blocks) and stateDiagram / stateDiagram-v2 ([*], transitions, descriptions, composite states,
   choice / fork / join). Any other type is shown as code with a notice. A line the engine does not understand raises an
   error that names the line, so the reader of an AI answer sees exactly where the diagram is wrong.

   DY.mermaid.parse(text) -> { kind: "flow" | "sequence", ... } or throws { line, message }. */
(function () {
  "use strict";

  const DY = DA.dynamite;
  const MM = (DY.mermaid = DY.mermaid || {});
  const KNOWN = { classDiagram: "classes", erDiagram: "entités-relations", gantt: "Gantt", pie: "secteurs", journey: "parcours",
    gitGraph: "git", mindmap: "carte mentale", timeline: "chronologie", quadrantChart: "quadrants", requirementDiagram: "requirements",
    C4Context: "C4", sankey: "Sankey", "sankey-beta": "Sankey", xychart: "XY", "xychart-beta": "XY", block: "blocs", "block-beta": "blocs",
    packet: "paquets", "packet-beta": "paquets", architecture: "architecture", "architecture-beta": "architecture", kanban: "kanban" };

  function fail(line, message) { const err = new Error(message); err.line = line; err.mermaid = true; throw err; }

  /** Label text: quotes removed, <br> and \n become line breaks, simple HTML / markdown marks removed, a few entities. */
  function label(raw) {
    let s = String(raw == null ? "" : raw).trim();
    if (/^"[\s\S]*"$/.test(s)) s = s.slice(1, -1);
    if (/^`[\s\S]*`$/.test(s)) s = s.slice(1, -1);
    s = s.replace(/<br\s*\/?>/gi, "\n").replace(/\\n/g, "\n").replace(/<[^>]{1,40}>/g, "")
      .replace(/\*\*([^*]+)\*\*/g, "$1").replace(/(^|[^*])\*([^*]+)\*/g, "$1$2")
      .replace(/#quot;/g, "\"").replace(/#amp;/g, "&").replace(/#lt;/g, "<").replace(/#gt;/g, ">").replace(/#35;/g, "#")
      .replace(/&quot;/g, "\"").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&nbsp;/g, " ");
    return s.split("\n").map((l) => l.trim()).join("\n");
  }

  /** Lines with their numbers: comments (%%) and directives (%%{…}%%) dropped, front matter skipped. */
  function lines(text) {
    const out = [];
    const raw = String(text || "").replace(/\r\n?/g, "\n").split("\n");
    let i = 0;
    if ((raw[0] || "").trim() === "---") {
      for (i = 1; i < raw.length && raw[i].trim() !== "---"; i++) { /* front matter (title, config) */ }
      i++;
    }
    for (; i < raw.length; i++) {
      const t = raw[i].replace(/%%.*$/, "").trim();
      if (t) out.push({ n: i + 1, t });
    }
    return out;
  }

  function parse(text) {
    const all = lines(text);
    if (!all.length) fail(1, "Diagramme vide.");
    const head = all[0].t;
    const word = head.split(/\s+/)[0];
    if (/^(flowchart|graph)$/i.test(word)) return flow(all, head);
    if (word === "sequenceDiagram") return sequence(all.slice(1));
    if (/^stateDiagram(-v2)?$/.test(word)) return state(all.slice(1));
    if (KNOWN[word]) fail(all[0].n, "Les diagrammes de type « " + KNOWN[word] + " » (" + word + ") ne sont pas encore dessinés par l'outil.");
    fail(all[0].n, "Type de diagramme inconnu : « " + word.slice(0, 30) + " ». Attendu : flowchart, graph, sequenceDiagram ou stateDiagram.");
    return null;
  }

  /* ------------------------------------------------------------------ flowchart ------------------------------------------------------------------ */
  const SHAPES = [ // opener, closer, shape -- longest first
    ["(((", ")))", "dcircle"], ["([", "])", "stadium"], ["((", "))", "circle"], ["[[", "]]", "subroutine"], ["[(", ")]", "cylinder"],
    ["{{", "}}", "hexagon"], ["[/", "/]", "lean_r"], ["[\\", "\\]", "lean_l"], ["[/", "\\]", "trapezoid"], ["[\\", "/]", "trapezoid_alt"],
    ["[", "]", "rect"], ["(", ")", "round"], ["{", "}", "diamond"], [">", "]", "flag"]];
  const ID_RE = /^[^\s\[\](){}<>|&;:"'=\-.~,]+(?:[.-][^\s\[\](){}<>|&;:"'=\-.~,]+)*/;
  const LINKS = [
    // label between pipes: A -->|yes| B
    [/^(<|o|x)?(-{2,}|={2,}|-\.+-|~{3,})(>|o|x)?\s*\|([^|]*)\|/, (m) => link(m[1], m[2], m[3], m[4])],
    // label inside the link: A -- yes --> B, A -. maybe .-> B, A == sure ==> B
    [/^(<|o|x)?(--|==|-\.)\s*((?:"[^"]*")|[^-=.>|"][^>|]*?)\s*(-{2,}|={2,}|\.+-)(>|o|x)/, (m) => link(m[1], m[2] + m[4], m[5], m[3])],
    [/^(<|o|x)?(-{2,}|={2,}|-\.+-|~{3,})(>|o|x)?/, (m) => link(m[1], m[2], m[3], "")]];

  function link(start, body, end, text) {
    return { style: body.includes("=") ? "thick" : body.includes(".") ? "dotted" : body.startsWith("~") ? "invisible" : "solid",
      start: start === "<" ? "arrow" : start === "o" ? "circle" : start === "x" ? "cross" : "",
      end: end === ">" ? "arrow" : end === "o" ? "circle" : end === "x" ? "cross" : "", text: label(text) };
  }

  function flow(all, head) {
    const dir = ((head.match(/^(?:flowchart|graph)\s+(TB|TD|BT|RL|LR)\b/i) || [])[1] || "TB").toUpperCase().replace("TD", "TB");
    const g = { kind: "flow", dir, nodes: new Map(), edges: [], groups: [], classes: {} };
    const stack = [];
    const statements = [];
    all.slice(1).forEach((l) => splitOutside(l.t, ";").forEach((t) => { if (t.trim()) statements.push({ n: l.n, t: t.trim() }); }));
    statements.forEach(({ n, t }) => {
      let m;
      if ((m = t.match(/^subgraph\s+(.*)$/))) {
        const rest = m[1].trim();
        const mm = rest.match(/^([^\s\[]+)\s*\[(.*)\]$/);
        const id = mm ? mm[1] : (/^".*"$/.test(rest) ? "sg" + g.groups.length : rest.split(/\s+/)[0]);
        const group = { id, title: label(mm ? mm[2] : rest), nodes: [], parent: stack.length ? stack[stack.length - 1] : null };
        g.groups.push(group);
        stack.push(group);
        return;
      }
      if (t === "end") { if (!stack.length) fail(n, "« end » sans « subgraph »."); stack.pop(); return; }
      if (/^direction\s+(TB|TD|BT|RL|LR)$/i.test(t)) return;
      if ((m = t.match(/^classDef\s+([\w,-]+)\s+(.+)$/))) { m[1].split(",").forEach((c) => { g.classes[c.trim()] = css(m[2]); }); return; }
      if ((m = t.match(/^class\s+([^\s]+)\s+([\w-]+)$/))) {
        m[1].split(",").forEach((id) => { const node = g.nodes.get(id.trim()); if (node) node.cls = m[2]; });
        return;
      }
      if ((m = t.match(/^style\s+([^\s]+)\s+(.+)$/))) { const node = g.nodes.get(m[1]); if (node) node.style = css(m[2]); return; }
      if (/^(linkStyle|click|accTitle|accDescr|title)\b/.test(t)) return;
      chain(g, t, n, stack);
    });
    if (stack.length) fail(all[all.length - 1].n, "« subgraph " + stack[stack.length - 1].id + " » sans « end ».");
    g.nodes = Array.from(g.nodes.values());
    return g;
  }

  function css(text) {
    const out = {};
    text.split(",").forEach((part) => {
      const m = part.match(/^\s*(fill|stroke|color|stroke-width|stroke-dasharray)\s*:\s*([#\w.() %-]{1,40})\s*$/);
      if (m) out[m[1]] = m[2].trim();
    });
    return out;
  }

  function splitOutside(text, sep) {
    const out = [];
    let cur = "", quote = false, depth = 0;
    for (const c of text) {
      if (c === "\"") quote = !quote;
      else if (!quote && "[({".includes(c)) depth++;
      else if (!quote && "])}".includes(c)) depth = Math.max(0, depth - 1);
      if (c === sep && !quote && depth === 0) { out.push(cur); cur = ""; } else cur += c;
    }
    out.push(cur);
    return out;
  }

  /** A [& B] --> C [& D] -->|x| E … : node groups separated by links. */
  function chain(g, text, n, stack) {
    let pos = 0;
    const ws = () => { while (pos < text.length && /\s/.test(text[pos])) pos++; };
    const group = () => {
      const ids = [];
      for (;;) {
        ws();
        ids.push(nodeRef(g, text, pos, n, stack, (p) => { pos = p; }));
        ws();
        if (text[pos] === "&") { pos++; continue; }
        return ids;
      }
    };
    let left = group();
    for (;;) {
      ws();
      if (pos >= text.length) return;
      const rest = text.slice(pos);
      let found = null;
      for (const [re, make] of LINKS) {
        const m = rest.match(re);
        if (m) { found = make(m); pos += m[0].length; break; }
      }
      if (!found) fail(n, "Lien ou forme incompris près de « " + rest.slice(0, 25) + " ».");
      const right = group();
      left.forEach((a) => right.forEach((b) => g.edges.push(Object.assign({ from: a, to: b }, found))));
      left = right;
    }
  }

  function nodeRef(g, text, pos, n, stack, setPos) {
    const m = text.slice(pos).match(ID_RE);
    if (!m) fail(n, "Nom de nœud attendu près de « " + text.slice(pos, pos + 25) + " ».");
    const id = m[0];
    pos += id.length;
    let shape = null, txt = null;
    for (const [open, close, kind] of SHAPES) {
      if (!text.startsWith(open, pos)) continue;
      const start = pos + open.length;
      let end;
      if (text[start] === "\"") {
        const q = text.indexOf("\"", start + 1);
        end = q < 0 ? -1 : text.indexOf(close, q + 1) === q + 1 ? q + 1 : -1;
      } else {
        end = text.indexOf(close, start);
      }
      if (end < 0) continue;
      shape = kind;
      txt = text.slice(start, end);
      pos = end + close.length;
      break;
    }
    if (shape === null && /^[\[({>]/.test(text.slice(pos))) fail(n, "Forme du nœud « " + id + " » non fermée.");
    let cls = "";
    const c = text.slice(pos).match(/^:::([\w-]+)/);
    if (c) { cls = c[1]; pos += c[0].length; }
    let node = g.nodes.get(id);
    if (!node) {
      node = { id, text: id, shape: "rect", cls: "" };
      g.nodes.set(id, node);
    }
    if (stack.length) {  // a node named inside a subgraph belongs to it (Mermaid's rule), even if it was declared before
      const top = stack[stack.length - 1];
      if (!top.nodes.includes(id)) {
        g.groups.forEach((gr) => { if (gr !== top) gr.nodes = gr.nodes.filter((x) => x !== id); });
        top.nodes.push(id);
      }
    }
    if (shape) { node.shape = shape; node.text = label(txt); }
    if (cls) node.cls = cls;
    setPos(pos);
    return id;
  }

  /* ------------------------------------------------------------------ state ------------------------------------------------------------------ */
  function state(all) {
    const g = { kind: "flow", dir: "TB", nodes: new Map(), edges: [], groups: [], classes: {}, state: true };
    const stack = [];
    const scope = () => (stack.length ? stack[stack.length - 1].id : "");
    const composite = new Set();
    const add = (id) => {
      const real = id, shape = "round", text = id;
      if (id === "[*]" || composite.has(id)) return id;
      if (!g.nodes.has(real)) {
        g.nodes.set(real, { id: real, text, shape, cls: "" });
        if (stack.length) stack[stack.length - 1].nodes.push(real);
      }
      return real;
    };
    const pseudo = (kind) => {
      const id = "[*]" + kind + "@" + scope();
      if (!g.nodes.has(id)) {
        g.nodes.set(id, { id, text: "", shape: kind === "start" ? "start" : "end", cls: "" });
        if (stack.length) stack[stack.length - 1].nodes.push(id);
      }
      return id;
    };
    let note = false;
    all.forEach(({ n, t }) => {
      let m;
      if (note) { if (/^end note$/i.test(t)) note = false; return; }
      if (/^note\s+(left|right)\s+of\s+[^:]+$/i.test(t)) { note = true; return; }
      if (/^note\s/i.test(t) || /^(direction|classDef|class|style|accTitle|accDescr|title)\b/.test(t) || t === "--") {
        if ((m = t.match(/^direction\s+(TB|TD|BT|RL|LR)$/i)) && !stack.length) g.dir = m[1].toUpperCase().replace("TD", "TB");
        return;
      }
      if ((m = t.match(/^state\s+"([^"]*)"\s+as\s+([^\s{]+)\s*(\{)?$/))) {
        const id = add(m[2]); g.nodes.get(id).text = label(m[1]);
        if (m[3]) open(id);
        return;
      }
      if ((m = t.match(/^state\s+([^\s{]+)\s*<<(choice|fork|join)>>$/))) {
        const id = add(m[1]); const node = g.nodes.get(id);
        node.shape = m[2] === "choice" ? "diamond" : "bar"; node.text = "";
        return;
      }
      if ((m = t.match(/^state\s+([^\s{]+)\s*\{$/))) { open(add(m[1])); return; }
      if ((m = t.match(/^state\s+([^\s{]+)$/))) { add(m[1]); return; }
      if (t === "}") { if (!stack.length) fail(n, "« } » sans état composé ouvert."); stack.pop(); return; }
      if ((m = t.match(/^(\S+)\s*-->\s*(\S+?)\s*(?::\s*(.*))?$/))) {
        const a = m[1] === "[*]" ? pseudo("start") : add(m[1]);
        const b = m[2] === "[*]" ? pseudo("end") : add(m[2]);
        g.edges.push({ from: a, to: b, style: "solid", start: "", end: "arrow", text: label(m[3] || "") });
        return;
      }
      if ((m = t.match(/^([^\s:]+)\s*:\s*(.+)$/))) {
        const id = add(m[1]); const node = g.nodes.get(id);
        node.text = node.text === id ? label(m[2]) : node.text + "\n" + label(m[2]);
        return;
      }
      if (/^[^\s:]+$/.test(t)) { add(t); return; }
      fail(n, "Ligne incomprise : « " + t.slice(0, 40) + " ».");
    });
    function open(id) {
      const group = { id, title: g.nodes.get(id).text, nodes: [], parent: stack.length ? stack[stack.length - 1] : null };
      g.nodes.delete(id);  // the composite state is drawn as its box
      composite.add(id);
      if (group.parent) group.parent.nodes = group.parent.nodes.filter((x) => x !== id);
      g.groups.push(group);
      stack.push(group);
    }
    if (stack.length) fail(all.length ? all[all.length - 1].n : 1, "État composé « " + stack[stack.length - 1].id + " » sans « } ».");
    // a transition to a composite state goes to its first inner state
    const firstOf = {}, lastOf = {};
    g.groups.forEach((gr) => {
      firstOf[gr.id] = gr.nodes.find((x) => x.startsWith("[*]start")) || gr.nodes[0];
      lastOf[gr.id] = gr.nodes.find((x) => x.startsWith("[*]end")) || gr.nodes[gr.nodes.length - 1];
    });
    g.edges = g.edges.map((e) => Object.assign(e, { from: g.nodes.has(e.from) ? e.from : lastOf[e.from] || e.from,
      to: g.nodes.has(e.to) ? e.to : firstOf[e.to] || e.to })).filter((e) => g.nodes.has(e.from) && g.nodes.has(e.to));
    g.nodes = Array.from(g.nodes.values());
    return g;
  }

  /* ------------------------------------------------------------------ sequence ------------------------------------------------------------------ */
  const ARROWS = ["<<-->>", "<<->>", "-->>", "->>", "--x", "-x", "--)", "-)", "-->", "->"];

  function sequence(all) {
    const d = { kind: "sequence", actors: [], items: [], autonumber: false };
    const byId = new Map();
    const actor = (id, kind, text) => {
      id = id.trim();
      if (!byId.has(id)) { const a = { id, text: label(text || id), kind: kind || "participant" }; byId.set(id, a); d.actors.push(a); }
      else if (text) byId.get(id).text = label(text);
      if (kind) byId.get(id).kind = kind;
      return byId.get(id);
    };
    const frames = [];
    all.forEach(({ n, t }) => {
      let m;
      if ((m = t.match(/^(participant|actor)\s+(.+?)(?:\s+as\s+(.+))?$/))) { actor(m[2], m[1], m[3]); return; }
      if ((m = t.match(/^create\s+(participant|actor)\s+(.+?)(?:\s+as\s+(.+))?$/))) { actor(m[2], m[1], m[3]); return; }
      if (/^(autonumber)\b/.test(t)) { d.autonumber = true; return; }
      if (/^(activate|deactivate|destroy|box|title|accTitle|accDescr|links?|properties|details)\b/.test(t)) {
        if (/^box\b/.test(t)) frames.push({ box: true });
        return;
      }
      if ((m = t.match(/^note\s+(left of|right of|over)\s+([^:]+):\s*(.*)$/i))) {
        const who = m[2].split(",").map((x) => actor(x).id);
        d.items.push({ type: "note", side: m[1].toLowerCase(), who, text: label(m[3]) });
        return;
      }
      if ((m = t.match(/^(loop|alt|opt|par|critical|break|rect)\b\s*(.*)$/))) {
        const f = { type: "frame", kind: m[1], text: m[1] === "rect" ? "" : label(m[2]) };
        frames.push(f); d.items.push(f); return;
      }
      if ((m = t.match(/^(else|and|option)\b\s*(.*)$/))) {
        if (!frames.length) fail(n, "« " + m[1] + " » hors d'un bloc alt, par ou critical.");
        d.items.push({ type: "section", text: label(m[2]) }); return;
      }
      if (t === "end") {
        if (!frames.length) fail(n, "« end » sans bloc ouvert.");
        const f = frames.pop();
        if (!f.box) d.items.push({ type: "endframe" });
        return;
      }
      const msg = message(t);
      if (msg) {
        const from = actor(msg.from).id, to = actor(msg.to).id;
        d.items.push({ type: "message", from, to, arrow: msg.arrow, text: label(msg.text) });
        return;
      }
      fail(n, "Ligne incomprise : « " + t.slice(0, 40) + " ».");
    });
    if (frames.some((f) => !f.box)) fail(all.length ? all[all.length - 1].n : 1, "Bloc « " + frames[frames.length - 1].kind + " » sans « end ».");
    if (!d.actors.length) fail(1, "Aucun participant.");
    return d;
  }

  function message(t) {
    const colon = t.indexOf(":");
    const head = colon < 0 ? t : t.slice(0, colon);
    for (const a of ARROWS) {
      const i = head.indexOf(a);
      if (i <= 0) continue;
      const from = head.slice(0, i).trim();
      const to = head.slice(i + a.length).trim().replace(/^[+-]/, "").trim();
      if (!from || !to) continue;
      return { from, to, arrow: a, text: colon < 0 ? "" : t.slice(colon + 1).trim() };
    }
    return null;
  }

  /** Does this code look like a Mermaid diagram (a code block an AI pasted without its language)? */
  function looks(text) {
    const first = lines(text)[0];
    return !!first && /^(flowchart|graph)\s+(TB|TD|BT|RL|LR)\b|^(sequenceDiagram|stateDiagram(-v2)?|classDiagram|erDiagram|gantt)\s*$/.test(first.t);
  }

  Object.assign(MM, { parse, looks, label });
})();
