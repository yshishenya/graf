#include "WebView2Host.h"

#include "../Contracts/WindowsDesktopContracts.h"
#include "../Upload/DesktopApiClient.h"
#include <cstdio>
#include <algorithm>
#include <random>

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
#include <fstream>
#include <winrt/Windows.Storage.h>
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

// Мост между страницей и приложением молча отбрасывает всё, что не прошло
// проверку, и без следа понять, где именно потерялось объявление, невозможно.
// Журнал хранит только имена команд и причины отказа: ни текстов, ни адресов,
// ни содержимого встреч здесь нет, поэтому он безопасен для диагностики.
void logBridgeEvent(std::string_view event) {
    static const std::filesystem::path path = [] {
        try {
            const auto folder = winrt::Windows::Storage::ApplicationData::Current().LocalFolder().Path();
            return std::filesystem::path(folder.c_str()) / L"bridge.log";
        } catch (...) {
            return std::filesystem::path{};
        }
    }();
    if (path.empty()) return;
    try {
        std::error_code error;
        if (std::filesystem::exists(path, error) && std::filesystem::file_size(path, error) > 64u * 1024u) {
            std::filesystem::remove(path, error);
        }
        std::ofstream log(path, std::ios::app);
        if (!log) return;
        log << GetTickCount64() << ' ' << event << '\n';
    } catch (...) {
        // Диагностика не имеет права мешать работе страницы.
    }
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
  // The cabinet's theme is a user setting in the cabinet itself (`data-theme`),
  // so the page tells the app which one is in force instead of the app guessing.
  const publishAppearance = () => {
    const theme = document.documentElement.dataset.theme;
    send('app_appearance', {theme: theme === 'light' || theme === 'dark' ? theme : 'system'});
  };
  new MutationObserver(publishAppearance).observe(document.documentElement, {
    attributes: true, attributeFilter: ['data-theme']
  });
  publishAppearance();
  document.addEventListener('click', (event) => {
    const button = event.target instanceof Element
      ? event.target.closest('[data-graf-app-quit], [data-graf-local-recording-action]') : null;
    if (!button || button.disabled) return;
    if (button.hasAttribute('data-graf-app-quit')) send('request_app_quit', {action: 'quit'});
    else send('local_recording', {action: button.dataset.grafLocalRecordingAction, id: button.dataset.grafLocalRecordingId});
  });
  // The deletion bridge in the page hands its selection here instead of posting an
  // envelope itself, so the nonce stays inside this script.
  window.addEventListener('graf:delete-selection', (event) => {
    if (!event.detail) return;
    send('delete_selection', event.detail);
  });
  // The settings shim asks the same way. Its request id travels with the request
  // and comes back with the answer, so two pages cannot answer each other.
  window.addEventListener('graf:native-settings', (event) => {
    if (!event.detail) return;
    send('native_settings', event.detail);
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
      // The theme is announced with the handshake, not at document start: the
      // envelope needs the nonce, and before the handshake the app would drop it
      // as a message from a document it has not accepted yet.
      publishAppearance();
    } else if (message.command === 'native_reply' && typeof message.request_id === 'number') {
      window.dispatchEvent(new CustomEvent('graf:native-settings-reply', {
        detail: {requestId: message.request_id, payload: message.payload || null}
      }));
    } else if (message.command === 'local_recordings' && nonce && message.nonce === nonce && Array.isArray(message.rows)) {
      rows = message.rows;
      // The deletions in flight and the recovery notice travel with the rows: the
      // cabinet prints them, so a saved request is not merely remembered by the app.
      const operations = Array.isArray(message.operations) ? message.operations : [];
      window.GRAFLocalRecordings?.update(rows, operations, message.recoveryRequired === true);
      adaptLocalDates();
    }
  });
})();
)JS";

} // namespace
#endif

namespace {

// The value the settings page must echo back. It binds a settings request to the
// document that was handed the shim; the envelope nonce is what authenticates the
// message itself, so this only has to be unique per document, and it is minted
// where both lanes can reach it.
std::string settingsHandshakeValue() {
    std::random_device source;
    std::uniform_int_distribution<unsigned> nibble(0, 15);
    constexpr char digits[] = "0123456789abcdef";
    std::string value;
    value.reserve(32);
    for (int index = 0; index < 32; ++index) value += digits[nibble(source)];
    return value;
}

} // namespace

