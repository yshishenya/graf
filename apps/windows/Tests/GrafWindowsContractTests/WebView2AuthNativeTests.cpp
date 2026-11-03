// Native T103 regression. Real WebView2Host::attach; no manual latch/nonce wiring.
#include "../../RecApp/Web/WebView2Host.h"
#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Data.Json.h>
#include <windows.h>
#include <appmodel.h>
#include <cstdio>
#include <filesystem>
#include <array>
#include <climits>
#include <cmath>
#include <stdexcept>
#include <utility>

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::Web::WebView2::Core;
using namespace graf::windows;

namespace graf::windows {
// Native test only: delay delivery, never synthesize a browser result or authority.
struct WebView2HistoryNativeFixture {
    std::function<void(std::string, WebView2Host::HistoryRead)> originalRead;
    std::function<void()> originalActivate, pending;
    DWORD uiThread = 0;
    unsigned reads = 0, captures = 0, deliveries = 0, activations = 0;
    bool terminal = false, reset = false, held = false, stopping = false, unexpected = false;
    int capturedResetId = -1;
    std::string capturedResetUrl;

    bool observeActivation(WebView2Host& owner) {
        if (originalActivate || !owner.nativeActivateDocument_) return false;
        originalActivate = owner.nativeActivateDocument_;
        owner.nativeActivateDocument_ = [this] {
            ++activations;
            const auto activate = originalActivate;
            activate(); // Observation only, including an erroneous late activation.
        };
        return true;
    }

    bool install(WebView2Host& owner, bool holdTerminal, bool holdReset = false) {
        if (originalRead || !owner.nativeReadHistory_ || !owner.nativeActivateDocument_) return false;
        uiThread = GetCurrentThreadId();
        terminal = holdTerminal;
        reset = holdReset;
        originalRead = owner.nativeReadHistory_;
        originalActivate = owner.nativeActivateDocument_;
        owner.nativeReadHistory_ = [this, &owner](std::string source, WebView2Host::HistoryRead complete) {
            ++reads;
            const bool capture = captures == 0 && owner.historyStage_ == (reset ?
                WebView2Host::HistoryStage::resetting : terminal ?
                WebView2Host::HistoryStage::accepting : WebView2Host::HistoryStage::selecting);
            const auto read = originalRead;
            read(std::move(source), [this, &owner, capture, complete = std::move(complete)](auto result) mutable {
                if (GetCurrentThreadId() != uiThread) unexpected = true;
                if (!capture || stopping) { complete(std::move(result)); return; }
                if (held || captures || !result) {
                    unexpected = true;
                    complete(std::move(result));
                    return;
                }
                if (reset) {
                    if (owner.historyStage_ != WebView2Host::HistoryStage::resetting || result->entries.size() != 1 ||
                        result->currentIndex != 0) {
                        unexpected = true; complete(std::move(result)); return;
                    }
                    capturedResetId = result->entries[0].id;
                    capturedResetUrl = result->entries[0].url;
                    std::printf("T103_RESET_READBACK_HELD id=%d RESETTING=1 ORIGINAL_RESULT=1\n", capturedResetId);
                }
                ++captures;
                held = true;
                pending = [complete = std::move(complete), result = std::move(result)]() mutable {
                    complete(std::move(result));
                };
                std::printf("T103_HISTORY_REAL_RESULT_HELD terminal=%d\n", int(terminal));
            });
        };
        owner.nativeActivateDocument_ = [this] {
            ++activations;
            const auto activate = originalActivate;
            activate(); // Observation only: never prevent an erroneous early activation.
        };
        return true;
    }

    void deliver() {
        if (GetCurrentThreadId() != uiThread || !held || !pending || deliveries) {
            unexpected = true; return;
        }
        auto complete = std::exchange(pending, {});
        held = false;
        ++deliveries;
        complete(); // Original continuation, original result, once on the original UI thread.
    }

    void restore(WebView2Host& owner) {
        if (!originalRead && !originalActivate) return;
        stopping = true;
        if (originalRead) owner.nativeReadHistory_ = std::exchange(originalRead, {});
        owner.nativeActivateDocument_ = std::exchange(originalActivate, {});
        if (held) deliver(); // The host remains alive until its real continuation is settled.
    }

    bool selecting(WebView2Host const& owner) const {
        return held && owner.historyStage_ == WebView2Host::HistoryStage::selecting && owner.navigationId_ == 0;
    }
    bool accepting(WebView2Host const& owner, std::uint64_t navigation) const {
        return held && owner.historyStage_ == WebView2Host::HistoryStage::accepting &&
            owner.navigationId_ == navigation && owner.documentResponse_.has_value() &&
            owner.documentCompletion_.has_value() && !owner.historyTerminalValidated_ && owner.documentNonce_.empty();
    }
    bool resetting(WebView2Host const& owner) const {
        return held && owner.historyStage_ == WebView2Host::HistoryStage::resetting && owner.navigationId_ == 0 &&
            owner.historyNeedsReset_ && owner.documentNonce_.empty();
    }
    bool resetRevoked(WebView2Host const& owner) const {
        return owner.historyStage_ == WebView2Host::HistoryStage::idle && owner.navigationId_ == 0 &&
            owner.historyNeedsReset_ && owner.historySingleForward_.empty() && !owner.history_.current() &&
            owner.documentNonce_.empty();
    }
    bool resetRecovered(WebView2Host const& owner) const {
        return owner.historyStage_ == WebView2Host::HistoryStage::idle && !owner.historyNeedsReset_ &&
            owner.historySingleForward_.empty() && owner.history_.currentIsGet(owner.policy_);
    }
    std::array<std::uint64_t, 3> boundary(WebView2Host const& owner) const {
        return {owner.historySession_, owner.historyOperation_, owner.history_.revision()};
    }
    bool navigatingWithoutResponse(WebView2Host const& owner, std::uint64_t navigation) const {
        return navigation != 0 && owner.navigationId_ == navigation && owner.historyNavigation_ == navigation &&
            owner.historyStage_ == WebView2Host::HistoryStage::navigating &&
            owner.runtimeState_ == WebRuntimeState::initializing && owner.documentNonce_.empty() &&
            !owner.documentResponse_ && !owner.documentCompletion_;
    }
    bool account(WebView2Host const& owner, std::string const& token, bool workspaceB) const {
        const auto& value = owner.userTimeAccount_;
        return !token.empty() && value.origin == owner.policy_.trustedOrigin() &&
            value.user == "11111111-1111-4111-8111-111111111111" &&
            value.workspace == (workspaceB ? "55555555-5555-4555-8555-555555555555" : "22222222-2222-4222-8222-222222222222") &&
            value.token == token && value.authGeneration == 1;
    }
};

struct ProtectedUploadQueueValueTestPeer {
    static std::shared_ptr<const ProtectedUploadQueueValue> inventory(bool workspaceB = false) {
        auto value = std::shared_ptr<ProtectedUploadQueueValue>(new ProtectedUploadQueueValue);
        for (unsigned n = 0; n != 301; ++n) {
            ProtectedUploadQueueValue::Item row;
            row.localRecordingId = (workspaceB ? "synthetic-workspaceB-" : "synthetic-protected-") + std::to_string(n);
            row.ownerUserId = n == 300 ? "44444444-4444-4444-8444-444444444444" : "11111111-1111-4111-8111-111111111111";
            row.ownerWorkspaceId = workspaceB ? "55555555-5555-4555-8555-555555555555" : "22222222-2222-4222-8222-222222222222";
            value->items_.push_back(std::move(row));
        }
        return value;
    }
};
}

namespace {
std::wstring profilePath;
std::string origin;
std::string scenario;
std::string initialPath = "/desktop/meetings";
std::string loginNext = "/login?next=%2Fdesktop%2Fmeetings";
int probeExit = 2;
bool completionFailureDiagnostic = false;

bool emailScenario() {
    return scenario == "email503" || scenario == "email429" || scenario == "email-json503";
}

bool historyEntryScenario() { return scenario == "history-entry" || scenario == "history-entry-same-url"; }
bool historySameUrlScenario() { return scenario == "history-entry-same-url" || scenario == "history-host-same-url"; }
bool historyCancelScenario() { return scenario == "cancel-history-host" || scenario == "cancel-history-script"; }
bool sameDocumentScenario() { return scenario == "history-same-document"; }
bool historyRaceScenario() { return scenario == "history-race-native-first" || scenario == "history-race-script-first"; }
bool historyResetScenario() { return scenario == "history-reset"; }
bool freshLoginScenario() { return scenario == "history-fresh-login-redirect"; }
bool staleResetScenario() { return scenario == "history-reset-stale-readback"; }
bool accountBoundaryScenario() { return scenario == "history-reset-account-boundary"; }
bool redirectHeldScenario() { return scenario == "history-account-boundary-redirect-held"; }
bool accountHistoryScenario() { return accountBoundaryScenario() || redirectHeldScenario(); }
bool heldResetScenario() { return staleResetScenario() || accountBoundaryScenario(); }
bool controlledHistoryScenario() { return scenario == "history-pending-read-fence" || scenario == "history-terminal-held"; }
bool fullGetHistoryScenario() { return scenario == "history-get" || scenario == "history-get-repeated-url"; }
bool productionHistoryScenario() { return scenario == "history-host-get" || scenario == "history-host-quarantine" ||
    scenario == "history-host-ordinary-back" ||
    fullGetHistoryScenario() || scenario == "history-post" || scenario == "history-host-same-url" || controlledHistoryScenario() || heldResetScenario() || redirectHeldScenario(); }
bool quarantineHistoryScenario() { return scenario == "history-host-quarantine" || scenario == "history-post" || scenario == "history-host-same-url" || heldResetScenario() || redirectHeldScenario(); }
bool retainedHistoryScenario() { return historyCancelScenario() || historyEntryScenario(); }
bool historyControlScenario() { return historyCancelScenario() || sameDocumentScenario(); }
bool historyScenario() { return scenario == "history-get" || scenario == "history-post" || historyEntryScenario() || historySameUrlScenario() || historyControlScenario() || historyRaceScenario() || historyResetScenario(); }

unsigned targetStatus() {
    if (scenario == "login400" || scenario == "login-post400") return 400;
    if (scenario == "login429" || scenario == "email429") return 429;
    if (scenario == "email503" || scenario == "email-json503" || scenario == "cabinet503") return 503;
    if (scenario == "tls-failure" || scenario == "transport-reset") return 0;
    return 200;
}

bool sameAbsolutePath(std::wstring_view left, std::wstring_view right) {
    const auto canonical = [](std::wstring_view input) {
        std::wstring value(input);
        wchar_t full[32768]{};
        const auto size = GetFullPathNameW(value.c_str(), 32768, full, nullptr);
        if (!size || size >= 32768) return std::wstring{};
        value.assign(full, size);
        while (value.size() > 3 && (value.back() == L'\\' || value.back() == L'/')) value.pop_back();
        return value;
    };
    const auto a = canonical(left), b = canonical(right);
    return !a.empty() && !b.empty() && CompareStringOrdinal(a.c_str(), -1, b.c_str(), -1, TRUE) == CSTR_EQUAL;
}

bool sameDirectoryIdentity(const std::wstring& left, const std::wstring& right) {
    const auto info = [](const std::wstring& path, BY_HANDLE_FILE_INFORMATION& result) {
        const auto handle = CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS, nullptr);
        if (handle == INVALID_HANDLE_VALUE) return false;
        const auto ok = GetFileInformationByHandle(handle, &result);
        CloseHandle(handle);
        return ok != FALSE;
    };
    BY_HANDLE_FILE_INFORMATION a{}, b{};
    return info(left, a) && info(right, b) && a.dwVolumeSerialNumber == b.dwVolumeSerialNumber &&
        a.nFileIndexHigh == b.nFileIndexHigh && a.nFileIndexLow == b.nFileIndexLow;
}

struct ProbeApp : ApplicationT<ProbeApp> {
    Window window{nullptr};
    Grid panel{nullptr};
    WebView2 view{nullptr};
    CoreWebView2Environment environment{nullptr};
    Microsoft::UI::Dispatching::DispatcherQueueTimer timer{nullptr};
    std::unique_ptr<WebView2Host> host;
    ULONGLONG began = 0;
    ULONGLONG closingAt = 0;
    std::atomic_bool closing{false};
    std::atomic_int browserExit{0}; // 0 pending, 1 normal after close, 2 unexpected.
    winrt::event_token browserExitToken{};
    bool exitSubscribed = false;
    bool profileVerified = false, scriptPending = false, emailStarted = false;
    bool formSubmitted = false;
    unsigned historyPhase = 0, historyExpectedCompletions = 1;
    unsigned cancelPhase = 0, authCallbacksBeforeCancel = 0;
    std::uint64_t cancelledNavigationId = 0, generationBeforeCancel = 0;
    bool cancelBridgeRequested = false;
    unsigned startsBeforeCancel = 0, completionsBeforeCancel = 0;
    unsigned controlEntryCount = 0, controlEntryIndex = 0;
    std::uint64_t controlDocumentNavigationId = 0;
    int controlReplacedEntryId = -1;
    bool controlEntryVerified = false, controlLostAuthority = false;
    bool historyEntryCommandAck = false;
    std::uint64_t lastStartedNavigationId = 0, lastCompletedNavigationId = 0;
    std::array<int, 3> historyEntryIds{-1, -1, -1};
    struct RaceNavigation {
        std::uint64_t id = 0;
        bool completed = false, loaded = false, success = false;
        CoreWebView2WebErrorStatus error = CoreWebView2WebErrorStatus::Unknown;
    };
    std::array<RaceNavigation, 2> raceNavigations{};
    WebView2HistoryNativeFixture historyFixture;
    std::array<RaceNavigation, 3> heldCompetitors{};
    unsigned heldAttempt = 0, heldRetainedDispatches = 0;
    unsigned heldAuth = 0, heldCookieReads = 0, heldSignedOut = 0, heldUpdates = 0;
    std::uint64_t heldGeneration = 0;
    bool heldCommandAck = false, heldDocumentVerified = false, heldButtonRequested = false;
    bool heldAttemptSent = false, heldRepeatedNative = false;
    unsigned staleResetPhase = 0;
    int staleResetEntryId = -1;
    bool staleRecoveryVerified = false;
    std::uint64_t staleResetGeneration = 0, staleResetNavigation = 0;
    std::string accountCookieToken;
    std::array<std::uint64_t, 3> accountBoundaryBefore{}, accountBoundaryAfter{};
    ULONGLONG accountBoundAt = 0, accountUnavailableAt = 0;
    bool accountTerminalLost = false;
    RaceNavigation redirectHeldNavigation;
    unsigned redirectHeldPhase = 0, redirectHeldResponses = 0, redirectLoginAttempts = 0;
    bool redirectHeldRequest = false, redirectHeldStarting = false, redirectReleased = false;
    ULONGLONG raceStartedAt = 0;
    int raceGetEntryId = -1;
    unsigned raceStarts = 0, raceCommands = 0;
    bool raceNativeAck = false, raceScriptFromC = false, raceUnexpected = false, raceUnsafe = false;
    std::uint64_t historyPreviousGeneration = 0;
    struct ResetDocument {
        std::uint64_t navigation = 0, generation = 0;
        unsigned responses = 0;
        bool get = false, post = false, loaded = false;
    } resetDocument;
    std::array<ResetDocument, 3> freshLoginDocuments{}; // C200, list302, login200; real native observations only.
    unsigned freshLoginPhase = 0, freshLoginAuth = 0, freshLoginCookieReads = 0, freshLoginSignedOut = 0;
    unsigned freshLoginInvalidations = 0;
    std::uint64_t freshLoginRedirectGeneration = 0;
    ULONGLONG freshLoginEditedAt = 0;
    bool resetPending = false, resetCaptured = false, resetVerified = false, resetLostAuthority = false;
    bool resetBridgeAwaiting = false;
    unsigned resetStarts = 0, resetCompletions = 0, resetAuthCallbacks = 0;
    std::uint64_t resetGeneration = 0, resetNavigation = 0;
    int resetEntryId = -1, resetForwardId = -1;
    bool productionCommitPending = false, productionPostSeen = false;
    int productionCommittedId = -1;
    bool recoveryActionRequested = false;
    ULONGLONG recoveryObservedAt = 0;
    unsigned starts = 0, completions = 0, observedStatus = 0;
    unsigned authCallbacks = 0;
    unsigned currentCookieReads = 0, signedOutObservations = 0, authInvalidations = 0;
    unsigned authCallbacksBeforeEmail = 0;
    std::uint64_t emailNavigationId = 0;
    bool sawEmail503 = false;
    CoreWebView2WebErrorStatus observedError = CoreWebView2WebErrorStatus::Unknown;
    bool observedSuccess = false;
    bool saw401 = false, sawTargetStatus = false;
    unsigned updatePhase = 0, updateCallbacks = 0;
    unsigned localDurationPhase = 0;
    unsigned inventoryPhase = 0;
    std::shared_ptr<const ProtectedUploadQueueValue> inventoryValue;
    std::optional<CustodyBytes> inventoryQuota;
    std::uint64_t inventoryRevision = 0;
    unsigned teardownErrors = 0;

    void traceTeardown(const char* stage) const {
        if (!completionFailureDiagnostic) return;
        std::printf("T103_TEARDOWN stage=%s errors=%u\n", stage, teardownErrors);
        std::fflush(stdout);
    }

    std::filesystem::path responseMarker(const wchar_t* name) const {
        return std::filesystem::path(profilePath).parent_path() / name;
    }
    bool responseMarkerExists(const wchar_t* name) const {
        const auto attributes = GetFileAttributesW(responseMarker(name).c_str());
        return attributes != INVALID_FILE_ATTRIBUTES && !(attributes & FILE_ATTRIBUTE_DIRECTORY);
    }
    bool releaseRedirectResponse() {
        const auto path = responseMarker(L"response-release");
        const auto file = CreateFileW(path.c_str(), GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
            nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) return false;
        redirectReleased = CloseHandle(file) != 0;
        return redirectReleased;
    }

    void finish(bool pass, const char* reason) {
        if (probeExit != 2) return;
        if (redirectHeldScenario() && responseMarkerExists(L"unexpected-http")) {
            pass = false; reason = "held-redirect-server-received-unexpected-get";
        }
        if (redirectHeldScenario() && !releaseRedirectResponse()) { pass = false; reason = "held-redirect-release-write"; }
        probeExit = pass ? 0 : 1;
        std::printf("T103_NATIVE case=%s result=%s reason=%s profile_verified=%d starts=%u completions=%u status=%u state=%d\n",
            scenario.c_str(), pass ? "PASS" : "FAIL", reason, int(profileVerified), starts,
            completions, observedStatus, host ? int(host->runtimeState()) : -1);
        std::fflush(stdout);
        std::printf("T116_AUTH_OBSERVATIONS current_reads=%u signed_out=%u invalidations=%u\n",
            currentCookieReads, signedOutObservations, authInvalidations);
        std::fflush(stdout);
        closingAt = GetTickCount64();
        closing.store(true);
        try { if ((controlledHistoryScenario() || heldResetScenario() || redirectHeldScenario()) && host) historyFixture.restore(*host); } catch (...) { ++teardownErrors; probeExit = 1; }
        traceTeardown("host-close-enter");
        try { if (host) host->close(); } catch (...) { ++teardownErrors; probeExit = 1; }
        traceTeardown("host-close-return");
        try { if (view) view.Close(); } catch (...) { ++teardownErrors; probeExit = 1; }
        traceTeardown("view-close-return");
        // Keep the UI dispatcher alive until this isolated browser has released
        // its profile. Exiting the host process is not that acknowledgement.
        if (environment && timer) return;
        exitProbe();
    }

    void exitProbe() {
        if (timer) timer.Stop();
        try {
            if (exitSubscribed) environment.BrowserProcessExited(browserExitToken);
            exitSubscribed = false;
        } catch (...) { ++teardownErrors; probeExit = 1; }
        try { if (window) window.Close(); } catch (...) { ++teardownErrors; probeExit = 1; }
        traceTeardown("terminal");
        Exit();
    }

