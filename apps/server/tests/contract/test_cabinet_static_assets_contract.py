import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "cabinet" / "static" / "cabinet"


def test_local_htmx_asset_is_pinned_with_source_and_license() -> None:
    htmx = (STATIC_DIR / "htmx-2.0.10.min.js").read_text()
    source = (STATIC_DIR / "htmx-2.0.10.source.txt").read_text()

    assert 'version:"2.0.10"' in htmx
    assert "selfRequestsOnly:true" in htmx
    assert "source: https://unpkg.com/htmx.org@2.0.10/dist/htmx.min.js" in source
    assert "package: https://www.npmjs.com/package/htmx.org/v/2.0.10" in source
    assert "license: 0BSD" in source


def test_cabinet_static_assets_do_not_reference_runtime_cdns_or_build_outputs() -> None:
    forbidden = (
        "cdn.",
        "cdnjs",
        "jsdelivr",
        "googleapis",
        "fonts.gstatic",
        "tailwind",
        "daisyui",
        "flowbite",
        "shadcn",
        "react",
        "vue",
        "svelte",
        "webpack",
        "vite",
    )
    checked = [
        STATIC_DIR / "cabinet.css",
        STATIC_DIR / "cabinet.js",
    ]

    for path in checked:
        content = path.read_text().lower()
        assert not [marker for marker in forbidden if marker in content]


def test_cabinet_brand_assets_are_local_and_nonempty() -> None:
    for filename in [
        "graf-icon.png",
        "graf-icon@2x.png",
        "favicon.ico",
        "favicon-16.png",
        "favicon-32.png",
        "apple-touch-icon.png",
        "graf-wordmark-dark.png",
        "graf-wordmark-dark@2x.png",
        "graf-wordmark-light.png",
        "graf-wordmark-light@2x.png",
    ]:
        path = STATIC_DIR / filename
        assert path.is_file()
        assert path.stat().st_size > 0


def test_cabinet_js_wires_csrf_header_for_unsafe_htmx_requests() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert 'meta[name="csrf-token"]' in script
    assert "htmx:configRequest" in script
    assert "X-CSRF-Token" in script
    assert "POST" in script
    assert "DELETE" in script


def test_tooltip_does_not_enter_layout_flow() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    tooltip_body = css[css.index(".cabinet-tooltip__body {") : css.index(".cabinet-tooltip:hover")]

    assert "position: absolute;" in tooltip_body
    assert "inset-inline-start: calc(100% + var(--tooltip-offset));" in tooltip_body
    assert "inset-block-start: 50%;" in tooltip_body
    assert "transform: translateY(calc(-50% - 2px));" in tooltip_body
    assert "max-width: min(var(--tooltip-max-width), 80vw);" in tooltip_body
    assert ".manual-upload-dialog .cabinet-tooltip__body" not in css
    assert "display: contents" not in tooltip_body
    assert "flex: 1 0 100%" not in tooltip_body
    assert ".settings-control-row:has(.cabinet-tooltip" not in css


def test_all_tooltips_use_one_shared_configuration() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    tokens = css[css.index(":root {") : css.index("}", css.index(":root {"))]
    tooltip = css[css.index(".cabinet-tooltip {") : css.index(".cabinet-loader {")]

    for token in [
        "--tooltip-trigger-size: 24px;",
        "--tooltip-icon-size: 14px;",
        "--tooltip-offset: 6px;",
        "--tooltip-max-width: 280px;",
        "--tooltip-padding: 8px 10px;",
        "--tooltip-radius: 10px;",
        "--tooltip-layer: 10;",
    ]:
        assert token in tokens
    for use in [
        "var(--tooltip-trigger-size)",
        "var(--tooltip-icon-size)",
        "var(--tooltip-offset)",
        "var(--tooltip-max-width)",
        "var(--tooltip-padding)",
        "var(--tooltip-radius)",
        "var(--tooltip-layer)",
    ]:
        assert use in tooltip
    assert (
        ".settings-control-row__title .cabinet-tooltip__body {\n    inset-inline-start: 50%;\n    transform: translate(-50%, calc(-50% - 2px));"
        in tooltip
    )
    assert (
        ".settings-control-row__title .cabinet-tooltip:focus-within .cabinet-tooltip__body {\n    transform: translate(-50%, -50%);"
        in tooltip
    )


def test_cabinet_js_keeps_fragment_state_ephemeral() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "htmx:afterSwap" in script
    assert "meeting-list-region" in script
    assert "localStorage" not in script
    assert script.count("sessionStorage") == 13
    assert script.count('sessionStorage.removeItem("htmx-history-cache")') == 1
    assert script.count('sessionStorage.removeItem("htmx-current-path-for-history")') == 2
    assert "graf-summary-candidate-" in script
    assert "sessionStorage.setItem(candidateStorageKey, JSON.stringify({" in script
    assert 'sessionStorage.getItem("graf-cabinet-rail")' in script
    assert (
        'sessionStorage.setItem("graf-cabinet-rail", pinned ? "expanded" : "collapsed")' in script
    )
    assert "poll_url: candidate.poll_url" in script
    assert "template: activeTemplate" in script


def test_processing_recovery_poll_is_not_dropped_while_window_is_hidden() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    recovery_polling = script[
        script.index("const scheduleProcessingRecoveryPolling") :
        script.index("const processingProjectionFromActionPayload")
    ]

    assert "if (!document.hidden)" not in recovery_polling
    assert "const delay = document.hidden || remaining === null" in recovery_polling


