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
  const calls = {beacons: [], fetches: [], goals: [], reloads: 0, consentOptions: null };
  const localStorage = createStorage(settings.localStorage);
  const sessionStorage = createStorage(settings.sessionStorage);
  const requestListeners = {};

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
    Blob,
    document: {
      readyState: "complete",
      head: { appendChild() {} },
      createElement: () => ({
        setAttribute() {},
        addEventListener() {},
        remove() {},
        removeAttribute() {},
        style: {},
      }),
      getElementById: (id) =>
        id === "graf-public-analytics-config" || id === "graf-product-analytics-provider-config"
          ? { textContent: JSON.stringify(config) }
          : null,
      querySelector: () => null,
      querySelectorAll: () => [],
      addEventListener: (type, handler) => {
        requestListeners[type] = handler;
      },
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
      return { catch() {}, then() {} };
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
  return { sandbox, calls };
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
    revision: 202609151,
    copy_version: "2026-09-15.1",
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
  for (const call of calls.fetches) {
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
  assert.equal(config.enabled, true, "the harness needs an enabled public analytics context");
  assert.equal(config.posthog_capture_endpoint, RELAY_ENDPOINT);

  // 1. No decision yet: the visitor has not chosen anything.
  {
    const environment = createEnvironment(config);
    assert.equal(environment.sandbox.GRAFPublicAnalytics.consentReady, true);
    assert.equal(dispatch(environment, "public_download_viewed"), false);
    assert.equal(relayCalls(environment.calls), 0);
    assert.equal(environment.calls.goals.length, 0);
    assert.equal(environment.sandbox.sessionStorage.length, 0, "no view id before consent");
    assert.equal(environment.sandbox.localStorage.length, 0, "no storage before consent");
    console.log("ok no_decision_sends_nothing");
  }

  // 2. Explicit refusal on this visit and on a repeat visit.
  {
    const refused = createEnvironment(config);
    refused.calls.consentOptions.onConsent({
      cookie: consentRecord(["necessary"], "necessary_only"),
    });
    assert.equal(dispatch(refused, "public_download_viewed"), false);
    assert.equal(relayCalls(refused.calls), 0);
    assert.equal(refused.sandbox.sessionStorage.length, 0);

    const repeatVisit = createEnvironment(config, {
      localStorage: {
        [CONSENT_STORAGE_KEY]: JSON.stringify(consentRecord(["necessary"], "necessary_only")),
      },
    });
    assert.equal(repeatVisit.sandbox.GRAFPublicAnalytics.currentConsentState, "necessary_only");
    assert.equal(dispatch(repeatVisit, "public_download_viewed"), false);
    assert.equal(relayCalls(repeatVisit.calls), 0);
    assert.equal(repeatVisit.calls.goals.length, 0);
    console.log("ok refusal_is_kept_on_a_repeat_visit");
  }

  // 3. A damaged or unreadable decision is a refusal (FR-059).
  {
    const damaged = createEnvironment(config);
    damaged.calls.consentOptions.onConsent({ cookie: { categories: "analytics" } });
    assert.equal(damaged.sandbox.GRAFPublicAnalytics.currentConsentState, "unknown");
    assert.equal(dispatch(damaged, "public_download_viewed"), false);
    assert.equal(relayCalls(damaged.calls), 0);

    const unknownCategory = createEnvironment(config);
    unknownCategory.calls.consentOptions.onConsent({
      cookie: consentRecord(["necessary", "analytics", "telepathy"], "accepted_all"),
    });
    assert.equal(unknownCategory.sandbox.GRAFPublicAnalytics.currentConsentState, "unknown");
    assert.equal(dispatch(unknownCategory, "public_download_viewed"), false);
    assert.equal(relayCalls(unknownCategory.calls), 0);
    console.log("ok damaged_decision_is_a_refusal");
  }

  // 4. Granted analytics: ordinary page properties go to the first-party relay.
  {
    const granted = createEnvironment(config);
    granted.calls.consentOptions.onConsent({
      cookie: consentRecord([
        "necessary",
        "analytics",
        "advertising_attribution",
        "behavior_replay",
      ]),
    });
    assert.equal(
      relayCalls(granted.calls),
      1,
      "the page view of a consented visit reaches the relay",
    );
    const sent = dispatch(granted, "public_installer_download_clicked", {
      cta_location: "download_page_installer",
      target_kind: "installer_package",
    });
    assert.equal(sent, true);
    const body = await relayedBodyOf(granted.calls, "public_installer_download_clicked");
    assert.ok(body, "the consented click event reached the relay");
    assert.equal(body.page_path, "/download");
    assert.equal(body.surface, "public_download");
    assert.equal(body.consent_state, "accepted_all");
    assert.deepEqual(body.consent_categories, [
      "necessary",
      "analytics",
      "advertising_attribution",
      "behavior_replay",
    ]);
    assert.equal(body.cta_location, "download_page_installer");
    assert.match(body.view_id, /^[A-Za-z0-9][A-Za-z0-9_.:-]{7,119}$/);
    assert.ok(
      !JSON.stringify(body).toLowerCase().includes("document.title"),
      "only ordinary page properties are sent",
    );
    for (const call of granted.calls.fetches.concat(granted.calls.beacons)) {
      assert.equal(call.url, RELAY_ENDPOINT, "no external endpoint is contacted");
    }
    console.log("ok consented_event_uses_the_first_party_relay");
  }

  // 5. Revoked consent stops optional sends.
  {
    const granted = createEnvironment(config);
    granted.calls.consentOptions.onConsent({
      cookie: consentRecord(["necessary", "analytics"]),
    });
    assert.equal(dispatch(granted, "public_download_viewed"), true);
    granted.calls.consentOptions.onConsent({
      cookie: consentRecord(["necessary"], "revoked"),
    });
    const before = relayCalls(granted.calls);
    assert.equal(dispatch(granted, "public_download_viewed"), false);
    assert.equal(granted.sandbox.GRAFPublicAnalytics.providerCaptureState().blocked, true);
    assert.equal(relayCalls(granted.calls), before);
    console.log("ok revocation_stops_optional_sends");
  }

  // 6. An unavailable optional stack leaves the visitor's page working.
  {
    const failing = createEnvironment(config, { beaconFails: true });
    failing.sandbox.fetch = () => {
      throw new Error("network unavailable");
    };
    failing.calls.consentOptions.onConsent({
      cookie: consentRecord(["necessary", "analytics"]),
    });
    const api = failing.sandbox.GRAFPublicAnalytics;
    // The external counter is unavailable too, so the relay is the only path
    // left and it fails: nothing is reported as sent, and nothing throws.
    api.providerLoaded = false;
    api.providerInitStarted = true;
    let sent;
    assert.doesNotThrow(() => {
      sent = dispatch(failing, "public_download_viewed");
    });
    assert.equal(sent, false, "a failed relay does not count as a sent event");
    assert.equal(api.providerCaptureState().failure, true);
    console.log("ok provider_failure_does_not_break_the_page");
  }

  // 7. FR-006: consent to analytics alone never starts behaviour recording.
  {
    const analyticsOnly = createEnvironment(config);
    analyticsOnly.calls.consentOptions.onConsent({
      cookie: consentRecord(["necessary", "analytics"], "customized"),
    });
    const inits = analyticsOnly.calls.goals.filter((args) => args[1] === "init");
    assert.ok(inits.length >= 1, "the counter is initialised for consented analytics");
    for (const args of inits) {
      assert.equal(args[2].webvisor, false, "analytics alone must not enable the replay");
      assert.equal(args[2].clickmap, false, "analytics alone must not enable the click map");
      assert.equal(args[2].form_analytics, false, "form analytics is never enabled");
    }
    assert.equal(
      analyticsOnly.calls.goals.some((args) => args[2] && args[2].webvisor === true),
      false,
      "no counter configuration in this visit enables the replay",
    );
    assert.equal(analyticsOnly.calls.reloads, 0, "no reload is needed to keep the replay off");

    // The opposite direction proves the flag is decided by the visitor's choice
    // rather than being hardcoded to false.
    const withReplay = createEnvironment(config);
    withReplay.calls.consentOptions.onConsent({
      cookie: consentRecord(["necessary", "analytics", "behavior_replay"]),
    });
    const replayInits = withReplay.calls.goals.filter((args) => args[1] === "init");
    assert.ok(
      replayInits.some((args) => args[2].webvisor === true && args[2].clickmap === true),
      "the published replay scope still starts when the visitor allows it",
    );
    console.log("ok analytics_consent_alone_keeps_behaviour_recording_off");
  }

  // 8. FR-027: measurement reaches the credential pages, and a filled form
  // value never reaches it.
  {
    const typedEmail = "visitor-273@example.test";
    const authConfig = Object.assign({}, config, {
      external_counter_allowed: false,
      page_path: "/sign-up",
      surface: "public_signup",
    });
    const environment = createEnvironment(authConfig);
    // The page really holds a filled credential form. The controller shares the
    // document with it, so only the controller's own field list keeps the typed
    // value out of the measurement.
    const formField = {
      id: "email",
      name: "email",
      type: "email",
      value: typedEmail,
      getAttribute: (name) => (name === "value" ? typedEmail : null),
      closest: () => null,
    };
    environment.sandbox.document.getElementById = (id) =>
      id === "graf-public-analytics-config"
        ? { textContent: JSON.stringify(authConfig) }
        : id === "email"
          ? formField
          : null;
    environment.sandbox.document.querySelector = (selector) =>
      selector.indexOf("input") !== -1 ? formField : null;
    environment.sandbox.document.querySelectorAll = (selector) =>
      selector.indexOf("input") !== -1 ? [formField] : [];

    environment.calls.consentOptions.onConsent({
      cookie: consentRecord([
        "necessary",
        "analytics",
        "advertising_attribution",
        "behavior_replay",
      ]),
    });
    const pageViewSent = dispatch(environment, "public_signup_viewed", {});
    // The typed value is offered to the controller as well, so the check covers
    // a caller that tries to attach it rather than only the page itself.
    dispatch(environment, "public_signup_viewed", {
      email: typedEmail,
      form_value: typedEmail,
      page_path: "/sign-up?email=" + typedEmail,
    });

    assert.equal(pageViewSent, true, "the consented signup page view reaches the relay");
    const bodies = await relayedBodies(environment.calls);
    assert.ok(bodies.length >= 1, "the signup page view was measured");
    for (const body of bodies) {
      assert.ok(body, "every relayed body is JSON");
      const text = JSON.stringify(body);
      assert.ok(!text.includes(typedEmail), "no typed credential value may be measured");
      assert.ok(!text.includes("example.test"), "no credential domain may be measured");
      assert.ok(!text.includes("form_value"), "no form field name may be measured");
      assert.equal(body.page_path, "/sign-up");
      assert.equal(body.surface, "public_signup");
      assert.equal(body.event_name, "public_signup_viewed");
    }
    // The credential page is relay-only: the external counter stays off it, so
    // no third-party script receives anything from this page.
    assert.equal(environment.calls.goals.length, 0, "no external counter on the signup page");
    assert.equal(environment.sandbox.GRAFPublicAnalytics.providerBlocked, true);
    assert.equal(environment.sandbox.GRAFPublicAnalytics.config.external_counter_allowed, false);
    for (const call of environment.calls.fetches.concat(environment.calls.beacons)) {
      assert.equal(call.url, RELAY_ENDPOINT, "the signup page talks to the first-party relay only");
    }
    console.log("ok signup_page_view_is_measured_without_form_values");
  }

  // 9. FR-004: the assembled modal offers refusal as the same kind of action as
  // consent, in one step, and does not hide it behind the preferences.
  {
    const environment = createEnvironment(config);
    const options = environment.sandbox.GRAFPublicAnalytics.consentOptions;
    assert.ok(options, "the controller must expose the options it assembled");
    const consentModal = options.language.translations.ru.consentModal;
    const preferencesModal = options.language.translations.ru.preferencesModal;
    assert.equal(consentModal.acceptAllBtn, "Разрешить все");
    assert.equal(consentModal.acceptNecessaryBtn, "Только необходимые");
    assert.equal(
      consentModal.acceptNecessaryBtn,
      preferencesModal.acceptNecessaryBtn,
      "the refusal label must not change between the banner and the settings",
    );
    assert.equal(
      consentModal.acceptAllBtn,
      preferencesModal.acceptAllBtn,
      "the acceptance label must not change between the banner and the settings",
    );
    assert.equal(options.mode, "opt-in");
    assert.equal(
      typeof options.onConsent,
      "function",
      "both decisions must arrive through the same handler",
    );
    assert.equal(options.onConsent, options.onChange, "one handler decides both directions");
    // A refusal is one action: no extra click, no preferences step, and the
    // modal itself must say how to refuse (FR-005).
    assert.match(consentModal.description, /Отказаться можно кнопкой «Только необходимые»/);
    assert.equal(consentModal.showPreferencesBtn, "Настроить");
    console.log("ok refusal_is_the_same_action_as_consent");
  }

  console.log("public_analytics_consent_harness=pass");
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
