#include "WebView2Host.h"

#include "../Contracts/WindowsDesktopContracts.h"
#include <cstdio>
#include <algorithm>

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
#include <winrt/Windows.Data.Json.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Microsoft.Web.WebView2.Core.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <windows.h>
#include <combaseapi.h>
#include <commdlg.h>
#include <knownfolders.h>
#include <shlobj.h>
#include <shellapi.h>

#include <filesystem>
#include <iterator>
#include <cmath>
#include <optional>
#endif

namespace graf::windows {

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
namespace {

constexpr double kJsonSafeIntegerMax = 9'007'199'254'740'991.0;
constexpr double kJsonVersionMax = 4'294'967'295.0;

std::string utf8(winrt::hstring const& value) {
    return winrt::to_string(std::wstring_view(value));
}

bool isJsonUnsignedInteger(double value, double maximum) noexcept {
    return std::isfinite(value) && value >= 0.0 && value <= maximum &&
        value <= kJsonSafeIntegerMax && std::floor(value) == value;
}

std::string newNonce() {
    GUID guid{};
    if (FAILED(CoCreateGuid(&guid))) return {};
    wchar_t value[40]{};
    if (StringFromGUID2(guid, value, static_cast<int>(std::size(value))) == 0) return {};
    return utf8(winrt::hstring(value));
}

std::filesystem::path webViewUserDataFolder() {
    PWSTR raw = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DEFAULT, nullptr, &raw)) || raw == nullptr) {
        return {};
    }
    std::filesystem::path result(raw);
    CoTaskMemFree(raw);
    result /= "GRAF";
    result /= "WebView2";
    std::error_code error;
    std::filesystem::create_directories(result, error);
    return error ? std::filesystem::path{} : result;
}

std::wstring suggestedFileName(winrt::Microsoft::Web::WebView2::Core::CoreWebView2DownloadStartingEventArgs const& args) {
    const auto suggested = args.ResultFilePath();
    if (!suggested.empty()) {
        const auto name = std::filesystem::path(std::wstring(suggested.c_str())).filename().wstring();
        if (!name.empty()) return name;
    }
    return L"graf-export";
}

std::optional<std::wstring> chooseDownloadPath(
    winrt::Microsoft::Web::WebView2::Core::CoreWebView2DownloadStartingEventArgs const& args) {
    auto fileName = suggestedFileName(args);
    wchar_t buffer[MAX_PATH]{};
    wcsncpy_s(buffer, fileName.c_str(), _TRUNCATE);
    OPENFILENAMEW dialog{};
    dialog.lStructSize = sizeof(dialog);
    dialog.hwndOwner = GetActiveWindow();
    dialog.lpstrFile = buffer;
    dialog.nMaxFile = static_cast<DWORD>(std::size(buffer));
    dialog.lpstrFilter = L"GRAF files\0*.*\0All files\0*.*\0";
    dialog.nFilterIndex = 1;
    dialog.Flags = OFN_PATHMUSTEXIST | OFN_OVERWRITEPROMPT;
    return GetSaveFileNameW(&dialog) ? std::optional<std::wstring>(buffer) : std::nullopt;
}

std::optional<WebViewBridgeEnvelope> parseEnvelope(std::string_view json, std::string origin) {
    try {
        const auto object = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(json));
        const auto version = object.GetNamedNumber(L"version");
        const auto messageId = object.GetNamedNumber(L"message_id");
        const auto sentAt = object.GetNamedNumber(L"sent_at_monotonic_ms");
        if (!isJsonUnsignedInteger(version, kJsonVersionMax) ||
            !isJsonUnsignedInteger(messageId, kJsonSafeIntegerMax) ||
            !isJsonUnsignedInteger(sentAt, kJsonSafeIntegerMax)) {
            return std::nullopt;
        }
        WebViewBridgeEnvelope envelope;
        envelope.protocol = utf8(object.GetNamedString(L"protocol"));
        envelope.version = static_cast<std::uint32_t>(version);
        envelope.messageId = static_cast<std::uint64_t>(messageId);
        envelope.nonce = utf8(object.GetNamedString(L"nonce"));
        envelope.origin = std::move(origin);
        const auto direction = utf8(object.GetNamedString(L"direction"));
        if (direction == "native_to_web") envelope.direction = BridgeDirection::nativeToWeb;
        else if (direction == "web_to_native") envelope.direction = BridgeDirection::webToNative;
        else return std::nullopt;
        envelope.command = utf8(object.GetNamedString(L"command"));
        envelope.payloadJson = utf8(object.GetNamedValue(L"payload").Stringify());
        envelope.sentAtMonotonicMs = static_cast<std::uint64_t>(sentAt);
        return envelope;
    } catch (...) {
        return std::nullopt;
    }
}

