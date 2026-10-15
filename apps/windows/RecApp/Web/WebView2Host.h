#pragma once

#include "WebViewRoutePolicy.h"
#include "WebViewBridge.h"
#include "RecordingDeletionBridge.h"
#include "NativeSettingsBridge.h"
#include "../Shell/CalendarJoinOperation.h"
#include "../Upload/DesktopUploadQueueService.h"

#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <atomic>
#include <memory>
#include <vector>
#include <chrono>
#include <set>

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.Web.WebView2.Core.h>
#endif

namespace graf::windows {

enum class WebRuntimeState {
    unavailable,
    initializing,
    ready,
    authRequired,
    unprivileged, // Visible payment/email form, never a native bridge or auth recovery signal.
    closed,
};

enum class WebProcessFailure {
    browserExited,
    renderExited,
    renderUnresponsive,
    frameRenderExited,
    automaticallyRecoverable,
};

struct WebViewLocalRecordingRow {
    std::string id;
    // The identifier the server knows for this local copy. The cabinet sends back
    // the row id it was shown, and a deletion request has to name what the server
    // can act on; empty means the row id is also the directory of the package.
    std::string originId;
    std::string title = "Запись";
    std::string startedAt;
    // Prefix the cabinet joins with its own date format, so the local row is
    // localized in the viewer's time zone instead of the recording machine's.
    // Empty when the package carries no start time, which keeps the plain title.
    std::string generatedTitlePrefix;
    std::string status;
    // Missing metadata is unknown, not a measured zero.
    std::optional<std::uint64_t> durationSeconds;
    // Wall-clock length of the whole session. It exceeds durationSeconds when
    // only the confirmed prefix of an interrupted recording survived.
    std::optional<std::uint64_t> sessionDurationSeconds;
    bool showsPartialDuration = false;
    bool canOpen = false;
    bool canSend = false;
    bool canDelete = false;
    bool uploadComplete = false;
    // Server meeting id once the server owns this recording. The cabinet uses it
    // to replace the local row with the server row instead of showing both.
    std::string meetingId;
    // The user asked to remove this local copy and the files are not proven gone.
    // The cabinet reports such a row as a pending cleanup instead of drawing it as
    // a recording, so it is not offered for upload or deletion again.
    // Сколько записи уже принято сервером, если это измеримо. Кабинет показывает
    // «Отправляется · N %», а неизвестный прогресс обязан молчать, а не врать нулём.
    std::optional<int> progressPercent;
    bool localDeletionPending = false;
    // The server was never told about this recording, so deleting it is a purely
    // local act. The cabinet says so in the delete dialog, and the executor treats
    // the same rows as requests that need no server call.
    bool deletionIsLocalOnly = false;
};

class WebView2Host final {
public:
    using NavigationHandler = std::function<void(RouteEvaluation)>;
    using RuntimeHandler = std::function<void(WebRuntimeState)>;
    using QuitHandler = std::function<void()>;
    using AuthSessionHandler = std::function<void(std::string)>;
    // Optional native-only decorator. Input is the already encoded, safe login
    // URL. It may append query fields, never replace next/origin/workspace.
    // Attribution validation/storage is owned by the caller, not this host.
    using SignInUrlBuilder = std::function<std::string(std::string_view)>;
    struct LocalRecordingRequest {
        std::string action, id;
        std::uint64_t documentGeneration = 0;
        std::string nonce;
    };
    using LocalRecordingHandler = std::function<void(LocalRecordingRequest)>;
    // One of `light`, `dark` or `system`, exactly as macOS accepts it and nothing
    // else: a page that announces something unknown must not decide the appearance
    // of native windows.
    using AppearanceHandler = std::function<void(std::string)>;
    [[nodiscard]] static bool isAllowedAppearance(std::string_view theme) noexcept;

