/* Verification of the requirements by the test results (0.60.91, D-O-097).
   #/testing/<KEY>/verification -> one line per requirement that cites tests: verified, with derogation, partially,
   failed or not run, with the verdict of each cited test (from the bundles of the test plans).
   Also T.executions(data): the results of one test, for its record page. */
(function () {
  "use strict";
  const { api, el } = DA;
  const T = (DA.testing = DA.testing || {});
  const CLASS = { verified: "ok", passed: "ok", derogation: "warn", partial: "warn", failed: "danger", not_run: "neutral", abandoned: "neutral" };
  const badge = (code, label) => el("span", { class: "badge badge-" + (CLASS[code] || "neutral") }, label);

  T.executions = function (data) {
    return el("section", { "data-new": "0.60.91-test-executions" }, el("h2", null, "Exécutions (" + data.executions.length + ")"),
      el("p", null, "Verdict : ", badge(data.verdict, data.verdict_label)),
      data.executions.length ? DA.table(["Plan", "Proto", "Résultat", "Justification", "Date"], data.executions.map((r) => el("tr", null,
        el("td", null, el("a", { class: "ag-key", href: T.href("plans/" + r.plan) }, r.plan)), el("td", null, r.proto + (r.serial ? " · " + r.serial : "")),
        el("td", null, badge(r.result, r.result_label)), el("td", null, r.note || "—"), el("td", null, DA.formatDate(r.at)))))
        : el("p", { class: "muted" }, "Pas encore exécuté : les résultats se saisissent dans les bundles d'un plan de test envoyé."));
  };

  T.verifyView = async function (main) {
    const data = await api.get(T.api("/api/testing/verification"));
    const summary = Object.entries(data.labels).map(([k, v]) => el("span", { class: "tv-count" }, badge(k, v), " " + data.counts[k]));
    main.append(el("div", { class: "page-head", "data-new": "0.60.91-verification" }, el("h1", null, "Vérification des requirements · " + data.space),
      el("p", { class: "muted" }, "Une ligne par requirement qui cite des tests (« Test Procedure »). Le verdict d'un test vient du dernier résultat sur chaque "
        + "prototype, dans les plans de test ; « Passed with derogation » reste visible ; « Abandoned » ne vérifie rien.")),
      el("p", { class: "tv-summary" }, summary));
    if (!data.requirements.length) {
      main.append(el("div", { class: "empty" }, el("p", null, "Aucune requirement de ce Space ne cite encore de test.")));
      return;
    }
    main.append(DA.table(["Requirement", "External ID", "Title", "Verdict", "Tests"], data.requirements.map((r) => el("tr", null,
      el("td", { class: "nowrap" }, el("a", { class: "ag-key", href: T.reqHref(r.key) }, r.key)), el("td", { class: "nowrap" }, r.external_id || "—"),
      el("td", null, r.title), el("td", null, badge(r.verdict, r.verdict_label)),
      el("td", null, r.tests.map((t) => el("a", { class: "tv-test", href: T.href("test/" + t.test_id), title: data.test_labels[t.verdict] },
        badge(t.verdict, t.test_id), " ")))))));
  };
})();
