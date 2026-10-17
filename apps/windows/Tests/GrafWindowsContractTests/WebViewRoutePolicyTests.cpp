#include "../../RecApp/Web/WebViewRoutePolicy.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

static void paymentAndResponseContract() {
    using namespace graf::windows;
    const WebViewRoutePolicy policy;
    const std::string origin = policy.trustedOrigin();
    const auto billing = origin + "/billing/checkout";
    for (const auto host : {"api.yookassa.ru", "api.yookassa.test", "yookassa.ru", "yookassa.test", "yoomoney.ru"}) {
        const auto provider = std::string("https://") + host + "/confirm";
        assert(policy.canStartPayment(billing, provider));
        assert(!policy.canStartPayment(origin + "/desktop/meetings", provider));
        assert(!policy.canStartPayment(origin + "/billing/unknown", provider));
        assert(!policy.canStartPayment("https://evil.test/billing", provider));
    }
    assert(policy.canStartPayment("HTTPS://REC.2BRAIN.PRO:443/billing", "HTTPS://API.YOOKASSA.RU:444/confirm"));
    for (const auto url : {"http://api.yookassa.ru/", "https://sub.yookassa.ru/", "https://yookassa.ru.evil.test/",
                          "https://user@yookassa.ru/", "https://yookassa.ru@evil.test/", "https://yookassa.ru:0/",
                          "https://yookassa.ru:65536/", "https://yookassa.ru\\@evil.test/", "javascript:alert(1)"}) {
        assert(!policy.canStartPayment(billing, url));
    }
    PaymentNavigation payment;
    assert(!payment.live(0));
    assert(payment.begin(policy, billing, "https://api.yookassa.ru/confirm", 100));
    assert(payment.live(900099));
    assert(!payment.begin(policy, billing, "https://yookassa.ru/confirm", 500)); // Never slide the deadline.
    assert(!payment.live(900100));
    assert(!payment.live(99)); // A broken clock cannot extend authority.
    assert(policy.evaluate("https://bank.test/3ds", true, AuthContinuation::none, payment.live(500)).kind == RouteKind::paymentProvider);
    assert(policy.evaluate("https://bank.test/3ds").decision == RouteDecision::openExternal);
    assert(policy.evaluate("http://bank.test/3ds", true, AuthContinuation::none, true).decision == RouteDecision::deny);
    assert(policy.evaluate("https://user@bank.test/3ds", true, AuthContinuation::none, true).decision == RouteDecision::deny);
    assert(policy.evaluate(origin + "/billing", false).decision == RouteDecision::allow);
    assert(policy.evaluate("https://bank.test/3ds", false).decision == RouteDecision::deny);
    assert(policy.evaluate("https://bank.test/3ds", false, AuthContinuation::none, true).decision == RouteDecision::allow);
    assert(policy.evaluate("https://bank.test/3ds", false, AuthContinuation::yandex).decision == RouteDecision::deny);
    payment.loaded(policy, "https://bank.test/3ds", 600);
    assert(payment.live(601));
    payment.loaded(policy, origin + "/billing", 700);
    assert(!payment.live(701));
    assert(!policy.allowsNativeBridge("https://bank.test/3ds"));
    assert(!policy.allowsNativeBridge(origin + "/login"));
    assert(!policy.allowsNativeBridge(origin + "/desktop/settings/account/email-link/verify"));
    assert(policy.allowsNativeBridge(origin + "/desktop/meetings"));

    for (const auto path : {"/login", "/login/email/start", "/login/email/verify", "/sign-up", "/sign-up/email/verify"}) {
        for (const int status : {200, 400, 401, 403, 429, 503}) {
            assert(policy.response(origin + path, {status}).decision == WebResponseDecision::interactiveForm);
        }
        assert(policy.response(origin + path, {0, false}).decision == WebResponseDecision::unavailable);
    }
    for (const auto path : {"/desktop/settings/account/email-link/start", "/desktop/settings/account/email-link/verify"}) {
        for (const int status : {400, 429, 503}) {
            assert(policy.response(origin + path, {status, true, "text/html; charset=utf-8"}).decision == WebResponseDecision::interactiveForm);
            assert(policy.response(origin + path, {status, true, "application/json"}).decision != WebResponseDecision::interactiveForm);
        }
        assert(policy.response(origin + path, {401, true, "text/html"}).decision == WebResponseDecision::expiredSession);
        assert(policy.response(origin + path, {200, true, "text/html", "reselect-space"}).decision == WebResponseDecision::workspaceReselection);
    }
    assert(policy.response(origin + "/billing", {401}).decision == WebResponseDecision::expiredSession);
    assert(policy.response(origin + "/billing", {403}).decision == WebResponseDecision::accessDenied);
    assert(policy.response(origin + "/billing", {200, true, "", "reselect-space"}).decision == WebResponseDecision::workspaceReselection);
    assert(policy.response(origin + "/billing", {503}).decision == WebResponseDecision::unavailable);
    assert(policy.response(origin + "/billing", {504}).decision == WebResponseDecision::timeout);
    assert(policy.response(origin + "/desktop/settings/account/email-link/start", {429, true, "Text/HTML ; charset=utf-8"}).decision == WebResponseDecision::interactiveForm);
    assert(policy.response(origin + "/desktop/settings/account/email-link/start", {503, false, "text/html"}).decision == WebResponseDecision::unavailable);
    assert(policy.response(origin + "/api/v1/auth/callback/google", {400}).decision != WebResponseDecision::interactiveForm);
    for (const int status : {401, 403}) {
        assert(policy.response("https://bank.test/3ds", {status}, AuthContinuation::none, true).decision == WebResponseDecision::externalDocument);
    }
    for (const auto path : {"/billing", "/billing/checkout", "/billing/checkout/status/invoice-1", "/desktop/meetings/123"}) {
        assert(policy.safeRecoveryUrl(origin + path + "?private=value#fragment", "GET") == origin + path);
        assert(policy.safeRecoveryUrl(origin + path, "POST").empty());
    }
    for (const auto path : {"/billing/checkout/start", "/billing/subscription/cancel", "/billing/discounts/apply",
                           "/billing/checkout/return", "/billing/checkout/status/invoice-1/continue", "/login",
                           "/desktop/settings/account/email-link/verify", "/desktop/meetings/123/delete"}) {
        assert(policy.safeRecoveryUrl(origin + path, "GET").empty());
    }
    assert(policy.safeRecoveryUrl("https://evil.test/billing", "GET").empty());
    assert(policy.recoveryUrl(WebResponseDecision::expiredSession, billing, true) == origin + "/login?next=%2Fbilling%2Fcheckout");
    assert(policy.recoveryUrl(WebResponseDecision::unavailable, "https://evil.test/", true) == origin + "/billing");
    assert(policy.recoveryUrl(WebResponseDecision::unavailable, "https://evil.test/", false) == origin + "/desktop/meetings");
    assert(policy.recoveryUrl(WebResponseDecision::accessDenied, billing, true) == origin + "/desktop/meetings");
}