    // One request from a cabinet settings page, already checked against the
    // protocol the page speaks. `action` is the page's own token.
    struct NativeSettingsRequest {
        std::string handler;
        std::string action;
        // `set` names the target it changes; empty for `read` and `setAll`.
        std::string targetId;
        // `set` and `setAll` carry the rule; empty for `read`.
        std::string rule;
        std::optional<NativeSettingsBridge::NotificationRequest> notification = std::nullopt;
    };
    // Answers one request with the JSON body the page validates. An empty answer
    // is a refusal and reaches the page as such.
    using NativeSettingsHandler = std::function<std::string(const NativeSettingsRequest&)>;

    // A deletion the cabinet asked for, together with the document that asked. The
    // answer is only delivered to the page it came from, so a slow deletion cannot
    // surface on a page the user has since opened.
    struct DeletionRequest {
        CabinetDeletionSelection selection;
        // What the selection resolved to against the rows the cabinet was shown,
        // decided with the gate so the page cannot name anything else and the
        // requester does not have to re-derive it from a page it no longer owns.
        std::vector<CabinetDeletionTarget> targets;
        std::uint64_t documentGeneration = 0;
    };
    using DeletionSelectionHandler = std::function<void(DeletionRequest)>;

    struct CalendarJoinRequest {
        CalendarJoinIntent intent;
        std::uint64_t documentGeneration = 0;
        std::string nonce;
    };
    using CalendarJoinHandler = std::function<void(CalendarJoinRequest)>;
    // Both callbacks belong to the single AppMain owner. Default/partial wiring
    // grants no calendar command authority. Cancellation never proves work drain.
    void setCalendarJoinHandlers(CalendarJoinHandler join, CalendarJoinHandler cancel);
    void replyCalendarJoin(const CalendarJoinRequest&, CalendarJoinResult);
    [[nodiscard]] bool calendarJoinCurrent(const CalendarJoinRequest& request) {
        return calendarRequestPending(request) && calendarDocumentCurrent(request) && bridge_.isAllowedWebCommand("calendar_join");
    }

    explicit WebView2Host(WebViewRoutePolicy policy = WebViewRoutePolicy());
    ~WebView2Host();

    WebView2Host(const WebView2Host&) = delete;
    WebView2Host& operator=(const WebView2Host&) = delete;
    WebView2Host(WebView2Host&&) = delete;
    WebView2Host& operator=(WebView2Host&&) = delete;

