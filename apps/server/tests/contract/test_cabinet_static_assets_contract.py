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


def test_cabinet_js_keeps_fragment_state_ephemeral() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "htmx:afterSwap" in script
    assert "meeting-list-region" in script
    assert "localStorage" not in script
    assert script.count("sessionStorage") == 7
    assert script.count('sessionStorage.removeItem("htmx-history-cache")') == 1
    assert script.count('sessionStorage.removeItem("htmx-current-path-for-history")') == 2
    assert "graf-summary-candidate-" in script
    assert "sessionStorage.setItem(candidateStorageKey, JSON.stringify({" in script
    assert "poll_url: candidate.poll_url" in script
    assert "template: activeTemplate" in script


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
        'status === 401',
        'status === 403',
        'getResponseHeader?.("X-GRAF-Cabinet-Recovery")',
        'recoveryHeader === "reselect-space"',
        'problemCode === "auth_session_invalid"',
        "accessLossProblemCodes.has(problemCode)",
        "unknownForbiddenMeansAccess",
        "status >= 400 && status < 500",
        'target?.removeAttribute("aria-busy")',
        "current.hidden = false",
        'data-list-retry',
        'data-list-sign-in',
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
        ROOT
        / "src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_list.html"
    ).read_text()
    rendering = (
        ROOT / "src/twobrain_rec_server/cabinet/rendering.py"
    ).read_text()
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
    assert '} else {\n      clearMeetingListAnnouncements();\n    }' in recovery_function

    announcement_clear = script[
        script.index("const clearMeetingListAnnouncements") : script.index(
            "const listInteractionIsActive"
        )
    ]
    assert "meetingResultCountAnnouncementVersion += 1" in announcement_clear
    assert 'document.querySelector("[data-upload-progress-announcer]")?.replaceChildren()' in announcement_clear
    assert 'document.querySelector("[data-upload-activity-announcer]")?.replaceChildren()' in announcement_clear
    assert 'document.querySelector("[data-meeting-result-announcer]")?.replaceChildren()' in announcement_clear
    assert "announcedUploadProgressBuckets.clear()" in announcement_clear

    interaction_guard = script[
        script.index("const listInteractionIsActive") : script.index(
            "const isUsableFocusTarget"
        )
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
        '[403, 404].includes(response.status)',
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

    assert 'const refreshFocusMeetingId = deleteFocusFallbackIds[0]' not in script


def test_meeting_list_js_announces_polled_progress_in_bounded_steps() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()
    template = (
        ROOT
        / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html"
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
        'data-upload-progress-active][data-upload-progress-percent',
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
        '        : "Показана первая часть встреч без поиска и фильтров"'
        in script
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
        (200, "", True, "https://graf.test/meetings/private-id", True),
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
  if (!expectReload && (error.hidden || submit.disabled)) {
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

    assert script.count("recoverMeetingDetailFromResponse(response)") == 3
    assert "summaryActionProblemCodes" in script
    assert "sharingActionProblemCodes" in script
    assert '"meeting_not_found"' in script
    assert "isShareRequest" in script
    assert "renderShareRequestError" in script
    assert "preserveDetail: shareRequest" in script
    assert "meeting-share-action-error" in script
    assert "meetingDetailRecoveredError" in script
    assert script.count(
        "recoverMeetingDetailFromResponse(response, { actionProblemCodes: summaryActionProblemCodes })"
    ) == 2
    assert script.count(
        "recoverMeetingDetailFromResponse(response, { actionProblemCodes: sharingActionProblemCodes })"
    ) == 2
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
        script.index('const confirm = event.target.closest("[data-delete-confirm]")') : script.index(
            'const row = event.target.closest("[data-meeting-row]")'
        )
    ]
    request_loop = deletion_handler[
        deletion_handler.index("for (const row of pendingDeleteRows)") : deletion_handler.index(
            "confirm.disabled = false"
        )
    ]

    assert "#delete-feedback-region" not in submit_deletion
    assert "responseDocument" not in submit_deletion
    assert "publishDeletionFeedback" not in request_loop
    assert 'document.querySelector("#delete-feedback-region")?.replaceChildren()' in deletion_handler
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
        '"Загружаем файл…"',
        '"Продолжаем загрузку…"',
        '"Проверяем…"',
    ]:
        assert product_copy in script


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

    assert 'resultCount.textContent = `Найдено: ${allRows().length}`' not in script
    assert "renderClientEmptyList" not in script
    assert "const setRowContextualAvailability" not in script
    assert 'event.target !== row' not in script


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


def test_collapsed_sidebar_only_expands_through_the_explicit_toggle() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()

    assert ".desktop-embedded.is-rail-pinned .sidebar" in css
    assert ".desktop-embedded .sidebar:hover" not in css
    assert ".desktop-embedded .sidebar:focus-within" not in css
    assert ".desktop-embedded .sidebar-foot {\n    visibility: hidden;\n  }" in css
    assert ".desktop-embedded.is-rail-pinned .sidebar-foot {\n    visibility: visible;\n  }" in css


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
        ROOT
        / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html"
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
        "Обработка ещё не запущена",
        "authUploadFailure",
        "conflictUploadFailure",
        "window.location.reload()",
        "dragover",
        "dropEffect",
        "meeting-list-region",
        "announceUploadActivity",
        "announcedProgressBucket",
        "Math.min(99",
        'activity.progress.hidden = !progressActive',
        'activity.percentLabel.hidden = true',
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
    ]:
        assert marker in css
    assert "Длительность не прочитана" in script
    assert 'data-upload-activity-list aria-live="polite"' not in template
    assert 'data-upload-activity-announcer role="status" aria-live="polite" aria-atomic="true"' in template
    assert "setActivityProgress(activity, 100, true)" not in script
    assert "dialog.dataset.uploadRefreshUrl" not in script
    assert 'durationInput?.addEventListener("input"' not in script
    assert ".manual-upload-duration__control" not in css


def test_manual_upload_hides_untrusted_progress_and_preserves_list_query_state() -> None:
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
if (!progress.hidden || activity.progressBar.style.width !== "0") {
  throw new Error("untrusted upload progress remained visible");
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


def test_auth_static_assets_keep_compact_panel_and_code_autosubmit() -> None:
    css = (STATIC_DIR / "cabinet.css").read_text()
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "--auth-content-width: min(100%, 448px)" in css
    assert "width: min(520px, 100%)" in css
    assert "requestSubmit" in script
    assert "slots.every((target) => target.value.length === 1)" in script
    assert "submitted = true" in script


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
        "--app-sidebar-width: 176px;",
        "--app-rail-width: 64px;",
        "outline: 2px solid var(--focus-ring);",
        ".meeting-row.cabinet-row:hover,\n.meeting-row.cabinet-row:focus-within",
        "grid-template-columns: var(--app-rail-width) minmax(0, 1fr);",
        "@media (max-width: 1120px)",
        ".new-button.manual-upload-trigger > span",
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
    assert ".selection-toolbar {\n  min-height: var(--control-height);\n  padding-left: 0;\n  gap: var(--space-1);\n  flex-wrap: wrap;" in css
    assert ".selection-clear {\n    display: none;\n  }" not in css
    assert (
        "@media (max-width: 620px) {" in css
        and "grid-template-columns: 32px 20px minmax(0, 1fr) 32px;" in css
        and ".meeting-row.cabinet-row .meeting-date {\n"
        "    grid-column: 3 / 5;\n"
        "    grid-row: 2;" in css
    )
    assert ".meeting-row:hover { transform: translateX(2px); }" not in css
