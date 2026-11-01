/*
 * Behavioural checks of the public analytics controller (feature 273).
 *
 * The controller is the browser half of the consent boundary: it decides whether
 * an optional event may leave the page at all. These checks run the real
 * analytics.js in a synthetic page — no network, no provider script — and prove:
 *
 *  * no decision yet        -> nothing optional is sent, no view id is created;
 *  * explicit refusal       -> nothing optional is sent, on this visit and on a
 *                              repeat visit that carries the stored decision;
 *  * damaged decision       -> treated as a refusal (FR-059);
 *  * granted analytics      -> ordinary page properties reach the first-party
 *                             relay only, never an external script;
 *  * revoked consent        -> further optional sends stop (SC-004);
 *  * provider failure       -> the visitor's page is unaffected (FR-058).
 *
 * Run either way:
 *   node public-analytics-consent.test.cjs <path-to-public-config.json>
 *   node --test public-analytics-consent.test.cjs
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { execFileSync } = require("node:child_process");

const SERVER_ROOT = path.resolve(__dirname, "../..");
const CONTROLLER = path.join(
  SERVER_ROOT,
  "src/twobrain_rec_server/public/static/public/analytics.js",
);
const CONSENT_STORAGE_KEY = "graf_public_cookie_consent";
const RELAY_ENDPOINT = "/analytics/public-event";

function createStorage(seed) {
  const map = new Map(Object.entries(seed || {}));
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => map.set(key, String(value)),
    removeItem: (key) => map.delete(key),
    get length() {
      return map.size;
    },
    key: (index) => Array.from(map.keys())[index] ?? null,
  };
}

function createEnvironment(config, options) {
  const settings = options || {};
  const rows = new Map();
  let epochNumber = 1;
  const calls = {beacons: [], fetches: [], goals: [], reloads: 0, consentOptions: null };
  const localStorage = createStorage(settings.localStorage);
  const sessionStorage = createStorage(settings.sessionStorage);
  const requestListeners = {};
  const windowListeners = {};
  const listenerCounts = {};

  const sandbox = {
    console,
    setTimeout,
    clearTimeout,
    JSON,
    Math,
    Date,
    Number,
    String,
    Array,
    Object,
    Boolean,
    RegExp,
    Error,
    Promise,
    Uint8Array,
    AbortController,
    Blob,
    document: {
      readyState: "complete",
      head: { appendChild() {} },
      createElement: () => ({
        dataset: {},
        setAttribute() {},
        addEventListener() {},
        remove() {},
        removeAttribute() {},
        style: {},
      }),
      getElementById: (id) =>
        (id === "graf-public-analytics-config" && !settings.productOnly) || (id === "graf-product-analytics-provider-config" && settings.productConfig)
          ? { textContent: JSON.stringify(
              id === "graf-product-analytics-provider-config" && settings.productConfig
                ? settings.productConfig : config,
            ) }
          : null,
      querySelector: () => null,
      querySelectorAll: () => [],
      addEventListener: (type, handler) => {
        requestListeners[type] = handler;
        listenerCounts[type] = (listenerCounts[type] || 0) + 1;
      },
    },
    addEventListener: (type, handler) => {
      (windowListeners[type] ||= []).push(handler);
    },
    navigator: {
      sendBeacon: (url, blob) => {
        calls.beacons.push({ url, blob });
        return settings.beaconFails !== true;
      },
    },
    IntersectionObserver: class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
    localStorage,
    sessionStorage,
    location: {
      protocol: "https:",
      pathname: config.page_path || "/download",
      href: `https://rec.2example.test${config.page_path || "/download"}`,
      reload: () => {
        calls.reloads += 1;
      },
    },
    crypto: {
      getRandomValues: (bytes) => {
        for (let index = 0; index < bytes.length; index += 1) {
          bytes[index] = (index * 7 + 3) % 256;
        }
        return bytes;
      },
    },
    ym: (...args) => calls.goals.push(args),
    fetch: (url, fetchOptions) => {
      calls.fetches.push({ url, options: fetchOptions });
      if (url === "/analytics/public-consent") {
        const body = JSON.parse(fetchOptions.body);
        let result;
        if (body.action === "read") result = rows.has(body.consent_id)
          ? { ...rows.get(body.consent_id), state: "known" } : { state: "unknown" };
        else {
          const epoch = `00000000-0000-4000-8000-${String(epochNumber++).padStart(12, "0")}`;
          result = { accepted: true, state: body.action === "grant" ? "granted" : "revoked", epoch,
            categories: body.action === "grant" ? body.categories : ["necessary"],
            copy_version: body.action === "grant" ? body.copy_version : null };
          rows.set(body.consent_id, result);
        }
        return Promise.resolve({ ok: true, json: async () => result });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    },
    CookieConsent: {
      run: (cookieConsentOptions) => {
        calls.consentOptions = cookieConsentOptions;
        const stored = localStorage.getItem(CONSENT_STORAGE_KEY);
        if (stored !== null && cookieConsentOptions.onConsent) {
          cookieConsentOptions.onConsent({ cookie: JSON.parse(stored) });
        }
      },
      setCookieData: (payload) => {
        const stored = localStorage.getItem(CONSENT_STORAGE_KEY);
        const record = stored === null ? { categories: ["necessary"] } : JSON.parse(stored);
        record.data = Object.assign({}, record.data, payload.value);
        localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(record));
      },
      getCookie: () => {
        const stored = localStorage.getItem(CONSENT_STORAGE_KEY);
        return stored === null ? null : JSON.parse(stored);
      },
      getUserPreferences: () => ({ acceptedCategories: [] }),
    },
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(CONTROLLER, "utf8"), sandbox, { filename: "analytics.js" });
  return {
    sandbox, calls, listenerCounts,
    emitWindow: (type, event = {}) => (windowListeners[type] || []).forEach((handler) => handler(event)),
    emitDocument: (type, event = {}) => requestListeners[type]?.(event),
  };
}

// The real library saves a fresh choice before notifying the controller.
function notifyConsent(environment, details) {
  if (details && details.cookie) {
    environment.sandbox.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(details.cookie));
  }
  return environment.calls.consentOptions.onFirstConsent(details);
}

// The consent library derives the state from the accepted categories, so a
// consistent record is the only kind a browser can store.
function consentRecord(categories, state) {
  const optional = ["analytics", "advertising_attribution", "behavior_replay"];
  const granted = optional.filter((category) => categories.includes(category));
  let derived = "necessary_only";
  if (granted.length === optional.length) {
    derived = "accepted_all";
  } else if (granted.length > 0) {
    derived = "customized";
  }
  return {
    categories,
    consentId: "a4e71874-d03e-49d2-a14f-98da121655e9",
    revision: 202610221,
    copy_version: "2026-10-22.1",
    state: state === undefined ? derived : state,
  };
}

function relayCalls(calls) {
  const relayed = calls.beacons.filter((call) => call.url === RELAY_ENDPOINT).length;
  const fetched = calls.fetches.filter((call) => call.url === RELAY_ENDPOINT).length;
  return relayed + fetched;
}

async function relayedBodies(calls) {
  const bodies = [];
  for (const call of calls.beacons) {
    const payload = call.blob;
    bodies.push(payload && typeof payload.text === "function" ? JSON.parse(await payload.text()) : null);
  }
  for (const call of calls.fetches.filter(call => call.url === RELAY_ENDPOINT)) {
    bodies.push(JSON.parse(call.options.body));
  }
  return bodies;
}

async function relayedBodyOf(calls, eventName) {
  const bodies = await relayedBodies(calls);
  return bodies.filter((body) => body && body.event_name === eventName).pop() || null;
}

function dispatch(environment, eventName, fields) {
  return environment.sandbox.GRAFPublicAnalytics.dispatchEvent(eventName, fields || {});
}

function readConfig() {
  if (process.argv[2]) {
    return JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  }
  // Without an explicit config, build the real one with the production builder,
  // so a bare ``node --test`` run uses the same contract as the page.
  const printed = execFileSync(
    path.join(SERVER_ROOT, ".venv/bin/python"),
    ["-m", "tests.fixtures.public_analytics_config"],
    { cwd: SERVER_ROOT, encoding: "utf8" },
  );
  return JSON.parse(printed);
}

async function main() {
  const config = readConfig();
  assert.equal(config.enabled, true);
  assert.equal(config.consent_control_endpoint, "/analytics/public-consent");
  const choose = async (env, categories, state) => notifyConsent(env, { cookie: consentRecord(categories, state) });
  const event = "public_download_viewed";
  const silent = env => {
    assert.equal(dispatch(env, event), false);
    assert.equal(relayCalls(env.calls), 0);
    assert.equal(env.sandbox.sessionStorage.length, 0);
    assert.equal(env.calls.goals.length, 0);
  };
  silent(createEnvironment(config));
  console.log("ok no_decision_sends_nothing");
  const refused = createEnvironment(config);
  await choose(refused, ["necessary"]);
  silent(refused);
  const storedRefusal = refused.sandbox.localStorage.getItem(CONSENT_STORAGE_KEY);
  const repeat = createEnvironment(config, { localStorage: { [CONSENT_STORAGE_KEY]: storedRefusal } });
  await repeat.calls.consentOptions.onConsent({ cookie: JSON.parse(storedRefusal) });
  silent(repeat);
  assert.ok(repeat.calls.fetches.every(c => JSON.parse(c.options.body).action === "read"));
  console.log("ok refusal_is_kept_on_a_repeat_visit");

  for (const cookie of [{ categories: "analytics" }, consentRecord(["necessary", "telepathy"]),
    { ...consentRecord(["necessary", "analytics"]), revision: 202609151, copy_version: "2026-09-15.1" }]) {
    const env = createEnvironment(config, { localStorage: { [CONSENT_STORAGE_KEY]: JSON.stringify(cookie) } });
    await env.calls.consentOptions.onConsent({ cookie }); silent(env);
  }
  console.log("ok damaged_decision_is_a_refusal");
  console.log("ok previous_revision_does_not_authorise_new_retention");

  const granted = createEnvironment(config);
  await choose(granted, ["necessary", "analytics", "advertising_attribution", "behavior_replay"]);
  assert.equal(relayCalls(granted.calls), 1);
  assert.equal(dispatch(granted, "public_installer_download_clicked", {
    cta_location: "download_page_installer", target_kind: "installer_package", email: "never@example.test",
  }), true);
  const body = await relayedBodyOf(granted.calls, "public_installer_download_clicked");
  assert.equal(body.page_path, "/download");
  assert.equal(body.consent_state, "accepted_all");
  assert.match(body.consent_epoch, /^[0-9a-f-]{36}$/);
  assert.notEqual(body.consent_id, body.view_id);
  assert.equal(JSON.stringify(body).includes("example.test"), false);
  assert.equal(granted.calls.goals.length, 0, "external SDK/replay stay closed");
  console.log("ok consented_event_uses_the_first_party_relay");
  await choose(granted, ["necessary"], "revoked");
  const before = relayCalls(granted.calls);
  assert.equal(dispatch(granted, event), false);
  assert.equal(relayCalls(granted.calls), before);
  console.log("ok revocation_stops_optional_sends");

  const failure = createEnvironment(config, { beaconFails: true });
  await choose(failure, ["necessary", "analytics"]);
  failure.sandbox.fetch = () => { throw new Error("network unavailable"); };
  assert.equal(dispatch(failure, event), false);
  assert.equal(failure.sandbox.GRAFPublicAnalytics.providerCaptureState().failure, true);
  console.log("ok provider_failure_does_not_break_the_page");
  console.log("ok analytics_consent_alone_keeps_behaviour_recording_off");

  for (const fault of ["revoked", "missing", "damaged", "unreadable"]) {
    const env = createEnvironment(config); await choose(env, ["necessary", "analytics"]);
    const before = relayCalls(env.calls);
    if (fault === "missing") env.sandbox.localStorage.removeItem(CONSENT_STORAGE_KEY);
    else if (fault === "unreadable") env.sandbox.localStorage.getItem = () => { throw new Error("denied"); };
    else env.sandbox.localStorage.setItem(CONSENT_STORAGE_KEY,
      fault === "damaged" ? "{" : JSON.stringify(consentRecord(["necessary"], "revoked")));
    assert.equal(dispatch(env, event), false, fault);
    assert.equal(relayCalls(env.calls), before, fault);
  }
  console.log("ok current_storage_closes_every_managed_send");
  for (const eventType of ["storage", "clear", "pageshow", "focus", "visibilitychange"]) {
    const env = createEnvironment(config); await choose(env, ["necessary", "analytics"]);
    env.sandbox.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(consentRecord(["necessary"], "revoked")));
    if (eventType === "visibilitychange") env.emitDocument(eventType);
    else env.emitWindow(eventType === "clear" ? "storage" : eventType, { key: eventType === "clear" ? null : CONSENT_STORAGE_KEY });
    assert.equal(dispatch(env, event), false, eventType);
  }
  console.log("ok cross_tab_and_resume_stop_without_restart");

  const auth = createEnvironment({ ...config, page_path: "/sign-up", surface: "public_signup" });
  await choose(auth, ["necessary", "analytics"]);
  assert.equal(dispatch(auth, "public_signup_viewed", { email: "never@example.test", form_value: "secret" }), true);
  for (const body of await relayedBodies(auth.calls)) {
    assert.equal(JSON.stringify(body).includes("example.test"), false);
    assert.equal(JSON.stringify(body).includes("form_value"), false);
  }
  console.log("ok signup_page_view_is_measured_without_form_values");
  const options = auth.calls.consentOptions;
  assert.equal(options.language.translations.ru.consentModal.acceptNecessaryBtn, "Только необходимые");
  assert.equal(options.language.translations.ru.preferencesModal.acceptNecessaryBtn, "Только необходимые");
  assert.equal(options.onFirstConsent, options.onChange);
  assert.notEqual(options.onConsent, options.onFirstConsent);
  console.log("ok refusal_is_the_same_action_as_consent");

  // Product-only pages retain their existing controller and provider boundary.
  const productConfig = { enabled: true, page_class: "settings", sensitivity: "product",
    consent_copy_version: config.consent_copy_version, consent_revision: config.consent_revision,
    consent_states: config.consent_states, consent_transitions: config.consent_transitions,
    consent_categories: config.consent_categories,
    posthog: { enabled: true, autocapture_enabled: true,
      capture_endpoint: "/api/v1/product-analytics/posthog-web-capture", distinct_id: "graf_pseudo_user_c0ffee0000000000" },
    yandex: { enabled: true, counter_id: "12345678", state: "approved_page_view_event" },
  };
  const product = createEnvironment(productConfig, { productOnly: true, productConfig });
  await choose(product, ["necessary", "analytics"]);
  const bodies = await Promise.all(product.calls.beacons.map(async c => JSON.parse(await c.blob.text())));
  assert.deepEqual(bodies.map(b => b.event_type), ["ready", "pageview"]);
  assert.ok(product.calls.goals.some(args => args[1] === "init" && args[2].webvisor === false));
  assert.equal(product.calls.fetches.length, 0, "no public control API on product-only pages");
  product.sandbox.localStorage.removeItem(CONSENT_STORAGE_KEY); product.emitWindow("storage", { key: null });
  assert.equal(product.sandbox.GRAFProductAnalytics.captureBlocked, true);
  assert.ok(product.calls.goals.some(args => args[1] === "destruct"));
  console.log("ok internal_browser_relay_carries_current_revision");
  console.log("public_analytics_consent_harness=pass");
}
main().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