    void setRuntimeState(WebRuntimeState state) noexcept;
    [[nodiscard]] WebRuntimeState runtimeState() const noexcept { return runtimeState_; }
    [[nodiscard]] bool genericHostObjectsAllowed() const noexcept { return false; }
    [[nodiscard]] RouteEvaluation navigate(std::string url);
    void close() noexcept;
    void reload();
    void handleProcessFailure(WebProcessFailure failure, std::int32_t exitCode) noexcept;
    void back();
    void forward();
    [[nodiscard]] bool canGoBack() const;
    [[nodiscard]] bool canGoForward() const;
    [[nodiscard]] const std::string& failureDetail() const noexcept { return failureDetail_; }
    void setNavigationHandler(NavigationHandler handler) { navigationHandler_ = std::move(handler); }
    void setRuntimeHandler(RuntimeHandler handler) { runtimeHandler_ = std::move(handler); }
    void setQuitHandler(QuitHandler handler) { quitHandler_ = std::move(handler); }
    void setUpdateHandler(std::function<void()> handler) { updateHandler_ = std::move(handler); }
    void setAppUpdateAvailable(bool available);
    void setAuthSessionHandler(AuthSessionHandler handler) { authSessionHandler_ = std::move(handler); }
    // Native confirmed account only. Metadata can change presentation, never auth.
    void bindUserTimeAccount(std::string origin, std::string user, std::string workspace,
                             std::string sessionToken, std::uint64_t authGeneration);
    [[nodiscard]] const std::string& preferredUserTimeZone() const noexcept { return userTimeZone_; }
    [[nodiscard]] std::uint64_t userTimeRevision() const noexcept { return userTimeRevision_; }
    void setSignInUrlBuilder(SignInUrlBuilder builder) { signInUrlBuilder_ = std::move(builder); }
    [[nodiscard]] std::string signInUrl() const;
    void setLocalRecordingHandler(LocalRecordingHandler handler) { localRecordingHandler_ = std::move(handler); }
    // The cabinet owns its theme and announces it (macOS receives the same value
    // through `grafAppAppearance`), so the native surfaces can follow the page
    // instead of assuming an appearance the user may not have chosen.
    void setAppearanceHandler(AppearanceHandler handler) { appearanceHandler_ = std::move(handler); }
    // Как страница видит системную тему. Без этого `prefers-color-scheme` внутри
    // кабинета расходится с темой окна, и при выборе «системная» кабинет рисуется
    // тёмным на светлом окне. Значение запоминается до создания среды.
    void setPreferredColorScheme(bool isDark) {
        colorSchemeIsDark_ = isDark;
        if (preferredColorScheme_) preferredColorScheme_(isDark);
    }
    // Settings pages are answered only while the document on screen is the page
    // they belong to. Without a handler nothing is installed at all, so a page
    // never asks a question this app cannot answer.
    void setNativeSettingsHandler(NativeSettingsHandler handler);
    // Called when the app's own settings change while the cabinet is open, so the
    // page shows the state that is actually stored. macOS does the same from its
    // settings notifications.
    void refreshNativeSettings();
    // Extends the cabinet's own session cookie to the deadline the server named
    // while answering an authenticated request. macOS rewrites the same cookie for
    // the same reason: a cookie that expires earlier than the server's session
    // signs the cabinet out while the app's own calls still work. The cookie is
    // only rewritten when its value is still the token that was used, so a
    // session that changed in the meantime is never prolonged.
    void extendAuthCookieExpiry(std::string_view token, std::int64_t unixSeconds);
    [[nodiscard]] static bool authCookieShouldBeExtended(std::string_view cookieValue,
                                                        std::string_view token,
                                                        std::int64_t unixSeconds,
                                                        std::int64_t nowUnixSeconds) noexcept;
    void setDeletionSelectionHandler(DeletionSelectionHandler handler) {
        deletionSelectionHandler_ = std::move(handler);
    }
    // Answers the page that asked. The bridge is the only thing that may tell the
    // cabinet a deletion is on its way, so the outcome travels through it.
    void completeDeletionSelection(const DeletionRequest& request, const CabinetDeletionOutcome& outcome);
    bool completeDeletionSelection(std::uint64_t documentGeneration, std::string_view requestId,
        const CabinetDeletionOutcome& outcome);
    // The gate a message has to pass before it becomes a deletion: the message has
    // to have the shape macOS accepts, the page has to be one that shows deletable
    // rows, every local row has to be one this app offers for deletion, and on a
    // meeting page the selection has to be that meeting. Kept free of the WebView
    // so the whole gate is testable without a browser.
    [[nodiscard]] std::optional<CabinetDeletionSelection> deletionSelectionFrom(
        const CabinetDeletionInput& input, std::string_view pageUrl) const noexcept;
    // The meeting a page shows, or empty for a page that shows more than one (the
    // meeting list) or is not a meeting page at all. The page is given, not read
    // from the host: the decision then depends only on what is being decided.
    [[nodiscard]] static std::string meetingIdOnPage(std::string_view pageUrl);
    // The local rows exactly as the cabinet sees them. A deletion is decided
    // against these, not against a second reading of the ledger.
    [[nodiscard]] std::vector<CabinetLocalRow> cabinetRows() const;
    // Rebuild the XAML WebView2 control and attach it again; retain the profile.
    void setRecreateHandler(std::function<void()> handler) { recreateHandler_ = std::move(handler); }
    // The rows and, with them, the deletions in flight: the cabinet prints the
    // phase of each one and what it is waiting for, so a saved request is visible
    // instead of only remembered. `recoveryRequired` is the page's own notice that
    // some local recordings are hidden because their account is not confirmed —
    // separate from storage checking/unavailability.
    void setLocalRecordings(std::vector<WebViewLocalRecordingRow> rows,
                            std::vector<CabinetDeletionOperation> operations = {},
                            bool recoveryRequired = false);
    void setProtectedLocalRecordings(std::shared_ptr<const ProtectedUploadQueueValue> value, bool complete,
        std::string origin, std::string user, std::string workspace, std::uint64_t authGeneration,
        std::shared_ptr<const ProtectedLocalRecordingTimings> timings = {});
    [[nodiscard]] static std::string_view localRecordingStatus(const ProtectedUploadQueueValue::Item&) noexcept;
    [[nodiscard]] bool localRecordingActionAllowed(std::string_view action, std::string_view id) const noexcept;
    [[nodiscard]] bool localPlaybackDocumentCurrent(std::uint64_t generation, std::string_view nonce) const noexcept;
    [[nodiscard]] static bool isAllowedQuitPayload(std::string_view payload) noexcept;
    // Fills the cabinet fields that come from the local package bounds: the
    // instant in wire form, the generated-title prefix, the session length and
    // whether the row must report a partial duration. Kept next to the row it
    // fills so the mapping is testable without a WebView or a window.
    static void applyLocalPackageTiming(
        WebViewLocalRecordingRow& row,
        std::uint64_t startedAtMs,
        std::uint64_t stoppedAtMs,
        bool captureInterrupted);

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
    void attach(winrt::Microsoft::UI::Xaml::Controls::WebView2 control,
        winrt::Microsoft::Web::WebView2::Core::CoreWebView2Environment environment = nullptr);
#endif

