/* Existing notice actions -> authenticated explicit consent. No capture. */
(function () {
  "use strict";
  var element = document.getElementById("graf-product-analytics-provider-config");
  if (!element) return;
  var config;
  try { config = JSON.parse(element.textContent).explicit_funnel; } catch (_) { return; }
  if (!config) return;
  var busy = false, queuedChoice = null, currentChoice = null;
  function signal(stage) {
    window.dispatchEvent(new CustomEvent("graf:explicit-analytics-consent", { detail: stage }));
  }
  function status(message, error) {
    var output = document.getElementById("graf-explicit-consent-status");
    if (!output) {
      output = document.createElement("p");
      output.id = "graf-explicit-consent-status";
      output.className = "settings-status";
      document.body.appendChild(output);
    }
    output.setAttribute("role", error ? "alert" : "status");
    output.textContent = message;
  }
  async function save() {
    if (busy) return;
    busy = true;
    while (queuedChoice !== null) {
      var accepted = queuedChoice;
      queuedChoice = null;
      currentChoice = accepted;
      try {
        var response = await fetch("/api/v1/product-analytics/explicit-context", { credentials: "same-origin", cache: "no-store" });
        if (!response.ok) throw new Error("context unavailable");
        var context = await response.json();
        if (context.stable_pseudonymous_user_id !== config.user_pseudonym ||
            (accepted && context.copy_version !== config.copy_version)) throw new Error("account or version changed");
        var headers = { "Content-Type": "application/json" };
        var token = context.csrf_token || document.querySelector('meta[name="csrf-token"]')?.content;
        if (token) headers["X-CSRF-Token"] = token;
        response = await fetch("/api/v1/product-analytics/explicit-consent", {
          method: "PUT", credentials: "same-origin", headers: headers,
          body: JSON.stringify({ accepted: accepted, copy_version: config.copy_version, expected_pseudonymous_user_id: config.user_pseudonym })
        });
        if (!response.ok) throw new Error("save unavailable");
        context = await response.json();
        if (context.stable_pseudonymous_user_id !== config.user_pseudonym ||
            (accepted ? context.telemetry_gate_state !== "accepted" : context.telemetry_gate_state !== "withdrawn")) throw new Error("save unconfirmed");
        if (queuedChoice === null) {
          status(accepted ? "Выбор аналитики сохранён." : "Согласие на аналитику отозвано.", false);
          signal("changed"); // Server readback is still required by native.
        }
      } catch (_) {
        if (queuedChoice === null) status(accepted ? "Сохранение согласия не подтверждено. Повторите выбор в настройках cookies." : "Отзыв согласия не подтвержден. Повторите выбор в настройках cookies.", true);
        // A lost reply may follow a commit. Never claim server state or reopen native.
      }
    }
    currentChoice = null;
    busy = false;
  }
  document.addEventListener("click", function (event) {
    var button = event.target.closest?.('#cc-main button[data-role="all"], #cc-main button[data-role="necessary"], #cc-main button[data-role="save"]');
    if (!event.isTrusted || !button || !window.CookieConsent) return;
    status("Сохранение выбора…", false);
    signal("pending"); // Synchronous invalidation before any network request.
    // Vendor button handlers run before bubbling reaches document. Snapshot the
    // choice now; a later revoke during a pending accept must not be dropped.
    var choice = window.CookieConsent.acceptedCategory("analytics");
    if (!busy || queuedChoice !== null || choice !== currentChoice) queuedChoice = choice;
    save();
  });
  // Hydration, onConsent and another account's storage never write server consent.
})();
