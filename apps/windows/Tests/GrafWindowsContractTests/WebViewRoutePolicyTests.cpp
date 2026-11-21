#include "../../RecApp/Web/WebViewRoutePolicy.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <utility>
#include <vector>

static void safeHistoryContract() {
    using namespace graf::windows;
    const WebViewRoutePolicy policy;
    const auto origin = policy.trustedOrigin();
    const auto list = origin + "/desktop/meetings";
    const auto detail = list + "/meeting-1";
    const auto settings = origin + "/desktop/settings";
    const auto notifications = origin + "/desktop/notifications";
    SafeHistory history;
    const auto admit = [&](std::vector<WebHistoryEntry> entries, std::size_t index,
                           const std::string& source, std::string_view method = "GET") {
        assert(history.acceptSnapshot(history.revision(), std::move(entries), index, source));
        return history.confirmCurrent(policy, history.revision(), source, method);
    };
    const auto targetIs = [&](bool back, int id) {
        const auto target = history.target(policy, back);
        return target && target->id == id;
    };
    assert(!history.current() && !history.target(policy, true) && !history.allGet(policy));
    assert(admit({{1, list}}, 0, list));
    assert(history.allGet(policy)); // No target is not quarantine.
    assert(!history.target(policy, true) && !history.target(policy, false));
    assert(admit({{1, list}, {2, detail}}, 1, detail));
    assert(targetIs(true, 1)); // Positive cases forbid an always-deny implementation.
    assert(admit({{1, list}, {2, detail}}, 0, list));
    assert(targetIs(false, 2));
    assert(admit({{1, list}, {2, detail}, {3, detail}}, 2, detail));
    assert(targetIs(true, 1)); // Nearest distinct, not a duplicate URL.
    assert(admit({{1, list}, {2, detail}, {3, detail}}, 0, list));
    assert(targetIs(false, 2));

    history.clear();
    assert(admit({{1, list}}, 0, list));
    assert(admit({{1, list}, {2, settings}}, 1, settings));
    assert(admit({{1, list}, {2, settings}, {3, notifications}}, 2, notifications));
    assert(admit({{1, list}, {2, settings}, {3, notifications}, {4, detail}}, 3, detail));
    assert(targetIs(true, 1)); // Meeting Back skips settings and the inbox.
    assert(admit({{1, list}, {2, settings}, {3, notifications}, {4, detail}}, 2, notifications));
    assert(targetIs(true, 2)); // Ordinary pages retain ordinary safe history.
    assert(targetIs(false, 4));

    // Unknown/POST anywhere, even an unrelated forward URL, quarantines ALL BF.
    assert(history.acceptSnapshot(history.revision(), {{1, list}, {2, settings}, {3, notifications},
        {4, detail}, {5, origin + "/billing"}}, 2, notifications));
    assert(!history.allGet(policy));
    assert(!history.target(policy, true) && !history.target(policy, false));
    assert(admit({{1, list}, {2, settings}, {3, notifications}, {4, detail},
        {5, origin + "/billing"}}, 4, origin + "/billing", "POST") == false);
    assert(!history.target(policy, true));
    // Renaming the unsafe entry cannot turn it into an earlier confirmed GET.
    assert(admit({{1, list}, {2, settings}, {3, notifications}, {4, detail}, {5, list}}, 3, detail));
    assert(!history.target(policy, true));
    assert(admit({{1, list}, {2, settings}, {3, notifications}, {4, detail}, {5, list},
        {6, list}}, 5, list)); // A fresh GET does not rehabilitate old POST ID 5.
    assert(!history.target(policy, true));

    // A reset snapshot alone proves nothing about a different remaining entry.
    assert(history.acceptSnapshot(history.revision(), {{7, list}}, 0, list));
    assert(!history.currentIsGet(policy));
    assert(history.confirmCurrent(policy, history.revision(), list, "GET"));
    assert(admit({{7, list}, {8, settings}}, 1, settings));
    assert(targetIs(true, 7));
    auto revision = history.revision();
    history.invalidate();
    assert(!history.allGet(policy));
    assert(!history.current() && !history.target(policy, true));
    assert(!history.acceptSnapshot(revision, {{7, list}, {8, settings}}, 1, settings));
    assert(!history.confirmCurrent(policy, revision, settings, "GET"));
    assert(admit({{7, list}, {8, settings}}, 1, settings));
    assert(targetIs(true, 7));
    // A late callback cannot overwrite a newer accepted snapshot either.
    revision = history.revision();
    assert(history.acceptSnapshot(revision, {{7, list}, {8, settings}}, 1, settings));
    assert(!history.acceptSnapshot(revision, {{7, list}}, 0, list));
    assert(!history.confirmCurrent(policy, revision, settings, "POST"));
    assert(targetIs(true, 7));
    history.forgetEntry(7); // Actual replacement, not a cancelled provisional load.
    assert(admit({{7, list}, {8, settings}}, 1, settings));
    assert(!history.target(policy, true));
    assert(admit({{7, list}, {8, settings}}, 0, list));
    assert(admit({{8, settings}}, 0, settings)); // Evicted proof cannot reappear.
    assert(admit({{7, list}, {8, settings}}, 1, settings));
    assert(!history.target(policy, true));
    assert(admit({{7, list}, {8, settings}}, 0, list));
    assert(history.acceptSnapshot(history.revision(), {{7, list + "#new"}, {8, settings}}, 1, settings));
    assert(!history.target(policy, true)); // Same ID/new URL does not inherit proof.
    assert(admit({{7, list}, {8, settings}}, 0, list));
    assert(targetIs(false, 8));
    history.clear();
    assert(admit({{7, list}, {8, settings}}, 1, settings));
    assert(!history.target(policy, true)); // Session clear removes every old proof.
    assert(admit({{7, list}, {8, settings}}, 0, list));
    assert(targetIs(false, 8));
    assert(!history.confirmCurrent(policy, history.revision(), settings, "GET"));
    assert(!history.target(policy, false)); // Response/source mismatch is not GET.

    const auto malformed = [&](std::vector<WebHistoryEntry> entries, std::size_t index,
                               const std::string& source) {
        history.clear();
        assert(admit({{1, list}}, 0, list));
        assert(admit({{1, list}, {2, settings}}, 1, settings));
        assert(targetIs(true, 1));
        assert(!history.acceptSnapshot(history.revision(), std::move(entries), index, source));
        assert(!history.current() && !history.target(policy, true));
    };
    malformed({}, 0, settings);
    malformed({{1, list}, {1, settings}}, 1, settings);
    malformed({{-1, list}}, 0, list);
    malformed({{1, list}}, 1, list);
    malformed({{1, list}}, 0, settings);
    malformed({{1, ""}}, 0, "");
    malformed({{1, list + "\n"}}, 0, list + "\n");
    malformed({{1, list + "\\"}}, 0, list + "\\");
    malformed({{1, std::string(8193, 'x')}}, 0, std::string(8193, 'x'));
    std::vector<WebHistoryEntry> oversized;
    for (int i = 0; i < 129; ++i) oversized.push_back({i, list});
    malformed(std::move(oversized), 0, list);
    history.clear();
    const auto login = origin + "/login";
    assert(history.acceptSnapshot(history.revision(), {{1, login}}, 0, login));
    assert(!history.confirmCurrent(policy, history.revision(), login, "GET"));
    assert(!history.currentIsGet(policy));
    for (const auto& ordinary : {list, origin + "/desktop/shared-with-me", origin + "/desktop/deletion-report"}) {
        history.clear();
        assert(admit({{1, settings}}, 0, settings));
        assert(admit({{1, settings}, {2, ordinary}}, 1, ordinary));
        assert(history.allGet(policy) && targetIs(true, 1));
        history.clear();
        assert(admit({{1, detail}}, 0, detail));
        assert(admit({{1, detail}, {2, settings}}, 1, settings));
        assert(admit({{1, detail}, {2, settings}, {3, ordinary}}, 2, ordinary));
        assert(targetIs(true, 2)); // Lists do not inherit the detail-only Back restriction.
    }
    for (const auto& review : {detail, origin + "/desktop/review/meeting-1", detail + "/share", detail + "/deletion-report"}) {
        history.clear();
        assert(admit({{1, list}}, 0, list));
        assert(admit({{1, list}, {2, settings}}, 1, settings));
        assert(admit({{1, list}, {2, settings}, {3, review}}, 2, review));
        assert(targetIs(true, 1));
    }
}

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