    void checkUpdateBadge() {
        const auto generation = host->documentGeneration();
        const auto phase = updatePhase;
        const auto dispatcher = view.DispatcherQueue();
        std::wstring script = LR"JS((() => {
          let button = document.getElementById('synthetic-update');
        )JS";
        if (phase == 0) script += LR"JS(
          if (button) throw new Error('synthetic-update-already-exists');
          button = document.createElement('button');
          button.id = 'synthetic-update'; button.type = 'button';
          button.setAttribute('data-graf-app-update', '');
          button.textContent = 'Synthetic update';
          document.body.append(button);
          document.dispatchEvent(new CustomEvent('htmx:afterSwap'));
        )JS";
        if (phase == 2) script += LR"JS(
          if (!button) throw new Error('synthetic-update-missing');
          const replacement = document.createElement('button');
          replacement.id = 'synthetic-update'; replacement.type = 'button';
          replacement.setAttribute('data-graf-app-update', '');
          replacement.hidden = true;
          const label = document.createElement('span');
          label.textContent = 'Synthetic replacement'; replacement.append(label);
          button.replaceWith(replacement); button = replacement;
          document.dispatchEvent(new CustomEvent('htmx:afterSwap'));
        )JS";
        script += LR"JS(
          if (!button) return false;
          const rect = button.getBoundingClientRect();
          const style = getComputedStyle(button);
          const visible = !button.hidden && !button.disabled && rect.width > 0 && rect.height > 0 &&
            style.display !== 'none' && style.visibility !== 'hidden';
        )JS";
        if (phase == 3) script += LR"JS(
          if (!visible || !button.firstElementChild) return false;
          button.firstElementChild.click();
        )JS";
        script += (phase == 0 || phase == 5)
            ? L"return button.hidden && rect.width === 0 && rect.height === 0 && style.display === 'none';})()"
            : L"return visible;})()";
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(script).Completed(
            [this, generation, phase, dispatcher](auto const& operation, auto const&) {
                dispatcher.TryEnqueue([this, generation, phase, operation] {
                    scriptPending = false;
                    if (probeExit != 2 || generation != host->documentGeneration() || phase != updatePhase) return;
                    try {
                        if (host->runtimeState() != WebRuntimeState::ready) { finish(false, "update-lost-ready"); return; }
                        if (operation.GetResults() != L"true") {
                            // Native availability changes run asynchronously; the existing deadline bounds polling.
                            if (phase == 1 || phase == 5) return;
                            finish(false, "update-dom-state"); return;
                        }
                        if (updateCallbacks > 1 || (phase < 3 && updateCallbacks != 0)) {
                            finish(false, "update-dispatch-count"); return;
                        }
                        if (phase == 4 && updateCallbacks == 0) return;
                        std::printf("T112_UPDATE_PHASE=%u CALLBACKS=%u\n", phase, updateCallbacks);
                        ++updatePhase;
                        if (phase == 0) host->setAppUpdateAvailable(true);
                        if (phase == 4) host->setAppUpdateAvailable(false);
                        if (phase == 5) {
                            if (updateCallbacks != 1) { finish(false, "update-dispatch-missing"); return; }
                            std::puts("T112_UPDATE_DOM_DISPATCH=PASS CALLBACKS=1");
                        }
                    } catch (...) { finish(false, "update-dom-script"); }
                });
            });
    }

    void checkLocalDurations() {
        const auto generation = host->documentGeneration();
        const auto phase = localDurationPhase;
        const auto dispatcher = view.DispatcherQueue();
        const auto script = phase == 0 ? LR"JS((() => {
          if (window.__syntheticLocalDuration) return 0;
          window.__syntheticLocalDuration = {count:0, bits:0};
          chrome.webview.addEventListener('message', e => {
            if (e.data?.command !== 'local_recordings') return;
            const state = window.__syntheticLocalDuration;
            ++state.count; state.bits = 0;
            const rows = e.data.rows;
            if (!Array.isArray(rows) || rows.length !== 1 || rows[0].id !== 'synthetic-duration') return;
            const row = rows[0];
            if (!Object.hasOwn(row, 'durationSeconds') && !Object.hasOwn(row, 'sessionDurationSeconds') && row.showsPartialDuration === false) state.bits = 1;
            if (!Object.hasOwn(row, 'durationSeconds') && typeof row.sessionDurationSeconds === 'number' && row.sessionDurationSeconds === 63 && row.showsPartialDuration === false) state.bits = 2;
            if (Object.hasOwn(row, 'durationSeconds') && Object.hasOwn(row, 'sessionDurationSeconds') && typeof row.durationSeconds === 'number' && typeof row.sessionDurationSeconds === 'number' && row.durationSeconds === 0 && row.sessionDurationSeconds === 0 && row.showsPartialDuration === false) state.bits = 4;
          });
          return 1;
        })())JS" : (L"(() => { const s=window.__syntheticLocalDuration; if(!s) return 0; if(s.count<" +
            std::to_wstring(phase) + L") return -1; return s.count===" + std::to_wstring(phase) +
            L" && s.bits===" + std::to_wstring(phase == 2 ? 2 : phase == 3 ? 4 : 1) + L" ? 1 : 0; })()");
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(script).Completed(
            [this, generation, phase, dispatcher](auto const& operation, auto const&) {
                dispatcher.TryEnqueue([this, generation, phase, operation] {
                    scriptPending = false;
                    if (probeExit != 2 || generation != host->documentGeneration() || phase != localDurationPhase) return;
                    try {
                        if (host->runtimeState() != WebRuntimeState::ready) { finish(false, "duration-lost-ready"); return; }
                        const auto result = operation.GetResults();
                        if (result == L"-1") return; // Await this phase's actual message, bounded by the existing deadline.
                        if (result != L"1") { finish(false, "duration-wire-fields"); return; }
                        std::printf("T116_LOCAL_DURATION_PHASE=%u PASS=1\n", phase);
                        ++localDurationPhase;
                        if (localDurationPhase == 5) { std::puts("T116_LOCAL_DURATION_WIRE=PASS CASES=4"); return; }
                        WebViewLocalRecordingRow row;
                        row.id = "synthetic-duration";
                        if (localDurationPhase == 2)
                            WebView2Host::applyLocalPackageTiming(row, 1'789722300000ULL, 1'789722363000ULL, true);
                        if (localDurationPhase == 3) {
                            row.durationSeconds = 0;
                            WebView2Host::applyLocalPackageTiming(row, 0, 0, true);
                        }
                        host->setLocalRecordings({std::move(row)});
                    } catch (...) { finish(false, "duration-script"); }
                });
            });
    }

    void checkProtectedInventory() {
        const auto phase = inventoryPhase;
        if (phase == 4 && host->userTimeRevision() <= inventoryRevision) return;
        const auto generation = host->documentGeneration();
        const auto dispatcher = view.DispatcherQueue();
        if (phase == 3) host->setProtectedLocalRecordings(inventoryValue, false, origin,
            "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", 1);
        const auto script = phase == 0 ? LR"JS((() => {
          window.__syntheticInventory = null;
          window.__syntheticInventoryCount = 0;
          window.GRAFLocalRecordings = {update(rows, operations, recovery, state) { window.__syntheticInventoryConsumer = {rows, operations, state}; }};
          chrome.webview.addEventListener('message', e => {
            if (e.data?.command === 'local_recordings' && Object.hasOwn(e.data, 'state')) {
              ++window.__syntheticInventoryCount;
              window.__syntheticInventory = e.data;
              if (e.data.rows?.some(r => r.id.startsWith('synthetic-workspaceB-'))) window.__syntheticBLeak = true;
            }
          });
          return 1;
        })())JS" : phase == 1 ? LR"JS((() => {
          const m = window.__syntheticInventory;
          if (!m || m.state !== 'ready') return -1;
          return JSON.stringify(m).length > 65536 && m.rows.length === 300 && m.rows.every((r,i) => r.id === 'synthetic-protected-'+i &&
            r.title === 'Запись' && r.status === 'Ожидает отправки' &&
            r.canOpen === true && r.canSend === true && r.canDelete === false &&
            !Object.hasOwn(r,'durationSeconds') && !Object.hasOwn(r,'startedAt') && !Object.hasOwn(r,'progressPercent')) ? 1 : 0;
        })())JS" : phase == 2 ? LR"JS((() => {
          const m = window.__syntheticInventoryConsumer;
          if (!m || m.state !== 'unavailable') return -1;
          return m.rows.length === 0 ? 1 : 0;
        })())JS" : phase == 3 ? LR"JS((() => {
          const m = window.__syntheticInventory;
          if (!m || m.state !== 'checking') return -1;
          window.__syntheticBeforeBCount = window.__syntheticInventoryCount;
          return m.rows.length === 300 ? 1 : 0;
        })())JS" : LR"JS((() => {
          const m = window.__syntheticInventory;
          if (!m || window.__syntheticInventoryCount < window.__syntheticBeforeBCount + 3) return -1;
          return m.state === 'checking' && m.rows.length === 0 && m.operations.length === 0 && !window.__syntheticBLeak &&
            document.querySelector('meta[name="graf-workspace"]').content === '22222222-2222-4222-8222-222222222222' ? 1 : 0;
        })())JS";
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(script).Completed([this, phase, generation, dispatcher](auto const& operation, auto const&) {
            dispatcher.TryEnqueue([this, phase, generation, operation] {
                scriptPending = false;
                if (probeExit != 2 || generation != host->documentGeneration() || phase != inventoryPhase) return;
                try {
                    const auto result = operation.GetResults();
                    if (result == L"-1") return;
                    if (result != L"1") {
                        std::printf("T116_INVENTORY_FAILED_PHASE=%u\n", phase);
                        finish(false, "protected-inventory-wire"); return;
                    }
                    ++inventoryPhase;
                    if (phase == 0) {
                        inventoryValue = ProtectedUploadQueueValueTestPeer::inventory();
                        host->setProtectedLocalRecordings(inventoryValue, true,
                            origin, "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", 1);
                    }
                    if (phase == 1) {
                        inventoryQuota.emplace();
                        inventoryQuota->resize(CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes());
                        host->setProtectedLocalRecordings(inventoryValue, false, origin,
                            "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", 1);
                    }
                    if (phase == 2) inventoryQuota.reset();
                    if (phase == 3) {
                        host->bindUserTimeAccount(origin, "11111111-1111-4111-8111-111111111111",
                            "55555555-5555-4555-8555-555555555555", "synthetic-inventory-session", 2);
                        inventoryRevision = host->userTimeRevision();
                        host->setProtectedLocalRecordings(ProtectedUploadQueueValueTestPeer::inventory(true), true, origin,
                            "11111111-1111-4111-8111-111111111111", "55555555-5555-4555-8555-555555555555", 2);
                    }
                    if (phase == 4) std::puts("T116_PROTECTED_INVENTORY_WIRE=PASS ROWS=300 FOREIGN=0 STALE=0 ACTIONS=0 QUOTA_RETRY=1");
                } catch (...) { finish(false, "protected-inventory-script"); }
            });
        });
    }

    void runHistoryControlScript(std::wstring_view script) {
        const auto queue = view.DispatcherQueue();
        const auto phase = cancelPhase;
        const auto generation = host->documentGeneration();
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(script).Completed([this, queue, phase, generation](auto const& command, auto const&) {
            queue.TryEnqueue([this, command, phase, generation] {
                scriptPending = false;
                if (probeExit != 2 || phase != cancelPhase || generation != host->documentGeneration()) return;
                try { if (command.GetResults() != L"true") finish(false, "history-control-script"); }
                catch (...) { finish(false, "history-control-script"); }
            });
        });
    }

    bool heldHistoryOwner() const {
        if (historyFixture.unexpected || historyFixture.captures != 1 || historyFixture.deliveries ||
            historyFixture.activations || authCallbacks != heldAuth || currentCookieReads != heldCookieReads ||
            signedOutObservations != heldSignedOut || authInvalidations || updateCallbacks < heldUpdates ||
            updateCallbacks > heldUpdates + heldRetainedDispatches) return false;
        const bool terminal = scenario == "history-terminal-held";
        const auto expected = origin + (terminal ? "/desktop/meetings/11111111-1111-4111-8111-111111111111" :
            "/desktop/meetings/33333333-3333-4333-8333-333333333333");
        if (host->currentUrl() != expected || to_string(view.CoreWebView2().Source()) != expected) return false;
        if (!terminal) return historyFixture.selecting(*host) && host->runtimeState() == WebRuntimeState::ready &&
            host->documentGeneration() == heldGeneration && starts == 3 && completions == 3;
        return historyFixture.accepting(*host, resetDocument.navigation) && host->runtimeState() != WebRuntimeState::ready &&
            resetDocument.get && !resetDocument.post && resetDocument.responses == 1 && resetDocument.loaded &&
            resetDocument.generation == host->documentGeneration() && resetDocument.generation > heldGeneration &&
            lastStartedNavigationId == resetDocument.navigation && lastCompletedNavigationId == resetDocument.navigation &&
            starts == 4 && completions == 4 && observedSuccess && observedStatus == 200;
    }

    void runHeldHistoryScript(std::wstring_view script) {
        heldCommandAck = false;
        scriptPending = true;
        const auto queue = view.DispatcherQueue();
        view.CoreWebView2().ExecuteScriptAsync(script).Completed([this, queue](auto const& operation, auto const&) {
            queue.TryEnqueue([this, operation] {
                scriptPending = false;
                if (probeExit != 2) return;
                try {
                    if (!heldHistoryOwner() || operation.GetResults() != L"true") {
                        finish(false, "held-real-script-or-owner"); return;
                    }
                    heldCommandAck = true;
                } catch (...) { finish(false, "held-real-script"); }
            });
        });
    }

    void inspectHeldHistoryDocument() {
        const bool terminal = scenario == "history-terminal-held";
        const auto queue = view.DispatcherQueue();
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(LR"JS((()=>{
          const m=document.getElementById('synthetic-marker');
          return ['history-a','history-b','history-c'].indexOf(m?.dataset.kind)+1+
            (m?.dataset.postAccepted==='1'?64:0);
        })())JS").Completed([this, queue, terminal](auto const& operation, auto const&) {
            queue.TryEnqueue([this, operation, queue, terminal] {
                if (probeExit != 2) { scriptPending = false; return; }
                try {
                    if (!heldHistoryOwner() || operation.GetResults() != (terminal ? L"2" : L"3"))
                        throw std::runtime_error("synthetic-held-dom");
                    view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
                        .Completed([this, queue, terminal](auto const& snapshot, auto const&) {
                            queue.TryEnqueue([this, snapshot, terminal] {
                                scriptPending = false;
                                if (probeExit != 2) return;
                                try {
                                    if (!heldHistoryOwner()) throw std::runtime_error("synthetic-held-owner");
                                    const auto result = Windows::Data::Json::JsonObject::Parse(snapshot.GetResults());
                                    const auto entries = result.GetNamedArray(L"entries");
                                    if (entries.Size() != 3 || result.GetNamedNumber(L"currentIndex") != (terminal ? 1 : 2))
                                        throw std::runtime_error("synthetic-held-shape");
                                    for (unsigned i = 0; i < 3; ++i) {
                                        const auto entry = entries.GetObjectAt(i);
                                        if (entry.GetNamedNumber(L"id") != historyEntryIds[i] ||
                                            to_string(entry.GetNamedString(L"url")) != productionHistoryPageUrl(i + 1))
                                            throw std::runtime_error("synthetic-held-entry");
                                    }
                                    heldDocumentVerified = true;
                                    std::printf("T103_HISTORY_HELD_ID_DOM_VERIFIED terminal=%d\n", int(terminal));
                                } catch (...) { finish(false, "held-actual-entry-or-owner"); }
                            });
                        });
                } catch (...) { scriptPending = false; finish(false, "held-actual-document"); }
            });
        });
    }

    void checkHeldHistory() {
        if (!heldHistoryOwner()) { finish(false, "held-early-authority-or-owner"); return; }
        const bool terminal = scenario == "history-terminal-held";
        if (!terminal && !heldRepeatedNative) {
            heldRepeatedNative = true;
            const auto readsBefore = historyFixture.reads;
            host->back(); host->forward(); // Must not create another native intent/read.
            if (historyFixture.reads != readsBefore || !heldHistoryOwner()) {
                finish(false, "held-second-native-intent"); return;
            }
        }
        if (!terminal && heldAttempt < heldCompetitors.size()) {
            if (!heldAttemptSent) {
                heldAttemptSent = true;
                if (heldAttempt == 0) runHeldHistoryScript(LR"JS((()=>{
                  if(document.getElementById('synthetic-marker')?.dataset.kind!=='history-c')return false;
                  history.go(-1);return true;
                })())JS");
                else if (heldAttempt == 1) runHeldHistoryScript(LR"JS((()=>{
                  if(document.getElementById('synthetic-marker')?.dataset.kind!=='history-c')return false;
                  location.assign('/desktop/meetings/11111111-1111-4111-8111-111111111111');return true;
                })())JS");
                else runHeldHistoryScript(LR"JS((()=>{
                  if(document.getElementById('synthetic-marker')?.dataset.kind!=='history-c')return false;
                  const f=document.createElement('form');f.method='POST';
                  f.action='/desktop/meetings/11111111-1111-4111-8111-111111111111';
                  const i=document.createElement('input');i.name='probe';i.value='synthetic-value';
                  f.append(i);document.body.append(f);f.requestSubmit();return true;
                })())JS");
            } else {
                const auto& attempt = heldCompetitors[heldAttempt];
                if (heldCommandAck && attempt.id && attempt.completed) {
                    if (attempt.loaded || attempt.success || attempt.error != CoreWebView2WebErrorStatus::OperationCanceled) {
                        finish(false, "held-competitor-not-cancelled"); return;
                    }
                    ++heldAttempt;
                    heldAttemptSent = false;
                }
            }
            return;
        }
        if (!heldDocumentVerified) { inspectHeldHistoryDocument(); return; }
        if (!heldButtonRequested) {
            heldButtonRequested = true;
            heldRetainedDispatches = terminal ? 0u : 1u;
            runHeldHistoryScript(terminal ? LR"JS((()=>{
              if(document.getElementById('synthetic-marker')?.dataset.kind!=='history-b')return false;
              const b=document.createElement('button');b.setAttribute('data-graf-app-update','');
              document.body.append(b);b.click();b.remove();return true;
            })())JS" : LR"JS((()=>{
              if(document.getElementById('synthetic-marker')?.dataset.kind!=='history-c')return false;
              const b=document.createElement('button');b.setAttribute('data-graf-app-update','');
              document.body.append(b);b.click();b.remove();return true;
            })())JS");
            return;
        }
        if (!heldCommandAck || updateCallbacks != heldUpdates + heldRetainedDispatches) return;
        if (!heldHistoryOwner()) { finish(false, "held-before-delivery-authority"); return; }
        std::printf("T103_HISTORY_HOLD_PROVEN terminal=%d cancelled=%u REAL_BUTTON=1 EARLY_ACTIVATION=0\n",
            int(terminal), heldAttempt);
        historyFixture.deliver(); // No finish/latch/nonce call: production resumes itself.
    }

    unsigned productionHistoryPage() const {
        if ((heldResetScenario() || redirectHeldScenario()) && historyPhase >= 3) return 1;
        constexpr unsigned getPages[] = {1, 2, 3, 2, 3};
        constexpr unsigned legacyGetPages[] = {1, 2, 3, 2, 1, 2, 3};
        constexpr unsigned quarantinePages[] = {1, 2, 3, 1, 3, 1, 3};
        if (fullGetHistoryScenario()) return legacyGetPages[historyPhase];
        return quarantineHistoryScenario() ? quarantinePages[historyPhase] : getPages[historyPhase];
    }

    std::string productionHistoryPageUrl(unsigned page) const {
        if (scenario == "history-host-ordinary-back")
            return origin + (page == 1 ? "/desktop/meetings" : page == 2 ? "/desktop/settings" : "/desktop/shared-with-me");
        return origin + (page == 1 || (page == 2 && historySameUrlScenario()) ||
            (page == 3 && scenario == "history-get-repeated-url") ? "/desktop/meetings" : page == 2 ?
            "/desktop/meetings/11111111-1111-4111-8111-111111111111" :
            "/desktop/meetings/33333333-3333-4333-8333-333333333333");
    }

    std::string productionHistoryUrl() const { return productionHistoryPageUrl(productionHistoryPage()); }

    bool productionHistoryOwner() const {
        return host->runtimeState() == WebRuntimeState::ready && observedSuccess && observedStatus == 200 &&
            observedError == CoreWebView2WebErrorStatus::Unknown &&
            starts == historyPhase + 1 && completions == historyPhase + 1 &&
            lastStartedNavigationId == resetDocument.navigation && lastCompletedNavigationId == resetDocument.navigation &&
            host->documentGeneration() == resetDocument.generation &&
            host->currentUrl() == productionHistoryUrl() && to_string(view.CoreWebView2().Source()) == productionHistoryUrl() &&
            authCallbacks == historyPhase + 1 && currentCookieReads == historyPhase + 1 &&
            signedOutObservations == (accountHistoryScenario() ? 0u : historyPhase + 1) && authInvalidations == 0 &&
            (!accountHistoryScenario() || historyFixture.account(*host, accountCookieToken, false));
    }

    void advanceProductionHistory() {
        std::printf("T103_HOST_HISTORY phase=%u id=%d GET=%d POST=%d REAL_BRIDGE=%u AUTHORITY=1\n",
            historyPhase, productionCommittedId, int(resetDocument.get), int(resetDocument.post), updateCallbacks);
        const auto phase = historyPhase;
        if (phase == (quarantineHistoryScenario() || fullGetHistoryScenario() ? 6u : 4u)) {
            if (controlledHistoryScenario() && (historyFixture.unexpected || historyFixture.captures != 1 ||
                historyFixture.deliveries != 1 || historyFixture.held || historyFixture.activations != 2 ||
                !heldDocumentVerified || !heldButtonRequested || !heldCommandAck)) {
                finish(false, "held-one-shot-or-final-activation"); return;
            }
            finish(true, scenario == "history-get-repeated-url" ? "host-all-get-repeated-url-selected-ids" :
                quarantineHistoryScenario() ? "host-quarantine-reset-fresh-forward-useful-bf" : "host-all-get-selected-ids");
            return;
        }
        if ((controlledHistoryScenario() || heldResetScenario() || redirectHeldScenario()) && phase == 2) {
            heldGeneration = host->documentGeneration();
            heldAuth = authCallbacks; heldCookieReads = currentCookieReads;
            heldSignedOut = signedOutObservations; heldUpdates = updateCallbacks;
            if (!(redirectHeldScenario() ? historyFixture.observeActivation(*host) :
                historyFixture.install(*host, scenario == "history-terminal-held", heldResetScenario()))) {
                finish(false, "held-native-adapter-unavailable"); return;
            }
        }
        ++historyPhase;
        historyPreviousGeneration = host->documentGeneration();
        productionCommittedId = -1;
        if (phase == 0 && quarantineHistoryScenario()) {
            // The browser submits a real form; no synthetic method/nonce/latch injection.
            formSubmitted = true;
            runHistoryControlScript(L"document.getElementById('synthetic-input').value='synthetic-value';document.getElementById('synthetic-form').requestSubmit();true;");
        } else if (phase < 2 || (redirectHeldScenario() && phase == 2)) {
            if (host->navigate(productionHistoryUrl()).decision != RouteDecision::allow)
                finish(false, "host-history-preparation-route");
        } else if (phase == 2 || (quarantineHistoryScenario() && phase == 4) || (fullGetHistoryScenario() && phase == 3)) {
            if (!host->canGoBack()) { finish(false, "host-history-back-unavailable"); return; }
            host->back(); // Always the real production controller, never CDP steering.
        } else {
            if (!host->canGoForward()) { finish(false, "host-history-forward-unavailable"); return; }
            host->forward();
        }
    }

    void observeProductionCommit(std::uint64_t navigation) {
        if (productionCommitPending || resetDocument.loaded || navigation != resetDocument.navigation) {
            finish(false, "host-history-content-owner"); return;
        }
        resetDocument.loaded = true;
        productionCommitPending = true;
        const auto phase = historyPhase;
        const auto generation = host->documentGeneration();
        const auto queue = view.DispatcherQueue();
        // Observation only, issued at actual ContentLoading, before ordinary acceptance.
        // The fixture never calls resetNavigationHistory or installs an ALL-nav fence here.
        view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
            .Completed([this, queue, phase, generation, navigation](auto const& operation, auto const&) {
                queue.TryEnqueue([this, operation, phase, generation, navigation] {
                    productionCommitPending = false;
                    if (probeExit != 2) return;
                    try {
                        if (phase != historyPhase || generation != host->documentGeneration() ||
                            navigation != lastStartedNavigationId || navigation != resetDocument.navigation)
                            throw std::runtime_error("synthetic-stale-commit");
                        const auto result = Windows::Data::Json::JsonObject::Parse(operation.GetResults());
                        const auto entries = result.GetNamedArray(L"entries");
                        const auto index = result.GetNamedNumber(L"currentIndex");
                        if (!std::isfinite(index) || index < 0 || std::floor(index) != index || index >= entries.Size() || entries.Size() > 128)
                            throw std::runtime_error("synthetic-commit-index");
                        const auto entry = entries.GetObjectAt(static_cast<unsigned>(index));
                        const auto id = entry.GetNamedNumber(L"id");
                        if (!std::isfinite(id) || id < 0 || id > INT_MAX || std::floor(id) != id ||
                            to_string(entry.GetNamedString(L"url")) != productionHistoryUrl())
                            throw std::runtime_error("synthetic-commit-entry");
                        productionCommittedId = static_cast<int>(id);
                        std::printf("T103_HOST_CONTENT phase=%u nav=%llu id=%d\n", phase,
                            static_cast<unsigned long long>(navigation), productionCommittedId);
                    } catch (...) { finish(false, "host-history-commit-snapshot"); }
                });
            });
    }

    void checkProductionHistory() {
        if (controlledHistoryScenario() && historyFixture.unexpected) { finish(false, "held-adapter-observation"); return; }
        if (resetBridgeAwaiting) {
            if (!productionHistoryOwner()) { finish(false, "host-history-bridge-owner"); return; }
            if (updateCallbacks < historyPhase + 1 + heldRetainedDispatches) return;
            if (updateCallbacks != historyPhase + 1 + heldRetainedDispatches) { finish(false, "host-history-bridge-count"); return; }
            resetBridgeAwaiting = false;
            advanceProductionHistory();
            return;
        }
        if (completions < historyPhase + 1 || productionCommitPending) return;
        if (!observedSuccess || observedStatus != 200 || host->runtimeState() == WebRuntimeState::unavailable) {
            finish(false, "host-history-navigation-failed"); return;
        }
        // Ready/DOM native_ready can precede cookie completion (the stage10 H1).
        if (host->runtimeState() != WebRuntimeState::ready || authCallbacks < historyPhase + 1 || resetDocument.responses == 0) return;
        const bool post = quarantineHistoryScenario() && historyPhase == 1;
        if (!productionHistoryOwner() || !resetDocument.loaded || productionCommittedId < 0 ||
            resetDocument.responses != 1 || resetDocument.get != !post || resetDocument.post != post ||
            (historyPhase && resetDocument.generation <= historyPreviousGeneration)) {
            finish(false, "host-history-final-method-or-latch"); return;
        }
        const auto phase = historyPhase;
        const auto generation = resetDocument.generation;
        const auto queue = view.DispatcherQueue();
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(LR"JS((()=>{
          const m=document.getElementById('synthetic-marker');
          return ['history-a','history-b','history-c'].indexOf(m?.dataset.kind)+1+
            (window.__grafDesktopBridgeInstalled===true?16:0)+
            (document.documentElement.dataset.syntheticNativeReady==='1'?32:0)+
            (m?.dataset.postAccepted==='1'&&document.getElementById('synthetic-input')?.value==='synthetic-value'?64:0);
        })())JS").Completed([this, queue, phase, generation, post](auto const& operation, auto const&) {
            queue.TryEnqueue([this, queue, operation, phase, generation, post] {
                if (probeExit != 2) { scriptPending = false; return; }
                try {
                    if (phase != historyPhase || generation != host->documentGeneration() || !productionHistoryOwner())
                        throw std::runtime_error("synthetic-stale-dom");
                    const auto bits = std::stoi(to_string(operation.GetResults()));
                    const auto documentPage = scenario == "history-get-repeated-url" && productionHistoryPage() == 3 ? 1u : productionHistoryPage();
                    if ((bits & 15) != static_cast<int>(documentPage) || bool(bits & 64) != post)
                        throw std::runtime_error("synthetic-wrong-document");
                    if ((bits & 48) != 48) { scriptPending = false; return; }
                    view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
                        .Completed([this, queue, phase, generation](auto const& snapshot, auto const&) {
                            queue.TryEnqueue([this, snapshot, phase, generation] {
                                scriptPending = false;
                                if (probeExit != 2) return;
                                try {
                                    if (phase != historyPhase || generation != host->documentGeneration() || !productionHistoryOwner())
                                        throw std::runtime_error("synthetic-stale-terminal");
                                    const auto result = Windows::Data::Json::JsonObject::Parse(snapshot.GetResults());
                                    const auto entries = result.GetNamedArray(L"entries");
                                    const auto index = result.GetNamedNumber(L"currentIndex");
                                    const bool quarantine = quarantineHistoryScenario();
                                    const auto count = phase < 3 ? phase + 1 : quarantine ? (phase == 3 ? 1u : 2u) : 3u;
                                    const auto selected = phase < 3 ? phase : quarantine ? (phase == 3 || phase == 5 ? 0u : 1u) : productionHistoryPage() - 1;
                                    const auto integer = [](double value) {
                                        if (!std::isfinite(value) || value < 0 || value > INT_MAX || std::floor(value) != value)
                                            throw std::runtime_error("synthetic-history-id");
                                        return static_cast<int>(value);
                                    };
                                    // Host reset is async after ordinary acceptance. Only this exact
                                    // pre-reset shape may wait; no action/bridge is issued until singleton.
                                    if (quarantine && phase == 3 && entries.Size() == 4 && index == 3) {
                                        for (unsigned i = 0; i < 4; ++i) {
                                            const auto entry = entries.GetObjectAt(i);
                                            const auto expectedId = i == 3 ? productionCommittedId : historyEntryIds[i];
                                            const auto expectedUrl = productionHistoryPageUrl(i == 3 ? 1u : i + 1);
                                            if (integer(entry.GetNamedNumber(L"id")) != expectedId ||
                                                to_string(entry.GetNamedString(L"url")) != expectedUrl ||
                                                (i < 3 && historyEntryIds[i] == productionCommittedId))
                                                throw std::runtime_error("synthetic-reset-pending-identity");
                                        }
                                        return; // The unchanged native deadline makes missing reset nonzero.
                                    }
                                    if (entries.Size() != count || index != selected)
                                        throw std::runtime_error("synthetic-history-shape");
                                    const auto id = integer(entries.GetObjectAt(selected).GetNamedNumber(L"id"));
                                    if (id != productionCommittedId || to_string(entries.GetObjectAt(selected).GetNamedString(L"url")) != productionHistoryUrl())
                                        throw std::runtime_error("synthetic-terminal-id");
                                    if (phase < 3) {
                                        for (unsigned i = 0; i < phase; ++i)
                                            if (historyEntryIds[i] == id) throw std::runtime_error("synthetic-reused-id");
                                        historyEntryIds[phase] = id;
                                    } else if (quarantine && phase <= 4) {
                                        for (const auto old : historyEntryIds)
                                            if (old == id) throw std::runtime_error("synthetic-old-post-or-get-id");
                                        if (phase == 3) resetEntryId = id;
                                        else {
                                            if (id == resetEntryId) throw std::runtime_error("synthetic-not-fresh-forward");
                                            resetForwardId = id;
                                        }
                                    }
                                    for (unsigned i = 0; i < count; ++i) {
                                        const auto entry = entries.GetObjectAt(i);
                                        const auto expectedId = quarantine && phase >= 3 ? (i == 0 ? resetEntryId : resetForwardId) : historyEntryIds[i];
                                        const auto expectedUrl = productionHistoryPageUrl(quarantine && phase >= 3 ? (i == 0 ? 1u : 3u) : i + 1);
                                        if (integer(entry.GetNamedNumber(L"id")) != expectedId || to_string(entry.GetNamedString(L"url")) != expectedUrl)
                                            throw std::runtime_error("synthetic-selected-history-order");
                                    }
                                    if (quarantine && phase == 3) {
                                        // Only host code can have removed A/POST-B/C; this fixture only observes.
                                        if (!host->canGoForward()) return; // Wait for host's reset terminal, never steer it.
                                        std::puts("T103_HOST_RESET_SAME_COMMITTED_ID_SINGLETON=1 FIXTURE_RESET=0 FIXTURE_ALL_NAV_FENCE=0");
                                    }
                                    requestHistoryResetBridge(); // Real bootstrap/nonce dispatch, counter-only native handler.
                                } catch (...) { finish(false, "host-history-selected-id-or-reset"); }
                            });
                        });
                } catch (...) { scriptPending = false; finish(false, "host-history-document-or-owner"); }
            });
        });
    }

    void advanceHistory(unsigned page) {
        const auto phase = historyPhase;
        const bool post = scenario != "history-get" && scenario != "cancel-history-host";
        std::printf("T103_HISTORY_PHASE=%u DOCUMENT=%u POST_DOCUMENT=%d AUTHORITY=1\n", phase, page, int(post && phase == 1));
        if (historyEntryScenario() && phase == 2) {
            // Unsolicited CDP traversal across a history containing POST: only
            // production may deny it. The fixture never supplies a BF permit/Cancel.
            generationBeforeCancel = host->documentGeneration();
            authCallbacksBeforeCancel = authCallbacks;
            startsBeforeCancel = starts;
            completionsBeforeCancel = completions;
            controlDocumentNavigationId = lastCompletedNavigationId;
            cancelPhase = 1;
            scriptPending = true;
            const auto queue = view.DispatcherQueue();
            view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.navigateToHistoryEntry",
                to_hstring("{\"entryId\":" + std::to_string(historyEntryIds[0]) + "}"))
                .Completed([this, queue](auto const& command, auto const&) {
                    queue.TryEnqueue([this, command] {
                        scriptPending = false;
                        if (probeExit != 2) return;
                        try {
                            if (cancelPhase != 1 || host->documentGeneration() != generationBeforeCancel ||
                                Windows::Data::Json::JsonObject::Parse(command.GetResults()).Size() != 0)
                                throw std::runtime_error("synthetic-unsolicited-command");
                            historyEntryCommandAck = true;
                            std::puts("T103_UNSOLICITED_CDP_ACK=1 EXPECT_PRODUCTION_CANCEL=1 FIXTURE_CANCEL=0");
                        } catch (...) { finish(false, "production-history-denial-command"); }
                    });
                });
            return;
        }
        if (historyResetScenario() && phase == 3 && !resetVerified) { startHistoryReset(); return; }
        if (historyResetScenario() && phase == 6) { finish(true, "actual-reset-and-useful-get-history"); return; }
        if (historyRaceScenario() && phase == 4) { startHistoryRace(); return; }
        if (!historyResetScenario() && phase == (post ? 4u : 6u)) {
            finish(true, historyEntryScenario() ? "actual-browser-entry-traversal" : "actual-history-traversal"); return;
        }
        ++historyPhase;
        historyExpectedCompletions = completions + 1;
        historyPreviousGeneration = host->documentGeneration();
        if (historyControlScenario() && phase == 2) {
            generationBeforeCancel = host->documentGeneration();
            authCallbacksBeforeCancel = authCallbacks;
            startsBeforeCancel = starts;
            completionsBeforeCancel = completions;
            controlDocumentNavigationId = lastCompletedNavigationId;
            cancelPhase = 1;
            if (sameDocumentScenario()) runHistoryControlScript(L"history.replaceState(null,'',location.pathname+'#synthetic-replace');true;");
            else if (scenario == "cancel-history-script") runHistoryControlScript(L"history.go(-2);true;");
            else if (host->canGoBack()) host->back();
            else finish(false, "history-back-unavailable");
        } else if ((historyRaceScenario() || historyResetScenario()) && (phase == 2 || phase == 3)) {
            const auto path = phase == 2 ? "/desktop/meetings" :
                "/desktop/meetings/33333333-3333-4333-8333-333333333333";
            if (host->navigate(origin + path).decision != RouteDecision::allow) finish(false, "race-preparation-route");
        } else if (historyResetScenario() && phase >= 4) {
            // Isolated reset API mechanism only; production cases use actual host buttons.
            const auto target = phase == 4 ? resetEntryId : resetForwardId;
            scriptPending = true;
            const auto queue = view.DispatcherQueue();
            view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.navigateToHistoryEntry",
                to_hstring("{\"entryId\":" + std::to_string(target) + "}"))
                .Completed([this, queue, nextPhase = historyPhase](auto const& command, auto const&) {
                    queue.TryEnqueue([this, command, nextPhase] {
                        scriptPending = false;
                        if (probeExit != 2 || historyPhase != nextPhase) return;
                        try {
                            if (Windows::Data::Json::JsonObject::Parse(command.GetResults()).Size() != 0)
                                finish(false, "history-entry-command-result");
                        } catch (...) { finish(false, "history-entry-command"); }
                    });
                });
        } else if (phase == 0 && post) {
            formSubmitted = true;
            const auto queue = view.DispatcherQueue();
            view.CoreWebView2().ExecuteScriptAsync(
                LR"JS(document.getElementById('synthetic-input').value='synthetic-value';document.getElementById('synthetic-form').requestSubmit();true;)JS")
                .Completed([this, queue](auto const& submitted, auto const&) {
                    queue.TryEnqueue([this, submitted] {
                        if (probeExit != 2) return;
                        try { (void)submitted.GetResults(); }
                        catch (...) { finish(false, "history-form-submit"); }
                    });
                });
        } else if (phase < 2) {
            const auto next = phase == 0 ? "/desktop/meetings/11111111-1111-4111-8111-111111111111" :
                "/desktop/meetings/33333333-3333-4333-8333-333333333333";
            if (host->navigate(origin + next).decision != RouteDecision::allow) finish(false, "history-route");
        } else if (phase == 2 || (!post && phase == 3)) {
            if (!host->canGoBack()) { finish(false, "history-back-unavailable"); return; }
            host->back();
        } else {
            if (!host->canGoForward()) { finish(false, "history-forward-unavailable"); return; }
            host->forward();
        }
    }

    void checkHistoryEntry(unsigned page, const std::string& expectedUrl) {
        const auto generation = host->documentGeneration();
        const auto navigation = lastCompletedNavigationId;
        const auto phase = historyPhase;
        const auto queue = view.DispatcherQueue();
        scriptPending = true;
        view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
            .Completed([this, queue, generation, navigation, phase, page, expectedUrl](auto const& snapshot, auto const&) {
                queue.TryEnqueue([this, snapshot, generation, navigation, phase, page, expectedUrl] {
                    scriptPending = false;
                    if (probeExit != 2 || phase != historyPhase || generation != host->documentGeneration() ||
                        navigation != lastStartedNavigationId || navigation != lastCompletedNavigationId) return;
                    try {
                        if (host->runtimeState() != WebRuntimeState::ready || !observedSuccess ||
                            host->currentUrl() != expectedUrl || to_string(view.CoreWebView2().Source()) != expectedUrl ||
                            (phase && generation <= historyPreviousGeneration)) { finish(false, "history-entry-owner"); return; }
                        const auto integer = [](double value) {
                            if (!std::isfinite(value) || value < 0 || value > INT_MAX || std::floor(value) != value)
                                throw std::runtime_error("synthetic-history-integer");
                            return static_cast<int>(value);
                        };
                        const auto response = Windows::Data::Json::JsonObject::Parse(snapshot.GetResults());
                        const auto entries = response.GetNamedArray(L"entries");
                        const auto index = integer(response.GetNamedNumber(L"currentIndex"));
                        if (entries.Size() > 128 || static_cast<unsigned>(index) >= entries.Size()) { finish(false, "history-entry-index"); return; }
                        const auto current = entries.GetObjectAt(static_cast<unsigned>(index));
                        const auto id = integer(current.GetNamedNumber(L"id"));
                        if (to_string(current.GetNamedString(L"url")) != expectedUrl) { finish(false, "history-entry-source"); return; }
                        if (historyResetScenario()) {
                            if (phase <= 3) {
                                if (entries.Size() != phase + 1 || index != static_cast<int>(phase)) {
                                    finish(false, "reset-preparation-shape"); return;
                                }
                                for (unsigned i = 0; i < phase; ++i) {
                                    const auto entry = entries.GetObjectAt(i);
                                    const auto url = origin + (i == 0 ? "/desktop/meetings" : i == 1 ?
                                        "/desktop/meetings/11111111-1111-4111-8111-111111111111" :
                                        "/desktop/meetings/33333333-3333-4333-8333-333333333333");
                                    if (integer(entry.GetNamedNumber(L"id")) != historyEntryIds[i] ||
                                        to_string(entry.GetNamedString(L"url")) != url || id == historyEntryIds[i]) {
                                        finish(false, "reset-preparation-identity"); return;
                                    }
                                }
                                if (phase < 3) historyEntryIds[phase] = id;
                                else resetEntryId = id; // Fresh GET-list, not original A or POST B.
                            } else {
                                if (phase == 4) {
                                    for (const auto old : historyEntryIds)
                                        if (id == old) { finish(false, "reset-new-get-reused-old-id"); return; }
                                    resetForwardId = id;
                                }
                                if (entries.Size() != 2 || index != (phase == 5 ? 0 : 1) ||
                                    resetForwardId == resetEntryId || resetForwardId < 0 ||
                                    integer(entries.GetObjectAt(0).GetNamedNumber(L"id")) != resetEntryId ||
                                    integer(entries.GetObjectAt(1).GetNamedNumber(L"id")) != resetForwardId ||
                                    to_string(entries.GetObjectAt(0).GetNamedString(L"url")) != origin + "/desktop/meetings" ||
                                    to_string(entries.GetObjectAt(1).GetNamedString(L"url")) != origin + "/desktop/meetings/33333333-3333-4333-8333-333333333333") {
                                    finish(false, "reset-useful-history-identity"); return;
                                }
                            }
                            std::printf("T103_RESET_ENTRY phase=%u id=%d count=%u FINAL_METHOD=%s\n",
                                phase, id, entries.Size(), resetDocument.get ? "GET" : "POST");
                            if (phase >= 4) requestHistoryResetBridge();
                            else advanceHistory(page);
                            return;
                        }
                        if (phase < 3) {
                            for (unsigned i = 0; i < phase; ++i)
                                if (historyEntryIds[i] == id) { finish(false, "history-entry-not-distinct"); return; }
                            historyEntryIds[phase] = id;
                            if (phase == 2 && (historyControlScenario() || historyEntryScenario())) {
                                controlEntryCount = entries.Size();
                                controlEntryIndex = static_cast<unsigned>(index);
                            }
                        } else if (historyRaceScenario()) {
                            if (phase == 3) {
                                raceGetEntryId = id;
                                for (const auto old : historyEntryIds)
                                    if (old == id) { finish(false, "race-fresh-get-not-distinct"); return; }
                            } else {
                                if (entries.Size() != 5 || index != 4 || raceGetEntryId < 0) { finish(false, "race-preparation-shape"); return; }
                                const int expectedIds[] = {historyEntryIds[0], historyEntryIds[1], historyEntryIds[2], raceGetEntryId, id};
                                for (unsigned i = 0; i < 5; ++i) {
                                    if (integer(entries.GetObjectAt(i).GetNamedNumber(L"id")) != expectedIds[i]) { finish(false, "race-preparation-ids"); return; }
                                    for (unsigned j = 0; j < i; ++j)
                                        if (expectedIds[i] == expectedIds[j]) { finish(false, "race-preparation-duplicate"); return; }
                                }
                            }
                        } else if (id != historyEntryIds[phase == 3 ? 0 : 2]) { finish(false, "history-entry-restored-id"); return; }
                        if (!historyRaceScenario() && (phase == 2 || phase == 3)) {
                            const auto target = historyEntryIds[phase == 2 ? 0 : 2];
                            const auto targetUrl = phase == 2 ? origin + "/desktop/meetings" :
                                origin + "/desktop/meetings/33333333-3333-4333-8333-333333333333";
                            unsigned found = 0;
                            for (unsigned i = 0; i < entries.Size(); ++i) {
                                const auto entry = entries.GetObjectAt(i);
                                if (integer(entry.GetNamedNumber(L"id")) == target &&
                                    to_string(entry.GetNamedString(L"url")) == targetUrl &&
                                    (phase == 2 ? i < static_cast<unsigned>(index) : i > static_cast<unsigned>(index))) ++found;
                            }
                            if (found != 1) { finish(false, "history-entry-target"); return; }
                        }
                        std::printf("T103_HISTORY_ENTRY phase=%u id=%d count=%u SAME_URL=%d\n", phase, id, entries.Size(), int(historySameUrlScenario()));
                        advanceHistory(page);
                    } catch (...) { finish(false, "history-entry-snapshot"); }
                });
            });
    }

    bool historyResetOwner() const {
        return !resetLostAuthority && host->runtimeState() == WebRuntimeState::ready &&
            host->documentGeneration() == resetGeneration && host->currentUrl() == origin + "/desktop/meetings" &&
            to_string(view.CoreWebView2().Source()) == host->currentUrl() &&
            lastStartedNavigationId == resetNavigation && lastCompletedNavigationId == resetNavigation &&
            starts == resetStarts && completions == resetCompletions && authCallbacks == resetAuthCallbacks;
    }

    void requestHistoryResetBridge() {
        resetBridgeAwaiting = true;
        scriptPending = true;
        const auto phase = historyPhase;
        const auto generation = host->documentGeneration();
        const auto queue = view.DispatcherQueue();
        // Existing product bootstrap supplies the real current nonce. Never read or set it.
        view.CoreWebView2().ExecuteScriptAsync(LR"JS((()=>{
          const b=document.createElement('button');b.setAttribute('data-graf-app-update','');
          document.body.append(b);b.click();b.remove();return true;
        })())JS").Completed([this, queue, phase, generation](auto const& operation, auto const&) {
            queue.TryEnqueue([this, operation, phase, generation] {
                scriptPending = false;
                if (probeExit != 2) return;
                try {
                    if (phase != historyPhase || generation != host->documentGeneration() || operation.GetResults() != L"true")
                        finish(false, "reset-real-bridge-script");
                } catch (...) { finish(false, "reset-real-bridge-script"); }
            });
        });
    }

    void checkHistoryResetBridge() {
        if (resetPending && !historyResetOwner()) { finish(false, "reset-retained-authority"); return; }
        if (!resetBridgeAwaiting || scriptPending) return;
        if (updateCallbacks != historyPhase - 2) return; // Missing dispatch reaches the unchanged deadline.
        if (host->runtimeState() != WebRuntimeState::ready ||
            host->documentGeneration() != resetDocument.generation ||
            lastStartedNavigationId != resetDocument.navigation || lastCompletedNavigationId != resetDocument.navigation ||
            authCallbacks != historyPhase + 1 || host->currentUrl() != to_string(view.CoreWebView2().Source())) {
            finish(false, "reset-real-bridge-owner"); return;
        }
        std::printf("T103_RESET_BRIDGE phase=%u dispatches=%u CURRENT_AUTHORITY=1\n", historyPhase, updateCallbacks);
        resetBridgeAwaiting = false;
        if (historyPhase == 3) resetPending = false;
        advanceHistory(historyPhase == 3 || historyPhase == 5 ? 1u : 3u);
    }

    void startHistoryReset() {
        if (!resetPending || historyPhase != 3 || resetEntryId < 0 || !resetDocument.get ||
            resetDocument.responses != 1 || !resetDocument.loaded) { finish(false, "reset-precondition"); return; }
        resetGeneration = host->documentGeneration();
        resetNavigation = lastCompletedNavigationId;
        resetStarts = starts; resetCompletions = completions; resetAuthCallbacks = authCallbacks;
        resetCaptured = true;
        const auto queue = view.DispatcherQueue();
        scriptPending = true;
        view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.resetNavigationHistory", L"{}")
            .Completed([this, queue](auto const& command, auto const&) {
                queue.TryEnqueue([this, command, queue] {
                    if (probeExit != 2) return;
                    try {
                        if (!historyResetOwner() || Windows::Data::Json::JsonObject::Parse(command.GetResults()).Size() != 0) {
                            finish(false, "reset-command-ack-or-owner"); return;
                        }
                        std::puts("T103_RESET_ACK_EMPTY=1 FIXTURE_BLOCK_ALL=1 PRODUCTION_FENCES_PROVEN=0");
                        // A second actual native snapshot, not the pre-reset response or ACK.
                        view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
                            .Completed([this, queue](auto const& snapshot, auto const&) {
                                queue.TryEnqueue([this, snapshot] {
                                    scriptPending = false;
                                    if (probeExit != 2) return;
                                    try {
                                        const auto result = Windows::Data::Json::JsonObject::Parse(snapshot.GetResults());
                                        const auto entries = result.GetNamedArray(L"entries");
                                        if (!historyResetOwner() || result.GetNamedNumber(L"currentIndex") != 0 || entries.Size() != 1 ||
                                            entries.GetObjectAt(0).GetNamedNumber(L"id") != resetEntryId ||
                                            to_string(entries.GetObjectAt(0).GetNamedString(L"url")) != origin + "/desktop/meetings") {
                                            finish(false, "reset-singleton-identity-or-owner"); return;
                                        }
                                        resetVerified = true;
                                        std::printf("T103_RESET_SINGLETON id=%d SAME_ID_URL_GEN_NAV_AUTH=1 FINAL_GET=1\n", resetEntryId);
                                        requestHistoryResetBridge();
                                    } catch (...) { finish(false, "reset-verification-snapshot"); }
                                });
                            });
                    } catch (...) { finish(false, "reset-command"); }
                });
            });
    }

    void checkHistoryDocument() {
        if (completions < historyExpectedCompletions || lastCompletedNavigationId != lastStartedNavigationId) return;
        const auto generation = host->documentGeneration();
        const auto phase = historyPhase;
        const auto navigation = lastCompletedNavigationId;
        const auto dispatcher = view.DispatcherQueue();
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(LR"JS((() => {
          const marker = document.getElementById('synthetic-marker');
          const id = ['history-a','history-b','history-c'].indexOf(marker?.dataset.kind) + 1;
          return id + (window.__grafDesktopBridgeInstalled === true ? 16 : 0) +
            (document.documentElement.dataset.syntheticNativeReady === '1' ? 32 : 0) +
            (marker?.dataset.postAccepted === '1' && document.getElementById('synthetic-input')?.value === 'synthetic-value' ? 64 : 0);
        })())JS").Completed([this, generation, phase, navigation, dispatcher](auto const& operation, auto const&) {
            dispatcher.TryEnqueue([this, generation, phase, navigation, operation] {
                scriptPending = false;
                if (probeExit != 2 || generation != host->documentGeneration() || phase != historyPhase ||
                    navigation != lastStartedNavigationId || navigation != lastCompletedNavigationId) return;
                try {
                    const auto bits = std::stoi(to_string(operation.GetResults()));
                    const bool post = scenario != "history-get" && scenario != "cancel-history-host";
                    constexpr unsigned getPages[] = {1,2,3,2,1,2,3};
                    constexpr unsigned postPages[] = {1,2,3,1,3,1,3};
                    const auto page = post ? postPages[phase] : getPages[phase];
                    const auto path = (page == 1 || (page == 2 && (historySameUrlScenario() || historyRaceScenario()))) ? "/desktop/meetings" : page == 2 ?
                        "/desktop/meetings/11111111-1111-4111-8111-111111111111" :
                        "/desktop/meetings/33333333-3333-4333-8333-333333333333";
                    const auto state = host->runtimeState();
                    const bool hostSourceMatches = host->currentUrl() == origin + path;
                    const bool coreSourceMatches = to_string(view.CoreWebView2().Source()) == origin + path;
                    if (state == WebRuntimeState::unavailable ||
                        (state == WebRuntimeState::ready && observedSuccess && (bits & 48) == 48)) {
                        std::printf("T103_HISTORY_OBSERVED phase=%u nav=%llu generation=%llu success=%d status=%u error=%d state=%d document=%d post=%d source_matches=%d,%d detail=%s\n",
                            phase, static_cast<unsigned long long>(navigation), static_cast<unsigned long long>(generation),
                            int(observedSuccess), observedStatus, int(observedError), int(state), bits & 15,
                            int((bits & 64) != 0), int(hostSourceMatches), int(coreSourceMatches), host->failureDetail().c_str());
                    }
                    if (state == WebRuntimeState::unavailable) { finish(false, "history-host-unavailable"); return; }
                    if (state != WebRuntimeState::ready || !observedSuccess || (bits & 48) != 48) return;
                    if (historyResetScenario()) {
                        if (phase > 6 || starts != phase + 1 || completions != phase + 1 || authCallbacks > phase + 1 ||
                            observedStatus != 200 || observedError != CoreWebView2WebErrorStatus::Unknown ||
                            resetDocument.navigation != navigation || resetDocument.generation != generation ||
                            resetDocument.responses != 1 || !resetDocument.loaded ||
                            (phase == 1 ? !resetDocument.post : !resetDocument.get)) {
                            finish(false, "reset-final-response-or-latch"); return;
                        }
                        // Ready/bootstrap can precede the native cookie completion.
                        // Wait within the existing deadline, before capturing reset's owner.
                        if (authCallbacks < phase + 1) return;
                    }
                    if (unsigned(bits & 15) != page) { finish(false, "history-document-identity"); return; }
                    const bool acceptedPost = (bits & 64) != 0;
                    if (acceptedPost != (post && phase == 1)) { finish(false, "history-post-document"); return; }
                    if (!hostSourceMatches || !coreSourceMatches) { finish(false, "history-source-identity"); return; }
                    if ((historyControlScenario() || historyRaceScenario() || historyEntryScenario()) && authCallbacks != phase + 1) {
                        if (authCallbacks > phase + 1) finish(false, "history-control-auth-count");
                        return;
                    }
                    // Observe real preparation IDs; entry cases issue one unsolicited
                    // CDP traversal for production denial, never a fixture permit.
                    if (historyEntryScenario() || historySameUrlScenario() || historyControlScenario() || historyRaceScenario() || historyResetScenario()) checkHistoryEntry(page, origin + path);
                    else advanceHistory(page);
                } catch (...) { finish(false, "history-script"); }
            });
        });
    }

    void startHistoryRace() {
        raceStartedAt = GetTickCount64();
        const auto queue = view.DispatcherQueue();
        const auto native = [this, queue] {
            view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.navigateToHistoryEntry",
                to_hstring("{\"entryId\":" + std::to_string(raceGetEntryId) + "}"))
                .Completed([this, queue](auto const& command, auto const&) {
                    queue.TryEnqueue([this, command] {
                        ++raceCommands;
                        try { raceNativeAck = Windows::Data::Json::JsonObject::Parse(command.GetResults()).Size() == 0; }
                        catch (...) { raceUnexpected = true; }
                        std::printf("RACE_NATIVE_ACK=%d\n", int(raceNativeAck));
                    });
                });
        };
        const auto script = [this, queue] {
            view.CoreWebView2().ExecuteScriptAsync(LR"JS((()=>{
              if(document.getElementById('synthetic-marker')?.dataset.kind!=='history-c')return false;
              history.go(-3);return true;
            })())JS").Completed([this, queue](auto const& command, auto const&) {
                queue.TryEnqueue([this, command] {
                    ++raceCommands;
                    try { raceScriptFromC = command.GetResults() == L"true"; }
                    catch (...) { raceUnexpected = true; }
                    std::printf("RACE_SCRIPT_FROM_C=%d\n", int(raceScriptFromC));
                });
            });
        };
        // Send order is not execution order; neither completion supplies an entry/NavId binding.
        if (scenario == "history-race-native-first") { native(); script(); }
        else { script(); native(); }
    }

    void checkHistoryRace() {
        if (GetTickCount64() - raceStartedAt < 1500) return;
        const auto queue = view.DispatcherQueue();
        const auto startingCount = starts;
        scriptPending = true;
        view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
            .Completed([this, queue, startingCount](auto const& command, auto const&) {
                queue.TryEnqueue([this, queue, command, startingCount] {
                    if (probeExit != 2) return;
                    if (starts != startingCount) { scriptPending = false; return; }
                    try {
                        const auto snapshot = Windows::Data::Json::JsonObject::Parse(command.GetResults());
                        const auto entries = snapshot.GetNamedArray(L"entries");
                        const auto index = snapshot.GetNamedNumber(L"currentIndex");
                        if (!std::isfinite(index) || index < 0 || index >= entries.Size() || std::floor(index) != index || entries.Size() > 128)
                            throw std::runtime_error("race-index");
                        const auto current = entries.GetObjectAt(static_cast<unsigned>(index));
                        const auto id = current.GetNamedNumber(L"id");
                        if (!std::isfinite(id) || id < 0 || id > INT_MAX || std::floor(id) != id)
                            throw std::runtime_error("race-entry");
                        if (id == historyEntryIds[1]) raceUnsafe = true;
                        const bool safeEntry = id == raceGetEntryId && to_string(current.GetNamedString(L"url")) == origin + "/desktop/meetings";
                        std::printf("RACE_FINAL_ENTRY=%d SAFE_GET=%d UNSAFE_POST_SEEN=%d\n", int(id), int(safeEntry), int(raceUnsafe));
                        // A proven unsafe ID is already decisive; a DOM read may
                        // fail on precisely this POST restore and must not erase it.
                        if (raceUnsafe) { scriptPending = false; finish(false, "race-hypothesis-refuted-unsafe-entry"); return; }
                        view.CoreWebView2().ExecuteScriptAsync(LR"JS((()=>{
                          const m=document.getElementById('synthetic-marker');
                          return (m?.dataset.kind==='history-a'?1:0)+(m?.dataset.postAccepted==='1'?2:0)+
                            (window.__grafDesktopBridgeInstalled===true?16:0)+
                            (document.documentElement.dataset.syntheticNativeReady==='1'?32:0);
                        })())JS").Completed([this, queue, startingCount, safeEntry](auto const& result, auto const&) {
                            queue.TryEnqueue([this, result, startingCount, safeEntry] {
                                scriptPending = false;
                                if (probeExit != 2 || starts != startingCount) return;
                                try {
                                    const auto bits = std::stoi(to_string(result.GetResults()));
                                    raceUnsafe = raceUnsafe || (bits & 2) != 0;
                                    if (raceUnsafe) { finish(false, "race-hypothesis-refuted-unsafe-entry"); return; }
                                    const auto& allowed = raceNavigations[0];
                                    const auto& denied = raceNavigations[1];
                                    const bool reached = raceCommands == 2 && raceNativeAck && raceScriptFromC && !raceUnexpected &&
                                        raceStarts == 2 && allowed.id && denied.id && allowed.id != denied.id &&
                                        allowed.completed && allowed.loaded && allowed.success && denied.completed &&
                                        !denied.loaded && !denied.success && denied.error == CoreWebView2WebErrorStatus::OperationCanceled;
                                    std::printf("RACE_TWO_STARTS_OBSERVED=%d STARTS=%u COMMANDS=%u DOM_BITS=%d SAFE_GET=%d\n",
                                        int(reached), raceStarts, raceCommands, bits, int(safeEntry));
                                    // Even two starts + final GET do not independently
                                    // identify the cancelled target. Never infer that
                                    // this URL/kind permit rejected the unsafe entry.
                                    finish(false, "race-inconclusive-cancelled-target-identity");
                                } catch (...) { finish(false, "race-inconclusive-dom"); }
                            });
                        });
                    } catch (...) { scriptPending = false; finish(false, "race-inconclusive-snapshot"); }
                });
            });
    }

    void checkRetainedHistoryEntry() {
        const auto queue = view.DispatcherQueue();
        const auto phase = cancelPhase;
        const auto expectedUrl = origin + "/desktop/meetings/33333333-3333-4333-8333-333333333333" +
            (sameDocumentScenario() ? (phase == 1 ? "#synthetic-replace" : "#synthetic-hash") : "");
        scriptPending = true;
        view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
            .Completed([this, queue, phase, expectedUrl](auto const& snapshot, auto const&) {
                queue.TryEnqueue([this, snapshot, phase, expectedUrl] {
                    scriptPending = false;
                    if (probeExit != 2 || phase != cancelPhase) return;
                    try {
                        if (host->runtimeState() != WebRuntimeState::ready || host->documentGeneration() != generationBeforeCancel ||
                            authCallbacks != authCallbacksBeforeCancel || host->currentUrl() != expectedUrl ||
                            to_string(view.CoreWebView2().Source()) != expectedUrl || controlLostAuthority) {
                            finish(false, "history-control-authority"); return;
                        }
                        const auto response = Windows::Data::Json::JsonObject::Parse(snapshot.GetResults());
                        const auto entries = response.GetNamedArray(L"entries");
                        const auto index = response.GetNamedNumber(L"currentIndex");
                        const bool hash = sameDocumentScenario() && phase == 2;
                        const auto expectedIndex = controlEntryIndex + unsigned(hash);
                        if (entries.Size() != controlEntryCount + unsigned(hash) || entries.Size() > 128 ||
                            index != expectedIndex || expectedIndex >= entries.Size()) { finish(false, "history-control-entry-index"); return; }
                        const auto current = entries.GetObjectAt(expectedIndex);
                        const auto id = current.GetNamedNumber(L"id");
                        if (!std::isfinite(id) || id < 0 || id > INT_MAX || std::floor(id) != id ||
                            to_string(current.GetNamedString(L"url")) != expectedUrl ||
                            (hash ? id == controlReplacedEntryId : !sameDocumentScenario() && id != historyEntryIds[2])) {
                            finish(false, "history-control-entry-identity"); return;
                        }
                        if (sameDocumentScenario() && phase == 1) controlReplacedEntryId = static_cast<int>(id);
                        if (hash) {
                            const auto replaced = entries.GetObjectAt(controlEntryIndex);
                            if (replaced.GetNamedNumber(L"id") != controlReplacedEntryId ||
                                to_string(replaced.GetNamedString(L"url")) != origin +
                                    "/desktop/meetings/33333333-3333-4333-8333-333333333333#synthetic-replace") {
                                finish(false, "history-control-replaced-entry"); return;
                            }
                        }
                        controlEntryVerified = true;
                        std::printf("T103_HISTORY_RETAINED phase=%u id=%d count=%u HASH=%d\n", phase, static_cast<int>(id), entries.Size(), int(hash));
                    } catch (...) { finish(false, "history-control-entry-snapshot"); }
                });
            });
    }

    void checkSameDocument() {
        const auto phase = cancelPhase;
        const bool final = phase == 3;
        const auto expectedUrl = origin + (final ? "/desktop/meetings" :
            phase == 1 ? "/desktop/meetings/33333333-3333-4333-8333-333333333333#synthetic-replace" :
                "/desktop/meetings/33333333-3333-4333-8333-333333333333#synthetic-hash");
        if (controlLostAuthority || (!final && (host->documentGeneration() != generationBeforeCancel ||
            authCallbacks != authCallbacksBeforeCancel || starts != startsBeforeCancel ||
            lastStartedNavigationId != controlDocumentNavigationId || lastCompletedNavigationId != controlDocumentNavigationId))) {
            finish(false, "same-document-revoked-authority"); return;
        }
        if (host->runtimeState() != WebRuntimeState::ready || host->currentUrl() != expectedUrl ||
            to_string(view.CoreWebView2().Source()) != expectedUrl) return;
        const auto queue = view.DispatcherQueue();
        const auto generation = host->documentGeneration();
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(LR"JS((() => {
          const marker = document.getElementById('synthetic-marker');
          return ['history-a','history-b','history-c'].indexOf(marker?.dataset.kind) + 1 +
            (window.__grafDesktopBridgeInstalled === true ? 16 : 0) +
            (document.documentElement.dataset.syntheticNativeReady === '1' ? 32 : 0);
        })())JS").Completed([this, queue, phase, generation, final](auto const& result, auto const&) {
            queue.TryEnqueue([this, result, phase, generation, final] {
                scriptPending = false;
                if (probeExit != 2 || phase != cancelPhase || generation != host->documentGeneration()) return;
                try {
                    const auto bits = std::stoi(to_string(result.GetResults()));
                    if ((bits & 48) != 48) return;
                    if ((bits & 15) != (final ? 1 : 3)) { finish(false, "same-document-marker"); return; }
                    if (final) {
                        if (observedSuccess && observedStatus == 200 && generation > generationBeforeCancel &&
                            starts == startsBeforeCancel + 1 && completions == completionsBeforeCancel + 1 &&
                            lastStartedNavigationId != controlDocumentNavigationId && lastCompletedNavigationId == lastStartedNavigationId &&
                            authCallbacks == authCallbacksBeforeCancel + 1 && updateCallbacks == 2)
                            finish(true, "same-document-authority-and-next-navigation");
                    } else if (!controlEntryVerified) checkRetainedHistoryEntry();
                    else if (!cancelBridgeRequested) {
                        cancelBridgeRequested = true;
                        host->setAppUpdateAvailable(true);
                        runHistoryControlScript(L"(()=>{const b=document.createElement('button');b.setAttribute('data-graf-app-update','');document.body.append(b);b.click();return true;})()");
                    } else if (updateCallbacks == phase) {
                        ++cancelPhase;
                        cancelBridgeRequested = false;
                        controlEntryVerified = false;
                        if (phase == 1) runHistoryControlScript(L"location.hash='synthetic-hash';true;");
                        else {
                            // Same-document events may retain the old navigation ID.
                            // Count the following new document from this fresh baseline.
                            startsBeforeCancel = starts;
                            completionsBeforeCancel = completions;
                            (void)host->navigate(origin + "/desktop/meetings");
                        }
                    }
                } catch (...) { finish(false, "same-document-script"); }
            });
        });
    }

    void checkCancelledNavigation() {
        if (cancelPhase == 1 && (!cancelledNavigationId || lastCompletedNavigationId != cancelledNavigationId)) return;
        if (historyEntryScenario() && cancelPhase == 1 && !historyEntryCommandAck) return;
        const auto generation = host->documentGeneration();
        if (cancelPhase == 1 && (host->runtimeState() != WebRuntimeState::ready ||
            generation != generationBeforeCancel || authCallbacks != authCallbacksBeforeCancel || controlLostAuthority)) {
            finish(false, "cancelled-navigation-revoked-current-document"); return;
        }
        if (host->runtimeState() != WebRuntimeState::ready) return;
        if (historyEntryScenario() && cancelPhase == 2 && resetDocument.responses == 0) return;
        const bool expectC = retainedHistoryScenario() ? cancelPhase == 1 : cancelPhase == 2;
        const auto path = expectC ? "/desktop/meetings/33333333-3333-4333-8333-333333333333" : "/desktop/meetings";
        if (host->currentUrl() != origin + path || to_string(view.CoreWebView2().Source()) != origin + path) {
            finish(false, "cancelled-navigation-source"); return;
        }
        const auto phase = cancelPhase;
        const auto navigation = lastCompletedNavigationId;
        const auto queue = view.DispatcherQueue();
        scriptPending = true;
        view.CoreWebView2().ExecuteScriptAsync(LR"JS((() => {
          const marker = document.getElementById('synthetic-marker');
          return ['history-a','history-b','history-c'].indexOf(marker?.dataset.kind) + 1 +
            (window.__grafDesktopBridgeInstalled === true ? 16 : 0) +
            (document.documentElement.dataset.syntheticNativeReady === '1' ? 32 : 0);
        })())JS").Completed([this, queue, generation, navigation, phase](auto const& operation, auto const&) {
            queue.TryEnqueue([this, operation, generation, navigation, phase, queue] {
                scriptPending = false;
                if (probeExit != 2 || phase != cancelPhase || generation != host->documentGeneration() ||
                    navigation != lastCompletedNavigationId) return;
                try {
                    const auto bits = std::stoi(to_string(operation.GetResults()));
                    if ((bits & 48) != 48) return;
                    const bool documentIsC = retainedHistoryScenario() ? phase == 1 : phase == 2;
                    if ((bits & 15) != (documentIsC ? 3 : 1)) { finish(false, "cancelled-navigation-document"); return; }
                    if (phase == 0) {
                        if (!observedSuccess || completions != 1 || authCallbacks != 1) return;
                        generationBeforeCancel = generation;
                        authCallbacksBeforeCancel = authCallbacks;
                        startsBeforeCancel = starts;
                        completionsBeforeCancel = completions;
                        cancelPhase = 1;
                        (void)host->navigate(origin + "/desktop/meetings/11111111-1111-4111-8111-111111111111");
                    } else if (phase == 1) {
                        if (observedSuccess || observedStatus != 0 || observedError != CoreWebView2WebErrorStatus::OperationCanceled ||
                            starts != startsBeforeCancel + 1 || completions != completionsBeforeCancel + 1) { finish(false, "cancelled-navigation-event"); return; }
                        if (retainedHistoryScenario() && !controlEntryVerified) { checkRetainedHistoryEntry(); return; }
                        if (!cancelBridgeRequested) {
                            cancelBridgeRequested = true;
                            host->setAppUpdateAvailable(true);
                            // A real bridge dispatch proves the old nonce still works;
                            // DOM bootstrap flags alone could have survived a revocation.
                            scriptPending = true;
                            view.CoreWebView2().ExecuteScriptAsync(LR"JS((() => {
                              const button = document.createElement('button');
                              button.setAttribute('data-graf-app-update', '');
                              document.body.append(button); button.click(); return true;
                            })())JS").Completed([this, queue, generation](auto const& clicked, auto const&) {
                                queue.TryEnqueue([this, clicked, generation] {
                                    scriptPending = false;
                                    if (probeExit != 2 || generation != host->documentGeneration() || cancelPhase != 1) return;
                                    try { if (clicked.GetResults() != L"true") finish(false, "cancelled-navigation-bridge-click"); }
                                    catch (...) { finish(false, "cancelled-navigation-bridge-click"); }
                                });
                            });
                        } else if (updateCallbacks == 1) {
                            cancelPhase = 2;
                            (void)host->navigate(origin + (retainedHistoryScenario() ? "/desktop/meetings" :
                                "/desktop/meetings/33333333-3333-4333-8333-333333333333"));
                        }
                    } else if (observedSuccess && observedStatus == 200 && starts == startsBeforeCancel + 2 && completions == completionsBeforeCancel + 2 &&
                        generation > generationBeforeCancel && updateCallbacks == 1 && authCallbacks == authCallbacksBeforeCancel + 1) {
                        if (!historyEntryScenario()) { finish(true, "cancelled-page-authority-and-next-navigation"); return; }
                        if (!resetDocument.get || resetDocument.post || resetDocument.responses != 1 || !resetDocument.loaded ||
                            resetDocument.navigation != lastStartedNavigationId || lastCompletedNavigationId != lastStartedNavigationId ||
                            resetDocument.generation != generation) { finish(false, "production-history-next-get-proof"); return; }
                        scriptPending = true;
                        view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
                            .Completed([this, queue, generation, navigation](auto const& snapshot, auto const&) {
                                queue.TryEnqueue([this, snapshot, generation, navigation] {
                                    scriptPending = false;
                                    if (probeExit != 2) return;
                                    try {
                                        if (cancelPhase != 2 || generation != host->documentGeneration() ||
                                            navigation != lastStartedNavigationId || navigation != lastCompletedNavigationId ||
                                            host->runtimeState() != WebRuntimeState::ready || authCallbacks != authCallbacksBeforeCancel + 1 ||
                                            host->currentUrl() != origin + "/desktop/meetings" || to_string(view.CoreWebView2().Source()) != host->currentUrl())
                                            throw std::runtime_error("synthetic-next-get-owner");
                                        const auto response = Windows::Data::Json::JsonObject::Parse(snapshot.GetResults());
                                        const auto entries = response.GetNamedArray(L"entries");
                                        const auto index = response.GetNamedNumber(L"currentIndex");
                                        if (!std::isfinite(index) || index < 0 || std::floor(index) != index || index >= entries.Size() || entries.Size() > 128)
                                            throw std::runtime_error("synthetic-next-get-index");
                                        const auto entry = entries.GetObjectAt(static_cast<unsigned>(index));
                                        const auto id = entry.GetNamedNumber(L"id");
                                        if (!std::isfinite(id) || id < 0 || id > INT_MAX || std::floor(id) != id ||
                                            to_string(entry.GetNamedString(L"url")) != host->currentUrl())
                                            throw std::runtime_error("synthetic-next-get-id");
                                        for (const auto old : historyEntryIds)
                                            if (id == old) throw std::runtime_error("synthetic-next-get-old-id");
                                        finish(true, "production-unsolicited-denied-retained-authority-next-get");
                                    } catch (...) { finish(false, "production-history-next-get-snapshot"); }
                                });
                            });
                    }
                } catch (...) { finish(false, "cancelled-navigation-script"); }
            });
        });
    }

    bool redirectTerminalOwner() const {
        if (!historyFixture.resetRevoked(*host) || historyFixture.unexpected || historyFixture.activations ||
            historyFixture.captures || historyFixture.deliveries || historyFixture.held || accountTerminalLost ||
            !historyFixture.account(*host, accountCookieToken, true) || host->runtimeState() != WebRuntimeState::unavailable ||
            host->canGoForward() || host->documentGeneration() != staleResetGeneration ||
            authCallbacks != heldAuth || currentCookieReads != heldCookieReads || signedOutObservations ||
            authInvalidations || updateCallbacks != heldUpdates || historyPhase != 3 ||
            starts != (redirectHeldStarting ? 5u : 4u) || completions != (redirectHeldNavigation.completed ? 4u : 3u) ||
            !accountUnavailableAt || accountUnavailableAt < accountBoundAt || accountUnavailableAt - accountBoundAt > 5000)
            return false;
        const auto current = historyFixture.boundary(*host);
        for (unsigned i = 0; i < current.size(); ++i) if (current[i] <= accountBoundaryBefore[i]) return false;
        return current == accountBoundaryAfter;
    }

    void checkRedirectHeld() {
        if (responseMarkerExists(L"unexpected-http")) {
            finish(false, "held-redirect-server-received-unexpected-get"); return;
        }
        if (responseMarkerExists(L"response-timeout") || responseMarkerExists(L"response-disconnected")) {
            finish(false, "held-redirect-response-not-delivered"); return;
        }
        if (redirectHeldPhase == 0) {
            if (!redirectHeldRequest || !responseMarkerExists(L"response-held")) return;
            if (!historyFixture.navigatingWithoutResponse(*host, redirectHeldNavigation.id) ||
                redirectHeldNavigation.completed || redirectHeldNavigation.loaded || redirectHeldResponses ||
                starts != 4 || completions != 3 || authCallbacks != 3 || currentCookieReads != 3 ||
                signedOutObservations || authInvalidations || updateCallbacks != 3 ||
                !historyFixture.account(*host, accountCookieToken, false) || historyFixture.activations) {
                finish(false, "held-redirect-not-real-pending-navigation"); return;
            }
            staleResetGeneration = host->documentGeneration();
            staleResetNavigation = redirectHeldNavigation.id;
            if (staleResetGeneration <= heldGeneration || lastStartedNavigationId != staleResetNavigation) {
                finish(false, "held-redirect-pending-owner"); return;
            }
            accountBoundaryBefore = historyFixture.boundary(*host);
            redirectHeldPhase = 1;
            accountBoundAt = GetTickCount64();
            std::printf("T103_HELD_REDIRECT_BOUNDARY nav=%llu REAL_UNMARKED_GET_HELD=1 PUBLIC_BIND=1\n",
                static_cast<unsigned long long>(staleResetNavigation));
            host->bindUserTimeAccount(origin, "11111111-1111-4111-8111-111111111111",
                "55555555-5555-4555-8555-555555555555", accountCookieToken, 1);
            return;
        }
        if (redirectHeldPhase == 1) {
            if (host->runtimeState() != WebRuntimeState::unavailable) {
                if (GetTickCount64() - accountBoundAt >= 5000) finish(false, "held-redirect-account-loading-timeout");
                return; // Never release the HTTP response merely to end a stranded loading state.
            }
            accountBoundaryAfter = historyFixture.boundary(*host);
            if (!redirectTerminalOwner()) { finish(false, "held-redirect-boundary-terminal-owner"); return; }
            redirectHeldPhase = 2;
            std::printf("T103_HELD_REDIRECT_UNAVAILABLE elapsed_ms=%llu ACCOUNT_B=1 AUTHORITY=0\n",
                static_cast<unsigned long long>(accountUnavailableAt - accountBoundAt));
            if (!releaseRedirectResponse()) finish(false, "held-redirect-release-write");
            return;
        }
        if (!redirectTerminalOwner()) { finish(false, "held-redirect-late-event-resurrection"); return; }
        if (!redirectHeldStarting || !redirectHeldNavigation.completed) return; // Real same-ID redirect and terminal14, not a server marker.
        std::printf("T103_HELD_REDIRECT_CANCELLED nav=%llu error=%d FIXTURE_CANCEL=0 ACCOUNT_B=1\n",
            static_cast<unsigned long long>(redirectHeldNavigation.id), int(redirectHeldNavigation.error));
        historyPhase = 4; staleResetPhase = 5;
        productionCommittedId = -1;
        host->reload(); // Actual native Reload path only after the old navigation is terminal.
    }

    bool staleResetOwner() const {
        if (historyFixture.unexpected || historyFixture.captures != 1 || historyFixture.activations ||
            historyFixture.deliveries != (staleResetPhase >= 4 ? 1u : 0u) ||
            historyFixture.held != (staleResetPhase < 4) || productionCommitPending || productionCommittedId < 0 ||
            authCallbacks != heldAuth || currentCookieReads != heldCookieReads || signedOutObservations != heldSignedOut ||
            authInvalidations || updateCallbacks != heldUpdates || historyPhase != 3 || starts != 4 || completions < 4 ||
            !resetDocument.loaded || resetDocument.responses != 1 || !resetDocument.get || resetDocument.post ||
            resetDocument.generation != staleResetGeneration || staleResetGeneration != host->documentGeneration() ||
            staleResetGeneration <= heldGeneration || resetDocument.navigation != staleResetNavigation ||
            lastStartedNavigationId != staleResetNavigation || lastCompletedNavigationId != staleResetNavigation)
            return false;
        const auto list = origin + "/desktop/meetings";
        if (to_string(view.CoreWebView2().Source()) != list +
            (accountBoundaryScenario() || staleResetPhase < 2 ? "" : "#synthetic-reset")) return false;
        if (accountBoundaryScenario()) {
            if (!historyFixture.account(*host, accountCookieToken, staleResetPhase >= 2)) return false;
            if (staleResetPhase >= 2) {
                const auto current = historyFixture.boundary(*host);
                for (unsigned i = 0; i < current.size(); ++i) if (current[i] <= accountBoundaryBefore[i]) return false;
                return !accountTerminalLost && completions == 4 && historyFixture.resetRevoked(*host) && host->runtimeState() == WebRuntimeState::unavailable &&
                    host->currentUrl() == list && !host->canGoForward() && accountUnavailableAt >= accountBoundAt &&
                    accountUnavailableAt - accountBoundAt <= 5000 && current == accountBoundaryAfter;
            }
        }
        if (staleResetPhase < 2) return historyFixture.resetting(*host) && host->runtimeState() != WebRuntimeState::ready &&
            host->currentUrl() == list && completions == 4 && observedSuccess && observedStatus == 200 &&
            observedError == CoreWebView2WebErrorStatus::Unknown;
        return historyFixture.resetRevoked(*host) && host->runtimeState() == WebRuntimeState::unavailable &&
            host->failureDetail() == "history-mutation · 0x00000000" && !host->canGoForward();
    }

    bool staleResetRecoveryOwner() const {
        return !historyFixture.unexpected && historyFixture.captures == (redirectHeldScenario() ? 0u : 1u) &&
            historyFixture.deliveries == (redirectHeldScenario() ? 0u : 1u) &&
            !historyFixture.held && historyFixture.activations == 1 && historyPhase == 4 &&
            historyFixture.resetRecovered(*host) && !host->canGoForward() &&
            host->runtimeState() == WebRuntimeState::ready && host->currentUrl() == origin + "/desktop/meetings" &&
            to_string(view.CoreWebView2().Source()) == host->currentUrl() && starts == (redirectHeldScenario() ? 6u : 5u) && completions >= 5 &&
            observedSuccess && observedStatus == 200 && observedError == CoreWebView2WebErrorStatus::Unknown &&
            !productionCommitPending && resetDocument.loaded && resetDocument.responses == 1 && resetDocument.get && !resetDocument.post &&
            resetDocument.generation == host->documentGeneration() && resetDocument.generation > staleResetGeneration &&
            resetDocument.navigation != staleResetNavigation && lastStartedNavigationId == resetDocument.navigation &&
            lastCompletedNavigationId == resetDocument.navigation && authCallbacks == heldAuth + 1 &&
            currentCookieReads == heldCookieReads + 1 &&
            signedOutObservations == heldSignedOut + (accountHistoryScenario() ? 0u : 1u) && authInvalidations == 0 &&
            (!accountHistoryScenario() || (completions == 5 && !accountTerminalLost &&
                historyFixture.account(*host, accountCookieToken, true)));
    }

    void inspectStaleResetDocument() {
        const auto phase = staleResetPhase;
        const auto generation = host->documentGeneration();
        const auto queue = view.DispatcherQueue();
        scriptPending = true;
        // A synthetic input proves DOM retention across the held operation, not document authority.
        std::wstring script = phase == 0 ? L"document.getElementById('synthetic-input').value='synthetic-reset-retained';" : L"";
        script += LR"JS((()=>{
          const m=document.getElementById('synthetic-marker'), input=document.getElementById('synthetic-input');
          const installed=window.__grafDesktopBridgeInstalled===true, ready=document.documentElement.dataset.syntheticNativeReady==='1';
          if(!installed && !ready){
            const b=document.createElement('button');b.setAttribute('data-graf-app-update','');
            document.body.append(b);b.click();b.remove();
          }
          return (m?.dataset.kind==='history-a'?1:0)+(installed?16:0)+(ready?32:0)+
            (input?.value==='synthetic-reset-retained'?64:0)+(m?.dataset.postAccepted==='1'?128:0);
        })())JS";
        view.CoreWebView2().ExecuteScriptAsync(script).Completed([this, queue, phase, generation](auto const& operation, auto const&) {
            queue.TryEnqueue([this, queue, phase, generation, operation] {
                if (probeExit != 2) { scriptPending = false; return; }
                try {
                    if (phase != staleResetPhase || generation != host->documentGeneration() ||
                        (phase == 5 ? !staleResetRecoveryOwner() : !staleResetOwner()))
                        throw std::runtime_error("synthetic-stale-reset-owner");
                    const auto bits = std::stoi(to_string(operation.GetResults()));
                    if (phase == 5 && (bits == 1 || bits == 17 || bits == 33)) { scriptPending = false; return; }
                    if (bits != (phase == 5 ? 49 : 65)) throw std::runtime_error("synthetic-stale-reset-dom");
                    view.CoreWebView2().CallDevToolsProtocolMethodAsync(L"Page.getNavigationHistory", L"{}")
                        .Completed([this, queue, phase, generation](auto const& snapshot, auto const&) {
                            queue.TryEnqueue([this, snapshot, phase, generation] {
                                scriptPending = false;
                                if (probeExit != 2) return;
                                try {
                                    if (phase != staleResetPhase || generation != host->documentGeneration() ||
                                        (phase == 5 ? !staleResetRecoveryOwner() : !staleResetOwner()))
                                        throw std::runtime_error("synthetic-stale-reset-snapshot-owner");
                                    const auto result = Windows::Data::Json::JsonObject::Parse(snapshot.GetResults());
                                    const auto entries = result.GetNamedArray(L"entries");
                                    const bool mutated = !accountBoundaryScenario() && (phase == 2 || phase == 4);
                                    if (entries.Size() != (mutated ? 2u : 1u) || result.GetNamedNumber(L"currentIndex") != (mutated ? 1 : 0))
                                        throw std::runtime_error("synthetic-stale-reset-shape");
                                    const auto integer = [](double value) {
                                        if (!std::isfinite(value) || value < 0 || value > INT_MAX || std::floor(value) != value)
                                            throw std::runtime_error("synthetic-stale-reset-id");
                                        return static_cast<int>(value);
                                    };
                                    const auto list = origin + "/desktop/meetings";
                                    const auto first = entries.GetObjectAt(0);
                                    const auto firstId = integer(first.GetNamedNumber(L"id"));
                                    if (to_string(first.GetNamedString(L"url")) != list ||
                                        (phase != 5 && (firstId != historyFixture.capturedResetId || firstId != productionCommittedId ||
                                            historyFixture.capturedResetUrl != list)))
                                        throw std::runtime_error("synthetic-stale-reset-singleton");
                                    if (phase == 0) for (const auto old : historyEntryIds)
                                        if (firstId == old) throw std::runtime_error("synthetic-not-fresh-list-id");
                                    if (mutated) {
                                        const auto current = entries.GetObjectAt(1);
                                        const auto id = integer(current.GetNamedNumber(L"id"));
                                        if (id == firstId || to_string(current.GetNamedString(L"url")) != list + "#synthetic-reset" ||
                                            (phase == 4 && id != staleResetEntryId))
                                            throw std::runtime_error("synthetic-stale-reset-mutated-id");
                                        for (const auto old : historyEntryIds) if (id == old) throw std::runtime_error("synthetic-old-history-id");
                                        if (phase == 2) staleResetEntryId = id;
                                    }
                                    std::printf("T103_STALE_RESET_OBSERVED phase=%u id=%d generation=%llu ENTRIES=%u NO_EXTRA_NAVIGATION=1\n",
                                        phase, mutated ? staleResetEntryId : firstId,
                                        static_cast<unsigned long long>(generation), entries.Size());
                                    if (phase == 0) { staleResetPhase = 1; return; }
                                    if (phase == 2) {
                                        if (accountBoundaryScenario()) std::printf(
                                            "T103_ACCOUNT_BOUNDARY_UNAVAILABLE elapsed_ms=%llu SESSION_OPERATION_REVISION_CHANGED=1 ACCOUNT_B=1 AUTHORITY=0\n",
                                            static_cast<unsigned long long>(accountUnavailableAt - accountBoundAt));
                                        historyFixture.deliver(); // Exact original singleton result, once on the UI thread; no finish call.
                                        staleResetPhase = 4;
                                        if (!staleResetOwner()) throw std::runtime_error("synthetic-stale-reset-resurrection");
                                        return;
                                    }
                                    if (phase == 4) {
                                        staleResetPhase = 5; historyPhase = 4;
                                        productionCommittedId = -1;
                                        if (accountBoundaryScenario()) host->reload(); // Same public command as native Reload, not a fixture Navigate.
                                        else if (host->navigate(list).decision != RouteDecision::allow)
                                            throw std::runtime_error("synthetic-stale-reset-recovery-route");
                                        return;
                                    }
                                    if (firstId != productionCommittedId || (!accountHistoryScenario() &&
                                        (firstId == historyFixture.capturedResetId || firstId == staleResetEntryId)))
                                        throw std::runtime_error("synthetic-stale-reset-recovery-id");
                                    if (!accountHistoryScenario()) for (const auto old : historyEntryIds)
                                        if (firstId == old) throw std::runtime_error("synthetic-old-recovery-id");
                                    staleRecoveryVerified = true;
                                    requestHistoryResetBridge(); // Ordinary recovered bootstrap supplies the nonce, never this fixture.
                                } catch (...) { finish(false, "stale-reset-independent-snapshot"); }
                            });
                        });
                } catch (...) { scriptPending = false; finish(false, "stale-reset-independent-dom"); }
            });
        });
    }

    void checkStaleReset() {
        if (redirectHeldScenario() && responseMarkerExists(L"unexpected-http")) {
            finish(false, "held-redirect-server-received-unexpected-get"); return;
        }
        if (historyFixture.unexpected) { finish(false, "stale-reset-adapter"); return; }
        if (staleResetPhase == 5) {
            if (host->runtimeState() != WebRuntimeState::ready || authCallbacks < heldAuth + 1 || productionCommitPending) return;
            if (!staleResetRecoveryOwner()) { finish(false, "stale-reset-recovery-owner"); return; }
            if (!staleRecoveryVerified) { inspectStaleResetDocument(); return; }
            if (updateCallbacks < heldUpdates + 1) return;
            if (updateCallbacks != heldUpdates + 1) { finish(false, "stale-reset-recovery-bridge-count"); return; }
            finish(true, redirectHeldScenario() ? "account-boundary-real-late-redirect-cancelled-reload-retains-b" :
                accountBoundaryScenario() ? "account-boundary-stale-reset-inert-reload-retains-b" :
                "stale-reset-revoked-real-result-fresh-get-recovery");
            return;
        }
        if (!historyFixture.held && !historyFixture.deliveries) return; // Real reset ACK/readback must arrive within the unchanged deadline.
        if (!staleResetGeneration) {
            if (productionCommitPending || completions < 4 || !resetDocument.responses) return;
            staleResetGeneration = resetDocument.generation; staleResetNavigation = resetDocument.navigation;
        }
        if (accountBoundaryScenario() && staleResetPhase == 2) {
            if (host->runtimeState() != WebRuntimeState::unavailable) {
                if (GetTickCount64() - accountBoundAt >= 5000) finish(false, "account-boundary-loading-timeout");
                return; // No recovery can hide a cancelled reset stranded in initializing.
            }
            if (!accountUnavailableAt || accountUnavailableAt - accountBoundAt > 5000) {
                finish(false, "account-boundary-terminal-deadline"); return;
            }
            accountBoundaryAfter = historyFixture.boundary(*host);
        }
        if (staleResetPhase == 2 && host->runtimeState() != WebRuntimeState::unavailable) return; // Await actual SourceChanged, not a fixture failure call.
        if (!staleResetOwner()) { finish(false, "stale-reset-early-authority-or-owner"); return; }
        if (staleResetPhase != 1) { inspectStaleResetDocument(); return; }
        if (accountBoundaryScenario()) {
            accountBoundaryBefore = historyFixture.boundary(*host);
            staleResetPhase = 2;
            accountBoundAt = GetTickCount64();
            std::printf("T103_ACCOUNT_BOUNDARY REAL_RESET_HELD=1 PUBLIC_BIND=1\n");
            host->bindUserTimeAccount(origin, "11111111-1111-4111-8111-111111111111",
                "55555555-5555-4555-8555-555555555555", accountCookieToken, 1);
            return;
        }
        staleResetPhase = 2;
        scriptPending = true;
        const auto queue = view.DispatcherQueue();
        view.CoreWebView2().ExecuteScriptAsync(LR"JS((()=>{
          if(document.getElementById('synthetic-marker')?.dataset.kind!=='history-a' ||
             document.getElementById('synthetic-input')?.value!=='synthetic-reset-retained')return false;
          history.pushState({},'', '#synthetic-reset');return true;
        })())JS").Completed([this, queue](auto const& operation, auto const&) {
            queue.TryEnqueue([this, operation] {
                scriptPending = false;
                if (probeExit != 2) return;
                try { if (operation.GetResults() != L"true") finish(false, "stale-reset-real-mutation"); }
                catch (...) { finish(false, "stale-reset-real-mutation"); }
            });
        });
    }

    void checkFreshLogin() {
        const auto& document = freshLoginDocuments[freshLoginPhase == 0 ? 0 : 2];
        const auto expectedUrl = origin + (freshLoginPhase == 0 ? initialPath : loginNext);
        if (freshLoginPhase == 0) {
            // As in the existing production cases, ready can precede the asynchronous cookie read.
            if (host->runtimeState() != WebRuntimeState::ready || authCallbacks < 1 || !document.responses || !document.loaded) return;
            if (starts != 1 || completions != 1 || !document.get || document.post ||
                document.navigation != lastStartedNavigationId || document.navigation != lastCompletedNavigationId ||
                document.generation != host->documentGeneration() || !observedSuccess || observedStatus != 200 ||
                observedError != CoreWebView2WebErrorStatus::Unknown || host->currentUrl() != expectedUrl ||
                to_string(view.CoreWebView2().Source()) != expectedUrl || authCallbacks != 1 ||
                currentCookieReads != 1 || signedOutObservations != 1 || authInvalidations != 0) {
                finish(false, "fresh-login-initial-owner"); return;
            }
            if (resetBridgeAwaiting) {
                if (updateCallbacks != 1) return; // Actual bootstrap dispatch, not retained DOM flags alone.
                freshLoginAuth = authCallbacks; freshLoginCookieReads = currentCookieReads;
                freshLoginSignedOut = signedOutObservations; freshLoginInvalidations = authInvalidations;
                freshLoginPhase = 1;
                std::printf("T103_FRESH_LOGIN_BACK INITIAL_GET_LATCH=1 REAL_BRIDGE=1\n");
                host->back(); // No fixture permit, CDP steering, Cancel or manual completion.
                return;
            }
        } else {
            if (host->runtimeState() != WebRuntimeState::authRequired || completions != 2 ||
                !document.responses || !freshLoginDocuments[1].responses) return;
            const auto& list = freshLoginDocuments[1];
            if (starts != 3 || !document.loaded || !document.get || document.post ||
                list.responses != 1 || !list.get || list.post || list.loaded ||
                !freshLoginRedirectGeneration || list.generation != freshLoginRedirectGeneration ||
                list.generation <= freshLoginDocuments[0].generation || document.generation < list.generation ||
                document.navigation != list.navigation || document.navigation != lastStartedNavigationId ||
                document.navigation != lastCompletedNavigationId || document.generation != host->documentGeneration() ||
                !observedSuccess || observedStatus != 200 || observedError != CoreWebView2WebErrorStatus::Unknown ||
                host->currentUrl() != expectedUrl || to_string(view.CoreWebView2().Source()) != expectedUrl ||
                host->pendingAuthRecovery() != WebResponseDecision::ignore || updateCallbacks != 1 ||
                authCallbacks != freshLoginAuth || currentCookieReads != freshLoginCookieReads ||
                signedOutObservations != freshLoginSignedOut || authInvalidations != freshLoginInvalidations) {
                finish(false, "fresh-login-final-owner"); return;
            }
            if (freshLoginEditedAt && GetTickCount64() - freshLoginEditedAt < 200) return;
        }
        scriptPending = true;
        const auto phase = freshLoginPhase;
        const auto generation = host->documentGeneration();
        const auto queue = view.DispatcherQueue();
        // Only synthetic DOM booleans leave the page. The final form is edited, never submitted.
        const auto script = phase == 0 ? LR"JS((()=>{
          return document.getElementById('synthetic-marker')?.dataset.kind==='history-c' &&
            window.__grafDesktopBridgeInstalled===true && document.documentElement.dataset.syntheticNativeReady==='1';
        })())JS" : freshLoginEditedAt == 0 ? LR"JS((()=>{
          const form=document.getElementById('synthetic-form'), input=document.getElementById('synthetic-input');
          const rect=form?.getBoundingClientRect(), style=form && getComputedStyle(form);
          if(document.getElementById('synthetic-marker')?.dataset.kind!=='form' || !form || !input ||
             input.disabled || input.readOnly || !rect.width || !rect.height || style.display==='none' ||
             style.visibility==='hidden' || !input.getBoundingClientRect().width || !input.getBoundingClientRect().height ||
             getComputedStyle(input).visibility==='hidden' || window.__grafDesktopBridgeInstalled===true ||
             document.documentElement.dataset.syntheticNativeReady==='1' || location.pathname!=='/login' ||
             location.search!=='?next=%2Fdesktop%2Fmeetings') return false;
          input.focus(); input.value='synthetic-login-edit'; input.dispatchEvent(new Event('input',{bubbles:true}));
          const button=document.createElement('button'); button.type='button'; button.setAttribute('data-graf-app-update','');
          document.body.append(button); button.click(); button.remove();
          return document.activeElement===input && input.value==='synthetic-login-edit';
        })())JS" : LR"JS((()=>{
          const input=document.getElementById('synthetic-input');
          return document.getElementById('synthetic-marker')?.dataset.kind==='form' &&
            input?.value==='synthetic-login-edit' && !input.disabled && !input.readOnly &&
            window.__grafDesktopBridgeInstalled!==true && document.documentElement.dataset.syntheticNativeReady!=='1' &&
            location.pathname==='/login' && location.search==='?next=%2Fdesktop%2Fmeetings';
        })())JS";
        view.CoreWebView2().ExecuteScriptAsync(script).Completed([this, phase, generation, queue](auto const& operation, auto const&) {
            queue.TryEnqueue([this, phase, generation, operation] {
                scriptPending = false;
                if (probeExit != 2) return;
                try {
                    if (phase != freshLoginPhase || generation != host->documentGeneration()) {
                        finish(false, "fresh-login-dom-owner"); return;
                    }
                    if (operation.GetResults() != L"true") {
                        if (phase == 0) return; // Bootstrap/handshake is asynchronous; unchanged overall deadline applies.
                        finish(false, "fresh-login-editable-form"); return;
                    }
                    if (phase == 0) { requestHistoryResetBridge(); return; }
                    if (!freshLoginEditedAt) { freshLoginEditedAt = GetTickCount64(); return; }
                    if (starts != 3 || completions != 2 || updateCallbacks != 1 || authCallbacks != freshLoginAuth ||
                        currentCookieReads != freshLoginCookieReads || signedOutObservations != freshLoginSignedOut ||
                        authInvalidations != freshLoginInvalidations || host->runtimeState() != WebRuntimeState::authRequired ||
                        host->currentUrl() != origin + loginNext || to_string(view.CoreWebView2().Source()) != origin + loginNext) {
                        finish(false, "fresh-login-post-edit-authority"); return;
                    }
                    std::printf("T103_FRESH_LOGIN_FINAL SAME_NAV_REDIRECT=1 NATIVE_GET_302_200=1 EDIT_RETAINED=1 NEW_AUTHORITY=0\n");
                    finish(true, "fresh-list-same-navigation-login-form");
                } catch (...) { finish(false, "fresh-login-dom-result"); }
            });
        });
    }

    void checkDocument() {
        if (probeExit != 2 || !profileVerified || scriptPending || !view.CoreWebView2() || !completions) return;
        if (freshLoginScenario()) { checkFreshLogin(); return; }
        if (redirectHeldScenario() && historyPhase == 3) { checkRedirectHeld(); return; }
        if (redirectHeldScenario() && historyPhase == 4) { checkStaleReset(); return; }
        if (heldResetScenario() && historyPhase >= 3) { checkStaleReset(); return; }
        if (controlledHistoryScenario() && historyFixture.held) { checkHeldHistory(); return; }
        if (productionHistoryScenario()) { checkProductionHistory(); return; }
        if (historyResetScenario() && (resetBridgeAwaiting || (resetPending && resetCaptured))) { checkHistoryResetBridge(); return; }
        if (raceStartedAt) { checkHistoryRace(); return; }
        if (scenario == "cancel-before-start") { checkCancelledNavigation(); return; }
        if (cancelPhase && retainedHistoryScenario()) { checkCancelledNavigation(); return; }
        if (cancelPhase && sameDocumentScenario()) { checkSameDocument(); return; }
        if (historyScenario()) { checkHistoryDocument(); return; }
        const auto core = view.CoreWebView2();
        const auto generation = host->documentGeneration();
        const auto dispatcher = view.DispatcherQueue();
        scriptPending = true;
        // Only booleans about our synthetic DOM; no URL, cookies, nonce or text leaves the page.
        const auto script = LR"JS((() => {
          const marker = document.getElementById('synthetic-marker');
          const form = document.getElementById('synthetic-form');
          const input = document.getElementById('synthetic-input');
          const rect = form?.getBoundingClientRect();
          let bits = 0;
          if (marker?.dataset.kind === 'cabinet') bits |= 1;
          if (marker?.dataset.kind === 'form') bits |= 2;
          if (marker?.dataset.kind === 'error') bits |= 4;
          if (form && input && !input.disabled && rect.width > 0 && rect.height > 0 &&
              getComputedStyle(form).display !== 'none' && getComputedStyle(form).visibility !== 'hidden') bits |= 8;
          if (window.__grafDesktopBridgeInstalled === true) bits |= 16;
          if (document.documentElement.dataset.syntheticNativeReady === '1') bits |= 32;
          if (marker?.dataset.postAccepted === '1' && input?.value === 'synthetic-value') bits |= 64;
          return bits;
        })())JS";
        core.ExecuteScriptAsync(script).Completed([this, generation, dispatcher](auto const& operation, auto const&) {
            if (!dispatcher.TryEnqueue([this, generation, operation] {
                scriptPending = false;
                if (probeExit != 2 || generation != host->documentGeneration()) return;
                try {
                    const auto bits = std::stoi(to_string(operation.GetResults()));
                    const auto state = host->runtimeState();
                    if ((emailScenario() || scenario == "reselect") && !emailStarted) {
                        if (state == WebRuntimeState::ready && (bits & 49) == 49 && authCallbacks == 1) {
                            emailStarted = true;
                            authCallbacksBeforeEmail = authCallbacks;
                            sawTargetStatus = false;
                            (void)host->navigate(origin + "/desktop/settings/account/email-link/start");
                        }
                        return;
                    }
                    const bool noBridge = (bits & 48) == 0;
                    const bool recoveryScenario = scenario == "cabinet401" || scenario == "billing401" ||
                        scenario == "meeting401" || scenario == "reselect";
                    if (recoveryScenario && !recoveryActionRequested) {
                        const auto expectedStarts = scenario == "reselect" ? 2u : 1u;
                        if (starts > expectedStarts) { finish(false, "automatic-auth-navigation"); return; }
                        const auto expectedReason = scenario == "reselect" ? WebResponseDecision::workspaceReselection : WebResponseDecision::expiredSession;
                        if (host->pendingAuthRecovery() != expectedReason) return;
                        if (!noBridge) { finish(false, "recovery-native-authority"); return; }
                        if (starts != expectedStarts || observedStatus != (scenario == "reselect" ? 503u : 401u)) return;
                        if (recoveryObservedAt == 0) recoveryObservedAt = GetTickCount64();
                        if (GetTickCount64() - recoveryObservedAt < 200) return;
                        recoveryActionRequested = true;
                        std::printf("RECOVERY_EXPLICIT_ACTION=1 NAVIGATIONS_BEFORE_ACTION=%u\n", starts);
                        if (host->navigate(host->recoveryUrl()).decision != RouteDecision::allow)
                            finish(false, "recovery-action-route");
                        return;
                    }
                    if (scenario == "login-post400" && !formSubmitted) {
                        if (state == WebRuntimeState::authRequired && observedStatus == 200 && (bits & 10) == 10 && noBridge) {
                            formSubmitted = true;
                            const auto queue = view.DispatcherQueue();
                            view.CoreWebView2().ExecuteScriptAsync(
                                LR"JS(document.getElementById('synthetic-input').value='synthetic-value';document.getElementById('synthetic-form').requestSubmit();true;)JS")
                                .Completed([this, queue](auto const& submitted, auto const&) {
                                    queue.TryEnqueue([this, submitted] {
                                        if (probeExit != 2) return;
                                        try { (void)submitted.GetResults(); }
                                        catch (...) { finish(false, "synthetic-form-submit"); }
                                    });
                                });
                        }
                        return;
                    }
                    bool pass = false;
                    if (scenario == "initial200") {
                        pass = state == WebRuntimeState::ready && sawTargetStatus && (bits & 49) == 49;
                        pass = pass && currentCookieReads == 1 && signedOutObservations == 0 && authInvalidations == 0;
                        if (pass && updatePhase < 6) { checkUpdateBadge(); return; }
                        pass = pass && updatePhase == 6 && updateCallbacks == 1;
                        if (pass && localDurationPhase < 5) { checkLocalDurations(); return; }
                        pass = pass && localDurationPhase == 5;
                        if (pass && inventoryPhase < 5) { checkProtectedInventory(); return; }
                        pass = pass && inventoryPhase == 5;
                    }
                    else if (scenario == "login400" || scenario == "login429") pass = state == WebRuntimeState::authRequired && sawTargetStatus && (bits & 10) == 10 && noBridge;
                    else if (scenario == "login-post400") pass = state == WebRuntimeState::authRequired && sawTargetStatus &&
                        starts == 2 && formSubmitted && (bits & 74) == 74 && noBridge;
                    else if (scenario == "email503" || scenario == "email429") pass = state == WebRuntimeState::unprivileged && sawTargetStatus && (bits & 10) == 10 && noBridge;
                    else if (scenario == "email-json503") pass = state == WebRuntimeState::unavailable && sawTargetStatus &&
                        starts == 2 && host->failureDetail() == "document · 0x000001F7" && (bits & 10) == 0 && noBridge;
                    else if (scenario == "cabinet401" || scenario == "billing401" || scenario == "meeting401" || scenario == "reselect")
                        pass = state == WebRuntimeState::authRequired &&
                        (scenario == "reselect" ? (sawEmail503 && !saw401) : saw401) && observedStatus == 200 &&
                        starts == (scenario == "reselect" ? 3u : 2u) &&
                        authCallbacks == (scenario == "reselect" ? authCallbacksBeforeEmail + 1 : 1u) &&
                        currentCookieReads == (scenario == "reselect" ? 1u : 0u) &&
                        signedOutObservations == currentCookieReads && authInvalidations == 1 &&
                        host->currentUrl() == origin + loginNext && (bits & 10) == 10 && noBridge;
                    else if (scenario == "cabinet503") pass = state == WebRuntimeState::unavailable && sawTargetStatus &&
                        starts == 1 && host->failureDetail() == "document · 0x000001F7" && (bits & 4) != 0 && noBridge;
                    else if (scenario == "tls-failure" || scenario == "transport-reset") {
                        using Error = CoreWebView2WebErrorStatus;
                        const bool certificate = observedError == Error::CertificateCommonNameIsIncorrect ||
                            observedError == Error::CertificateExpired || observedError == Error::ClientCertificateContainsErrors ||
                            observedError == Error::CertificateRevoked || observedError == Error::CertificateIsInvalid;
                        const bool connection = observedError == Error::ConnectionReset || observedError == Error::ConnectionAborted ||
                            observedError == Error::Disconnected || observedError == Error::CannotConnect ||
                            observedError == Error::ErrorHttpInvalidServerResponse;
                        pass = state == WebRuntimeState::unavailable && sawTargetStatus && observedStatus == 0 &&
                            !observedSuccess && starts == 1 && authCallbacks == 0 && noBridge &&
                            (scenario == "tls-failure" ? certificate : connection);
                    }
                    if (pass && state == WebRuntimeState::authRequired)
                        pass = host->pendingAuthRecovery() == WebResponseDecision::ignore;
                    if (pass) {
                        std::printf("DOM_FLAGS=%d NATIVE_BRIDGE=%d HANDSHAKE=%d\n", bits, int((bits & 16) != 0), int((bits & 32) != 0));
                        finish(true, "actual-attach-document");
                    }
                } catch (hresult_error const& error) {
                    std::printf("SCRIPT_HRESULT=%08X\n", unsigned(error.code().value));
                    finish(false, "dom-read");
                } catch (...) { finish(false, "dom-result"); }
            })) {
                // No WinUI access from this completion thread. UI timer remains bounded.
            }
        });
    }

    void OnLaunched(LaunchActivatedEventArgs const&) {
        try {
            began = GetTickCount64();
            window = Window(); panel = Grid(); view = WebView2();
            view.Width(800); view.Height(600);
            panel.Children().Append(view);
            window.Content(panel); // Never Activate; no installed application/UI input.
            panel.Measure(Windows::Foundation::Size{800,600});
            panel.Arrange(Windows::Foundation::Rect{0,0,800,600});
            host = std::make_unique<WebView2Host>(WebViewRoutePolicy(origin));
            host->setRuntimeHandler([this](WebRuntimeState state) {
                std::printf("HOST_STATE=%d\n", int(state));
                if (accountHistoryScenario() && accountBoundAt && !accountUnavailableAt && state == WebRuntimeState::unavailable)
                    accountUnavailableAt = GetTickCount64();
                if (accountHistoryScenario() && accountUnavailableAt && historyPhase == 3 && state != WebRuntimeState::unavailable)
                    accountTerminalLost = true;
                if (historyResetScenario() && resetPending && resetCaptured && state != WebRuntimeState::ready)
                    resetLostAuthority = true;
                if (probeExit == 2 && ((cancelPhase == 1 && retainedHistoryScenario()) ||
                    (sameDocumentScenario() && cancelPhase > 0 && cancelPhase < 3)) && state != WebRuntimeState::ready)
                    controlLostAuthority = true;
            });
            host->setAuthSessionHandler([this](std::string token, bool currentCookieRead) {
                ++authCallbacks;
                if (accountHistoryScenario()) {
                    if (currentCookieRead) { ++currentCookieReads; if (token.empty()) ++signedOutObservations; }
                    else ++authInvalidations;
                    if (!currentCookieRead || token != "synthetic-history-session") {
                        finish(false, "account-boundary-real-cookie"); return;
                    }
                    if (accountCookieToken.empty()) {
                        accountCookieToken = std::move(token); // Only the actual native cookie observation supplies the bind token.
                        host->bindUserTimeAccount(origin, "11111111-1111-4111-8111-111111111111",
                            "22222222-2222-4222-8222-222222222222", accountCookieToken, 1);
                    } else if (token != accountCookieToken ||
                        !historyFixture.account(*host, accountCookieToken, accountBoundAt != 0))
                        finish(false, "account-boundary-cookie-rebound-account");
                    return; // Recovery observes B; it never rebinds the initial A context.
                }
                if (currentCookieRead) {
                    ++currentCookieReads;
                    if (token.empty()) ++signedOutObservations;
                    if ((scenario == "initial200" && token != "synthetic-inventory-session") ||
                        (scenario != "initial200" && !token.empty())) {
                        finish(false, "cookie-observation-token"); return;
                    }
                } else {
                    ++authInvalidations;
                    if (!token.empty()) { finish(false, "invalidation-retained-token"); return; }
                }
                if (scenario == "initial200" && token == "synthetic-inventory-session")
                    host->bindUserTimeAccount(origin, "11111111-1111-4111-8111-111111111111",
                        "22222222-2222-4222-8222-222222222222", std::move(token), 1);
            });
            if (scenario == "initial200") host->setUpdateHandler([this] {
                ++updateCallbacks; // Actual bridge dispatch only; never invokes an installer.
                if (updateCallbacks != 1 || updatePhase < 3) finish(false, "unexpected-update-dispatch");
            });
            if (freshLoginScenario()) host->setUpdateHandler([this] {
                ++updateCallbacks; // Harmless actual bridge callback only; no installer.
                if (freshLoginPhase != 0 || !resetBridgeAwaiting || updateCallbacks != 1 ||
                    host->runtimeState() != WebRuntimeState::ready ||
                    host->documentGeneration() != freshLoginDocuments[0].generation ||
                    host->currentUrl() != origin + initialPath || to_string(view.CoreWebView2().Source()) != origin + initialPath)
                    finish(false, "fresh-login-unexpected-bridge");
            });
            if (scenario == "cancel-before-start" || historyControlScenario() || historyEntryScenario()) host->setUpdateHandler([this] {
                ++updateCallbacks;
                const auto expected = sameDocumentScenario() ? cancelPhase : 1u;
                if ((sameDocumentScenario() ? cancelPhase < 1 || cancelPhase > 2 : cancelPhase != 1) ||
                    !cancelBridgeRequested || updateCallbacks != expected ||
                    host->runtimeState() != WebRuntimeState::ready || host->documentGeneration() != generationBeforeCancel)
                    finish(false, "cancelled-navigation-bridge-authority");
            });
            if (historyResetScenario()) host->setUpdateHandler([this] {
                // Harmless actual bridge dispatch only: no update service/installer is attached.
                ++updateCallbacks;
                if (!resetBridgeAwaiting || historyPhase < 3 || historyPhase > 6 ||
                    updateCallbacks != historyPhase - 2 || !resetVerified ||
                    host->runtimeState() != WebRuntimeState::ready ||
                    host->documentGeneration() != resetDocument.generation ||
                    lastStartedNavigationId != resetDocument.navigation || lastCompletedNavigationId != resetDocument.navigation ||
                    host->currentUrl() != to_string(view.CoreWebView2().Source()) ||
                    (resetPending && !historyResetOwner())) finish(false, "reset-bridge-authority");
            });
            if (productionHistoryScenario()) host->setUpdateHandler([this] {
                ++updateCallbacks; // Actual bootstrap dispatch only, never an installer.
                if ((heldResetScenario() || redirectHeldScenario()) && historyPhase >= 3) {
                    if (historyPhase != 4 || !staleRecoveryVerified || !resetBridgeAwaiting ||
                        updateCallbacks != heldUpdates + 1 || !staleResetRecoveryOwner())
                        finish(false, "stale-reset-unexpected-bridge");
                    return;
                }
                if (controlledHistoryScenario() && historyFixture.held) {
                    if (scenario != "history-pending-read-fence" || !heldButtonRequested ||
                        heldRetainedDispatches != 1 || updateCallbacks != heldUpdates + 1 || !heldHistoryOwner())
                        finish(false, "held-bridge-authority");
                    return;
                }
                if (!resetBridgeAwaiting || updateCallbacks != historyPhase + 1 + heldRetainedDispatches || !productionHistoryOwner())
                    finish(false, "host-history-real-bridge-authority");
            });
            // Register before attach: its own Initialized handler navigates synchronously.
            view.CoreWebView2Initialized([this](auto const& sender, auto const& initialized) {
                try {
                    if (FAILED(initialized.Exception()) || !sender.CoreWebView2()) { finish(false, "environment-init"); return; }
                    const auto core = sender.CoreWebView2();
                    const std::wstring actualProfile(core.Environment().UserDataFolder().c_str());
                    profileVerified = sameAbsolutePath(actualProfile, profilePath) &&
                        sameDirectoryIdentity(actualProfile, profilePath);
                    std::printf("PROFILE_EXACT_MATCH=%d NAVIGATIONS_BEFORE_CHECK=%u\n", int(profileVerified), starts);
                    if (!profileVerified || starts != 0) { core.Stop(); sender.Close(); finish(false, "profile-isolation"); return; }
                    core.NavigationCompleted([this](auto const&, auto const& event) {
                        if (redirectHeldScenario() && historyPhase == 3) {
                            if (responseMarkerExists(L"unexpected-http")) {
                                finish(false, "held-redirect-server-received-unexpected-get"); return;
                            }
                            if (event.NavigationId() != redirectHeldNavigation.id || redirectHeldNavigation.completed ||
                                !redirectReleased || !redirectHeldStarting || event.IsSuccess() ||
                                event.WebErrorStatus() != CoreWebView2WebErrorStatus::OperationCanceled) {
                                finish(false, "held-redirect-missing-same-id-cancelled-terminal"); return;
                            }
                            redirectHeldNavigation.completed = true;
                            redirectHeldNavigation.success = event.IsSuccess();
                            redirectHeldNavigation.error = event.WebErrorStatus();
                            ++completions;
                            lastCompletedNavigationId = event.NavigationId();
                            std::printf("T103_HELD_REDIRECT_COMPLETED nav=%llu success=0 error=%d\n",
                                static_cast<unsigned long long>(event.NavigationId()), int(event.WebErrorStatus()));
                            return; // Separate cancelled owner; do not overwrite the recovery document's observations.
                        }
                        if (freshLoginScenario()) {
                            std::printf("T103_FRESH_LOGIN_COMPLETED nav=%llu success=%d status=%d web_error=%d\n",
                                static_cast<unsigned long long>(event.NavigationId()), int(event.IsSuccess()),
                                event.HttpStatusCode(), int(event.WebErrorStatus()));
                            const auto index = completions == 0 ? 0u : 2u;
                            if (completions >= 2 || starts != (index == 0 ? 1u : 3u) ||
                                !freshLoginDocuments[index].navigation ||
                                event.NavigationId() != freshLoginDocuments[index].navigation ||
                                !event.IsSuccess() || event.HttpStatusCode() != 200 ||
                                event.WebErrorStatus() != CoreWebView2WebErrorStatus::Unknown) {
                                finish(false, "fresh-login-native-completion"); return;
                            }
                        }
                        if (controlledHistoryScenario() && historyFixture.held && scenario == "history-pending-read-fence") {
                            for (auto& attempt : heldCompetitors) if (attempt.id && attempt.id == event.NavigationId()) {
                                if (attempt.completed || event.HttpStatusCode() != 0) { finish(false, "held-competitor-completion"); return; }
                                attempt.completed = true; attempt.success = event.IsSuccess(); attempt.error = event.WebErrorStatus();
                                std::printf("T103_HELD_COMPETITOR_COMPLETED nav=%llu success=%d error=%d\n",
                                    static_cast<unsigned long long>(attempt.id), int(attempt.success), int(attempt.error));
                                return; // Separate per-ID observations; never overwrite accepted C's completion.
                            }
                            finish(false, "held-unmatched-completion"); return;
                        }
                        if (raceStartedAt) for (auto& item : raceNavigations) if (item.id == event.NavigationId()) {
                            item.completed = true; item.success = event.IsSuccess(); item.error = event.WebErrorStatus();
                        }
                        ++completions;
                        lastCompletedNavigationId = event.NavigationId();
                        // Test-only fence installed before the product completion/latch.
                        // It never sets ready/nonce or supplies metadata to production.
                        if (historyResetScenario() && historyPhase == 3) resetPending = true;
                        observedStatus = unsigned(event.HttpStatusCode());
                        observedError = event.WebErrorStatus();
                        observedSuccess = event.IsSuccess();
                        saw401 = saw401 || observedStatus == 401;
                        if (emailNavigationId != 0 && event.NavigationId() == emailNavigationId && observedStatus == 503)
                            sawEmail503 = true;
                        sawTargetStatus = sawTargetStatus || observedStatus == targetStatus();
                        std::printf("DOCUMENT_COMPLETED nav=%llu status=%u success=%d web_error=%d\n",
                            static_cast<unsigned long long>(event.NavigationId()), observedStatus,
                            int(event.IsSuccess()), int(event.WebErrorStatus()));
                        if (completionFailureDiagnostic && probeExit == 2) {
                            if (!event.NavigationId() || starts != 1 || completions != 1 ||
                                !event.IsSuccess() || observedStatus != 200 ||
                                observedError != CoreWebView2WebErrorStatus::Unknown) {
                                finish(false, "teardown-control-precondition"); return;
                            }
                            traceTeardown("completion-enter");
                            // Fixture lifetime control, never a product navigation/authority result.
                            finish(false, "controlled-teardown-failure");
                            traceTeardown("completion-return");
                            return;
                        }
                    });
                    core.ContentLoading([this](auto const&, auto const& event) {
                        if (redirectHeldScenario() && historyPhase == 3) {
                            if (!redirectReleased || event.NavigationId() != redirectHeldNavigation.id) {
                                finish(false, "held-redirect-content-before-release"); return;
                            }
                            redirectHeldNavigation.loaded = true;
                            return; // A late browser document/error page is not accepted native authority.
                        }
                        if (freshLoginScenario()) {
                            auto& document = freshLoginDocuments[freshLoginPhase == 0 ? 0 : 2];
                            if (!document.navigation || document.loaded || event.NavigationId() != document.navigation || event.IsErrorPage()) {
                                finish(false, "fresh-login-native-content"); return;
                            }
                            document.loaded = true;
                        }
                        if (controlledHistoryScenario() && historyFixture.held && scenario == "history-pending-read-fence") {
                            for (auto& attempt : heldCompetitors) if (attempt.id == event.NavigationId()) attempt.loaded = true;
                            finish(false, "held-competitor-replaced-document"); return;
                        }
                        if (historyEntryScenario() && cancelPhase == 1) {
                            finish(false, "production-history-denial-replaced-document"); return;
                        }
                        if (historyEntryScenario() && cancelPhase == 2) {
                            if (event.NavigationId() != resetDocument.navigation) { finish(false, "production-history-next-get-content"); return; }
                            resetDocument.loaded = true;
                        }
                        if (productionHistoryScenario()) observeProductionCommit(event.NavigationId());
                        if (historyResetScenario()) {
                            if (resetPending || event.NavigationId() != resetDocument.navigation) {
                                finish(false, "reset-unexpected-content-loading"); return;
                            }
                            resetDocument.loaded = true;
                        }
                        if (raceStartedAt) {
                            for (auto& item : raceNavigations) if (item.id == event.NavigationId()) item.loaded = true;
                            std::printf("RACE_CONTENT_LOADING nav=%llu\n", static_cast<unsigned long long>(event.NavigationId()));
                        }
                    });
                    if (historyResetScenario() || productionHistoryScenario() || historyEntryScenario()) core.WebResourceResponseReceived([this](auto const&, auto const& args) {
                        try {
                            if (historyEntryScenario() && cancelPhase != 2) return;
                            const auto request = args.Request();
                            const auto headers = request.Headers();
                            if (!headers.Contains(L"Sec-Fetch-Dest") || headers.GetHeader(L"Sec-Fetch-Dest") != L"document") return;
                            if (redirectHeldScenario() && args.Response().StatusCode() == 302) {
                                const auto responseHeaders = args.Response().Headers();
                                if (!redirectReleased || ++redirectHeldResponses != 1 || request.Method() != L"GET" ||
                                    to_string(request.Uri()) != origin + "/desktop/meetings" || headers.Contains(L"X-GRAF-History-Intent") ||
                                    !headers.Contains(L"X-GRAF-Desktop-Navigation") ||
                                    to_string(headers.GetHeader(L"X-GRAF-Desktop-Navigation")) != std::to_string(staleResetGeneration) ||
                                    !responseHeaders.Contains(L"Location") || to_string(responseHeaders.GetHeader(L"Location")) != loginNext) {
                                    finish(false, "held-redirect-real-302-owner"); return;
                                }
                                return; // Observe the old actual response, never feed it into the product latch.
                            }
                            const auto path = historyPhase == 1 ? "/desktop/meetings/11111111-1111-4111-8111-111111111111" :
                                historyPhase == 2 || historyPhase == 4 || historyPhase == 6 ?
                                "/desktop/meetings/33333333-3333-4333-8333-333333333333" : "/desktop/meetings";
                            const auto generation = host->documentGeneration();
                            const auto expectedUrl = historyEntryScenario() ? origin + "/desktop/meetings" :
                                productionHistoryScenario() ? productionHistoryUrl() : origin + path;
                            if ((resetPending && resetCaptured) || historyPhase > 6 || to_string(request.Uri()) != expectedUrl ||
                                (scenario == "history-get-repeated-url" && headers.Contains(L"X-GRAF-History-Intent")) ||
                                !headers.Contains(L"X-GRAF-Desktop-Navigation") ||
                                to_string(headers.GetHeader(L"X-GRAF-Desktop-Navigation")) != std::to_string(generation) ||
                                args.Response().StatusCode() != 200 || !headers.Contains(L"Sec-Fetch-Mode") ||
                                headers.GetHeader(L"Sec-Fetch-Mode") != L"navigate" ||
                                resetDocument.navigation != lastStartedNavigationId || ++resetDocument.responses != 1) {
                                finish(false, "reset-native-final-response"); return;
                            }
                            resetDocument.generation = generation;
                            resetDocument.get = request.Method() == L"GET";
                            resetDocument.post = request.Method() == L"POST";
                            if ((productionHistoryScenario() || historyEntryScenario()) &&
                                (resetDocument.post != (quarantineHistoryScenario() && historyPhase == 1) ||
                                 resetDocument.get != !(quarantineHistoryScenario() && historyPhase == 1))) {
                                finish(false, "host-history-unexpected-method"); return;
                            }
                            std::printf("T103_RESET_RESPONSE phase=%u nav=%llu GENERATION_TAG_MATCH=1 GET=%d POST=%d\n",
                                historyPhase, static_cast<unsigned long long>(resetDocument.navigation),
                                int(resetDocument.get), int(resetDocument.post));
                        } catch (...) { finish(false, "reset-native-response-observation"); }
                    });
                    if (freshLoginScenario()) core.WebResourceResponseReceived([this](auto const&, auto const& args) {
                        try {
                            const auto request = args.Request();
                            const auto headers = request.Headers();
                            if (!headers.Contains(L"Sec-Fetch-Dest") || headers.GetHeader(L"Sec-Fetch-Dest") != L"document") return;
                            const auto url = to_string(request.Uri());
                            const unsigned index = url == origin + initialPath ? 0u : url == origin + "/desktop/meetings" ? 1u : 2u;
                            auto& document = freshLoginDocuments[index];
                            const auto response = args.Response();
                            const auto responseHeaders = response.Headers();
                            const auto generation = index == 1 && freshLoginRedirectGeneration ?
                                freshLoginRedirectGeneration : host->documentGeneration();
                            if ((index == 2 && url != origin + loginNext) || !document.navigation || !generation ||
                                ++document.responses != 1 || request.Method() != L"GET" ||
                                !headers.Contains(L"Sec-Fetch-Mode") || headers.GetHeader(L"Sec-Fetch-Mode") != L"navigate" ||
                                !headers.Contains(L"X-GRAF-Desktop-Navigation") ||
                                to_string(headers.GetHeader(L"X-GRAF-Desktop-Navigation")) != std::to_string(generation) ||
                                response.StatusCode() != (index == 1 ? 302 : 200) ||
                                (index == 1 ? !responseHeaders.Contains(L"Location") ||
                                    to_string(responseHeaders.GetHeader(L"Location")) != loginNext :
                                    !responseHeaders.Contains(L"Content-Type") ||
                                    to_string(responseHeaders.GetHeader(L"Content-Type")) != "text/html; charset=utf-8")) {
                                finish(false, "fresh-login-native-response"); return;
                            }
                            document.generation = generation; document.get = true;
                            std::printf("T103_FRESH_LOGIN_RESPONSE slot=%u nav=%llu generation=%llu GET=1 status=%d TAG_MATCH=1\n",
                                index, static_cast<unsigned long long>(document.navigation),
                                static_cast<unsigned long long>(generation), response.StatusCode());
                        } catch (...) { finish(false, "fresh-login-response-observation"); }
                    });
                    if (historyResetScenario()) core.FrameNavigationStarting([this](auto const&, auto const& event) {
                        if (resetPending) { event.Cancel(true); finish(false, "reset-interval-frame-navigation"); }
                    });
                    // Isolation fence only; never provides response metadata or calls the host latch.
                    core.AddWebResourceRequestedFilter(L"*", CoreWebView2WebResourceContext::All,
                        CoreWebView2WebResourceRequestSourceKinds::All);
                    core.WebResourceRequested([this](auto const& senderCore, auto const& args) {
                        try {
                            if (accountHistoryScenario() && accountBoundAt && historyPhase == 3) {
                                const auto request = args.Request();
                                const auto requestUrl = to_string(request.Uri());
                                if (requestUrl.rfind("https://", 0) == 0 || requestUrl.rfind("http://", 0) == 0) {
                                    if (redirectHeldScenario() && redirectReleased) {
                                        const bool sameOrigin = host->routePolicy().sharesOrigin(requestUrl);
                                        const auto method = request.Method();
                                        const char* pathCategory = requestUrl == origin + loginNext ? "login" :
                                            requestUrl == origin + "/desktop/meetings" ? "list" :
                                            requestUrl == origin + "/desktop/meetings/11111111-1111-4111-8111-111111111111" ||
                                            requestUrl == origin + "/desktop/meetings/33333333-3333-4333-8333-333333333333" ? "detail" : "other";
                                        std::printf("T103_HELD_REDIRECT_REQUEST_ATTEMPT same_origin=%d path=%s method=%s context=%d\n",
                                            int(sameOrigin), pathCategory, method == L"GET" ? "GET" : method == L"POST" ? "POST" : "other",
                                            int(args.ResourceContext()));
                                        if (sameOrigin && requestUrl == origin + loginNext && method == L"GET" &&
                                            args.ResourceContext() == CoreWebView2WebResourceContext::Document && ++redirectLoginAttempts == 1)
                                            return; // Notification only: let the later product subscriber run before any verdict.
                                    }
                                    finish(false, "account-boundary-http-before-reload"); return;
                                }
                            }
                            if (redirectHeldScenario() && historyPhase == 3) {
                                const auto request = args.Request();
                                const auto requestUrl = to_string(request.Uri());
                                if (requestUrl.rfind("https://", 0) == 0 || requestUrl.rfind("http://", 0) == 0) {
                                    if (redirectHeldRequest || request.Method() != L"GET" ||
                                        requestUrl != origin + "/desktop/meetings" ||
                                        request.Headers().Contains(L"X-GRAF-History-Intent") || !redirectHeldNavigation.id) {
                                        finish(false, "held-redirect-not-single-unmarked-get"); return;
                                    }
                                    redirectHeldRequest = true;
                                }
                            }
                            if (freshLoginScenario() && args.Request().Method() != L"GET") {
                                finish(false, "fresh-login-unexpected-non-get"); return;
                            }
                            if (productionHistoryScenario() && args.Request().Method() == L"POST" &&
                                (!quarantineHistoryScenario() || historyPhase != 1 || productionPostSeen ||
                                 to_string(args.Request().Uri()) != productionHistoryUrl())) {
                                finish(false, "host-history-unexpected-post-request"); return;
                            }
                            if (productionHistoryScenario() && args.Request().Method() == L"POST") productionPostSeen = true;
                            if (!host->routePolicy().sharesOrigin(to_string(args.Request().Uri()))) {
                                args.Response(senderCore.Environment().CreateWebResourceResponse(nullptr, 403, L"Synthetic only", L"Content-Length: 0"));
                            }
                        } catch (...) { finish(false, "resource-isolation"); }
                    });
                } catch (hresult_error const& error) {
                    std::printf("ISOLATION_HRESULT=%08X\n", unsigned(error.code().value));
                    finish(false, "isolation-handler");
                }
            });
            view.NavigationStarting([this](auto const&, auto const& event) {
                if (redirectHeldScenario() && historyPhase == 3 && event.IsRedirected()) {
                    if (!redirectReleased || redirectHeldPhase != 2 || redirectHeldStarting || redirectHeldNavigation.completed ||
                        event.NavigationId() != redirectHeldNavigation.id || to_string(event.Uri()) != origin + loginNext ||
                        event.NavigationKind() == CoreWebView2NavigationKind::BackOrForward ||
                        event.RequestHeaders().Contains(L"X-GRAF-History-Intent")) {
                        finish(false, "held-redirect-real-start-owner"); return;
                    }
                    redirectHeldStarting = true;
                    ++starts;
                    lastStartedNavigationId = event.NavigationId();
                    std::printf("T103_HELD_REDIRECT_START nav=%llu redirected=1 FIXTURE_CANCEL=0\n",
                        static_cast<unsigned long long>(event.NavigationId()));
                    return; // Observe only; the later production subscriber must reject this unowned redirect.
                }
                if (controlledHistoryScenario() && historyFixture.held && scenario == "history-pending-read-fence") {
                    if (!heldAttemptSent || heldAttempt >= heldCompetitors.size() || heldCompetitors[heldAttempt].id ||
                        event.NavigationId() == 0 || event.NavigationId() == lastStartedNavigationId || event.IsRedirected() ||
                        to_string(event.Uri()) != origin + "/desktop/meetings/11111111-1111-4111-8111-111111111111" ||
                        (event.NavigationKind() == CoreWebView2NavigationKind::BackOrForward) != (heldAttempt == 0)) {
                        finish(false, "held-competitor-start"); return;
                    }
                    for (const auto& attempt : heldCompetitors)
                        if (attempt.id == event.NavigationId()) { finish(false, "held-duplicate-navigation-id"); return; }
                    heldCompetitors[heldAttempt].id = event.NavigationId();
                    std::printf("T103_HELD_COMPETITOR_START ordinal=%u nav=%llu FIXTURE_CANCEL=0\n", heldAttempt,
                        static_cast<unsigned long long>(event.NavigationId()));
                    return; // Observer only: the later production subscriber must cancel it.
                }
                ++starts;
                lastStartedNavigationId = event.NavigationId();
                if (freshLoginScenario()) {
                    const auto index = starts - 1;
                    const auto expectedUrl = origin + (index == 0 ? initialPath : index == 1 ? "/desktop/meetings" : loginNext);
                    if (index >= freshLoginDocuments.size() || !event.NavigationId() ||
                        freshLoginPhase != (index == 0 ? 0u : 1u) || to_string(event.Uri()) != expectedUrl ||
                        event.NavigationKind() == CoreWebView2NavigationKind::BackOrForward ||
                        event.IsRedirected() != (index == 2) ||
                        (index == 1 && event.NavigationId() == freshLoginDocuments[0].navigation) ||
                        (index == 2 && event.NavigationId() != freshLoginDocuments[1].navigation)) {
                        finish(false, "fresh-login-native-start"); return;
                    }
                    freshLoginDocuments[index].navigation = event.NavigationId();
                    if (index == 2) {
                        freshLoginRedirectGeneration = host->documentGeneration(); // Actual list request owner, before the host processes redirect.
                        if (freshLoginDocuments[1].responses && freshLoginDocuments[1].generation != freshLoginRedirectGeneration) {
                            finish(false, "fresh-login-redirect-owner"); return;
                        }
                    }
                    std::printf("T103_FRESH_LOGIN_START slot=%u nav=%llu kind=%d redirected=%d FIXTURE_CANCEL=0 HISTORY_INTENT_PRESENT=%d\n",
                        index, static_cast<unsigned long long>(event.NavigationId()), int(event.NavigationKind()), int(event.IsRedirected()),
                        int(event.RequestHeaders().Contains(L"X-GRAF-History-Intent")));
                }
                if (historyEntryScenario() && cancelPhase == 2) {
                    if (event.IsRedirected() || event.NavigationKind() == CoreWebView2NavigationKind::BackOrForward ||
                        to_string(event.Uri()) != origin + "/desktop/meetings") {
                        finish(false, "production-history-next-get-start"); return;
                    }
                    resetDocument = {};
                    resetDocument.navigation = event.NavigationId();
                }
                if (productionHistoryScenario()) {
                    // Observe only: no fixture navigation cancellation/permit/reset in these cases.
                    std::printf("T103_HOST_HISTORY_START phase=%u nav=%llu kind=%d HISTORY_INTENT_PRESENT=%d\n",
                        historyPhase, static_cast<unsigned long long>(event.NavigationId()), int(event.NavigationKind()),
                        int(event.RequestHeaders().Contains(L"X-GRAF-History-Intent")));
                    const bool bf = quarantineHistoryScenario() ? historyPhase >= 5 : historyPhase >= 3;
                    if (event.IsRedirected() || starts != historyPhase + 1 + (redirectHeldScenario() && historyPhase == 4 ? 1u : 0u) ||
                        (scenario == "history-get-repeated-url" && (!event.NavigationId() || event.RequestHeaders().Contains(L"X-GRAF-History-Intent"))) ||
                        to_string(event.Uri()) != productionHistoryUrl() ||
                        (event.NavigationKind() == CoreWebView2NavigationKind::BackOrForward) != bf) {
                        finish(false, "host-history-unexpected-start"); return;
                    }
                    resetDocument = {};
                    resetDocument.navigation = event.NavigationId();
                    if (redirectHeldScenario() && historyPhase == 3) {
                        if (!event.NavigationId() || redirectHeldNavigation.id ||
                            event.RequestHeaders().Contains(L"X-GRAF-History-Intent")) {
                            finish(false, "held-redirect-initial-start-owner"); return;
                        }
                        redirectHeldNavigation.id = event.NavigationId();
                    }
                }
                if (historyResetScenario()) {
                    if (resetPending) {
                        event.Cancel(true); // Test-only ALL navigation fence, before the production subscriber.
                        finish(false, "reset-interval-navigation"); return;
                    }
                    if (event.IsRedirected() || (historyPhase >= 5 && event.NavigationKind() != CoreWebView2NavigationKind::BackOrForward)) {
                        event.Cancel(true); finish(false, "reset-unexpected-navigation-kind"); return;
                    }
                    resetDocument = {};
                    resetDocument.navigation = event.NavigationId();
                }
                if (!profileVerified || !host->routePolicy().sharesOrigin(to_string(event.Uri()))) {
                    event.Cancel(true); finish(false, "unexpected-navigation"); return;
                }
                if (raceStartedAt) {
                    const bool candidate = event.NavigationKind() == CoreWebView2NavigationKind::BackOrForward &&
                        to_string(event.Uri()) == origin + "/desktop/meetings" && !event.IsRedirected();
                    if (!candidate || raceStarts >= raceNavigations.size() ||
                        raceNavigations[0].id == event.NavigationId()) {
                        raceUnexpected = true; event.Cancel(true);
                    } else {
                        auto& item = raceNavigations[raceStarts++];
                        item.id = event.NavigationId();
                        if (raceStarts == 2) event.Cancel(true);
                    }
                    std::printf("RACE_START nav=%llu kind=%d cancel=%d ordinal=%u candidate=%d\n",
                        static_cast<unsigned long long>(event.NavigationId()), int(event.NavigationKind()),
                        int(event.Cancel()), raceStarts, int(candidate));
                }
                if (emailStarted && to_string(event.Uri()) == origin + "/desktop/settings/account/email-link/start")
                    emailNavigationId = event.NavigationId();
                if (historyEntryScenario() && cancelPhase == 1) {
                    if (cancelledNavigationId || event.IsRedirected() || to_string(event.Uri()) != origin + "/desktop/meetings" ||
                        event.NavigationKind() != CoreWebView2NavigationKind::BackOrForward) {
                        finish(false, "production-history-denial-unexpected-start"); return;
                    }
                    cancelledNavigationId = event.NavigationId();
                    std::printf("HISTORY_UNSOLICITED_START=1 KIND=%d EXPECT_PRODUCTION_CANCEL=1 FIXTURE_CANCEL=0\n",
                        int(event.NavigationKind()));
                    // Intentionally no event.Cancel: the production subscriber owns denial.
                }
                if (historyCancelScenario() && cancelPhase == 1) {
                    const auto target = origin + (scenario == "cancel-history-host" ?
                        "/desktop/meetings/11111111-1111-4111-8111-111111111111" : "/desktop/meetings");
                    if (cancelledNavigationId || to_string(event.Uri()) != target ||
                        event.NavigationKind() != CoreWebView2NavigationKind::BackOrForward) {
                        event.Cancel(true); finish(false, "history-cancel-unexpected-start"); return;
                    }
                    cancelledNavigationId = event.NavigationId();
                    event.Cancel(true);
                    std::printf("HISTORY_CANCEL_BEFORE_PRODUCT=1 KIND=%d DRIVER=%s\n", int(event.NavigationKind()),
                        scenario == "cancel-history-host" ? "host-back" : "script-go-minus-two");
                }
                if (scenario == "cancel-before-start" && cancelPhase == 1 && to_string(event.Uri()) ==
                    origin + "/desktop/meetings/11111111-1111-4111-8111-111111111111") {
                    cancelledNavigationId = event.NavigationId();
                    event.Cancel(true); // Before the product's NavigationStarting subscriber.
                    std::puts("CANCEL_BEFORE_PRODUCT_START=1");
                }
                std::printf("DOCUMENT_START nav=%llu redirected=%d\n",
                    static_cast<unsigned long long>(event.NavigationId()), int(event.IsRedirected()));
            });
            (void)host->navigate(origin + initialPath);
            timer = view.DispatcherQueue().CreateTimer();
            timer.Interval(std::chrono::milliseconds(100));
            timer.Tick([this](auto const&, auto const&) {
                if (closingAt != 0) {
                    const auto exitState = browserExit.load();
                    if (exitState != 0) {
                        if (exitState != 1) probeExit = 1;
                        std::puts(exitState == 1 ? "T103_BROWSER_EXITED=PASS" : "T103_BROWSER_EXITED=UNEXPECTED");
                        exitProbe();
                    } else if (GetTickCount64() - closingAt >= 10000) {
                        probeExit = 1;
                        std::puts("T103_BROWSER_EXITED=TIMEOUT");
                        exitProbe();
                    }
                    return;
                }
                if (browserExit.load() != 0) { finish(false, "early-browser-exit"); return; }
                if (GetTickCount64() - began >= 20000) { finish(false, "deadline"); return; }
                checkDocument();
            });
            timer.Start();
            CoreWebView2EnvironmentOptions options;
            std::wstring arguments = L"--host-resolver-rules=\"MAP graf.test 127.0.0.1\" --no-proxy-server --disable-background-networking";
            if (scenario != "tls-failure") arguments += L" --ignore-certificate-errors";
            options.AdditionalBrowserArguments(arguments);
            const auto dispatcher = view.DispatcherQueue();
            CoreWebView2Environment::CreateWithOptionsAsync({}, profilePath, options).Completed(
                [this, dispatcher](auto const& operation, auto const&) {
                    dispatcher.TryEnqueue([this, operation] {
                        if (probeExit != 2) return;
                        try {
                            environment = operation.GetResults();
                            const std::wstring actual(environment.UserDataFolder().c_str());
                            const bool matches = sameAbsolutePath(actual, profilePath) &&
                                sameDirectoryIdentity(actual, profilePath);
                            std::printf("ENVIRONMENT_PROFILE_MATCH=%d CONTROLLER_CREATED=0\n", int(matches));
                            if (!matches) { finish(false, "environment-profile"); return; }
                            browserExitToken = environment.BrowserProcessExited([this](auto const&, auto const& args) {
                                browserExit.store(closing.load() &&
                                    args.BrowserProcessExitKind() == CoreWebView2BrowserProcessExitKind::Normal ? 1 : 2);
                            });
                            exitSubscribed = true;
                            // Sole lifecycle authority: actual product events and bootstrap.
                            host->attach(view, environment);
                        } catch (hresult_error const& error) {
                            std::printf("ENVIRONMENT_HRESULT=%08X\n", unsigned(error.code().value));
                            finish(false, "explicit-environment");
                        } catch (...) { finish(false, "explicit-environment"); }
                    });
                });
        } catch (hresult_error const& error) {
            std::printf("INITIALIZE_HRESULT=%08X\n", unsigned(error.code().value));
            finish(false, "initialize");
        }
    }
};
}

