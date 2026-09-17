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

int main() {
    testTheSessionCookieIsExtendedOnlyOnTheAppsOwnTerms();
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