static void billingActionParityContract() {
    using namespace graf::windows;
    const WebViewRoutePolicy policy;
    const auto origin = policy.trustedOrigin();
    for (const auto path : {"/billing/storage/preview", "/billing/storage/cancel-selection",
                           "/billing/subscription/early-preview", "/billing/purchases/confirm"}) {
        const auto url = origin + path;
        const auto route = policy.evaluate(url);
        assert(route.decision == RouteDecision::allow && route.kind == RouteKind::billing);
        assert(policy.evaluate(url + "?cycle=month#summary").kind == RouteKind::billing);
        assert(policy.canStartPayment(url, "https://api.yookassa.ru/confirm"));
        assert(!policy.canStartPayment(url, "https://api.yookassa.ru.evil.test/confirm"));
        // Navigation to an action does not authorize replay after auth recovery.
        assert(policy.safeRecoveryUrl(url, "GET").empty());
        assert(policy.safeRecoveryUrl(url, "POST").empty());
        assert(policy.recoveryUrl(WebResponseDecision::expiredSession, url, true) ==
            origin + "/login?next=%2Fbilling");
        for (const auto suffix : {"/", "/extra", "-extra", "/../checkout", "/%2fextra"}) {
            const auto invalid = url + suffix;
            assert(policy.evaluate(invalid).decision == RouteDecision::deny);
            assert(!policy.allowsNativeBridge(invalid));
            assert(!policy.canStartPayment(invalid, "https://api.yookassa.ru/confirm"));
        }
        assert(policy.evaluate(origin + "/desktop" + path).decision == RouteDecision::deny);
        const auto external = std::string("https://evil.test") + path;
        assert(policy.evaluate(external).decision == RouteDecision::openExternal);
        assert(!policy.allowsNativeBridge(external));
        assert(!policy.canStartPayment(external, "https://api.yookassa.ru/confirm"));
        assert(policy.safeRecoveryUrl(external).empty());
    }
}

