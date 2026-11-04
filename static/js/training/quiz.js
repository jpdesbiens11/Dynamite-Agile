/* Training test page (D-A-045; circle-back 0.50.10, D-B-128): #/training/test/<item id>.
   The employee answers the whole test and gets his mark at the end. At or above the pass mark the item becomes
   « Completed » (green). Below it, only the missed questions come back (options shuffled), round after round, until
   each one is answered right -- then the item is Completed too. The server grades; right answers and explanations of
   a question still missed are never sent. A page, not a dialog: no scroll bar inside a window (D-B-118). el() only. */
(function () {
  "use strict";
  const { api, el, clear, toast } = DA;
  const TR = (DA.training = DA.training || {});

  function shuffled(list) {
    const out = list.slice();
    for (let i = out.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  }

  const refLink = (it) => (it.reference ? el("a", { href: it.reference, class: "tr-ref" }, it.ref_label || it.reference) : null);

  function scoreCard(r, item) {
    const done = r.passed;
    const head = r.mode === "full"
      ? el("p", { class: "tr-score-big" }, r.score + " %", el("span", { class: "tr-score-sub" }, " " + r.right + " / " + r.total + " · seuil " + r.pass + " %"))
      : el("p", { class: "tr-score-big" }, r.right + " / " + r.total, el("span", { class: "tr-score-sub" }, " réussies dans cette reprise · note du test "
        + r.first + " %"));
    let line;
    if (done && r.mode === "full") line = "Test réussi : la formation passe à « Completed ». Votre gestionnaire l'évalue, puis coche « Achieved ».";
    else if (done) line = "Toutes les questions manquées sont maintenant réussies : la formation passe à « Completed ». "
      + "Votre gestionnaire voit votre note du test (" + r.first + " %).";
    else if (r.mode === "full") line = "Sous le seuil de " + r.pass + " % : les " + r.remaining.length + " question(s) manquée(s) vont revenir, "
      + "jusqu'à ce que chacune soit réussie. Les bonnes réponses ne sont pas montrées : relisez la référence avant de reprendre.";
    else line = r.remaining.length + " question(s) encore à reprendre. Relisez la référence, puis reprenez.";
    return el("section", { class: "tr-score " + (done ? "tr-pass" : "tr-fail"), role: "status", "aria-live": "polite" },
      head, el("p", null, line), done ? null : el("p", { class: "tr-meta" }, "Référence : ", refLink(item) || "—"));
  }

  function questionBlock(question, n, shuffle) {
    const order = shuffle ? shuffled(question.options.map((t, j) => [t, j])) : question.options.map((t, j) => [t, j]);
    const inputs = order.map(([, j]) => el("input", { type: question.multiple ? "checkbox" : "radio", name: "q" + question.index, value: String(j) }));
    const labels = order.map(([text, j], k) => el("label", { class: "tr-option", "data-opt": String(j) }, inputs[k], el("span", null, text)));
    const fs = el("fieldset", { class: "tr-question", "data-q": String(question.index) },
      el("legend", null, n + ". " + question.text + (question.multiple ? " (plusieurs réponses)" : "")), labels);
    return { fs, inputs, question };
  }

  function showReview(blocks, review) {
    const byIndex = new Map(review.map((rv) => [rv.index, rv]));
    blocks.forEach((b) => {
      const rv = byIndex.get(b.question.index);
      if (!rv) return;
      b.inputs.forEach((input) => { input.disabled = true; });
      b.fs.classList.add(rv.ok ? "tr-ok" : "tr-ko");
      b.fs.append(el("p", { class: "tr-verdict" }, rv.ok ? "✓ Réussie" : "✗ Manquée — elle reviendra"));
      if (rv.right) b.fs.querySelectorAll("label").forEach((lab) => { if (rv.right.includes(Number(lab.dataset.opt))) lab.classList.add("tr-right"); });
      if (rv.explain) b.fs.append(el("p", { class: "tr-explain" }, rv.explain));
    });
  }

  TR.testView = async function (main, iid) {
    const q = await api.get("/api/training/items/" + iid + "/quiz");
    const item = q.item;
    const cb = q.circle_back;
    const back = el("a", { class: "btn btn-small", href: "#/training" }, "← Mon plan");
    const steps = el("ol", { class: "tr-steps", "aria-label": "Étapes du test", "data-new": "0.50.10-training-circle" },
      el("li", { class: cb ? "done" : "now" }, "Test complet"),
      el("li", { class: cb ? "now" : "" }, cb ? "Reprise " + cb.round : "Reprise des questions manquées (au besoin)"),
      el("li", null, "Completed"));
    main.append(el("div", { class: "page-head" }, el("p", { class: "tr-back" }, back),
      el("h1", null, "Test — " + (item.code ? item.code + " · " : "") + item.title),
      el("p", { class: "muted" }, cb
        ? "Reprise " + cb.round + " : " + cb.remaining + " question(s) manquée(s) à refaire, réponses mélangées. Note du test : " + cb.first + " %."
        : q.total + " questions · seuil de réussite " + q.pass + " %. Votre note s'affiche à la fin ; sous le seuil, les questions "
          + "manquées reviennent jusqu'à ce que chacune soit réussie."),
      steps));
    const blocks = q.questions.map((question, n) => questionBlock(question, n + 1, true));  // options always shuffled
    const result = el("div");
    const submit = el("button", { type: "submit", class: "btn btn-primary" }, cb ? "Remettre cette reprise" : "Remettre mes réponses");
    const form = el("form", { class: "ag-form tr-quiz", onsubmit: async (ev) => {
      ev.preventDefault();
      const answers = {};
      blocks.forEach((b) => b.inputs.forEach((input) => {
        if (input.checked) (answers[b.question.index] = answers[b.question.index] || []).push(Number(input.value));
      }));
      const missing = blocks.map((b, n) => (answers[b.question.index] ? null : n + 1)).filter(Boolean);
      if (missing.length) {
        toast(missing.length + " question(s) sans réponse : " + missing.slice(0, 8).join(", ") + ".", "error");
        return;
      }
      submit.disabled = true;
      let r;
      try { r = await api.post("/api/training/items/" + iid + "/quiz", { answers }); }
      catch (err) { submit.disabled = false; toast(err.message, "error"); return; }
      showReview(blocks, r.review);
      clear(result);
      result.append(scoreCard(r, item), el("div", { class: "form-actions tt-left tr-next" },
        r.passed ? el("a", { class: "btn btn-primary", href: "#/training" }, "Retour à mon plan")
          : el("button", { type: "button", class: "btn btn-primary", "data-new": "0.50.10-training-retry",
            onclick: () => TR.go("#/training/test/" + iid) }, "Reprendre les " + r.remaining.length + " question(s) manquée(s)"),
        r.passed ? null : el("a", { class: "btn", href: "#/training" }, "Plus tard")));
      submit.remove();
      window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });  // mark first
      if (r.passed) {
        steps.querySelectorAll("li").forEach((li) => { li.className = "done"; });
        toast("« " + item.title + " » : Completed.", "success");
      }
    } }, result, blocks.map((b) => b.fs), el("div", { class: "form-actions tt-left" }, submit));
    main.append(form);
  };

  /* Re-render the same address (a new round of the same item). */
  TR.go = function (hash) {
    if (location.hash === hash) window.dispatchEvent(new HashChangeEvent("hashchange")); else location.hash = hash;
  };
})();
