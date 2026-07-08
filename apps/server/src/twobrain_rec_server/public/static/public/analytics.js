/*!
 * GRAF public analytics controller scaffold.
 * Phase 1 provider loading is added only after consent logic is implemented.
 */
(function () {
  "use strict";

  var YANDEX_TAG_URL = "https://mc.yandex.ru/metrika/tag.js";
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

  var eventNames = {};
  (config.event_catalog || []).forEach(function (event) {
    if (event && event.event_name) {
      eventNames[event.event_name] = true;
    }
  });

  function hasCategory(categories, category) {
    if (categories === true || categories === "all") {
      return true;
    }
    if (Array.isArray(categories)) {
      return categories.indexOf(category) !== -1;
    }
    return Boolean(categories && categories[category] === true);
  }

  function buildEventPayload(eventName, fields) {
    if (!eventNames[eventName]) {
      return null;
    }

    return Object.assign(
      {
        event_name: eventName,
        page_path: config.page_path,
        surface: config.surface,
        campaign_attribution: config.campaign_attribution || {},
      },
      fields || {},
    );
  }

  function ensureYandexProvider(categories) {
    if (!hasCategory(categories, "analytics") || !config.yandex_metrica_id) {
      return false;
    }
    if (api.providerLoaded || document.querySelector('script[data-graf-provider="yandex-metrica"]')) {
      api.providerLoaded = true;
      return true;
    }

    window.ym =
      window.ym ||
      function () {
        (window.ym.a = window.ym.a || []).push(arguments);
      };
    window.ym.l = Number(new Date());

    var script = document.createElement("script");
    script.async = true;
    script.src = YANDEX_TAG_URL;
    script.dataset.grafProvider = "yandex-metrica";
    script.onload = function () {
      api.providerLoaded = true;
    };
    script.onerror = function () {
      api.providerBlocked = true;
    };
    document.head.appendChild(script);
    window.ym(config.yandex_metrica_id, "init", {
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true,
      webvisor: hasCategory(categories, "behavior_replay") && config.replay_allowed,
    });
    api.providerLoaded = true;
    return true;
  }

  function dispatchEvent(eventName, fields) {
    var payload = buildEventPayload(eventName, fields);
    if (!payload) {
      return false;
    }
    api.queuedEvents.push(payload);
    if (api.providerLoaded && window.ym && config.yandex_metrica_id) {
      window.ym(config.yandex_metrica_id, "reachGoal", eventName, payload);
    }
    return true;
  }

  var api = {
    buildEventPayload: buildEventPayload,
    config: Object.freeze(config),
    dispatchEvent: dispatchEvent,
    ensureYandexProvider: ensureYandexProvider,
    providerBlocked: false,
    providerLoaded: false,
    queuedEvents: [],
    version: "093-us1",
  };

  window.GRAFPublicAnalytics = api;
})();
