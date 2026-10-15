// Regressions for the WebView2 host lifecycle (Feature 200, T080).
//
// The real control only exists in the packaged/native lane. Everything pinned
// here is the part that decides *whether* and *where* the control may be
// driven: the runtime state machine, the safe failure detail, the retry target
// and the gates a web document has to pass. Those rules must hold even when the
// browser cannot start, because that is exactly the offline case they exist for.

#ifdef NDEBUG
#undef NDEBUG
#endif

#include "../../RecApp/Web/WebView2Host.h"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using graf::windows::RouteDecision;
using graf::windows::RouteEvaluation;
using graf::windows::RouteKind;
using graf::windows::WebRuntimeState;
using graf::windows::WebView2Host;
using graf::windows::WebViewLocalRecordingRow;

constexpr const char* kTrusted = "https://rec.2brain.pro";

void testNotificationV2IsNotStoppedByRecordingV1HostGuard() {
    // The real native dispatch is behind _WIN32. Pin its wiring as well as the
    // portable parser tests; this is not a live WebView messaging test.
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path();
    std::ifstream input(root / "RecApp/Web/WebView2Host.cpp");
    assert(input.is_open());
    const std::string text{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    const auto begin = text.find("const auto request = payload.GetNamedObject(L\"request\")");
    const auto parse = text.find("NativeSettingsBridge::parseNotificationPayload(", begin);
    const auto recordingVersion = text.find("request.GetNamedNumber(L\"version\") != 1.0", begin);
    assert(begin != std::string::npos && parse != std::string::npos && recordingVersion != std::string::npos);
    assert(parse < recordingVersion); // recording-only v1 guard, after the notification branch
}

void testProtectedPlaybackWindowCallbackWiring() {
    // Source wiring only: actual WinUI callback/engine acceptance belongs to the native lane.
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path();
    std::ifstream input(root / "RecApp/AppMain.cpp"); assert(input.is_open());
    const std::string text{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    const auto begin = text.find("void showLocalPlayback()");
    const auto end = text.find("void pollLocalPlayback()", begin);
    assert(begin != std::string::npos && end != std::string::npos);
    const auto window = text.substr(begin, end - begin);
    for (const auto callback : {"playbackButton_.Click([this, generation]", "playbackSeek_.ValueChanged([this, generation]", "playbackWindow_.Closed([this, generation]", "playbackPanel_.KeyDown([this, generation]"}) {
        const auto at = window.find(callback); assert(at != std::string::npos);
        const auto guard = window.find("generation != playbackWindowGeneration_", at);
        assert(guard != std::string::npos && guard - at < 160);
    }
    assert(window.find("playbackStatus_.TextWrapping(TextWrapping::Wrap)") != std::string::npos);
    assert(window.find("TextTrimming::CharacterEllipsis") == std::string::npos);
    assert(window.find("SetLiveSetting(playbackStatus_") != std::string::npos);
    assert(window.find("scroll.VerticalScrollBarVisibility(ScrollBarVisibility::Auto)") != std::string::npos);
    assert(window.find("scroll.HorizontalScrollBarVisibility(ScrollBarVisibility::Disabled)") != std::string::npos);
    assert(window.find("scroll.BringIntoViewOnFocusChange(true)") != std::string::npos);
    assert(window.find("scroll.Content(playbackPanel_)") != std::string::npos);
    assert(window.find("playbackWindow_.Content(scroll)") != std::string::npos);
    assert(window.find("VirtualKey::Escape") != std::string::npos);
    const auto retryClick = window.find("if (state.terminal && FAILED(state.media.error))");
    assert(retryClick != std::string::npos && "protected_playback_retry_must_wait_for_actual_terminal");
    assert(window.find("pendingPlayback_ = *playbackRequest_", retryClick) != std::string::npos);
    const auto poll = text.substr(end, text.find("void handleLocalRecording(", end) - end);
    assert(poll.find("const bool retry = !pendingPlayback_ && state.terminal && FAILED(state.media.error)") != std::string::npos);
    assert(poll.find("playbackButton_.IsEnabled(usable || retry)") != std::string::npos);
    assert(poll.find("L\"Повторить\"") != std::string::npos);
    assert(poll.find("L\"Повторить открытие локальной записи\"") != std::string::npos);
    const auto dismiss = text.find("void dismissPlaybackWindow()");
    const auto invalidate = text.find("++playbackWindowGeneration_", dismiss);
    const auto close = text.find("closing.Close()", dismiss);
    assert(dismiss != std::string::npos && invalidate < close && close != std::string::npos);
    const auto handler = text.find("void handleLocalRecording(");
    assert(handler != std::string::npos && text.find("if (action == \"open\")", handler) < text.find("!capture_->localQueueComplete()", handler));
    assert(text.find("meeting-review.m4a") == std::string::npos); // No external plaintext player fallback.
}

std::string lastNavigation(std::vector<RouteEvaluation>& seen) {
    assert(!seen.empty());
    return seen.back().normalizedUrl;
}

} // namespace

void testOnlyTheThreeAppearancesTheCabinetOwnsAreAccepted() {
    using graf::windows::WebView2Host;
    // The announcement decides the appearance of native windows, so it is read as
    // strictly as macOS reads it: the three values the cabinet itself sets, and
    // nothing else. An empty or unknown value must not become an appearance.
    assert(WebView2Host::isAllowedAppearance("light"));
    assert(WebView2Host::isAllowedAppearance("dark"));
    assert(WebView2Host::isAllowedAppearance("system"));
    assert(!WebView2Host::isAllowedAppearance(""));
    assert(!WebView2Host::isAllowedAppearance("Dark"));
    assert(!WebView2Host::isAllowedAppearance("high-contrast"));
    assert(!WebView2Host::isAllowedAppearance("light; rm -rf"));
}

void testTheSessionCookieIsExtendedOnlyOnTheAppsOwnTerms() {
    using graf::windows::WebView2Host;
    // The deadline the server named goes onto the cabinet's session cookie, but
    // only while that cookie still holds the token the request used and only for
    // a deadline in the future. macOS rewrites the same cookie under the same
    // three conditions.
    assert(WebView2Host::authCookieShouldBeExtended("token", "token", 2'000'000'000, 1'900'000'000));
    // A cookie that already changed belongs to another session.
    assert(!WebView2Host::authCookieShouldBeExtended("other", "token", 2'000'000'000, 1'900'000'000));
    // No token means the app is not holding the session the deadline is for.
    assert(!WebView2Host::authCookieShouldBeExtended("token", "", 2'000'000'000, 1'900'000'000));
    assert(!WebView2Host::authCookieShouldBeExtended("", "", 2'000'000'000, 1'900'000'000));
    // A deadline that has passed would shorten a session the server extended.
    assert(!WebView2Host::authCookieShouldBeExtended("token", "token", 1'800'000'000, 1'900'000'000));
    assert(!WebView2Host::authCookieShouldBeExtended("token", "token", 1'900'000'000, 1'900'000'000));
}

void testDocumentResponseLatch() {
    using namespace graf::windows;
    const auto url = std::string(kTrusted) + "/desktop/meetings/123";
    for (const bool responseFirst : {false, true}) {
        for (const bool reselect : {false, true}) {
            WebView2Host host;
            int logouts = 0;
            host.setAuthSessionHandler([&](std::string) { ++logouts; });
            (void)host.beginDocumentNavigation(url, 1, false, 0, "");
            // Request tagging has no dependency on early browser headers.
            const auto tag = host.documentRequestTag(url);
            assert(!tag.empty());
            assert(host.documentRequestTag("https://bank.test/3ds").empty());
            const WebDocumentResponse metadata{200, true, "text/html", reselect ? "reselect-space" : ""};
            const auto response = [&] {
                assert(host.observeDocumentResponseHeaders(url, tag, "document", "GET", metadata));
            };
            if (responseFirst) response();
            assert(host.tryFinishDocumentNavigation(1) == WebResponseDecision::ignore);
            assert(host.observeDocumentCompletion(url, 1, 200, true, false, 2));
            if (!responseFirst) {
                assert(host.tryFinishDocumentNavigation(3) == WebResponseDecision::ignore);
                assert(host.runtimeState() == WebRuntimeState::initializing && logouts == 0);
                response();
            }
            assert(host.tryFinishDocumentNavigation(4) ==
                (reselect ? WebResponseDecision::workspaceReselection : WebResponseDecision::cabinet));
            assert(logouts == (reselect ? 1 : 0));
            assert(host.tryFinishDocumentNavigation(5) == WebResponseDecision::ignore);
            assert(!host.observeDocumentResponseHeaders(url, tag, "document", "GET", metadata));
        }
    }
    {
        WebView2Host host;
        (void)host.beginDocumentNavigation(url, 1, false, 0, "");
        const auto oldTag = host.documentRequestTag(url);
        assert(host.observeDocumentCompletion(url, 1, 200, true, false, 1));
        (void)host.beginDocumentNavigation(url, 2, false, 2, "");
        const auto tag = host.documentRequestTag(url);
        assert(tag != oldTag);
        assert(!host.observeDocumentCompletion(url, 1, 200, true, false, 3));
        assert(!host.observeDocumentResponseHeaders(url, oldTag, "document", "GET", {200, true, "", "reselect-space"}));
        for (const auto dest : {"iframe", "frame", "empty", ""})
            assert(!host.observeDocumentResponseHeaders(url, tag, dest, "GET", {200}));
        for (const auto& badTag : {std::string{}, oldTag, tag + "x", "-" + tag})
            assert(!host.observeDocumentResponseHeaders(url, badTag, "document", "GET", {200}));
        assert(!host.observeDocumentResponseHeaders(url + "/other", tag, "document", "GET", {200}));
        assert(host.tryFinishDocumentNavigation(6000) == WebResponseDecision::ignore); // No old timer ownership.
        assert(host.observeDocumentCompletion(url, 2, 200, true, false, 6001));
        assert(!host.observeDocumentCompletion(url, 2, 200, true, false, 10999)); // Cannot slide the deadline.
        assert(host.tryFinishDocumentNavigation(11000) == WebResponseDecision::ignore);
        assert(host.tryFinishDocumentNavigation(11001) == WebResponseDecision::unavailable);
        assert(host.failureDetail().find("response-metadata-timeout") == 0);
        assert(!host.observeDocumentResponseHeaders(url, tag, "document", "GET", {200}));
        assert(host.tryFinishDocumentNavigation(11002) == WebResponseDecision::ignore);
    }
    {
        WebView2Host host;
        (void)host.beginDocumentNavigation(url, 7, false, 0, "");
        const auto oldTag = host.documentRequestTag(url);
        // Redirects retain NavigationId but must not retain the response tag.
        (void)host.beginDocumentNavigation(url, 7, true, 1, "");
        const auto tag = host.documentRequestTag(url);
        assert(tag != oldTag);
        assert(!host.observeDocumentResponseHeaders(url, oldTag, "document", "GET", {200}));
        assert(host.observeDocumentCompletion(url, 7, 200, true, false, 2));
        assert(host.observeDocumentResponseHeaders(url, tag, "document", "GET", {200}));
        assert(host.tryFinishDocumentNavigation(5002) == WebResponseDecision::unavailable); // A late callback cannot beat timeout.
        (void)host.beginDocumentNavigation(url, 8, false, 5003, "");
        assert(host.observeDocumentCompletion(std::string(kTrusted) + "/billing", 8, 200, true, false, 5004));
        assert(host.tryFinishDocumentNavigation(5004) == WebResponseDecision::blocked);
    }
    {
        WebView2Host host;
        const auto login = std::string(kTrusted) + "/login/email/verify";
        (void)host.beginDocumentNavigation(login, 1, false, 0, "");
        const auto tag = host.documentRequestTag(login);
        assert(host.observeDocumentCompletion(login, 1, 400, false, true, 1));
        assert(host.tryFinishDocumentNavigation(2) == WebResponseDecision::ignore);
        assert(host.observeDocumentResponseHeaders(login, tag, "document", "POST", {400, true, "text/html"}));
        assert(host.tryFinishDocumentNavigation(3) == WebResponseDecision::interactiveForm);
        (void)host.beginDocumentNavigation(url, 2, false, 4, "");
        assert(host.observeDocumentCompletion(url, 2, 0, false, false, 5));
        assert(host.tryFinishDocumentNavigation(5) == WebResponseDecision::unavailable); // TLS/network needs no metadata wait.
        (void)host.beginDocumentNavigation(url, 3, false, 6, "");
        assert(host.observeDocumentCompletion(url, 3, 200, true, false, 7));
        host.close();
        assert(host.tryFinishDocumentNavigation(6000) == WebResponseDecision::ignore);
    }
}

void testHttpErrorDocumentGate() {
    using namespace graf::windows;
    const auto login = std::string(kTrusted) + "/login";
    const auto email = std::string(kTrusted) + "/desktop/settings/account/email-link/start";
    for (const bool headersFirst : {false, true}) {
        for (const int status : {400, 429, 503}) {
            for (const auto& target : {login, email}) {
                WebView2Host host;
                (void)host.beginDocumentNavigation(target, 1, false, 0, "");
                const auto tag = host.documentRequestTag(target);
                if (headersFirst)
                    assert(host.observeDocumentResponseHeaders(target, tag, "document", "POST", {status, true, "text/html"}));
                assert(host.observeDocumentCompletion(target, 1, status, false, true, 1));
                if (!headersFirst) {
                    assert(host.tryFinishDocumentNavigation(2) == WebResponseDecision::ignore);
                    assert(!host.observeDocumentResponseHeaders(target, tag, "iframe", "POST", {status, true, "text/html"}));
                    assert(host.observeDocumentResponseHeaders(target, tag, "document", "POST", {status, true, "text/html"}));
                }
                assert(host.tryFinishDocumentNavigation(3) == WebResponseDecision::interactiveForm);
                assert(host.runtimeState() != WebRuntimeState::ready);
            }
        }
    }
    for (const int status : {0, 200, 400, 503}) {
        WebView2Host host;
        (void)host.beginDocumentNavigation(login, 1, false, 0, "");
        assert(host.observeDocumentResponseHeaders(login, host.documentRequestTag(login), "document", "GET", {status, true, "text/html"}));
        // A known transport/cancellation error cannot become a form solely
        // because response headers or an HTTP error status were observed.
        assert(host.observeDocumentCompletion(login, 1, status, false, false, 1));
        assert(host.tryFinishDocumentNavigation(2) == WebResponseDecision::unavailable);
    }
    WebView2Host missing;
    (void)missing.beginDocumentNavigation(login, 1, false, 0, "");
    assert(missing.observeDocumentCompletion(login, 1, 400, false, true, 1));
    assert(missing.tryFinishDocumentNavigation(2) == WebResponseDecision::ignore);
    assert(missing.tryFinishDocumentNavigation(5001) == WebResponseDecision::unavailable);
}

void testAuthRecoveryPresentation() {
    using namespace graf::windows;
    for (const bool reselect : {false, true}) {
        WebView2Host host;
        const auto page = std::string(kTrusted) + "/billing/checkout?source=synthetic#details";
        assert(host.pendingAuthRecovery() == WebResponseDecision::ignore);
        int cleared = 0;
        host.setAuthSessionHandler([&](std::string value) { assert(value.empty()); ++cleared; });
        (void)host.beginDocumentNavigation(page, 1, false, 0, "GET");
        const auto reason = reselect ? WebResponseDecision::workspaceReselection : WebResponseDecision::expiredSession;
        assert(host.completeDocumentNavigation(page, 1,
            {reselect ? 503 : 401, true, "text/html", reselect ? "reselect-space" : ""}, 1) == reason);
        assert(cleared == 1 && host.pendingAuthRecovery() == reason);
        assert(host.runtimeState() == WebRuntimeState::authRequired);
        assert(host.currentUrl() == page);
        const auto target = host.recoveryUrl();
        assert(target == std::string(kTrusted) + "/login?next=%2Fbilling%2Fcheckout");
        // The native button chooses the validated GET target, not reload of the failed action.
        assert(host.navigate(target).decision == RouteDecision::allow);
        (void)host.beginDocumentNavigation(target, 2, false, 2, "GET");
        assert(host.pendingAuthRecovery() == WebResponseDecision::ignore);
        assert(host.completeDocumentNavigation(target, 2, {429, true, "text/html"}, 3) == WebResponseDecision::interactiveForm);
        assert(host.runtimeState() == WebRuntimeState::authRequired);
        assert(host.pendingAuthRecovery() == WebResponseDecision::ignore); // Do not cover the working form.
        assert(cleared == 1);
        host.close();
        assert(host.pendingAuthRecovery() == WebResponseDecision::ignore);
    }
}

void testProcessFailureRecovery() {
    using namespace graf::windows;
    const auto url = std::string(kTrusted) + "/desktop/meetings";
    for (const auto state : {WebRuntimeState::ready, WebRuntimeState::initializing,
                            WebRuntimeState::authRequired, WebRuntimeState::unprivileged}) {
        WebView2Host host;
        host.setRuntimeState(state);
        int changes = 0;
        host.setRuntimeHandler([&](auto) { ++changes; });
        host.handleProcessFailure(WebProcessFailure::automaticallyRecoverable, 123);
        assert(host.runtimeState() == state && changes == 0);
        assert(host.failureDetail().empty());
    }
    // A GPU restart during navigation must not discard the real response latch.
    {
        WebView2Host host;
        (void)host.beginDocumentNavigation(url, 1, false, 0, "");
        const auto tag = host.documentRequestTag(url);
        host.handleProcessFailure(WebProcessFailure::automaticallyRecoverable, 0);
        assert(host.observeDocumentCompletion(url, 1, 200, true, false, 1));
        assert(host.observeDocumentResponseHeaders(url, tag, "document", "GET", {200}));
        assert(host.tryFinishDocumentNavigation(2) == WebResponseDecision::cabinet);
    }
    for (const auto failure : {WebProcessFailure::browserExited, WebProcessFailure::renderExited,
                              WebProcessFailure::renderUnresponsive, WebProcessFailure::frameRenderExited}) {
        WebView2Host host;
        (void)host.beginDocumentNavigation(url, 1, false, 0, "");
        const auto tag = host.documentRequestTag(url);
        int recreations = 0;
        host.setRecreateHandler([&] { ++recreations; });
        host.handleProcessFailure(failure, static_cast<std::int32_t>(0xC0000005u));
        assert(host.runtimeState() == WebRuntimeState::unavailable);
        assert(host.failureDetail().find("0xC0000005") != std::string::npos);
        assert(!host.observeDocumentResponseHeaders(url, tag, "document", "GET", {200}));
        assert(!host.observeDocumentCompletion(url, 1, 200, true, false, 1));
        host.reload();
        assert(recreations == (failure == WebProcessFailure::browserExited ? 1 : 0));
        host.close();
        host.handleProcessFailure(failure, 0);
        assert(host.runtimeState() == WebRuntimeState::closed);
    }
}

void testPaymentPopupAdmissionAndLifetime() {
    using namespace graf::windows;
    const std::string billing = std::string(kTrusted) + "/billing";
    const auto loadBilling = [&](WebView2Host& host) {
        assert(host.beginDocumentNavigation(billing, 1, false, 0).decision == RouteDecision::allow);
        assert(host.completeDocumentNavigation(billing, 1, {200}, 1) == WebResponseDecision::cabinet);
        host.setRuntimeState(WebRuntimeState::ready);
    };
    for (const auto target : {"https://api.yookassa.ru/confirm", "https://rec.2brain.pro/billing/checkout/start"}) {
        WebView2Host host;
        loadBilling(host);
        WebView2Host::PopupSource source{host.documentGeneration(), 7, 7, true};
        int cleanups = 0;
        assert(host.beginPaymentPopup(target, source, 100, [&] { ++cleanups; }));
        assert(host.runtimeState() == WebRuntimeState::unprivileged);
        assert(host.canGoBack());
        assert(!host.canGoForward());
        assert(!host.localRecordingActionAllowed("send", "any"));
        assert(!host.beginPaymentPopup(target, source, 101, [] {})); // one owned child
        assert(host.handOffPaymentPopup(source, 102));
        assert(!host.handOffPaymentPopup(source, 103)); // no repeated NewWindow assignment
        assert(host.evaluatePaymentPopupDocument(target, 104).decision == RouteDecision::allow);
        assert(host.evaluatePaymentPopupDocument("https://api.yookassa.ru/confirm", 105).decision == RouteDecision::allow);
        assert(host.evaluatePaymentPopupDocument("https://bank.test/3ds", 106).decision == RouteDecision::allow);
        assert(host.paymentNavigationAllowedAt(106));
        assert(host.evaluatePaymentPopupDocument(billing, 107).decision == RouteDecision::allow);
        assert(!host.paymentNavigationAllowedAt(107)); // return ends external authority before load
        assert(host.evaluatePaymentPopupDocument("https://bank.test/again", 108).decision == RouteDecision::deny);
        host.cancelPaymentPopup();
        host.close();
        assert(cleanups == 1);
    }
    // URL equality cannot prove a main-frame source, even for a same-origin iframe.
    for (int invalid = 0; invalid != 5; ++invalid) {
        WebView2Host host;
        loadBilling(host);
        WebView2Host::PopupSource proof{host.documentGeneration(), 7, 7, true};
        if (invalid == 0) proof.isMainFrame = false;
        if (invalid == 1) proof.frameId = 0;
        if (invalid == 2) proof.coreFrameId = 0;
        if (invalid == 3) proof.frameId = 8;
        if (invalid == 4) ++proof.documentGeneration;
        assert(!host.beginPaymentPopup("https://yookassa.ru/pay", proof, 100, [] {}));
        assert(host.runtimeState() == WebRuntimeState::ready);
    }
    for (const auto url : {"about:blank", "https://bank.test/first", "https://yookassa.ru.evil.test/pay",
             "http://yookassa.ru/pay", "https://user@yookassa.ru/pay", "file:///checkout"}) {
        WebView2Host host;
        loadBilling(host);
        assert(!host.beginPaymentPopup(url, {host.documentGeneration(), 7, 7, true}, 100, [] {}));
    }
    for (int interruption = 0; interruption != 6; ++interruption) {
        WebView2Host host;
        loadBilling(host);
        const WebView2Host::PopupSource proof{host.documentGeneration(), 7, 7, true};
        int cleanups = 0;
        assert(host.beginPaymentPopup("https://yookassa.ru/pay", proof, 100, [&] { ++cleanups; }));
        if (interruption == 0) (void)host.beginDocumentNavigation(billing, 2, false, 101);
        if (interruption == 1) host.close();
        if (interruption == 2) host.handleProcessFailure(WebProcessFailure::renderExited, 0);
        if (interruption == 3) host.setRuntimeState(WebRuntimeState::authRequired);
        if (interruption == 4) assert(!host.handOffPaymentPopup(proof, 900100));
        if (interruption == 5) assert(!host.handOffPaymentPopup({proof.documentGeneration, 8, 8, true}, 101));
        if (interruption >= 4) {
            assert(host.runtimeState() == WebRuntimeState::unavailable);
            assert(host.failureDetail().find("payment-popup-binding") == 0);
            assert(!host.localRecordingActionAllowed("send", "any"));
        }
        assert(!host.handOffPaymentPopup(proof, 102));
        host.cancelPaymentPopup();
        assert(cleanups == 1);
        assert(!host.paymentNavigationAllowedAt(102));
    }
    {
        WebView2Host host;
        loadBilling(host);
        const WebView2Host::PopupSource old{host.documentGeneration(), 7, 7, true};
        assert(host.beginPaymentPopup("https://yookassa.ru/pay", old, 100, [] {}));
        (void)host.beginDocumentNavigation(billing, 2, false, 101);
        assert(host.completeDocumentNavigation(billing, 2, {200}, 102) == WebResponseDecision::cabinet);
        host.setRuntimeState(WebRuntimeState::ready);
        const WebView2Host::PopupSource current{host.documentGeneration(), 9, 9, true};
        int currentCleanups = 0;
        assert(host.beginPaymentPopup("https://yookassa.ru/pay", current, 103, [&] { ++currentCleanups; }));
        assert(!host.handOffPaymentPopup(old, 104));
        assert(currentCleanups == 0 && host.failureDetail().empty());
        assert(host.handOffPaymentPopup(current, 105));
        assert(!host.localRecordingActionAllowed("send", "any"));
        host.close();
        assert(currentCleanups == 1);
    }
    for (const bool reload : {false, true}) {
        WebView2Host host;
        loadBilling(host);
        int cleanups = 0;
        std::vector<RouteEvaluation> navigations;
        host.setNavigationHandler([&](RouteEvaluation route) { navigations.push_back(std::move(route)); });
        assert(host.beginPaymentPopup("https://yookassa.ru/pay", {host.documentGeneration(), 7, 7, true}, 100, [&] { ++cleanups; }));
        host.forward();
        assert(navigations.empty());
        if (reload) host.reload(); else host.back();
        assert(cleanups == 1 && navigations.size() == 1);
        assert(navigations.front().normalizedUrl == billing);
    }
    {
        WebView2Host host;
        loadBilling(host);
        const WebView2Host::PopupSource proof{host.documentGeneration(), 7, 7, true};
        int cleanups = 0;
        assert(host.beginPaymentPopup("https://rec.2brain.pro/billing/checkout/start", proof, 100, [&] { ++cleanups; }));
        assert(host.handOffPaymentPopup(proof, 101));
        // Same-origin checkout is not a licence for a first arbitrary bank hop.
        assert(host.evaluatePaymentPopupDocument("https://bank.test/first", 102).decision == RouteDecision::deny);
        assert(cleanups == 1);
        assert(!host.paymentNavigationAllowedAt(102));
    }
}

void testNestedPaymentPopupKeepsOriginalDeadline() {
    using namespace graf::windows;
    WebView2Host host;
    const auto billing = std::string(kTrusted) + "/billing";
    (void)host.beginDocumentNavigation(billing, 1, false, 0);
    (void)host.completeDocumentNavigation(billing, 1, {200}, 1);
    host.setRuntimeState(WebRuntimeState::ready);
    const auto generation = host.documentGeneration();
    int parentCleanup = 0, childCleanup = 0;
    assert(host.beginPaymentPopup("https://yookassa.ru/pay", {generation, 7, 7, true}, 100, [&] { ++parentCleanup; }));
    assert(host.handOffPaymentPopup({generation, 7, 7, true}, 101));
    assert(host.paymentPopupChildCurrent(generation, 1, 101));
    assert(!host.bindPaymentPopupFrame(0, generation, 1, 101));
    assert(!host.bindPaymentPopupFrame(11, generation + 1, 1, 101));
    assert(host.bindPaymentPopupFrame(11, generation, 1, 101));
    assert(host.evaluatePaymentPopupDocument("https://yookassa.ru/pay", 102).decision == RouteDecision::allow);
    assert(!host.beginPaymentPopup("https://bank.test/3ds", {generation, 7, 7, true}, 200, [] {}));
    assert(!host.beginPaymentPopup("https://bank.test/3ds", {generation, 12, 11, false}, 200, [] {}));
    assert(host.beginPaymentPopup("https://bank.test/3ds", {generation, 11, 11, true}, 900098, [&] { ++childCleanup; }));
    assert(host.handOffPaymentPopup({generation, 11, 11, true}, 900099));
    assert(!host.paymentPopupChildCurrent(generation, 1, 900099));
    assert(!host.bindPaymentPopupFrame(11, generation, 1, 900099));
    assert(host.paymentPopupChildCurrent(generation, 2, 900099));
    // Replacing the active child revokes the previous opener immediately, even
    // before the new child's first ContentLoading supplies a positive frame ID.
    assert(!host.beginPaymentPopup("https://bank.test/stale", {generation, 11, 11, true}, 900099, [] {}));
    assert(host.bindPaymentPopupFrame(17, generation, 2, 900099));
    assert(!host.bindPaymentPopupFrame(11, generation, 1, 900099));
    assert(host.paymentPopupLiveAt(900099));
    assert(!host.paymentPopupLiveAt(900100));
    assert(host.evaluatePaymentPopupDocument("https://bank.test/next", 900100).decision == RouteDecision::deny);
    assert(parentCleanup == 1 && childCleanup == 1);
    host.close();
    assert(!host.bindPaymentPopupFrame(17, generation, 2, 900099));
    assert(parentCleanup == 1 && childCleanup == 1);
}

void testLatePopupReturnKeepsParentDeadline() {
    using namespace graf::windows;
    WebView2Host host;
    const auto billing = std::string(kTrusted) + "/billing";
    const std::string provider = "https://yookassa.ru/pay";
    (void)host.beginDocumentNavigation(billing, 1, false, 0);
    assert(host.completeDocumentNavigation(billing, 1, {200}, 1) == WebResponseDecision::cabinet);
    host.setRuntimeState(WebRuntimeState::ready);
    assert(host.beginDocumentNavigation(provider, 2, false, 100).decision == RouteDecision::allow);
    assert(host.completeDocumentNavigation(provider, 2, {200}, 101) == WebResponseDecision::externalDocument);
    const WebView2Host::PopupSource source{host.documentGeneration(), 7, 7, true};
    int cleanups = 0;
    assert(host.beginPaymentPopup("https://bank.test/3ds", source, 899000, [&] { ++cleanups; }));
    assert(host.handOffPaymentPopup(source, 899001));
    assert(host.bindPaymentPopupFrame(11, source.documentGeneration, 1, 899002));
    assert(host.evaluatePaymentPopupDocument(billing, 899999).decision == RouteDecision::allow);
    assert(!host.paymentNavigationAllowedAt(899999)); // Return stopped external authority.
    assert(host.paymentPopupLiveAt(899999));
    assert(!host.paymentPopupLiveAt(900100)); // But must not reset the parent's clock.
    assert(host.evaluatePaymentPopupDocument(billing, 900100).decision == RouteDecision::deny);
    assert(cleanups == 1);
    host.close();
    assert(cleanups == 1);
}

int main() {
    testLatePopupReturnKeepsParentDeadline();
    testNestedPaymentPopupKeepsOriginalDeadline();
    testPaymentPopupAdmissionAndLifetime();
    testNotificationV2IsNotStoppedByRecordingV1HostGuard();
    testProtectedPlaybackWindowCallbackWiring();
    testHttpErrorDocumentGate();
    testAuthRecoveryPresentation();
    testProcessFailureRecovery();
    testDocumentResponseLatch();
    {
        // WebView2's popup event does not carry a reusable request body. Both a
        // provider popup and a same-origin checkout POST must fail explicitly,
        // never become Navigate(Uri) GET or an external-browser handoff.
        using namespace graf::windows;
        for (const auto target : {"https://api.yookassa.ru/confirm", "https://rec.2brain.pro/billing/checkout/start"}) {
            WebView2Host host;
            const auto billing = std::string(kTrusted) + "/billing";
            (void)host.beginDocumentNavigation(billing, 1, false, 0);
            (void)host.completeDocumentNavigation(billing, 1, {200}, 1);
            assert(host.evaluatePopupNavigation(target, 2).decision == RouteDecision::deny);
            assert(host.failureDetail().find("payment-popup-request-unavailable") == 0);
            assert(!host.paymentNavigationAllowedAt(2));
        }
    }
    // T102/T103 use the same event transitions as the native adapter, with an
    // injected monotonic clock. No browser, network, cookie or payment fixture.
    {
        using namespace graf::windows;
        WebView2Host host;
        const std::string billing = std::string(kTrusted) + "/billing/checkout";
        int logoutCalls = 0;
        host.setAuthSessionHandler([&](std::string token) { if (token.empty()) ++logoutCalls; });
        assert(host.beginDocumentNavigation(billing, 1, false, 0).decision == RouteDecision::allow);
        assert(host.completeDocumentNavigation(billing, 1, {200}, 1) == WebResponseDecision::cabinet);
        const auto start = std::string(kTrusted) + "/billing/checkout/start";
        assert(host.beginDocumentNavigation(start, 2, false, 2).decision == RouteDecision::allow);
        assert(host.beginDocumentNavigation("https://api.yookassa.ru/confirm", 2, true, 3).kind == RouteKind::paymentProvider);
        assert(host.completeDocumentNavigation("https://api.yookassa.ru/confirm", 2, {200}, 4) == WebResponseDecision::externalDocument);
        assert(host.runtimeState() == WebRuntimeState::unprivileged);
        assert(host.beginDocumentNavigation("https://bank.test/3ds", 3, false, 5).kind == RouteKind::paymentProvider);
        assert(host.completeDocumentNavigation("https://bank.test/3ds", 3, {200}, 6) == WebResponseDecision::externalDocument);
        assert(logoutCalls == 0);
        assert(host.safeRecoveryUrl() == billing);
        assert(!host.localRecordingActionAllowed("send", "any"));
        // A replaced navigation cannot clear a live payment or install a bridge.
        assert(host.completeDocumentNavigation(billing, 1, {200}, 7) == WebResponseDecision::ignore);
        assert(host.paymentNavigationAllowedAt(8));
        (void)host.beginDocumentNavigation("https://bank.test/error", 33, false, 8);
        assert(host.completeDocumentNavigation("https://bank.test/error", 33, {401}, 8) == WebResponseDecision::externalDocument);
        assert(logoutCalls == 0 && !host.paymentNavigationAllowedAt(8));
        assert(host.beginDocumentNavigation(billing, 4, false, 9).decision == RouteDecision::allow);
        assert(host.completeDocumentNavigation(billing, 4, {401}, 10) == WebResponseDecision::expiredSession);
        assert(!host.paymentNavigationAllowedAt(11));
        assert(logoutCalls == 1);
        const auto login = host.recoveryUrl();
        assert(login == std::string(kTrusted) + "/login?next=%2Fbilling%2Fcheckout");
        assert(host.beginDocumentNavigation(login, 5, false, 12).decision == RouteDecision::allow);
        assert(host.completeDocumentNavigation(login, 5, {429}, 13) == WebResponseDecision::interactiveForm);
        assert(host.runtimeState() == WebRuntimeState::authRequired);
        assert(host.safeRecoveryUrl() == billing);
        assert(host.beginDocumentNavigation(billing, 6, false, 14).decision == RouteDecision::allow);
        assert(host.completeDocumentNavigation(billing, 6, {403}, 15) == WebResponseDecision::accessDenied);
        assert(logoutCalls == 1); // No fake logout for cabinet 403 either.
        assert(host.recoveryUrl() == std::string(kTrusted) + "/desktop/meetings");
    }
    {
        using namespace graf::windows;
        WebView2Host host;
        const auto billing = std::string(kTrusted) + "/billing";
        (void)host.beginDocumentNavigation(billing, 1, false, 0);
        (void)host.completeDocumentNavigation(billing, 1, {200}, 1);
        (void)host.beginDocumentNavigation("https://yookassa.ru/confirm", 2, false, 100);
        (void)host.completeDocumentNavigation("https://yookassa.ru/confirm", 2, {200}, 101);
        assert(host.paymentNavigationAllowedAt(900099));
        assert(host.beginDocumentNavigation("https://bank.test/3ds", 3, true, 900100).decision == RouteDecision::deny);
        assert(!host.paymentNavigationAllowedAt(900100));
        assert(host.runtimeState() == WebRuntimeState::unavailable);
        host.close();
        assert(!host.paymentNavigationAllowedAt(101));
    }
    {
        using namespace graf::windows;
        WebView2Host host;
        const auto detail = std::string(kTrusted) + "/desktop/meetings/123";
        (void)host.beginDocumentNavigation(detail, 1, false, 0);
        (void)host.completeDocumentNavigation(detail, 1, {200}, 1);
        (void)host.beginDocumentNavigation(std::string(kTrusted) + "/billing/checkout/start", 2, false, 2);
        (void)host.completeDocumentNavigation(std::string(kTrusted) + "/billing/checkout/start", 2, {503}, 3);
        // A payment action is never replayed by recovery, even if native code
        // tries to navigate to it as a GET.
        assert(host.recoveryUrl().find("/checkout/start") == std::string::npos);
    }
    testTheSessionCookieIsExtendedOnlyOnTheAppsOwnTerms();
    {
        WebView2Host host;
        const auto billing = std::string(kTrusted) + "/billing/checkout";
        (void)host.navigate(billing);
        const auto plain = std::string(kTrusted) + "/login?next=%2Fbilling%2Fcheckout";
        assert(host.signInUrl() == plain);
        host.setSignInUrlBuilder([](std::string_view url) { return std::string(url) + "&utm_source=synthetic"; });
        assert(host.signInUrl() == plain + "&utm_source=synthetic");
        for (const auto suffix : {"&next=https://evil.test", "&%6eext=/billing", "#fragment", "&workspace_id=other"}) {
            host.setSignInUrlBuilder([suffix](std::string_view url) { return std::string(url) + suffix; });
            assert(host.signInUrl() == plain);
        }
        host.setSignInUrlBuilder([](std::string_view) { return std::string("https://evil.test/login"); });
        assert(host.signInUrl() == plain);
        host.setSignInUrlBuilder([](std::string_view) -> std::string { throw std::runtime_error("optional decoration failed"); });
        assert(host.signInUrl() == plain);
    }
    {
        using namespace graf::windows;
        WebView2Host host;
        const auto detail = std::string(kTrusted) + "/desktop/meetings/123";
        (void)host.beginDocumentNavigation(detail, 1, false, 0, "");
        const auto oldGeneration = host.documentGeneration();
        (void)host.beginDocumentNavigation(detail, 2, false, 1, "");
        assert(!host.observeDocumentResponse(detail, oldGeneration, "GET", {200, true, "", "reselect-space"}));
        assert(!host.observeDocumentResponse("https://bank.test/3ds", host.documentGeneration(), "GET", {200}));
        assert(host.observeDocumentResponse(detail, host.documentGeneration(), "POST", {200}));
        assert(host.safeRecoveryUrl().empty()); // Unknown/POST never becomes a retry document.
        (void)host.completeDocumentNavigation(detail, 2, {200}, 2);
        assert(!host.observeDocumentResponse(detail, host.documentGeneration(), "GET", {200}));
        (void)host.beginDocumentNavigation(detail, 3, false, 3, "");
        assert(host.observeDocumentResponse(detail, host.documentGeneration(), "GET", {200}));
        assert(host.safeRecoveryUrl() == detail);
        (void)host.completeDocumentNavigation(detail, 3, {200}, 4);
        const auto login = std::string(kTrusted) + "/login";
        (void)host.beginDocumentNavigation(login, 4, false, 5);
        // A login document's history.replaceState cannot turn its completion
        // into authority for a different cabinet page with the same nav id.
        assert(host.completeDocumentNavigation(detail, 4, {200}, 6) == WebResponseDecision::blocked);
    }
    {
        using namespace graf::windows;
        WebView2Host host;
        const auto billing = std::string(kTrusted) + "/billing";
        (void)host.beginDocumentNavigation(billing, 1, false, 0);
        (void)host.completeDocumentNavigation(billing, 1, {200}, 1);
        (void)host.beginDocumentNavigation("https://yookassa.ru/confirm", 2, false, 2);
        (void)host.completeDocumentNavigation("https://yookassa.ru/confirm", 2, {200}, 3);
        // Expiry removes external authority, not the ability to leave the bank.
        assert(host.beginDocumentNavigation(billing, 3, false, 900002).decision == RouteDecision::allow);
        assert(!host.paymentNavigationAllowedAt(900002));
        (void)host.completeDocumentNavigation(billing, 3, {200}, 900003);
        (void)host.beginDocumentNavigation("https://yookassa.ru/confirm", 4, false, 900004);
        assert(host.completeDocumentNavigation("https://yookassa.ru/confirm", 4, {0, false}, 900005) == WebResponseDecision::unavailable);
        assert(!host.paymentNavigationAllowedAt(900005));
    }
    testOnlyTheThreeAppearancesTheCabinetOwnsAreAccepted();
    // A host that was never attached claims nothing: no runtime, no failure, no
    // history, and no capability it cannot honour.
    {
        WebView2Host host;
        assert(host.runtimeState() == WebRuntimeState::unavailable);
        assert(host.failureDetail().empty());
        assert(host.currentUrl().empty());
        assert(!host.canGoBack());
        assert(!host.canGoForward());
        assert(!host.genericHostObjectsAllowed());
        assert(host.routePolicy().trustedOrigin() == kTrusted);
    }

    // Retry before any approved route goes to the default cabinet route, so an
    // unavailable runtime never leaves the user without a destination.
    {
        WebView2Host host;
        std::vector<RouteEvaluation> seen;
        host.setNavigationHandler([&seen](const RouteEvaluation& evaluation) { seen.push_back(evaluation); });
        host.reload();
        assert(seen.size() == 1);
        assert(seen.front().decision == RouteDecision::allow);
        assert(seen.front().kind == RouteKind::meetings);
        assert(seen.front().normalizedUrl == std::string(kTrusted) + "/desktop/meetings");
    }

    // A refused document is refused at the policy, and it must not become the
    // destination a later retry replays.
    {
        WebView2Host host;
        std::vector<RouteEvaluation> seen;
        host.setNavigationHandler([&seen](const RouteEvaluation& evaluation) { seen.push_back(evaluation); });

        seen.clear();
        const auto denied = host.navigate("file:///tmp/index.html");
        assert(denied.decision == RouteDecision::deny);
        assert(seen.size() == 1);
        seen.clear();
        host.reload();
        assert(lastNavigation(seen) == std::string(kTrusted) + "/desktop/meetings");

        // An off-origin page is a legal "open in the system browser" request,
        // not a legal document, so it is not a retry destination either.
        seen.clear();
        const auto external = host.navigate("https://evil.example/desktop/meetings");
        assert(external.decision == RouteDecision::openExternal);
        seen.clear();
        host.reload();
        assert(lastNavigation(seen) == std::string(kTrusted) + "/desktop/meetings");
    }

    // An approved route does become the retry destination: a transient network
    // failure must return the user to where they were, not to the entry page.
    {
        WebView2Host host;
        std::vector<RouteEvaluation> seen;
        host.setNavigationHandler([&seen](const RouteEvaluation& evaluation) { seen.push_back(evaluation); });

        const auto approved = host.navigate(std::string(kTrusted) + "/desktop/settings");
        assert(approved.decision == RouteDecision::allow);
        assert(approved.kind == RouteKind::settings);
        assert(approved.normalizedUrl == std::string(kTrusted) + "/desktop/settings");

        seen.clear();
        host.reload();
        assert(seen.size() == 1);
        assert(seen.front().decision == RouteDecision::allow);
        assert(seen.front().normalizedUrl == approved.normalizedUrl);
    }

    // Closing is final for driving the control. The host still reports what a
    // caller asked for, but it must not schedule any further navigation.
    {
        WebView2Host host;
        std::vector<RouteEvaluation> seen;
        host.setNavigationHandler([&seen](const RouteEvaluation& evaluation) { seen.push_back(evaluation); });
        (void)host.navigate(std::string(kTrusted) + "/desktop/settings");

        host.close();
        assert(host.runtimeState() == WebRuntimeState::closed);
        assert(host.runtimeState() != WebRuntimeState::ready);

        seen.clear();
        host.reload();
        assert(seen.empty());
        // The caller is still told what the policy decided, but nothing is
        // scheduled and the destination is not remembered.
        (void)host.navigate(std::string(kTrusted) + "/desktop/meetings");
        assert(seen.size() == 1);
        seen.clear();
        host.reload();
        assert(seen.empty());

        // A closed host no longer accepts a new destination either.
        (void)host.navigate(std::string(kTrusted) + "/desktop/settings");
        seen.clear();
        host.reload();
        assert(seen.empty());

        // Closing twice is a no-op rather than a second teardown.
        host.close();
        assert(host.runtimeState() == WebRuntimeState::closed);
    }

    // A throwing UI callback must not escape: setRuntimeState is noexcept, and a
    // broken presentation layer degrades the host instead of terminating it.
    {
        WebView2Host host;
        std::vector<WebRuntimeState> states;
        host.setRuntimeHandler([&states](WebRuntimeState state) {
            states.push_back(state);
            throw std::runtime_error("presentation layer failed");
        });
        host.setRuntimeState(WebRuntimeState::ready);
        assert(states.size() == 1 && states.front() == WebRuntimeState::ready);
        assert(host.runtimeState() == WebRuntimeState::unavailable);
        assert(host.failureDetail().empty());

        host.setRuntimeHandler({});
        host.setRuntimeState(WebRuntimeState::ready);
        assert(host.runtimeState() == WebRuntimeState::ready);
    }

    // The local-recording actions the cabinet may ask for are gated on a ready
    // runtime and on the row actually offering the action.
    {
        WebView2Host host;
        WebViewLocalRecordingRow openable;
        openable.id = "row-open";
        openable.canOpen = true;
        openable.uploadComplete = false;
        WebViewLocalRecordingRow sendable;
        sendable.id = "row-send";
        sendable.canSend = true;
        host.setLocalRecordings({openable, sendable});

        // Nothing is allowed while the runtime is not ready.
        assert(!host.localRecordingActionAllowed("open", "row-open"));
        host.setRuntimeState(WebRuntimeState::ready);
        assert(host.localRecordingActionAllowed("open", "row-open"));
        assert(host.localRecordingActionAllowed("send", "row-send"));
        assert(!host.localRecordingActionAllowed("send", "row-open"));
        assert(!host.localRecordingActionAllowed("delete", "row-open"));
        assert(!host.localRecordingActionAllowed("open", "row-missing"));
        assert(!host.localRecordingActionAllowed("open", ""));
        assert(!host.localRecordingActionAllowed("open", std::string(301, 'x')));

        // Leaving ready revokes the gate again.
        host.setRuntimeState(WebRuntimeState::unavailable);
        assert(!host.localRecordingActionAllowed("open", "row-open"));
        assert(!host.localRecordingActionAllowed("send", "row-send"));
    }

    // Quit is accepted only as the exact documented payload.
    {
        assert(WebView2Host::isAllowedQuitPayload(R"({"action":"quit"})"));
        assert(!WebView2Host::isAllowedQuitPayload(R"({"action":"quit","extra":1})"));
        assert(!WebView2Host::isAllowedQuitPayload(""));
        assert(!WebView2Host::isAllowedQuitPayload("quit"));
    }

    // The cabinet localizes the row itself, so it receives the instant in wire
    // form and a prefix instead of a date already rendered on this machine.
    {
        WebViewLocalRecordingRow unmeasured;
        assert(!std::optional<std::uint64_t>(unmeasured.durationSeconds).has_value() &&
            "unknown_duration_is_not_measured_zero");
        unmeasured.canOpen = true;
        WebView2Host::applyLocalPackageTiming(unmeasured, 0, 0, true);
        assert(!std::optional<std::uint64_t>(unmeasured.sessionDurationSeconds).has_value());
        assert(!unmeasured.showsPartialDuration && unmeasured.startedAt.empty());
        WebView2Host::applyLocalPackageTiming(unmeasured, 1'789722300000ULL, 1'789722363000ULL, true);
        assert(!std::optional<std::uint64_t>(unmeasured.durationSeconds).has_value());
        assert(unmeasured.sessionDurationSeconds == 63 && !unmeasured.showsPartialDuration);
        WebView2Host::applyLocalPackageTiming(unmeasured, 0, 0, true);
        assert(!std::optional<std::uint64_t>(unmeasured.sessionDurationSeconds).has_value() &&
            "missing_timing_revokes_previous_session_duration");
        unmeasured.durationSeconds = 0;
        WebView2Host::applyLocalPackageTiming(unmeasured, 0, 0, true);
        assert(std::optional<std::uint64_t>(unmeasured.durationSeconds).has_value());
        assert(unmeasured.durationSeconds == 0 && unmeasured.sessionDurationSeconds == 0 && !unmeasured.showsPartialDuration);

        WebViewLocalRecordingRow row;
        row.durationSeconds = 90;
        row.canOpen = true;
        WebView2Host::applyLocalPackageTiming(row, 1'789722300000ULL, 1'789722363000ULL, false);
        assert(row.startedAt == "2026-09-18T09:05:00Z");
        assert(row.generatedTitlePrefix == "Запись ");
        // The longer of the two: the saved audio here outlives the session clock.
        assert(row.sessionDurationSeconds == 90);
        assert(!row.showsPartialDuration);

        // An interrupted recording keeps its whole session length, so the saved
        // part can be reported as a part. Rounding up never reports 0 seconds.
        WebViewLocalRecordingRow partial;
        partial.durationSeconds = 10;
        partial.canOpen = true;
        WebView2Host::applyLocalPackageTiming(partial, 1'789722300000ULL, 1'789722363000ULL, true);
        assert(partial.durationSeconds == 10 && partial.sessionDurationSeconds == 63);
        assert(partial.showsPartialDuration);

        // The same fault without a playable prefix is not offered as playable,
        // and a package with no readable bounds keeps the plain title.
        WebViewLocalRecordingRow unplayable;
        unplayable.durationSeconds = 10;
        WebView2Host::applyLocalPackageTiming(unplayable, 1'789722300000ULL, 1'789722363000ULL, true);
        assert(!unplayable.showsPartialDuration && unplayable.sessionDurationSeconds == 63);
        WebViewLocalRecordingRow unknown;
        unknown.durationSeconds = 10;
        unknown.canOpen = true;
        WebView2Host::applyLocalPackageTiming(unknown, 0, 0, true);
        assert(unknown.startedAt.empty() && unknown.generatedTitlePrefix.empty());
        assert(unknown.sessionDurationSeconds == 10 && !unknown.showsPartialDuration);
    }

    // A deletion the cabinet asks for has to pass a gate of its own: the message
    // shape, the page it came from, and the rows this app actually offers for
    // deletion. None of it needs a browser, so all of it is pinned here.
    {
        using graf::windows::CabinetDeletionInput;
        using graf::windows::DeletionTarget;
        using graf::windows::RecordingDeletionBridge;
        using graf::windows::WebView2Host;

        const std::string row = "0BADCA32-921E-4284-B63C-BFBFB837B7C7";
        const std::string origin = "D4C613C4-C35B-4208-8549-23307BA3FC39";
        const std::string meeting = "33333333-3333-4333-8333-333333333333";
        const std::string otherMeeting = "55555555-5555-4555-8555-555555555555";
        const std::string request = "44444444-4444-4444-8444-444444444444";

        const auto selection = [&](std::vector<std::string> localIds, std::vector<std::string> meetingIds) {
            CabinetDeletionInput input;
            input.version = 1;
            input.action = "deleteSelection";
            input.requestId = request;
            input.localIds = std::move(localIds);
            input.meetingIds = std::move(meetingIds);
            return input;
        };

        WebView2Host host;
        WebViewLocalRecordingRow deletable;
        deletable.id = row;
        // The server knows this local copy by its directory, which is not
        // necessarily the row id the page was shown.
        deletable.originId = origin;
        deletable.canDelete = true;
        host.setLocalRecordings({deletable});

        const std::string list = std::string(kTrusted) + "/desktop/meetings";
        const std::string page = std::string(kTrusted) + "/desktop/meetings/" + meeting;
        const std::string shared = std::string(kTrusted) + "/shared-meetings/" + meeting + "?workspace_id=" + meeting;
        const std::string settings = std::string(kTrusted) + "/desktop/settings";

        // A page that is not a meeting list, and a runtime that is not ready,
        // accept nothing at all.
        assert(!host.deletionSelectionFrom(selection({row}, {}), list));
        assert(!host.deletionSelectionFrom(selection({row}, {}), "file:///tmp/index.html"));
        host.setRuntimeState(WebRuntimeState::ready);
        assert(!host.deletionSelectionFrom(selection({row}, {}), ""));
        assert(!host.deletionSelectionFrom(selection({row}, {}), "file:///tmp/index.html"));

        // The meeting list takes local rows and meetings alike.
        const auto onList = host.deletionSelectionFrom(selection({row}, {meeting}), list);
        assert(onList && onList->total() == 2);

        // The rows the gate decides against are the rows the page was shown, and
        // the selection resolves to what the lane that executes it has to name: the
        // server identifier for a local copy, never the row id.
        assert(host.cabinetRows().size() == 1 && host.cabinetRows()[0].originId == origin);
        const auto resolved = RecordingDeletionBridge::targets(*onList, host.cabinetRows());
        assert(resolved.size() == 2);
        assert(resolved[0].target == DeletionTarget::ownOrigin && resolved[0].targetId == origin);
        assert(resolved[1].target == DeletionTarget::meeting && resolved[1].targetId == meeting);

        // On a meeting page only that meeting, or local rows alone, may be named.
        assert(WebView2Host::meetingIdOnPage(page) == meeting);
        assert(host.deletionSelectionFrom(selection({}, {meeting}), page));
        assert(host.deletionSelectionFrom(selection({row}, {}), page));
        assert(!host.deletionSelectionFrom(selection({}, {otherMeeting}), page));
        assert(!host.deletionSelectionFrom(selection({row}, {meeting}), page));
        assert(!host.deletionSelectionFrom(selection({row}, {otherMeeting}), page));
        // A shared meeting is one meeting too, and the same rule applies.
        assert(WebView2Host::meetingIdOnPage(shared) == meeting);
        assert(host.deletionSelectionFrom(selection({}, {meeting}), shared));
        assert(!host.deletionSelectionFrom(selection({}, {otherMeeting}), shared));
        // The list itself is not a meeting.
        assert(WebView2Host::meetingIdOnPage(list).empty());
        assert(WebView2Host::meetingIdOnPage(std::string(kTrusted) + "/desktop/meetings/" + meeting + "#recording") == meeting);

        // A page that is not a meeting page is not a deletion surface, whatever
        // the message says.
        assert(!host.deletionSelectionFrom(selection({row}, {meeting}), settings));
        assert(!host.deletionSelectionFrom(selection({}, {meeting}), settings));
        // A page on the trusted origin that only looks like a meeting page is not
        // one for the route policy either.
        assert(!host.deletionSelectionFrom(selection({}, {meeting}),
            std::string(kTrusted) + "/desktop/meetings/" + meeting + "/deletion-report"));

        // A row the app does not offer for deletion is refused on the page that
        // does show it, not merely on a page that does not.
        WebViewLocalRecordingRow kept;
        kept.id = "3EBBD476-2D97-40D8-9612-F26105C90069";
        kept.canDelete = false;
        host.setLocalRecordings({deletable, kept});
        assert(!host.deletionSelectionFrom(selection({kept.id}, {}), list));
        assert(host.deletionSelectionFrom(selection({row}, {}), list));
    }

    return 0;
}
