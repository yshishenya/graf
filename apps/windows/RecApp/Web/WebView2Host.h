#pragma once

#include "WebViewRoutePolicy.h"
#include "WebViewBridge.h"
#include "RecordingDeletionBridge.h"
#include "NativeSettingsBridge.h"

#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <atomic>
#include <memory>
#include <vector>
#include <chrono>

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#endif

namespace graf::windows {

enum class WebRuntimeState {
    unavailable,
    initializing,
    ready,
    authRequired,
    closed,
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
    std::uint64_t durationSeconds = 0;
    // Wall-clock length of the whole session. It exceeds durationSeconds when
    // only the confirmed prefix of an interrupted recording survived.
    std::uint64_t sessionDurationSeconds = 0;
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
    using LocalRecordingHandler = std::function<void(std::string, std::string)>;
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
    void back();
    void forward();
    [[nodiscard]] bool canGoBack() const;
    [[nodiscard]] bool canGoForward() const;
    [[nodiscard]] const std::string& failureDetail() const noexcept { return failureDetail_; }
    void setNavigationHandler(NavigationHandler handler) { navigationHandler_ = std::move(handler); }
    void setRuntimeHandler(RuntimeHandler handler) { runtimeHandler_ = std::move(handler); }
    void setQuitHandler(QuitHandler handler) { quitHandler_ = std::move(handler); }
    void setAuthSessionHandler(AuthSessionHandler handler) { authSessionHandler_ = std::move(handler); }
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
    // false on Windows, where every row is shown with its reason.
    void setLocalRecordings(std::vector<WebViewLocalRecordingRow> rows,
                            std::vector<CabinetDeletionOperation> operations = {},
                            bool recoveryRequired = false);
    [[nodiscard]] bool localRecordingActionAllowed(std::string_view action, std::string_view id) const noexcept;
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
    void attach(winrt::Microsoft::UI::Xaml::Controls::WebView2 control);
#endif

    [[nodiscard]] const std::string& currentUrl() const noexcept { return currentUrl_; }
    [[nodiscard]] const WebViewRoutePolicy& routePolicy() const noexcept { return policy_; }

private:
    WebViewRoutePolicy policy_;
    NavigationHandler navigationHandler_;
    RuntimeHandler runtimeHandler_;
    QuitHandler quitHandler_;
    AuthSessionHandler authSessionHandler_;
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
    std::string retryUrl_;
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

};

} // namespace graf::windows
