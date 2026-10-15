// Native T103 regression. Real WebView2Host::attach; no manual latch/nonce wiring.
#include "../../RecApp/Web/WebView2Host.h"
#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <windows.h>
#include <appmodel.h>
#include <cstdio>
#include <filesystem>

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::Web::WebView2::Core;
using namespace graf::windows;

namespace graf::windows {
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

bool emailScenario() {
    return scenario == "email503" || scenario == "email429" || scenario == "email-json503";
}

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
    bool recoveryActionRequested = false;
    ULONGLONG recoveryObservedAt = 0;
    unsigned starts = 0, completions = 0, observedStatus = 0;
    unsigned authCallbacks = 0;
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

    void finish(bool pass, const char* reason) {
        if (probeExit != 2) return;
        probeExit = pass ? 0 : 1;
        std::printf("T103_NATIVE case=%s result=%s reason=%s profile_verified=%d starts=%u completions=%u status=%u state=%d\n",
            scenario.c_str(), pass ? "PASS" : "FAIL", reason, int(profileVerified), starts,
            completions, observedStatus, host ? int(host->runtimeState()) : -1);
        std::fflush(stdout);
        closingAt = GetTickCount64();
        closing.store(true);
        try { if (host) host->close(); } catch (...) { probeExit = 1; }
        try { if (view) view.Close(); } catch (...) { probeExit = 1; }
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
        } catch (...) { probeExit = 1; }
        try { if (window) window.Close(); } catch (...) { probeExit = 1; }
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
            r.canOpen === false && r.canSend === false && r.canDelete === false &&
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
                    if (result != L"1") { finish(false, "protected-inventory-wire"); return; }
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

    void checkDocument() {
        if (probeExit != 2 || !profileVerified || scriptPending || !view.CoreWebView2() || !completions) return;
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
            host->setRuntimeHandler([](WebRuntimeState state) { std::printf("HOST_STATE=%d\n", int(state)); });
            host->setAuthSessionHandler([this](std::string token) {
                ++authCallbacks;
                if (scenario == "initial200" && token == "synthetic-inventory-session")
                    host->bindUserTimeAccount(origin, "11111111-1111-4111-8111-111111111111",
                        "22222222-2222-4222-8222-222222222222", std::move(token), 1);
            });
            if (scenario == "initial200") host->setUpdateHandler([this] {
                ++updateCallbacks; // Actual bridge dispatch only; never invokes an installer.
                if (updateCallbacks != 1 || updatePhase < 3) finish(false, "unexpected-update-dispatch");
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
                        ++completions;
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
                    });
                    // Isolation fence only; never provides response metadata or calls the host latch.
                    core.AddWebResourceRequestedFilter(L"*", CoreWebView2WebResourceContext::All,
                        CoreWebView2WebResourceRequestSourceKinds::All);
                    core.WebResourceRequested([this](auto const& senderCore, auto const& args) {
                        try {
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
                ++starts;
                if (!profileVerified || !host->routePolicy().sharesOrigin(to_string(event.Uri()))) {
                    event.Cancel(true); finish(false, "unexpected-navigation"); return;
                }
                if (emailStarted && to_string(event.Uri()) == origin + "/desktop/settings/account/email-link/start")
                    emailNavigationId = event.NavigationId();
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
    if (argc != 5) return 2;
    profilePath = argv[1]; origin = to_string(argv[2]); scenario = to_string(argv[3]);
    bool known = false;
    for (const auto name : {"initial200", "login400", "email503", "cabinet401", "cabinet503", "login429", "email429",
        "email-json503", "reselect", "billing401", "meeting401", "transport-reset", "tls-failure", "login-post400"})
        known = known || scenario == name;
    if (!known) return 2;
    if (scenario.rfind("login", 0) == 0 || scenario == "tls-failure" || scenario == "transport-reset") initialPath = "/login";
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
    } catch (hresult_error const& error) { std::printf("APPLICATION_HRESULT=%08X\n", unsigned(error.code().value)); }
    return probeExit;
}
