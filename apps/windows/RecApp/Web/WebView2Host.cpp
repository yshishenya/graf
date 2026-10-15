#include "WebView2Host.h"

#include "../Contracts/WindowsDesktopContracts.h"
#include "../Upload/DesktopApiClient.h"
#include "../Shell/MeetingReminderPresenter.h"
#include <cstdio>
#include <algorithm>
#include <random>
#include <charconv>
#include <stdexcept>

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
#include <winrt/Windows.Data.Json.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Microsoft.Web.WebView2.Core.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <winrt/Microsoft.UI.Xaml.Automation.h>
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

// Owns the browser deferral and XAML child, not a second privileged host.
// Events hold weak references so Close also releases their captured state.
struct PaymentPopupWindow {
    winrt::Microsoft::UI::Xaml::Controls::WebView2 child{nullptr};
    winrt::Microsoft::UI::Xaml::Controls::WebView2 opener{nullptr};
    winrt::Microsoft::UI::Xaml::Controls::Panel panel{nullptr};
    winrt::Microsoft::UI::Dispatching::DispatcherQueueTimer timer{nullptr};
    winrt::Microsoft::UI::Dispatching::DispatcherQueue dispatcher{nullptr};
    winrt::Windows::Foundation::Deferral deferral{nullptr};
    std::atomic_bool cancellationRequested{false};
    bool completed = false;
    bool closed = false;
    bool ready = false;
    std::uint64_t generation = 0;
    unsigned childOrdinal = 0;
    std::uint64_t navigationId = 0;
    std::uint64_t interruptedNavigationId = 0;
    std::uint64_t interruptedAt = 0;
    static constexpr std::uint64_t replacementWindowMs = 100;
    std::string navigationUrl;

    void complete() noexcept {
        if (std::exchange(completed, true)) return;
        try { if (deferral) deferral.Complete(); } catch (...) {}
        deferral = nullptr;
    }
    void close() noexcept {
        // Completion delegates may run outside the UI apartment. The host owns
        // this object until its UI timer/teardown consumes the cancellation.
        if (dispatcher && !dispatcher.HasThreadAccess()) { cancellationRequested.store(true); return; }
        if (std::exchange(closed, true)) return;
        ready = false;
        try { if (timer) timer.Stop(); } catch (...) {}
        timer = nullptr;
        try { if (child) child.Close(); } catch (...) {}
        // Closing must precede release of a cancelled browser request, especially
        // if NewWindow succeeded but a later configuration operation failed.
        complete();
        try {
            std::uint32_t index = 0;
            if (panel && child && panel.Children().IndexOf(child, index)) panel.Children().RemoveAt(index);
        } catch (...) {}
        child = nullptr;
        panel = nullptr;
        try { if (opener) opener.Visibility(winrt::Microsoft::UI::Xaml::Visibility::Visible); } catch (...) {}
        opener = nullptr;
    }
    ~PaymentPopupWindow() { close(); }
};

