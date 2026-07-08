/*!
 * GRAF public analytics controller scaffold.
 * Phase 1 provider loading is added only after consent logic is implemented.
 */
(function () {
  "use strict";

  var configElement = document.getElementById("graf-public-analytics-config");
  if (!configElement) {
    return;
  }

  var config;
  try {
    config = JSON.parse(configElement.textContent || "{}");
  } catch (_) {
    return;
  }

  if (!config.enabled) {
    return;
  }

  window.GRAFPublicAnalytics = {
    config: Object.freeze(config),
    providerLoaded: false,
    queuedEvents: [],
    version: "093-foundation",
  };
})();