int main() {
    paymentAndResponseContract();
    using namespace graf::windows;
    WebViewRoutePolicy policy;
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings").decision == RouteDecision::allow);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/shared-with-me").kind == RouteKind::meetings);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/123").kind == RouteKind::meetingDetail);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/123/share").kind == RouteKind::share);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/123/deletion-report").kind == RouteKind::deletionReport);
    assert(policy.evaluate("https://rec.2brain.pro/api/v1/cabinet/meetings/123/downloads/audio").kind == RouteKind::artifactDownload);
    assert(policy.evaluate("https://rec.2brain.pro/sign-up").kind == RouteKind::authRecovery);
    assert(policy.evaluate("https://rec.2brain.pro/api/v1/auth/callback/google").kind == RouteKind::authRecovery);
    assert(policy.evaluate("https://rec.2brain.pro/billing/plans").kind == RouteKind::billing);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/settings/meeting-detection").kind == RouteKind::nativeSettings);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/settings/meeting-detection-extra").kind != RouteKind::nativeSettings);
    const std::string shared = "https://rec.2brain.pro/shared-meetings/11111111-1111-4111-8111-111111111111";
    const std::string workspace = "?workspace_id=22222222-2222-4222-8222-222222222222";
    assert(policy.evaluate(shared + workspace).kind == RouteKind::meetingDetail);
    assert(policy.evaluate(shared + workspace + "#recording").decision == RouteDecision::allow);
    assert(policy.evaluate(shared + workspace + "&extra=1").decision == RouteDecision::deny);
    assert(policy.evaluate(shared + workspace + "#unknown").decision == RouteDecision::deny);
    assert(policy.evaluate(shared).decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/api/v1/cabinet/shared-meetings/11111111-1111-4111-8111-111111111111/downloads/audio" + workspace).kind == RouteKind::artifactDownload);
    const auto legal = policy.evaluate("https://rec.2brain.pro/privacy?token=private#fragment");
    assert(legal.decision == RouteDecision::openExternal && legal.normalizedUrl == "https://rec.2brain.pro/privacy");
    assert(policy.evaluate("https://rec.2brain.pro/admin").decision == RouteDecision::openExternal);
    assert(policy.evaluate("https://evil.example/desktop/meetings").decision == RouteDecision::openExternal);
    assert(policy.evaluate("file:///tmp/index.html").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/native/record").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/?next=/desktop/meetings").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/desktop/meetings/../settings").decision == RouteDecision::deny);
    assert(policy.evaluate("https://rec.2brain.pro/api/v1/cabinet/meetings/123/downloads/secret").decision == RouteDecision::deny);
    for (const auto path : {"/desktop/account", "/desktop/account/profile", "/desktop/account/security",
                           "/desktop/account/notifications", "/desktop/account/fair-use",
                           "/desktop/account/fair-use/review-123/appeal"}) {
        const auto result = policy.evaluate(std::string("https://rec.2brain.pro") + path);
        assert(result.decision == RouteDecision::allow && result.kind == RouteKind::settings);
    }
    for (const auto path : {"/desktop/account/unknown", "/desktop/account/profile/extra",
                           "/desktop/account/fair-use/appeal", "/desktop/account/fair-use//appeal",
                           "/desktop/account/fair-use/../appeal", "/desktop/account/fair-use/x/appeal/more",
                           "/desktop/account/fair-use/%2f/appeal", "/desktop/accounts/profile"}) {
        assert(policy.evaluate(std::string("https://rec.2brain.pro") + path).decision == RouteDecision::deny);
    }
    // The notification inbox and the deletion page are ordinary same-origin
    // anchors in the cabinet, so both must stay navigable. Their children are
    // not routes: the pages are exact, and a state-changing read endpoint the
    // cabinet calls with fetch() must never become a navigable document.
    for (const auto path : {"/desktop/notifications", "/notifications"}) {
        const auto result = policy.evaluate(std::string("https://rec.2brain.pro") + path);
        assert(result.decision == RouteDecision::allow && result.kind == RouteKind::meetings);
    }
    const auto deletions = policy.evaluate("https://rec.2brain.pro/desktop/deletions");
    assert(deletions.decision == RouteDecision::allow && deletions.kind == RouteKind::deletionReport);
    for (const auto path : {"/desktop/notifications/archive", "/notifications/1", "/desktop/deletions/42",
                           "/api/v1/notifications/11111111-1111-4111-8111-111111111111/read"}) {
        assert(policy.evaluate(std::string("https://rec.2brain.pro") + path).decision == RouteDecision::deny);
    }

    // Support links leave the window only as one plain address, so a page cannot
    // compose a message, copy a recipient or attach anything.
    const auto support = policy.evaluate("mailto:support@2brain.pro");
    assert(support.decision == RouteDecision::openExternal && support.kind == RouteKind::external);
    assert(support.normalizedUrl == "mailto:support@2brain.pro");
    assert(policy.evaluate("MAILTO:support@2brain.pro").normalizedUrl == "mailto:support@2brain.pro");
    for (const auto url : {"mailto:support@2brain.pro?subject=hi", "mailto:support@2brain.pro#fragment",
                           "mailto:support@2brain.pro,other@2brain.pro", "mailto:support@2brain.pro;other@2brain.pro",
                           "mailto:support@2brain.pro?cc=other@2brain.pro", "mailto:a b@2brain.pro",
                           "mailto:@2brain.pro", "mailto:support@", "mailto:a@b@c", "mailto:",
                           "mailto:support@2brain.pro\\", "javascript:alert(1)"}) {
        assert(policy.evaluate(url).decision == RouteDecision::deny);
    }
    assert(policy.evaluate("mailto:support@2brain.pro", false).decision == RouteDecision::deny);
    assert(policy.evaluate(std::string("mailto:") + std::string(300, 'a') + "@2brain.pro").decision == RouteDecision::deny);

    assert(policy.authContinuationForStart("https://rec.2brain.pro/login/yandex/start?next=/desktop/meetings") == AuthContinuation::yandex);
    assert(policy.authContinuationForStart("https://rec.2brain.pro/desktop/settings/provider-links/vk/start") == AuthContinuation::vk);
    assert(policy.authContinuationForStart("https://rec.2brain.pro/desktop/settings/provider-links/yandex/start") == AuthContinuation::yandex);
    // Login and signup share these server-rendered provider start links.
    for (const auto hint : {"vkid", "mail_ru", "ok_ru"}) {
        assert(policy.authContinuationForStart(std::string("https://rec.2brain.pro/login/vk/start?next=/desktop/meetings&auth_provider=") + hint) == AuthContinuation::vk);
        assert(policy.evaluate(std::string("https://id.vk.ru/authorize?provider=") + hint,
            true, AuthContinuation::vk).decision == RouteDecision::allow);
    }
    for (const auto url : {"https://evil.example/login/yandex/start", "https://rec.2brain.pro/login",
                          "https://rec.2brain.pro/login/google/start", "https://rec.2brain.pro/login/yandex/start/extra",
                          "https://rec.2brain.pro/desktop/meetings?next=/login/yandex/start"}) {
        assert(policy.authContinuationForStart(url) == AuthContinuation::none);
    }
    for (const auto url : {"https://oauth.yandex.ru/authorize?state=synthetic", "https://passport.yandex.ru/auth"}) {
        assert(policy.evaluate(url).decision == RouteDecision::openExternal);
        const auto result = policy.evaluate(url, true, AuthContinuation::yandex);
        assert(result.decision == RouteDecision::allow && result.kind == RouteKind::authProvider);
        assert(policy.evaluate(url, false, AuthContinuation::yandex).decision == RouteDecision::deny);
        assert(policy.evaluate(url, true, AuthContinuation::vk).decision == RouteDecision::deny);
    }
    assert(policy.evaluate("https://id.vk.ru/authorize", true, AuthContinuation::vk).kind == RouteKind::authProvider);
    for (const auto url : {"https://oauth.yandex.ru.evil.example/authorize", "https://oauth.yandex.ru@evil.example/",
                          "https://evil.example@oauth.yandex.ru/", "https://oauth.yandex.ru:444/",
                          "https://oauth.yandex.ru\\@evil.example/", "https://oauth.yandex.ru/\n",
                          "https://evil.example/", "http://oauth.yandex.ru/", "https://id.vk.ru/authorize"}) {
        assert(policy.evaluate(url, true, AuthContinuation::yandex).decision == RouteDecision::deny);
    }
    const std::string source = "https://rec.2brain.pro/desktop/meetings/123#recording";
    const std::string blob = "blob:https://rec.2brain.pro/11111111-1111-4111-8111-111111111111";
    assert(policy.isAllowedDownload(blob, source));
    assert(policy.evaluate(blob).decision == RouteDecision::deny); // download permission is not document permission
    assert(policy.isAllowedDownload("https://rec.2brain.pro/api/v1/cabinet/meetings/123/downloads/audio", source));
    assert(!policy.isAllowedDownload(blob, "https://passport.yandex.ru/auth"));
    assert(!policy.isAllowedDownload(blob, "https://rec.2brain.pro/login"));
    assert(!policy.isAllowedDownload("blob:https://evil.example/11111111-1111-4111-8111-111111111111", source));
    assert(!policy.isAllowedDownload("file:///tmp/private", source));
    assert(!policy.isAllowedDownload("https://rec.2brain.pro/desktop/settings/account", source));
    return 0;
}
