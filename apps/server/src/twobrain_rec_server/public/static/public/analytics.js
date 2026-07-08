/*!
 * GRAF public analytics controller scaffold.
 * Phase 1 provider loading is added only after consent logic is implemented.
 */
(function () {
  "use strict";

  var CONSENT_STORAGE_KEY = "graf_public_analytics_consent";
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
  var currentCategories = [];
  var currentConsentState = "unknown";
  var providerInitStarted = false;
  var optionalConsentCategories = ["analytics", "advertising_attribution", "behavior_replay"];
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

  function normalizedCategories(categories) {
    if (!Array.isArray(categories)) {
      return [];
    }
    return categories.filter(function (category, index) {
      return typeof category === "string" && categories.indexOf(category) === index;
    });
  }

  function configuredValues(labelClass) {
    return (config.stable_labels && config.stable_labels[labelClass]) || [];
  }

  function allowedLabel(labelClass, value) {
    return typeof value === "string" && configuredValues(labelClass).indexOf(value) !== -1;
  }

  function configuredConsentState(state) {
    return (config.consent_states || []).indexOf(state) !== -1;
  }

  function readStoredConsent() {
    try {
      return JSON.parse(localStorage.getItem(CONSENT_STORAGE_KEY) || "null");
    } catch (_) {
      return null;
    }
  }

  function writeStoredConsent(state, categories) {
    var payload = {
      advertising_attribution_allowed: hasCategory(categories, "advertising_attribution"),
      analytics_allowed: hasCategory(categories, "analytics"),
      behavior_replay_allowed: hasCategory(categories, "behavior_replay"),
      categories: categories.slice(),
      copy_version: config.consent_copy_version,
      decided_at: new Date().toISOString(),
      state: state,
      surface: config.page_path,
    };
    try {
      localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(payload));
    } catch (_) {
      return false;
    }
    return true;
  }

  function previouslyAllowedOptionalCategory(previous) {
    return Boolean(
      previous &&
        (previous.analytics_allowed ||
          previous.advertising_attribution_allowed ||
          previous.behavior_replay_allowed),
    );
  }

  function consentStateForCategories(categories) {
    var grantedOptional = optionalConsentCategories.filter(function (category) {
      return hasCategory(categories, category);
    });
    var state = "necessary_only";
    if (grantedOptional.length === optionalConsentCategories.length) {
      state = "accepted_all";
    } else if (grantedOptional.length > 0) {
      state = "customized";
    } else if (previouslyAllowedOptionalCategory(readStoredConsent())) {
      state = "revoked";
    }
    return configuredConsentState(state) ? state : "unknown";
  }

  function revisionFromCopyVersion(copyVersion) {
    var digits = String(copyVersion || "").replace(/\D/g, "").slice(0, 9);
    return digits ? Number(digits) : 0;
  }

  function safeEventFields(fields) {
    var source = fields || {};
    var safe = {};
    if (allowedLabel("section_id", source.section_id)) {
      safe.section_id = source.section_id;
    }
    if (allowedLabel("cta_location", source.cta_location)) {
      safe.cta_location = source.cta_location;
    }
    if (allowedLabel("target_kind", source.target_kind)) {
      safe.target_kind = source.target_kind;
    }
    return safe;
  }

  function buildEventPayload(eventName, fields) {
    if (!eventNames[eventName]) {
      return null;
    }

    return Object.assign(
      {
        consent_state: currentConsentState,
        event_name: eventName,
        page_path: config.page_path,
        surface: config.surface,
        campaign_attribution: config.campaign_attribution || {},
      },
      safeEventFields(fields),
    );
  }

  function ensureYandexProvider(categories) {
    var grantedCategories = normalizedCategories(categories);
    if (api.providerBlocked || !hasCategory(grantedCategories, "analytics") || !config.yandex_metrica_id) {
      return false;
    }
    currentCategories = grantedCategories;
    currentConsentState = consentStateForCategories(grantedCategories);
    api.currentCategories = currentCategories.slice();
    api.currentConsentState = currentConsentState;
    if (api.providerLoaded || providerInitStarted || document.querySelector('script[data-graf-provider="yandex-metrica"]')) {
      api.providerLoaded = true;
      api.providerInitStarted = true;
      return true;
    }

    providerInitStarted = true;
    api.providerInitStarted = true;
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
      api.providerLoaded = false;
      api.providerInitStarted = false;
      providerInitStarted = false;
    };
    document.head.appendChild(script);
    window.ym(config.yandex_metrica_id, "init", {
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true,
      webvisor: hasCategory(grantedCategories, "behavior_replay") && config.replay_allowed,
    });
    api.providerLoaded = true;
    return true;
  }

  function dispatchEvent(eventName, fields) {
    var payload = buildEventPayload(eventName, fields);
    if (!payload) {
      return false;
    }
    if (
      hasCategory(currentCategories, "analytics") &&
      api.providerLoaded &&
      !api.providerBlocked &&
      window.ym &&
      config.yandex_metrica_id
    ) {
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
        if (
          !allowedLabel("cta_location", element.dataset.analyticsCta) ||
          !allowedLabel("target_kind", targetKind)
        ) {
          return;
        }
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
          if (allowedLabel("section_id", sectionId)) {
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

  function handleConsent(cookie) {
    var categories = normalizedCategories((cookie && cookie.categories) || []);
    var state = consentStateForCategories(categories);
    currentCategories = categories;
    currentConsentState = state;
    api.currentCategories = categories.slice();
    api.currentConsentState = state;
    writeStoredConsent(state, categories);
    if (!hasCategory(categories, "analytics")) {
      return false;
    }
    return startGrantedTracking(categories);
  }

  function runCookieConsent() {
    if (!window.CookieConsent || typeof window.CookieConsent.run !== "function") {
      api.consentReady = false;
      return false;
    }
    window.CookieConsent.run({
      autoShow: true,
      cookie: {
        expiresAfterDays: 180,
        name: "graf_public_cookie_consent",
        path: "/",
        sameSite: "Lax",
        secure: window.location.protocol === "https:",
        useLocalStorage: true,
      },
      categories: {
        necessary: {
          enabled: true,
          readOnly: true,
        },
        analytics: {},
        advertising_attribution: {},
        behavior_replay: {},
      },
      language: {
        default: "ru",
        translations: {
          ru: {
            consentModal: {
              acceptAllBtn: "Разрешить все",
              acceptNecessaryBtn: "Только необходимые",
              description:
                "Мы используем аналитику Яндекс Метрики только после вашего согласия. " +
                "Без согласия сайт работает, но мы не увидим источники переходов, клики и прокрутку.",
              footer:
                '<a href="/privacy">Конфиденциальность</a>' +
                '<a href="/cookies">Cookies</a>' +
                '<a href="/analytics-consent">Согласие на аналитику</a>',
              showPreferencesBtn: "Настроить",
              title: "Аналитика и cookies",
            },
            preferencesModal: {
              acceptAllBtn: "Разрешить все",
              acceptNecessaryBtn: "Только необходимые",
              closeIconLabel: "Закрыть настройки",
              savePreferencesBtn: "Сохранить выбор",
              sections: [
                {
                  description:
                    "Эти cookies и localStorage нужны для сохранения вашего выбора. " +
                    "Они не включают аналитику и не передают данные провайдерам.",
                  linkedCategory: "necessary",
                  title: "Необходимые",
                },
                {
                  description:
                    "Помогает считать посещения, источники переходов, клики по кнопкам и " +
                    "достижение страницы скачивания. Не отправляем email, телефоны, " +
                    "тексты встреч, аудио, токены или приватные ссылки.",
                  linkedCategory: "analytics",
                  title: "Аналитика",
                },
                {
                  description:
                    "Помогает связать рекламные кампании с web-конверсией. В Phase 1 " +
                    "используются только безопасные UTM-метки и цели Яндекс Метрики.",
                  linkedCategory: "advertising_attribution",
                  title: "Рекламная атрибуция",
                },
                {
                  description:
                    "Разрешает поведенческую запись Яндекс Метрики только на публичных " +
                    "страницах / и /download. Не используется на логине, кабинете, " +
                    "записях встреч, админке и других продуктовых страницах.",
                  linkedCategory: "behavior_replay",
                  title: "Поведенческая запись",
                },
              ],
              title: "Настройки аналитики",
            },
          },
        },
      },
      mode: "opt-in",
      onChange: function (details) {
        handleConsent(details.cookie);
      },
      onConsent: function (details) {
        handleConsent(details.cookie);
      },
      onFirstConsent: function (details) {
        handleConsent(details.cookie);
      },
      revision: revisionFromCopyVersion(config.consent_copy_version),
    });
    api.consentReady = true;
    return true;
  }

  var api = {
    buildEventPayload: buildEventPayload,
    config: Object.freeze(config),
    consentReady: false,
    currentCategories: [],
    currentConsentState: currentConsentState,
    dispatchEvent: dispatchEvent,
    dispatchOnce: dispatchOnce,
    ensureYandexProvider: ensureYandexProvider,
    providerBlocked: false,
    providerInitStarted: false,
    providerLoaded: false,
    sentEvents: [],
    startGrantedTracking: startGrantedTracking,
    version: "093-us5",
  };

  window.GRAFPublicAnalytics = api;
  runCookieConsent();
})();