def test_processing_status_poll_recovers_after_transient_failure_while_hidden() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const refreshProcessingStatus"),
  script.indexOf("const processingProjectionFromActionPayload"),
);
const detail = {
  dataset: { processingStatusUrl: "/api/v1/meetings/meeting-a/processing" },
  isConnected: true,
};
const recovery = { closest: () => detail };
const timers = [];
const responses = [
  { ok: false, status: 503 },
  { ok: true, status: 200, json: async () => ({ meeting_id: "meeting-a", state: "failed_terminal", retry_class: "terminal" }) },
  { ok: false, status: 503 },
];
let failures = 0;
let rendered = 0;
global.document = {
  hidden: true,
  querySelector: (selector) => selector === "[data-processing-recovery]" ? recovery : null,
};
global.window = {
  setTimeout(callback, delay) { timers.push({ callback, delay }); return timers.length; },
};
global.fetch = async () => responses.shift();
vm.runInThisContext(`
  let processingRecoveryGeneration = 0;
  let processingRecoveryActionRequest = null;
  let processingRecoveryRequest = null;
  let processingRecoveryStatusController = null;
  let processingRecoveryPollTimer = null;
  const stopProcessingRecoveryPolling = () => {};
  const abortProcessingRecoveryStatusRequest = () => {};
  const recoverMeetingDetailFromResponse = async () => false;
  const processingProjectionMatchesDetail = () => true;
  const renderProcessingProjection = (_detail, projection) => {
    rendered += 1;
    detail.dataset.processingTerminal = projection.retry_class === "terminal" ? "true" : "false";
    return true;
  };
  const renderProcessingRecoveryFailure = () => { failures += 1; };
  ${source}
  global.refreshProcessingStatus = refreshProcessingStatus;
`);
(async () => {
  await global.refreshProcessingStatus();
  if (failures !== 1 || timers.length !== 1 || timers[0].delay !== 15000) {
    throw new Error("transient status failure did not schedule one bounded retry");
  }
  timers.shift().callback();
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  if (rendered !== 1 || responses.length !== 1) {
    throw new Error("hidden retry did not render the later terminal projection");
  }
  await global.refreshProcessingStatus({ force: true });
  if (failures !== 1 || timers.length !== 0 || responses.length !== 0) {
    throw new Error("terminal projection restarted polling after a transient refresh failure");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_processing_status_failure_preserves_ready_transcript_and_export() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const renderProcessingRecoveryFailure"),
  script.indexOf("const abortProcessingRecoveryStatusRequest"),
);
const transcript = { hidden: false, setAttribute(_name, value) { this.ariaHidden = value; } };
const pending = { hidden: true };
const recovery = {
  hidden: true,
  dataset: {},
  setAttribute() {},
  querySelector(selector) {
    if (selector === "[data-processing-recovery-title]") return { textContent: "" };
    if (selector === "[data-processing-recovery-copy]") return { textContent: "" };
    if (selector === "[data-processing-check]") return null;
    if (selector === "[data-processing-new-attempt]") return null;
    if (selector === "[data-processing-upload-another]") return null;
    if (selector === "[data-processing-refresh]") return null;
    return null;
  },
};
const detail = {
  dataset: { processingTranscriptVisible: "true" },
  querySelector(selector) {
    if (selector === "[data-processing-recovery]") return recovery;
    if (selector === "[data-playback-transcript]") return transcript;
    if (selector === "[data-transcript-pending]") return pending;
    return null;
  },
};
const resetProcessingRecoveryCountdown = () => {};
const stopProcessingRecoveryPolling = () => {};
let exported = null;
let announcement = "";
const updateProcessingExportVisibility = (value) => { exported = value; };
const announceProcessingChange = (_detail, value) => { announcement = value; };
vm.runInThisContext(`${source}; global.renderProcessingRecoveryFailure = renderProcessingRecoveryFailure;`);
global.renderProcessingRecoveryFailure(detail);
if (transcript.hidden || transcript.ariaHidden !== "false" || pending.hidden !== true || exported !== true) {
  throw new Error("transient status failure hid ready content");
}
if (announcement.includes("null")) throw new Error("recovery announcement contains null");
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_processing_list_projection_fences_identity_and_stale_requests() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const processingListStatusNode"),
  script.indexOf("const initSummaryFormats"),
);
class FakeElement {
  constructor(kind, meetingId = "") {
    this.kind = kind;
    this.dataset = meetingId ? { meetingId } : {};
    this.isConnected = true;
    this.textContent = "";
    this.nodes = new Map();
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  contains(target) { return this.kind === "list" && rows.includes(target); }
  querySelector(selector) { return this.nodes.get(selector) || null; }
}
const list = new FakeElement("list");
const announcer = new FakeElement("announcer");
const rows = [];
const deferred = [];
const makeRow = (meetingId) => {
  const row = new FakeElement("row", meetingId);
  const status = new FakeElement("status");
  row.nodes.set("[data-processing-list-status]", status);
  row.nodes.set(".meeting-content-readiness", status);
  rows.push(row);
  return row;
};
const response = (projection) => ({ ok: true, json: async () => projection });
global.document = {
  querySelector(selector) {
    if (selector === "[data-meeting-list]") return list;
    if (selector === "[data-processing-list-announcer]") return announcer;
    return null;
  },
  createElement() { return new FakeElement("created"); },
};
global.fetch = (url) => new Promise((resolve) => deferred.push({ url, resolve }));
vm.runInThisContext(`
  let meetingListRequestGeneration = 0;
  const currentList = () => global.list;
  const processingListProjectionRequests = new Map();
  const processingListProjectionLastFetchedAt = new Map();
  const processingListProjectionStates = new Map();
  const processingTranscriptReady = () => false;
  const processingSummaryState = () => "processing";
  const processingSummaryPending = () => true;
  ${source}
  global.requestProcessingListProjection = requestProcessingListProjection;
  global.setMeetingListRequestGeneration = (value) => { meetingListRequestGeneration = value; };
`);
global.list = list;
(async () => {
  const rowA = makeRow("meeting-a");
  const rowB = makeRow("meeting-b");
  global.requestProcessingListProjection(rowA);
  global.requestProcessingListProjection(rowB);
  deferred.shift().resolve(response({ meeting_id: "meeting-a", retry_class: "retryable" }));
  deferred.shift().resolve(response({ meeting_id: "meeting-a", retry_class: "retryable" }));
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  if (rowA.querySelector("[data-processing-list-status]").textContent !== "Обработка временно приостановлена") {
    throw new Error("matching projection did not update its own row");
  }
  if (rowB.querySelector("[data-processing-list-status]").textContent) {
    throw new Error("projection for meeting-a updated meeting-b");
  }
  const detached = makeRow("meeting-detached");
  global.requestProcessingListProjection(detached);
  detached.isConnected = false;
  deferred.shift().resolve(response({ meeting_id: "meeting-detached", retry_class: "retryable" }));
  const stale = makeRow("meeting-stale");
  global.requestProcessingListProjection(stale);
  global.setMeetingListRequestGeneration(1);
  deferred.shift().resolve(response({ meeting_id: "meeting-stale", retry_class: "retryable" }));
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  if (detached.querySelector("[data-processing-list-status]").textContent) {
    throw new Error("detached row accepted a late projection");
  }
  if (stale.querySelector("[data-processing-list-status]").textContent) {
    throw new Error("old list generation accepted a late projection");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_processing_list_projection_only_polls_active_rows_and_refreshes_terminal_once() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const processingListStatusNode"),
  script.indexOf("const initSummaryFormats"),
);
let now = 100000;
const fetches = [];
const timers = [];
let refreshes = 0;
class FakeElement {
  constructor(kind, meetingId = "", statusKind = "") {
    this.kind = kind;
    this.dataset = meetingId ? { meetingId } : statusKind ? { statusKind } : {};
    this.isConnected = true;
    this.textContent = "";
    this.nodes = new Map();
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  append(node) { this.nodes.set("[data-processing-list-status]", node); }
  contains(target) { return this.kind === "list" ? rows.includes(target) : false; }
  querySelector(selector) { return this.nodes.get(selector) || null; }
}
const list = new FakeElement("list");
const announcer = new FakeElement("announcer");
const rows = [];
const makeRow = (meetingId, statusKind, withReadiness) => {
  const row = new FakeElement("row", meetingId);
  const status = new FakeElement("status", "", statusKind);
  row.nodes.set(".meeting-status[data-status-kind]", status);
  row.nodes.set(".meeting-content", new FakeElement("content"));
  if (withReadiness) {
    const readiness = new FakeElement("readiness");
    readiness.textContent = "Спикеры определяются · расшифровка готовится";
    row.nodes.set(".meeting-content-readiness", readiness);
    row.nodes.set("[data-processing-list-status]", readiness);
  }
  rows.push(row);
  return row;
};
const failedAbove = makeRow("failed-above", "failed", false);
const processing = makeRow("processing", "processing", true);
const failedBelow = makeRow("failed-below", "failed", false);
const projections = [
  { meeting_id: "processing", state: "polling", retry_class: "retryable" },
  { meeting_id: "processing", state: "processed", retry_class: "none" },
];
global.document = {
  activeElement: null,
  querySelector(selector) {
    if (selector === "[data-meeting-list]") return list;
    if (selector === "[data-processing-list-announcer]") return announcer;
    return null;
  },
  createElement() { return new FakeElement("created"); },
};
global.window = {
  clearTimeout() {},
  setTimeout(callback, delay) { timers.push({ callback, delay }); return timers.length; },
};
global.fetch = (url) => {
  fetches.push(url);
  const projection = projections.shift();
  return Promise.resolve({ ok: true, json: async () => projection });
};
Date.now = () => now;
vm.runInThisContext(`
  let meetingListRequestGeneration = 0;
  let processingListProjectionPollTimer = null;
  const currentList = () => global.list;
  const allRows = () => global.rows;
  const processingListProjectionRequests = new Map();
  const processingListProjectionLastFetchedAt = new Map();
  const processingListProjectionStates = new Map();
  const processingTranscriptReady = () => false;
  const processingSummaryState = () => "processing";
  const processingSummaryPending = () => true;
  const requestMeetingListRefresh = () => { refreshes += 1; return true; };
  ${source}
  global.initProcessingListProjection = initProcessingListProjection;
`);
global.list = list;
global.rows = rows;
(async () => {
  global.initProcessingListProjection();
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  if (fetches.length !== 1 || !fetches[0].endsWith("/processing/processing")) {
    throw new Error(`projection fetched non-active rows: ${fetches.join(",")}`);
  }
  if (timers.length !== 1 || timers[0].delay !== 15000) {
    throw new Error("active processing projection did not schedule one 15-second tick");
  }
  if (failedAbove.nodes.has("[data-processing-list-status]") || failedBelow.nodes.has("[data-processing-list-status]")) {
    throw new Error("failed neighbor received a processing status node");
  }
  processing.isConnected = false;
  const replacement = makeRow("processing", "processing", true);
  rows.splice(rows.indexOf(processing), 1);
  global.initProcessingListProjection();
  if (replacement.querySelector(".meeting-content-readiness").textContent !== "Обработка временно приостановлена") {
    throw new Error("progress swap reset the last processing projection");
  }
  if (fetches.length !== 1) throw new Error("projection snapshot bypassed the 15-second throttle");
  now += 15000;
  timers.shift().callback();
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  if (fetches.length !== 2) throw new Error("second active projection tick did not run");
  if (refreshes !== 1) throw new Error(`terminal transition requested ${refreshes} refreshes`);
  if (failedAbove.nodes.has("[data-processing-list-status]") || failedBelow.nodes.has("[data-processing-list-status]")) {
    throw new Error("terminal transition changed a failed neighbor");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_processing_detail_polling_stops_in_manual_pause_without_a_timer() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const scheduleProcessingRecoveryPolling"),
  script.indexOf("const renderProcessingProjection"),
);
const scheduled = [];
let processingRecoveryPollTimer = null;
const processingRecoveryActionRequest = null;
const stopProcessingRecoveryPolling = () => { processingRecoveryPollTimer = null; };
const processingTerminalFailure = () => false;
const processingSummaryState = (projection) => projection.summary_status;
const processingSummaryPending = (state) => state === "processing";
const processingServerSecondsRemaining = (projection) => projection.remaining ?? null;
const processingServerClockOffset = () => 0;
global.document = { hidden: false };
global.window = {
  setTimeout(_callback, delay) { scheduled.push(delay); return scheduled.length; },
};
const detail = { dataset: { processingStatusUrl: "/status" } };
vm.runInThisContext(`${source}; global.scheduleProcessingRecoveryPolling = scheduleProcessingRecoveryPolling;`);
global.scheduleProcessingRecoveryPolling(detail, {
  retry_class: "retryable",
  attempt_in_flight: false,
  next_attempt_at: null,
  summary_status: "unavailable",
});
if (scheduled.length !== 0) throw new Error("manual-only pause scheduled background polling");
global.scheduleProcessingRecoveryPolling(detail, {
  retry_class: "retryable",
  attempt_in_flight: false,
  next_attempt_at: "2026-01-01T00:00:00Z",
  remaining: 360,
  summary_status: "unavailable",
});
global.scheduleProcessingRecoveryPolling(detail, {
  retry_class: "none",
  attempt_in_flight: true,
  next_attempt_at: null,
  summary_status: "unavailable",
});
global.scheduleProcessingRecoveryPolling(detail, {
  retry_class: "none",
  attempt_in_flight: false,
  next_attempt_at: null,
  summary_status: "processing",
});
global.scheduleProcessingRecoveryPolling(detail, {
  retry_class: "retryable",
  attempt_in_flight: false,
  next_attempt_at: "2026-01-01T00:00:00Z",
  remaining: 0,
  summary_status: "unavailable",
});
    if (scheduled.join(",") !== "360000,15000,15000,1000") {
  throw new Error(`unexpected polling delays: ${scheduled.join(",")}`);
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_processing_status_retry_survives_transient_fetch_and_action_failures() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    script = script_path.read_text()
    manual_catch = script[
        script.index("signature: `manual-check-failed-${generation}`") :
        script.index("const runProcessingNewAttempt")
    ]
    new_attempt_catch = script[
        script.index("} catch (error) {", script.index("const runProcessingNewAttempt")) :
        script.index("const initProcessingRecovery")
    ]
    assert "scheduleProcessingStatusRetry(generation);" in manual_catch
    assert "scheduleProcessingStatusRetry(generation);" in new_attempt_catch
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const scheduleProcessingStatusRetry"),
  script.indexOf("const announceProcessingChange"),
);
const scheduled = [];
const refreshes = [];
let processingRecoveryPollTimer = null;
let processingRecoveryGeneration = 7;
let processingRecoveryActionRequest = null;
const stopProcessingRecoveryPolling = () => { processingRecoveryPollTimer = null; };
global.document = { hidden: false };
global.window = {
  setTimeout(callback, delay) { scheduled.push({ callback, delay }); return scheduled.length; },
};
global.refreshProcessingStatus = (options) => { refreshes.push(options); };
vm.runInThisContext(`${source}; global.scheduleProcessingStatusRetry = scheduleProcessingStatusRetry;`);
global.scheduleProcessingStatusRetry();
if (scheduled[0].delay !== 15000) throw new Error("status retry did not use bounded delay");
scheduled.shift().callback();
if (refreshes.length !== 1 || refreshes[0].force !== true || refreshes[0].generation !== 7) {
  throw new Error("status retry did not force the current generation");
}
processingRecoveryActionRequest = {};
global.scheduleProcessingStatusRetry(7, 1000);
scheduled.shift().callback();
if (refreshes.length !== 1) throw new Error("status retry raced an active action");
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_processing_detail_refreshes_content_once_when_artifacts_first_become_ready() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const refreshProcessingDetailContentOnce"),
  script.indexOf("const renderProcessingProjection"),
);
let fetchCount = 0;
let replaceCount = 0;
let initCount = 0;
let stopCount = 0;
let failNext = true;
let staleDetail = null;
const scheduled = [];
const nextDetail = { dataset: {} };
const detail = {
  dataset: {
    playbackPollUrl: "/meetings/meeting-1",
    meetingId: "meeting-1",
    mediaRevisionId: "revision-1",
    processingScheduleGeneration: "1",
    processingTranscriptContentReady: "false",
    processingSummaryContentReady: "false",
  },
  isConnected: true,
  replaceWith(node) {
    if (node !== nextDetail) throw new Error("unexpected detail fragment");
    replaceCount += 1;
    this.isConnected = false;
  },
};
const processingTranscriptReady = (projection) => projection.transcript_ready === true;
const processingSummaryState = (projection) => projection.summary_status;
const processingProjectionMatchesDetail = (node, projection) => (
  node.dataset.meetingId === projection.meeting_id
  && node.dataset.mediaRevisionId === projection.media_revision_id
);
const recoverMeetingDetailFromResponse = async () => false;
const stopProcessingRecoveryCountdown = () => { stopCount += 1; };
const stopProcessingRecoveryPolling = () => { stopCount += 1; };
const initCabinet = () => { initCount += 1; };
global.fetch = async () => {
  fetchCount += 1;
  if (failNext) {
    failNext = false;
    return { ok: false, text: async () => "" };
  }
  return {
    ok: true,
    text: async () => {
      if (staleDetail) processingRecoveryGeneration += 1;
      return "<main></main>";
    },
  };
};
global.DOMParser = class {
  parseFromString() { return { querySelector() { return nextDetail; } }; }
};
let processingRecoveryPollTimer = null;
let processingRecoveryGeneration = 0;
global.window = { setTimeout(callback) { scheduled.push(callback); } };
vm.runInThisContext(`${source}; global.refreshProcessingDetailContentOnce = refreshProcessingDetailContentOnce;`);
(async () => {
  const projection = {
    meeting_id: "meeting-1",
    media_revision_id: "revision-1",
    transcript_ready: true,
    summary_status: "available",
  };
  await global.refreshProcessingDetailContentOnce(detail, projection);
  if (
    fetchCount !== 1
    || detail.dataset.processingTranscriptContentReady !== "false"
    || detail.dataset.processingSummaryContentReady !== "false"
    || scheduled.length !== 1
  ) {
    throw new Error("failed refresh claim was not released");
  }
  scheduled.shift()();
  await new Promise((resolve) => setImmediate(resolve));
  scheduled.shift()();
  if (fetchCount !== 2 || replaceCount !== 1 || initCount !== 1 || stopCount !== 2) {
    throw new Error(`unexpected refresh counts: ${fetchCount}/${replaceCount}/${initCount}`);
  }
  if (nextDetail.dataset.processingTranscriptContentReady !== "true") {
    throw new Error("transcript refresh marker was not preserved");
  }
  if (nextDetail.dataset.processingSummaryContentReady !== "true") {
    throw new Error("summary refresh marker was not preserved");
  }
  await global.refreshProcessingDetailContentOnce(nextDetail, projection);
  if (fetchCount !== 2) throw new Error("ready content refreshed more than once");
  staleDetail = {
    dataset: {
      playbackPollUrl: "/meetings/meeting-1",
      meetingId: "meeting-1",
      mediaRevisionId: "revision-1",
      processingScheduleGeneration: "2",
      processingTranscriptContentReady: "false",
      processingSummaryContentReady: "false",
    },
    isConnected: true,
    replaceWith() { replaceCount += 1; },
  };
  await global.refreshProcessingDetailContentOnce(staleDetail, projection);
  if (
    replaceCount !== 1
    || stopCount !== 2
    || staleDetail.dataset.processingTranscriptContentReady !== "false"
    || staleDetail.dataset.processingSummaryContentReady !== "false"
  ) {
    throw new Error("stale fragment response mutated the current detail lifecycle");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_newer_processing_projection_supersedes_stale_fragment_refresh_claim() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const refreshProcessingDetailContentOnce"),
  script.indexOf("const renderProcessingProjection"),
);
let firstResolve;
let secondResolve;
let fetchCount = 0;
let replaceCount = 0;
const detail = {
  dataset: {
    playbackPollUrl: "/meetings/meeting-1",
    meetingId: "meeting-1",
    mediaRevisionId: "revision-1",
    processingScheduleGeneration: "1",
    processingTranscriptContentReady: "false",
    processingSummaryContentReady: "false",
  },
  isConnected: true,
  replaceWith() {
    replaceCount += 1;
    this.isConnected = false;
  },
};
const fragments = {
  first: { dataset: {} },
  second: { dataset: {} },
};
const processingTranscriptReady = (projection) => projection.transcript_ready === true;
const processingSummaryState = (projection) => projection.summary_status;
const processingProjectionMatchesDetail = (node, projection) => (
  node.dataset.meetingId === projection.meeting_id
  && node.dataset.mediaRevisionId === projection.media_revision_id
);
const recoverMeetingDetailFromResponse = async () => false;
const stopProcessingRecoveryCountdown = () => {};
const stopProcessingRecoveryPolling = () => {};
const initCabinet = () => {};
global.fetch = async () => {
  fetchCount += 1;
  const body = await new Promise((resolve) => {
    if (fetchCount === 1) firstResolve = resolve;
    else secondResolve = resolve;
  });
  return { ok: true, text: async () => body };
};
global.DOMParser = class {
  parseFromString(body) { return { querySelector() { return fragments[body]; } }; }
};
let processingRecoveryPollTimer = null;
let processingRecoveryGeneration = 0;
global.window = { setTimeout(callback) { callback(); } };
vm.runInThisContext(`${source}; global.refreshProcessingDetailContentOnce = refreshProcessingDetailContentOnce;`);
(async () => {
  const firstProjection = {
    meeting_id: "meeting-1",
    media_revision_id: "revision-1",
    updated_at: "2026-01-01T00:00:00Z",
    transcript_ready: true,
    summary_status: "processing",
  };
  const secondProjection = {
    ...firstProjection,
    updated_at: "2026-01-01T00:00:01Z",
    summary_status: "available",
  };
  const first = global.refreshProcessingDetailContentOnce(detail, firstProjection);
  await new Promise((resolve) => setImmediate(resolve));
  detail.dataset.processingScheduleGeneration = "2";
  const second = global.refreshProcessingDetailContentOnce(detail, secondProjection);
  await new Promise((resolve) => setImmediate(resolve));
  if (fetchCount !== 2) throw new Error("newer projection was blocked by stale refresh claim");
  firstResolve("first");
  await first;
  if (replaceCount !== 0 || !detail.dataset.processingContentRefreshClaim) {
    throw new Error("stale owner released the newer refresh claim");
  }
  secondResolve("second");
  await second;
  if (
    replaceCount !== 1
    || fragments.second.dataset.processingTranscriptContentReady !== "true"
    || fragments.second.dataset.processingSummaryContentReady !== "true"
  ) {
    throw new Error("newer fragment was not installed with ready content markers");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_processing_terminal_projections_never_fall_back_to_active_copy() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = script.slice(
  script.indexOf("const processingRecoveryCopy"),
  script.indexOf("const renderProcessingCountdown"),
);
const processingNewAttemptAllowed = (projection) => (
  projection?.retry_class === "terminal"
  && projection?.manual_action === "new_attempt"
  && projection?.attempt_in_flight !== true
);
vm.runInThisContext(`${source}; global.processingRecoveryCopy = processingRecoveryCopy;`);
const cases = [
  {
    projection: { state: "blocked", retry_class: "none", manual_action: "contact_support" },
    title: "Нужна помощь с обработкой",
    showRefresh: true,
  },
  {
    projection: { state: "canceled", retry_class: "none", manual_action: "none" },
    title: "Обработка отменена",
    showRefresh: false,
  },
  {
    projection: { state: "blocked", retry_class: "none", manual_action: "none" },
    title: "Обработка остановлена",
    showRefresh: true,
  },
  {
    projection: {
      state: "failed_terminal",
      retry_class: "terminal",
      manual_action: "new_attempt",
      reason_code: "blocked_free_processing_exhausted",
    },
    title: "Лимит расшифровки исчерпан",
    showRefresh: false,
    canStartNewAttempt: true,
  },
  {
    projection: {
      state: "failed_terminal",
      retry_class: "terminal",
      manual_action: "upload_another",
      reason_code: "storage_capacity_exceeded",
    },
    title: "Недостаточно места для аудио",
    showRefresh: false,
    uploadWithoutArchive: true,
  },
  {
    projection: {
      state: "failed_terminal",
      retry_class: "terminal",
      manual_action: "new_attempt",
      reason_code: "processing_retry_deadline_exceeded",
    },
    title: "Обработка завершилась без результата",
    showRefresh: true,
    canStartNewAttempt: true,
  },
];
for (const testCase of cases) {
  const copy = global.processingRecoveryCopy(testCase.projection, false);
  if (
    copy?.state !== "terminal"
    || copy?.title !== testCase.title
    || copy?.showRefresh !== testCase.showRefresh
    || copy?.uploadWithoutArchive !== testCase.uploadWithoutArchive
    || ("canStartNewAttempt" in testCase
      && copy?.canStartNewAttempt !== testCase.canStartNewAttempt)
  ) {
    throw new Error(`terminal projection used wrong copy: ${JSON.stringify({ copy, testCase })}`);
  }
  if (copy.copy.includes("Спикеры ещё определяются")) {
    throw new Error("terminal projection fell back to active processing copy");
  }
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    script = script_path.read_text(encoding="utf-8")
    assert 'payload?.code === "processing_quota_exceeded"' in script
    assert "Лимит расшифровки ещё не обновился" in script


def test_storage_failure_recovery_links_directly_to_no_archive_upload() -> None:
    template = (
        ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html"
    ).read_text()

    assert 'data-no-archive-href="{{ base_path }}?archive_audio=false#manual-upload"' in template
    assert 'href="/billing/storage" data-processing-manage-storage' not in template
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const source = [
  script.slice(
    script.indexOf("const processingRecoveryCopy"),
    script.indexOf("const renderProcessingCountdown"),
  ),
  script.slice(
    script.indexOf("const renderProcessingProjection"),
    script.indexOf("const focusProcessingRecovery"),
  ),
].join("\n");
const processingNewAttemptAllowed = () => false;
const processingProjectionMatchesDetail = () => true;
const processingProjectionIsStale = () => false;
const processingTimestamp = () => null;
const processingTranscriptReady = () => false;
const processingArtifactState = () => "unavailable";
const processingTerminalFailure = () => true;
const updateProcessingExportVisibility = () => {};
const updateProcessingStage = () => {};
const processingArtifactVisible = () => false;
const processingSummaryState = () => "unavailable";
const processingSummaryCopy = () => null;
const resetProcessingRecoveryCountdown = () => {};
const announceProcessingChange = () => {};
const scheduleProcessingRecoveryPolling = () => {};
let processingRecoveryActionRequest = null;
let processingRecoveryRequest = null;
const uploadAnother = {
  dataset: {
    defaultHref: "/meetings#manual-upload",
    noArchiveHref: "/meetings?archive_audio=false#manual-upload",
  },
  hidden: true,
  href: "",
  textContent: "",
};
const recovery = {
  dataset: {},
  hidden: true,
  setAttribute() {},
  querySelector(selector) {
    return selector === "[data-processing-upload-another]" ? uploadAnother : null;
  },
};
const detail = {
  dataset: { storedOutcomesAvailable: "false" },
  querySelector(selector) {
    return selector === "[data-processing-recovery]" ? recovery : null;
  },
};
vm.runInThisContext(`${source}; global.renderProcessingProjection = renderProcessingProjection;`);
global.renderProcessingProjection(detail, {
  state: "failed_terminal",
  retry_class: "terminal",
  manual_action: "upload_another",
  reason_code: "storage_capacity_exceeded",
});
if (
  uploadAnother.hidden
  || uploadAnother.href !== uploadAnother.dataset.noArchiveHref
  || uploadAnother.textContent !== "Загрузить без сохранения аудио"
) throw new Error("storage recovery action is not the no-archive upload");
global.renderProcessingProjection(detail, {
  state: "failed_terminal",
  retry_class: "terminal",
  manual_action: "upload_another",
  reason_code: "corrupt_source",
});
if (
  uploadAnother.hidden
  || uploadAnother.href !== uploadAnother.dataset.defaultHref
  || uploadAnother.textContent !== "Загрузить другой файл"
) throw new Error("upload recovery action did not return to its default state");
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(STATIC_DIR / "cabinet.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_cabinet_rail_initial_state_uses_surface_breakpoints() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    css = (STATIC_DIR / "cabinet.css").read_text()
    for marker in [
        "const expandedMedia = window.matchMedia(",
        '"(min-width: 1121px)" : "(min-width: 981px)"',
    ]:
        assert marker in script
    assert "@media (max-width: 1120px)" in css

    rail_source = script[
        script.index("const initCabinetRail") : script.index("const initCabinetProfileMenus")
    ]
    assert 'window.addEventListener("resize"' not in rail_source
    assert rail_source.count('toggle.addEventListener("click"') == 1


def test_cabinet_rail_ready_state_geometry() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    collapsed_selector = (
        'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.is-rail-pinned) {'
    )
    expanded_selector = (
        'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell].is-rail-pinned {'
    )
    assert (
        f"{collapsed_selector}\n  grid-template-columns: var(--app-rail-width) minmax(0, 1fr);"
        in css
    )
    assert (
        f"{expanded_selector}\n  grid-template-columns: var(--app-sidebar-width) minmax(0, 1fr);"
        in css
    )
    assert f"{collapsed_selector}\n  --playback-inline-start: var(--app-rail-width);\n  grid-template-columns: var(--app-rail-width) minmax(0, 1fr);" in css
    assert f"{expanded_selector}\n  --playback-inline-start: var(--app-sidebar-width);\n  grid-template-columns: var(--app-sidebar-width) minmax(0, 1fr);" in css


def test_cabinet_collapsed_rail_uses_one_centered_control_geometry() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    collapsed_start = css.index(
        'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.is-rail-pinned) .sidebar {'
    )
    collapsed_end = css.index("\n.sidebar-download {", collapsed_start)
    collapsed_css = css[collapsed_start:collapsed_end]

    collapsed_root = (
        'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.is-rail-pinned)'
    )
    assert (
        f"{collapsed_root} .cabinet-rail-toggle,\n"
        f"{collapsed_root} .cabinet-sidebar-nav__item,\n"
        f"{collapsed_root} .sidebar-app-update,\n"
        f"{collapsed_root} .sidebar-download,\n"
        f"{collapsed_root} .sidebar-profile__trigger {{\n"
        "  width: 40px;\n"
        "  height: 40px;\n"
        "  min-width: 40px;\n"
        "  min-height: 40px;\n"
        "  margin-inline: auto;\n"
        "  padding: 0;\n"
        "}"
    ) in collapsed_css
    assert (
        f"{collapsed_root} .sidebar-foot {{\n"
        "  display: grid;\n"
        "  width: 52px;\n"
        "  opacity: 1;\n"
        "  pointer-events: auto;\n"
        "  visibility: visible;\n"
        "}"
    ) in collapsed_css
    assert f"{collapsed_root} .sidebar-app-update__label," in collapsed_css
    assert f"{collapsed_root} .cabinet-sidebar-nav {{\n  gap: 4px;\n}}" in collapsed_css

    assert (
        ".app-shell[data-cabinet-shell] .cabinet-rail-toggle {\n"
        "  position: relative;\n"
        "  display: grid;\n"
        "  width: 40px;\n"
        "  height: 40px;\n"
        "  min-width: 40px;\n"
        "  min-height: 40px;\n"
        "  margin-inline: 2px auto;\n"
        "  inset-block-start: -4px;"
    ) in css
    assert (".sidebar {\n  padding: 12px 10px;\n  gap: 12px;") in css
    assert (
        ".app-shell.desktop-embedded.is-rail-pinned .cabinet-rail-toggle {\n"
        "    margin-inline-start: 6px;\n"
        "    inset-block-start: 0;"
    ) in css


def test_cabinet_playback_shares_ready_state_geometry() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    collapsed_selector = 'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.is-rail-pinned) {'
    expanded_selector = 'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell].is-rail-pinned {'
    assert f"{collapsed_selector}\n  --playback-inline-start: var(--app-rail-width);" in css
    assert f"{expanded_selector}\n  --playback-inline-start: var(--app-sidebar-width);" in css
    assert "left: var(--playback-inline-start);" in css
    assert (
        'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell] .sidebar {\n'
        "    z-index: 31;\n"
        "    display: flex;\n"
        "  }"
    ) in css


def test_cabinet_rail_node_harness_keeps_responsive_defaults_and_manual_state() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const surface = process.argv[2];
const width = Number(process.argv[3]);
const explicitPinned = process.argv[4] === "pinned";
const embedded = surface === "embedded";
const documentListeners = new Map();
const windowListeners = new Map();
class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.style = {};
    this.attributes = {};
    this.hidden = false;
    this.disabled = false;
    this.isConnected = true;
    this.listeners = new Map();
    this.classList = {
      values: new Set(),
      add: (...names) => names.forEach((name) => this.classList.values.add(name)),
      remove: (...names) => names.forEach((name) => this.classList.values.delete(name)),
      toggle: (name, force) => {
        const next = force === undefined ? !this.classList.values.has(name) : force;
        if (next) this.classList.values.add(name); else this.classList.values.delete(name);
        return next;
      },
      contains: (name) => this.classList.values.has(name),
    };
  }
  addEventListener(name, handler) {
    const handlers = this.listeners.get(name) || [];
    handlers.push(handler);
    this.listeners.set(name, handlers);
  }
  dispatch(name, event = {}) {
    for (const handler of this.listeners.get(name) || []) handler(event);
  }
  listenerCount(name) { return (this.listeners.get(name) || []).length; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  querySelector(selector) {
    if (this === shell && selector === "[data-cabinet-navigation]") return sidebar;
    if (this === shell && selector === "[data-cabinet-rail-toggle]") return toggle;
    return null;
  }
  querySelectorAll(selector) {
    if (this === sidebar && selector === "a[href]") return [navLink];
    return [];
  }
  matches() { return false; }
  closest() { return null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] || null; }
  removeAttribute(name) { delete this.attributes[name]; }
  focus() { this.focused = true; document.activeElement = this; }
}
const shell = new FakeElement("div");
const sidebar = new FakeElement("aside");
const toggle = new FakeElement("button");
const navLink = new FakeElement("a");
const content = new FakeElement("main");
if (embedded) shell.classList.add("desktop-embedded");
if (explicitPinned) shell.classList.add("is-rail-pinned");
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
const body = new FakeElement("body");
global.document = {
  activeElement: null,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener(name, handler) {
    const handlers = documentListeners.get(name) || [];
    handlers.push(handler);
    documentListeners.set(name, handlers);
  },
  removeEventListener(name, handler) {
    documentListeners.set(name, (documentListeners.get(name) || []).filter((candidate) => candidate !== handler));
  },
  querySelector(selector) {
    if (selector === 'meta[name="csrf-token"]') return null;
    return null;
  },
  querySelectorAll(selector) {
    return selector === "[data-cabinet-shell]" ? [shell] : [];
  },
  createElement(tag) { return new FakeElement(tag); },
};
global.location = { pathname: "/meetings", search: "", hash: "", href: "https://graf.test/meetings" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {}, getItem() { return null; }, setItem() {} };
global.fetch = async () => ({ status: 200, ok: true, redirected: false, headers: { get() { return ""; } } });
global.window = {
  innerWidth: width,
  addEventListener(name, handler) {
    const handlers = windowListeners.get(name) || [];
    handlers.push(handler);
    windowListeners.set(name, handlers);
  },
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia(query) {
    const breakpoint = embedded ? 1121 : 981;
    const matches = query === `(min-width: ${breakpoint}px)` && width >= breakpoint;
    return { matches, addEventListener() {} };
  },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const expectedPinned = explicitPinned || width >= (embedded ? 1121 : 981);
if (shell.classList.contains("is-rail-pinned") !== expectedPinned) {
  throw new Error(`wrong initial class for ${surface} ${width}`);
}
const expectedExpanded = expectedPinned ? "true" : "false";
const expectedLabel = expectedPinned ? "Скрыть боковую панель" : "Показать боковую панель";
if (toggle.attributes["aria-expanded"] !== expectedExpanded) throw new Error("wrong initial aria state");
if (toggle.attributes["aria-label"] !== expectedLabel) throw new Error("wrong initial action label");
toggle.dispatch("click");
toggle.dispatch("click");
if (!toggle.focused) throw new Error("toggle did not retain focus");
if (shell.classList.contains("is-rail-pinned") !== expectedPinned) throw new Error("two toggles changed final state");
navLink.dispatch("click");
if (shell.classList.contains("is-rail-pinned") !== expectedPinned) throw new Error("navigation click changed manual state");
for (const handler of documentListeners.get("click") || []) handler({ target: content });
if (shell.classList.contains("is-rail-pinned") !== expectedPinned) throw new Error("content click changed manual state");
const resizeHandlers = windowListeners.get("resize") || [];
for (const handler of resizeHandlers) handler();
if (shell.classList.contains("is-rail-pinned") !== expectedPinned) throw new Error("resize changed manual state");
if ((toggle.listeners.get("click") || []).length !== 1) throw new Error("duplicate rail listener");
"""
    cases = [
        ("browser", 1280, "default"),
        ("browser", 981, "default"),
        ("browser", 980, "default"),
        ("embedded", 1121, "default"),
        ("embedded", 1120, "default"),
        ("embedded", 1120, "pinned"),
        ("embedded", 720, "default"),
    ]
    for surface, width, pin_state in cases:
        completed = subprocess.run(
            ["node", "-e", harness, str(script_path), surface, str(width), pin_state],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr + completed.stdout


def test_meeting_review_resize_uses_bounded_keyboard_and_pointer_contract() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in [
        "data-speaker-timeline-shell",
        "data-speaker-timeline-resize",
        "speakerTimelineCount",
        "pointerdown",
        "pointermove",
        "pointerup",
        "ArrowUp",
        "ArrowDown",
        "aria-valuemin",
        "aria-valuemax",
        "aria-valuenow",
        "scrollHeight",
        "measureNaturalHeight",
        "DEFAULT_TIMELINE_HEIGHT",
        "const DEFAULT_TIMELINE_HEIGHT = 120",
    ]:
        assert marker in script
    for marker in [
        ".speaker-timeline-shell",
        ".speaker-timeline-resize",
        "cursor: ns-resize",
        ".speaker-timeline-resize:focus-visible",
        ".speaker-timeline-resize.is-dragging",
        "height: auto",
        "max-height: 120px",
    ]:
        assert marker in css


def test_meeting_review_resize_node_harness_keeps_bounds_and_one_listener() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const scenario = process.argv[2];
const listeners = new Map();
const windowListeners = new Map();
class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.style = {};
    this.attributes = {};
    this.hidden = false;
    this.isConnected = true;
    this.listeners = new Map();
    this.classList = {
      values: new Set(),
      add: (...names) => names.forEach((name) => this.classList.values.add(name)),
      remove: (...names) => names.forEach((name) => this.classList.values.delete(name)),
      toggle: (name, force) => {
        const next = force === undefined ? !this.classList.values.has(name) : force;
        if (next) this.classList.values.add(name); else this.classList.values.delete(name);
        return next;
      },
      contains: (name) => this.classList.values.has(name),
    };
  }
  addEventListener(name, handler) {
    const handlers = this.listeners.get(name) || [];
    handlers.push(handler);
    this.listeners.set(name, handlers);
  }
  dispatch(name, event = {}) {
    for (const handler of this.listeners.get(name) || []) handler(event);
  }
  listenerCount(name) { return (this.listeners.get(name) || []).length; }
  append(...nodes) { this.children.push(...nodes); }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  closest(selector) { return selector === "[data-playback-shell]" ? playback : null; }
  getBoundingClientRect() { return { top: Number(process.argv[3] || 500) }; }
  setPointerCapture() {}
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] || null; }
  removeAttribute(name) { delete this.attributes[name]; }
  focus() { this.focused = true; }
}
const playback = new FakeElement("section");
const shell = new FakeElement("div");
const timeline = new FakeElement("div");
const handle = new FakeElement("div");
timeline.dataset.speakerTimelineDefaultHeight = "120";
const speakerCount = scenario === "one" ? 1 : scenario === "two" ? 2 : scenario === "fit" ? 3 : 12;
timeline.dataset.speakerTimelineCount = String(speakerCount);
timeline.scrollHeight = scenario === "one" ? 28 : scenario === "two" ? 56 : scenario === "fit" ? 80 : scenario === "viewport" ? 900 : 320;
shell.querySelector = (selector) => {
  if (selector === "[data-speaker-timeline]") return timeline;
  if (selector === "[data-speaker-timeline-resize]") return handle;
  return null;
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
const body = new FakeElement("body");
global.document = {
  activeElement: null,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener(name, handler) {
    const handlers = listeners.get(name) || [];
    handlers.push(handler);
    listeners.set(name, handlers);
  },
  removeEventListener(name, handler) {
    listeners.set(name, (listeners.get(name) || []).filter((candidate) => candidate !== handler));
  },
  dispatch(name, event = {}) {
    for (const handler of listeners.get(name) || []) handler(event);
  },
  querySelector(selector) {
    if (selector === "meta[name='csrf-token']") return null;
    return null;
  },
  querySelectorAll(selector) {
    return selector === "[data-speaker-timeline-shell]" ? [shell] : [];
  },
  createElement(tag) { return new FakeElement(tag); },
};
global.location = { pathname: "/meetings", search: "", hash: "", href: "https://graf.test/meetings" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.fetch = async () => ({ status: 200, ok: true, redirected: false, headers: { get() { return ""; } } });
global.window = {
  addEventListener(name, handler) {
    const handlers = windowListeners.get(name) || [];
    handlers.push(handler);
    windowListeners.set(name, handlers);
  },
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const resizeHandlerCount = handle.listenerCount("keydown");
if (resizeHandlerCount !== 1) throw new Error(`expected one key handler, got ${resizeHandlerCount}`);
if ((windowListeners.get("resize") || []).length !== 1) throw new Error("expected one page resize listener");
const currentTime = 42;
playback.currentTime = currentTime;
if (["one", "two", "fit"].includes(scenario)) {
  if (!handle.hidden) throw new Error("fit rows exposed a resize affordance");
  if (timeline.style.height !== "") throw new Error("natural rows received a fixed height");
  const expectedNaturalHeight = scenario === "one" ? 28 : scenario === "two" ? 56 : 80;
  if (handle.attributes["aria-valuemin"] !== String(expectedNaturalHeight)) throw new Error("wrong natural minimum");
} else {
  if (handle.hidden) throw new Error("overflow rows hid the resize affordance");
  handle.dispatch("pointerdown", { button: 0, pointerId: 1, clientY: 100, preventDefault() {} });
  document.dispatch("pointermove", { pointerId: 1, clientY: 70 });
  document.dispatch("pointerup", { pointerId: 1 });
  if (timeline.style.height !== "150px") throw new Error("pointer resize did not move the bounded panel");
  handle.dispatch("keydown", { key: "End", preventDefault() {} });
  const expectedMax = scenario === "viewport" ? 228 : 320;
  if (handle.attributes["aria-valuemax"] !== String(expectedMax)) throw new Error("wrong resize ceiling");
  if (timeline.style.height !== `${expectedMax}px`) throw new Error("End did not use bounded height");
  handle.dispatch("keydown", { key: "Home", preventDefault() {} });
  if (timeline.style.height !== "") throw new Error("Home did not restore the default height");
}
body.dispatch("htmx:afterSwap", { detail: { target: null } });
if (handle.listenerCount("keydown") !== 1) throw new Error("partial update duplicated resize listeners");
if ((windowListeners.get("resize") || []).length !== 1) throw new Error("partial update duplicated page resize listeners");
if (playback.currentTime !== currentTime) throw new Error("resize changed playback position");
"""
    for scenario, top in [
        ("one", 500),
        ("two", 500),
        ("fit", 500),
        ("overflow", 500),
        ("viewport", 120),
    ]:
        completed = subprocess.run(
            ["node", "-e", harness, str(script_path), scenario, str(top)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr


def test_speaker_rename_node_harness_preserves_playback_states() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const playing = process.argv[2] === "playing";
const success = process.argv[3] === "success";
let submitHandler = null;
let reloadCount = 0;
class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.hidden = false;
    this.disabled = false;
    this.isConnected = true;
    this.listeners = new Map();
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener(name, handler) {
    if (this === form && name === "submit") submitHandler = handler;
    const handlers = this.listeners.get(name) || [];
    handlers.push(handler);
    this.listeners.set(name, handlers);
  }
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
  contains() { return false; }
  focus() { this.focused = true; }
  matches() { return false; }
  querySelector(selector) {
    if (this !== form) return null;
    if (selector === "[data-speaker-name-error]") return error;
    if (selector === "button[type='submit']") return submit;
    if (selector === "input[name='display_name']") return input;
    return null;
  }
  querySelectorAll() { return []; }
  setAttribute(name, value) { this[name] = String(value); }
}
const detail = new FakeElement("main");
const player = new FakeElement("audio");
player.currentTime = 37.5;
player.paused = !playing;
player.src = "/private-audio.m4a";
const error = new FakeElement("span");
error.hidden = true;
const submit = new FakeElement("button");
const input = new FakeElement("input");
input.value = "Мария";
const form = new FakeElement("form");
form.dataset.speakerKey = "speaker_00";
form.id = "speaker-name-form-speaker_00";
form.action = "/meetings/private-id/speakers/speaker_00";
const body = new FakeElement("body");
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.FormData = class {};
global.document = {
  activeElement: form,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  title: "PRIVATE MEETING - GRAF",
  addEventListener() {},
  createElement(tag) { return new FakeElement(tag); },
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "meta[name='csrf-token']") return null;
    if (selector === "[data-playback-player]") return player;
    return null;
  },
  querySelectorAll(selector) {
    if (selector === "[data-speaker-name-form]") return [form];
    return [];
  },
};
global.location = {
  pathname: "/meetings/private-id",
  search: "",
  hash: "",
  href: "https://graf.test/meetings/private-id",
  reload() { reloadCount += 1; },
  replace() {},
};
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.fetch = async () => ({
  status: success ? 200 : 422,
  ok: success,
  redirected: false,
  headers: { get() { return ""; } },
  text: async () => "",
});
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
(async () => {
  vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
  if (!submitHandler) throw new Error("speaker submit handler was not installed");
  const originalPlayer = player;
  const originalTime = player.currentTime;
  const originalPaused = player.paused;
  await submitHandler({ preventDefault() {} });
  if (player !== originalPlayer || player.currentTime !== originalTime || player.paused !== originalPaused) {
    throw new Error("speaker rename changed playback state");
  }
  if (reloadCount !== 0) throw new Error("speaker rename reloaded the page");
  if (success && error.hidden !== true) throw new Error("successful rename left an error visible");
  if (!success && (error.hidden || submit.disabled)) throw new Error("failed rename did not leave a retryable error");
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    for playing in ("playing", "paused"):
        for result in ("success", "failure"):
            completed = subprocess.run(
                ["node", "-e", harness, str(script_path), playing, result],
                capture_output=True,
                text=True,
                check=False,
            )
            assert completed.returncode == 0, completed.stderr


def test_speaker_rename_success_updates_labels_without_reload() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    rename_handler = script[
        script.index("const initSpeakerNameForms") : script.index("const initContentExport")
    ]

    assert "data-speaker-key" in rename_handler
    assert "DOMParser" in rename_handler
    assert "replaceSpeakerNameInPlace" in rename_handler
    assert "window.location.reload()" not in rename_handler
    assert "data-speaker-name-error" in rename_handler


def test_meeting_list_js_separates_open_selection_and_fragment_reconciliation() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for marker in [
        "const selectedMeetingIds = new Set()",
        "const selectableRows = ()",
        'row.querySelector("[data-meeting-open]")',
        "primaryLink?.click()",
        'event.target.closest("a,button,input,.row-select-hit")',
        "rowPrimaryFocusTarget",
        "Выбрано: ${rows.length}",
        "reconcileMeetingSelection",
        "selectedMeetingIds.has(row.dataset.meetingId)",
    ]:
        assert marker in script

    assert "checkbox.checked = !checkbox.checked;\n      updateSelection();\n    });" not in script


def test_meeting_list_js_owns_loading_and_metadata_safe_recovery_states() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for marker in [
        '"htmx:beforeRequest"',
        '"htmx:beforeSwap"',
        '"htmx:sendError"',
        '"htmx:timeout"',
        '"htmx:responseError"',
        "showMeetingListLoading",
        "renderMeetingListRecovery",
        "observeDetachedMeetingListRequest",
        "observedDetachedMeetingListRequests",
        "handledMeetingListAuthorizationRequests",
        "meetingListRequestGeneration += 1",
        "clearMeetingListAnnouncements",
        "current.replaceChildren(recovery)",
        "navigator.onLine",
        "status === 401",
        "status === 403",
        'getResponseHeader?.("X-GRAF-Cabinet-Recovery")',
        'recoveryHeader === "reselect-space"',
        'problemCode === "auth_session_invalid"',
        "accessLossProblemCodes.has(problemCode)",
        "unknownForbiddenMeansAccess",
        "status >= 400 && status < 500",
        'target?.removeAttribute("aria-busy")',
        "current.hidden = false",
        "data-list-retry",
        "data-list-sign-in",
        "Нет подключения",
        "Запись на Mac продолжает работать.",
        "Не удалось загрузить встречи",
        "Попробуйте ещё раз.",
        "Нужно войти снова",
        "Сессия завершилась.",
        "Нужно выбрать пространство",
        "Доступ к выбранному пространству больше не подтверждён.",
        "Войти и выбрать пространство",
        "Нет доступа к встречам",
        "Обратитесь к владельцу рабочего пространства.",
        "Повторить",
        "Войти",
        'history.replaceState(null, "", neutralPath)',
        "window.location.replace(neutralPath)",
    ]:
        assert marker in script

    meeting_list_template = (
        ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_list.html"
    ).read_text()
    rendering = (ROOT / "src/twobrain_rec_server/cabinet/rendering.py").read_text()
    assert "data-list-loading-state" in rendering
    assert "Загружаем встречи…" in rendering
    assert 'id="meeting-list-region"' in meeting_list_template

    recovery_function = script[
        script.index("const renderMeetingListRecovery") : script.index(
            "const showMeetingListLoading"
        )
    ]
    assert "innerHTML =" not in recovery_function
    assert 'target.querySelector("[data-list-loading-state]")' in recovery_function
    assert 'target.querySelector("[data-list-current-content]")' in recovery_function
    assert "target.replaceChildren(loading, current)" in recovery_function
    assert "loading.hidden = true" in recovery_function
    assert "current.hidden = false" in recovery_function
    assert "} else {\n      clearMeetingListAnnouncements();\n    }" in recovery_function

    announcement_clear = script[
        script.index("const clearMeetingListAnnouncements") : script.index(
            "const listInteractionIsActive"
        )
    ]
    assert "meetingResultCountAnnouncementVersion += 1" in announcement_clear
    assert (
        'document.querySelector("[data-upload-progress-announcer]")?.replaceChildren()'
        in announcement_clear
    )
    assert (
        'document.querySelector("[data-upload-activity-announcer]")?.replaceChildren()'
        in announcement_clear
    )
    assert (
        'document.querySelector("[data-meeting-result-announcer]")?.replaceChildren()'
        in announcement_clear
    )
    assert "announcedUploadProgressBuckets.clear()" in announcement_clear

    interaction_guard = script[
        script.index("const listInteractionIsActive") : script.index("const isUsableFocusTarget")
    ]
    assert "[data-delete-dialog][open]" in interaction_guard
    assert 'matches(":hover")' not in interaction_guard
    assert "document.activeElement" not in interaction_guard
    assert "selectedRows()" not in interaction_guard


def test_meeting_list_js_closes_authorization_retry_and_deletion_boundaries() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for marker in [
        '"auth_session_invalid"',
        '"device_untrusted"',
        'problemCode === "workspace_scope_denied"',
        'location.pathname.startsWith("/desktop/")',
        "meetingListRequestFocusRecoveries",
        'kind: "retry"',
        "retryLoadingOwnsFocus",
        "loading.focus({ preventScroll: true })",
        'recovery.querySelector("[data-list-retry], [data-list-sign-in]")',
        'document.querySelector("[data-list-title]")?.focus({ preventScroll: true })',
        "scrubManualUploadPrivateState",
        "scrubManualUploadPrivateState({ authorizationLost: true })",
        "deleteDialogWasOpen",
        "closeDeleteDialog({ restoreFocus: false })",
        'dialog.dataset.uploadAvailable = "false"',
        "trigger.disabled = true",
        'dialog.dataset.uploadAvailable === "true"',
        'if (titleInput) titleInput.value = ""',
        "closeDialog({ restoreFocus: false })",
        "publishDeletionFeedback",
        "announceDeletionResult",
        "Запись удалена из списка.",
        "Не удалось удалить ${failures}",
        "listRefreshFocusMeetingIds",
        "listRefreshFocusOrigin",
        "restoreListRefreshFocus",
        "restoreMeetingListRequestFocus(requestEvent, recovery, { force: authorizationLost })",
        "restoreListRefreshFocus(recovery, { force: authorizationLost })",
        ".map((meetingId) => allRows().find((row) => row.dataset.meetingId === meetingId))",
        ".find(Boolean)",
        "xhrProblemCode",
        'JSON.parse(xhr?.responseText || "{}")',
        "[403, 404].includes(response.status)",
        'response.status === 404 && problemCode === "meeting_not_found"',
        'deletionResult === "missing"',
        'row.removeAttribute("data-meeting-id")',
        "missingCount += 1",
    ]:
        assert marker in script

    upload_scrub = script[
        script.index("scrubManualUploadPrivateState =") : script.index(
            'dialog.addEventListener("keydown", (event) => trapModalFocus(dialog, event))',
            script.index("scrubManualUploadPrivateState ="),
        )
    ]
    assert 'if (authorizationLost) dialog.dataset.uploadAvailable = "false"' in upload_scrub
    assert "scrubUploadActivities();" in upload_scrub
    assert "trigger.disabled = true" in upload_scrub

    session_scrub = script[
        script.index("const scrubSessionMeetingMetadata") : script.index(
            "const renderMeetingListRecovery"
        )
    ]
    for marker in [
        'document.querySelector("[data-delete-dialog]")?.hasAttribute("open")',
        "pendingDeleteRows.length",
        "deleteReturnFocus",
        "deleteReturnMeetingId",
        "deleteFocusFallbackIds.length",
        "closeDeleteDialog({ restoreFocus: false })",
        "return manualUploadWasOpen || deleteDialogWasOpen",
    ]:
        assert marker in session_scrub

    upload_readiness = script[
        script.index("const syncReady =") : script.index("const ensureLocalId =")
    ]
    assert 'dialog.dataset.uploadAvailable === "true"' in upload_readiness

    assert "const refreshFocusMeetingId = deleteFocusFallbackIds[0]" not in script


def test_meeting_list_js_announces_polled_progress_in_bounded_steps() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    template = (
        ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html"
    ).read_text()

    for marker in [
        "announcedUploadProgressBuckets",
        "announcedUploadProgressMetadata",
        "uploadProgressTrackingTtlMs",
        "uploadProgressTrackingPruneTimer",
        "pruneUploadProgressTracking",
        "scheduleUploadProgressTrackingPrune",
        "rememberUploadProgressMetadata",
        "announceUploadProgress",
        "data-upload-progress-active][data-upload-progress-percent",
        'compactStatus?.dataset.statusKind === "uploading"',
        "Number.isFinite(previousState?.bucket)",
        "announcedUploadProgressBuckets.set(meetingId, { bucket: null })",
        "Math.floor(Math.max(0, Math.min(99, percent)) / 10) * 10",
        'row?.querySelector(".meeting-status[data-status-kind]")',
        'status?.dataset.statusKind === "uploading"',
        "rowsByMeetingId.get(meetingId)",
        "Отправка завершена",
        'messages.join(". ")',
    ]:
        assert marker in script
    assert 'data-upload-progress-announcer role="status" aria-live="polite"' in template
    assert 'data-meeting-result-announcer role="status" aria-live="polite"' in template
    assert 'aria-atomic="true"' in template
    assert "meetingResultCountShouldAnnounce" in script
    assert "meetingResultCountHadRefinement" in script
    assert "announceMeetingResultCount" in script
    assert '?.dataset.meetingResultComplete === "true"' in script
    assert (
        'resultIsComplete\n        ? "Показаны все встречи"\n'
        '        : "Показана первая часть встреч без поиска и фильтров"' in script
    )
    assert 'const message = count || "Показаны все встречи"' not in script
    assert "if (!announcer || !count) return" not in script
    assert "beginAuthoritativeMeetingListRequest(event)" in script
    assert "finishAuthoritativeMeetingListRequest" in script
    assert "rememberProgressPollGeneration(event)" in script
    assert "progressPollIsStale(event)" in script
    assert "authoritativeMeetingListRequestIsStale(event)" in script
    assert "meetingListRequestGeneration" in script
    assert "activeMeetingListRequests" in script
    assert "requestIsMeetingListProgressPoll(event)" in script
    assert "event.detail?.requestConfig?.elt" in script
    delayed_poll_guard = script[
        script.index('document.body.addEventListener("htmx:beforeSwap"') : script.index(
            'document.body.addEventListener("htmx:sendError"'
        )
    ]
    assert "requestIsMeetingListProgressPoll(event)" in delayed_poll_guard
    assert "progressPollIsStale(event)" in delayed_poll_guard
    assert "listInteractionIsActive()" in delayed_poll_guard
    assert "event.preventDefault()" in delayed_poll_guard
    assert "if (event.detail) event.detail.shouldSwap = false" in delayed_poll_guard
    assert 'document.querySelector("[data-meeting-result-count]")' in script


def test_meeting_list_runtime_announces_completion_when_upload_row_leaves_filter() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const script = fs.readFileSync(process.argv[1], "utf8");
const uploadProgressTrackingTtlMs = 5 * 60 * 1000;
let uploadProgressTrackingPruneTimer = null;
let scheduledPruneCallback = null;
let nextTimerId = 0;
globalThis.setTimeout = (callback) => {
  scheduledPruneCallback = callback;
  nextTimerId += 1;
  return nextTimerId;
};
globalThis.clearTimeout = () => {};
const announceSource = [
  script.slice(
    script.indexOf("const pruneUploadProgressTracking"),
    script.indexOf("const announceUploadProgress"),
  ),
  script.slice(
    script.indexOf("const announceUploadProgress"),
    script.indexOf("const announceMeetingResultCount"),
  ),
].join("\n");
const announcedUploadProgressBuckets = new Map();
const announcedUploadProgressMetadata = new Map();
let rows = [];
const announcer = { textContent: "" };
const document = global.document = {
  querySelector(selector) {
    return selector === "[data-upload-progress-announcer]" ? announcer : null;
  },
};
const allRows = () => rows;
eval(`${announceSource}\n;global.announceUploadProgress = announceUploadProgress;`);
class FakeElement {
  constructor(kind, textContent = "") {
    this.kind = kind;
    this.textContent = textContent;
    this.dataset = {};
    this.nodes = new Map();
  }
  querySelector(selector) { return this.nodes.get(selector) || null; }
}
const row = new FakeElement("row");
row.dataset.meetingId = "upload-meeting";
const title = new FakeElement("title", "Приватная встреча");
const progress = new FakeElement("progress", "Загрузка 10%");
progress.dataset.uploadProgressPercent = "10";
const compactStatus = new FakeElement("status", "Обрабатывается");
compactStatus.dataset.statusKind = "uploading";
row.nodes.set(".row-title", title);
row.nodes.set("[data-upload-progress-active][data-upload-progress-percent]", progress);
row.nodes.set(".meeting-status[data-status-kind]", compactStatus);
rows = [row];
announceUploadProgress();
if (typeof scheduledPruneCallback !== "function") {
  throw new Error("upload progress cleanup timer was not scheduled");
}
if (announcer.textContent) throw new Error("initial upload progress announced unexpectedly");
progress.dataset.uploadProgressPercent = "20";
progress.textContent = "Загрузка 20%";
announceUploadProgress();
if (announcer.textContent !== "Приватная встреча: Загрузка 20%") {
  throw new Error(`progress bucket announcement was lost: ${announcer.textContent}`);
}
rows = [];
announceUploadProgress();
if (announcer.textContent) {
  throw new Error(`filtered upload was announced without terminal evidence: ${announcer.textContent}`);
}
progress.dataset.uploadProgressPercent = "";
row.nodes.delete("[data-upload-progress-active][data-upload-progress-percent]");
compactStatus.dataset.statusKind = "ready";
compactStatus.textContent = "Аудио готово";
rows = [row];
announceUploadProgress();
if (announcer.textContent !== "Приватная встреча: Аудио готово") {
  throw new Error(`completion announcement was lost after terminal row returned: ${announcer.textContent}`);
}
progress.dataset.uploadProgressPercent = "30";
progress.textContent = "Загрузка 30%";
row.nodes.set("[data-upload-progress-active][data-upload-progress-percent]", progress);
compactStatus.dataset.statusKind = "uploading";
compactStatus.textContent = "Обрабатывается";
announceUploadProgress();
rows = [];
const realNow = Date.now;
Date.now = () => realNow() + 5 * 60 * 1000 + 1;
scheduledPruneCallback();
Date.now = realNow;
if (announcedUploadProgressBuckets.size || announcedUploadProgressMetadata.size) {
  throw new Error("orphaned upload progress tracking was not pruned");
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_list_runtime_rejects_stale_poll_and_preserves_row_focus() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
let modalOpen = false;
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.dataset = {};
    this.id = "";
    this.hidden = false;
    this.isConnected = true;
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  closest() { return null; }
  contains() { return false; }
  focus() {}
  matches(selector) { return selector === "[data-upload-progress-poll]" && this.kind === "poll"; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  removeAttribute() {}
  setAttribute() {}
}
const list = new FakeElement("list");
const region = new FakeElement("region");
region.id = "meeting-list-region";
region.contains = () => true;
region.matches = (selector) => selector === ":hover";
const listTitle = new FakeElement("list-title");
listTitle.focus = () => { document.activeElement = listTitle; };
const toolbar = new FakeElement("toolbar");
toolbar.hidden = false;
const toolbarCount = new FakeElement("toolbar-count");
const toolbarToggle = new FakeElement("toolbar-toggle");
const toolbarToggleLabel = new FakeElement("toolbar-toggle-label");
const toolbarButton = new FakeElement("toolbar-clear");
toolbarButton.matches = (selector) => selector === "[data-clear-selection]";
toolbarButton.closest = (selector) => selector === "[data-selection-toolbar]" ? toolbar : null;
toolbar.querySelector = (selector) => {
  if (selector === "[data-clear-selection]") return toolbarButton;
  if (selector === "[data-selection-toggle]") return toolbarToggle;
  return null;
};
toolbar.contains = (target) => target === toolbarButton;
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: new FakeElement("focused-row-control"),
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener() {},
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "[data-meeting-list]") return list;
    if (selector === "#meeting-list-region") return region;
    if (selector === "[data-list-title]") return listTitle;
    if (selector === "[data-selection-toolbar]") return toolbar;
    if (selector === "[data-selection-count]") return toolbarCount;
    if (selector === "[data-selection-toggle]") return toolbarToggle;
    if (selector === "[data-selection-toggle-label]") return toolbarToggleLabel;
    if (selector === "[data-delete-dialog][open], [data-meeting-delete-dialog][open], [data-manual-upload-dialog][open], [data-content-export-dialog][open]") {
      return modalOpen ? new FakeElement("modal") : null;
    }
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = { pathname: "/meetings", search: "", hash: "" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const selectedCheckbox = { checked: true };
selectedCheckbox.closest = (selector) => selector === "[data-meeting-select]" ? selectedCheckbox : null;
const selectedRow = new FakeElement("row");
selectedRow.dataset.meetingId = "selected-meeting";
selectedRow.querySelector = (selector) => selector === "[data-meeting-select]" ? selectedCheckbox : null;
list.querySelectorAll = (selector) => selector === "[data-meeting-row]" ? [selectedRow] : [];
listeners.get("change")[0]({ target: selectedCheckbox });
const eventFor = (xhr, source) => ({
  detail: { xhr, elt: source, requestConfig: { elt: source }, target: region },
  target: source,
  defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; },
});
const beforeRequest = listeners.get("htmx:beforeRequest")[0];
const beforeSwap = listeners.get("htmx:beforeSwap")[0];
const afterRequest = listeners.get("htmx:afterRequest")[0];
const pollSource = new FakeElement("poll");
const pollXhr = {};
const pollStart = eventFor(pollXhr, pollSource);
beforeRequest(pollStart);
if (pollStart.defaultPrevented) throw new Error("initial poll was unexpectedly blocked");
const refinementXhr = {};
const refinementStart = eventFor(refinementXhr, new FakeElement("refinement"));
beforeRequest(refinementStart);
const newerRefinementXhr = {};
const newerRefinementStart = eventFor(newerRefinementXhr, new FakeElement("refinement"));
beforeRequest(newerRefinementStart);
const staleRefinementSwap = eventFor(refinementXhr, new FakeElement("refinement"));
staleRefinementSwap.detail.shouldSwap = true;
beforeSwap(staleRefinementSwap);
if (!staleRefinementSwap.defaultPrevented || staleRefinementSwap.detail.shouldSwap !== false) {
  throw new Error("older refinement was allowed to replace a newer request");
}
const newerRefinementSwap = eventFor(newerRefinementXhr, new FakeElement("refinement"));
newerRefinementSwap.detail.shouldSwap = true;
beforeSwap(newerRefinementSwap);
if (newerRefinementSwap.defaultPrevented || newerRefinementSwap.detail.shouldSwap !== true) {
  throw new Error("newest refinement was unexpectedly blocked");
}
afterRequest(eventFor(refinementXhr, new FakeElement("refinement")));
afterRequest(eventFor(newerRefinementXhr, new FakeElement("refinement")));
const latePollSwap = eventFor(pollXhr, pollSource);
latePollSwap.detail.shouldSwap = true;
beforeSwap(latePollSwap);
if (!latePollSwap.defaultPrevented || latePollSwap.detail.shouldSwap !== false) {
  throw new Error("poll older than refinement was allowed to swap");
}
const focusedDelete = new FakeElement("delete");
focusedDelete.closest = (selector) => selector === "[data-meeting-row]" ? selectedRow : null;
focusedDelete.matches = (selector) => selector === "[data-row-delete]";
document.activeElement = focusedDelete;
const currentPollXhr = {};
const currentPollStart = eventFor(currentPollXhr, pollSource);
beforeRequest(currentPollStart);
const currentPollSwap = eventFor(currentPollXhr, pollSource);
currentPollSwap.detail.shouldSwap = true;
beforeSwap(currentPollSwap);
if (currentPollSwap.defaultPrevented || currentPollSwap.detail.shouldSwap !== true) {
  throw new Error("current poll was unexpectedly blocked");
}
const replacementDelete = new FakeElement("delete");
replacementDelete.focus = () => { document.activeElement = replacementDelete; };
const replacementRow = new FakeElement("row");
replacementRow.dataset.meetingId = selectedRow.dataset.meetingId;
replacementRow.querySelector = (selector) => {
  if (selector === "[data-meeting-select]") return selectedCheckbox;
  if (selector === "[data-row-delete]") return replacementDelete;
  return null;
};
list.querySelectorAll = (selector) => selector === "[data-meeting-row]" ? [replacementRow] : [];
listeners.get("htmx:afterSwap")[0](eventFor(currentPollXhr, pollSource));
if (document.activeElement !== replacementDelete) {
  throw new Error("current poll did not restore the focused row control");
}
document.activeElement = toolbarButton;
const toolbarPollXhr = {};
beforeRequest(eventFor(toolbarPollXhr, pollSource));
const toolbarPollSwap = eventFor(toolbarPollXhr, pollSource);
toolbarPollSwap.detail.shouldSwap = true;
beforeSwap(toolbarPollSwap);
const restoredToolbarButton = new FakeElement("toolbar-clear");
restoredToolbarButton.focus = () => { document.activeElement = restoredToolbarButton; };
restoredToolbarButton.matches = (selector) => selector === "[data-clear-selection]";
restoredToolbarButton.closest = (selector) => selector === "[data-selection-toolbar]" ? toolbar : null;
toolbar.querySelector = (selector) => selector === "[data-clear-selection]" ? restoredToolbarButton : null;
listeners.get("htmx:afterSwap")[0](eventFor(toolbarPollXhr, pollSource));
if (document.activeElement !== restoredToolbarButton) {
  throw new Error("poll stole focus from the selection toolbar");
}
replacementDelete.closest = (selector) => selector === "[data-meeting-row]" ? replacementRow : null;
replacementDelete.matches = (selector) => selector === "[data-row-delete]";
document.activeElement = replacementDelete;
const automaticRefreshXhr = {};
const automaticSource = new FakeElement("automatic-refresh");
beforeRequest(eventFor(automaticRefreshXhr, automaticSource));
const automaticSwap = eventFor(automaticRefreshXhr, automaticSource);
automaticSwap.detail.shouldSwap = true;
beforeSwap(automaticSwap);
const automaticReplacementDelete = new FakeElement("delete");
automaticReplacementDelete.focus = () => { document.activeElement = automaticReplacementDelete; };
const automaticReplacementRow = new FakeElement("row");
automaticReplacementRow.dataset.meetingId = replacementRow.dataset.meetingId;
automaticReplacementRow.querySelector = (selector) => {
  if (selector === "[data-meeting-select]") return selectedCheckbox;
  if (selector === "[data-row-delete]") return automaticReplacementDelete;
  return null;
};
list.querySelectorAll = (selector) => selector === "[data-meeting-row]" ? [automaticReplacementRow] : [];
listeners.get("htmx:afterSwap")[0](eventFor(automaticRefreshXhr, automaticSource));
afterRequest(eventFor(automaticRefreshXhr, automaticSource));
if (document.activeElement !== automaticReplacementDelete) {
  throw new Error("automatic list refresh did not restore the focused row control");
}
automaticReplacementDelete.closest = (selector) => selector === "[data-meeting-row]" ? automaticReplacementRow : null;
automaticReplacementDelete.matches = (selector) => selector === "[data-row-delete]";
document.activeElement = automaticReplacementDelete;
const secondDelete = new FakeElement("delete");
const secondRow = new FakeElement("row");
secondRow.dataset.meetingId = "second-meeting";
secondDelete.closest = (selector) => selector === "[data-meeting-row]" ? secondRow : null;
secondDelete.matches = (selector) => selector === "[data-row-delete]";
secondRow.querySelector = (selector) => selector === "[data-row-delete]" ? secondDelete : null;
list.querySelectorAll = (selector) => selector === "[data-meeting-row]"
  ? [automaticReplacementRow, secondRow]
  : [];
const withinListMoveXhr = {};
beforeRequest(eventFor(withinListMoveXhr, pollSource));
document.activeElement = secondDelete;
const withinListMoveSwap = eventFor(withinListMoveXhr, pollSource);
withinListMoveSwap.detail.shouldSwap = true;
beforeSwap(withinListMoveSwap);
const nextSecondDelete = new FakeElement("delete");
nextSecondDelete.focus = () => { document.activeElement = nextSecondDelete; };
const nextSecondRow = new FakeElement("row");
nextSecondRow.dataset.meetingId = secondRow.dataset.meetingId;
nextSecondRow.querySelector = (selector) => selector === "[data-row-delete]" ? nextSecondDelete : null;
list.querySelectorAll = (selector) => selector === "[data-meeting-row]"
  ? [automaticReplacementRow, nextSecondRow]
  : [];
listeners.get("htmx:afterSwap")[0](eventFor(withinListMoveXhr, pollSource));
if (document.activeElement !== nextSecondDelete) {
  throw new Error("poll restored its initial row after focus moved to another row");
}
document.activeElement = automaticReplacementDelete;
const movedFocusPollXhr = {};
beforeRequest(eventFor(movedFocusPollXhr, pollSource));
const outsideList = new FakeElement("outside-list");
document.activeElement = outsideList;
const movedFocusPollSwap = eventFor(movedFocusPollXhr, pollSource);
movedFocusPollSwap.detail.shouldSwap = true;
beforeSwap(movedFocusPollSwap);
listeners.get("htmx:afterSwap")[0](eventFor(movedFocusPollXhr, pollSource));
if (document.activeElement !== outsideList) {
  throw new Error("poll restored stale row focus after the user moved elsewhere");
}
document.activeElement = automaticReplacementDelete;
const disappearingPollXhr = {};
beforeRequest(eventFor(disappearingPollXhr, pollSource));
const disappearingPollSwap = eventFor(disappearingPollXhr, pollSource);
disappearingPollSwap.detail.shouldSwap = true;
beforeSwap(disappearingPollSwap);
list.querySelectorAll = () => [];
listeners.get("htmx:afterSwap")[0](eventFor(disappearingPollXhr, pollSource));
if (document.activeElement !== listTitle) {
  throw new Error("poll did not move focus to the list title after the focused row disappeared");
}
const retry = new FakeElement("retry");
retry.closest = (selector) => selector === "[data-list-retry]" ? retry : null;
document.activeElement = retry;
const retryXhr = {};
const retrySource = new FakeElement("retry-source");
beforeRequest(eventFor(retryXhr, retrySource));
const focusAfterRetry = new FakeElement("search");
document.activeElement = focusAfterRetry;
const retrySwap = eventFor(retryXhr, retrySource);
retrySwap.detail.shouldSwap = true;
beforeSwap(retrySwap);
listeners.get("htmx:afterSwap")[0](eventFor(retryXhr, retrySource));
afterRequest(eventFor(retryXhr, retrySource));
if (document.activeElement !== focusAfterRetry) {
  throw new Error("delayed retry completion stole newer user focus");
}
modalOpen = true;
const modalPollStart = eventFor({}, pollSource);
beforeRequest(modalPollStart);
if (!modalPollStart.defaultPrevented) {
  throw new Error("poll was allowed to replace the list behind an open modal");
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_list_runtime_moves_focus_before_hiding_selection_toolbar() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const script = fs.readFileSync(process.argv[1], "utf8");
const updateSelectionSource = script.slice(
  script.indexOf("const updateSelection"),
  script.indexOf("const reconcileMeetingSelection"),
);
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.checked = false;
    this.classList = { toggle() {} };
    this.dataset = {};
    this.hidden = false;
  }
  contains(target) { return this.kind === "toolbar" && target === document.activeElement; }
  focus() { document.activeElement = this; }
  querySelector() { return null; }
  setAttribute() {}
}
global.HTMLElement = FakeElement;
const toolbar = new FakeElement("toolbar");
const toolbarButton = new FakeElement("toolbar-button");
const countLabel = new FakeElement("count");
const heading = new FakeElement("heading");
const rowLink = new FakeElement("row-link");
const checkbox = new FakeElement("checkbox");
const row = new FakeElement("row");
row.dataset.meetingId = "surviving-meeting";
row.querySelector = (selector) => {
  if (selector === "[data-meeting-open]") return rowLink;
  if (selector === "[data-meeting-select]") return checkbox;
  return null;
};
global.document = {
  activeElement: toolbarButton,
  querySelector(selector) {
    if (selector === "[data-selection-toolbar]") return toolbar;
    if (selector === "[data-selection-count]") return countLabel;
    if (selector === "[data-list-title]") return heading;
    return null;
  },
};
const selectedMeetingIds = new Set(["removed-meeting"]);
const allRows = () => [row];
const selectableRows = () => [row];
const selectedRows = () => [];
const currentList = () => row;
const rowPrimaryFocusTarget = (candidate) => candidate?.querySelector("[data-meeting-open]") || null;
eval(`${updateSelectionSource}\n;global.updateSelection = updateSelection;`);
updateSelection();
if (!toolbar.hidden) throw new Error("empty selection toolbar remained visible");
if (document.activeElement !== rowLink) {
  throw new Error("focus was hidden with the selection toolbar");
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_list_runtime_announces_only_user_refinements() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.dataset = {};
    this.hidden = false;
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  closest(selector) {
    if (this.kind === "search" && selector.includes("#meeting-search")) return this;
    return null;
  }
  contains() { return false; }
  focus() { document.activeElement = this; }
  matches(selector) { return selector === "[data-upload-progress-poll]" && this.kind === "poll"; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  removeAttribute() {}
  replaceChildren() { this.textContent = ""; }
  setAttribute() {}
}
const list = new FakeElement("list");
const region = new FakeElement("region");
region.id = "meeting-list-region";
const count = new FakeElement("count");
count.textContent = "Найдено: 3";
const current = new FakeElement("current");
current.dataset.meetingResultComplete = "true";
const announcer = new FakeElement("announcer");
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: body,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener() {},
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "[data-meeting-list]") return list;
    if (selector === "#meeting-list-region") return region;
    if (selector === "[data-meeting-result-count]") return count;
    if (selector === "[data-list-current-content]") return current;
    if (selector === "[data-meeting-result-announcer]") return announcer;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = { pathname: "/meetings", search: "", hash: "" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const eventFor = (xhr, triggeringTarget = null) => ({
  detail: {
    xhr,
    elt: region,
    requestConfig: { elt: region, triggeringEvent: triggeringTarget ? { target: triggeringTarget } : null },
    target: region,
    shouldSwap: true,
  },
  target: region,
  preventDefault() {},
});
const beforeRequest = listeners.get("htmx:beforeRequest")[0];
const afterSwap = listeners.get("htmx:afterSwap")[0];
const automaticXhr = {};
beforeRequest(eventFor(automaticXhr));
afterSwap(eventFor(automaticXhr));
if (announcer.textContent) {
  throw new Error("programmatic list refresh announced a result count");
}
const refinementXhr = {};
beforeRequest(eventFor(refinementXhr, new FakeElement("search")));
afterSwap(eventFor(refinementXhr, new FakeElement("search")));
if (announcer.textContent !== "Найдено: 3") {
  throw new Error("user refinement did not announce the result count");
}
announcer.textContent = "";
const supersededRefinementXhr = {};
const winningAutomaticXhr = {};
beforeRequest(eventFor(supersededRefinementXhr, new FakeElement("search")));
beforeRequest(eventFor(winningAutomaticXhr));
afterSwap(eventFor(winningAutomaticXhr));
if (announcer.textContent !== "Найдено: 3") {
  throw new Error("winning automatic request lost a pending refinement announcement");
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_list_runtime_reset_clears_refinements_preserves_sort_and_restores_focus() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
let countVisible = true;
let navigationCount = 0;
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.dataset = {};
    this.hidden = false;
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.value = "";
    this.selectedOptions = [];
    this.handlers = new Map();
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener(name, handler) { this.handlers.set(name, handler); }
  append() {}
  closest(selector) {
    if (this.kind === "reset" && selector.includes("[data-filter-reset]")) return this;
    if (this.kind === "reset" && selector === "form") return form;
    if (this.kind === "form" && selector.includes(".cabinet-list-controls")) return this;
    return null;
  }
  contains() { return false; }
  focus() { document.activeElement = this; this.focused = true; }
  matches(selector) { return selector === "[data-meeting-list]" && this.kind === "list"; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  removeAttribute() {}
  replaceChildren() { this.textContent = ""; }
  setAttribute() {}
}
const search = new FakeElement("search");
search.value = "синк";
const status = new FakeElement("status");
status.value = "processing";
const access = new FakeElement("access");
access.value = "shared";
const sort = new FakeElement("sort");
sort.value = "updated_desc";
sort.selectedOptions = [{ textContent: "Недавно обновлённые" }];
const reset = new FakeElement("reset");
const filterLabel = new FakeElement("filter-label");
const filterSummary = new FakeElement("filter-summary");
filterSummary.querySelector = (selector) => selector === ".cabinet-control-label" ? filterLabel : null;
const filterDisclosure = new FakeElement("filter-disclosure");
filterDisclosure.querySelector = (selector) => selector === "summary" ? filterSummary : null;
const sortLabel = new FakeElement("sort-label");
const sortSummary = new FakeElement("sort-summary");
const form = new FakeElement("form");
form.querySelector = (selector) => ({
  "#meeting-search": search,
  "#meeting-status": status,
  "#meeting-access": access,
  "#meeting-sort": sort,
  "[data-filter-disclosure]": filterDisclosure,
  "[data-filter-reset]": reset,
  "[data-sort-disclosure] .cabinet-control-label": sortLabel,
  "[data-sort-disclosure] > summary": sortSummary,
}[selector] || null);
const list = new FakeElement("list");
const loading = new FakeElement("loading");
loading.hidden = true;
const current = new FakeElement("current");
current.dataset.meetingResultComplete = "true";
const region = new FakeElement("region");
region.id = "meeting-list-region";
region.querySelector = (selector) => {
  if (selector === "[data-list-loading-state]") return loading;
  if (selector === "[data-list-current-content]") return current;
  return null;
};
const count = new FakeElement("count");
count.textContent = "Найдено: 4";
const announcer = new FakeElement("announcer");
const heading = new FakeElement("heading");
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: reset,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener() {},
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "meta[name='csrf-token']") return null;
    if (selector === ".cabinet-list-controls") return form;
    if (selector === "[data-meeting-list]") return list;
    if (selector === "#meeting-list-region") return region;
    if (selector === "[data-meeting-result-count]") return countVisible ? count : null;
    if (selector === "[data-list-current-content]") return current;
    if (selector === "[data-meeting-result-announcer]") return announcer;
    if (selector === "[data-list-title]") return heading;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = {
  pathname: "/meetings",
  search: "?q=%D1%81%D0%B8%D0%BD%D0%BA&status=processing&access=shared&sort=updated_desc",
  hash: "",
  href: "https://graf.test/meetings?q=test",
  assign() { navigationCount += 1; },
  replace() { navigationCount += 1; },
  reload() {},
};
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
form.requestSubmit = () => {
  const xhr = {};
  const event = {
    detail: {
      xhr,
      elt: form,
      requestConfig: { elt: form, triggeringEvent: { type: "submit", target: form } },
      target: region,
      shouldSwap: true,
    },
    target: form,
    preventDefault() {},
  };
  for (const handler of listeners.get("htmx:beforeRequest") || []) handler(event);
  countVisible = false;
  for (const handler of listeners.get("htmx:afterSwap") || []) handler(event);
};
(async () => {
  vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
  const clickHandlers = listeners.get("click") || [];
  if (!clickHandlers.length) throw new Error("meeting-list click handler was not installed");
  let defaultPrevented = false;
  const clickEvent = { target: reset, preventDefault() { defaultPrevented = true; } };
  for (const click of clickHandlers) await click(clickEvent);
  if (!defaultPrevented || navigationCount !== 0) throw new Error("reset used full navigation");
  if (search.value || status.value || access.value) throw new Error("reset left a refinement value");
  if (sort.value !== "updated_desc") throw new Error("reset discarded the selected sort");
  if (!reset.hidden || filterLabel.textContent !== "Фильтры") {
    throw new Error("reset did not synchronize the visible controls");
  }
  if (announcer.textContent !== "Показаны все встречи") {
    throw new Error(`reset announcement missing: ${announcer.textContent}`);
  }
  if (document.activeElement !== heading || !heading.focused) {
    throw new Error("reset did not restore focus to the list heading");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_list_runtime_restores_focused_poll_error_to_recovery() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.children = [];
    this.dataset = {};
    this.hidden = false;
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
  contains() { return false; }
  focus() { document.activeElement = this; }
  matches(selector) { return selector === "[data-upload-progress-poll]" && this.kind === "poll"; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  removeAttribute() {}
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute() {}
}
const row = new FakeElement("row");
row.dataset.meetingId = "focused-meeting";
const focusedDelete = new FakeElement("delete");
focusedDelete.closest = (selector) => selector === "[data-meeting-row]" ? row : null;
focusedDelete.matches = (selector) => selector === "[data-row-delete]";
row.querySelector = (selector) => selector === "[data-row-delete]" ? focusedDelete : null;
const list = new FakeElement("list");
list.querySelectorAll = (selector) => selector === "[data-meeting-row]" ? [row] : [];
const loading = new FakeElement("loading");
const current = new FakeElement("current");
const region = new FakeElement("region");
region.id = "meeting-list-region";
region.querySelector = (selector) => {
  if (selector === "[data-list-loading-state]") return loading;
  if (selector === "[data-list-current-content]") return current;
  return null;
};
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: focusedDelete,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener() {},
  createElement(kind) { return new FakeElement(kind); },
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "[data-meeting-list]") return list;
    if (selector === "#meeting-list-region") return region;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = { pathname: "/meetings", search: "", hash: "" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const poll = new FakeElement("poll");
const xhr = { status: 500, getResponseHeader() { return ""; } };
const event = {
  detail: { xhr, elt: poll, requestConfig: { elt: poll }, target: region },
  target: poll,
  preventDefault() {},
};
listeners.get("htmx:beforeRequest")[0](event);
listeners.get("htmx:responseError")[0](event);
const recovery = current.children[0];
if (!recovery || document.activeElement !== recovery) {
  throw new Error("poll error did not move focused removed content to recovery");
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_list_refresh_respects_newer_user_focus() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const script = fs.readFileSync(process.argv[1], "utf8");
const restoreSource = script.slice(
  script.indexOf("const restoreListRefreshFocus"),
  script.indexOf("const updateSelection"),
);
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.isConnected = true;
  }
  closest() { return null; }
  focus() { document.activeElement = this; }
  querySelector() { return null; }
}
global.HTMLElement = FakeElement;
const body = new FakeElement("body");
const documentElement = new FakeElement("document-element");
const heading = new FakeElement("heading");
const link = new FakeElement("link");
const row = new FakeElement("row");
row.dataset = { meetingId: "next-meeting" };
row.querySelector = (selector) => selector === "[data-meeting-open]" ? link : null;
const origin = new FakeElement("origin");
const outside = new FakeElement("outside");
global.document = {
  activeElement: outside,
  body,
  documentElement,
  querySelector(selector) { return selector === "[data-list-title]" ? heading : null; },
};
let listRefreshFocusMeetingIds = ["next-meeting"];
let listRefreshShouldRestoreFocus = true;
let listRefreshFocusOrigin = origin;
const allRows = () => [row];
const rowPrimaryFocusTarget = (candidate) => candidate?.querySelector("[data-meeting-open]") || null;
eval(`${restoreSource}\n;global.restoreListRefreshFocus = restoreListRefreshFocus;`);
if (restoreListRefreshFocus()) {
  throw new Error("refresh reported focus restoration after the user moved elsewhere");
}
if (document.activeElement !== outside) {
  throw new Error("refresh overrode newer user focus");
}
if (listRefreshShouldRestoreFocus || listRefreshFocusMeetingIds.length || listRefreshFocusOrigin !== null) {
  throw new Error("cancelled focus recovery retained stale state");
}
listRefreshFocusMeetingIds = ["next-meeting"];
listRefreshShouldRestoreFocus = true;
listRefreshFocusOrigin = origin;
document.activeElement = origin;
if (!restoreListRefreshFocus() || document.activeElement !== link) {
  throw new Error("refresh did not restore focus when user focus remained at the origin");
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    ("status", "expected_copy"),
    [(401, "Нужно войти снова"), (403, "Нет доступа к встречам")],
)
def test_meeting_list_runtime_scrubs_stale_poll_after_authorization_loss(
    status: int,
    expected_copy: str,
) -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
let replacedPath = "";
let navigatedPath = "";
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.children = [];
    this.dataset = {};
    this.hidden = false;
    this.id = "";
    this.textContent = "";
    this.attributes = new Set();
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
  contains() { return false; }
  focus() { this.focused = true; }
  hasAttribute(name) { return this.attributes.has(name); }
  matches(selector) { return selector === "[data-upload-progress-poll]" && this.kind === "poll"; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  remove() { this.removed = true; }
  removeAttribute(name) { this.attributes.delete(name); }
  replaceChildren(...nodes) { this.children = nodes; this.textContent = ""; }
  setAttribute(name, value) { this.attributes.add(name); this[name] = String(value); }
}
const list = new FakeElement("list");
const loading = new FakeElement("loading");
const current = new FakeElement("current");
current.textContent = "PRIVATE MEETING TITLE";
const region = new FakeElement("region");
region.id = "meeting-list-region";
region.querySelector = (selector) => {
  if (selector === "[data-list-loading-state]") return loading;
  if (selector === "[data-list-current-content]") return current;
  return null;
};
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: null,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener() {},
  createElement(kind) { return new FakeElement(kind); },
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "[data-meeting-list]") return list;
    if (selector === "#meeting-list-region") return region;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = {
  pathname: "/meetings",
  search: "?q=private",
  hash: "",
  replace(path) { navigatedPath = path; },
};
global.history = { replaceState() { throw new Error("synthetic history rejection"); } };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const eventFor = (xhr, source) => ({
  detail: { xhr, elt: source, requestConfig: { elt: source }, target: region, shouldSwap: false },
  target: source,
  defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; },
});
const beforeRequest = listeners.get("htmx:beforeRequest")[0];
const beforeSwap = listeners.get("htmx:beforeSwap")[0];
const responseError = listeners.get("htmx:responseError")[0];
const pollSource = new FakeElement("poll");
const pollXhr = {};
beforeRequest(eventFor(pollXhr, pollSource));
beforeRequest(eventFor({}, new FakeElement("refinement")));
const status = Number(process.argv[2]);
const authXhr = {
  status,
  responseText: status === 403 ? JSON.stringify({ code: "meeting_access_revoked" }) : "{}",
  getResponseHeader() { return ""; },
};
const authEvent = eventFor(authXhr, pollSource);
beforeSwap(authEvent);
if (authEvent.defaultPrevented) {
  throw new Error("authorization loss was suppressed as a stale poll");
}
responseError(authEvent);
const allText = (node) => [node.textContent, ...node.children.flatMap(allText)].join(" ");
const rendered = allText(current);
if (rendered.includes("PRIVATE")) throw new Error("private list metadata remained connected");
if (!rendered.includes(process.argv[3])) throw new Error(`missing recovery copy: ${rendered}`);
if (replacedPath !== "" || navigatedPath !== "/meetings") {
  throw new Error(`private list URL did not use the navigation fallback: ${navigatedPath}`);
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path), str(status), expected_copy],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_list_runtime_invalidates_and_recovers_detached_authorization_requests() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
class FakeElement {
  constructor(kind = "") {
    this.kind = kind;
    this.children = [];
    this.dataset = {};
    this.hidden = false;
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
  contains() { return false; }
  focus() { document.activeElement = this; }
  matches(selector) { return selector === "[data-upload-progress-poll]" && this.kind === "poll"; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  remove() { this.isConnected = false; }
  removeAttribute() {}
  replaceChildren(...nodes) { this.children = nodes; this.textContent = ""; }
  setAttribute() {}
}
const list = new FakeElement("list");
const loading = new FakeElement("loading");
const current = new FakeElement("current");
current.textContent = "PRIVATE MEETING TITLE";
const region = new FakeElement("region");
region.id = "meeting-list-region";
region.querySelector = (selector) => {
  if (selector === "[data-list-loading-state]") return loading;
  if (selector === "[data-list-current-content]") return current;
  return null;
};
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: body,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  addEventListener() {},
  createElement(kind) { return new FakeElement(kind); },
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "[data-meeting-list]") return list;
    if (selector === "#meeting-list-region") return region;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = { pathname: "/meetings", search: "?q=private", hash: "" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const eventFor = (xhr, source) => ({
  detail: { xhr, elt: source, requestConfig: { elt: source }, target: region, shouldSwap: true },
  target: source,
  defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; },
});
const beforeRequest = listeners.get("htmx:beforeRequest")[0];
const beforeSwap = listeners.get("htmx:beforeSwap")[0];
const afterRequest = listeners.get("htmx:afterRequest")[0];
const responseError = listeners.get("htmx:responseError")[0];
const pendingXhr = {};
const pendingSource = new FakeElement("refinement");
beforeRequest(eventFor(pendingXhr, pendingSource));
const authXhr = {
  status: 401,
  responseText: "{}",
  getResponseHeader() { return ""; },
};
responseError(eventFor(authXhr, new FakeElement("refinement")));
const pendingSwap = eventFor(pendingXhr, pendingSource);
pendingSwap.detail.shouldSwap = true;
beforeSwap(pendingSwap);
if (!pendingSwap.defaultPrevented || pendingSwap.detail.shouldSwap !== false) {
  throw new Error("in-flight list response was allowed after authorization recovery");
}
afterRequest(eventFor(pendingXhr, pendingSource));
const detachedXhr = {
  readyState: 1,
  status: 0,
  responseText: "{}",
  listeners: {},
  addEventListener(name, callback) { this.listeners[name] = callback; },
  getResponseHeader() { return ""; },
};
const detachedSource = new FakeElement("poll");
beforeRequest(eventFor(detachedXhr, detachedSource));
detachedSource.isConnected = false;
detachedXhr.status = 403;
detachedXhr.responseText = JSON.stringify({ code: "meeting_access_revoked" });
detachedXhr.readyState = 4;
if (typeof detachedXhr.listeners.readystatechange !== "function") {
  throw new Error("detached request did not get an authorization observer");
}
detachedXhr.listeners.readystatechange();
const allText = (node) => [node.textContent, ...node.children.flatMap(allText)].join(" ");
const rendered = allText(current);
if (rendered.includes("PRIVATE")) throw new Error("private list metadata remained after detached authorization loss");
if (!rendered.includes("Нет доступа к встречам")) throw new Error(`missing detached recovery copy: ${rendered}`);
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_meeting_detail_runtime_scrubs_private_dom_after_access_loss() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
let intervalCallback = null;
let currentMain = null;
let replacedPath = "";
let navigatedPath = "";
const removedStorageKeys = [];
class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.hidden = false;
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
  contains() { return false; }
  focus() { this.focused = true; }
  matches() { return false; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  removeAttribute() {}
  replaceWith(node) {
    this.isConnected = false;
    currentMain = node;
  }
  setAttribute(name, value) { this[name] = String(value); }
}
const makeRecovery = () => {
  const main = new FakeElement("main");
  main.id = "cabinet-main";
  const state = new FakeElement("section");
  const title = new FakeElement("h1");
  title.id = "meeting-detail-recovery-title";
  const description = new FakeElement("p");
  const action = new FakeElement("a");
  state.append(title, description, action);
  main.append(state);
  main.querySelector = (selector) => ({
    "[data-cabinet-state]": state,
    "h1": title,
    ".cabinet-state__description": description,
    ".cabinet-state__action a": action,
  })[selector] || null;
  return main;
};
const recoveryTemplate = {
  content: { firstElementChild: { cloneNode() { return makeRecovery(); } } },
};
const detail = new FakeElement("main");
detail.id = "cabinet-main";
detail.dataset.playbackPollActive = "true";
detail.dataset.playbackPollUrl = "/meetings/private-id";
detail.dataset.mediaRevisionId = "private-revision-id";
detail.textContent = "PRIVATE MEETING TITLE";
currentMain = detail;
const body = new FakeElement("body");
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: null,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  title: "PRIVATE MEETING TITLE - GRAF",
  addEventListener() {},
  createElement(tag) { return new FakeElement(tag); },
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "[data-meeting-detail-recovery-template]") return recoveryTemplate;
    if (selector === "[data-playback-poll-url]") return currentMain === detail ? detail : null;
    if (selector === "#cabinet-main") return currentMain;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = {
  pathname: "/meetings/private-id",
  search: "",
  hash: "",
  href: "https://graf.test/meetings/private-id",
  replace(path) { navigatedPath = path; },
};
global.history = { replaceState() { throw new Error("synthetic history rejection"); } };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem(key) { removedStorageKeys.push(key); } };
global.fetch = async () => ({
  redirected: false,
  status: 403,
  ok: false,
  headers: { get() { return ""; } },
  clone() { return { json: async () => ({ code: "meeting_access_revoked" }) }; },
});
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval(callback) { intervalCallback = callback; return 1; },
  setTimeout,
};
const allText = (node) => [node.textContent, ...node.children.flatMap(allText)].join(" ");
(async () => {
  vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
  if (!intervalCallback) throw new Error("playback recovery poll did not start");
  intervalCallback();
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  if (currentMain === detail || detail.isConnected) throw new Error("private detail remained connected");
  if (allText(currentMain).includes("PRIVATE")) throw new Error("private detail leaked into recovery DOM");
  if (document.title.includes("PRIVATE") || document.title !== "Встреча больше недоступна - GRAF") {
    throw new Error("private document title was not replaced");
  }
  if (replacedPath !== "" || navigatedPath !== "/meetings") {
    throw new Error("private detail URL did not use the navigation fallback");
  }
  if (!removedStorageKeys.includes("htmx-history-cache") || !removedStorageKeys.includes("htmx-current-path-for-history")) {
    throw new Error("private HTMX history was not cleared");
  }
  if (currentMain.id !== "cabinet-main" || !currentMain.focused) {
    throw new Error("safe recovery main was not installed and focused");
  }
  const state = currentMain.children[0];
  const heading = state?.children[0];
  const action = state?.children[2];
  if (heading?.tagName !== "H1" || action?.href !== "/meetings") {
    throw new Error("safe recovery semantics or action are incomplete");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    ("status", "problem_code", "redirected", "response_url", "expect_reload"),
    [
        (200, "", True, "https://graf.test/meetings/private-id", False),
        (404, "speaker_not_found", False, "https://graf.test/speakers/unknown", False),
        (403, "export_policy_denied", False, "https://graf.test/content-exports", False),
    ],
)
def test_detail_fetch_actions_keep_accessible_detail_for_local_action_outcomes(
    status: int,
    problem_code: str,
    redirected: bool,
    response_url: str,
    expect_reload: bool,
) -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
let submitHandler = null;
let currentMain = null;
let reloadCount = 0;
class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.hidden = false;
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.disabled = false;
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener(name, handler) {
    if (this === form && name === "submit") submitHandler = handler;
  }
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
  contains() { return false; }
  focus() { this.focused = true; }
  matches() { return false; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  removeAttribute() {}
  replaceWith(node) { this.isConnected = false; currentMain = node; }
  setAttribute(name, value) { this[name] = String(value); }
}
const detail = new FakeElement("main");
detail.id = "cabinet-main";
detail.dataset.playbackPollActive = "false";
detail.dataset.playbackPollUrl = "/meetings/private-id";
detail.textContent = "PRIVATE MEETING";
currentMain = detail;
const error = new FakeElement("p");
error.hidden = true;
const submit = new FakeElement("button");
const form = new FakeElement("form");
form.action = "/meetings/private-id/speakers/unknown";
form.querySelector = (selector) => {
  if (selector === "[data-speaker-name-error]") return error;
  if (selector === "button[type='submit']") return submit;
  return null;
};
const body = new FakeElement("body");
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.FormData = class {};
global.document = {
  activeElement: form,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  title: "PRIVATE MEETING - GRAF",
  addEventListener() {},
  createElement(tag) { return new FakeElement(tag); },
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "meta[name='csrf-token']") return null;
    if (selector === "[data-playback-poll-url]") return currentMain === detail ? detail : null;
    if (selector === "#cabinet-main") return currentMain;
    return null;
  },
  querySelectorAll(selector) {
    return selector === "[data-speaker-name-form]" ? [form] : [];
  },
};
global.location = {
  pathname: "/meetings/private-id",
  search: "",
  hash: "",
  href: "https://graf.test/meetings/private-id",
  reload() { reloadCount += 1; },
  replace() {},
};
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.fetch = async () => ({
  status: Number(process.argv[2]),
  ok: Number(process.argv[2]) >= 200 && Number(process.argv[2]) < 400,
  redirected: process.argv[4] === "true",
  url: process.argv[5],
  headers: { get() { return ""; } },
  clone() { return { json: async () => ({ code: process.argv[3] }) }; },
});
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { return 1; },
  setTimeout,
};
(async () => {
  vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
  if (!submitHandler) throw new Error("speaker submit handler was not installed");
  await submitHandler({ preventDefault() {} });
  const expectReload = process.argv[6] === "true";
  if (currentMain !== detail || !detail.isConnected) {
    throw new Error("local action outcome removed an accessible meeting detail");
  }
  if ((reloadCount === 1) !== expectReload) {
    throw new Error(`unexpected reload count: ${reloadCount}`);
  }
  if (!expectReload && Number(process.argv[2]) >= 400 && (error.hidden || submit.disabled)) {
    throw new Error("local action error was not shown with an enabled retry");
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
"""
    completed = subprocess.run(
        [
            "node",
            "-e",
            harness,
            str(script_path),
            str(status),
            problem_code,
            str(redirected).lower(),
            response_url,
            str(expect_reload).lower(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("status", [403, 404])
def test_ready_meeting_detail_scrubs_private_dom_after_htmx_access_loss(status: int) -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
let currentMain = null;
class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  append(...nodes) { this.children.push(...nodes); }
  closest() { return null; }
  contains(target) { return target === this || target?.detailOwner === this; }
  focus() { this.focused = true; }
  matches() { return false; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  removeAttribute() {}
  replaceWith(node) { this.isConnected = false; currentMain = node; }
  setAttribute(name, value) { this[name] = String(value); }
}
const makeRecovery = () => {
  const main = new FakeElement("main");
  main.id = "cabinet-main";
  const state = new FakeElement("section");
  const title = new FakeElement("h1");
  title.id = "meeting-detail-recovery-title";
  const description = new FakeElement("p");
  const link = new FakeElement("a");
  state.append(title, description, link);
  main.append(state);
  main.querySelector = (selector) => ({
    "[data-cabinet-state]": state,
    "h1": title,
    ".cabinet-state__description": description,
    ".cabinet-state__action a": link,
  })[selector] || null;
  return main;
};
const recoveryTemplate = {
  content: { firstElementChild: { cloneNode() { return makeRecovery(); } } },
};
const detail = new FakeElement("main");
detail.id = "cabinet-main";
detail.dataset.playbackPollActive = "false";
detail.dataset.playbackPollUrl = "/meetings/private-id";
detail.textContent = "PRIVATE READY MEETING";
currentMain = detail;
const action = new FakeElement("button");
action.detailOwner = detail;
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: action,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  title: "PRIVATE READY MEETING - GRAF",
  addEventListener() {},
  createElement(tag) { return new FakeElement(tag); },
  getElementById() { return null; },
  querySelector(selector) {
    if (selector === "[data-meeting-detail-recovery-template]") return recoveryTemplate;
    if (selector === "[data-playback-poll-url]") return currentMain === detail ? detail : null;
    if (selector === "#cabinet-main") return currentMain;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = { pathname: "/meetings/private-id", search: "", hash: "", href: "https://graf.test/meetings/private-id" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout,
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { throw new Error("ready detail unexpectedly started polling"); },
  setTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const status = Number(process.argv[2]);
const xhr = {
  status,
  responseText: status === 403 ? JSON.stringify({ code: "meeting_access_revoked" }) : "{}",
  responseURL: "https://graf.test/meetings/private-id",
  getResponseHeader() { return ""; },
};
const event = {
  detail: { xhr, elt: action, target: detail, shouldSwap: true },
  target: action,
  defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; },
};
for (const handler of listeners.get("htmx:beforeSwap") || []) handler(event);
if (!event.defaultPrevented || event.detail.shouldSwap !== false) {
  throw new Error("private error response was allowed to swap");
}
if (currentMain === detail || detail.isConnected) {
  throw new Error("ready private detail remained connected");
}
if (document.title !== "Встреча больше недоступна - GRAF") {
  throw new Error(`private document title survived: ${document.title}`);
}
const rendered = [currentMain.textContent, ...currentMain.children.map((node) => node.textContent)].join(" ");
if (rendered.includes("PRIVATE")) throw new Error("private detail leaked into recovery DOM");
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path), str(status)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_detail_fetch_actions_share_fail_closed_authorization_recovery() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert script.count("recoverMeetingDetailFromResponse(response)") == 4
    assert "summaryActionProblemCodes" in script
    assert "sharingActionProblemCodes" in script
    assert '"meeting_not_found"' in script
    assert "isShareRequest" in script
    assert "renderShareRequestError" in script
    assert "preserveDetail: shareRequest" in script
    assert "meeting-share-action-error" in script
    assert "meetingDetailRecoveredError" in script
    assert (
        script.count(
            "recoverMeetingDetailFromResponse(response, { actionProblemCodes: summaryActionProblemCodes })"
        )
        == 2
    )
    assert (
        script.count(
            "recoverMeetingDetailFromResponse(response, { actionProblemCodes: sharingActionProblemCodes })"
        )
        == 2
    )
    assert "initMeetingDetailAuthorizationRecovery()" in script
    assert 'document.body.addEventListener("htmx:beforeSwap", recoverFromHtmx)' in script
    assert 'document.body.addEventListener("htmx:responseError", recoverFromHtmx)' in script


def test_share_fragment_404_keeps_accessible_detail_and_shows_local_error() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const listeners = new Map();
let currentMain = null;
class FakeElement {
  constructor(tag = "div") {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.id = "";
    this.isConnected = true;
    this.textContent = "";
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
  }
  addEventListener() {}
  append(...nodes) { this.children.push(...nodes); }
  closest(selector) {
    if (selector === "[data-share-dialog-open]" && this.isShareTrigger) return this;
    if (selector.includes("#meeting-share-host") && this.id === "meeting-share-host") return this;
    return null;
  }
  contains(target) { return target === this || target?.detailOwner === this; }
  focus() {}
  matches() { return false; }
  querySelector(selector) {
    if (selector === "#meeting-share-host" && this === detail) return shareHost;
    return null;
  }
  querySelectorAll() { return []; }
  replaceChildren(...nodes) { this.children = nodes; }
  removeAttribute() {}
  replaceWith(node) { this.isConnected = false; currentMain = node; }
  setAttribute(name, value) { this[name] = String(value); }
}
const detail = new FakeElement("main");
detail.id = "cabinet-main";
detail.dataset.playbackPollUrl = "/meetings/private-id";
detail.textContent = "PRIVATE MEETING";
const shareHost = new FakeElement("div");
shareHost.id = "meeting-share-host";
shareHost.detailOwner = detail;
const shareTrigger = new FakeElement("button");
shareTrigger.isShareTrigger = true;
shareTrigger.detailOwner = detail;
currentMain = detail;
const body = new FakeElement("body");
body.addEventListener = (name, handler) => {
  const handlers = listeners.get(name) || [];
  handlers.push(handler);
  listeners.set(name, handlers);
};
global.Element = FakeElement;
global.HTMLElement = FakeElement;
global.HTMLFormElement = FakeElement;
global.HTMLButtonElement = FakeElement;
global.HTMLDialogElement = FakeElement;
global.Node = FakeElement;
global.document = {
  activeElement: shareTrigger,
  body,
  documentElement: { dataset: {} },
  hidden: false,
  title: "PRIVATE MEETING - GRAF",
  addEventListener() {},
  createElement(tag) { return new FakeElement(tag); },
  querySelector(selector) {
    if (selector === "[data-playback-poll-url]") return currentMain === detail ? detail : null;
    if (selector === "#cabinet-main") return currentMain;
    return null;
  },
  querySelectorAll() { return []; },
};
global.location = { pathname: "/meetings/private-id", search: "", hash: "", href: "https://graf.test/meetings/private-id" };
global.history = { replaceState() {} };
global.navigator = { onLine: true };
global.sessionStorage = { removeItem() {} };
global.window = {
  addEventListener() {},
  clearInterval() {},
  clearTimeout() {},
  htmx: null,
  location: global.location,
  matchMedia() { return { matches: false }; },
  requestAnimationFrame(callback) { callback(); },
  setInterval() { throw new Error("share recovery unexpectedly started polling"); },
  setTimeout() { return 1; },
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const xhr = {
  status: 404,
  responseText: JSON.stringify({ code: "meeting_not_found" }),
  responseURL: "https://graf.test/meetings/private-id/share",
  getResponseHeader() { return ""; },
};
const event = {
  detail: { xhr, elt: shareTrigger, target: shareHost, shouldSwap: true },
  target: shareTrigger,
  defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; },
};
for (const handler of listeners.get("htmx:beforeSwap") || []) handler(event);
if (!event.defaultPrevented || event.detail.shouldSwap !== false) throw new Error("share error was allowed to swap");
if (currentMain !== detail || !detail.isConnected) throw new Error("share error removed accessible detail");
if (!shareHost.children[0]?.textContent.includes("Не удалось открыть настройки доступа")) {
  throw new Error("share error did not stay local to the detail");
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_batch_deletion_keeps_success_out_of_visible_feedback_region() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    submit_deletion = script[
        script.index("const submitDeletionForm") : script.index("const requestMeetingListRefresh")
    ]
    deletion_handler = script[
        script.index(
            'const confirm = event.target.closest("[data-delete-confirm]")'
        ) : script.index('const row = event.target.closest("[data-meeting-row]")')
    ]
    request_loop = deletion_handler[
        deletion_handler.index("for (const row of pendingDeleteRows)") : deletion_handler.index(
            "confirm.disabled = false"
        )
    ]

    assert "#delete-feedback-region" not in submit_deletion
    assert "responseDocument" not in submit_deletion
    assert "publishDeletionFeedback" not in request_loop
    assert (
        'document.querySelector("#delete-feedback-region")?.replaceChildren()' in deletion_handler
    )
    assert 'publishDeletionFeedback(failureMessage, "error")' in deletion_handler
    assert "announceDeletionResult" in deletion_handler
    assert "Запись удалена из списка. Очистка данных GRAF продолжается." not in deletion_handler


def test_authorization_disabled_upload_name_keeps_the_visible_label() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "Загрузить запись — недоступно. Войдите снова." in script


def test_cabinet_js_uses_product_facing_ellipsis_in_async_states() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for legacy_copy in [
        '"Удаляем..."',
        '"Загружаем файл..."',
        '"Продолжаем загрузку..."',
        '"Проверяем..."',
    ]:
        assert legacy_copy not in script
    for product_copy in [
        '"Удаляем…"',
        '"Проверяем…"',
    ]:
        assert product_copy in script

    for short_upload_copy in [
        '"Загрузка"',
        '"Загрузка продолжена"',
        '"На сервере · Обрабатываем"',
        '"На сервере · Ждёт обработки"',
        '"Не удалось загрузить"',
        '"Загрузка остановлена"',
    ]:
        assert short_upload_copy in script

    for actionable_upload_error in [
        'empty_media_upload: "Файл пустой"',
        'upload_part_bytes_exceeded: "Файл слишком большой"',
        'unsafe_meeting_title: "Измените название"',
        "uploadFailureMessage(failureCode)",
    ]:
        assert actionable_upload_error in script


def test_cabinet_js_owns_component_dom_behavior() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for marker in [
        "data-code-form",
        "syncRefinementState",
        "auth-leaving",
        "data-delete-dialog",
        "activateDetailTab",
        "data-playback-player",
        "new FormData(form)",
        '"HX-Request": "true"',
        "if (!response.ok)",
        "const response = await fetch(form.action",
        "const failedRows = []",
        "pendingDeleteRows = failedRows",
        "authorizationRecoveryKind",
        "responseProblemCode",
        "[403, 404].includes(response.status)",
        'xhr.getResponseHeader("X-GRAF-Cabinet-Recovery")',
        'response.headers.get("X-GRAF-Cabinet-Recovery")',
        "renderMeetingListRecovery(recoveryKind)",
        'document.querySelector("#delete-feedback-region")?.replaceChildren()',
        'dialog.querySelector("[data-delete-cancel]")?.focus({ preventScroll: true })',
        'deleteDialog?.addEventListener("cancel"',
        'source.matches("[data-upload-progress-poll]")',
        "listInteractionIsActive()",
        "[data-delete-dialog][open], [data-meeting-delete-dialog][open], [data-manual-upload-dialog][open], [data-content-export-dialog][open]",
        "deleteReturnMeetingId",
        "isUsableFocusTarget(deleteReturnFocus)",
        "target.closest(\"[hidden], [aria-hidden='true']\") === null",
        "rowPrimaryFocusTarget(returnRow)",
        "if (!shouldSelectAll) {",
        "rowPrimaryFocusTarget(rows[0])",
        "closeDeleteDialog();",
        'event.key !== "Escape"',
        'openDisclosure.querySelector("summary")?.focus({ preventScroll: true })',
        'event.target.closest("[data-filter-disclosure], [data-sort-disclosure]")',
        "requestMeetingListRefresh",
        "form.requestSubmit();",
        "listRefreshShouldRestoreFocus",
        'selectionToggleLabel.textContent = allSelected ? "Снять выбор" : "Выбрать все"',
        "rowPrimaryFocusTarget",
    ]:
        assert marker in script

    assert "resultCount.textContent = `Найдено: ${allRows().length}`" not in script
    assert "renderClientEmptyList" not in script
    assert "const setRowContextualAvailability" not in script
    assert "event.target !== row" not in script


def test_feature_159_shared_shell_initializers_are_idempotent_and_safe() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for marker in [
        'document.querySelectorAll("[data-cabinet-shell]")',
        'shell.dataset.railReady === "true"',
        "data-profile-menu-trigger",
        "data-profile-menu-ready",
        'event.key === "Escape"',
        "trigger.focus({ preventScroll: true })",
        "Скрыть боковую панель",
        "Показать боковую панель",
    ]:
        assert marker in script


def test_feature_159_shared_shell_static_contract_keeps_search_and_download_boundaries() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    sections = (
        ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html"
    ).read_text()

    assert "padding-inline-start: 42px;" in css
    assert "padding-inline-end: 34px;" in css
    assert ".sidebar-download" in css
    assert "position: fixed;" in css
    assert "max-height: calc(100vh - 24px);" in css
    assert "overflow-y: auto;" in css
    assert 'data-sidebar-download href="/download"' in sections
    assert 'data-sidebar-download href="/download"' not in sections.replace(
        'data-sidebar-download href="/download"', "", 1
    )
    assert "data-graf-app-update" in sections
    assert 'aria-label="{{ item.label }}" title="{{ item.label }}"' in sections
    assert 'aria-label="К встречам" title="К встречам"' in sections
    assert 'aria-label="Обзор" title="Обзор"' in sections


def test_meeting_list_css_keeps_reset_copy_and_touch_actions_visible() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    assert (
        ".cabinet-filter-reset.icon-control {\n"
        "  width: auto;\n"
        "  min-width: 88px;\n"
        "  height: var(--control-height);"
    ) in css
    assert ".cabinet-filter-reset .cabinet-control-label {\n  display: none;\n}" not in css
    assert (
        "@media (hover: none), (pointer: coarse) {\n"
        "  .meeting-row:not(:hover):not(:focus-within):not(.is-selected) .row-select-hit,\n"
        "  .meeting-row:not(:hover):not(:focus-within):not(.is-selected) .row-delete {\n"
        "    opacity: 1;"
    ) in css


def test_collapsed_sidebar_footer_cannot_inherit_the_narrow_hidden_state() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    assert ".desktop-embedded.is-rail-pinned .sidebar" in css
    assert ".desktop-embedded .sidebar:hover" not in css
    assert ".desktop-embedded .sidebar:focus-within" not in css
    assert (
        ".desktop-embedded .sidebar > .primary,\n"
        "  .desktop-embedded .sidebar-foot {\n"
        "    width: calc(var(--app-sidebar-width) - 12px);\n"
        "    display: none;"
    ) not in css
    assert (
        'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:'
        "not(.is-rail-pinned) .sidebar-foot {\n  display: grid;"
    ) in css


def test_sidebar_toggle_tooltip_is_visible_on_hover_and_keyboard_focus() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in (
        ".app-shell[data-cabinet-shell]::after",
        "content: attr(data-rail-tooltip);",
        "position: fixed;",
        "pointer-events: none;",
        ":has(.cabinet-rail-toggle:hover)::after",
        ":has(.cabinet-rail-toggle:focus-visible)::after",
        "max-width: min(220px, calc(100vw - 72px));",
    ):
        assert marker in css


def test_embedded_update_slot_is_accessible_and_native_owned() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in [
        ".sidebar-app-update",
        "min-height: 40px;",
        "color: var(--focus-ring);",
        ".sidebar-app-update:hover",
        ".sidebar-app-update:focus-visible",
        ".sidebar-app-update[hidden]",
    ]:
        assert marker in css


def test_cabinet_js_owns_manual_upload_without_frontend_toolchain() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    css = (STATIC_DIR / "cabinet.css").read_text()
    template = (
        ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html"
    ).read_text()

    for marker in [
        "initManualUpload",
        "XMLHttpRequest",
        "data-manual-upload-dialog",
        "data-manual-upload-dropzone",
        "data-upload-activity-list",
        "data-upload-activity-cancel",
        "data-upload-activity-retry",
        "data-upload-activity-recover",
        "data-upload-activity-resume",
        "data-manual-upload-submit",
        "focusDialogElement",
        'dialog.addEventListener("keydown"',
        'event.key !== "Tab"',
        'document.body.addEventListener("click"',
        "event.preventDefault();",
        "duration_seconds",
        "local_recording_id",
        "X-CSRF-Token",
        "abort",
        "refreshMeetingList",
        "workflow_started",
        "На сервере · Ждёт обработки",
        "На сервере · Обрабатываем",
        "authUploadFailure",
        "conflictUploadFailure",
        "window.location.reload()",
        "dragover",
        "dropEffect",
        "meeting-list-region",
        "announceUploadActivity",
        "announcedProgressBucket",
        "Math.min(99",
        "activity.progress.hidden = !progressActive",
        "activity.percentLabel.hidden = true",
        "await refreshMeetingList();",
        "currentMeetingListUrl",
        "new FormData(form).forEach",
    ]:
        assert marker in script
    for marker in [
        ".manual-upload-dialog",
        ".manual-upload-dropzone",
        ".manual-upload-file-card",
        ".manual-upload-validation",
        ".upload-activity-row",
        ".upload-activity-progress",
        ".upload-activity-actions",
        ".upload-activity-action",
        "color-mix(in srgb, var(--accent)",
        "grid-template-columns: 30px minmax(0, 1fr) auto;",
    ]:
        assert marker in css
    assert '<span class="upload-activity-state">' in script
    assert script.index("data-upload-activity-status") < script.index(
        "data-upload-activity-percent"
    )
    assert script.index("data-upload-activity-percent") < script.index("upload-activity-progress")
    assert "Перетащите файл сюда" not in script
    assert "Длительность не прочитана" in script
    assert 'data-upload-activity-list aria-live="polite"' not in template
    assert (
        'data-upload-activity-announcer role="status" aria-live="polite" aria-atomic="true"'
        in template
    )
    assert "setActivityProgress(activity, 100, true)" not in script
    assert "dialog.dataset.uploadRefreshUrl" not in script
    assert 'durationInput?.addEventListener("input"' not in script
    assert ".manual-upload-duration__control" not in css


def test_manual_upload_keeps_untrusted_progress_indeterminate_and_preserves_list_query_state() -> (
    None
):
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const script = fs.readFileSync(process.argv[1], "utf8");
const progressSource = script.slice(
  script.indexOf("const setActivityProgress"),
  script.indexOf("const setActivityState"),
);
const urlSource = script.slice(
  script.indexOf("const currentMeetingListUrl"),
  script.indexOf("const refreshMeetingList"),
);
global.announceUploadActivity = () => {};
eval(`${progressSource}\n;global.setActivityProgress = setActivityProgress;`);
class FakeClassList {
  toggle() {}
  remove() {}
}
const progress = {
  hidden: false,
  classList: new FakeClassList(),
  attributes: new Set(["aria-valuenow"]),
  removeAttribute(name) { this.attributes.delete(name); },
  setAttribute(name) { this.attributes.add(name); },
};
const activity = {
  progress,
  progressBar: { style: { width: "36%" } },
  percentLabel: { textContent: "36%", hidden: false },
  announcedProgressBucket: null,
};
setActivityProgress(activity, 36, false);
    if (progress.hidden || activity.progressBar.style.width !== "0") {
  throw new Error("untrusted upload progress was not kept visible");
}
if (!activity.percentLabel.hidden || activity.percentLabel.textContent) {
  throw new Error("untrusted upload percentage remained visible");
}
if (progress.attributes.has("aria-valuenow")) {
  throw new Error("untrusted upload progress kept aria-valuenow");
}

class FakeForm {}
const form = new FakeForm();
form.action = "/meetings";
global.HTMLFormElement = FakeForm;
global.location = {
  pathname: "/meetings",
  search: "?limit=1&q=old&status=processing&tenant=private",
  href: "https://graf.test/meetings?limit=1&q=old&status=processing&tenant=private",
};
global.window = { location: global.location };
global.document = {
  querySelector(selector) {
    return selector === ".cabinet-list-controls" ? form : null;
  },
};
global.FormData = class {
  constructor() {
    this.fields = [
      ["q", "new search"],
      ["status", "failed"],
      ["access", ""],
      ["sort", "started_desc"],
    ];
  }
  forEach(callback) {
    this.fields.forEach(([key, value]) => callback(value, key));
  }
};
eval(`${urlSource}\n;global.currentMeetingListUrl = currentMeetingListUrl;`);
const result = global.currentMeetingListUrl();
const query = new URLSearchParams(result.split("?", 2)[1]);
if (query.get("limit") !== "1" || query.get("tenant") !== "private") {
  throw new Error(`refresh dropped existing query state: ${result}`);
}
if (query.get("q") !== "new search" || query.get("status") !== "failed" || query.get("access") !== null || query.get("sort") !== "started_desc") {
  throw new Error(`refresh did not overlay current controls: ${result}`);
}
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_auth_static_assets_keep_compact_panel_and_six_slot_code_autosubmit() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "--auth-content-width: min(100%, 448px)" in css
    assert "width: min(520px, 100%)" in css
    assert "requestSubmit" in script
    assert "data-code-slot" in script
    assert "data-code-hidden" in script
    assert "hidden.disabled = false" in script
    assert 'replace(/\\D/g, "").slice(0, 6)' in script
    assert "isComplete" in script
    assert "fillFromStart" in script
    assert "event.preventDefault()" in script
    assert "submitted = true" in script
    assert (
        "[data-embedded-code-panel],\n"
        "[data-embedded-code-panel] .auth-form > *,\n"
        "[data-embedded-code-panel] .code-slot {\n"
        "  animation: none;\n"
        "}"
    ) in css
    assert ".code-slots {" in css
    assert "grid-template-columns: repeat(6, minmax(0, 1fr));" in css
    assert "aspect-ratio: 1;" in css


def test_auth_code_slots_distribute_digits_and_submit_once() -> None:
    script_path = STATIC_DIR / "cabinet.js"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const script = fs.readFileSync(process.argv[1], "utf8");
const initSource = script.slice(
  script.indexOf("  const initCodeForms = () => {"),
  script.indexOf("  const initOutcomeFocus = () => {"),
);
const timers = [];
const expect = (condition, message) => {
  if (!condition) throw new Error(message);
};
global.window = { setTimeout(callback) { timers.push(callback); } };
global.document = { activeElement: null, querySelectorAll() { return []; } };
const flushTimers = () => {
  while (timers.length) timers.shift()();
};
class FakeInput {
  constructor() {
    this.value = "";
    this.dataset = {};
    this.listeners = new Map();
  }
  addEventListener(name, handler) {
    const handlers = this.listeners.get(name) || [];
    handlers.push(handler);
    this.listeners.set(name, handlers);
  }
  dispatch(name, event = {}) {
    event.target ||= this;
    for (const handler of this.listeners.get(name) || []) handler(event);
    return event;
  }
  focus() { document.activeElement = this; }
}
class FakeForm extends FakeInput {
  constructor() {
    super();
    this.slots = Array.from({ length: 6 }, () => new FakeInput());
    this.hidden = new FakeInput();
    this.hidden.disabled = true;
    this.submitCalls = 0;
  }
  querySelectorAll(selector) {
    return selector === "[data-code-slot]" ? this.slots : [];
  }
  querySelector(selector) {
    return selector === "[data-code-hidden]" ? this.hidden : null;
  }
  requestSubmit() {
    this.submitCalls += 1;
    let prevented = false;
    this.dispatch("submit", {
      preventDefault() { prevented = true; },
    });
    expect(!prevented, "complete code was blocked by submit guard");
  }
}
const form = new FakeForm();
document.querySelectorAll = (selector) => selector === "[data-code-form]" ? [form] : [];
vm.runInThisContext(`${initSource}\nglobal.initCodeForms = initCodeForms;`);
global.initCodeForms();
expect(form.hidden.disabled === false, "hidden code field stayed disabled");
expect(document.activeElement === form.slots[0], "first slot did not receive focus");

form.slots[0].value = "7";
form.slots[0].dispatch("input");
flushTimers();
expect(form.hidden.value === "7", "single digit was not synchronized");
expect(document.activeElement === form.slots[1], "focus did not advance after a digit");

form.slots[1].value = "x";
form.slots[1].dispatch("input");
flushTimers();
expect(form.slots[1].value === "", "non-digit was accepted");

let incompletePrevented = false;
form.dispatch("submit", { preventDefault() { incompletePrevented = true; } });
expect(incompletePrevented, "incomplete submit was not blocked");
expect(document.activeElement === form.slots[1], "incomplete submit did not focus the first empty slot");

form.slots[1].value = "2";
let backspacePrevented = false;
form.slots[1].dispatch("keydown", {
  key: "Backspace",
  preventDefault() { backspacePrevented = true; },
});
expect(backspacePrevented && form.slots[1].value === "", "Backspace did not clear the current slot");
form.slots[1].dispatch("keydown", { key: "Backspace", preventDefault() {} });
expect(form.slots[0].value === "" && document.activeElement === form.slots[0], "Backspace did not move to the previous slot");

let pastePrevented = false;
form.slots[2].dispatch("paste", {
  clipboardData: { getData() { return "a1-2 3foo456789"; } },
  preventDefault() { pastePrevented = true; },
});
flushTimers();
expect(pastePrevented, "paste was not consumed");
expect(form.slots.map((slot) => slot.value).join("") === "123456", "paste did not distribute six digits");
expect(form.hidden.value === "123456", "pasted code was not synchronized");
expect(form.submitCalls === 1, "complete code did not submit exactly once");

form.slots[5].value = "7";
form.slots[5].dispatch("input");
flushTimers();
expect(form.submitCalls === 1, "same form submitted more than once");
form.slots[5].dispatch("keydown", { key: "ArrowLeft", preventDefault() {} });
expect(document.activeElement === form.slots[4], "ArrowLeft navigation failed");
form.slots[4].dispatch("keydown", { key: "Home", preventDefault() {} });
expect(document.activeElement === form.slots[0], "Home navigation failed");
form.slots[0].dispatch("keydown", { key: "End", preventDefault() {} });
expect(document.activeElement === form.slots[5], "End navigation failed");
"""
    completed = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_feature_104_css_uses_shared_density_focus_and_responsive_contracts() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in [
        "--space-1: 8px;",
        "--space-2: 12px;",
        "--space-3: 16px;",
        "--space-4: 24px;",
        "--control-height: 36px;",
        "--meeting-row-height: 48px;",
        "--focus-ring: #b6aaff;",
        "--app-sidebar-width: 240px;",
        "--app-rail-width: 64px;",
        "outline: 2px solid var(--focus-ring);",
        ".meeting-row.cabinet-row:hover,\n.meeting-row.cabinet-row:focus-within",
        "grid-template-columns: var(--app-rail-width) minmax(0, 1fr);",
        "@media (max-width: 1120px)",
        ".manual-upload-trigger > span",
        ".desktop-embedded .cabinet-list-controls .manual-upload-trigger {",
        "grid-column: auto;",
        ".cabinet-workspace-header--brand .cabinet-workspace-header__avatar",
        '[data-icon="panel-left-close"]',
        "@media (prefers-contrast: more)",
        "@media (prefers-reduced-motion: reduce)",
    ]:
        assert marker in css

    assert "min-height: var(--meeting-row-height);" in css
    assert "min-height: var(--control-height);" in css
    assert "overflow-x: hidden" in css
    assert (
        ".desktop-embedded .cabinet-list-controls .manual-upload-trigger {\n"
        "    grid-column: auto;\n"
        "    width: 40px;\n"
        "    min-width: 40px;\n"
        "    padding: 0;\n"
        "  }"
    ) in css
    assert (
        ".desktop-embedded .cabinet-list-controls .manual-upload-trigger {\n"
        "    grid-column: 1 / -1;\n"
        "    width: 100%;\n"
        "  }"
    ) not in css
    assert 'aria-label="Сохраненные"' not in css


def test_feature_191_centralizes_interaction_tokens_and_compact_upload_contract() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    script = (STATIC_DIR / "cabinet.js").read_text()
    manual_upload = (
        ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html"
    ).read_text()

    for token in [
        "--accent-hover:",
        "--accent-solid: #6347d9;",
        "--accent-foreground: #fff;",
        "--sidebar-accent: #8c73ff;",
        "--sidebar-focus-ring: #b6aaff;",
        "--accent-soft:",
        "--accent-surface:",
        "--accent-border:",
        "--success-surface:",
        "--success-border:",
        "--warning-surface:",
        "--warning-border:",
        "--danger-surface:",
        "--danger-border:",
        "--font-size-caption: 11px;",
        "--font-size-helper: 12px;",
        "--font-size-body: 13px;",
        "--font-size-label: 14px;",
        "--control-height-sm: 32px;",
        "--control-height: 36px;",
        "--control-height-lg: 40px;",
        "--radius-control: 7px;",
        "--radius-card: 10px;",
        "--radius-panel: 12px;",
        "--radius-dialog: 16px;",
    ]:
        assert token in css

    assert "accent-color: var(--accent);" in css
    assert "--accent: var(--sidebar-accent);" in css
    assert "--focus-ring: var(--sidebar-focus-ring);" in css
    assert (
        ".primary { background: var(--accent-solid); border-color: var(--accent-solid); "
        "color: var(--accent-foreground);"
    ) in css
    assert "var(--blue)" not in css
    for product_blue in [
        "#2f91ff",
        "#2088ff",
        "rgba(47,145,255",
        "rgba(32,136,255",
        "rgba(92, 155, 235",
    ]:
        assert product_blue not in css.lower()

    assert "grid-template-columns: 30px minmax(0, 1fr) auto;" in css
    assert ".upload-activity-state" in css
    assert '<span class="upload-activity-state">' in script
    assert len(re.findall(r"(?m)^\.settings-overview-card \{", css)) == 1
    assert ".cabinet-sidebar-nav__label" in css
    assert "text-overflow: ellipsis;" in css
    assert "white-space: nowrap;" in css
    for shared_control in [
        ".cabinet-switch",
        ".cabinet-switch__track",
        ".settings-control-row",
        ".theme-picker",
        ".theme-picker__option",
        ".cabinet-tooltip__trigger",
    ]:
        assert shared_control in css
    assert "--switch-width: 36px;" in css
    assert "--switch-height: 20px;" in css
    assert "--switch-thumb: 14px;" in css
    assert ".calendar-settings__topbar h1 {\n  font-size: var(--font-size-page-title);" in css
    assert ".calendar-provider-modal__header h2 {\n  font-size: var(--font-size-section);" in css

    for copy in [
        "Загрузить файл",
        "Аудио или видео с аудиодорожкой.",
        "Перетащите файл",
        "WAV, MP3, M4A, MP4 и другие",
        ">Выбрать<",
        "Сохранить аудио",
        "Без аудио останутся расшифровка и итоги. Минуты тарифа спишутся.",
    ]:
        assert copy in manual_upload
    assert "Перетащите файл сюда" not in manual_upload
    assert "Сохранить аудио для последующего прослушивания" not in manual_upload
    assert "manual-upload-archive-choice" not in manual_upload
    assert "ui.switch(" in manual_upload
    assert 'hint_id="manual-upload-archive-help"' in manual_upload


def test_feature_191_shared_button_contract_keeps_actions_centered_and_on_one_line() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    script = (STATIC_DIR / "cabinet.js").read_text()
    account = (
        ROOT
        / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html"
    ).read_text()
    button_contract = css[css.index("button, .button {") : css.index("button[disabled]")]

    for marker in [
        "align-items: center;",
        "justify-content: center;",
        "line-height: var(--line-height-body);",
        "text-align: center;",
        "white-space: nowrap;",
        "overflow-wrap: normal;",
    ]:
        assert marker in button_contract

    assert script.count('class="button quiet upload-activity-action"') == 5
    assert 'class="upload-activity-action"' not in script
    assert ".settings-list-item > form { flex: 0 0 auto; }" in css
    assert ".calendar-empty-state > .button { flex: 0 0 auto; }" in css
    assert "align-self: flex-start;" in css
    assert (
        ".account-email-form__heading { position: relative; display: flex; flex-wrap: wrap;" in css
    )
    mobile_controls = css[
        css.index("@media (max-width: 620px)") : css.index("@media (max-width: 480px)")
    ]
    assert ".desktop-embedded .cabinet-list-controls .manual-upload-trigger {" in mobile_controls
    assert "min-width: 156px;" in mobile_controls
    assert ".manual-upload-trigger > span {" in mobile_controls
    assert "position: static;" in mobile_controls
    assert ".cabinet-titleline {" in mobile_controls
    assert "flex-direction: column;" in mobile_controls
    assert ".cabinet-titleline h1 { white-space: normal; }" in mobile_controls
    assert ".cabinet-titleline > p { margin: 0; }" in mobile_controls
    calendar_reflow = css[css.index("@media (max-width: 760px)") :]
    assert ".calendar-empty-state {" in calendar_reflow
    assert ".calendar-preference-group {" in calendar_reflow
    assert "grid-template-columns: 1fr;" in calendar_reflow
    assert ".calendar-section-head > .button { align-self: flex-start; }" in calendar_reflow
    for compound_action in [
        ".meeting-action-item {",
        ".summary-format-grid > button {",
        ".calendar-provider-button {",
        ".share-recipient-results button { display: grid;",
        ".sidebar-profile__trigger {\n  width: 100%;",
    ]:
        block = css[css.index(compound_action) : css.index("}", css.index(compound_action))]
        assert "white-space: normal;" in block
    assert ">Завершить<" in account
    assert ">Завершить сеанс<" not in account


def test_feature_191_full_page_states_reuse_one_component_and_standard_actions() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    script = (STATIC_DIR / "cabinet.js").read_text()
    templates = ROOT / "src/twobrain_rec_server/cabinet/templates/cabinet"
    sections = (templates / "components/sections.html").read_text()
    unavailable = (templates / "pages/meeting_unavailable_content.html").read_text()
    invitation = (templates / "pages/share_invitation_content.html").read_text()
    shared = (templates / "pages/shared_with_me_list_content.html").read_text()
    detail = (templates / "pages/meeting_detail_content.html").read_text()
    recovery = script[
        script.index("const renderMeetingDetailRecovery") : script.index(
            "const renderShareRequestError"
        )
    ]

    assert "{% macro state_panel(" in sections
    assert "{% macro full_page_state(" in sections
    assert "sections.full_page_state(" in unavailable
    assert "sections.full_page_state(" in invitation
    assert "sections.state_panel(" in shared
    assert "data-meeting-detail-recovery-template" in detail
    assert "sections.full_page_state(" in detail
    assert 'document.querySelector("[data-meeting-detail-recovery-template]")' in recovery
    assert "cloneNode(true)" in recovery
    assert 'document.createElement("main")' not in recovery
    assert 'document.createElement("section")' not in recovery

    for source in (css, script, unavailable, invitation, shared, detail):
        assert "new-button" not in source
    assert css.count(".empty-state,") == 1
    assert ".desktop-embedded .empty-state" not in css
    for marker in [
        ".cabinet-state-page",
        ".cabinet-state {",
        ".cabinet-state__icon",
        ".cabinet-state__copy",
        ".cabinet-state__action",
        ".cabinet-link--primary",
    ]:
        assert marker in css


def test_meeting_list_css_binds_target_geometry_contrast_and_motion_contracts() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    for marker in [
        "--meeting-row-height: 48px;",
        "--meeting-row-exception-height: 56px;",
        ".meeting-row.has-status {\n  min-height: var(--meeting-row-exception-height);",
        ".meeting-row.has-status .meeting-content {\n  padding-block: 2px;",
        ".row-select-hit,\n.row-delete-form {\n  width: 32px;\n  height: 32px;",
        ".calendar-context-list-action {\n  min-height: 32px;",
        ".meeting-title {",
        "text-overflow: ellipsis;",
        ".meeting-date {",
        "white-space: nowrap;",
        "@media (max-width: 1120px)",
        "@media (max-width: 860px)",
        "@media (hover: none), (pointer: coarse)",
        "@media (prefers-reduced-motion: reduce)",
        "transition-duration: .001ms !important;",
        "@media (forced-colors: active)",
        ".meeting-row.is-selected::before",
        "background: Highlight;",
        "@media (prefers-contrast: more)",
    ]:
        assert marker in css

    assert "html, body { min-height: 100%; margin: 0;" in css
    assert "overflow-x: hidden;" in css
    assert "minmax(0, 1fr)" in css
    assert (
        ".selection-toolbar {\n  min-height: var(--control-height);\n  padding-left: 0;\n  gap: var(--space-1);\n  flex-wrap: wrap;"
        in css
    )
    assert ".selection-clear {\n    display: none;\n  }" not in css
    assert (
        "@media (max-width: 620px) {" in css
        and "grid-template-columns: 32px 20px minmax(0, 1fr) 32px;" in css
        and ".meeting-row.cabinet-row .meeting-date {\n    grid-column: 3 / 5;\n    grid-row: 2;"
        in css
    )
    assert ".meeting-row:hover { transform: translateX(2px); }" not in css
