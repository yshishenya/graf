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
  var sentKeys = {};
  var listenersBound = false;
  var sectionsObserved = false;
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
    if (api.providerLoaded && window.ym && config.yandex_metrica_id) {
      window.ym(config.yandex_metrica_id, "reachGoal", eventName, payload);
      api.sentEvents.push(payload);
      return true;
    }
    return false;
  }

  function dedupeKey(eventName, fields) {
    var stable = fields || {};
    return [
      eventName,
      stable.section_id || "",
      stable.cta_location || "",
      stable.target_kind || "",
      config.page_path || "",
    ].join("|");
  }

  function dispatchOnce(eventName, fields) {
    var key = dedupeKey(eventName, fields);
    if (sentKeys[key]) {
      return false;
    }
    if (dispatchEvent(eventName, fields)) {
      sentKeys[key] = true;
      return true;
    }
    return false;
  }

  function pageViewEventName() {
    return config.surface === "public_download" ? "public_download_viewed" : "public_landing_viewed";
  }

  function eventNameForCta(targetKind) {
    if (targetKind === "installer_package") {
      return "public_installer_download_clicked";
    }
    if (targetKind === "login") {
      return "public_login_intent_clicked";
    }
    return "public_landing_cta_clicked";
  }

  function bindClickTracking() {
    if (listenersBound) {
      return;
    }
    listenersBound = true;
    document.querySelectorAll("[data-analytics-cta]").forEach(function (element) {
      element.addEventListener("click", function () {
        var targetKind = element.dataset.analyticsTarget || "download_page";
        dispatchOnce(eventNameForCta(targetKind), {
          cta_location: element.dataset.analyticsCta,
          target_kind: targetKind,
        });
      });
    });
  }

  function observeSections() {
    if (sectionsObserved || typeof IntersectionObserver === "undefined") {
      return;
    }
    sectionsObserved = true;
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }
          var sectionId = entry.target.dataset.analyticsSection;
          if (sectionId) {
            dispatchOnce("public_landing_section_seen", {
              section_id: sectionId,
              target_kind: "section",
            });
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.52 },
    );

    document.querySelectorAll("[data-analytics-section]").forEach(function (element) {
      observer.observe(element);
    });
  }

  function startGrantedTracking(categories) {
    if (!ensureYandexProvider(categories)) {
      return false;
    }
    dispatchOnce(pageViewEventName(), {});
    bindClickTracking();
    observeSections();
    return true;
  }

  var api = {
    buildEventPayload: buildEventPayload,
    config: Object.freeze(config),
    dispatchEvent: dispatchEvent,
    dispatchOnce: dispatchOnce,
    ensureYandexProvider: ensureYandexProvider,
    providerBlocked: false,
    providerLoaded: false,
    sentEvents: [],
    startGrantedTracking: startGrantedTracking,
    version: "093-us2",
  };

  window.GRAFPublicAnalytics = api;
})();
