/* « Versions » page (0.60.12, D-O-024): reads updates/versions.json (built with the package by the Pages workflow) and
   shows the latest package, its SHA-256 and the versions newer than the one of the portal (#depuis=0.60.11, the link of
   Admin → Update). No call to anything but this site. */
(function () {
  "use strict";
  const EN = document.documentElement.lang === "en";
  const T = EN ? {
    yours: "Your portal: ", newer: (n) => n ? n + " newer version(s), all in the package below." : "it is up to date.",
    none: "Type the version shown in Admin → Update to see what is new for you.", get: "Download the package ", size: " KB",
    sha: "SHA-256 (compare it with the one shown in Admin → Update): ", missing: "The list of versions is built when the site is "
      + "published. Open this page on the project's website.", fresh: "new for you", date: "Published on ", label: "Your version",
  } : {
    yours: "Votre portail : ", newer: (n) => n ? n + " version(s) plus récente(s), toutes dans le paquet ci-dessous." : "il est à jour.",
    none: "Tapez la version affichée dans Admin → Update pour voir ce qui est nouveau pour vous.", get: "Télécharger le paquet ",
    size: " Ko", sha: "SHA-256 (à comparer avec celle qu'affiche Admin → Update) : ", missing: "La liste des versions est construite "
      + "à la publication du site. Ouvrez cette page sur le site du projet.", fresh: "nouvelle pour vous", date: "Publiée le ",
    label: "Votre version",
  };
  const ROOT = EN ? "../" : "";  // the package and its listing live once, at the root of the site
  const $ = (id) => document.getElementById(id);
  const tuple = (v) => (String(v || "").match(/\d+/g) || []).slice(0, 3).map(Number);
  const newer = (a, b) => { const x = tuple(a), y = tuple(b); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); } return false; };
  const node = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };

  function from() {
    const m = location.hash.match(/depuis=([\d.]+)/) || location.hash.match(/from=([\d.]+)/);
    return m ? m[1] : "";
  }

  function draw(data, mine) {
    const lang = EN ? "en" : "fr";
    const box = $("ver-pkg");
    box.textContent = "";
    const a = node("a", "btn btn-primary", T.get + data.latest + " (.zip, " + Math.round(data.bytes / 1024) + T.size + ")");
    a.href = ROOT + "updates/" + data.package;
    a.setAttribute("download", "");
    const sha = node("p", "small");
    sha.append(T.sha, node("code", "sha", data.sha256));
    box.append(a, node("p", "small", T.date + data.date), sha);
    const list = $("ver-list");
    list.textContent = "";
    let count = 0;
    data.versions.forEach((v) => {
      const fresh = mine && newer(v.version, mine);
      if (fresh) count++;
      const li = node("li", fresh ? "ok" : "");
      const head = node("b", null, v.version + " · " + v.date);
      li.append(head);
      if (fresh) li.append(node("span", "tag", T.fresh));
      li.append(node("span", null, (v.summary && (v.summary[lang] || v.summary.fr)) || ""));
      if (v.changes && v.changes.length) {
        const ul = node("ul", "small");
        v.changes.forEach((c) => ul.append(node("li", null, c)));
        li.append(ul);
      }
      list.append(li);
    });
    $("ver-yours").textContent = mine ? T.yours + mine + " — " + T.newer(count) : T.none;
  }

  function start() {
    const input = $("ver-input");
    input.setAttribute("aria-label", T.label);
    input.value = from();
    fetch(ROOT + "updates/versions.json", { cache: "no-store" }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))).then((data) => {
      draw(data, input.value);
      input.addEventListener("input", () => draw(data, input.value.trim()));
      window.addEventListener("hashchange", () => { input.value = from(); draw(data, input.value); });
    }).catch(() => { $("ver-pkg").textContent = T.missing; $("ver-yours").textContent = ""; });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
