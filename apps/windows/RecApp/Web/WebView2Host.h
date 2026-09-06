#pragma once

#include "WebViewRoutePolicy.h"
#include "WebViewBridge.h"

#include <functional>
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
    std::string title = "Локальная запись";
    std::string startedAt;
    std::string status;
    std::uint64_t durationSeconds = 0;
    bool canOpen = false;
    bool canSend = false;
    bool canDelete = false;
    bool uploadComplete = false;
};

class WebView2Host final {
public:
    using NavigationHandler = std::function<void(RouteEvaluation)>;
    using RuntimeHandler = std::function<void(WebRuntimeState)>;
    using QuitHandler = std::function<void()>;
    using AuthSessionHandler = std::function<void(std::string)>;
    using LocalRecordingHandler = std::function<void(std::string, std::string)>;

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
    // Rebuild the XAML WebView2 control and attach it again; retain the profile.
    void setRecreateHandler(std::function<void()> handler) { recreateHandler_ = std::move(handler); }
    void setLocalRecordings(std::vector<WebViewLocalRecordingRow> rows);
    [[nodiscard]] bool localRecordingActionAllowed(std::string_view action, std::string_view id) const noexcept;
    [[nodiscard]] static bool isAllowedQuitPayload(std::string_view payload) noexcept;

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
    std::vector<WebViewLocalRecordingRow> localRecordings_;
    std::function<void()> nativePublishLocalRecordings_;
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