std::string originFromUrl(std::string_view url) {
    const auto schemeEnd = url.find("://");
    if (schemeEnd == std::string_view::npos) return {};
    const auto authorityStart = schemeEnd + 3;
    const auto authorityEnd = url.find_first_of("/?#", authorityStart);
    return std::string(url.substr(0, authorityEnd == std::string_view::npos ? url.size() : authorityEnd));
}

constexpr wchar_t kDesktopBridgeScript[] = LR"JS(
(() => {
  if (window.__grafDesktopBridgeInstalled) return;
  window.__grafDesktopBridgeInstalled = true;
  let nonce = null;
  let nextMessageId = 1;
  const send = (command, payload) => {
    if (!nonce) return;
      window.chrome.webview.postMessage({
        protocol: 'graf.desktop.bridge',
        version: 1,
        direction: 'web_to_native',
        message_id: nextMessageId++,
        nonce,
        origin: window.location.origin,
        command,
        payload,
        sent_at_monotonic_ms: Math.floor(window.performance.now())
      });
  };
  document.addEventListener('click', (event) => {
    const button = event.target instanceof Element
      ? event.target.closest('[data-graf-app-quit], [data-graf-local-recording-action]') : null;
    if (!button || button.disabled) return;
    if (button.hasAttribute('data-graf-app-quit')) send('request_app_quit', {action: 'quit'});
    else send('local_recording', {action: button.dataset.grafLocalRecordingAction, id: button.dataset.grafLocalRecordingId});
  });
  let rows = [];
  const adaptLocalDates = () => {
    document.querySelectorAll('[data-graf-local-recording-row]').forEach((element) => {
      const row = rows.find((item) => item.id === element.dataset.grafLocalRecordingId);
      if (!row) return;
      if (!row.startedAt) {
        const date = element.querySelector('.meeting-date');
        if (date) date.textContent = 'На этом компьютере';
      }
    });
  };
  document.addEventListener('htmx:afterSwap', adaptLocalDates);
  window.chrome.webview.addEventListener('message', (event) => {
    const message = event.data;
    if (!message) return;
    if (message.command === 'native_ready' && typeof message.nonce === 'string') {
      nonce = message.nonce;
      nextMessageId = 1;
    } else if (message.command === 'local_recordings' && nonce && message.nonce === nonce && Array.isArray(message.rows)) {
      rows = message.rows;
      window.GRAFLocalRecordings?.update(rows);
      adaptLocalDates();
    }
  });
})();
)JS";

} // namespace
#endif

WebView2Host::WebView2Host(WebViewRoutePolicy policy)
    : policy_(std::move(policy)), bridge_(policy_.trustedOrigin()),
      retryUrl_(policy_.trustedOrigin() + "/desktop/meetings") {}

WebView2Host::~WebView2Host() {
    runtimeHandler_ = {};
    authSessionHandler_ = {};
    close();
}

void WebView2Host::setRuntimeState(WebRuntimeState state) noexcept {
    runtimeState_ = state;
    if (state != WebRuntimeState::ready) {
        bridge_.invalidate();
        nativePublishLocalRecordings_ = {};
    }
    try {
        if (runtimeHandler_) runtimeHandler_(state);
    } catch (...) {
        runtimeState_ = WebRuntimeState::unavailable;
        bridge_.invalidate();
    }
}

void WebView2Host::fail(std::string_view stage, std::int32_t code) noexcept {
    authContinuation_ = AuthContinuation::none;
    cancelDialog();
    char hex[16]{};
    std::snprintf(hex, sizeof(hex), "0x%08X", static_cast<unsigned>(code));
    failureDetail_ = std::string(stage) + " · " + hex;
    setRuntimeState(WebRuntimeState::unavailable);
}