WebView2Host::WebView2Host(WebViewRoutePolicy policy)
    : policy_(std::move(policy)), bridge_(policy_.trustedOrigin()),
      retryUrl_(policy_.trustedOrigin() + "/desktop/meetings") {}

WebView2Host::~WebView2Host() {
    runtimeHandler_ = {};
    authSessionHandler_ = {};
    close();
}

void WebView2Host::setRuntimeState(WebRuntimeState state) noexcept {
    if (state != WebRuntimeState::ready) nativeSettingsNonce_.clear();
    runtimeState_ = state;
    if (state != WebRuntimeState::ready) {
        bridge_.invalidate();
        nativePublishLocalRecordings_ = {};
        nativeRunScript_ = {};
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
    nativeRunScript_ = {};
    nativeExtendAuthCookie_ = {};
    preferredColorScheme_ = {};
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

bool WebView2Host::isAllowedAppearance(std::string_view theme) noexcept {
    // The three values macOS accepts. `system` means the user has not chosen one,
    // which is not the same as an unknown value.
    return theme == "light" || theme == "dark" || theme == "system";
}

void WebView2Host::setNativeSettingsHandler(NativeSettingsHandler handler) {
    nativeSettingsHandler_ = std::move(handler);
    // A document that is already on screen was never handed the shim. The next
    // navigation installs it; until then nothing answers, and nothing is asked.
    nativeSettingsNonce_.clear();
}

void WebView2Host::beginNativeSettings() {
    nativeSettingsNonce_.clear();
    if (!nativeSettingsHandler_ || !nativeRunScript_) return;
    // The handshake belongs to the settings page. Handing it to another page would
    // install a bridge that page never asks for, and would keep a nonce alive for
    // a document that is not the one it was minted for.
    if (!NativeSettingsBridge::isSettingsRoute(currentUrl_)) return;
    const auto nonce = settingsHandshakeValue();
    if (nonce.empty()) return;
    nativeSettingsNonce_ = nonce;
    // Each page exposes its own object and is handed the same handshake value.
    if (NativeSettingsBridge::isRecordingSettingsRoute(currentUrl_)) {
        nativeRunScript_("window.GRAFRecordingSettings?.connect('" + nonce + "')");
    } else {
        nativeRunScript_("window.GRAFNotificationSettings?.connect('" + nonce + "')");
    }
}

bool WebView2Host::authCookieShouldBeExtended(std::string_view cookieValue, std::string_view token,
                                             std::int64_t unixSeconds, std::int64_t nowUnixSeconds) noexcept {
    // The same three refusals macOS makes before it rewrites a cookie: there has
    // to be a token, the cookie has to still hold that token, and the deadline has
    // to be in the future. A deadline in the past would shorten a session the
    // server has already extended, and an empty token would rewrite a cookie the
    // app is not holding.
    if (token.empty() || cookieValue != token) return false;
    if (unixSeconds <= nowUnixSeconds) return false;
    return true;
}

void WebView2Host::extendAuthCookieExpiry(std::string_view token, std::int64_t unixSeconds) {
    if (nativeExtendAuthCookie_) nativeExtendAuthCookie_(token, unixSeconds);
}

void WebView2Host::refreshNativeSettings() {
    if (nativeSettingsNonce_.empty() || !nativeRunScript_) return;
    if (NativeSettingsBridge::isRecordingSettingsRoute(currentUrl_)) {
        nativeRunScript_("window.GRAFRecordingSettings?.refresh()");
    } else {
        nativeRunScript_("window.GRAFNotificationSettings?.refresh()");
    }
}

void WebView2Host::setLocalRecordings(std::vector<WebViewLocalRecordingRow> rows,
                                     std::vector<CabinetDeletionOperation> operations, bool recoveryRequired) {
    localRecordings_ = std::move(rows);
    localDeletionOperations_ = std::move(operations);
    localRecoveryRequired_ = recoveryRequired;
    if (runtimeState_ == WebRuntimeState::ready && nativePublishLocalRecordings_) nativePublishLocalRecordings_();
}

void WebView2Host::applyLocalPackageTiming(WebViewLocalRecordingRow& row, std::uint64_t startedAtMs,
                                           std::uint64_t stoppedAtMs, bool captureInterrupted) {
    row.startedAt = DesktopApiClient::formatUtcInstant(startedAtMs);
    row.generatedTitlePrefix.clear();
    // The cabinet formats the date itself, so it receives a prefix and the
    // instant rather than a date this machine already rendered. A recording with
    // no readable start keeps the plain title instead of an empty date.
    if (!row.startedAt.empty()) row.generatedTitlePrefix = "Запись ";
    const auto sessionSeconds = stoppedAtMs > startedAtMs ? (stoppedAtMs - startedAtMs + 999) / 1000 : 0;
    row.sessionDurationSeconds = std::max(row.durationSeconds, sessionSeconds);
    // "Saved X of Y" is a claim about a fault: it is true only for an
    // interrupted recording whose confirmed prefix survived, is playable, and is
    // shorter than the session it came from.
    row.showsPartialDuration = captureInterrupted && row.canOpen &&
        row.durationSeconds < row.sessionDurationSeconds;
}

bool WebView2Host::localRecordingActionAllowed(std::string_view action, std::string_view id) const noexcept {
    if (runtimeState_ != WebRuntimeState::ready || id.empty() || id.size() > 300) return false;
    const auto row = std::find_if(localRecordings_.begin(), localRecordings_.end(),
        [id](const auto& item) { return item.id == id; });
    return row != localRecordings_.end() &&
        ((action == "open" && row->canOpen) || (action == "send" && row->canSend) ||
         (action == "delete" && row->canDelete));
}

std::string WebView2Host::meetingIdOnPage(std::string_view pageUrl) {
    constexpr std::string_view detailPrefix = "/desktop/meetings/";
    const auto schemeEnd = pageUrl.find("://");
    if (schemeEnd == std::string_view::npos) return {};
    const auto pathStart = pageUrl.find('/', schemeEnd + 3);
    if (pathStart == std::string_view::npos) return {};
    const auto pathEnd = pageUrl.find_first_of("?#", pathStart);
    const auto path = pageUrl.substr(pathStart,
        (pathEnd == std::string_view::npos ? pageUrl.size() : pathEnd) - pathStart);
    // The meeting list and a single meeting are the same route kind; the id in the
    // path is what separates them, and a shared meeting is one meeting as well.
    constexpr std::string_view sharedPrefix = "/shared-meetings/";
    const auto prefix = path.rfind(detailPrefix, 0) == 0 ? detailPrefix
        : (path.rfind(sharedPrefix, 0) == 0 ? sharedPrefix : std::string_view());
    if (prefix.empty() || path.size() != prefix.size() + 36) return {};
    const auto candidate = path.substr(prefix.size());
    return DesktopApiClient::accountId(candidate) ? std::string(candidate) : std::string();
}

std::vector<CabinetLocalRow> WebView2Host::cabinetRows() const {
    std::vector<CabinetLocalRow> rows;
    rows.reserve(localRecordings_.size());
    for (const auto& row : localRecordings_) {
        rows.push_back({row.id, row.originId.empty() ? row.id : row.originId, row.canDelete});
    }
    return rows;
}

std::optional<CabinetDeletionSelection> WebView2Host::deletionSelectionFrom(
    const CabinetDeletionInput& input, std::string_view pageUrl) const noexcept {
    if (runtimeState_ != WebRuntimeState::ready) return std::nullopt;
    // The page has to be one that shows deletable rows: the meeting list or a
    // single meeting, the same two routes macOS admits. A selection is not a
    // deletion request merely because it arrived through a valid bridge.
    const auto route = policy_.evaluate(pageUrl);
    if (route.decision != RouteDecision::allow ||
        (route.kind != RouteKind::meetings && route.kind != RouteKind::meetingDetail)) return std::nullopt;
    const auto rows = cabinetRows();
    const auto selection = RecordingDeletionBridge::validate(input, rows);
    if (!selection || !RecordingDeletionBridge::fitsRoute(*selection, meetingIdOnPage(pageUrl))) return std::nullopt;
    return selection;
}

void WebView2Host::completeDeletionSelection(const DeletionRequest& request,
                                            const CabinetDeletionOutcome& outcome) {
    const auto script = RecordingDeletionBridge::completionScript(request.selection.requestId, outcome);
    if (script.empty() || !nativeRunScript_) return;
    // A page that has since been replaced is not waiting for this answer.
    if (request.documentGeneration == 0 || request.documentGeneration != documentGeneration_) return;
    nativeRunScript_(script);
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
    // The cookie the cabinet signs in with is the app's own session token, so the
    // deadline the server names belongs on that cookie. WebView2 exposes it
    // through the cookie manager; the value is rewritten only when it is still the
    // token the request used.
    nativeExtendAuthCookie_ = [this, alive, dispatcher, control](std::string_view token, std::int64_t unixSeconds) {
        if (!alive->load() || token.empty() || unixSeconds <= 0) return;
        try {
            if (!control.CoreWebView2()) return;
            const auto generation = documentGeneration_;
            const auto expected = std::string(token);
            control.CoreWebView2().CookieManager().GetCookiesAsync(
                winrt::to_hstring(policy_.trustedOrigin())).Completed(
                [this, alive, dispatcher, control, generation, expected, unixSeconds](auto const& operation, auto const&) {
                    dispatcher.TryEnqueue([this, alive, control, generation, expected, unixSeconds, operation] {
                        if (!alive->load() || generation != documentGeneration_) return;
                        try {
                            const auto now = std::chrono::duration_cast<std::chrono::seconds>(
                                std::chrono::system_clock::now().time_since_epoch()).count();
                            for (const auto& cookie : operation.GetResults()) {
                                if (utf8(cookie.Name()) != "__Host-twobrain_rec_owner_session") continue;
                                if (!authCookieShouldBeExtended(utf8(cookie.Value()), expected, unixSeconds, now)) continue;
                                // The WebView2 cookie API states expiry as Unix
                                // seconds, which is the same unit the server used.
                                cookie.Expires(static_cast<double>(unixSeconds));
                                control.CoreWebView2().CookieManager().AddOrUpdateCookie(cookie);
                            }
                        } catch (...) {
                            // A cookie that cannot be rewritten is not an error the
                            // user has to see: the session the app holds is intact.
                        }
                    });
                });
        } catch (...) {
        }
    };
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
            // Тема страницы и тема окна обязаны совпадать: кабинет узнаёт
            // системную тему из `prefers-color-scheme`, а окно — из системной
            // настройки, и по умолчанию они расходятся.
            preferredColorScheme_ = [this, alive, core](bool isDark) {
                if (!alive->load()) return;
                try {
                    core.Profile().PreferredColorScheme(isDark
                        ? winrt::Microsoft::Web::WebView2::Core::CoreWebView2PreferredColorScheme::Dark
                        : winrt::Microsoft::Web::WebView2::Core::CoreWebView2PreferredColorScheme::Light);
                } catch (...) {
                    // Старая среда может не знать этой настройки: окно всё равно
                    // уже следует выбранной теме, а страница — своему оформлению.
                }
            };
            preferredColorScheme_(colorSchemeIsDark_);
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
                        policy_.evaluate(sourceUrl).decision != RouteDecision::allow) {
                        // Страница ушла вперёд приложения: сообщение приходит из
                        // документа, который приложение ещё не считает текущим.
                        logBridgeEvent(sourceUrl != currentUrl_ ? "stale-document" : "source-rejected");
                        return;
                    }
                    const auto message = parseEnvelope(rawJson, originFromUrl(sourceUrl));
                    if (!message) {
                        logBridgeEvent("envelope-rejected");
                        return;
                    }
                    const auto validation = bridge_.validate(*message);
                    if (validation != BridgeValidationError::none) {
                        logBridgeEvent("validation-rejected " + message->command);
                        return;
                    }
                    logBridgeEvent("accepted " + message->command);
                    if (message->command == "native_settings") {
                        // A settings request is answered only for the page it
                        // belongs to, and only for the document that was handed
                        // the handshake. The request carries exactly the fields
                        // its action has; anything else is not that request.
                        if (!nativeSettingsHandler_ || nativeSettingsNonce_.empty() ||
                            !NativeSettingsBridge::isSettingsRoute(currentUrl_)) return;
                        const auto payload = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(message->payloadJson));
                        if (payload.Size() != 3) return;
                        const auto handler = utf8(payload.GetNamedString(L"handler"));
                        if (handler != NativeSettingsBridge::kRecordingSettingsHandler &&
                            handler != NativeSettingsBridge::kNotificationSettingsHandler) return;
                        // The handler must belong to the page that asked: the
                        // recording page cannot answer for the notification page.
                        if (handler == NativeSettingsBridge::kRecordingSettingsHandler &&
                            !NativeSettingsBridge::isRecordingSettingsRoute(currentUrl_)) return;
                        if (handler == NativeSettingsBridge::kNotificationSettingsHandler &&
                            !NativeSettingsBridge::isNotificationSettingsRoute(currentUrl_)) return;
                        const auto requestId = payload.GetNamedNumber(L"requestId");
                        if (!isJsonUnsignedInteger(requestId, kJsonSafeIntegerMax)) return;
                        const auto request = payload.GetNamedObject(L"request");
                        if (request.GetNamedNumber(L"version") != 1.0) return;
                        if (utf8(request.GetNamedString(L"nonce")) != nativeSettingsNonce_) return;
                        const auto action = NativeSettingsBridge::actionFromToken(
                            utf8(request.GetNamedString(L"action")));
                        if (!action) return;
                        NativeSettingsRequest parsed;
                        parsed.handler = handler;
                        parsed.action = std::string(NativeSettingsBridge::actionToken(*action));
                        if (*action == NativeSettingsBridge::Action::read) {
                            if (request.Size() != 3) return;
                        } else if (*action == NativeSettingsBridge::Action::set) {
                            if (request.Size() != 5) return;
                            parsed.targetId = utf8(request.GetNamedString(L"targetID"));
                            parsed.rule = utf8(request.GetNamedString(L"rule"));
                            if (parsed.targetId.empty() || !NativeSettingsBridge::isRule(parsed.rule)) return;
                        } else {
                            if (request.Size() != 4) return;
                            parsed.rule = utf8(request.GetNamedString(L"rule"));
                            if (!NativeSettingsBridge::isRule(parsed.rule)) return;
                        }
                        const auto answer = nativeSettingsHandler_(parsed);
                        // An empty answer is a refusal, and a refusal is sent:
                        // the page is waiting for one and would otherwise report
                        // a failure fifteen seconds later.
                        const auto body = answer.empty()
                            ? NativeSettingsBridge::failureReply("Настройку не удалось сохранить.")
                            : answer;
                        using namespace winrt::Windows::Data::Json;
                        JsonObject reply;
                        reply.Insert(L"protocol", JsonValue::CreateStringValue(winrt::to_hstring(std::string(kBridgeProtocol))));
                        reply.Insert(L"version", JsonValue::CreateNumberValue(kBridgeProtocolVersion));
                        reply.Insert(L"message_id", JsonValue::CreateNumberValue(1));
                        reply.Insert(L"nonce", JsonValue::CreateStringValue(winrt::to_hstring(documentNonce_)));
                        reply.Insert(L"origin", JsonValue::CreateStringValue(winrt::to_hstring(policy_.trustedOrigin())));
                        reply.Insert(L"direction", JsonValue::CreateStringValue(L"native_to_web"));
                        reply.Insert(L"command", JsonValue::CreateStringValue(L"native_reply"));
                        reply.Insert(L"request_id", JsonValue::CreateNumberValue(requestId));
                        reply.Insert(L"payload", JsonObject::Parse(winrt::to_hstring(body)));
                        reply.Insert(L"sent_at_monotonic_ms", JsonValue::CreateNumberValue(static_cast<double>(GetTickCount64())));
                        core.PostWebMessageAsJson(reply.Stringify());
                    } else if (message->command == "app_appearance") {
                        // The announcement decides the appearance of native
                        // windows, so it is read as strictly as macOS reads it.
                        const auto payload = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(message->payloadJson));
                        if (payload.Size() != 1) return;
                        const auto theme = utf8(payload.GetNamedString(L"theme"));
                        if (isAllowedAppearance(theme) && appearanceHandler_) appearanceHandler_(theme);
                    } else if (message->command == "request_app_quit") {
                        if (isAllowedQuitPayload(message->payloadJson) && quitHandler_) quitHandler_();
                    } else if (message->command == "local_recording") {
                        const auto payload = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(message->payloadJson));
                        if (payload.Size() != 2) return;
                        const auto action = utf8(payload.GetNamedString(L"action"));
                        const auto id = utf8(payload.GetNamedString(L"id"));
                        if (localRecordingActionAllowed(action, id) && localRecordingHandler_) localRecordingHandler_(action, id);
                    } else if (message->command == "delete_selection") {
                        const auto payload = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(message->payloadJson));
                        // Exactly the five fields the cabinet's deletion message
                        // carries; a missing or extra one is not that message.
                        if (payload.Size() != 5) return;
                        CabinetDeletionInput input;
                        input.action = utf8(payload.GetNamedString(L"action"));
                        const auto version = payload.GetNamedNumber(L"version");
                        if (version < 0 || version > 4294967295.0) return;
                        input.version = static_cast<std::uint32_t>(version);
                        input.requestId = utf8(payload.GetNamedString(L"requestId"));
                        const auto readIds = [](const auto& source, std::vector<std::string>& target) {
                            for (const auto& value : source) {
                                if (value.ValueType() != winrt::Windows::Data::Json::JsonValueType::String) return false;
                                target.push_back(utf8(value.GetString()));
                            }
                            return true;
                        };
                        if (!readIds(payload.GetNamedArray(L"localIds"), input.localIds)) return;
                        if (!readIds(payload.GetNamedArray(L"meetingIds"), input.meetingIds)) return;
                        const auto selection = deletionSelectionFrom(input, sourceUrl);
                        // A selection that fails the gate is dropped without an
                        // answer: the page must not learn that some other
                        // selection would have been accepted.
                        if (selection && deletionSelectionHandler_) {
                            deletionSelectionHandler_(
                                {*selection, RecordingDeletionBridge::targets(*selection, cabinetRows()),
                                 documentGeneration_});
                        }
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
                    documentNonce_ = nonce;
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
                            // Absent, not empty: the cabinet treats a missing field
                            // as unknown, while an empty instant is a date it cannot
                            // parse and would render as "Без даты".
                            if (!item.startedAt.empty())
                                row.Insert(L"startedAt", JsonValue::CreateStringValue(winrt::to_hstring(item.startedAt)));
                            if (!item.generatedTitlePrefix.empty())
                                row.Insert(L"generatedTitlePrefix", JsonValue::CreateStringValue(winrt::to_hstring(item.generatedTitlePrefix)));
                            row.Insert(L"status", JsonValue::CreateStringValue(winrt::to_hstring(item.status)));
                            row.Insert(L"durationSeconds", JsonValue::CreateNumberValue(static_cast<double>(item.durationSeconds)));
                            row.Insert(L"sessionDurationSeconds", JsonValue::CreateNumberValue(static_cast<double>(item.sessionDurationSeconds)));
                            row.Insert(L"showsPartialDuration", JsonValue::CreateBooleanValue(item.showsPartialDuration));
                            row.Insert(L"canOpen", JsonValue::CreateBooleanValue(item.canOpen));
                            row.Insert(L"canSend", JsonValue::CreateBooleanValue(item.canSend));
                            row.Insert(L"canDelete", JsonValue::CreateBooleanValue(item.canDelete));
                            row.Insert(L"uploadComplete", JsonValue::CreateBooleanValue(item.uploadComplete));
                            row.Insert(L"localDeletionPending", JsonValue::CreateBooleanValue(item.localDeletionPending));
                            row.Insert(L"deletionIsLocalOnly", JsonValue::CreateBooleanValue(item.deletionIsLocalOnly));
                            if (!item.meetingId.empty())
                                row.Insert(L"meetingId", JsonValue::CreateStringValue(winrt::to_hstring(item.meetingId)));
                            rows.Append(row);
                        }
                        JsonArray operations;
                        for (const auto& item : localDeletionOperations_) {
                            using namespace winrt::Windows::Data::Json;
                            JsonObject operation;
                            operation.Insert(L"id", JsonValue::CreateStringValue(winrt::to_hstring(item.id)));
                            operation.Insert(L"phase", JsonValue::CreateStringValue(winrt::to_hstring(item.phase)));
                            // Absent, not empty: the page prints the phase when it
                            // has no reason to print instead.
                            if (!item.waitReason.empty())
                                operation.Insert(L"waitReason", JsonValue::CreateStringValue(winrt::to_hstring(item.waitReason)));
                            // The target is the encoded enum macOS sends, because the
                            // page reads `target.meeting._0` and `target.ownOrigin._0`.
                            if (!item.targetMeetingId.empty() || !item.targetDirectoryId.empty()) {
                                JsonObject target;
                                JsonObject value;
                                if (!item.targetMeetingId.empty()) {
                                    value.Insert(L"_0", JsonValue::CreateStringValue(winrt::to_hstring(item.targetMeetingId)));
                                    target.Insert(L"meeting", value);
                                } else {
                                    value.Insert(L"_0", JsonValue::CreateStringValue(winrt::to_hstring(item.targetDirectoryId)));
                                    target.Insert(L"ownOrigin", value);
                                }
                                operation.Insert(L"target", target);
                            }
                            if (!item.receiptMeetingId.empty()) {
                                JsonObject receipt;
                                receipt.Insert(L"meeting_id", JsonValue::CreateStringValue(winrt::to_hstring(item.receiptMeetingId)));
                                operation.Insert(L"receipt", receipt);
                            }
                            operations.Append(operation);
                        }
                        JsonObject message;
                        message.Insert(L"command", JsonValue::CreateStringValue(L"local_recordings"));
                        message.Insert(L"nonce", JsonValue::CreateStringValue(winrt::to_hstring(nonce)));
                        message.Insert(L"rows", rows);
                        message.Insert(L"operations", operations);
                        message.Insert(L"recoveryRequired", JsonValue::CreateBooleanValue(localRecoveryRequired_));
                        core.PostWebMessageAsJson(message.Stringify());
                    };
                    // The page is answered only through the script that carries the
                    // nonce, and only while this document is still the one on screen.
                    nativeRunScript_ = [this, core, generation](std::string_view script) {
                        if (generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready) return;
                        if (utf8(core.Source()) != currentUrl_ ||
                            policy_.evaluate(currentUrl_).decision != RouteDecision::allow) return;
                        core.ExecuteScriptAsync(winrt::to_hstring(std::string(script)));
                    };
                    core.ExecuteScriptAsync(winrt::to_hstring(kDesktopBridgeScript)).Completed(
                        [this, alive, dispatcher, core, nonce, generation](auto const& operation, auto const&) {
                            dispatcher.TryEnqueue([this, alive, dispatcher, core, nonce, generation, operation] {
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
                                    // Тема читается у самой страницы, а не ждётся
                                    // объявлением: объявление приходит только после
                                    // рукопожатия, а окно обязано совпасть с
                                    // кабинетом уже при первой отрисовке. Пустое
                                    // значение означает «как в системе», и это
                                    // ровно то, что окно уже показывает.
                                    core.ExecuteScriptAsync(L"document.documentElement.dataset.theme || ''").Completed(
                                        [this, alive, dispatcher, core, generation](auto const& read, auto const&) {
                                            dispatcher.TryEnqueue([this, alive, core, generation, read, dispatcher] {
                                                if (!alive->load() || generation != documentGeneration_ ||
                                                    runtimeState_ != WebRuntimeState::ready) return;
                                                try {
                                                    if (utf8(core.Source()) != currentUrl_ ||
                                                        policy_.evaluate(currentUrl_).decision != RouteDecision::allow) return;
                                                    const auto theme = utf8(
                                                        winrt::Windows::Data::Json::JsonValue::Parse(read.GetResults()).GetString());
                                                    if (isAllowedAppearance(theme) && appearanceHandler_) appearanceHandler_(theme);
                                                } catch (...) {
                                                    // Нечитаемая тема не становится оформлением.
                                                }
                                            });
                                        });
                                    // The cabinet's deletion gate reads this version
                                    // at click time, so it is installed with the
                                    // page. It is installed only when something
                                    // behind it can actually store a deletion:
                                    // without that the page would ask this app to
                                    // delete and wait for an answer that never
                                    // comes, and on a meeting page it would stop
                                    // using the form that does work.
                                    if (deletionSelectionHandler_) {
                                        core.ExecuteScriptAsync(winrt::to_hstring(
                                            std::string(RecordingDeletionBridge::documentScript())));
                                    }
                                    if (nativeSettingsHandler_) {
                                        core.ExecuteScriptAsync(winrt::to_hstring(
                                            std::string(NativeSettingsBridge::documentScript())));
                                        // macOS starts the same handshake when its
                                        // settings page loads, and only there.
                                        beginNativeSettings();
                                    }
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
