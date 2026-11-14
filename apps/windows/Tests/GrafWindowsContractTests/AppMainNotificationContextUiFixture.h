#pragma once
// AppMain context/refresh regression, without a browser, storage or devices.
#include "AppMainProblemUiFixture.h"
#include "../../RecApp/Shell/CabinetWindow.h"

namespace graf::windows {
struct WebView2SettingsContextFixture {
    static void observe(WebView2Host& host, std::function<void(std::string_view)> observer) {
        host.currentUrl_ = host.policy_.trustedOrigin() + "/desktop/settings/notifications";
        host.nativeSettingsNonce_ = "generated-context-nonce";
        host.nativeRunScript_ = std::move(observer);
    }
    static void detach(WebView2Host& host) {
        host.nativeRunScript_ = {};
        host.nativeSettingsNonce_.clear();
    }
};
namespace testing {
struct NotificationContextUiState {
    std::filesystem::path root = std::filesystem::temp_directory_path() /
        ("graf-notification-context-" + native_capture_detail::newSessionId());
    winrt::handle release{CreateEventW(nullptr, TRUE, FALSE, nullptr)};
    unsigned refreshes = 0, initialRefreshes = 0;
    bool lastCanEdit = false, closing = false, finished = false, failed = false;
    ULONGLONG began = GetTickCount64();

    DesktopHttpTransport::UploadResponse account(const DesktopHttpConfig& config,
        const DesktopHttpTransport::UploadRequest& request) const {
        requireProblemUi(config.sessionToken == "generated-context-token" && request.method == "GET",
            "context_generated_wire");
        if (request.path == "/desktop/settings/spaces")
            return {200, R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})"};
        requireProblemUi(request.path == "/api/v1/auth/me", "context_identity_only");
        requireProblemUi(WaitForSingleObject(release.get(), 5000) == WAIT_OBJECT_0, "context_account_deadline");
        return {200, R"({"user_id":"11111111-1111-4111-8111-111111111111","workspace_id":"22222222-2222-4222-8222-222222222222","active_session_id":"33333333-3333-4333-8333-333333333333"})"};
    }
};
} // namespace testing
} // namespace graf::windows