WebView2Host::PopupSource paymentPopupSource(
    winrt::Microsoft::Web::WebView2::Core::CoreWebView2 const& core,
    winrt::Microsoft::Web::WebView2::Core::CoreWebView2NewWindowRequestedEventArgs const& args,
    std::uint64_t generation) {
    // Unsupported runtime interfaces or UNKNOWN/zero identities fail closed.
    try {
        const auto frame = args.OriginalSourceFrameInfo();
        return {generation, frame.FrameId(), core.FrameId(),
            frame.FrameKind() == winrt::Microsoft::Web::WebView2::Core::CoreWebView2FrameKind::MainFrame};
    } catch (...) { return {}; }
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
        // Preserve/validate original calendar JSON BEFORE SDK normalization.
        const auto join = DesktopApiClient::calendarJoinEnvelopePayload(json, "calendar_join");
        const auto cancel = DesktopApiClient::calendarJoinEnvelopePayload(json, "calendar_join_cancel");
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
        envelope.origin = origin;
        const auto direction = utf8(object.GetNamedString(L"direction"));
        if (direction == "native_to_web") envelope.direction = BridgeDirection::nativeToWeb;
        else if (direction == "web_to_native") envelope.direction = BridgeDirection::webToNative;
        else return std::nullopt;
        envelope.command = utf8(object.GetNamedString(L"command"));
        if (envelope.command == "calendar_join" || envelope.command == "calendar_join_cancel") {
            const auto& payload = envelope.command == "calendar_join" ? join : cancel;
            if (!payload || utf8(object.GetNamedString(L"origin")) != origin) return std::nullopt;
            envelope.payloadJson = *payload;
        } else envelope.payloadJson = utf8(object.GetNamedValue(L"payload").Stringify());
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
  // Presentation only. This script is installed after the host accepts the document.
  window.GRAFDesktopPlatform = 'windows';
  window.GRAFPlatform?.refresh();
  let nonce = null;
  let nextMessageId = 1;
  let calendarAvailable = false;
  let calendarPending = null;
  const calendarUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const send = (command, payload) => {
    if (!nonce) return false;
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
    return true;
  };
  const calendarButtons = eventId => [...document.querySelectorAll('[data-calendar-join]')]
    .filter(button => button.dataset.calendarJoin.toLowerCase() === eventId && button.isConnected);
  const calendarActionable = button => button.isConnected && !button.hasAttribute('disabled') && !button.closest('[hidden],[inert]');
  const calendarFeedback = (item, state) => {
    const busy = state === 'resolving' || state === 'opening';
    for (const [button, previous] of item.buttons) {
      if (!button.isConnected) item.buttons.delete(button);
      else if (!busy && button.getAttribute('aria-disabled') === 'true') {
        if (previous === null) button.removeAttribute('aria-disabled'); else button.setAttribute('aria-disabled', previous);
      }
    }
    calendarButtons(item.eventId).forEach(button => {
      let status = button.parentElement.querySelector('[data-calendar-join-status]');
      if (!status) {
        status = document.createElement('span'); status.dataset.calendarJoinStatus = ''; button.after(status);
      }
      status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
      const messages = {resolving:'Открываем…', opening:'Открываем…', handed_off:'Ссылка передана приложению',
        failed:'Не удалось открыть. Повторите попытку.', cancelled:'Действие отменено. Повторите попытку.'};
      if (status.textContent !== messages[state]) status.textContent = messages[state];
      if (busy && button.getAttribute('aria-disabled') !== 'true') {
        item.buttons.set(button, button.getAttribute('aria-disabled')); button.setAttribute('aria-disabled', 'true');
      }
    });
  };
  const cancelCalendar = () => {
    const item = calendarPending;
    if (!item) return;
    calendarPending = null;
    calendarFeedback(item, 'cancelled');
    try { send('calendar_join_cancel', {eventId:item.eventId, requestId:item.requestId}); } catch (_) {}
  };
  // Presentation only; the host separately validates both handlers and the current document.
  window.__grafSetCalendarJoinAvailable = available => {
    calendarAvailable = available === true;
    if (!calendarAvailable) cancelCalendar();
  };
  new MutationObserver(() => {
    if (!calendarPending) return;
    if (!calendarButtons(calendarPending.eventId).some(calendarActionable)) cancelCalendar();
    else calendarFeedback(calendarPending, calendarPending.state);
  }).observe(document.documentElement, {childList:true, subtree:true, attributes:true,
    attributeFilter:['data-calendar-join','hidden','inert','disabled']});
  window.addEventListener('pagehide', cancelCalendar);
  document.addEventListener('click', event => {
    const button = event.target instanceof Element ? event.target.closest('[data-calendar-join]') : null;
    if (!button || !event.isTrusted || !nonce || !calendarAvailable) return;
    event.preventDefault();
    if (calendarPending || !calendarActionable(button) || button.getAttribute('aria-disabled') === 'true' ||
        !calendarUUID.test(button.dataset.calendarJoin || '')) return;
    const item = {eventId:button.dataset.calendarJoin.toLowerCase(), requestId:crypto.randomUUID(), state:'resolving', buttons:new Map()};
    calendarPending = item;
    calendarFeedback(item, item.state);
    try {
      if (send('calendar_join', {action:'joinCalendarEvent', eventId:item.eventId, requestId:item.requestId})) return;
    } catch (_) {}
    if (calendarPending === item) {calendarPending = null; calendarFeedback(item, 'failed');}
  }, true);
)JS" LR"JS(  // The cabinet's theme is a user setting in the cabinet itself (`data-theme`),
  // so the page tells the app which one is in force instead of the app guessing.
  const publishAppearance = () => {
    const theme = document.documentElement.dataset.theme;
    send('app_appearance', {theme: theme === 'light' || theme === 'dark' ? theme : 'system'});
  };
  new MutationObserver(publishAppearance).observe(document.documentElement, {
    attributes: true, attributeFilter: ['data-theme']
  });
  publishAppearance();
  let updateAvailable = false;
  const paintUpdate = () => document.querySelectorAll('[data-graf-app-update]').forEach(button => {
    button.hidden = !updateAvailable;
  });
  window.__grafSetUpdateAvailable = available => {
    updateAvailable = available === true;
    paintUpdate();
  };
  document.addEventListener('htmx:afterSwap', paintUpdate);
  document.addEventListener('click', (event) => {
    const button = event.target instanceof Element
      ? event.target.closest('[data-graf-app-quit], [data-graf-local-recording-action], [data-graf-app-update]') : null;
    if (!button || button.disabled) return;
    if (button.hasAttribute('data-graf-app-quit')) send('request_app_quit', {action: 'quit'});
    else if (button.hasAttribute('data-graf-app-update')) send('request_app_update', {});
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
      if (nonce !== message.nonce) cancelCalendar();
      nonce = message.nonce;
      nextMessageId = 1;
      // The theme is announced with the handshake, not at document start: the
      // envelope needs the nonce, and before the handshake the app would drop it
      // as a message from a document it has not accepted yet.
      publishAppearance();
    } else if (message.command === 'calendar_join_reply' && calendarPending && nonce && message.nonce === nonce &&
        message.request_id === calendarPending.requestId) {
      if (!calendarButtons(calendarPending.eventId).some(calendarActionable)) {cancelCalendar(); return;}
      const state = message.state;
      const reasons = ['busy','not_ready','stale','auth_required','event_unavailable','dependency_unavailable',
        'invalid_target','launch_failed','cancelled'];
      if (message.reason !== undefined && !reasons.includes(message.reason)) return;
      if ((state === 'resolving' && calendarPending.state === 'resolving') ||
          (state === 'opening' && calendarPending.state === 'resolving' && message.reason === undefined)) {
        calendarPending.state = state; calendarFeedback(calendarPending, state);
      } else if (state === 'failed' || state === 'cancelled' ||
          (state === 'handed_off' && calendarPending.state === 'opening' && message.reason === undefined)) {
        const item = calendarPending; calendarPending = null; calendarFeedback(item, state);
      }
    } else if (message.command === 'native_reply' && typeof message.request_id === 'number') {
      window.dispatchEvent(new CustomEvent('graf:native-settings-reply', {
        detail: {requestId: message.request_id, payload: message.payload || null}
      }));
    } else if (message.command === 'local_recordings' && nonce && message.nonce === nonce && Array.isArray(message.rows)) {
      rows = message.rows;
      // The deletions in flight and the recovery notice travel with the rows: the
      // cabinet prints them, so a saved request is not merely remembered by the app.
      const operations = Array.isArray(message.operations) ? message.operations : [];
      window.GRAFLocalRecordings?.update(rows, operations, message.recoveryRequired === true, message.state);
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
    : policy_(std::move(policy)), bridge_(policy_.trustedOrigin()) {}

WebView2Host::~WebView2Host() {
    runtimeHandler_ = {};
    authSessionHandler_ = {};
    close();
}

void WebView2Host::invalidateUserTime() noexcept {
    localDocumentIdentity_ = false;
    userTimeZone_.clear(); userTimeSession_.clear();
    userTimeAttemptedRevision_.reset();
    ++userTimeRevision_;
}

void WebView2Host::bindUserTimeAccount(std::string origin, std::string user, std::string workspace,
    std::string sessionToken, std::uint64_t authGeneration) {
    if (origin != policy_.trustedOrigin() || !DesktopApiClient::accountId(user) ||
        !DesktopApiClient::accountId(workspace) || sessionToken.empty()) {
        origin.clear(); user.clear(); workspace.clear(); sessionToken.clear();
    }
    const bool changed = userTimeAccount_.origin != origin || userTimeAccount_.user != user ||
        userTimeAccount_.workspace != workspace || userTimeAccount_.token != sessionToken ||
        userTimeAccount_.authGeneration != authGeneration;
    if (changed) {
        invalidateUserTime();
        userTimeAccount_ = {std::move(origin), std::move(user), std::move(workspace), std::move(sessionToken),
                            {}, {}, authGeneration, 0, 0};
    }
    refreshUserTime();
    if (changed && protectedLocalMode_ && nativePublishLocalRecordings_) nativePublishLocalRecordings_();
}

bool WebView2Host::userTimeDocumentCurrent() const {
    if (!alive_ || !alive_->load() || runtimeState_ != WebRuntimeState::ready || documentNonce_.empty() ||
        currentUrl_ != committedDocumentUrl_ || userTimeAccount_.origin != policy_.trustedOrigin() ||
        userTimeAccount_.token.empty() || userTimeAccount_.token != userTimeCookieToken_ ||
        userTimeCookieGeneration_ != documentGeneration_) return false;
    const auto route = policy_.evaluate(currentUrl_);
    if (route.decision != RouteDecision::allow || !policy_.sharesOrigin(currentUrl_) ||
        !policy_.allowsNativeBridge(currentUrl_)) return false;
    // Billing action URLs are navigation targets, not confirmed display pages.
    if (route.kind == RouteKind::billing && policy_.safeRecoveryUrl(currentUrl_).empty()) return false;
    return route.kind == RouteKind::meetings || route.kind == RouteKind::meetingDetail ||
        route.kind == RouteKind::share || route.kind == RouteKind::deletionReport ||
        route.kind == RouteKind::settings || route.kind == RouteKind::nativeSettings || route.kind == RouteKind::billing;
}

bool WebView2Host::userTimeReadCurrent(const UserTimeRead& read) const {
    return userTimeDocumentCurrent() && read.documentGeneration == documentGeneration_ &&
        read.revision == userTimeRevision_ && read.nonce == documentNonce_ && read.url == currentUrl_ &&
        read.origin == userTimeAccount_.origin && read.user == userTimeAccount_.user &&
        read.workspace == userTimeAccount_.workspace && read.token == userTimeAccount_.token &&
        read.authGeneration == userTimeAccount_.authGeneration;
}

void WebView2Host::refreshUserTime() {
    if (!nativeReadUserTime_ || userTimeAttemptedRevision_ == userTimeRevision_ || !userTimeDocumentCurrent()) return;
    auto read = userTimeAccount_;
    read.documentGeneration = documentGeneration_; read.revision = userTimeRevision_;
    read.nonce = documentNonce_; read.url = currentUrl_;
    userTimeAttemptedRevision_ = userTimeRevision_;
    const auto alive = alive_;
    const auto invoke = nativeReadUserTime_;
    try { invoke(read); }
    catch (...) {
        if (alive->load()) completeUserTimeRead(read, {}, read.url);
    }
}

void WebView2Host::reconcileUserTimeCookie(std::uint64_t generation, std::string_view nonce,
    std::string_view url, std::string token) {
    if (!alive_ || !alive_->load() || generation != documentGeneration_ || nonce != documentNonce_ ||
        runtimeState_ != WebRuntimeState::ready || url != currentUrl_ || url != committedDocumentUrl_ ||
        !policy_.allowsNativeBridge(url)) return;
    userTimeCookieGeneration_ = generation;
    userTimeCookieToken_ = std::move(token);
    refreshUserTime();
}

void WebView2Host::completeUserTimeRead(const UserTimeRead& read, std::string_view raw, std::string_view source) {
    if (!userTimeReadCurrent(read) || source != read.url) return;
    const auto metadata = DesktopApiClient::decodeUserTimeMetadata(raw);
    const bool identityAccepted = metadata && metadata->userId == read.user && metadata->workspaceId == read.workspace &&
        metadata->documentUrl == read.url;
    const bool accepted = identityAccepted && MeetingReminderPresenter::upcomingTime(0, metadata->timeZone).has_value();
    invalidateUserTime();
    localDocumentIdentity_ = identityAccepted;
    if (accepted) { userTimeZone_ = metadata->timeZone; userTimeSession_ = metadata->sessionId; }
    // One read per confirmed context, including invalid/empty metadata. Same-page
    // saves are staged until the next confirmed document, just as on macOS.
    userTimeAttemptedRevision_ = userTimeRevision_;
    if (protectedLocalMode_ && nativePublishLocalRecordings_) nativePublishLocalRecordings_();
}

bool WebView2Host::reconcileAuthSessionForDocument(std::uint64_t generation, std::string nonce,
    std::string url, std::string token, bool reconciled) {
    const auto alive = alive_;
    if (!alive || !alive->load() || generation != documentGeneration_ || nonce != documentNonce_ ||
        runtimeState_ != WebRuntimeState::ready || url != currentUrl_ || url != committedDocumentUrl_ ||
        !policy_.allowsNativeBridge(url)) return false;
    const auto revision = userTimeRevision_;
    const auto handler = authSessionHandler_;
    try { if (handler) handler(token); }
    catch (...) {
        if (alive->load() && generation == documentGeneration_ && nonce == documentNonce_ &&
            runtimeState_ == WebRuntimeState::ready && url == currentUrl_ && url == committedDocumentUrl_ &&
            revision == userTimeRevision_) bindUserTimeAccount({}, {}, {}, {}, 0);
        return false;
    }
    return alive->load() && reconciled && generation == documentGeneration_ && nonce == documentNonce_ &&
        runtimeState_ == WebRuntimeState::ready && url == currentUrl_ && url == committedDocumentUrl_;
}

void WebView2Host::setRuntimeState(WebRuntimeState state) noexcept {
    if (state != WebRuntimeState::ready) {
        invalidateUserTime(); userTimeCookieToken_.clear(); userTimeCookieGeneration_ = 0;
        nativeReadUserTime_ = {};
    }
    if (state != WebRuntimeState::ready) revokeCalendarDocument();
    if (state == WebRuntimeState::authRequired || state == WebRuntimeState::closed ||
        state == WebRuntimeState::unavailable) cancelPaymentPopup();
    if (state != WebRuntimeState::ready) nativeSettingsNonce_.clear();
    runtimeState_ = state;
    if (state != WebRuntimeState::ready) {
        documentNonce_.clear();
        bridge_.invalidate();
        nativePublishLocalRecordings_ = {};
        nativeRunScript_ = {};
        nativeReplyCalendarJoin_ = {};
    }
    try {
        if (runtimeHandler_) runtimeHandler_(state);
    } catch (...) {
        invalidateUserTime(); userTimeCookieToken_.clear(); userTimeCookieGeneration_ = 0;
        nativeReadUserTime_ = {};
        revokeCalendarDocument();
        runtimeState_ = WebRuntimeState::unavailable;
        documentNonce_.clear();
        nativeReplyCalendarJoin_ = {};
        bridge_.invalidate();
    }
}

void WebView2Host::fail(std::string_view stage, std::int32_t code) noexcept {
    revokeCalendarDocument();
    cancelPaymentPopup();
    authContinuation_ = AuthContinuation::none;
    payment_.stop();
    navigationId_ = 0;
    resetDocumentResponse();
    committedDocumentUrl_.clear();
    cancelDialog();
    char hex[16]{};
    std::snprintf(hex, sizeof(hex), "0x%08X", static_cast<unsigned>(code));
    failureDetail_ = std::string(stage) + " · " + hex;
    setRuntimeState(WebRuntimeState::unavailable);
}

std::uint64_t WebView2Host::monotonicMilliseconds() noexcept {
#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
    return GetTickCount64(); // Includes suspend; wall-clock changes cannot extend payment permission.
#else
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
#endif
}

WebResponseDecision WebView2Host::pendingAuthRecovery() const noexcept {
    if (runtimeState_ == WebRuntimeState::authRequired &&
        (recoveryReason_ == WebResponseDecision::expiredSession || recoveryReason_ == WebResponseDecision::workspaceReselection))
        return recoveryReason_;
    return WebResponseDecision::ignore;
}

std::string WebView2Host::recoveryUrl() const {
    if (recoveryReason_ == WebResponseDecision::expiredSession || recoveryReason_ == WebResponseDecision::workspaceReselection)
        return signInUrl();
    return policy_.recoveryUrl(recoveryReason_, safeRecoveryUrl_, billingContext_);
}

std::string WebView2Host::signInUrl() const {
    const auto plain = policy_.recoveryUrl(WebResponseDecision::expiredSession, safeRecoveryUrl_, billingContext_);
    if (!signInUrlBuilder_) return plain;
    try {
        const auto decorated = signInUrlBuilder_(plain);
        if (decorated == plain) return plain;
        if (decorated.size() > 2048 || decorated.size() <= plain.size() ||
            decorated.compare(0, plain.size(), plain) != 0 || decorated[plain.size()] != '&' ||
            decorated.find('#') != std::string::npos || policy_.evaluate(decorated).kind != RouteKind::authRecovery) return plain;
        auto fields = std::string_view(decorated).substr(plain.size() + 1);
        while (!fields.empty()) {
            const auto end = fields.find('&');
            const auto field = fields.substr(0, end);
            const auto key = field.substr(0, field.find('='));
            if (key.empty() || key == "next" || key == "workspace_id") return plain;
            for (const char c : key) {
                if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) return plain;
            }
            if (end == std::string_view::npos) break;
            fields.remove_prefix(end + 1);
        }
        return decorated;
    } catch (...) { return plain; } // Optional attribution must never prevent sign-in.
}

RouteEvaluation WebView2Host::beginDocumentNavigation(std::string_view url, std::uint64_t id,
    bool redirected, std::uint64_t now, std::string_view method) {
    if (runtimeState_ == WebRuntimeState::closed || id == 0) return {};
    cancelPaymentPopup(); // A new parent document cannot retain an old payment child.
    if (payment_.started() && !payment_.live(now)) {
        payment_.stop();
        if (!policy_.sharesOrigin(url)) {
            fail("payment-expired", 0);
            return {};
        }
    }
    if (authContinuation_ != AuthContinuation::none && activeAuthContinuation() == AuthContinuation::none) {
        fail("auth-expired", 0);
        return {};
    }
    const auto source = redirected && id == navigationId_ ? navigationSourceUrl_ : committedDocumentUrl_;
    const bool startsPayment = !payment_.started() && policy_.canStartPayment(source, url);
    const auto route = policy_.evaluate(url, true, activeAuthContinuation(), payment_.live(now) || startsPayment);
    if (route.decision != RouteDecision::allow) {
        if (payment_.started() || redirected) fail("route", 0);
        return route;
    }
    if (route.kind == RouteKind::nativeSettings || route.kind == RouteKind::artifactDownload) return route;
    if (startsPayment) (void)payment_.begin(policy_, source, url, now);
    const auto start = policy_.authContinuationForStart(url);
    if (start != AuthContinuation::none && !redirected) {
        payment_.stop();
        authContinuation_ = start;
        authStarted_ = std::chrono::steady_clock::now();
        authNavigations_ = 0;
    } else if (route.kind != RouteKind::authProvider && route.kind != RouteKind::authRecovery) {
        authContinuation_ = AuthContinuation::none;
    }
    if (authContinuation_ != AuthContinuation::none) ++authNavigations_;
    if (route.kind == RouteKind::authRecovery) payment_.stop();
    if (route.kind == RouteKind::billing && !billingContext_) {
        billingContext_ = true;
        safeRecoveryUrl_ = policy_.trustedOrigin() + "/billing";
    }
    if (const auto safe = policy_.safeRecoveryUrl(url, method); !safe.empty()) safeRecoveryUrl_ = safe;
    recoveryReason_ = WebResponseDecision::unavailable;
    navigationSourceUrl_ = source;
    requestedDocumentUrl_.clear();
    navigationUrl_ = std::string(url);
    navigationMethod_ = std::string(method);
    revokeCalendarDocument();
    resetDocumentResponse();
    committedDocumentUrl_.clear();
    cancelDialog();
    ++documentGeneration_;
    navigationId_ = id;
    failureDetail_.clear();
    setRuntimeState(WebRuntimeState::initializing);
    return route;
}

bool WebView2Host::observeDocumentResponse(std::string_view url, std::uint64_t generation,
    std::string_view method, const WebDocumentResponse& response) {
    const auto withoutFragment = [](std::string_view value) { return value.substr(0, value.find('#')); };
    if (navigationId_ == 0 || generation != documentGeneration_ ||
        withoutFragment(url) != withoutFragment(navigationUrl_) || !policy_.sharesOrigin(url)) return false;
    navigationMethod_ = std::string(method);
    documentResponse_ = response;
    if (const auto safe = policy_.safeRecoveryUrl(url, method); !safe.empty()) safeRecoveryUrl_ = safe;
    return true;
}

void WebView2Host::resetDocumentResponse() noexcept {
    documentResponse_.reset();
    documentCompletion_.reset();
    try { if (nativeStopResponseTimer_) nativeStopResponseTimer_(); } catch (...) {}
}

std::string WebView2Host::documentRequestTag(std::string_view url) const {
    if (navigationId_ == 0 || !policy_.sharesOrigin(url) ||
        url != std::string_view(navigationUrl_).substr(0, navigationUrl_.find('#'))) return {};
    return std::to_string(documentGeneration_);
}

bool WebView2Host::observeDocumentResponseHeaders(std::string_view url, std::string_view tag,
    std::string_view destination, std::string_view method, const WebDocumentResponse& response) {
    if (destination != "document" || tag.empty()) return false;
    std::uint64_t generation = 0;
    const auto parsed = std::from_chars(tag.data(), tag.data() + tag.size(), generation);
    if (parsed.ec != std::errc{} || parsed.ptr != tag.data() + tag.size()) return false;
    return observeDocumentResponse(url, generation, method, response);
}

bool WebView2Host::observeDocumentCompletion(std::string_view url, std::uint64_t id,
    int status, bool succeeded, bool httpErrorDocument, std::uint64_t now) {
    if (runtimeState_ == WebRuntimeState::closed || id == 0 || id != navigationId_ || documentCompletion_) return false;
    documentCompletion_ = DocumentCompletion{std::string(url), status, succeeded, httpErrorDocument, now};
    return true;
}

WebResponseDecision WebView2Host::tryFinishDocumentNavigation(std::uint64_t now) {
    if (navigationId_ == 0 || !documentCompletion_) return WebResponseDecision::ignore;
    const auto completion = *documentCompletion_;
    const bool httpDocument = completion.succeeded ||
        (completion.httpErrorDocument && completion.status >= 400 && completion.status <= 599);
    const bool sameDocument = std::string_view(completion.url).substr(0, completion.url.find('#')) ==
        std::string_view(navigationUrl_).substr(0, navigationUrl_.find('#'));
    // Own-origin forms need the response headers too (not only bridge pages):
    // reselect-space and email-link MIME must survive either callback order.
    if (httpDocument && sameDocument && policy_.sharesOrigin(completion.url)) {
        if (now < completion.observedAt || now - completion.observedAt >= kResponseWaitMs) {
            fail("response-metadata-timeout", 0);
            return WebResponseDecision::unavailable;
        }
        if (!documentResponse_) return WebResponseDecision::ignore;
    }
    auto response = documentResponse_.value_or(WebDocumentResponse{});
    response.status = completion.status;
    response.transportSucceeded = httpDocument;
    documentCompletion_.reset();
    if (nativeStopResponseTimer_) nativeStopResponseTimer_();
    return completeDocumentNavigation(completion.url, navigationId_, response, now);
}

bool WebView2Host::beginPaymentPopup(std::string_view url, PopupSource source, std::uint64_t now,
    std::function<void()> cleanup) {
    if ((runtimeState_ != WebRuntimeState::ready && runtimeState_ != WebRuntimeState::unprivileged) ||
        source.documentGeneration != documentGeneration_ || !source.isMainFrame ||
        source.frameId == 0 || source.frameId != source.coreFrameId ||
        (payment_.started() && !payment_.live(now))) return false;
    if (paymentPopup_) {
        // A bounded chain keeps every opener alive but has only one active surface.
        // Neither nesting nor controller creation restarts the first deadline.
        if (!paymentPopupLiveAt(now) || !paymentPopup_->handedOff || paymentPopup_->returning ||
            !payment_.live(now) || source.frameId != paymentPopup_->activeFrameId ||
            paymentPopup_->children >= 8 ||
            policy_.evaluate(url, true, AuthContinuation::none, true).kind != RouteKind::paymentProvider) return false;
        auto previous = std::move(paymentPopup_->cleanup);
        paymentPopup_->cleanup = [previous = std::move(previous), cleanup = std::move(cleanup)] {
            try { if (cleanup) cleanup(); } catch (...) {}
            try { if (previous) previous(); } catch (...) {}
        };
        paymentPopup_->source = source;
        paymentPopup_->handedOff = false;
        paymentPopup_->activeFrameId = 0;
        ++paymentPopup_->children;
        return true;
    }
    const auto from = policy_.evaluate(committedDocumentUrl_);
    const auto own = policy_.evaluate(url);
    const bool starts = policy_.canStartPayment(committedDocumentUrl_, url);
    const bool checkout = from.kind == RouteKind::billing && own.kind == RouteKind::billing &&
        own.decision == RouteDecision::allow;
    if (!checkout && !starts && !(payment_.live(now) &&
        policy_.evaluate(url, true, AuthContinuation::none, true).decision == RouteDecision::allow)) return false;
    // Keep the original parent deadline even after an own-origin return stops
    // external navigation authority. A late popup cannot start another 15 minutes.
    paymentPopup_ = PaymentPopup{source, committedDocumentUrl_, payment_.startedAt().value_or(now), false, false, std::move(cleanup)};
    if (starts) (void)payment_.begin(policy_, committedDocumentUrl_, url, now);
    cancelDialog();
    setRuntimeState(WebRuntimeState::unprivileged); // Revoke the opener's old nonce as well.
    return true;
}

bool WebView2Host::paymentPopupLiveAt(std::uint64_t now) const noexcept {
    return paymentPopup_ && runtimeState_ == WebRuntimeState::unprivileged &&
        paymentPopup_->source.documentGeneration == documentGeneration_ &&
        now >= paymentPopup_->admittedAt && now - paymentPopup_->admittedAt < 900000 &&
        (!payment_.started() || payment_.live(now));
}

bool WebView2Host::handOffPaymentPopup(PopupSource source, std::uint64_t now) {
    if (!paymentPopup_ || paymentPopup_->handedOff || source.documentGeneration != documentGeneration_) return false;
    if (!paymentPopupLiveAt(now) || !source.isMainFrame || source.frameId == 0 ||
        source.frameId != source.coreFrameId || source.frameId != paymentPopup_->source.frameId ||
        source.documentGeneration != documentGeneration_) {
        fail("payment-popup-binding", 0);
        return false;
    }
    paymentPopup_->handedOff = true;
    return true;
}

bool WebView2Host::paymentPopupChildCurrent(std::uint64_t generation, unsigned childOrdinal,
    std::uint64_t now) const noexcept {
    return paymentPopupLiveAt(now) && paymentPopup_->handedOff && generation == documentGeneration_ &&
        childOrdinal == paymentPopup_->children;
}

bool WebView2Host::bindPaymentPopupFrame(std::uint32_t frameId, std::uint64_t generation,
    unsigned childOrdinal, std::uint64_t now) {
    if (!paymentPopupChildCurrent(generation, childOrdinal, now) || frameId == 0 ||
        (paymentPopup_->activeFrameId != 0 && paymentPopup_->activeFrameId != frameId)) return false;
    paymentPopup_->activeFrameId = frameId;
    return true;
}

RouteEvaluation WebView2Host::evaluatePaymentPopupDocument(std::string_view url, std::uint64_t now) {
    if (!paymentPopupLiveAt(now) || !paymentPopup_->handedOff) {
        cancelPaymentPopup();
        return {};
    }
    const bool starts = !payment_.started() && !paymentPopup_->returning &&
        policy_.canStartPayment(paymentPopup_->billingSource, url);
    const auto result = policy_.evaluate(url, true, AuthContinuation::none, payment_.live(now) || starts);
    if (result.decision != RouteDecision::allow || result.kind == RouteKind::artifactDownload ||
        result.kind == RouteKind::nativeSettings) {
        cancelPaymentPopup();
        return {};
    }
    if (starts) (void)payment_.begin(policy_, paymentPopup_->billingSource, url, now);
    if (payment_.started() && policy_.sharesOrigin(url)) {
        paymentPopup_->returning = true;
        payment_.stop(); // The original return request still executes; no GET substitution.
    }
    return result;
}

void WebView2Host::cancelPaymentPopup() noexcept {
    auto popup = std::exchange(paymentPopup_, std::nullopt);
    if (!popup) return;
    payment_.stop();
    try { if (popup->cleanup) popup->cleanup(); } catch (...) {}
}

RouteEvaluation WebView2Host::evaluatePopupNavigation(std::string_view url, std::uint64_t now) {
    if (runtimeState_ == WebRuntimeState::closed) return {};
    if (payment_.started() && !payment_.live(now)) { fail("payment-expired", 0); return {}; }
    if (payment_.started() || policy_.evaluate(committedDocumentUrl_).kind == RouteKind::billing ||
        policy_.evaluate(url).kind == RouteKind::billing) {
        // The URI-only popup event proves neither GET nor preservation of POST.
        fail("payment-popup-request-unavailable", static_cast<std::int32_t>(0x80004001u));
        return {};
    }
    return policy_.evaluate(url, true, activeAuthContinuation());
}

WebResponseDecision WebView2Host::completeDocumentNavigation(std::string_view url, std::uint64_t id,
    const WebDocumentResponse& response, std::uint64_t now) {
    using D = WebResponseDecision;
    if (runtimeState_ == WebRuntimeState::closed || id == 0 || id != navigationId_) return D::ignore;
    if (url.substr(0, url.find('#')) != std::string_view(navigationUrl_).substr(0, navigationUrl_.find('#'))) {
        fail("document-changed", 0);
        return D::blocked;
    }
    navigationId_ = 0;
    const auto result = policy_.response(url, response, activeAuthContinuation(), payment_.live(now)).decision;
    payment_.loaded(policy_, url, now);
    currentUrl_ = std::string(url);
    recoveryReason_ = result;
    if (result == D::externalDocument) {
        committedDocumentUrl_ = std::string(url);
        // HTTP failures at a bank/provider are not failures of GRAF's session.
        if (response.status >= 400) payment_.stop();
        setRuntimeState(WebRuntimeState::unprivileged);
    } else if (result == D::interactiveForm) {
        committedDocumentUrl_ = std::string(url);
        const auto kind = policy_.evaluate(url).kind;
        setRuntimeState(kind == RouteKind::authRecovery ? WebRuntimeState::authRequired : WebRuntimeState::unprivileged);
    } else if (result == D::cabinet && policy_.allowsNativeBridge(url)) {
        committedDocumentUrl_ = std::string(url);
        authContinuation_ = AuthContinuation::none;
        // The native completion handler alone creates a nonce/bridge afterwards.
    } else if (result == D::expiredSession || result == D::workspaceReselection) {
        payment_.stop();
        authContinuation_ = AuthContinuation::none;
        if (authSessionHandler_) authSessionHandler_({});
        setRuntimeState(WebRuntimeState::authRequired);
    } else {
        fail(result == D::accessDenied ? "access-denied" : result == D::notFound ? "not-found" :
            result == D::timeout ? "timeout" : "document", response.status);
    }
    return result;
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
    revokeCalendarDocument();
    if (alive_) alive_->store(false);
    ++documentGeneration_;
    navigationId_ = 0;
    authContinuation_ = AuthContinuation::none;
    payment_.stop();
    committedDocumentUrl_.clear();
    navigationSourceUrl_.clear();
    navigationUrl_.clear();
    resetDocumentResponse();
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
    nativeFinishDocument_ = {};
    nativeStopResponseTimer_ = {};
    preferredColorScheme_ = {};
    userTimeAccount_ = {};
    setRuntimeState(WebRuntimeState::closed);
}

RouteEvaluation WebView2Host::navigate(std::string url) {
    const auto evaluation = policy_.evaluate(url);
    if (runtimeState_ != WebRuntimeState::closed && evaluation.decision == RouteDecision::allow) {
        // Native callers can request account/login recovery before a control is
        // ready. Keep the approved destination without inventing a loaded source.
        if (const auto safe = policy_.safeRecoveryUrl(url); !safe.empty()) {
            safeRecoveryUrl_ = safe;
            billingContext_ = evaluation.kind == RouteKind::billing;
            recoveryReason_ = WebResponseDecision::unavailable;
            requestedDocumentUrl_ = url;
        } else {
            const auto pathEnd = url.find('?');
            const auto entry = url.substr(0, pathEnd);
            if (entry == policy_.trustedOrigin() + "/login" || entry == policy_.trustedOrigin() + "/sign-up")
                requestedDocumentUrl_ = url;
        }
#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
        if (nativeNavigate_) nativeNavigate_(url);
#endif
    }
    if (navigationHandler_) navigationHandler_(evaluation);
    return evaluation;
}

void WebView2Host::reload() {
    if (runtimeState_ == WebRuntimeState::closed) return;
    if (paymentPopup_) {
        cancelPaymentPopup();
        (void)navigate(policy_.trustedOrigin() + "/billing");
        return;
    }
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
    (void)navigate(requestedDocumentUrl_.empty() ? recoveryUrl() : requestedDocumentUrl_);
}

void WebView2Host::handleProcessFailure(WebProcessFailure failure, std::int32_t exitCode) noexcept {
    // GPU/utility failures are recovered by WebView2 without replacing the
    // document. Invalidating its bridge here strands an otherwise live cabinet.
    if (runtimeState_ == WebRuntimeState::closed ||
        failure == WebProcessFailure::automaticallyRecoverable) return;
    const char* stage = "webview-process";
    switch (failure) {
    case WebProcessFailure::browserExited:
        recreateRequired_ = true;
        stage = "browser-process-exited";
        break;
    case WebProcessFailure::renderExited: stage = "render-process-exited"; break;
    case WebProcessFailure::renderUnresponsive: stage = "render-process-unresponsive"; break;
    case WebProcessFailure::frameRenderExited: stage = "frame-render-process-exited"; break;
    case WebProcessFailure::automaticallyRecoverable: return;
    }
    revokeCalendarDocument();
    ++documentGeneration_;
    fail(stage, exitCode);
}

void WebView2Host::back() {
    if (paymentPopup_) {
        cancelPaymentPopup();
        (void)navigate(policy_.trustedOrigin() + "/billing");
    } else if (canGoBack()) nativeBack_();
}
void WebView2Host::forward() { if (canGoForward()) nativeForward_(); }
bool WebView2Host::canGoBack() const {
    if (paymentPopup_) return true; // One action out even on the first payment page.
    try { return !recreateRequired_ && nativeCanGoBack_ && nativeCanGoBack_(); } catch (...) { return false; }
}
bool WebView2Host::canGoForward() const {
    if (paymentPopup_) return false; // Never traverse/replay a checkout action.
    try { return !recreateRequired_ && nativeCanGoForward_ && nativeCanGoForward_(); } catch (...) { return false; }
}

bool WebView2Host::isAllowedQuitPayload(std::string_view payload) noexcept {
    return payload == R"({"action":"quit"})";
}

void WebView2Host::setAppUpdateAvailable(bool available) {
    appUpdateAvailable_ = available;
    if (runtimeState_ == WebRuntimeState::ready && nativeRunScript_)
        nativeRunScript_(available ? "window.__grafSetUpdateAvailable?.(true)" : "window.__grafSetUpdateAvailable?.(false)");
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
    protectedLocalMode_ = false;
    protectedLocalValue_.reset();
    protectedLocalTimings_.reset();
    localRecordings_ = std::move(rows);
    localDeletionOperations_ = std::move(operations);
    localRecoveryRequired_ = recoveryRequired;
    if (runtimeState_ == WebRuntimeState::ready && nativePublishLocalRecordings_) nativePublishLocalRecordings_();
}

void WebView2Host::setProtectedLocalRecordings(std::shared_ptr<const ProtectedUploadQueueValue> value, bool complete,
    std::string origin, std::string user, std::string workspace, std::uint64_t authGeneration,
    std::shared_ptr<const ProtectedLocalRecordingTimings> timings) {
    if (timings && (!value || timings->snapshot != value || timings->rows.size() != value->items().size())) timings.reset();
    const bool unchanged = protectedLocalMode_ && protectedLocalValue_ == value && protectedLocalComplete_ == complete &&
        protectedLocalTimings_ == timings &&
        localAccount_.origin == origin && localAccount_.user == user && localAccount_.workspace == workspace &&
        localAccount_.authGeneration == authGeneration;
    if (unchanged && (!protectedLocalPublicationPending_ || std::chrono::steady_clock::now() < protectedLocalRetryAt_)) return;
    protectedLocalMode_ = true;
    protectedLocalValue_ = std::move(value);
    protectedLocalTimings_ = std::move(timings);
    protectedLocalComplete_ = complete;
    localAccount_ = {std::move(origin), std::move(user), std::move(workspace), {}, {}, {}, authGeneration, 0, 0};
    protectedLocalPublicationPending_ = true;
    std::vector<WebViewLocalRecordingRow>().swap(localRecordings_);
    std::vector<CabinetDeletionOperation>().swap(localDeletionOperations_);
    if (runtimeState_ == WebRuntimeState::ready && nativePublishLocalRecordings_) nativePublishLocalRecordings_();
}

void WebView2Host::failProtectedLocalPublication() noexcept {
    protectedLocalPublicationPending_ = true;
    protectedLocalRetryAt_ = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    try {
        if (nativeRunScript_) nativeRunScript_("window.GRAFLocalRecordings?.update([],[],false,'unavailable')");
    } catch (...) { /* The same unavailable WebView may also reject the fallback; keep the pending retry. */ }
}

std::string_view WebView2Host::localRecordingStatus(const ProtectedUploadQueueValue::Item& item) noexcept {
    switch (item.status) {
    case UploadQueueStatus::pending: return "Ожидает отправки";
    case UploadQueueStatus::uploading: return "Отправляется";
    case UploadQueueStatus::retry: return item.safeReason == "retry_budget_exhausted"
        ? "Автоматические повторы остановлены" : "Ожидает повторной отправки";
    case UploadQueueStatus::needsAuth: return "Не удалось подтвердить аккаунт для отправки";
    case UploadQueueStatus::uploaded: return "Отправлено";
    case UploadQueueStatus::quarantined: return "Требует проверки · не отправлена";
    case UploadQueueStatus::blocked: return DesktopUploadQueueService::isPermanentUploadReason(item.safeReason)
        ? "Сервер отклонил запись без возможности повторной отправки"
        : item.safeReason == "needs_admin" ? "Ожидает действия администратора рабочего пространства"
        : "Отправка невозможна без исправления на этом компьютере";
    }
    return "Требует проверки";
}

CustodyString WebView2Host::protectedLocalRecordingsMessage() const {
    // One charged output and one retained immutable value; no ordinary inventory
    // DTO, package inspection or filesystem access on the presentation thread.
    const auto value = protectedLocalValue_;
    const auto timings = protectedLocalTimings_;
    const bool current = localPlaybackDocumentCurrent(documentGeneration_, documentNonce_);
    CustodyString json;
    const auto append = [&](std::string_view text) {
        json.append(text.data(), text.size());
    };
    const auto quote = [&](std::string_view text) {
        append("\"");
        for (const unsigned char c : text) {
            if (c == '"' || c == '\\') { append("\\"); const char byte = static_cast<char>(c); append({&byte, 1}); }
            else if (c < 32) {
                constexpr char hex[] = "0123456789abcdef";
                const char escaped[]{'\\','u','0','0',hex[c >> 4],hex[c & 15]}; append({escaped, 6});
            } else { const char byte = static_cast<char>(c); append({&byte, 1}); }
        }
        append("\"");
    };
    const auto field = [&](std::string_view name, std::string_view text) { append(name); quote(text); };
    const auto number = [&](std::string_view name, std::uint64_t value) {
        char digits[32];
        const auto encoded = std::to_chars(std::begin(digits), std::end(digits), value);
        if (encoded.ec != std::errc{}) throw std::runtime_error("local_inventory_number");
        append(name); append({digits, static_cast<std::size_t>(encoded.ptr - digits)});
    };
    field("{\"command\":", "local_recordings"); field(",\"nonce\":", documentNonce_);
    field(",\"state\":", !current ? "checking" : !value ? "unavailable" : protectedLocalComplete_ ? "ready" : "checking");
    append(",\"rows\":[");
    bool first = true, recovery = false;
    if (current && value) for (std::size_t index = 0; index != value->items().size(); ++index) {
        const auto& item = value->items()[index];
        if (item.ownerUserId.empty() || item.ownerWorkspaceId.empty()) { recovery = true; continue; }
        if (std::string_view(item.ownerUserId) != localAccount_.user || std::string_view(item.ownerWorkspaceId) != localAccount_.workspace) continue;
        if (!first) append(",");
        first = false;
        field("{\"id\":", item.localRecordingId); field(",\"title\":", "Запись");
        field(",\"status\":", localRecordingStatus(item));
        if (timings && timings->rows[index]) {
            const auto& timing = *timings->rows[index];
            const auto startedAt = DesktopApiClient::formatUtcInstant<CustodyString>(timing.startedAtMs);
            if (!startedAt.empty()) {
                field(",\"startedAt\":", startedAt);
                field(",\"generatedTitlePrefix\":", "Запись ");
            }
            std::optional<std::uint64_t> sessionSeconds;
            if (timing.durationMs > 0) {
                sessionSeconds = timing.durationMs / 1000;
                number(",\"durationSeconds\":", *sessionSeconds);
            }
            if (!startedAt.empty() && timing.stoppedAtMs > timing.startedAtMs) {
                const auto elapsed = timing.stoppedAtMs - timing.startedAtMs;
                sessionSeconds = std::max(sessionSeconds.value_or(0), elapsed / 1000 + (elapsed % 1000 != 0));
            }
            if (sessionSeconds) number(",\"sessionDurationSeconds\":", *sessionSeconds);
        }
        append(",\"canOpen\":"); append(current && protectedLocalOpenAllowed(item) ? "true" : "false");
        append(",\"canSend\":"); append(protectedLocalComplete_ &&
            value->canManualSend(index, localAccount_.user, localAccount_.workspace, false) ? "true" : "false");
        append(",\"canDelete\":"); append(protectedLocalComplete_ &&
            value->canLocalRemoval(index, localAccount_.user, localAccount_.workspace) ? "true" : "false");
        append(",\"showsPartialDuration\":false,\"uploadComplete\":");
        append(item.status == UploadQueueStatus::uploaded ? "true" : "false");
        append(",\"localDeletionPending\":"); append(item.safeReason == "local_delete_pending" ? "true" : "false");
        append(",\"deletionIsLocalOnly\":");
        append(item.meetingId.empty() && item.attempts == 0 && item.status != UploadQueueStatus::uploaded ? "true" : "false");
        if (!item.meetingId.empty()) field(",\"meetingId\":", item.meetingId);
        append("}");
    }
    append("],\"operations\":["); first = true;
    if (current && value) for (const auto& operation : value->deletionOperations()) {
        if (std::string_view(operation.actorUserId) != localAccount_.user || std::string_view(operation.workspaceId) != localAccount_.workspace ||
            std::string_view(operation.serverOrigin) != localAccount_.origin) continue;
        if (!first) append(",");
        first = false;
        constexpr std::string_view phases[]{"queued", "sending", "resolving", "accepted", "rejected", "verified"};
        field("{\"id\":", operation.operationId);
        if (static_cast<unsigned>(operation.phase) >= std::size(phases)) throw std::invalid_argument("local_inventory_phase");
        field(",\"phase\":", phases[static_cast<unsigned>(operation.phase)]);
        field(",\"waitReason\":", pageDeletionWaitReason(operation.safeReason));
        append(operation.target == DeletionTarget::meeting ? ",\"target\":{\"meeting\":{\"_0\":" : ",\"target\":{\"ownOrigin\":{\"_0\":");
        quote(operation.targetId); append("}}");
        if (operation.target == DeletionTarget::meeting && deletionPhaseIsAccepted(operation.phase)) {
            field(",\"receipt\":{\"meeting_id\":", operation.targetId); append("}");
        }
        append("}");
    }
    append("],\"recoveryRequired\":"); append(recovery ? "true}" : "false}");
    return json;
}

void WebView2Host::applyLocalPackageTiming(WebViewLocalRecordingRow& row, std::uint64_t startedAtMs,
                                           std::uint64_t stoppedAtMs, bool captureInterrupted) {
    row.startedAt = DesktopApiClient::formatUtcInstant(startedAtMs);
    row.generatedTitlePrefix.clear();
    // The cabinet formats the date itself, so it receives a prefix and the
    // instant rather than a date this machine already rendered. A recording with
    // no readable start keeps the plain title instead of an empty date.
    if (!row.startedAt.empty()) row.generatedTitlePrefix = "Запись ";
    row.sessionDurationSeconds = row.durationSeconds;
    if (!row.startedAt.empty() && stoppedAtMs > startedAtMs) {
        const auto sessionMs = stoppedAtMs - startedAtMs;
        const auto sessionSeconds = sessionMs / 1000 + (sessionMs % 1000 != 0);
        row.sessionDurationSeconds = std::max(row.durationSeconds.value_or(0), sessionSeconds);
    }
    // "Saved X of Y" is a claim about a fault: it is true only for an
    // interrupted recording whose confirmed prefix survived, is playable, and is
    // shorter than the session it came from.
    row.showsPartialDuration = captureInterrupted && row.canOpen &&
        row.durationSeconds.has_value() && row.sessionDurationSeconds.has_value() &&
        *row.durationSeconds < *row.sessionDurationSeconds;
}

bool WebView2Host::localPlaybackDocumentCurrent(std::uint64_t generation, std::string_view nonce) const noexcept try {
    return protectedLocalMode_ && generation != 0 && generation == documentGeneration_ &&
        !nonce.empty() && nonce == documentNonce_ && localDocumentIdentity_ && userTimeDocumentCurrent() &&
        localAccount_.origin == userTimeAccount_.origin && localAccount_.user == userTimeAccount_.user &&
        localAccount_.workspace == userTimeAccount_.workspace &&
        localAccount_.authGeneration == userTimeAccount_.authGeneration;
} catch (...) { return false; }

bool WebView2Host::protectedLocalOpenAllowed(const ProtectedUploadQueueValue::Item& item) const noexcept {
    if (!protectedLocalComplete_ || !protectedLocalValue_ || item.localRecordingId.empty() ||
        item.localRecordingId.size() > 300 || item.ownerUserId.empty() || item.ownerWorkspaceId.empty() ||
        std::string_view(item.ownerUserId) != localAccount_.user || std::string_view(item.ownerWorkspaceId) != localAccount_.workspace ||
        !item.meetingId.empty() || item.status == UploadQueueStatus::quarantined || item.safeReason == "local_delete_pending") return false;
    const auto& operations = protectedLocalValue_->deletionOperations();
    return std::none_of(operations.begin(), operations.end(), [&](const auto& operation) {
        return operation.phase != DeletionOperationPhase::rejected && operation.targetId == item.localRecordingId;
    });
}

bool WebView2Host::localRecordingActionAllowed(std::string_view action, std::string_view id) const noexcept {
    if (runtimeState_ != WebRuntimeState::ready || id.empty() || id.size() > 300) return false;
    if (protectedLocalMode_) {
        if (!protectedLocalValue_ || !localPlaybackDocumentCurrent(documentGeneration_, documentNonce_)) return false;
        const auto& rows = protectedLocalValue_->items();
        const auto row = std::find_if(rows.begin(), rows.end(), [id](const auto& item) { return std::string_view(item.localRecordingId) == id; });
        return row != rows.end() && ((action == "open" && protectedLocalOpenAllowed(*row)) ||
            (action == "delete" && protectedLocalComplete_ && protectedLocalValue_->canLocalRemoval(
                static_cast<std::size_t>(row - rows.begin()), localAccount_.user, localAccount_.workspace)) ||
            (action == "send" && protectedLocalComplete_ && protectedLocalValue_->canManualSend(
                static_cast<std::size_t>(row - rows.begin()), localAccount_.user, localAccount_.workspace, false)));
    }
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
    completeDeletionSelection(request.documentGeneration, request.selection.requestId, outcome);
}
bool WebView2Host::completeDeletionSelection(std::uint64_t documentGeneration, std::string_view requestId,
                                            const CabinetDeletionOutcome& outcome) {
    // A page that has since been replaced is not waiting for this answer.
    if (documentGeneration == 0 || documentGeneration != documentGeneration_) return true;
    if (!nativeRunScript_ || runtimeState_ != WebRuntimeState::ready) return false;
    const auto script = RecordingDeletionBridge::completionScript<CustodyString>(requestId, outcome);
    if (script.empty()) return true; // Invalid request ID cannot be delivered as script.
    nativeRunScript_(script);
    return true;
}

void WebView2Host::setCalendarJoinHandlers(CalendarJoinHandler join, CalendarJoinHandler cancel) {
    bridge_.setCalendarJoinEnabled(false);
    cancelPendingCalendarJoin();
    try { if (nativeRunScript_) nativeRunScript_("window.__grafSetCalendarJoinAvailable?.(false)"); } catch (...) {}
    calendarJoinHandler_ = std::move(join);
    calendarCancelHandler_ = std::move(cancel);
    bridge_.setCalendarJoinEnabled(calendarJoinHandler_ && calendarCancelHandler_);
    publishCalendarJoinAvailability();
}

void WebView2Host::publishCalendarJoinAvailability() {
    try { if (nativeRunScript_)
        nativeRunScript_(bridge_.isAllowedWebCommand("calendar_join") && calendarJoinHandler_ && calendarCancelHandler_ &&
            policy_.evaluate(currentUrl_).kind == RouteKind::meetings
            ? "window.__grafSetCalendarJoinAvailable?.(true)" : "window.__grafSetCalendarJoinAvailable?.(false)");
    } catch (...) {
        bridge_.setCalendarJoinEnabled(false);
        cancelPendingCalendarJoin();
    }
}

bool WebView2Host::calendarDocumentCurrent(const CalendarJoinRequest& request) const {
    return alive_ && alive_->load() && runtimeState_ == WebRuntimeState::ready && documentGeneration_ != 0 &&
        request.documentGeneration == documentGeneration_ && !request.nonce.empty() &&
        request.nonce == documentNonce_ && currentUrl_ == committedDocumentUrl_ &&
        policy_.allowsNativeBridge(currentUrl_) && policy_.evaluate(currentUrl_).kind == RouteKind::meetings;
}

void WebView2Host::emitCalendarJoinReply(const CalendarJoinRequest& request, CalendarJoinResult result) {
    if (nativeReplyCalendarJoin_ && calendarDocumentCurrent(request)) {
        const auto reply = nativeReplyCalendarJoin_;
        reply(request, result);
    }
}

void WebView2Host::replyCalendarJoin(const CalendarJoinRequest& request, CalendarJoinResult result) {
    if (!calendarRequestPending(request) || !calendarDocumentCurrent(request)) return;
    const bool terminal = result.state == CalendarJoinState::handedOff ||
        result.state == CalendarJoinState::failed || result.state == CalendarJoinState::cancelled;
    if ((!terminal && (result.state != CalendarJoinState::opening || calendarJoinState_ != CalendarJoinState::resolving)) ||
        (result.state == CalendarJoinState::handedOff && calendarJoinState_ != CalendarJoinState::opening) ||
        ((result.state == CalendarJoinState::opening || result.state == CalendarJoinState::handedOff) &&
            result.reason != CalendarJoinReason::none)) return;
    calendarJoinState_ = result.state;
    if (terminal) pendingCalendarJoin_.reset(); // Before any reentrant delivery.
    emitCalendarJoinReply(request, result);
}

bool WebView2Host::calendarRequestPending(const CalendarJoinRequest& request) const noexcept {
    return pendingCalendarJoin_ && request.documentGeneration == pendingCalendarJoin_->documentGeneration &&
        request.nonce == pendingCalendarJoin_->nonce && request.intent.eventId == pendingCalendarJoin_->intent.eventId &&
        request.intent.requestId == pendingCalendarJoin_->intent.requestId;
}

void WebView2Host::cancelPendingCalendarJoin() noexcept {
    if (calendarInvalidating_) return;
    calendarInvalidating_ = true;
    const auto request = std::exchange(pendingCalendarJoin_, std::nullopt);
    if (request) {
        calendarJoinState_ = CalendarJoinState::cancelled;
        try {
            const auto cancel = calendarCancelHandler_;
            if (cancel) cancel(*request);
        } catch (...) {} // Still deliver the terminal to its original document.
        try { emitCalendarJoinReply(*request, {CalendarJoinState::cancelled, CalendarJoinReason::cancelled}); }
        catch (...) {}
    }
    calendarInvalidating_ = false;
}

void WebView2Host::revokeCalendarDocument() noexcept {
    cancelPendingCalendarJoin();
    try { if (nativeRunScript_) nativeRunScript_("window.__grafSetCalendarJoinAvailable?.(false)"); } catch (...) {}
    calendarRequestIds_.clear();
}

void WebView2Host::handleCalendarJoinMessage(const WebViewBridgeEnvelope& message, std::string_view sourceUrl) {
    if (message.command != "calendar_join" && message.command != "calendar_join_cancel") return;
    const CalendarJoinRequest document{{}, documentGeneration_, documentNonce_};
    if (sourceUrl != currentUrl_ || !calendarDocumentCurrent(document) ||
        bridge_.validate(message) != BridgeValidationError::none) return;
    const auto intent = DesktopApiClient::decodeCalendarJoinIntent(message.payloadJson, message.command);
    if (!intent) return;
    if (message.command == "calendar_join_cancel") {
        if (pendingCalendarJoin_ && pendingCalendarJoin_->intent.eventId == intent->eventId &&
            pendingCalendarJoin_->intent.requestId == intent->requestId) cancelPendingCalendarJoin();
        return;
    }
    if (calendarRequestIds_.count(intent->requestId)) return;
    const CalendarJoinRequest request{*intent, documentGeneration_, documentNonce_};
    if (calendarRequestIds_.size() == 1024) {
        emitCalendarJoinReply(request, {CalendarJoinState::cancelled, CalendarJoinReason::notReady});
        return;
    }
    calendarRequestIds_.insert(intent->requestId);
    if (calendarInvalidating_ || !calendarJoinHandler_ || !calendarCancelHandler_) {
        emitCalendarJoinReply(request, {CalendarJoinState::cancelled, CalendarJoinReason::notReady});
    } else if (pendingCalendarJoin_) {
        emitCalendarJoinReply(request, {CalendarJoinState::cancelled, CalendarJoinReason::busy});
    } else {
        pendingCalendarJoin_ = request;
        calendarJoinState_ = CalendarJoinState::resolving;
        try {
            emitCalendarJoinReply(request, {CalendarJoinState::resolving, CalendarJoinReason::none});
            // Delivery can synchronously navigate/cancel. Do not dispatch its old intent.
            if (!calendarRequestPending(request) || !calendarDocumentCurrent(request)) return;
            const auto join = calendarJoinHandler_;
            if (join) join(request);
        } catch (...) {
            if (calendarRequestPending(request)) cancelPendingCalendarJoin();
        }
    }
}

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
void WebView2Host::openPaymentPopup(winrt::Microsoft::UI::Xaml::Controls::WebView2 opener,
    winrt::Microsoft::Web::WebView2::Core::CoreWebView2NewWindowRequestedEventArgs args) {
    using namespace winrt::Microsoft::UI::Xaml;
    using namespace winrt::Microsoft::UI::Xaml::Controls;
    using namespace winrt::Microsoft::Web::WebView2::Core;
    const auto alive = alive_;
    const auto dispatcher = opener.DispatcherQueue();
    const auto window = std::make_shared<PaymentPopupWindow>();
    window->dispatcher = dispatcher;
    try {
        const auto core = opener.CoreWebView2();
        const auto openerUrl = utf8(core.Source());
        const auto source = paymentPopupSource(core, args, documentGeneration_);
        window->panel = opener.Parent().try_as<Panel>();
        if (!window->panel || (!paymentPopup_ && utf8(core.Source()) != committedDocumentUrl_) ||
            !beginPaymentPopup(utf8(args.Uri()), source, monotonicMilliseconds(), [window] { window->close(); })) return;
        window->generation = source.documentGeneration;
        window->childOrdinal = paymentPopup_->children;
        window->opener = opener;
        window->deferral = args.GetDeferral();
        const auto environment = core.Environment();
        const auto profile = core.Profile();
        const auto options = environment.CreateCoreWebView2ControllerOptions();
        options.ProfileName(profile.ProfileName());
        options.IsInPrivateModeEnabled(profile.IsInPrivateModeEnabled());
        window->child = WebView2();
        const auto child = window->child;
        child.HorizontalAlignment(opener.HorizontalAlignment());
        child.VerticalAlignment(opener.VerticalAlignment());
        child.Margin(opener.Margin());
        Grid::SetRow(child, Grid::GetRow(opener));
        Grid::SetColumn(child, Grid::GetColumn(opener));
        Grid::SetRowSpan(child, Grid::GetRowSpan(opener));
        Grid::SetColumnSpan(child, Grid::GetColumnSpan(opener));
        Automation::AutomationProperties::SetName(child, L"Оплата GRAF");
        window->panel.Children().Append(child);
        const std::weak_ptr<PaymentPopupWindow> weak = window;
        window->timer = dispatcher.CreateTimer();
        window->timer.Interval(std::chrono::milliseconds(100));
        window->timer.Tick([this, alive, weak](auto const& timer, auto const&) {
            const auto window = weak.lock();
            if (!window || window->closed || !alive->load()) { timer.Stop(); return; }
            if (window->cancellationRequested.load()) { fail("payment-dispatch", E_ABORT); return; }
            const auto now = monotonicMilliseconds();
            if (!paymentPopupLiveAt(now)) { fail("payment-expired", E_ABORT); return; }
            if (window->interruptedNavigationId != 0 &&
                paymentPopupChildCurrent(window->generation, window->childOrdinal, now) &&
                (now < window->interruptedAt || now - window->interruptedAt >= PaymentPopupWindow::replacementWindowMs))
                fail("payment-document", E_FAIL);
        });
        window->timer.Start();
        // Bind creation to the opener's captured native environment and profile.
        // Environment() may return distinct WinRT wrappers for the same environment;
        // wrapper reference equality is not an environment identity check.
        child.EnsureCoreWebView2Async(environment, options).Completed(
            [this, alive, dispatcher, opener, core, args, window, source, openerUrl](auto const& operation, auto const&) {
                if (!dispatcher.TryEnqueue([this, alive, dispatcher, opener, core, args, window, source, openerUrl, operation] {
                    if (!alive->load() || window->closed) { window->close(); return; }
                    if (source.documentGeneration != documentGeneration_ || !paymentPopup_ ||
                        window->childOrdinal != paymentPopup_->children) { window->close(); return; }
                    try {
                        operation.GetResults();
                        const auto child = window->child;
                        const auto target = child.CoreWebView2();
                        const auto settings = target.Settings();
                        settings.AreHostObjectsAllowed(false);
                        settings.IsWebMessageEnabled(false);
                        settings.AreDefaultScriptDialogsEnabled(false);
                        settings.IsStatusBarEnabled(false);
                        const std::weak_ptr<PaymentPopupWindow> weak = window;
                        target.NavigationStarting([this, alive, weak](auto const& sender, auto const& event) {
                            const auto window = weak.lock();
                            if (!window || window->closed || !window->ready || !alive->load()) { event.Cancel(true); return; }
                            try {
                                if (!paymentPopupChildCurrent(window->generation, window->childOrdinal, monotonicMilliseconds())) {
                                    event.Cancel(true);
                                    return; // A replaced child cannot affect its successor.
                                }
                                const auto now = monotonicMilliseconds();
                                if (window->interruptedNavigationId != 0 &&
                                    (now < window->interruptedAt || now - window->interruptedAt >= PaymentPopupWindow::replacementWindowMs)) {
                                    event.Cancel(true);
                                    fail("payment-document", E_FAIL);
                                    return;
                                }
                                // This is the owned Core's main-navigation event, not a
                                // frame URL guess. FrameId may remain zero until ContentLoading.
                                if (paymentPopup_->activeFrameId != 0 && sender.FrameId() != paymentPopup_->activeFrameId) {
                                    event.Cancel(true);
                                    fail("payment-opener-navigation", E_ABORT);
                                    return;
                                }
                                const auto url = utf8(event.Uri());
                                if (evaluatePaymentPopupDocument(url, monotonicMilliseconds()).decision != RouteDecision::allow) {
                                    event.Cancel(true);
                                    fail("payment-route", E_ACCESSDENIED);
                                    return;
                                }
                                window->navigationId = event.NavigationId();
                                window->navigationUrl = url;
                                if (window->navigationId != window->interruptedNavigationId)
                                    window->interruptedNavigationId = 0;
                            } catch (...) { event.Cancel(true); fail("payment-navigation", E_FAIL); }
                        });
                        target.ContentLoading([this, alive, weak](auto const& sender, auto const& event) {
                            const auto window = weak.lock();
                            if (!alive->load() || !window || window->closed || !window->ready ||
                                window->navigationId == 0 || event.NavigationId() != window->navigationId ||
                                !paymentPopupChildCurrent(window->generation, window->childOrdinal, monotonicMilliseconds())) return;
                            try {
                                if (!bindPaymentPopupFrame(sender.FrameId(), window->generation, window->childOrdinal,
                                    monotonicMilliseconds())) fail("payment-frame", E_ABORT);
                            } catch (...) { fail("payment-frame", E_FAIL); }
                        });
                        target.FrameNavigationStarting([this, alive, weak](auto const&, auto const& event) {
                            const auto window = weak.lock();
                            if (!window || window->closed || !alive->load()) { event.Cancel(true); return; }
                            try {
                                if (!paymentPopupLiveAt(monotonicMilliseconds()) ||
                                    policy_.evaluate(utf8(event.Uri()), false, AuthContinuation::none,
                                        payment_.live(monotonicMilliseconds())).decision != RouteDecision::allow) event.Cancel(true);
                            } catch (...) { event.Cancel(true); }
                        });
                        target.PermissionRequested([](auto const&, auto const& event) {
                            event.State(CoreWebView2PermissionState::Deny);
                            event.Handled(true);
                        });
                        target.DownloadStarting([](auto const&, auto const& event) { event.Cancel(true); event.Handled(true); });
                        target.NewWindowRequested([this, alive, weak](auto const&, auto const& event) {
                            event.Handled(true);
                            const auto window = weak.lock();
                            if (!alive->load() || !window || window->closed) return;
                            openPaymentPopup(window->child, event);
                        });
                        target.ProcessFailed([this, alive, weak](auto const&, auto const&) {
                            const auto window = weak.lock();
                            if (alive->load() && window && !window->closed) fail("payment-process", E_FAIL);
                        });
                        target.WindowCloseRequested([this, alive, weak, dispatcher](auto const&, auto const&) {
                            const auto window = weak.lock();
                            if (!alive->load() || !window || window->closed) return;
                            dispatcher.TryEnqueue([this, alive, weak] {
                                const auto window = weak.lock();
                                if (!alive->load() || !window || window->closed) return;
                                cancelPaymentPopup();
                                (void)navigate(policy_.trustedOrigin() + "/billing");
                            });
                        });
                        target.NavigationCompleted([this, alive, weak, dispatcher](auto const& sender, auto const& event) {
                            const auto window = weak.lock();
                            if (!alive->load() || !window || window->closed || event.NavigationId() != window->navigationId) return;
                            try {
                                if (!paymentPopupChildCurrent(window->generation, window->childOrdinal, monotonicMilliseconds())) return;
                                // A failed first navigation may never emit ContentLoading,
                                // so it must not wait for a frame ID to expose recovery.
                                if (!event.IsSuccess()) {
                                    // An immediate form can replace the initial popup load.
                                    // Wait only for a bounded, policy-validated new navigation;
                                    // a genuine aborted connection still exposes recovery.
                                    if (event.WebErrorStatus() == CoreWebView2WebErrorStatus::ConnectionAborted &&
                                        paymentPopup_->activeFrameId == 0) {
                                        if (window->interruptedNavigationId == 0) {
                                            window->interruptedNavigationId = event.NavigationId();
                                            window->interruptedAt = monotonicMilliseconds();
                                        }
                                    } else fail("payment-document", E_FAIL);
                                    return;
                                }
                                if (paymentPopup_->activeFrameId == 0 || sender.FrameId() != paymentPopup_->activeFrameId) return;
                                const auto url = utf8(sender.Source());
                                if (url != window->navigationUrl) { fail("payment-document", E_FAIL); return; }
                                // The original request (including a return POST) has completed.
                                // Only now restore a fresh privileged GET, never replay an action.
                                if (!policy_.sharesOrigin(url)) return;
                                if (!paymentPopup_ || !paymentPopup_->returning) return;
                                auto safe = policy_.safeRecoveryUrl(url);
                                if (safe.empty()) safe = policy_.trustedOrigin() + "/billing";
                                const auto completedNavigationId = event.NavigationId();
                                const auto completedFrameId = sender.FrameId();
                                dispatcher.TryEnqueue([this, alive, weak, safe, completedNavigationId, completedFrameId] {
                                    const auto window = weak.lock();
                                    if (!alive->load() || !window || window->closed || !paymentPopupLiveAt(monotonicMilliseconds())) return;
                                    if (window->navigationId != completedNavigationId ||
                                        paymentPopup_->activeFrameId != completedFrameId || !paymentPopup_->returning) return;
                                    cancelPaymentPopup();
                                    (void)navigate(safe);
                                });
                            } catch (...) { fail("payment-document", E_FAIL); }
                        });
                        // Re-read native frame identity after asynchronous controller creation.
                        const auto proof = paymentPopupSource(core, args, documentGeneration_);
                        if (utf8(core.Source()) != openerUrl ||
                            target.Profile().ProfileName() != core.Profile().ProfileName() ||
                            target.Profile().IsInPrivateModeEnabled() != core.Profile().IsInPrivateModeEnabled() ||
                            !handOffPaymentPopup(proof, monotonicMilliseconds())) { fail("payment-popup-binding", E_ABORT); return; }
                        // NewWindow also enforces native environment/profile compatibility.
                        args.NewWindow(target); // Browser owns method/body/name/opener; never Navigate(Uri).
                        if (popupHandoffCheckpoint_) popupHandoffCheckpoint_(false, target);
                        // WebView2 replaces the contents on NewWindow assignment. Resource
                        // filters must apply to those contents, before completing the deferral.
                        target.AddWebResourceRequestedFilter(L"*", CoreWebView2WebResourceContext::Document,
                            CoreWebView2WebResourceRequestSourceKinds::Document);
                        const auto deniedDocument = core.Environment().CreateWebResourceResponse(nullptr, 403,
                            L"Forbidden", L"Content-Length: 0\r\nCache-Control: no-store\r\n");
                        target.WebResourceRequested([this, alive, weak, deniedDocument](auto const&, auto const& event) {
                            const auto window = weak.lock();
                            try {
                                if (alive->load() && window && !window->closed) {
                                    const auto now = monotonicMilliseconds();
                                    const auto request = event.Request();
                                    const auto url = utf8(request.Uri());
                                    if (paymentPopupChildCurrent(window->generation, window->childOrdinal, now) &&
                                        policy_.evaluate(url, false, AuthContinuation::none, payment_.live(now)).decision == RouteDecision::allow) {
                                        if (policy_.sharesOrigin(url)) request.Headers().SetHeader(L"X-GRAF-Client", L"desktop");
                                        return; // Preserve the browser's original request, including POST.
                                    }
                                }
                            } catch (...) {}
                            // NavigationStarting.Cancel may arrive after a GET was sent.
                            // Supply a local response at the request boundary instead.
                            try { event.Response(deniedDocument); }
                            catch (...) {
                                if (alive->load() && window && !window->closed && paymentPopup_ &&
                                    window->generation == documentGeneration_ && window->childOrdinal == paymentPopup_->children)
                                    fail("payment-request", E_FAIL);
                            }
                        });
                        opener.Visibility(Visibility::Collapsed);
                        window->ready = true;
                        window->complete();
                        if (popupHandoffCheckpoint_) popupHandoffCheckpoint_(true, target);
                    } catch (const winrt::hresult_error& error) { fail("payment-popup", error.code().value); window->close(); }
                    catch (...) { fail("payment-popup", E_FAIL); window->close(); }
                })) window->cancellationRequested.store(true);
            });
    } catch (const winrt::hresult_error& error) { fail("payment-popup", error.code().value); window->close(); }
    catch (...) { fail("payment-popup", E_FAIL); window->close(); }
}

void WebView2Host::attach(winrt::Microsoft::UI::Xaml::Controls::WebView2 control,
    winrt::Microsoft::Web::WebView2::Core::CoreWebView2Environment suppliedEnvironment) {
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
            if (!control.CoreWebView2() || runtimeState_ != WebRuntimeState::ready ||
                !policy_.allowsNativeBridge(utf8(control.CoreWebView2().Source()))) return;
            const auto generation = documentGeneration_;
            const auto expected = std::string(token);
            control.CoreWebView2().CookieManager().GetCookiesAsync(
                winrt::to_hstring(policy_.trustedOrigin())).Completed(
                [this, alive, dispatcher, control, generation, expected, unixSeconds](auto const& operation, auto const&) {
                    dispatcher.TryEnqueue([this, alive, control, generation, expected, unixSeconds, operation] {
                        if (!alive->load() || generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready ||
                            !policy_.allowsNativeBridge(utf8(control.CoreWebView2().Source()))) return;
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
            const auto evaluation = beginDocumentNavigation(url, args.NavigationId(), args.IsRedirected(),
                monotonicMilliseconds(), ""); // Browser method is not exposed by NavigationStarting.
            if (evaluation.decision == RouteDecision::openExternal) {
                args.Cancel(true);
                if (args.IsUserInitiated() && !args.IsRedirected() && runtimeState_ != WebRuntimeState::unavailable)
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
            const auto responseTimer = dispatcher.CreateTimer();
            responseTimer.Interval(std::chrono::milliseconds(100));
            responseTimer.IsRepeating(true);
            nativeStopResponseTimer_ = [responseTimer] { responseTimer.Stop(); };
            responseTimer.Tick([this, alive](auto const& timer, auto const&) {
                if (!alive->load()) { timer.Stop(); return; }
                const auto finish = nativeFinishDocument_;
                if (finish) finish();
                else timer.Stop();
            });
            nativeNavigate_ = [core](std::string_view url) { core.Navigate(winrt::to_hstring(url)); };
            nativeReload_ = [this, core] {
                // A failed first navigation may leave about:blank as Source.
                // Retry the approved requested route without deleting user data.
                core.Navigate(winrt::to_hstring(requestedDocumentUrl_.empty() ? recoveryUrl() : requestedDocumentUrl_));
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
                    const auto route = policy_.evaluate(source, true, activeAuthContinuation(), payment_.live(monotonicMilliseconds()));
                    if (route.decision != RouteDecision::allow || route.kind == RouteKind::artifactDownload ||
                        route.kind == RouteKind::nativeSettings) {
                        currentUrl_.clear();
                        if (!args.IsNewDocument()) fail("source", E_ACCESSDENIED);
                        return;
                    }
                    currentUrl_ = source;
                    // replaceState/hash changes do not replace the document.
                    // Keep its generation, nonce and replay counter intact.
                    if (!args.IsNewDocument() && runtimeState_ == WebRuntimeState::ready) {
                        if (!policy_.allowsNativeBridge(source)) { fail("source-authority", E_ACCESSDENIED); return; }
                        // A history mutation must not turn a POST into a retryable GET.
                        if (const auto safe = policy_.safeRecoveryUrl(source, navigationMethod_); !safe.empty()) {
                            safeRecoveryUrl_ = safe;
                        }
                    }
                } catch (...) { fail("source", E_FAIL); }
            });
            core.AddWebResourceRequestedFilter(winrt::to_hstring(policy_.trustedOrigin() + "/*"),
                winrt::Microsoft::Web::WebView2::Core::CoreWebView2WebResourceContext::Document);
            core.WebResourceRequested([this, alive](auto const&, auto const& args) {
                if (!alive->load()) return;
                try {
                    const auto request = args.Request();
                    const auto url = utf8(request.Uri());
                    if (!policy_.sharesOrigin(url)) return;
                    if (policy_.evaluate(url).decision == RouteDecision::allow)
                        request.Headers().SetHeader(L"X-GRAF-Client", L"desktop");
                    request.Headers().RemoveHeader(L"X-GRAF-Desktop-Navigation");
                    // Browser headers may be added after this event. Tag the
                    // own-origin Document request now; reject frames using the
                    // final browser-owned destination in ResponseReceived.
                    const auto tag = documentRequestTag(url);
                    if (!tag.empty()) request.Headers().SetHeader(L"X-GRAF-Desktop-Navigation", winrt::to_hstring(tag));
                } catch (...) { fail("request-metadata", E_FAIL); }
            });
            core.WebResourceResponseReceived([this, alive](auto const&, auto const& args) {
                if (!alive->load()) return;
                try {
                    const auto request = args.Request();
                    const auto headers = request.Headers();
                    if (!headers.Contains(L"Sec-Fetch-Dest") ||
                        !headers.Contains(L"X-GRAF-Desktop-Navigation")) return;
                    const auto tag = utf8(headers.GetHeader(L"X-GRAF-Desktop-Navigation"));
                    const auto response = args.Response();
                    const auto responseHeaders = response.Headers();
                    WebDocumentResponse metadata;
                    metadata.status = response.StatusCode();
                    if (responseHeaders.Contains(L"Content-Type")) metadata.contentType = utf8(responseHeaders.GetHeader(L"Content-Type"));
                    if (responseHeaders.Contains(L"X-GRAF-Cabinet-Recovery"))
                        metadata.recoveryHeader = utf8(responseHeaders.GetHeader(L"X-GRAF-Cabinet-Recovery"));
                    if (observeDocumentResponseHeaders(utf8(request.Uri()), tag,
                        utf8(headers.GetHeader(L"Sec-Fetch-Dest")), utf8(request.Method()), metadata)) {
                        const auto finish = nativeFinishDocument_;
                        if (finish) finish();
                    }
                } catch (...) {
                    // Missing correlated metadata never grants document authority.
                }
            });
            core.ScriptDialogOpening([this, alive, dispatcher, control](auto const& core, auto const& args) {
                using namespace winrt::Microsoft::UI::Xaml::Controls;
                using Kind = winrt::Microsoft::Web::WebView2::Core::CoreWebView2ScriptDialogKind;
                if (!alive->load() || nativeCancelDialog_ || utf8(args.Uri()) != utf8(core.Source()) ||
                    utf8(core.Source()) != currentUrl_ ||
                    !policy_.allowsNativeBridge(currentUrl_) ||
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
                    if (policy_.evaluate(utf8(args.Uri()), false, AuthContinuation::none,
                        payment_.live(monotonicMilliseconds())).decision != RouteDecision::allow) args.Cancel(true);
                } catch (...) { args.Cancel(true); }
            });
            core.NewWindowRequested([this, alive, control](auto const& core, auto const& args) {
                args.Handled(true);
                if (!alive->load()) return;
                const auto url = utf8(args.Uri());
                if (payment_.started() || policy_.evaluate(committedDocumentUrl_).kind == RouteKind::billing) {
                    openPaymentPopup(control, args);
                    return;
                }
                // URI-only fallback for contexts outside the payment adapter.
                // Its evaluator explicitly denies payment requests: Navigate(Uri)
                // cannot preserve their method/body or browser opener semantics.
                const auto evaluation = evaluatePopupNavigation(url, monotonicMilliseconds());
                if (evaluation.decision == RouteDecision::allow) {
                    // Only non-payment routes admitted by the URI-only policy;
                    // NavigationStarting rechecks them. No generic new windows.
                    core.Navigate(args.Uri());
                } else if (evaluation.decision == RouteDecision::openExternal && args.IsUserInitiated()) {
                    (void)::ShellExecuteW(nullptr, L"open", winrt::to_hstring(evaluation.normalizedUrl).c_str(), nullptr, nullptr, SW_SHOWNORMAL);
                }
            });
            core.ProcessFailed([this, alive](auto const&, auto const& args) {
                if (!alive->load()) return;
                using Kind = winrt::Microsoft::Web::WebView2::Core::CoreWebView2ProcessFailedKind;
                const auto kind = args.ProcessFailedKind();
                std::int32_t exitCode = E_FAIL;
                try { exitCode = args.ExitCode(); } catch (...) {}
                // Numeric metadata only: never log descriptions, frames or URLs.
                char event[96]{};
                std::snprintf(event, sizeof(event), "process-failed kind=%d exit=0x%08X",
                    static_cast<int>(kind), static_cast<unsigned>(exitCode));
                logBridgeEvent(event);
                auto failure = WebProcessFailure::automaticallyRecoverable;
                switch (kind) {
                case Kind::BrowserProcessExited: failure = WebProcessFailure::browserExited; break;
                case Kind::RenderProcessExited: failure = WebProcessFailure::renderExited; break;
                case Kind::RenderProcessUnresponsive: failure = WebProcessFailure::renderUnresponsive; break;
                case Kind::FrameRenderProcessExited: failure = WebProcessFailure::frameRenderExited; break;
                default: break; // GPU, utility and other auxiliary processes recover themselves.
                }
                handleProcessFailure(failure, exitCode);
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
                        !policy_.allowsNativeBridge(sourceUrl)) {
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
                    if (message->command == "calendar_join" || message->command == "calendar_join_cancel") {
                        handleCalendarJoinMessage(*message, sourceUrl);
                        return;
                    }
                    const auto validation = bridge_.validate(*message);
                    if (validation != BridgeValidationError::none) {
                        logBridgeEvent("validation-rejected");
                        return;
                    }
                    logBridgeEvent("accepted");
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
                        if (utf8(request.GetNamedString(L"nonce")) != nativeSettingsNonce_) return;
                        NativeSettingsRequest parsed;
                        parsed.handler = handler;
                        if (handler == NativeSettingsBridge::kNotificationSettingsHandler) {
                            // Retain original JSON: WinRT Stringify collapses duplicate
                            // fields and rewrites fractional numbers as integers.
                            const auto rawEnvelope = DesktopApiClient::jsonObjectFields(rawJson);
                            if (!rawEnvelope) return;
                            const auto rawPayload = rawEnvelope->find("payload");
                            if (rawPayload == rawEnvelope->end()) return;
                            const auto notification = NativeSettingsBridge::parseNotificationPayload(rawPayload->second, nativeSettingsNonce_);
                            if (notification) parsed.notification = notification->request;
                            // Invalid current-document requests still receive an explicit
                            // refusal from the owner, never a timed-out web promise.
                        } else {
                            if (request.GetNamedNumber(L"version") != 1.0) return;
                            const auto action = NativeSettingsBridge::actionFromToken(utf8(request.GetNamedString(L"action")));
                            if (!action) return;
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
                        // Only the three validated theme names may reach the log.
                        if (!isAllowedAppearance(theme)) return;
                        logBridgeEvent("appearance " + theme);
                        if (appearanceHandler_) appearanceHandler_(theme);
                    } else if (message->command == "request_app_quit") {
                        if (isAllowedQuitPayload(message->payloadJson) && quitHandler_) quitHandler_();
                    } else if (message->command == "request_app_update") {
                        // Empty payload was validated before dispatch; never installs.
                        if (updateHandler_) updateHandler_();
                    } else if (message->command == "local_recording") {
                        const auto payload = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(message->payloadJson));
                        if (payload.Size() != 2) return;
                        const auto action = utf8(payload.GetNamedString(L"action"));
                        const auto id = utf8(payload.GetNamedString(L"id"));
                        if (localRecordingActionAllowed(action, id) && localRecordingHandler_)
                            localRecordingHandler_({action, id, documentGeneration_, documentNonce_});
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
            // Both native events and the nonblocking deadline use this one
            // finalizer. No nonce/cookies/bootstrap before the two-event latch.
            nativeFinishDocument_ = [this, alive, dispatcher, core] {
                if (!alive->load() || navigationId_ == 0 || !documentCompletion_) return;
                try {
                    const auto source = utf8(core.Source());
                    const auto& completedUrl = documentCompletion_->url;
                    if (source.substr(0, source.find('#')) != completedUrl.substr(0, completedUrl.find('#'))) {
                        fail("document-changed", E_ACCESSDENIED);
                        return;
                    }
                    const auto result = tryFinishDocumentNavigation(monotonicMilliseconds());
                    // Auth recovery waits for the same explicit user action as macOS.
                    // The shell distinguishes it from an already open sign-in form.
                    if (result != WebResponseDecision::cabinet) return;
                    // Native acceptance must prove request/response correlation
                    // on WebView2. Never ignore a possible recovery header and
                    // install a bridge merely because NavigationCompleted says 200.
                    if (!documentResponse_ || !policy_.allowsNativeBridge(source)) {
                        fail("response-metadata", E_ACCESSDENIED);
                        return;
                    }
                    const auto generation = documentGeneration_;
                    const auto nonce = newNonce();
                    if (nonce.empty()) { fail("nonce", E_FAIL); return; }
                    setRuntimeState(WebRuntimeState::ready);
                    if (!alive->load() || generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready) return;
                    revokeCalendarDocument();
                    bridge_.rotateNonce(nonce);
                    documentNonce_ = nonce;
                    nativeReplyCalendarJoin_ = [this, alive, core, generation](const CalendarJoinRequest& request, CalendarJoinResult result) {
                        if (!alive->load() || generation != documentGeneration_ || !calendarDocumentCurrent(request) ||
                            utf8(core.Source()) != currentUrl_) return;
                        using namespace winrt::Windows::Data::Json;
                        const auto state = result.state == CalendarJoinState::resolving ? L"resolving" :
                            result.state == CalendarJoinState::opening ? L"opening" :
                            result.state == CalendarJoinState::handedOff ? L"handed_off" :
                            result.state == CalendarJoinState::failed ? L"failed" : L"cancelled";
                        const auto reason = result.reason == CalendarJoinReason::busy ? L"busy" :
                            result.reason == CalendarJoinReason::notReady ? L"not_ready" :
                            result.reason == CalendarJoinReason::stale ? L"stale" :
                            result.reason == CalendarJoinReason::authRequired ? L"auth_required" :
                            result.reason == CalendarJoinReason::eventUnavailable ? L"event_unavailable" :
                            result.reason == CalendarJoinReason::dependencyUnavailable ? L"dependency_unavailable" :
                            result.reason == CalendarJoinReason::invalidTarget ? L"invalid_target" :
                            result.reason == CalendarJoinReason::launchFailed ? L"launch_failed" : L"cancelled";
                        JsonObject reply;
                        reply.Insert(L"command", JsonValue::CreateStringValue(L"calendar_join_reply"));
                        reply.Insert(L"nonce", JsonValue::CreateStringValue(winrt::to_hstring(request.nonce)));
                        reply.Insert(L"request_id", JsonValue::CreateStringValue(winrt::to_hstring(request.intent.requestId)));
                        reply.Insert(L"state", JsonValue::CreateStringValue(state));
                        if (result.reason != CalendarJoinReason::none) reply.Insert(L"reason", JsonValue::CreateStringValue(reason));
                        core.PostWebMessageAsJson(reply.Stringify());
                    };
                    // Completion delegates have no UI-apartment guarantee. Marshal
                    // every WinUI/WebView access, including GetResults, to its owner.
                    core.CookieManager().GetCookiesAsync(winrt::to_hstring(policy_.trustedOrigin())).Completed(
                        [this, alive, dispatcher, core, generation, nonce](auto const& operation, auto const&) {
                            dispatcher.TryEnqueue([this, alive, core, generation, nonce, operation] {
                                if (!alive->load() || generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready) return;
                                std::string token;
                                bool reconciled = false;
                                try {
                                    if (nonce != documentNonce_ || utf8(core.Source()) != currentUrl_ ||
                                        !policy_.allowsNativeBridge(currentUrl_)) return;
                                    for (const auto& cookie : operation.GetResults()) {
                                        const auto name = utf8(cookie.Name());
                                        if (name == "__Host-twobrain_rec_owner_session") {
                                            token = utf8(cookie.Value());
                                            break;
                                        }
                                    }
                                    reconciled = true;
                                } catch (...) { token.clear(); }
                                const auto revision = userTimeRevision_;
                                try {
                                    if (!reconcileAuthSessionForDocument(generation, nonce, utf8(core.Source()), token, reconciled)) return;
                                    // Read actual native Source again after the
                                    // handler; a requested navigation is not proof.
                                    reconcileUserTimeCookie(generation, nonce, utf8(core.Source()), std::move(token));
                                } catch (...) {
                                    if (alive->load() && generation == documentGeneration_ && nonce == documentNonce_ &&
                                        runtimeState_ == WebRuntimeState::ready && revision == userTimeRevision_) invalidateUserTime();
                                }
                            });
                        });
                    nativePublishLocalRecordings_ = [this, core, nonce, generation] {
                        if (generation != documentGeneration_ || runtimeState_ != WebRuntimeState::ready) return;
                        if (protectedLocalMode_) {
                            try {
                                if (utf8(core.Source()) != currentUrl_ || !policy_.allowsNativeBridge(currentUrl_)) return;
                                const auto json = protectedLocalRecordingsMessage();
                                const auto length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS,
                                    json.data(), static_cast<int>(json.size()), nullptr, 0);
                                if (length <= 0) throw std::runtime_error("local_inventory_encoding");
                                CustodyWideString wide(static_cast<std::size_t>(length), L'\0');
                                if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, json.data(), static_cast<int>(json.size()),
                                    wide.data(), length) != length) throw std::runtime_error("local_inventory_encoding");
                                // param::hstring references this NUL-terminated buffer
                                // until the synchronous call returns; no owned native
                                // whole-inventory HSTRING/JsonArray duplicate.
                                core.PostWebMessageAsJson(std::wstring_view(wide.data(), wide.size()));
                                protectedLocalPublicationPending_ = false;
                            } catch (...) {
                                failProtectedLocalPublication();
                            }
                            return;
                        }
                        if (utf8(core.Source()) != currentUrl_ || !policy_.allowsNativeBridge(currentUrl_)) return;
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
                            if (item.durationSeconds.has_value())
                                row.Insert(L"durationSeconds", JsonValue::CreateNumberValue(static_cast<double>(*item.durationSeconds)));
                            if (item.sessionDurationSeconds.has_value())
                                row.Insert(L"sessionDurationSeconds", JsonValue::CreateNumberValue(static_cast<double>(*item.sessionDurationSeconds)));
                            row.Insert(L"showsPartialDuration", JsonValue::CreateBooleanValue(item.showsPartialDuration));
                            row.Insert(L"canOpen", JsonValue::CreateBooleanValue(item.canOpen));
                            row.Insert(L"canSend", JsonValue::CreateBooleanValue(item.canSend));
                            row.Insert(L"canDelete", JsonValue::CreateBooleanValue(item.canDelete));
                            row.Insert(L"uploadComplete", JsonValue::CreateBooleanValue(item.uploadComplete));
                            // Кабинет ждёт число или отсутствие поля: неизмеримый
                            // прогресс не превращается в ноль процентов.
                            if (item.progressPercent.has_value()) {
                                row.Insert(L"progressPercent", JsonValue::CreateNumberValue(*item.progressPercent));
                            }
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
                            !policy_.allowsNativeBridge(currentUrl_)) return;
                        core.ExecuteScriptAsync(winrt::to_hstring(std::string(script)));
                    };
                    nativeReadUserTime_ = [this, alive, dispatcher, core](UserTimeRead read) {
                        if (!alive->load() || !userTimeReadCurrent(read) || utf8(core.Source()) != read.url) return;
                        // Execute on the main document, not a page message/frame.
                        // Missing metadata remains missing and fails strict decoding.
                        constexpr auto script = LR"JS((() => {
                            const read = name => document.querySelector('meta[name="' + name + '"]')?.content;
                            return {userId: read('graf-time-user'), workspaceId: read('graf-workspace'),
                                sessionId: read('graf-time-session'), timeZone: read('graf-time-preferred'),
                                documentURL: document.URL};
                        })())JS";
                        core.ExecuteScriptAsync(script).Completed(
                            [this, alive, dispatcher, core, read](auto const& operation, auto const&) {
                                dispatcher.TryEnqueue([this, alive, core, read, operation] {
                                    if (!alive->load() || !userTimeReadCurrent(read)) return;
                                    std::string raw, source;
                                    try {
                                        source = utf8(core.Source());
                                        if (source != read.url) return;
                                        const auto result = operation.GetResults();
                                        if (result.size() <= 2048) raw = utf8(result);
                                    } catch (...) { raw.clear(); source = read.url; }
                                    completeUserTimeRead(read, raw, source);
                                });
                            });
                    };
                    refreshUserTime();
                    core.ExecuteScriptAsync(winrt::to_hstring(kDesktopBridgeScript)).Completed(
                        [this, alive, dispatcher, core, nonce, generation](auto const& operation, auto const&) {
                            dispatcher.TryEnqueue([this, alive, dispatcher, core, nonce, generation, operation] {
                                if (!alive->load() || generation != documentGeneration_ ||
                                    runtimeState_ != WebRuntimeState::ready) return;
                                try {
                                    if (utf8(core.Source()) != currentUrl_ || !policy_.allowsNativeBridge(currentUrl_)) return;
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
                                    publishCalendarJoinAvailability();
                                    setAppUpdateAvailable(appUpdateAvailable_);
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
                                                        !policy_.allowsNativeBridge(currentUrl_)) return;
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
            };
            core.NavigationCompleted([this, alive, responseTimer](auto const& core, auto const& args) {
                if (!alive->load() || navigationId_ == 0 || args.NavigationId() != navigationId_) return;
                try {
                    using Error = winrt::Microsoft::Web::WebView2::Core::CoreWebView2WebErrorStatus;
                    const auto status = args.HttpStatusCode();
                    // Runtime also reports ordinary HTTP 4xx/5xx with Unknown.
                    // This is only a candidate: the response latch still requires
                    // correlated document headers before applying auth/MIME policy.
                    const bool httpErrorDocument = args.WebErrorStatus() == Error::Unknown ||
                        args.WebErrorStatus() == Error::ErrorHttpInvalidServerResponse ||
                        (status == 401 && args.WebErrorStatus() == Error::ValidAuthenticationCredentialsRequired);
                    if (!observeDocumentCompletion(utf8(core.Source()), args.NavigationId(), status,
                        args.IsSuccess(), httpErrorDocument, monotonicMilliseconds())) return;
                    const auto finish = nativeFinishDocument_;
                    if (finish) finish();
                    if (alive->load() && args.NavigationId() == navigationId_ && documentCompletion_)
                        responseTimer.Start();
                } catch (const winrt::hresult_error& error) { fail("document", error.code().value); }
                catch (...) { fail("document", E_FAIL); }
            });
            core.Navigate(winrt::to_hstring(requestedDocumentUrl_.empty() ? recoveryUrl() : requestedDocumentUrl_));
        } catch (const winrt::hresult_error& error) {
            fail("configure", error.code().value);
        } catch (...) { fail("configure", E_FAIL); }
    });
    const auto ensureControl = [this, alive, dispatcher, control](auto const& environment) {
        control.EnsureCoreWebView2Async(environment).Completed(
            [this, alive, dispatcher](auto const& ensured, auto const&) {
                dispatcher.TryEnqueue([this, alive, ensured] {
                    if (!alive->load()) return;
                    try { ensured.GetResults(); }
                    catch (const winrt::hresult_error& error) { fail("ensure-control", error.code().value); }
                    catch (...) { fail("ensure-control", E_FAIL); }
                });
            });
    };
    nativeInitialize_ = [this, alive, dispatcher, ensureControl, suppliedEnvironment] {
        if (!alive->load() || runtimeState_ == WebRuntimeState::initializing) return;
        try {
            failureDetail_.clear();
            setRuntimeState(WebRuntimeState::initializing);
            if (suppliedEnvironment) {
                ensureControl(suppliedEnvironment);
                return;
            }
            const auto userData = webViewUserDataFolder();
            if (userData.empty()) { fail("profile", E_ACCESSDENIED); return; }
            auto environment = winrt::Microsoft::Web::WebView2::Core::CoreWebView2Environment::CreateWithOptionsAsync(
                winrt::hstring{}, winrt::hstring(userData.wstring()),
                winrt::Microsoft::Web::WebView2::Core::CoreWebView2EnvironmentOptions{});
            environment.Completed([this, alive, dispatcher, ensureControl](auto const& operation, auto const&) {
                dispatcher.TryEnqueue([this, alive, ensureControl, operation] {
                    if (!alive->load()) return;
                    try {
                        ensureControl(operation.GetResults());
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