static void sharedMeetingReadOnlyContract() {
    using namespace graf::windows;
    const WebViewRoutePolicy policy;
    const auto origin = policy.trustedOrigin();
    const std::string token(43, 'a');
    const std::string version = "0123456789abcdef01234567";
    const auto reader = origin + "/api/v1/cabinet/public-shares/" + token;
    const std::string query = "?workspace_id=ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF";
    const auto first = policy.evaluate(reader + query);
    assert(first.decision == RouteDecision::allow && "T121_public_reader_route_must_be_allowed");

    const auto own = origin + "/desktop/meetings";
    const auto download = origin + "/api/v1/cabinet/meetings/meeting-1/downloads/audio";
    const auto blob = "blob:" + origin + "/11111111-1111-4111-8111-111111111111";
    const auto media = reader + "/playback" + query + "&media_version=" + version;
    const auto continuation = reader + "/continue" + query;
    const auto readOnly = [&](const std::string& url, bool mediaResource = false) {
        const auto route = policy.evaluate(url);
        assert(route.decision == RouteDecision::allow);
        assert(!policy.allowsNativeBridge(url));
        assert(route.kind != RouteKind::settings && route.kind != RouteKind::nativeSettings &&
            route.kind != RouteKind::authProvider && route.kind != RouteKind::paymentProvider);
        if (!mediaResource) assert(route.kind != RouteKind::artifactDownload);
        assert(!policy.isAllowedDownload(download, url));
        assert(!policy.isAllowedDownload(blob, url));
        assert(!policy.isAllowedDownload(media, url));
    };
    // Public reading is not a Save capability, even from an ordinary cabinet.
    assert(policy.allowsNativeBridge(own));
    assert(policy.isAllowedDownload(download, own));
    assert(!policy.isAllowedDownload(media, own));
    for (const auto suffix : {"", "#outcomes", "#recording", "#recording?position_ms=0",
                             "#recording?position_ms=86400000"}) {
        readOnly(reader + query + suffix);
        readOnly(reader + query + "&media_version=" + version + suffix);
    }
    readOnly(reader + "?media_version=" + version + "&workspace_id=00000000-0000-0000-0000-000000000000#outcomes");
    for (const auto length : {32, 128})
        readOnly(origin + "/api/v1/cabinet/public-shares/" + std::string(length, 'a') + query);
    readOnly(media, true);
    readOnly(origin + "/shared-meeting/continue");
    for (const auto action : {"", "&action=sign-in", "&action=sign-up"}) {
        for (const auto tab : {"", "&tab=outcomes", "&tab=recording"}) {
            readOnly(continuation + action + tab);
            readOnly(continuation + action + tab + "&media_version=" + version);
        }
        readOnly(continuation + action + "&tab=recording&position_ms=0");
        readOnly(continuation + action + "&tab=recording&position_ms=86400000&media_version=" + version);
    }
    const auto denied = [&](const std::string& url) {
        assert(policy.evaluate(url).decision == RouteDecision::deny);
        assert(!policy.allowsNativeBridge(url));
        assert(!policy.isAllowedDownload(url, own));
    };
    denied(reader);
    for (const auto suffix : {"&extra=1", "&tab=recording", "&workspace_id=00000000-0000-0000-0000-000000000000",
                             "&%77orkspace_id=00000000-0000-0000-0000-000000000000", "#unknown",
                             "#outcomes?position_ms=1", "#recording?position_ms=-1",
                             "#recording?position_ms=86400001", "#recording?position_ms=000000000"})
        denied(reader + query + suffix);
    for (const auto bad : {"", "0123456789ABCDEF01234567", "0123456789abcdef0123456",
                           "0123456789abcdef012345678"})
        denied(reader + query + "&media_version=" + bad);
    denied(reader + query + "&media_version=" + version + "&media_version=" + version);
    for (const auto length : {31, 129})
        denied(origin + "/api/v1/cabinet/public-shares/" + std::string(length, 'a') + query);
    for (const auto path : {"/extra", "/", "/../other", "/%2fextra"}) denied(reader + path + query);
    denied(reader + "/playback" + query);
    for (const auto suffix : {"#recording", "&tab=recording", "&action=sign-in", "&extra=1"}) denied(media + suffix);
    for (const auto suffix : {"#recording", "&action=other", "&action=", "&tab=other", "&tab=",
                             "&position_ms=1", "&tab=outcomes&position_ms=1",
                             "&tab=recording&position_ms=-1", "&tab=recording&position_ms=86400001",
                             "&tab=recording&position_ms=000000000", "&action=sign-in&action=sign-up",
                             "&next=/desktop/meetings", "&tab=recording&tab=outcomes"})
        denied(continuation + suffix);
    for (const auto suffix : {"?", "#", "?workspace_id=00000000-0000-0000-0000-000000000000", "#recording", "/extra"})
        denied(origin + "/shared-meeting/continue" + suffix);
    const auto pathAndQuery = reader.substr(origin.size()) + query;
    for (const auto foreign : {"https://evil.test", "https://rec.2brain.pro.evil.test", "https://rec.2brain.pro:444"}) {
        const auto url = std::string(foreign) + pathAndQuery;
        assert(policy.evaluate(url).decision != RouteDecision::allow);
        assert(!policy.allowsNativeBridge(url));
        assert(!policy.isAllowedDownload(url, own));
    }
    denied("https://user@rec.2brain.pro" + pathAndQuery);
    denied("http://rec.2brain.pro" + pathAndQuery);
    for (const auto& path : std::vector<std::string>{
        "/api/v1/cabinet/public-shares%2F" + token + "/playback",
        "/%61pi/v1/cabinet/public-shares/" + token + "/playback",
        "/api/v1/cabinet/%70ublic-shares/" + token + "/playback",
        "/api%2fv1%2fcabinet%2fpublic-shares%2f" + token + "/playback",
        "/api/v1/cabinet/public-shares%5C" + token + "/playback",
        "/ordinary/../api/v1/cabinet/public-shares/" + token,
        "/ordinary/%2e%2e/api/v1/cabinet/public-shares/" + token,
        "/api//v1/cabinet/./public-shares/" + token,
        "/api/v1/cabinet/%70ublic-shares/../other",
        "/shared%2dmeetings/00000000-0000-0000-0000-000000000000",
        "/api/v1/cabinet/shared%2Dmeetings/00000000-0000-0000-0000-000000000000/playback",
        "/shared-meeting/%63ontinue"}) {
        const auto alias = origin + path + query + "&media_version=" + version + "&extra=1";
        assert(policy.evaluate(alias, false).decision == RouteDecision::deny && "T121_noncanonical_shared_frame_must_be_denied");
        assert(policy.evaluate(alias, false, AuthContinuation::none, true).decision == RouteDecision::deny);
        assert(policy.evaluate(alias).decision == RouteDecision::deny);
        assert(!policy.allowsNativeBridge(alias) && !policy.isAllowedDownload(alias, own));
    }
    assert(policy.evaluate(origin + "/ordinary%2Fframe", false).kind == RouteKind::frame);
    assert(policy.evaluate(origin + "/ordinary/../frame", false).kind == RouteKind::frame);
    assert(policy.evaluate(origin + "/api/v1/cabinet/public-shares-other%2Fframe", false).kind == RouteKind::frame);
    assert(policy.evaluate("https://bank.test/frame", false, AuthContinuation::none, true).kind == RouteKind::frame);
}