int wmain(int argc, wchar_t** argv) {
    if (argc != 5 && argc != 6) return 2;
    profilePath = argv[1]; origin = to_string(argv[2]); scenario = to_string(argv[3]);
    if (argc == 6) {
        if (scenario != "initial200" || std::wstring_view(argv[5]) != L"--fail-completion") return 2;
        completionFailureDiagnostic = true;
    }
    bool known = false;
    for (const auto name : {"history-get-repeated-url", "history-host-ordinary-back", "initial200", "login400", "email503", "cabinet401", "cabinet503", "login429", "email429",
        "email-json503", "reselect", "billing401", "meeting401", "transport-reset", "tls-failure", "login-post400",
        "history-get", "history-post", "history-entry", "history-entry-same-url", "cancel-before-start", "history-host-same-url",
        "cancel-history-host", "cancel-history-script", "history-same-document", "history-race-native-first", "history-race-script-first", "history-reset",
        "history-host-get", "history-host-quarantine", "history-pending-read-fence", "history-terminal-held", "history-fresh-login-redirect", "history-reset-stale-readback", "history-reset-account-boundary", "history-account-boundary-redirect-held"})
        known = known || scenario == name;
    if (!known) return 2;
    if (scenario.rfind("login", 0) == 0 || scenario == "tls-failure" || scenario == "transport-reset") initialPath = "/login";
    else if (freshLoginScenario()) initialPath = "/desktop/meetings/33333333-3333-4333-8333-333333333333";
    else if (scenario == "billing401") {
        initialPath = "/billing?source=synthetic#details";
        loginNext = "/login?next=%2Fbilling";
    } else if (scenario == "meeting401") {
        initialPath = "/desktop/meetings/11111111-1111-4111-8111-111111111111?view=synthetic#details";
        loginNext = "/login?next=%2Fdesktop%2Fmeetings%2F11111111-1111-4111-8111-111111111111";
    }
    if (origin.rfind("https://graf.test:", 0) != 0 || profilePath.empty()) return 2;
    UINT32 identityLength = 0;
    if (GetCurrentPackageFullName(&identityLength, nullptr) != APPMODEL_ERROR_NO_PACKAGE) return 3;
    const auto attributes = GetFileAttributesW(profilePath.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_REPARSE_POINT) ||
        !(attributes & FILE_ATTRIBUTE_DIRECTORY) || !std::filesystem::is_empty(profilePath)) return 3;
    const auto bootstrap = LoadLibraryW(argv[4]);
    if (!bootstrap) return 4;
    using Initialize = HRESULT(WINAPI*)(UINT32, PCWSTR, PACKAGE_VERSION, UINT32);
    const auto initialize = reinterpret_cast<Initialize>(GetProcAddress(bootstrap, "MddBootstrapInitialize2"));
    if (!initialize) return 4;
    const auto hr = initialize(0x00020000, L"", PACKAGE_VERSION{}, 0);
    if (FAILED(hr)) { std::printf("BOOTSTRAP_HRESULT=%08X\n", unsigned(hr)); return 4; }
    try {
        init_apartment(apartment_type::single_threaded);
        Application::Start([](auto&&) { make<ProbeApp>(); });
        if (completionFailureDiagnostic) std::puts("T103_TEARDOWN_APPLICATION_RETURN=1");
    } catch (hresult_error const& error) { std::printf("APPLICATION_HRESULT=%08X\n", unsigned(error.code().value)); }
    return probeExit;
}