AuthContinuation WebView2Host::activeAuthContinuation() const noexcept {
    return authNavigations_ < 32 && std::chrono::steady_clock::now() - authStarted_ < std::chrono::minutes(10)
        ? authContinuation_ : AuthContinuation::none;
}

void WebView2Host::cancelDialog() noexcept {
    // Release the slot before Hide can complete an older dialog asynchronously.
    auto cancel = std::exchange(nativeCancelDialog_, {});
    try { if (cancel) cancel(); } catch (...) {}
}

void WebView2Host::close() noexcept {
    if (alive_) alive_->store(false);
    ++documentGeneration_;
    navigationId_ = 0;
    authContinuation_ = AuthContinuation::none;
    cancelDialog();
    try { if (nativeClose_) nativeClose_(); } catch (...) {}
    nativeNavigate_ = {};
    nativeReload_ = {};
    nativeBack_ = {};
    nativeForward_ = {};
    nativeCanGoBack_ = {};
    nativeCanGoForward_ = {};
    nativeClose_ = {};
    nativeInitialize_ = {};
    nativePublishLocalRecordings_ = {};
    setRuntimeState(WebRuntimeState::closed);
}

RouteEvaluation WebView2Host::navigate(std::string url) {
    const auto evaluation = policy_.evaluate(url);
    if (runtimeState_ != WebRuntimeState::closed && evaluation.decision == RouteDecision::allow) {
        // Native callers can request account/login recovery before a control is
        // ready. Keep the approved destination without inventing a loaded source.
        if (evaluation.kind != RouteKind::nativeSettings && evaluation.kind != RouteKind::artifactDownload &&
            evaluation.kind != RouteKind::authProvider) retryUrl_ = url;
#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
        if (nativeNavigate_) nativeNavigate_(url);
#endif
    }
    if (navigationHandler_) navigationHandler_(evaluation);
    return evaluation;
}

void WebView2Host::reload() {
    if (runtimeState_ == WebRuntimeState::closed) return;
    if (recreateRequired_) {
        auto recreate = recreateHandler_; // It may replace this host/control.
        if (recreate) recreate();
        return;
    }
#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
    if (nativeReload_ && runtimeState_ != WebRuntimeState::closed) {
        try { nativeReload_(); }
        catch (const winrt::hresult_error& error) { fail("reload", error.code().value); }
        catch (...) { fail("reload", E_FAIL); }
        return;
    }
    if (nativeInitialize_ && runtimeState_ == WebRuntimeState::unavailable) {
        nativeInitialize_();
        return;
    }
#endif
    if (!retryUrl_.empty()) (void)navigate(retryUrl_);
}

void WebView2Host::back() { if (canGoBack()) nativeBack_(); }
void WebView2Host::forward() { if (canGoForward()) nativeForward_(); }
bool WebView2Host::canGoBack() const {
    try { return !recreateRequired_ && nativeCanGoBack_ && nativeCanGoBack_(); } catch (...) { return false; }
}
bool WebView2Host::canGoForward() const {
    try { return !recreateRequired_ && nativeCanGoForward_ && nativeCanGoForward_(); } catch (...) { return false; }
}

bool WebView2Host::isAllowedQuitPayload(std::string_view payload) noexcept {
    return payload == R"({"action":"quit"})";
}

void WebView2Host::setLocalRecordings(std::vector<WebViewLocalRecordingRow> rows) {
    localRecordings_ = std::move(rows);
    if (runtimeState_ == WebRuntimeState::ready && nativePublishLocalRecordings_) nativePublishLocalRecordings_();
}