static void sharedMeetingProtocolContract() {
    using namespace graf::windows;
    const WebViewRoutePolicy policy("https://graf.example.test");
    const std::string upper = "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF";
    const std::string lower = "abcdefab-cdef-4abc-8def-abcdefabcdef";
    const std::string nil = "00000000-0000-0000-0000-000000000000";
    const std::string token(43, 'a');
    const std::string version = "0123456789abcdef01234567";
    const std::string prefix = "grafrec://shared-meeting?";
    const auto required = "v=1&workspace_id=" + upper;
    const auto publicIntent = prefix + required + "&share_token=" + token + "&tab=outcomes";
    const auto publicRoute = "/api/v1/cabinet/public-shares/" + token + "?workspace_id=" + lower;
    const auto addressed = prefix + required + "&meeting_id=" + upper + "&tab=recording";
    const auto addressedRoute = "/shared-meetings/" + lower + "?workspace_id=" + lower;
    const auto check = [&](const std::string& uri, const std::string& expected, bool publicReader) {
        const auto route = WebViewRoutePolicy::sharedMeetingRoute(uri);
        assert(route && *route == expected);
        assert(route->front() == '/' && route->find("://") == std::string::npos);
        const auto full = policy.trustedOrigin() + *route;
        assert(policy.evaluate(full).decision == RouteDecision::allow);
        if (publicReader) {
            assert(!policy.allowsNativeBridge(full));
            assert(!policy.isAllowedDownload("blob:" + policy.trustedOrigin() + "/" + nil, full));
        }
    };
    check(publicIntent, publicRoute + "#outcomes", true);
    check("grafrec://%73hared-meeting?" + publicIntent.substr(prefix.size()), publicRoute + "#outcomes", true);
    check(publicIntent + "&media_version=" + version, publicRoute + "&media_version=" + version + "#outcomes", true);
    check(addressed, addressedRoute + "#recording", false);
    check(addressed + "&media_version=" + version + "&position_ms=00014000",
        addressedRoute + "&media_version=" + version + "#recording?position_ms=14000", false);
    for (const auto& position : {std::string("0"), std::string("86400000"), std::string("00000000")})
        check(addressed + "&position_ms=" + position,
            addressedRoute + "#recording?position_ms=" + (position == "00000000" ? "0" : position), false);
    check(prefix + "tab=outcomes&share_token=" + token + "&workspace_id=" + nil + "&v=1",
        "/api/v1/cabinet/public-shares/" + token + "?workspace_id=" + nil + "#outcomes", true);
    check(prefix + "v=1&workspace_id=" + nil + "&meeting_id=" + nil + "&tab=outcomes",
        "/shared-meetings/" + nil + "?workspace_id=" + nil + "#outcomes", false);
    for (const auto length : {32, 128}) {
        const std::string boundToken = "_-A0" + std::string(static_cast<std::size_t>(length - 4), 'z');
        check(prefix + required + "&share_token=" + boundToken + "&tab=recording&position_ms=0",
            "/api/v1/cabinet/public-shares/" + boundToken + "?workspace_id=" + lower + "#recording?position_ms=0", true);
    }
    check(prefix + "v=%31&%77orkspace_id=ABCDEFAB%2DCDEF-4ABC-8DEF-ABCDEFABCDEF&share_token=" + token + "&tab=%6futcomes",
        publicRoute + "#outcomes", true);
    const auto rejected = [&](const std::string& uri) { assert(!WebViewRoutePolicy::sharedMeetingRoute(uri)); };
    for (const auto suffix : {"&tab=recording", "&%74ab=recording", "&share_token=other", "&meeting_id=", "&position_ms=0",
                             "&next=/desktop/meetings", "&origin=https://evil.test", "&cookie=secret", "&utm_source=x",
                             "&", "&&", "&=1", "#", "#recording", "&%2574ab=recording"}) rejected(publicIntent + suffix);
    rejected(publicIntent + "&meeting_id=" + lower);
    rejected(prefix + "workspace_id=" + lower + "&share_token=" + token + "&tab=outcomes");
    rejected(prefix + "v=1&share_token=" + token + "&tab=outcomes");
    rejected(prefix + "v=1&workspace_id=" + lower + "&share_token=" + token);
    rejected(prefix + required + "&share_token=&tab=outcomes");
    for (const auto bad : {"00000000-0000-0000-0000-00000000000", "Z0000000-0000-0000-0000-000000000000", "{00000000-0000-0000-0000-000000000000}"}) {
        rejected(prefix + "v=1&workspace_id=" + bad + "&share_token=" + token + "&tab=outcomes");
        rejected(prefix + required + "&meeting_id=" + bad + "&tab=recording");
    }
    for (const auto key : {"v", "workspace_id", "meeting_id", "tab", "position_ms", "media_version"})
        rejected(addressed + "&position_ms=1&media_version=" + version + "&" + key + "=1");
    for (const auto query : {"", "?", "v=1", "v=1&workspace_id=", "v=1&tab=outcomes", "v=1&workspace_id=x&tab=outcomes",
                            "v=1&workspace_id=00000000-0000-0000-0000-000000000000&tab=outcomes"}) rejected(prefix + query);
    for (const auto authority : {"GRAFREC://shared-meeting?", "grafrec://SHARED-MEETING?", "grafrec://%2573hared-meeting?",
                                "grafrec-dev://shared-meeting?", "https://shared-meeting?", "grafrec:shared-meeting?",
                                "grafrec://other?", "grafrec://user@shared-meeting?", "grafrec://u:p@shared-meeting?",
                                "grafrec://shared-meeting:443?", "grafrec://shared-meeting/?", "grafrec://shared-meeting/extra?",
                                "grafrec://shared-meeting%2F?"}) rejected(std::string(authority) + publicIntent.substr(prefix.size()));
    for (const auto bad : {"", "2", "01", "%", "%0", "%GG", "%C0%AF", "%ED%A0%80", "%F4%90%80%80", "%00", "%0A", "%7F"})
        rejected(prefix + "v=" + bad + "&workspace_id=" + lower + "&share_token=" + token + "&tab=outcomes");
    for (const auto bad : {"", "other", "Outcomes", "outcomes+", "%256futcomes"})
        rejected(prefix + required + "&share_token=" + token + "&tab=" + bad);
    for (const auto bad : {"-1", "86400001", "99999999", "000000000", "18446744073709551616", "+1", "1.0", "1e2", ""})
        rejected(addressed + "&position_ms=" + bad);
    for (const auto bad : {"", "0123456789ABCDEF01234567", "0123456789abcdef0123456", "0123456789abcdef012345678", "%2561"})
        rejected(publicIntent + "&media_version=" + bad);
    for (const auto length : {31, 129})
        rejected(prefix + required + "&share_token=" + std::string(static_cast<std::size_t>(length), 'a') + "&tab=outcomes");
    for (const auto bad : {"+", "/", "%2F", "%252F", "%00", "%GG", "#", " "})
        rejected(prefix + required + "&share_token=" + std::string(32, 'a') + bad + "&tab=outcomes");
    rejected(prefix + "v=1&workspace_id=" + lower + "0&share_token=" + token + "&tab=outcomes");
    rejected(prefix + required + "&share_token=" + token + "&tab=outcomes&extra=" + std::string(16384, 'a'));
    rejected(std::string(16385, 'a'));
    rejected(publicIntent + std::string(1, '\0'));
    rejected(publicIntent + std::string(1, static_cast<char>(0xff)));
    check(publicIntent, publicRoute + "#outcomes", true); // Invalid calls retain no state.
}

