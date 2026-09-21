/*!
 * GRAF public and product analytics controller.
 *
 * Providers are intentionally initialized only from a CookieConsent callback.
 * The browser gate is a safety boundary, not a replacement for the server
 * inventory or the provider-side privacy settings.
 */
(function () {
  "use strict";

  if (window.__GRAF_ANALYTICS_CONTROLLER_LOADED__) {
    return;
  }
  window.__GRAF_ANALYTICS_CONTROLLER_LOADED__ = true;

  var YANDEX_TAG_URL = "https://mc.yandex.ru/metrika/tag.js";
  // The external counter keeps the two surfaces the published cookies policy
  // names. A page outside this list — the pages with a credential form in
  // particular — is measured through the first-party relay only, so the visitor's
  // decision never loads a third-party script there.
  var EXTERNAL_COUNTER_SURFACES = ["public_landing", "public_download"];
  var productConfigElement = document.getElementById("graf-product-analytics-provider-config");
  var publicConfigElement = document.getElementById("graf-public-analytics-config");

  function parseConfig(element) {
    if (!element) {
      return null;
    }
    try {
      return JSON.parse(element.textContent || "{}");
    } catch (_) {
      return null;
    }
  }

  var productConfig = parseConfig(productConfigElement);
  var publicConfig = parseConfig(publicConfigElement);
  var config = publicConfig || productConfig;
  if (!config || (!publicConfig && !productConfig)) {
    return;
  }
  if (publicConfig && !publicConfig.enabled && !publicConfig.consent_ui_enabled && (!productConfig || !productConfig.enabled)) {
    return;
  }

  var eventNames = {};
  var sentKeys = {};
  var listenersBound = false;
  var sectionsObserved = false;
  var sectionObserver = null;
  var currentCategories = [];
  var currentConsentState = "unknown";
  var previousOptionalConsent = false;
  var consentBlocked = false;
  var publicProviderInitStarted = false;
  var publicProviderFailure = false;
  var productYandexInitStarted = false;
  var productYandexFailure = false;
  var productAutocaptureStarted = false;
  var productCaptureBlocked = false;
  var publicProviderCaptureBlocked = false;
  var publicProviderCaptureFailure = false;

  (publicConfig && publicConfig.event_catalog ? publicConfig.event_catalog : []).forEach(function (event) {
    if (event && event.event_name) {
      eventNames[event.event_name] = true;
    }
  });

  function consentCategories() {
    var browserConsent = config.browser_consent || {};
    return config.consent_categories || browserConsent.categories || [
      "necessary",
      "analytics",
      "advertising_attribution",
      "behavior_replay",
    ];
  }

  function consentCopyVersion() {
    var browserConsent = config.browser_consent || {};
    return config.consent_copy_version || browserConsent.copy_version || null;
  }

  function revisionFromCopyVersion(copyVersion) {
    var digits = String(copyVersion || "").replace(/\D/g, "");
    return digits ? Number(digits) : 0;
  }

  function consentRevision() {
    var derivedRevision = revisionFromCopyVersion(consentCopyVersion());
    if (derivedRevision) {
      return derivedRevision;
    }
    var browserConsent = config.browser_consent || {};
    var revision = config.consent_revision || browserConsent.revision;
    return typeof revision === "number" ? revision : revisionFromCopyVersion(consentCopyVersion());
  }

  function hasCategory(categories, category) {
    return Array.isArray(categories) && categories.indexOf(category) !== -1;
  }

  function normalizedCategories(categories) {
    if (!Array.isArray(categories)) {
      return null;
    }
    var known = consentCategories();
    var seen = {};
    for (var index = 0; index < categories.length; index += 1) {
      var category = categories[index];
      if (typeof category !== "string" || known.indexOf(category) === -1 || seen[category]) {
        return null;
      }
      seen[category] = true;
    }
    if (known.indexOf("necessary") === -1 || !seen.necessary) {
      return null;
    }
    return known.filter(function (category) {
      return seen[category];
    });
  }

  function consentVersionMatches(cookie) {
    if (!cookie || typeof cookie !== "object") {
      return false;
    }
    var data = cookie.data && typeof cookie.data === "object" ? cookie.data : {};
    var storedCopyVersion = cookie.copy_version || data.graf_consent_copy_version;
    if (storedCopyVersion && storedCopyVersion !== consentCopyVersion()) {
      return false;
    }
    if (
      data.graf_consent_revision !== undefined &&
      Number(data.graf_consent_revision) !== consentRevision()
    ) {
      return false;
    }
    return storedCopyVersion === consentCopyVersion() || Number(cookie.revision) === consentRevision();
  }

  function cookieHadOptionalConsent(cookie) {
    var data = cookie && cookie.data && typeof cookie.data === "object" ? cookie.data : {};
    return Boolean(
      (cookie && cookie.state && ["accepted_all", "customized"].indexOf(cookie.state) !== -1) ||
        ["accepted_all", "customized", "revoked"].indexOf(data.graf_consent_state) !== -1,
    );
  }

  function consentStateFor(cookie, categories, hadOptionalConsent) {
    if (!consentVersionMatches(cookie) || !categories) {
      return "unknown";
    }
    var data = cookie && cookie.data && typeof cookie.data === "object" ? cookie.data : {};
    var storedState = cookie && cookie.state ? cookie.state : data.graf_consent_state;
    var optional = consentCategories().filter(function (category) {
      return category !== "necessary";
    });
    var grantedOptional = optional.filter(function (category) {
      return hasCategory(categories, category);
    });
    var state = "necessary_only";
    if (grantedOptional.length === optional.length) {
      state = "accepted_all";
    } else if (grantedOptional.length > 0) {
      state = "customized";
    } else if (hadOptionalConsent || storedState === "revoked") {
      state = "revoked";
    }
    if (cookie && cookie.state && cookie.state !== state) {
      return "unknown";
    }
    return (config.consent_states || (config.browser_consent && config.browser_consent.states) || []).indexOf(state) === -1
      ? "unknown"
      : state;
  }

  function transitionAllowed(nextState) {
    if (currentConsentState === "unknown" || currentConsentState === nextState) {
      return true;
    }
    var transitions = config.consent_transitions || (config.browser_consent && config.browser_consent.transitions) || {};
    return Array.isArray(transitions[currentConsentState]) && transitions[currentConsentState].indexOf(nextState) !== -1;
  }

  function stableToken(value, maxLength) {
    if (typeof value !== "string") {
      return null;
    }
    var trimmed = value.trim().slice(0, maxLength || 80);
    if (!trimmed || !/^[a-zA-Z0-9_.:-]+$/.test(trimmed)) {
      return null;
    }
    return trimmed;
  }

  function configuredValues(labelClass) {
    return (publicConfig && publicConfig.stable_labels && publicConfig.stable_labels[labelClass]) || [];
  }

  function allowedLabel(labelClass, value) {
    return typeof value === "string" && configuredValues(labelClass).indexOf(value) !== -1;
  }

  function productAllowlistedValue(list, value) {
    return typeof value === "string" && Array.isArray(list) && list.indexOf(value) !== -1 ? value : null;
  }

  function safeCampaignAttribution() {
    return hasCategory(currentCategories, "advertising_attribution") && publicConfig
      ? publicConfig.campaign_attribution || {}
      : {};
  }

  function buildEventPayload(eventName, fields) {
    if (!publicConfig || !eventNames[eventName]) {
      return null;
    }

    var source = fields || {};
    var safe = {
      consent_state: currentConsentState,
      event_name: eventName,
      page_path: publicConfig.page_path,
      surface: publicConfig.surface,
      campaign_attribution: safeCampaignAttribution(),
      product_activation_bridge_supported: Boolean(
        hasCategory(currentCategories, "advertising_attribution") &&
          publicConfig.product_activation_bridge &&
          publicConfig.product_activation_bridge.bridge_supported,
      ),
    };
    ["section_id", "cta_location", "target_kind", "product_tab", "pricing_cycle", "faq_item"].forEach(function (labelClass) {
      if (allowedLabel(labelClass, source[labelClass])) {
        safe[labelClass] = source[labelClass];
      }
    });
    return safe;
  }

  function canUseAnalytics() {
    return Boolean(
      api.consentReady &&
        !consentBlocked &&
        currentConsentState !== "unknown" &&
        hasCategory(currentCategories, "analytics"),
    );
  }

  function isPublicPageAllowed(pageConfig) {
    // Measurement by consent covers every public surface; the field list of the
    // relay stays closed, so a measured auth page still carries no form value.
    return Boolean(
      pageConfig &&
        typeof pageConfig.surface === "string" &&
        pageConfig.surface.indexOf("public_") === 0,
    );
  }

  function isYandexPageAllowed(pageConfig) {
    // Two different counters pass through here: the product counter carries an
    // inventory state instead of a surface, and the public counter carries a
    // surface. Each keeps its own gate, and the public one also honours the
    // scope the server published, so narrowing the scope on the server is enough
    // and the browser fails closed on either signal.
    return Boolean(
      pageConfig &&
        (!pageConfig.surface ||
          EXTERNAL_COUNTER_SURFACES.indexOf(pageConfig.surface) !== -1) &&
        pageConfig.external_counter_allowed !== false &&
        (!pageConfig.yandex_state || pageConfig.yandex_state === "approved_page_view_event"),
    );
  }

  function ensureYandexTag(onFailure) {
    if (document.querySelector('script[data-graf-provider="yandex-metrica"]')) {
      return true;
    }
    if (config.validation_mode === "render_only") {
      return true;
    }
    var script = document.createElement("script");
    script.async = true;
    script.src = YANDEX_TAG_URL;
    script.dataset.grafProvider = "yandex-metrica";
    script.onload = function () {};
    script.onerror = function () {
      onFailure();
    };
    document.head.appendChild(script);
    return true;
  }

  function prepareYandexQueue() {
    window.ym =
      window.ym ||
      function () {
        (window.ym.a = window.ym.a || []).push(arguments);
      };
    window.ym.l = Number(new Date());
  }

  function ensurePublicYandexProvider() {
    if (
      !publicConfig ||
      !publicConfig.enabled ||
      !isPublicPageAllowed(publicConfig) ||
      !isYandexPageAllowed(publicConfig)
    ) {
      // A surface outside the counter scope is still measured, but only through
      // the first-party relay: the external script stays off it.
      api.providerBlocked = true;
      return false;
    }
    if (
      !canUseAnalytics() ||
      publicProviderFailure ||
      api.providerBlocked ||
      !publicConfig.yandex_metrica_id
    ) {
      return false;
    }
    api.currentCategories = currentCategories.slice();
    api.currentConsentState = currentConsentState;
    if (api.providerLoaded || publicProviderInitStarted) {
      return true;
    }

    publicProviderInitStarted = true;
    api.providerInitStarted = true;
    prepareYandexQueue();
    ensureYandexTag(function () {
      publicProviderFailure = true;
      api.providerBlocked = true;
      api.providerLoaded = false;
      api.providerInitStarted = false;
      publicProviderInitStarted = false;
    });
    var replayAllowed = Boolean(
      hasCategory(currentCategories, "behavior_replay") &&
        publicConfig.replay_allowed &&
        publicConfig.webvisor_allowed &&
        publicConfig.click_map_allowed &&
        publicConfig.scroll_map_allowed &&
        ["public_landing", "public_download"].indexOf(publicConfig.surface) !== -1,
    );
    window.ym(publicConfig.yandex_metrica_id, "init", {
      clickmap: replayAllowed,
      trackLinks: false,
      accurateTrackBounce: true,
      defer: true,
      trackHash: false,
      webvisor: replayAllowed,
      form_analytics: false,
    });
    window.ym(publicConfig.yandex_metrica_id, "hit", publicConfig.page_path, {
      params: {
        campaign_attribution: safeCampaignAttribution(),
        surface: publicConfig.surface,
      },
      sendTitle: false,
    });
    api.providerLoaded = true;
    return true;
  }

  function disableYandexCounter(counterId) {
    if (!counterId) {
      return false;
    }
    window["disableYaCounter" + counterId] = true;
    return true;
  }

  function publicCaptureEndpoint() {
    if (!publicConfig || typeof publicConfig.posthog_capture_endpoint !== "string") {
      return null;
    }
    var endpoint = publicConfig.posthog_capture_endpoint;
    if (endpoint.indexOf("/") !== 0 || endpoint.indexOf("//") !== -1 || endpoint.indexOf("@") !== -1) {
      return null;
    }
    return endpoint;
  }

  function publicViewId() {
    var storageKey = "graf_public_analytics_view_id";
    var pattern = /^[a-zA-Z0-9][a-zA-Z0-9_.:-]{7,119}$/;
    try {
      var existing = window.sessionStorage ? window.sessionStorage.getItem(storageKey) : null;
      if (typeof existing === "string" && pattern.test(existing)) {
        return existing;
      }
      if (!window.crypto || typeof window.crypto.getRandomValues !== "function") {
        return null;
      }
      var alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";
      var bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      var suffix = "";
      for (var index = 0; index < bytes.length; index += 1) {
        suffix += alphabet[bytes[index] % alphabet.length];
      }
      var viewId = "graf_public_view_" + suffix;
      if (window.sessionStorage) {
        window.sessionStorage.setItem(storageKey, viewId);
      }
      return viewId;
    } catch (_) {
      return null;
    }
  }

  function publicRelayPayload(eventName, payload) {
    if (!publicConfig || !publicConfig.page_path) {
      return null;
    }
    var viewId = publicViewId();
    if (!viewId) {
      return null;
    }
    var body = {
      event_name: eventName,
      page_path: publicConfig.page_path,
      surface: publicConfig.surface,
      view_id: viewId,
      consent_state: currentConsentState,
      consent_categories: currentCategories.slice(),
    };
    if (
      payload &&
      payload.campaign_attribution &&
      hasCategory(currentCategories, "advertising_attribution")
    ) {
      body.campaign_attribution = payload.campaign_attribution;
    }
    [
      "section_id",
      "cta_location",
      "target_kind",
      "product_tab",
      "pricing_cycle",
      "faq_item",
    ].forEach(function (field) {
      if (payload && payload[field]) {
        body[field] = payload[field];
      }
    });
    return body;
  }

  // Consented public page events go to the ordinary first-party relay and never
  // to an external script: no provider library is loaded, no project key reaches
  // the page, and a failed call stays invisible to the visitor.
  function sendPublicProviderEvent(eventName, payload) {
    if (!publicConfig || !eventName || !canUseAnalytics() || publicProviderCaptureBlocked) {
      return false;
    }
    var endpoint = publicCaptureEndpoint();
    var body = publicRelayPayload(eventName, payload);
    if (!endpoint || !body) {
      return false;
    }
    var serialized = JSON.stringify(body);
    var sent = false;
    try {
      if (navigator.sendBeacon) {
        sent = navigator.sendBeacon(endpoint, new Blob([serialized], { type: "application/json" }));
      }
      if (!sent && window.fetch) {
        window.fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: serialized,
          credentials: "omit",
          keepalive: true,
        }).catch(function () {});
        sent = true;
      }
    } catch (_) {
      publicProviderCaptureFailure = true;
      return false;
    }
    if (!sent) {
      publicProviderCaptureFailure = true;
    }
    return sent;
  }

  function enableYandexCounter(counterId) {
    if (!counterId) {
      return false;
    }
    try {
      delete window["disableYaCounter" + counterId];
    } catch (_) {}
    return true;
  }

  function disableOptionalProviders() {
    consentBlocked = true;
    publicProviderCaptureBlocked = true;
    if (publicConfig) {
      disableYandexCounter(publicConfig.yandex_metrica_id);
      api.providerBlocked = true;
    }
    if (productConfig && productConfig.yandex) {
      disableYandexCounter(productConfig.yandex.counter_id);
    }
    productCaptureBlocked = true;
    if (window.GRAFProductAnalytics) {
      window.GRAFProductAnalytics.captureBlocked = true;
    }
  }

  function enableOptionalProviders() {
    consentBlocked = false;
    publicProviderCaptureBlocked = false;
    productCaptureBlocked = false;
    if (publicConfig && !publicProviderFailure) {
      api.providerBlocked = false;
      enableYandexCounter(publicConfig.yandex_metrica_id);
    }
    if (productConfig && !productYandexFailure && productConfig.yandex) {
      enableYandexCounter(productConfig.yandex.counter_id);
    }
    if (window.GRAFProductAnalytics) {
      window.GRAFProductAnalytics.captureBlocked = false;
    }
  }

  function consentStorageWritable() {
    var storageKey = config.consent_storage_key || "graf_public_cookie_consent";
    try {
      if (!window.localStorage) {
        return false;
      }
      var probeKey = storageKey + ".__graf_probe__";
      window.localStorage.setItem(probeKey, "1");
      var writable = window.localStorage.getItem(probeKey) === "1";
      window.localStorage.removeItem(probeKey);
      return writable;
    } catch (_) {
      return false;
    }
  }

  function persistedConsentMetadataMatches(state) {
    var storageKey = config.consent_storage_key || "graf_public_cookie_consent";
    try {
      var raw = window.localStorage.getItem(storageKey);
      var cookie = raw ? JSON.parse(raw) : null;
      var data = cookie && cookie.data && typeof cookie.data === "object" ? cookie.data : {};
      return Boolean(
        data.graf_consent_copy_version === consentCopyVersion() &&
          Number(data.graf_consent_revision) === consentRevision() &&
          data.graf_consent_state === state,
      );
    } catch (_) {
      return false;
    }
  }

  function persistConsentMetadata(state) {
    if (
      !window.CookieConsent ||
      typeof window.CookieConsent.setCookieData !== "function" ||
      !consentStorageWritable()
    ) {
      return false;
    }
    try {
      window.CookieConsent.setCookieData({
        mode: "update",
        value: {
          graf_consent_copy_version: consentCopyVersion(),
          graf_consent_revision: consentRevision(),
          graf_consent_state: state,
        },
      });
      return persistedConsentMetadataMatches(state);
    } catch (_) {
      return false;
    }
  }

  function consentCookieFromDetails(details) {
    if (details && details.cookie) {
      return details.cookie;
    }
    if (window.CookieConsent && typeof window.CookieConsent.getCookie === "function") {
      try {
        var storedCookie = window.CookieConsent.getCookie();
        if (storedCookie && typeof storedCookie === "object") {
          return storedCookie;
        }
      } catch (_) {}
    }
    if (window.CookieConsent && typeof window.CookieConsent.getUserPreferences === "function") {
      try {
        var preferences = window.CookieConsent.getUserPreferences();
        return {
          categories: preferences.acceptedCategories || [],
          revision: consentRevision(),
        };
      } catch (_) {}
    }
    return null;
  }

  function handleConsent(details) {
    var cookie = consentCookieFromDetails(details);
    var categories = normalizedCategories(cookie && cookie.categories);
    var hadOptionalConsent = previousOptionalConsent || cookieHadOptionalConsent(cookie);
    var nextState = consentStateFor(cookie, categories, hadOptionalConsent);
    if (nextState === "unknown" || !transitionAllowed(nextState)) {
      currentCategories = [];
      currentConsentState = "unknown";
      api.currentCategories = [];
      api.currentConsentState = "unknown";
      disableOptionalProviders();
      return false;
    }

    var replayConsentChanged =
      hasCategory(currentCategories, "behavior_replay") !== hasCategory(categories, "behavior_replay");
    previousOptionalConsent = previousOptionalConsent || hasCategory(currentCategories, "analytics") || hasCategory(currentCategories, "advertising_attribution") || hasCategory(currentCategories, "behavior_replay");
    currentCategories = categories;
    currentConsentState = nextState;
    api.currentCategories = categories.slice();
    api.currentConsentState = nextState;
    if (!persistConsentMetadata(nextState)) {
      currentCategories = [];
      currentConsentState = "unknown";
      api.currentCategories = [];
      api.currentConsentState = "unknown";
      disableOptionalProviders();
      return false;
    }
    if (api.providerLoaded && replayConsentChanged) {
      disableOptionalProviders();
      window.location.reload();
      return true;
    }
    if (!hasCategory(categories, "analytics")) {
      if (previousOptionalConsent || api.providerLoaded || productAutocaptureStarted) {
        disableOptionalProviders();
      }
      return false;
    }
    enableOptionalProviders();
    startGrantedProviders();
    return true;
  }

  function ensureProductAnalyticsApi() {
    window.GRAFProductAnalytics = window.GRAFProductAnalytics || {
      events: [],
      provider: "posthog",
      replayEnabled: false,
      sentEvents: [],
      captureBlocked: false,
    };
    return window.GRAFProductAnalytics;
  }

  function bindProductYandexUserID(counterId, providerConfig) {
    var yandexUserId = stableToken(
      providerConfig && providerConfig.yandex && providerConfig.yandex.user_id,
      96,
    );
    if (!counterId || !yandexUserId || !window.ym) {
      return false;
    }
    window.ym(counterId, "setUserID", yandexUserId);
    window.ym(counterId, "userParams", { UserID: yandexUserId });
    return true;
  }

  function initializeProductYandexProvider(providerConfig) {
    if (
      !providerConfig ||
      !providerConfig.yandex ||
      !providerConfig.yandex.enabled ||
      !providerConfig.yandex.counter_id ||
      !canUseAnalytics() ||
      productYandexFailure ||
      productYandexInitStarted ||
      !isYandexPageAllowed(providerConfig.yandex)
    ) {
      return false;
    }
    var counterId = stableToken(providerConfig.yandex.counter_id, 32);
    if (!counterId) {
      return false;
    }
    var analytics = ensureProductAnalyticsApi();
    productYandexInitStarted = true;
    prepareYandexQueue();
    ensureYandexTag(function () {
      productYandexFailure = true;
      productYandexInitStarted = false;
    });
    window.ym(counterId, "init", {
      clickmap: false,
      trackLinks: false,
      accurateTrackBounce: true,
      defer: true,
      trackHash: false,
      webvisor: false,
      form_analytics: false,
    });
    bindProductYandexUserID(counterId, providerConfig);
    var pageClass = stableToken(providerConfig.page_class, 80);
    if (pageClass) {
      window.ym(counterId, "hit", "/__graf/" + pageClass, {
        params: { page_class: pageClass },
        sendTitle: false,
      });
    }
    analytics.yandexEnabled = true;
    analytics.events.push({
      event: "yandex_product_pageview_ready",
      page_class: providerConfig.page_class,
      replay_enabled: false,
      yandex_state: providerConfig.yandex.state,
    });
    return true;
  }

  function initializePostHogAutocapture(providerConfig) {
    if (
      !providerConfig ||
      !providerConfig.posthog ||
      !providerConfig.posthog.enabled ||
      !providerConfig.posthog.autocapture_enabled ||
      !providerConfig.posthog.capture_endpoint ||
      !canUseAnalytics() ||
      productAutocaptureStarted
    ) {
      return false;
    }
    if (typeof providerConfig.posthog.capture_endpoint !== "string" || providerConfig.posthog.capture_endpoint.indexOf("/") !== 0 || providerConfig.posthog.capture_endpoint.indexOf("//") !== -1) {
      return false;
    }
    var analytics = ensureProductAnalyticsApi();
    // An anonymous browser carries no analytics identity. A shared placeholder
    // would report unrelated visitors as one person, so the controller sends
    // nothing at all until an authenticated pseudonym arrives (T033, FR-007).
    var distinctId = stableToken(providerConfig.posthog.distinct_id, 120);
    if (!distinctId) {
      analytics.autocaptureBlockedReason = "identity_unavailable";
      return false;
    }
    productAutocaptureStarted = true;
    analytics.autocaptureEnabled = true;
    analytics.pageClass = providerConfig.page_class;
    analytics.credentialSuppression = providerConfig.posthog.credential_suppression || [];
    analytics.consentState = currentConsentState;

    var actionAllowlist = providerConfig.analytics_action_allowlist || [];
    var targetAllowlist = providerConfig.analytics_target_allowlist || [];
    var allowedTags = ["a", "button", "details", "input", "label", "select", "summary", "textarea"];
    var allowedRoles = ["button", "checkbox", "link", "menuitem", "tab", "switch"];

    function sendAutocapture(eventType, fields) {
      if (!canUseAnalytics() || productCaptureBlocked) {
        return false;
      }
      var tagName = stableToken(fields && fields.tag_name, 24);
      var role = stableToken(fields && fields.role, 80);
      var payload = {
        distinct_id: distinctId,
        event_type: eventType,
        device_class: stableToken(providerConfig.posthog.device_class, 80),
        identity_state: stableToken(providerConfig.posthog.identity_state, 80),
        page_class: stableToken(providerConfig.page_class, 80) || "unknown",
        path_class: providerConfig.page_class,
        sensitivity: stableToken(providerConfig.sensitivity, 40) || "unknown",
        source: "browser_autocapture",
        workspace_pseudonym: stableToken(providerConfig.posthog.workspace_pseudonym, 120),
        consent_state: currentConsentState,
      };
      if (tagName && allowedTags.indexOf(tagName) !== -1) {
        payload.tag_name = tagName;
      }
      if (role && allowedRoles.indexOf(role) !== -1) {
        payload.role = role;
      }
      var action = productAllowlistedValue(actionAllowlist, fields && fields.analytics_action);
      var target = productAllowlistedValue(targetAllowlist, fields && fields.analytics_target);
      if (action) {
        payload.analytics_action = action;
      }
      if (target) {
        payload.analytics_target = target;
      }
      var serialized = JSON.stringify(payload);
      var sent = false;
      if (navigator.sendBeacon) {
        sent = navigator.sendBeacon(providerConfig.posthog.capture_endpoint, new Blob([serialized], { type: "application/json" }));
      }
      if (!sent && window.fetch) {
        window.fetch(providerConfig.posthog.capture_endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: serialized,
          credentials: "omit",
          keepalive: true,
        }).catch(function () {});
        sent = true;
      }
      analytics.sentEvents.push({
        event_type: eventType,
        page_class: payload.page_class,
        sent: sent,
      });
      return sent;
    }

    sendAutocapture("ready", { path_class: providerConfig.page_class });
    sendAutocapture("pageview", { path_class: providerConfig.page_class });
    document.addEventListener(
      "click",
      function (event) {
        var element = event.target && event.target.closest ? event.target.closest("[data-analytics-cta], [data-analytics-action], button, a") : null;
        if (!element) {
          return;
        }
        sendAutocapture("click", {
          tag_name: element.tagName ? element.tagName.toLowerCase() : null,
          role: element.getAttribute("role"),
          analytics_action: element.dataset && (element.dataset.analyticsAction || element.dataset.analyticsCta),
          analytics_target: element.dataset && element.dataset.analyticsTarget,
        });
      },
      true,
    );
    analytics.events.push({
      event: "posthog_autocapture_ready",
      page_class: providerConfig.page_class,
      replay_enabled: false,
      yandex_state: providerConfig.yandex && providerConfig.yandex.state,
    });
    return true;
  }

  function dispatchEvent(eventName, fields) {
    var payload = buildEventPayload(eventName, fields);
    if (!payload || !canUseAnalytics()) {
      return false;
    }
    var sent = false;
    if (sendPublicProviderEvent(eventName, payload)) {
      sent = true;
    }
    if (
      api.providerLoaded &&
      !api.providerBlocked &&
      window.ym &&
      publicConfig &&
      publicConfig.yandex_metrica_id
    ) {
      window.ym(publicConfig.yandex_metrica_id, "reachGoal", eventName, payload);
      sent = true;
    }
    if (!sent) {
      return false;
    }
    api.sentEvents.push(payload);
    return true;
  }

  function dedupeKey(eventName, fields) {
    var stable = fields || {};
    return [
      eventName,
      stable.section_id || "",
      stable.cta_location || "",
      stable.target_kind || "",
      stable.product_tab || "",
      stable.pricing_cycle || "",
      stable.faq_item || "",
      publicConfig && publicConfig.page_path ? publicConfig.page_path : "",
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
    if (!publicConfig) {
      return "public_landing_viewed";
    }
    if (publicConfig.surface === "public_download") {
      return "public_download_viewed";
    }
    if (publicConfig.surface === "public_signup") {
      return "public_signup_viewed";
    }
    if (publicConfig.surface === "public_login") {
      return "public_login_viewed";
    }
    return "public_landing_viewed";
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
    if (listenersBound || !publicConfig) {
      return;
    }
    listenersBound = true;
    document.querySelectorAll("[data-analytics-cta]").forEach(function (element) {
      element.addEventListener("click", function () {
        var targetKind = element.dataset.analyticsTarget || "download_page";
        if (!allowedLabel("cta_location", element.dataset.analyticsCta) || !allowedLabel("target_kind", targetKind)) {
          return;
        }
        dispatchOnce(eventNameForCta(targetKind), {
          cta_location: element.dataset.analyticsCta,
          target_kind: targetKind,
        });
      });
    });
    document.addEventListener("graf:product-tab-selected", function (event) {
      var detail = event && event.detail ? event.detail : {};
      if (allowedLabel("product_tab", detail.productTab)) {
        dispatchOnce("public_product_tab_selected", { product_tab: detail.productTab });
      }
    });
    document.addEventListener("graf:pricing-cycle-selected", function (event) {
      var detail = event && event.detail ? event.detail : {};
      if (allowedLabel("pricing_cycle", detail.pricingCycle)) {
        dispatchOnce("public_pricing_cycle_selected", { pricing_cycle: detail.pricingCycle });
      }
    });
    document.querySelectorAll("details[data-faq-id]").forEach(function (element) {
      element.addEventListener("toggle", function () {
        if (element.open && allowedLabel("faq_item", element.dataset.faqId)) {
          dispatchOnce("public_faq_opened", { faq_item: element.dataset.faqId });
        }
      });
    });
  }

  function observeSections() {
    if (!publicConfig || typeof IntersectionObserver === "undefined") {
      return;
    }
    if (!sectionObserver) {
      sectionObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) {
              return;
            }
            var sectionId = entry.target.dataset.analyticsSection;
            if (allowedLabel("section_id", sectionId)) {
              var key = dedupeKey("public_landing_section_seen", { section_id: sectionId });
              if (dispatchOnce("public_landing_section_seen", { section_id: sectionId }) || sentKeys[key]) {
                sectionObserver.unobserve(entry.target);
              }
            }
          });
        },
        { threshold: 0.12 },
      );
    }
    document.querySelectorAll("[data-analytics-section]").forEach(function (element) {
      sectionObserver.observe(element);
    });
    sectionsObserved = true;
  }

  function startPublicTracking() {
    if (!publicConfig || !isPublicPageAllowed(publicConfig) || !canUseAnalytics()) {
      return false;
    }
    // The page view is reported through the first-party relay, and the external
    // counter is started only on the surfaces the published scope names. A
    // blocked or unavailable counter therefore costs a measurement gap, not the
    // consented measurement of the page.
    ensurePublicYandexProvider();
    var sent = dispatchOnce(pageViewEventName(), {});
    bindClickTracking();
    observeSections();
    return sent || api.providerLoaded;
  }

  function startGrantedProviders() {
    var started = false;
    if (startPublicTracking()) {
      started = true;
    }
    if (initializePostHogAutocapture(productConfig)) {
      started = true;
    }
    if (initializeProductYandexProvider(productConfig)) {
      started = true;
    }
    return started;
  }

  function runCookieConsent() {
    if (!window.CookieConsent || typeof window.CookieConsent.run !== "function") {
      api.consentReady = false;
      return false;
    }
    api.consentReady = true;
    // FR-004: refusal is not harder than consent. Both decisions are the same
    // kind of button of the same modal, the refusal button is declared here next
    // to the acceptance button so the pair cannot drift, and both decisions
    // arrive through the same onConsent handler below.
    var acceptAllBtn = "Разрешить все";
    var acceptNecessaryBtn = "Только необходимые";
    var options = {
      autoShow: true,
      cookie: {
        expiresAfterDays: 180,
        name: config.consent_storage_key || "graf_public_cookie_consent",
        path: "/",
        sameSite: "Lax",
        secure: window.location.protocol === "https:",
        useLocalStorage: true,
      },
      categories: {
        necessary: { enabled: true, readOnly: true },
        analytics: {},
        advertising_attribution: {},
        behavior_replay: {},
      },
      language: {
        default: "ru",
        translations: {
          ru: {
            consentModal: {
              acceptAllBtn: acceptAllBtn,
              acceptNecessaryBtn: acceptNecessaryBtn,
              // FR-005: the visitor reads what is measured with consent, what
              // is measured anonymously without it, and how to refuse. The
              // claims are exact sentences because the copy comparison checks
              // them as statements, not as stems.
              description:
                "ГРАФ использует необходимые технологии для работы сайта. " +
                "Аналитика, рекламная атрибуция и поведенческая запись включаются " +
                "только после вашего выбора. " +
                "Обезличенный счет ведется без согласия. " +
                "Отказаться можно кнопкой «Только необходимые» или снять " +
                "отдельные разрешения в настройках cookies.",
              footer:
                '<a href="/privacy">Конфиденциальность</a>' +
                '<a href="/cookies">Cookies</a>' +
                '<a href="/analytics-consent">Об аналитике</a>',
              showPreferencesBtn: "Настроить",
              title: "Аналитика и cookies",
            },
            preferencesModal: {
              acceptAllBtn: acceptAllBtn,
              acceptNecessaryBtn: acceptNecessaryBtn,
              closeIconLabel: "Закрыть настройки",
              savePreferencesBtn: "Сохранить выбор",
              sections: [
                {
                  description:
                    "Нужны для работы сайта и сохранения вашего выбора. " +
                    "Не включают необязательный сбор.",
                  linkedCategory: "necessary",
                  title: "Необходимые",
                },
                {
                  description:
                    "Разрешает безопасные просмотры и цели публичных страниц, " +
                    "а также обезличенные продуктовые события во внутренних разделах " +
                    "после существующего gate. Не отправляем email, телефоны, " +
                    "тексты, записи, файлы, токены или платежные сведения.",
                  linkedCategory: "analytics",
                  title: "Аналитика",
                },
                {
                  description:
                    "Разрешает безопасные UTM-метки и категорию источника перехода. " +
                    "Полный URL, query, hash и произвольный текст не передаются.",
                  linkedCategory: "advertising_attribution",
                  title: "Рекламная атрибуция",
                },
                {
                  description:
                    "Разрешает техническое воспроизведение поведения — движения " +
                    "указателя, кликов, прокрутки и состояния интерфейса — только на " +
                    "публичных страницах / и /download. Внутренние страницы, встречи, " +
                    "формы, аудио и экран не записываются.",
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
      onChange: handleConsent,
      onConsent: handleConsent,
      onFirstConsent: handleConsent,
      revision: consentRevision(),
    };
    // The options stay readable so a test can render the real modal from the
    // real configuration instead of a hand-written copy of it (FR-004).
    api.consentOptions = options;
    try {
      window.CookieConsent.run(options);
    } catch (_) {
      api.consentReady = false;
      return false;
    }
    return true;
  }

  var api = {
    buildEventPayload: buildEventPayload,
    config: Object.freeze(publicConfig || {}),
    consentOptions: null,
    consentReady: false,
    currentCategories: [],
    currentConsentState: currentConsentState,
    dispatchEvent: dispatchEvent,
    dispatchOnce: dispatchOnce,
    disableYandexProvider: function () {
      disableOptionalProviders();
      return true;
    },
    ensureYandexProvider: ensurePublicYandexProvider,
    providerBlocked: false,
    providerInitStarted: false,
    providerLoaded: false,
    sentEvents: [],
    startGrantedTracking: startPublicTracking,
    providerCaptureState: function () {
      return {
        blocked: publicProviderCaptureBlocked,
        failure: publicProviderCaptureFailure,
        endpoint: publicCaptureEndpoint(),
      };
    },
    version: "273-us2",
  };

  if (publicConfig) {
    window.GRAFPublicAnalytics = api;
  }
  runCookieConsent();
})();