bool WebView2Host::localRecordingActionAllowed(std::string_view action, std::string_view id) const noexcept {
    if (runtimeState_ != WebRuntimeState::ready || id.empty() || id.size() > 300) return false;
    const auto row = std::find_if(localRecordings_.begin(), localRecordings_.end(),
        [id](const auto& item) { return item.id == id; });
    return row != localRecordings_.end() &&
        ((action == "open" && row->canOpen) || (action == "send" && row->canSend) ||
         (action == "delete" && row->canDelete));
}

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
void WebView2Host::attach(winrt::Microsoft::UI::Xaml::Controls::WebView2 control) {
    close();
    alive_ = std::make_shared<std::atomic_bool>(true);
    const auto alive = alive_;
    const auto dispatcher = control.DispatcherQueue();
    currentUrl_.clear();
    recreateRequired_ = false;
    nativeClose_ = [control] { control.Close(); };
    control.NavigationStarting([this, alive, control](auto const&, auto const& args) {
        if (!alive->load()) return;
        try {
            const auto url = utf8(args.Uri());
            const auto source = control.CoreWebView2() ? utf8(control.CoreWebView2().Source()) : std::string{};
            // A download never becomes the privileged document or a retry URL.
            if (runtimeState_ == WebRuntimeState::ready && source == currentUrl_ &&
                policy_.isAllowedDownload(url, source)) return;
            if (authContinuation_ != AuthContinuation::none && activeAuthContinuation() == AuthContinuation::none) {
                authContinuation_ = AuthContinuation::none;
                args.Cancel(true);
                fail("auth-expired", E_ACCESSDENIED);
                return;
            }
            const auto evaluation = policy_.evaluate(url, true, activeAuthContinuation());
            if (evaluation.decision == RouteDecision::openExternal) {
                args.Cancel(true);
                if (args.IsUserInitiated() && !args.IsRedirected())
                    (void)::ShellExecuteW(nullptr, L"open", winrt::to_hstring(evaluation.normalizedUrl).c_str(), nullptr, nullptr, SW_SHOWNORMAL);
            } else if (evaluation.kind == RouteKind::nativeSettings) {
                args.Cancel(true);
                if (navigationHandler_) navigationHandler_(evaluation);
            } else if (evaluation.decision != RouteDecision::allow) {
                args.Cancel(true);
                if (args.IsRedirected() || authContinuation_ != AuthContinuation::none) {
                    navigationId_ = 0;
                    fail("route", E_ACCESSDENIED);
                }
            } else {
                if (evaluation.kind == RouteKind::artifactDownload) { args.Cancel(true); return; }
                const auto start = policy_.authContinuationForStart(url);
                if (start != AuthContinuation::none && !args.IsRedirected()) {
                    authContinuation_ = start;
                    authStarted_ = std::chrono::steady_clock::now();
                    authNavigations_ = 0;
                } else if (evaluation.kind != RouteKind::authProvider && evaluation.kind != RouteKind::authRecovery) {
                    authContinuation_ = AuthContinuation::none;
                }
                if (authContinuation_ != AuthContinuation::none) ++authNavigations_;
                cancelDialog();
                ++documentGeneration_;
                navigationId_ = args.NavigationId();
                if (evaluation.kind != RouteKind::authProvider) retryUrl_ = url;
                failureDetail_.clear();
                setRuntimeState(WebRuntimeState::initializing);
                if (navigationHandler_) navigationHandler_(evaluation);
            }
        } catch (const winrt::hresult_error& error) {
            args.Cancel(true);
            fail("navigation", error.code().value);
        } catch (...) {
            args.Cancel(true);
            fail("navigation", E_FAIL);
        }
    });
    control.CoreWebView2Initialized([this, alive, dispatcher, control](auto const& sender, auto const& initialized) {
        if (!alive->load()) return;
        try {
            if (FAILED(initialized.Exception())) {
                fail("initialize", initialized.Exception());
                return;
            }
            auto core = sender.CoreWebView2();
            if (!core) { fail("initialize", E_POINTER); return; }
            nativeNavigate_ = [core](std::string_view url) { core.Navigate(winrt::to_hstring(url)); };
            nativeReload_ = [this, core] {
                // A failed first navigation may leave about:blank as Source.
                // Retry the approved requested route without deleting user data.
                core.Navigate(winrt::to_hstring(retryUrl_));
            };
            nativeBack_ = [core] { core.GoBack(); };
            nativeForward_ = [core] { core.GoForward(); };
            nativeCanGoBack_ = [core] { return core.CanGoBack(); };
            nativeCanGoForward_ = [core] { return core.CanGoForward(); };
            core.Settings().AreHostObjectsAllowed(false);
            core.Settings().IsStatusBarEnabled(false);
            core.Settings().AreDefaultScriptDialogsEnabled(false);
            core.SourceChanged([this, alive](auto const& core, auto const& args) {
                if (!alive->load()) return;
                try {
                    const auto source = utf8(core.Source());
                    const auto route = policy_.evaluate(source, true, activeAuthContinuation());
                    if (route.decision != RouteDecision::allow || route.kind == RouteKind::artifactDownload ||
                        route.kind == RouteKind::nativeSettings) {
                        currentUrl_.clear();
                        if (!args.IsNewDocument()) fail("source", E_ACCESSDENIED);
                        return;
                    }
                    currentUrl_ = source;
                    // replaceState/hash changes do not replace the document.
                    // Keep its generation, nonce and replay counter intact.
                    if (!args.IsNewDocument() && route.kind != RouteKind::authProvider) retryUrl_ = source;
                } catch (...) { fail("source", E_FAIL); }
            });
            core.AddWebResourceRequestedFilter(winrt::to_hstring(policy_.trustedOrigin() + "/*"),
                winrt::Microsoft::Web::WebView2::Core::CoreWebView2WebResourceContext::Document);
            core.WebResourceRequested([this, alive](auto const&, auto const& args) {
                if (!alive->load()) return;
                const auto request = args.Request();
                if (policy_.evaluate(utf8(request.Uri())).decision == RouteDecision::allow) {
                    request.Headers().SetHeader(L"X-GRAF-Client", L"desktop");
                }
            });
            core.ScriptDialogOpening([this, alive, dispatcher, control](auto const& core, auto const& args) {
                using namespace winrt::Microsoft::UI::Xaml::Controls;
                using Kind = winrt::Microsoft::Web::WebView2::Core::CoreWebView2ScriptDialogKind;
                if (!alive->load() || nativeCancelDialog_ || utf8(args.Uri()) != utf8(core.Source()) ||
                    utf8(core.Source()) != currentUrl_ ||
                    policy_.evaluate(currentUrl_).decision != RouteDecision::allow ||
                    (args.Kind() != Kind::Confirm && args.Kind() != Kind::Alert)) return;
                const auto deferral = args.GetDeferral();
                const auto generation = documentGeneration_;
                nativeCancelDialog_ = [] {}; // Reserve the single dialog before dispatch.
                // A modal loop inside a WebView callback is not supported.
                const auto queued = dispatcher.TryEnqueue([this, alive, dispatcher, control, args, deferral, generation] {
                    if (!alive->load() || generation != documentGeneration_) { deferral.Complete(); return; }
                    try {
                        ContentDialog dialog;
                        dialog.XamlRoot(control.XamlRoot());
                        dialog.Title(winrt::box_value(L"GRAF"));
                        const auto text = std::wstring(args.Message().c_str()).substr(0, 2048);
                        dialog.Content(winrt::box_value(text));
                        dialog.CloseButtonText(args.Kind() == Kind::Alert ? L"Закрыть" : L"Отмена");
                        if (args.Kind() == Kind::Confirm) dialog.PrimaryButtonText(L"Подтвердить");
                        dialog.DefaultButton(ContentDialogButton::Close);
                        nativeCancelDialog_ = [dialog] { dialog.Hide(); };
                        dialog.ShowAsync().Completed([this, alive, dispatcher, args, deferral, generation](auto const& operation, auto const&) {
                            const auto completionQueued = dispatcher.TryEnqueue([this, alive, args, deferral, generation, operation] {
                                try {
                                    if (alive->load() && generation == documentGeneration_) {
                                        nativeCancelDialog_ = {};
                                        if (operation.GetResults() == ContentDialogResult::Primary) args.Accept();
                                    }
                                } catch (...) {}
                                deferral.Complete();
                            });
                            if (!completionQueued) { try { deferral.Complete(); } catch (...) {} }
                        });
                    } catch (...) {
                        nativeCancelDialog_ = {};
                        deferral.Complete();
                    }
                });
                if (!queued) {
                    nativeCancelDialog_ = {};
                    deferral.Complete();
                }
            });
            core.FrameNavigationStarting([this, alive](auto const&, auto const& args) {
                if (!alive->load()) { args.Cancel(true); return; }
                try {
                    if (policy_.evaluate(utf8(args.Uri()), false).decision != RouteDecision::allow) args.Cancel(true);
                } catch (...) { args.Cancel(true); }
            });
            core.NewWindowRequested([this, alive](auto const& core, auto const& args) {
                args.Handled(true);
                if (!alive->load()) return;
                const auto evaluation = policy_.evaluate(utf8(args.Uri()), true, activeAuthContinuation());
                if (evaluation.decision == RouteDecision::allow) {
                    // Keep provider popups in this profile, with the same policy
                    // rechecked by NavigationStarting. No generic new windows.
                    core.Navigate(args.Uri());
                } else if (evaluation.decision == RouteDecision::openExternal && args.IsUserInitiated()) {
                    (void)::ShellExecuteW(nullptr, L"open", winrt::to_hstring(evaluation.normalizedUrl).c_str(), nullptr, nullptr, SW_SHOWNORMAL);
                }
            });
            core.ProcessFailed([this, alive](auto const&, auto const& args) {
                if (!alive->load()) return;
                using Kind = winrt::Microsoft::Web::WebView2::Core::CoreWebView2ProcessFailedKind;
                if (args.ProcessFailedKind() == Kind::BrowserProcessExited) recreateRequired_ = true;
                ++documentGeneration_;
                navigationId_ = 0;
                fail("browser-process", E_FAIL);
            });
            core.DownloadStarting([this, alive, dispatcher](auto const& core, auto const& args) {
                if (!alive->load()) { args.Cancel(true); return; }
                try {
                    const auto source = utf8(core.Source());
                    if (runtimeState_ != WebRuntimeState::ready || source != currentUrl_ || nativeCancelDialog_ ||
                        !policy_.isAllowedDownload(utf8(args.DownloadOperation().Uri()), source)) {
                        args.Cancel(true);
                        return;
                    }
                    const auto deferral = args.GetDeferral();
                    const auto generation = documentGeneration_;
                    args.Handled(true);
                    nativeCancelDialog_ = [] {}; // Serialize native dialogs.
                    const auto queued = dispatcher.TryEnqueue([this, alive, args, deferral, generation] {
                        try {
                            if (!alive->load() || generation != documentGeneration_) {
                                args.Cancel(true);
                            } else {
                                // Run the modal native picker outside the WebView
                                // callback; never replace the current document.
                                const auto path = chooseDownloadPath(args);
                                if (!alive->load() || generation != documentGeneration_ || !path) args.Cancel(true);
                                else args.ResultFilePath(winrt::hstring(*path));
                            }
                        } catch (...) { try { args.Cancel(true); } catch (...) {} }
                        if (alive->load() && generation == documentGeneration_) nativeCancelDialog_ = {};
                        try { deferral.Complete(); } catch (...) {}
                    });
                    if (!queued) {
                        nativeCancelDialog_ = {};
                        args.Cancel(true);
                        deferral.Complete();
                    }
                } catch (...) { args.Cancel(true); }
            });
            core.WebMessageReceived([this, alive](auto const& core, auto const& args) {
                if (!alive->load() || runtimeState_ != WebRuntimeState::ready) return;
                try {
                    const auto rawJson = utf8(args.WebMessageAsJson());
                    if (rawJson.size() > kBridgeMaxSerializedBytes) return;
                    const auto sourceUrl = utf8(args.Source());
                    if (sourceUrl != utf8(core.Source()) || sourceUrl != currentUrl_ ||
                        policy_.evaluate(sourceUrl).decision != RouteDecision::allow) return;
                    const auto message = parseEnvelope(rawJson, originFromUrl(sourceUrl));
                    if (!message || bridge_.validate(*message) != BridgeValidationError::none) return;
                    if (message->command == "request_app_quit") {
                        if (isAllowedQuitPayload(message->payloadJson) && quitHandler_) quitHandler_();
                    } else if (message->command == "local_recording") {
                        const auto payload = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(message->payloadJson));
                        if (payload.Size() != 2) return;
                        const auto action = utf8(payload.GetNamedString(L"action"));
                        const auto id = utf8(payload.GetNamedString(L"id"));
                        if (localRecordingActionAllowed(action, id) && localRecordingHandler_) localRecordingHandler_(action, id);
                    }
                } catch (...) {
                    // Malformed browser messages have no native side effects.
                }
            });
            core.NavigationCompleted([this, alive, dispatcher](auto const& core, auto const& args) {
                if (!alive->load() || navigationId_ == 0 || args.NavigationId() != navigationId_) return;
                navigationId_ = 0;
                try {
                    if (!args.IsSuccess()) {
                        fail("network", static_cast<std::int32_t>(args.WebErrorStatus()));
                        return;
                    }
                    const auto source = utf8(core.Source());
                    const auto route = policy_.evaluate(source, true, activeAuthContinuation());
                    if (route.decision != RouteDecision::allow) { fail("document-origin", E_ACCESSDENIED); return; }
                    currentUrl_ = source;
                    if (route.kind == RouteKind::authProvider) {
                        setRuntimeState(WebRuntimeState::authRequired);
                        return; // Never read cookies or install a bridge in an OAuth provider document.
                    }
                    if (args.HttpStatusCode() == 401 || args.HttpStatusCode() == 403) {
                        if (authSessionHandler_) authSessionHandler_({});
                        setRuntimeState(WebRuntimeState::authRequired);
                        if (route.kind != RouteKind::authRecovery) {
                            core.Navigate(winrt::to_hstring(policy_.trustedOrigin() + "/login?next=/desktop/meetings"));
                        }
                        return;
                    }
                    if (args.HttpStatusCode() >= 400) {
                        fail("http", args.HttpStatusCode());
                        return;
                    }
                    if (route.kind == RouteKind::authRecovery) {
                        setRuntimeState(WebRuntimeState::authRequired);
                        if (authSessionHandler_) authSessionHandler_({});
                        return;
                    }
                    authContinuation_ = AuthContinuation::none;
                    retryUrl_ = source;
                    const auto generation = documentGeneration_;
                    const auto nonce = newNonce();
                    if (nonce.empty()) { fail("nonce", E_FAIL); return; }
                    setRuntimeState(WebRuntimeState::ready);
                    if (!alive->load() || generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready) return;
                    bridge_.rotateNonce(nonce);
                    // Completion delegates have no UI-apartment guarantee. Marshal
                    // every WinUI/WebView access, including GetResults, to its owner.
                    core.CookieManager().GetCookiesAsync(winrt::to_hstring(policy_.trustedOrigin())).Completed(
                        [this, alive, dispatcher, core, generation](auto const& operation, auto const&) {
                            dispatcher.TryEnqueue([this, alive, core, generation, operation] {
                                if (!alive->load() || generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready) return;
                                try {
                                    if (policy_.evaluate(utf8(core.Source())).decision != RouteDecision::allow) return;
                                    std::string token;
                                    for (const auto& cookie : operation.GetResults()) {
                                        const auto name = utf8(cookie.Name());
                                        if (name == "__Host-twobrain_rec_owner_session") {
                                            token = utf8(cookie.Value());
                                            break;
                                        }
                                    }
                                    if (authSessionHandler_) authSessionHandler_(std::move(token));
                                } catch (...) {
                                    if (authSessionHandler_) authSessionHandler_({});
                                }
                            });
                        });
                    nativePublishLocalRecordings_ = [this, core, nonce, generation] {
                        if (generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready) return;
                        if (utf8(core.Source()) != currentUrl_ || policy_.evaluate(currentUrl_).decision != RouteDecision::allow) return;
                        using namespace winrt::Windows::Data::Json;
                        JsonArray rows;
                        for (const auto& item : localRecordings_) {
                            JsonObject row;
                            row.Insert(L"id", JsonValue::CreateStringValue(winrt::to_hstring(item.id)));
                            row.Insert(L"title", JsonValue::CreateStringValue(winrt::to_hstring(item.title)));
                            row.Insert(L"startedAt", JsonValue::CreateStringValue(winrt::to_hstring(item.startedAt)));
                            row.Insert(L"status", JsonValue::CreateStringValue(winrt::to_hstring(item.status)));
                            row.Insert(L"durationSeconds", JsonValue::CreateNumberValue(static_cast<double>(item.durationSeconds)));
                            row.Insert(L"canOpen", JsonValue::CreateBooleanValue(item.canOpen));
                            row.Insert(L"canSend", JsonValue::CreateBooleanValue(item.canSend));
                            row.Insert(L"canDelete", JsonValue::CreateBooleanValue(item.canDelete));
                            row.Insert(L"uploadComplete", JsonValue::CreateBooleanValue(item.uploadComplete));
                            rows.Append(row);
                        }
                        JsonObject message;
                        message.Insert(L"command", JsonValue::CreateStringValue(L"local_recordings"));
                        message.Insert(L"nonce", JsonValue::CreateStringValue(winrt::to_hstring(nonce)));
                        message.Insert(L"rows", rows);
                        core.PostWebMessageAsJson(message.Stringify());
                    };
                    core.ExecuteScriptAsync(winrt::to_hstring(kDesktopBridgeScript)).Completed(
                        [this, alive, dispatcher, core, nonce, generation](auto const& operation, auto const&) {
                            dispatcher.TryEnqueue([this, alive, core, nonce, generation, operation] {
                                if (!alive->load() || generation != documentGeneration_ ||
                                    runtimeState_ != WebRuntimeState::ready) return;
                                try {
                                    if (utf8(core.Source()) != currentUrl_ || policy_.evaluate(currentUrl_).decision != RouteDecision::allow) return;
                                    (void)operation.GetResults();
                                    winrt::Windows::Data::Json::JsonObject ready;
                                    using Value = winrt::Windows::Data::Json::JsonValue;
                                    ready.Insert(L"protocol", Value::CreateStringValue(winrt::to_hstring(std::string(kBridgeProtocol))));
                                    ready.Insert(L"version", Value::CreateNumberValue(kBridgeProtocolVersion));
                                    ready.Insert(L"message_id", Value::CreateNumberValue(1));
                                    ready.Insert(L"nonce", Value::CreateStringValue(winrt::to_hstring(nonce)));
                                    ready.Insert(L"origin", Value::CreateStringValue(winrt::to_hstring(policy_.trustedOrigin())));
                                    ready.Insert(L"direction", Value::CreateStringValue(L"native_to_web"));
                                    ready.Insert(L"command", Value::CreateStringValue(L"native_ready"));
                                    ready.Insert(L"payload", winrt::Windows::Data::Json::JsonObject{});
                                    ready.Insert(L"sent_at_monotonic_ms", Value::CreateNumberValue(static_cast<double>(GetTickCount64())));
                                    core.PostWebMessageAsJson(ready.Stringify());
                                    if (nativePublishLocalRecordings_) nativePublishLocalRecordings_();
                                } catch (const winrt::hresult_error& error) {
                                    fail("bridge", error.code().value);
                                } catch (...) { fail("bridge", E_FAIL); }
                            });
                        });
                } catch (const winrt::hresult_error& error) {
                    fail("document", error.code().value);
                } catch (...) { fail("document", E_FAIL); }
            });
            core.Navigate(winrt::to_hstring(retryUrl_));
        } catch (const winrt::hresult_error& error) {
            fail("configure", error.code().value);
        } catch (...) { fail("configure", E_FAIL); }
    });
    nativeInitialize_ = [this, alive, dispatcher, control] {
        if (!alive->load() || runtimeState_ == WebRuntimeState::initializing) return;
        try {
            failureDetail_.clear();
            setRuntimeState(WebRuntimeState::initializing);
            const auto userData = webViewUserDataFolder();
            if (userData.empty()) { fail("profile", E_ACCESSDENIED); return; }
            auto environment = winrt::Microsoft::Web::WebView2::Core::CoreWebView2Environment::CreateWithOptionsAsync(
                winrt::hstring{}, winrt::hstring(userData.wstring()),
                winrt::Microsoft::Web::WebView2::Core::CoreWebView2EnvironmentOptions{});
            environment.Completed([this, alive, dispatcher, control](auto const& operation, auto const&) {
                dispatcher.TryEnqueue([this, alive, dispatcher, control, operation] {
                    if (!alive->load()) return;
                    try {
                        control.EnsureCoreWebView2Async(operation.GetResults()).Completed(
                            [this, alive, dispatcher](auto const& ensured, auto const&) {
                                dispatcher.TryEnqueue([this, alive, ensured] {
                                    if (!alive->load()) return;
                                    try { ensured.GetResults(); }
                                    catch (const winrt::hresult_error& error) { fail("ensure-control", error.code().value); }
                                    catch (...) { fail("ensure-control", E_FAIL); }
                                });
                            });
                    } catch (const winrt::hresult_error& error) {
                        fail("environment", error.code().value);
                    } catch (...) { fail("environment", E_FAIL); }
                });
            });
        } catch (const winrt::hresult_error& error) {
            fail("environment", error.code().value);
        } catch (...) { fail("environment", E_FAIL); }
    };
    nativeInitialize_();
}
#endif

} // namespace graf::windows