static void sharedMeetingRecoveryContract() {
    using namespace graf::windows;
    const WebViewRoutePolicy policy("https://graf.example.test");
    const auto origin = policy.trustedOrigin();
    const std::string id = "abcdefab-cdef-4abc-8def-abcdefabcdef";
    const std::string version = "0123456789abcdef01234567";
    const auto publicPath = "/api/v1/cabinet/public-shares/" + std::string(43, 'a');
    const auto query = "?workspace_id=" + id;
    const auto publicReader = origin + publicPath + query + "&media_version=" + version + "#recording?position_ms=14000";
    assert(policy.safeRecoveryUrl(publicReader, "GET") == publicReader && "T121_shared_GET_reader_must_preserve_recovery_context");
    const std::vector<std::pair<std::string, std::string>> fragments = {
        {"", "outcomes"}, {"#outcomes", "outcomes"}, {"#recording", "recording"},
        {"#recording?position_ms=0", "recording&position_ms=0"},
        {"#recording?position_ms=86400000", "recording&position_ms=86400000"}};
    for (const auto& mediaVersion : {std::string{}, "&media_version=" + version}) {
        for (const auto& fragment : fragments) {
            const auto reader = origin + publicPath + query + mediaVersion + fragment.first;
            const auto continuation = origin + publicPath + "/continue" + query + mediaVersion + "&action=sign-in&tab=" + fragment.second;
            assert(policy.safeRecoveryUrl(reader) == reader);
            for (const auto reason : {WebResponseDecision::expiredSession, WebResponseDecision::workspaceReselection}) {
                assert(policy.recoveryUrl(reason, reader) == continuation);
                assert(policy.evaluate(continuation).decision == RouteDecision::allow);
                assert(policy.evaluate(continuation).kind == RouteKind::publicReader);
                assert(!policy.allowsNativeBridge(continuation));
                assert(continuation.find("/login?next=") == std::string::npos);
            }
            for (const auto reason : {WebResponseDecision::unavailable, WebResponseDecision::timeout})
                assert(policy.recoveryUrl(reason, reader) == reader);
            for (const auto reason : {WebResponseDecision::accessDenied, WebResponseDecision::notFound})
                assert(policy.recoveryUrl(reason, reader) == origin + "/desktop/meetings");
            assert(policy.safeRecoveryUrl(reader, "POST").empty());
            assert(policy.safeRecoveryUrl(reader, "HEAD").empty());
        }
    }
    const auto addressed = origin + "/shared-meetings/" + id + query + "&media_version=" + version + "#recording?position_ms=14000";
    const auto addressedLogin = origin + "/login?next=%2Fshared-meetings%2F" + id + "%3Fworkspace_id%3D" + id +
        "%26media_version%3D" + version + "%23recording%3Fposition_ms%3D14000";
    assert(policy.safeRecoveryUrl(addressed) == addressed);
    for (const auto reason : {WebResponseDecision::expiredSession, WebResponseDecision::workspaceReselection})
        assert(policy.recoveryUrl(reason, addressed) == addressedLogin);
    assert(policy.recoveryUrl(WebResponseDecision::timeout, addressed) == addressed);
    assert(policy.recoveryUrl(WebResponseDecision::notFound, addressed) == origin + "/desktop/meetings");
    assert(policy.safeRecoveryUrl(addressed, "POST").empty());
    const auto encodedAddressed = origin + "/shared-meetings/" + id + "?%77orkspace_id=" + id + "#outcomes";
    assert(policy.safeRecoveryUrl(encodedAddressed) == encodedAddressed);
    assert(policy.recoveryUrl(WebResponseDecision::expiredSession, encodedAddressed) ==
        origin + "/login?next=%2Fshared-meetings%2F" + id + "%3F%2577orkspace_id%3D" + id + "%23outcomes");
    for (const auto& invalid : std::vector<std::string>{
        origin + publicPath, publicReader + "&extra=1", origin + publicPath + query + "&next=/desktop/meetings",
        origin + publicPath + query + "&%6eext=/desktop/meetings", origin + publicPath + query + "#unknown",
        origin + publicPath + query + "&workspace_id=" + id,
        origin + publicPath + "/playback" + query + "&media_version=" + version,
        origin + publicPath + "/continue" + query + "&action=sign-in&tab=recording&position_ms=1",
        origin + "/shared-meeting/continue", origin + "/api/v1/cabinet/shared-meetings/" + id + "/playback" + query,
        origin + "/shared-meetings/" + id, origin + "/shared-meetings/" + id + query + "&extra=1",
        "https://evil.test" + publicPath + query,
        "https://graf.example.test:444" + publicPath + query}) {
        assert(policy.safeRecoveryUrl(invalid).empty());
        assert(policy.recoveryUrl(WebResponseDecision::unavailable, invalid) == origin + "/desktop/meetings");
        assert(policy.recoveryUrl(WebResponseDecision::expiredSession, invalid) == origin + "/login?next=%2Fdesktop%2Fmeetings");
    }
    assert(!policy.allowsNativeBridge(publicReader));
    assert(!policy.isAllowedDownload(origin + "/api/v1/cabinet/meetings/item/downloads/audio", publicReader));
}

