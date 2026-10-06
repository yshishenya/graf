#pragma once

#include <string>
#include <string_view>
#include <cstdint>
#include <optional>

namespace graf::windows {

enum class RouteKind {
    meetings,
    meetingDetail,
    artifactDownload,
    settings,
    nativeSettings,
    authRecovery,
    authProvider,
    paymentProvider,
    frame,
    review,
    deletionReport,
    share,
    billing,
    external,
    denied,
};

enum class RouteDecision {
    allow,
    openExternal,
    deny,
};

struct RouteEvaluation {
    RouteDecision decision = RouteDecision::deny;
    RouteKind kind = RouteKind::denied;
    std::string normalizedUrl;
};

enum class AuthContinuation { none, yandex, vk };

enum class WebResponseDecision {
    cabinet, interactiveForm, externalDocument, expiredSession, workspaceReselection,
    accessDenied, notFound, timeout, unavailable, malformed, blocked, ignore,
};

struct WebDocumentResponse {
    int status = 200;
    bool transportSucceeded = true;
    std::string contentType{};
    std::string recoveryHeader{};
};

struct WebResponseEvaluation {
    WebResponseDecision decision;
};

class WebViewRoutePolicy final {
public:
    explicit WebViewRoutePolicy(std::string trustedOrigin = "https://rec.2brain.pro");

    // Host grants a short-lived, provider-specific continuation only after an
    // approved same-origin start route. It never grants bridge permissions.
    [[nodiscard]] RouteEvaluation evaluate(std::string_view url, bool topLevel = true,
        AuthContinuation auth = AuthContinuation::none, bool payment = false) const;
    [[nodiscard]] AuthContinuation authContinuationForStart(std::string_view url) const noexcept;
    [[nodiscard]] bool isAllowedDownload(std::string_view url, std::string_view sourceUrl) const;
    [[nodiscard]] bool sharesOrigin(std::string_view url) const;
    [[nodiscard]] bool canStartPayment(std::string_view source, std::string_view destination) const;
    [[nodiscard]] bool allowsNativeBridge(std::string_view url) const;
    [[nodiscard]] WebResponseEvaluation response(std::string_view url, const WebDocumentResponse& response,
        AuthContinuation auth = AuthContinuation::none, bool payment = false) const;
    [[nodiscard]] std::string safeRecoveryUrl(std::string_view url, std::string_view method = "GET") const;
    [[nodiscard]] std::string recoveryUrl(WebResponseDecision reason, std::string_view safeDocument,
        bool billingContext = false) const;
    [[nodiscard]] const std::string& trustedOrigin() const noexcept { return trustedOrigin_; }

private:
    std::string trustedOrigin_;
};

// One non-persistent allowance per host. Milliseconds are supplied by the host's
// monotonic clock (GetTickCount64 on Windows, including time asleep) or a test.
class PaymentNavigation final {
public:
    [[nodiscard]] bool begin(const WebViewRoutePolicy& policy, std::string_view source,
        std::string_view destination, std::uint64_t now);
    [[nodiscard]] bool live(std::uint64_t now) const noexcept;
    [[nodiscard]] bool started() const noexcept { return startedAt_.has_value(); }
    void loaded(const WebViewRoutePolicy& policy, std::string_view url, std::uint64_t now);
    void stop() noexcept { startedAt_.reset(); }
private:
    std::optional<std::uint64_t> startedAt_;
};

} // namespace graf::windows
