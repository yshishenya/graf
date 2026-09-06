#include "../../RecApp/Web/WebViewRoutePolicy.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
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