static void retiredNotificationSettingsContract() {
    using namespace graf::windows;
    const WebViewRoutePolicy policy;
    const auto origin = policy.trustedOrigin();
    const auto notifications = origin + "/desktop/settings/notifications";
    const auto audio = origin + "/api/v1/cabinet/meetings/123/downloads/audio";
    const auto blob = "blob:" + origin + "/11111111-1111-4111-8111-111111111111";
    assert(policy.evaluate(notifications).decision == RouteDecision::allow);
    assert(policy.evaluate(notifications).kind == RouteKind::settings);
    assert(policy.allowsNativeBridge(notifications));
    assert(policy.isAllowedDownload(audio, notifications));
    assert(policy.isAllowedDownload(blob, notifications));
    // The retired Mac route is denied, not an alias for ordinary notifications.
    for (const auto path : {"/desktop/settings/notifications/mac", "/desktop/settings/notifications/mac?x=1",
                           "/desktop/settings/notifications/mac#x", "/desktop/settings/notifications/mac/",
                           "/desktop/settings/notifications/mac/child", "/desktop/settings/notifications/%6dac",
                           "/desktop/settings/notifications/../notifications/mac", "/desktop/settings/notifications%2fmac"}) {
        const auto retired = origin + path;
        const auto result = policy.evaluate(retired);
        assert(result.decision == RouteDecision::deny);
        assert(result.kind == RouteKind::denied);
        assert(!policy.allowsNativeBridge(retired));
        assert(!policy.isAllowedDownload(audio, retired));
        assert(!policy.isAllowedDownload(blob, retired));
        assert(!policy.isAllowedDownload(retired, notifications));
    }
}

int main() {
    retiredNotificationSettingsContract();
    safeHistoryContract();
    billingActionParityContract();
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
    sharedMeetingReadOnlyContract();
    sharedMeetingProtocolContract();
    sharedMeetingRecoveryContract();
    return 0;
}