    [[nodiscard]] const std::string& currentUrl() const noexcept { return currentUrl_; }
    [[nodiscard]] const WebViewRoutePolicy& routePolicy() const noexcept { return policy_; }
    // Shared lifecycle core, exercised by portable tests and the native events.
    // Only main-document NavigationStarting/Completed may call these methods.
    [[nodiscard]] RouteEvaluation beginDocumentNavigation(std::string_view url, std::uint64_t id,
        bool redirected, std::uint64_t now, std::string_view method = "GET");
    [[nodiscard]] WebResponseDecision completeDocumentNavigation(std::string_view url, std::uint64_t id,
        const WebDocumentResponse& response, std::uint64_t now);
    [[nodiscard]] RouteEvaluation evaluatePopupNavigation(std::string_view url, std::uint64_t now);
    // Native frame identity, never inferred from a frame URL or page script.
    struct PopupSource {
        std::uint64_t documentGeneration = 0;
        std::uint32_t frameId = 0;
        std::uint32_t coreFrameId = 0;
        bool isMainFrame = false;
    };
    [[nodiscard]] bool beginPaymentPopup(std::string_view url, PopupSource source,
        std::uint64_t now, std::function<void()> cleanup);
    [[nodiscard]] bool handOffPaymentPopup(PopupSource source, std::uint64_t now);
    [[nodiscard]] bool paymentPopupChildCurrent(std::uint64_t generation, unsigned childOrdinal,
        std::uint64_t now) const noexcept;
    [[nodiscard]] bool bindPaymentPopupFrame(std::uint32_t frameId, std::uint64_t generation,
        unsigned childOrdinal, std::uint64_t now);
    [[nodiscard]] RouteEvaluation evaluatePaymentPopupDocument(std::string_view url, std::uint64_t now);
    [[nodiscard]] bool paymentPopupLiveAt(std::uint64_t now) const noexcept;
    void cancelPaymentPopup() noexcept;
    [[nodiscard]] bool paymentNavigationAllowedAt(std::uint64_t now) const noexcept { return payment_.live(now); }
    [[nodiscard]] const std::string& safeRecoveryUrl() const noexcept { return safeRecoveryUrl_; }
    [[nodiscard]] std::string recoveryUrl() const;
    // Only a failed protected document needs the native recovery screen.
    // Interactive sign-in documents also use authRequired, but must stay visible.
    [[nodiscard]] WebResponseDecision pendingAuthRecovery() const noexcept;
    // Metadata is bound to the main request generation, not merely a URL which
    // an older request or iframe can share with the next document.
    [[nodiscard]] bool observeDocumentResponse(std::string_view url, std::uint64_t generation,
        std::string_view method, const WebDocumentResponse& response);
    // The request tag is issued before browser-added headers are necessarily
    // available. Only the final browser document destination can consume it.
    [[nodiscard]] std::string documentRequestTag(std::string_view url) const;
    [[nodiscard]] bool observeDocumentResponseHeaders(std::string_view url, std::string_view tag,
        std::string_view destination, std::string_view method, const WebDocumentResponse& response);
    [[nodiscard]] bool observeDocumentCompletion(std::string_view url, std::uint64_t id,
        int status, bool succeeded, bool httpErrorDocument, std::uint64_t now);
    [[nodiscard]] WebResponseDecision tryFinishDocumentNavigation(std::uint64_t now);
    [[nodiscard]] std::uint64_t documentGeneration() const noexcept { return documentGeneration_; }

private:
    friend struct WebView2CalendarJoinFixture;
    struct UserTimeRead {
        std::string origin, user, workspace, token, nonce, url;
        std::uint64_t authGeneration = 0, documentGeneration = 0, revision = 0;
    };
    UserTimeRead userTimeAccount_;
    UserTimeRead localAccount_;
    std::shared_ptr<const ProtectedUploadQueueValue> protectedLocalValue_;
    std::shared_ptr<const ProtectedLocalRecordingTimings> protectedLocalTimings_;
    bool protectedLocalMode_ = false, protectedLocalComplete_ = false, localDocumentIdentity_ = false;
    bool protectedLocalPublicationPending_ = false;
    std::chrono::steady_clock::time_point protectedLocalRetryAt_{};
    [[nodiscard]] CustodyString protectedLocalRecordingsMessage() const;
    [[nodiscard]] bool protectedLocalOpenAllowed(const ProtectedUploadQueueValue::Item&) const noexcept;
    void failProtectedLocalPublication() noexcept;
    std::string userTimeZone_, userTimeSession_, userTimeCookieToken_;
    std::uint64_t userTimeRevision_ = 0, userTimeCookieGeneration_ = 0;
    std::optional<std::uint64_t> userTimeAttemptedRevision_;
    std::function<void(UserTimeRead)> nativeReadUserTime_;
    void invalidateUserTime() noexcept;
    void refreshUserTime();
    [[nodiscard]] bool userTimeDocumentCurrent() const;
    [[nodiscard]] bool userTimeReadCurrent(const UserTimeRead&) const;
    void reconcileUserTimeCookie(std::uint64_t generation, std::string_view nonce,
                                 std::string_view url, std::string token);
    [[nodiscard]] bool reconcileAuthSessionForDocument(std::uint64_t generation, std::string nonce,
                                        std::string url, std::string token, bool reconciled);
    void completeUserTimeRead(const UserTimeRead&, std::string_view raw, std::string_view source);
    CalendarJoinHandler calendarJoinHandler_, calendarCancelHandler_;
    std::optional<CalendarJoinRequest> pendingCalendarJoin_;
    CalendarJoinState calendarJoinState_ = CalendarJoinState::idle;
    std::set<std::string> calendarRequestIds_;
    bool calendarInvalidating_ = false;
    std::function<void(const CalendarJoinRequest&, CalendarJoinResult)> nativeReplyCalendarJoin_;
    [[nodiscard]] bool calendarDocumentCurrent(const CalendarJoinRequest&) const;
    [[nodiscard]] bool calendarRequestPending(const CalendarJoinRequest&) const noexcept;
    void publishCalendarJoinAvailability();
    void handleCalendarJoinMessage(const WebViewBridgeEnvelope&, std::string_view sourceUrl);
    void emitCalendarJoinReply(const CalendarJoinRequest&, CalendarJoinResult);
    void cancelPendingCalendarJoin() noexcept;
    void revokeCalendarDocument() noexcept;
#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
    friend struct WebView2PaymentPopupNativeFixture;
    // Native fixture injects a failure at the irreversible browser handoff.
    // Never set by the application or a web message.
    std::function<void(bool, winrt::Microsoft::Web::WebView2::Core::CoreWebView2 const&)> popupHandoffCheckpoint_;
    void openPaymentPopup(winrt::Microsoft::UI::Xaml::Controls::WebView2 opener,
        winrt::Microsoft::Web::WebView2::Core::CoreWebView2NewWindowRequestedEventArgs args);
#endif
    WebViewRoutePolicy policy_;
    NavigationHandler navigationHandler_;
    RuntimeHandler runtimeHandler_;
    QuitHandler quitHandler_;
    std::function<void()> updateHandler_;
    bool appUpdateAvailable_ = false;
    AuthSessionHandler authSessionHandler_;
    SignInUrlBuilder signInUrlBuilder_;
    LocalRecordingHandler localRecordingHandler_;
    AppearanceHandler appearanceHandler_;
    std::function<void(bool)> preferredColorScheme_;
    bool colorSchemeIsDark_ = true;
    NativeSettingsHandler nativeSettingsHandler_;
    // The value the page had to echo back. Rotated with every document that may
    // use the bridge, so a request from an older page is not answered.
    std::string nativeSettingsNonce_;
    // The nonce of the document on screen, kept so an answer carries the same
    // envelope the page was handed when it loaded.
    std::string documentNonce_;
    std::function<void(std::string_view, std::int64_t)> nativeExtendAuthCookie_;
    void beginNativeSettings();
    DeletionSelectionHandler deletionSelectionHandler_;
    std::vector<WebViewLocalRecordingRow> localRecordings_;
    std::vector<CabinetDeletionOperation> localDeletionOperations_;
    bool localRecoveryRequired_ = false;
    std::function<void()> nativePublishLocalRecordings_;
    std::function<void(std::string_view)> nativeRunScript_;
    WebViewBridge bridge_;
    WebRuntimeState runtimeState_ = WebRuntimeState::unavailable;
    std::string currentUrl_;
    // A native GET requested before the control exists is not a loaded document
    // or a recovery target. Keep it separately until NavigationStarting.
    std::string requestedDocumentUrl_;
    std::string safeRecoveryUrl_;
    bool billingContext_ = false;
    WebResponseDecision recoveryReason_ = WebResponseDecision::unavailable;
    PaymentNavigation payment_;
    struct PaymentPopup {
        PopupSource source;
        std::string billingSource;
        std::uint64_t admittedAt;
        bool handedOff = false;
        bool returning = false;
        std::function<void()> cleanup;
        std::uint32_t activeFrameId = 0;
        unsigned children = 1;
    };
    std::optional<PaymentPopup> paymentPopup_;
    std::string committedDocumentUrl_;
    std::string navigationSourceUrl_;
    std::string navigationUrl_;
    std::string navigationMethod_;
    std::optional<WebDocumentResponse> documentResponse_;
    struct DocumentCompletion {
        std::string url;
        int status;
        bool succeeded;
        bool httpErrorDocument;
        std::uint64_t observedAt;
    };
    std::optional<DocumentCompletion> documentCompletion_;
    static constexpr std::uint64_t kResponseWaitMs = 5000;
    std::function<void()> nativeFinishDocument_;
    std::function<void()> nativeStopResponseTimer_;
    void resetDocumentResponse() noexcept;
    std::uint64_t navigationId_ = 0;
    AuthContinuation authContinuation_ = AuthContinuation::none;
    std::chrono::steady_clock::time_point authStarted_{};
    unsigned authNavigations_ = 0;
    bool recreateRequired_ = false;
    std::function<void()> recreateHandler_;
    std::function<void(std::string_view)> nativeNavigate_;
    std::function<void()> nativeReload_;
    std::function<void()> nativeBack_;
    std::function<void()> nativeForward_;
    std::function<bool()> nativeCanGoBack_;
    std::function<bool()> nativeCanGoForward_;
    std::function<void()> nativeClose_;
    std::function<void()> nativeCancelDialog_;
    std::function<void()> nativeInitialize_;
    std::shared_ptr<std::atomic_bool> alive_;
    std::uint64_t documentGeneration_ = 0;
    std::string failureDetail_;
    void fail(std::string_view stage, std::int32_t code) noexcept;
    void cancelDialog() noexcept;
    [[nodiscard]] AuthContinuation activeAuthContinuation() const noexcept;
    [[nodiscard]] static std::uint64_t monotonicMilliseconds() noexcept;

};

} // namespace graf::windows
