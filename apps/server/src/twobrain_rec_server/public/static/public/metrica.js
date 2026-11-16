(function () {
  "use strict";
  var node = document.getElementById("graf-public-analytics-config");
  if (!node || window.GRAFPublicMetrica) return;
  var config;
  try { config = JSON.parse(node.textContent); } catch (_) { return; }
  if (!config.automatic_enabled || ["/", "/download"].indexOf(config.page_path) === -1) return;
  var key = "graf_public_metrica_choice";
  var legacyKey = config.consent_storage_key || "graf_public_cookie_consent";
  var active = false, attempted = false, stopped = false, replay = false, script;
  var buttons = document.querySelectorAll("[data-metrica-toggle]");
  var storageReady = false;
  try {
    window.localStorage.setItem(key + ".probe", "1");
    storageReady = window.localStorage.getItem(key + ".probe") === "1";
    window.localStorage.removeItem(key + ".probe");
  } catch (_) {}

  function preference() {
    try {
      if (!storageReady) return {allowed: false};
      var storage = window.localStorage;
      var choice = storage.getItem(key);
      if (choice === "disabled") return {allowed: false};
      var raw = storage.getItem(legacyKey);
      if (choice !== null) {
        var explicit = JSON.parse(choice);
        // A later legacy refusal supersedes the explicit re-enable action.
        if (explicit.enabled !== true || !Object.prototype.hasOwnProperty.call(explicit, "legacy")) return {allowed: false};
        if (explicit.legacy === raw) return {allowed: true, replay: true};
      }
      if (raw === null) return {allowed: true, replay: true};
      var legacy = JSON.parse(raw);
      var state = legacy.data && legacy.data.graf_consent_state;
      if (["revoked", "necessary_only", "unknown"].indexOf(state) !== -1) return {allowed: false};
      var categories = legacy.categories;
      if (!Array.isArray(categories) || categories.indexOf("necessary") === -1 ||
          categories.some(function (c) { return ["necessary", "analytics", "behavior_replay", "advertising_attribution"].indexOf(c) === -1; })) {
        return {allowed: false};
      }
      return {allowed: categories.indexOf("analytics") !== -1,
        replay: categories.indexOf("behavior_replay") !== -1,
        attribution: categories.indexOf("advertising_attribution") !== -1};
    } catch (_) { return {allowed: false}; }
  }

  function trustedMapFrame() {
    try {
      if (!config.replay_allowed) return false;
      var parent = new URL(document.referrer);
      if (parent.protocol !== "https:" || parent.port) return false;
      var origins = config.map_frame_origins || [];
      return origins.indexOf(parent.origin) !== -1 ||
        (origins.indexOf("https://*.webvisor.com") !== -1 && parent.hostname.endsWith(".webvisor.com"));
    } catch (_) { return false; }
  }
  function safeAddress(pref) {
    try {
      var url = new URL(window.location.href);
      if ((window.top !== window.self && !trustedMapFrame()) || url.pathname !== config.page_path || url.username || url.password) return false;
      if (url.hash && ["#main", "#top", "#for-whom", "#how", "#faq", "#price", "#analytics-settings"].indexOf(url.hash) === -1) return false;
      var seen = new Set();
      for (var pair of url.searchParams) {
        var name = pair[0], value = pair[1];
        if (pref.attribution === false || seen.has(name)) return false;
        seen.add(name);
        if (name === "yclid" && /^\d{1,32}$/.test(value)) continue;
        if (name === "ysclid" && /^[a-z0-9]{1,64}$/.test(value)) continue;
        if (!/^utm_(source|medium|campaign|id|content|term)$/.test(name) ||
            !value || (name === "utm_source" || name === "utm_medium" ? value.trim().toLowerCase() : value.trim()) !== (config.campaign_attribution || {})[name]) return false;
      }
      return true;
    } catch (_) { return false; }
  }

  function stop() {
    stopped = true;
    if (script && !active) script.remove();
    if (active) {
      active = false;
      try { window.ym(config.yandex_metrica_id, "destruct"); } catch (_) {}
    }
  }
  function updateButtons(pref) {
    buttons.forEach(function (button) {
      button.textContent = pref.allowed ? "Отключить Метрику и Вебвизор" : "Включить Метрику и Вебвизор";
      button.setAttribute("aria-pressed", String(Boolean(pref.allowed)));
    });
  }
  function refresh() {
    var pref = preference();
    updateButtons(pref);
    if (!pref.allowed || !safeAddress(pref) || (active && replay && !pref.replay)) stop();
    if (attempted || stopped || !pref.allowed || !safeAddress(pref) || !config.external_counter_allowed) return;
    attempted = true;
    script = document.createElement("script");
    script.async = true;
    script.src = "https://mc.yandex.ru/metrika/tag.js";
    script.referrerPolicy = "no-referrer";
    script.onerror = stop;
    script.onload = function () {
      pref = preference();
      if (stopped || !pref.allowed || !safeAddress(pref) || typeof window.ym !== "function") return;
      function maskFields() {
        document.querySelectorAll("form, input, textarea, select, [contenteditable]").forEach(function (el) {
          el.classList.add("ym-hide-content", "ym-disable-keys", "ym-disable-submit");
        });
      }
      maskFields();
      if (typeof window.MutationObserver === "function") {
        new window.MutationObserver(maskFields).observe(document.documentElement, {
          childList: true, subtree: true, attributes: true, attributeFilter: ["contenteditable"]
        });
      }
      replay = Boolean(config.replay_allowed && pref.replay);
      try {
        window.ym(config.yandex_metrica_id, "init", {
          defer: true, webvisor: replay, clickmap: replay, trackLinks: false,
          trackHash: false, accurateTrackBounce: true, childIframe: false,
          ecommerce: false, disableYtm: true, sendTitle: false
        });
        active = true;
        var referer = "";
        try { referer = new URL(document.referrer).origin + "/"; } catch (_) {}
        var address = new URL(window.location.origin + config.page_path);
        new URL(window.location.href).searchParams.forEach(function (value, name) {
          address.searchParams.set(name, name.indexOf("utm_") === 0 ? config.campaign_attribution[name] : value);
        });
        window.ym(config.yandex_metrica_id, "hit", address.href, {referer: referer});
        goal(config.surface === "public_landing" ? "public_landing_viewed" : "public_download_viewed", {});
        observeSections();
      } catch (_) { stop(); }
    };
    window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
    window.ym.l = window.ym.l || Date.now();
    document.head.appendChild(script);
  }

  function goal(name, fields) {
    var pref = preference();
    if (!active || !pref.allowed || !safeAddress(pref) || (replay && !pref.replay)) { if (active) stop(); return; }
    var event = (config.event_catalog || []).find(function (entry) { return entry.event_name === name; });
    if (!event || (event.surface && event.surface !== config.surface)) return;
    var params = {};
    for (var field of Object.keys(fields)) {
      if (event.stable_fields.indexOf(field) === -1 ||
          (config.stable_labels[field] || []).indexOf(fields[field]) === -1) return;
      params[field] = fields[field];
    }
    try { window.ym(config.yandex_metrica_id, "reachGoal", name, params); } catch (_) { stop(); }
  }
  document.querySelectorAll("[data-analytics-cta]").forEach(function (el) {
    el.addEventListener("click", function () {
      var target = el.dataset.analyticsTarget || "download_page";
      goal(target === "installer_package" ? "public_installer_download_clicked" :
        target === "login" ? "public_login_intent_clicked" : "public_landing_cta_clicked",
        {cta_location: el.dataset.analyticsCta, target_kind: target});
    });
  });
  [["graf:product-tab-selected", "public_product_tab_selected", "product_tab", "productTab"],
    ["graf:pricing-cycle-selected", "public_pricing_cycle_selected", "pricing_cycle", "pricingCycle"]].forEach(function (entry) {
    document.addEventListener(entry[0], function (event) {
      var fields = {}; fields[entry[2]] = (event.detail || {})[entry[3]]; goal(entry[1], fields);
    });
  });
  document.querySelectorAll("details[data-faq-id]").forEach(function (el) {
    el.addEventListener("toggle", function () { if (el.open) goal("public_faq_opened", {faq_item: el.dataset.faqId}); });
  });
  function observeSections() {
    if (typeof window.IntersectionObserver !== "function") return;
    var observer = new window.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting && active) {
          goal("public_landing_section_seen", {section_id: entry.target.dataset.analyticsSection});
          observer.unobserve(entry.target);
        }
      });
    }, {threshold: 0.12});
    document.querySelectorAll("[data-analytics-section]").forEach(function (el) { observer.observe(el); });
  }
  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      var enabled = !preference().allowed;
      if (!enabled) stop();
      try {
        var value = enabled ? JSON.stringify({enabled: true, legacy: window.localStorage.getItem(legacyKey)}) : "disabled";
        window.localStorage.setItem(key, value);
        if (window.localStorage.getItem(key) !== value) throw new Error();
        if (enabled && attempted) { window.location.reload(); return; }
        stopped = !enabled;
        refresh();
      } catch (_) {
        stop();
        document.querySelectorAll("[data-metrica-status]").forEach(function (el) {
          el.textContent = "Метрика остановлена. Браузер не позволяет сохранить выбор; заблокируйте сторонние скрипты в его настройках.";
        });
      }
    });
  });
  window.GRAFPublicMetrica = {stop: stop};
  window.addEventListener("storage", function (event) {
    if (event.key === null || event.key === key || event.key === legacyKey) refresh();
  });
  ["focus", "pageshow", "hashchange", "popstate"].forEach(function (event) { window.addEventListener(event, refresh); });
  document.addEventListener("visibilitychange", refresh);
  refresh();
})();
