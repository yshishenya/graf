import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetRoutePolicyTests: XCTestCase {
    func testAllowsMeetingListDetailAndLoginRoutes() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings")).decision, .allow)
        let detail = policy.decision(for: try url("/desktop/meetings/meeting-033"))
        XCTAssertEqual(detail.decision, .allow)
        XCTAssertEqual(detail.route.kind, .meetingDetail)
        XCTAssertEqual(detail.route.meetingId, "meeting-033")

        let deletionReport = policy.decision(for: try url("/desktop/meetings/meeting-033/deletion-report"))
        XCTAssertEqual(deletionReport.decision, .allow)
        XCTAssertEqual(deletionReport.route.kind, .meetingDeletionReport)
        XCTAssertEqual(deletionReport.route.meetingId, "meeting-033")
        XCTAssertEqual(deletionReport.reason, .allowedMeetingDeletionReport)

        let calendarSettings = policy.decision(for: try url("/desktop/settings/integrations/calendar"))
        XCTAssertEqual(calendarSettings.decision, .allow)
        XCTAssertEqual(calendarSettings.route.kind, .calendarSettings)
        XCTAssertEqual(calendarSettings.reason, .allowedCalendarSettings)
        for route in [
            "/desktop/settings/integrations/calendar/provider-result?provider_family=caldav_yandex&result=success",
            "/desktop/settings/integrations/calendar/preferences",
            "/desktop/settings/integrations/calendar/providers/caldav_yandex/connect",
            "/desktop/settings/integrations/calendar/sources/source-033/calendars",
            "/desktop/settings/integrations/calendar/sources/source-033/sync",
            "/desktop/settings/integrations/calendar/sources/source-033/disconnect"
        ] {
            let decision = policy.decision(for: try url(route))
            XCTAssertEqual(decision.decision, .allow, route)
            XCTAssertEqual(decision.route.kind, .calendarSettings, route)
            XCTAssertEqual(decision.reason, .allowedCalendarSettings, route)
        }

        let meetingDetectionSettings = policy.decision(for: try url("/desktop/settings/meeting-detection"))
        XCTAssertEqual(meetingDetectionSettings.decision, .allow)
        XCTAssertEqual(meetingDetectionSettings.route.kind, .meetingDetectionSettings)
        XCTAssertEqual(meetingDetectionSettings.reason, .allowedMeetingDetectionSettings)

        let login = policy.decision(for: try url("/login?next=/desktop/meetings"))
        XCTAssertEqual(login.decision, .allow)
        XCTAssertEqual(login.route.kind, .authLogin)
        XCTAssertEqual(login.reason, .allowedAuthLogin)
        XCTAssertEqual(policy.decision(for: try url("/login/email/start")).decision, .allow)
        XCTAssertEqual(policy.decision(for: try url("/login/email/verify")).decision, .allow)
        for route in [
            "/api/v1/auth/callback/yandex?state=state&code=code",
            "/api/v1/auth/callback/future-provider_1?state=state&code=code"
        ] {
            let callback = policy.decision(for: try url(route))
            XCTAssertEqual(callback.decision, .allow, route)
            XCTAssertEqual(callback.route.kind, .authCallback, route)
            XCTAssertEqual(callback.reason, .allowedAuthCallback, route)
        }

        let signup = policy.decision(for: try url("/sign-up?next=/desktop/meetings"))
        XCTAssertEqual(signup.decision, .allow)
        XCTAssertEqual(signup.route.kind, .authSignup)
        XCTAssertEqual(signup.reason, .allowedAuthSignup)
        XCTAssertEqual(policy.decision(for: try url("/sign-up?next=/desktop/meetings&mode=email")).decision, .allow)
        XCTAssertEqual(policy.decision(for: try url("/sign-up/email/start")).decision, .allow)
        XCTAssertEqual(policy.decision(for: try url("/sign-up/email/verify")).decision, .allow)
    }

    func testAllowsEmbeddedLogoutCompatibilityTarget() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))
        let decision = policy.decision(for: try url("/desktop/meetings"))

        XCTAssertEqual(decision.decision, .allow)
        XCTAssertEqual(decision.route.kind, .meetingList)
        XCTAssertEqual(decision.reason, .allowedMeetingList)
    }

    func testAllowsProviderLegsOnlyDuringAuthContinuation() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        for target in [
            "https://oauth.yandex.ru/authorize?state=state&redirect_uri=https%3A%2F%2Frec.2brain.dev%2Fapi%2Fv1%2Fauth%2Fcallback%2Fyandex",
            "https://passport.yandex.ru/auth?retpath=https%3A%2F%2Foauth.yandex.ru%2Fauthorize",
            "https://id.vk.ru/authorize?state=state",
            "https://id.future-provider.example/authorize?state=state"
        ] {
            let url = try XCTUnwrap(URL(string: target))
            XCTAssertEqual(policy.decision(for: url).decision, .blockWithMessage, target)
            let decision = policy.decision(for: url, allowExternalAuthProvider: true)
            XCTAssertEqual(decision.decision, .allow, target)
            XCTAssertEqual(decision.route.kind, .authProvider, target)
            XCTAssertEqual(decision.reason, .allowedAuthProvider, target)
        }

        XCTAssertEqual(
            policy.decision(for: try XCTUnwrap(URL(string: "https://unknown.example/authorize?state=state"))).decision,
            .blockWithMessage
        )
    }

    func testBlocksNonHTTPSProviderLegsEvenWhenAuthContinuationIsActive() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))
        let insecureProvider = try XCTUnwrap(URL(string: "http://id.future-provider.example/authorize?state=state"))

        XCTAssertEqual(policy.decision(for: insecureProvider, allowExternalAuthProvider: true).decision, .blockWithMessage)
    }

    func testBlocksFutureGovernanceAndNativeCaptureRoutes() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        let admin = policy.decision(for: try url("/admin"))
        XCTAssertEqual(admin.decision, .openExternally)
        XCTAssertEqual(admin.route.kind, .admin)
        XCTAssertEqual(admin.reason, .openBrowserOwnedAdmin)

        let share = policy.decision(for: try url("/desktop/meetings/meeting-033/share"))
        XCTAssertEqual(share.decision, .allow)
        XCTAssertEqual(share.route.kind, .meetingShare)
        XCTAssertEqual(share.route.meetingId, "meeting-033")
        XCTAssertEqual(share.reason, .allowedMeetingShare)
        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/download")).reason, .blockedFutureGovernance)
        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/delete")).reason, .blockedFutureGovernance)
        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/deletion")).reason, .blockedFutureGovernance)
        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/retention")).reason, .blockedFutureGovernance)
        XCTAssertEqual(policy.decision(for: try url("/desktop/capture/record")).reason, .blockedNativeCaptureControl)
        XCTAssertEqual(policy.decision(for: try url("/desktop/diagnostics/bundle")).reason, .blockedLocalFileOrDiagnostic)
    }

    func testRoutePolicyDoesNotUseBroadSubstringMatchingForSafeMeetingIds() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        let detail = policy.decision(for: try url("/desktop/meetings/delete-retention-notes"))

        XCTAssertEqual(detail.decision, .allow)
        XCTAssertEqual(detail.route.kind, .meetingDetail)
        XCTAssertEqual(detail.route.meetingId, "delete-retention-notes")
    }

    func testBlocksLocalUploadDeviceAndPermissionRoutes() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        XCTAssertEqual(policy.decision(for: try url("/desktop/upload")).reason, .blockedLocalFileOrDiagnostic)
        XCTAssertEqual(policy.decision(for: try url("/desktop/upload/picker")).reason, .blockedLocalFileOrDiagnostic)
        XCTAssertEqual(policy.decision(for: try url("/desktop/audio-devices")).reason, .blockedNativeCaptureControl)
        XCTAssertEqual(policy.decision(for: try url("/desktop/permissions/recover")).reason, .blockedNativeCaptureControl)
        XCTAssertEqual(policy.decision(for: try url("/desktop/driver")).reason, .blockedNativeCaptureControl)
    }

    func testExternalLinksDoNotEmbedByDefault() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        XCTAssertEqual(policy.decision(for: try XCTUnwrap(URL(string: "https://docs.2brain.dev/help"))).decision, .openExternally)
        XCTAssertEqual(policy.decision(for: try XCTUnwrap(URL(string: "https://evil.example/desktop/meetings"))).decision, .blockWithMessage)
    }

    func testAllowsBlobDownloadOnlyFromAnAllowedMainFrame() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))
        let blob = try XCTUnwrap(URL(string: "blob:https://rec.2brain.dev/export-id"))
        let detail = try url("/desktop/meetings/meeting-033")

        XCTAssertTrue(EmbeddedCabinetWebView.allowsBlobDownload(
            requested: true,
            targetURL: blob,
            sourceURL: detail,
            sourceIsMainFrame: true,
            routePolicy: policy
        ))
        XCTAssertFalse(EmbeddedCabinetWebView.allowsBlobDownload(
            requested: false,
            targetURL: blob,
            sourceURL: detail,
            sourceIsMainFrame: true,
            routePolicy: policy
        ))
        XCTAssertFalse(EmbeddedCabinetWebView.allowsBlobDownload(
            requested: true,
            targetURL: blob,
            sourceURL: detail,
            sourceIsMainFrame: false,
            routePolicy: policy
        ))
        XCTAssertFalse(EmbeddedCabinetWebView.allowsBlobDownload(
            requested: true,
            targetURL: try url("/api/v1/cabinet/meetings/meeting-033/content-exports"),
            sourceURL: detail,
            sourceIsMainFrame: true,
            routePolicy: policy
        ))
        XCTAssertFalse(EmbeddedCabinetWebView.allowsBlobDownload(
            requested: true,
            targetURL: blob,
            sourceURL: try XCTUnwrap(URL(string: "https://evil.example/desktop/meetings/meeting-033")),
            sourceIsMainFrame: true,
            routePolicy: policy
        ))
        XCTAssertFalse(EmbeddedCabinetWebView.allowsBlobDownload(
            requested: true,
            targetURL: blob,
            sourceURL: try url("/login"),
            sourceIsMainFrame: true,
            routePolicy: policy
        ))
    }

    func testNativeSaveUsesAFlatSuggestedFilenameAndTreatsCancelAsNoDestination() throws {
        XCTAssertEqual(
            EmbeddedCabinetWebView.safeDownloadFilename("../../meeting.txt"),
            "meeting.txt"
        )
        XCTAssertEqual(EmbeddedCabinetWebView.safeDownloadFilename("/"), "GRAF export")

        let selectedURL = try XCTUnwrap(URL(string: "file:///tmp/meeting.txt"))
        XCTAssertEqual(
            EmbeddedCabinetWebView.nativeSaveDestination(response: .OK, selectedURL: selectedURL),
            selectedURL
        )
        XCTAssertNil(
            EmbeddedCabinetWebView.nativeSaveDestination(response: .cancel, selectedURL: selectedURL)
        )
    }

    func testReviewRouteRequiresReviewAvailableServerMeeting() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        let unavailable = policy.reviewDecision(
            for: try url("/desktop/meetings/meeting-processing"),
            reviewAvailableMeetingIds: []
        )
        XCTAssertEqual(unavailable.decision, .blockWithMessage)
        XCTAssertEqual(unavailable.reason, .blockedReviewUnavailable)

        let available = policy.reviewDecision(
            for: try url("/desktop/meetings/meeting-ready"),
            reviewAvailableMeetingIds: ["meeting-ready"]
        )
        XCTAssertEqual(available.decision, .allow)
        XCTAssertEqual(available.reason, .allowedMeetingDetail)
    }

    func testForbiddenControlCopyRemainsOutOfEmbeddedPolicyMessages() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))
        let decision = policy.decision(for: try url("/desktop/capture/record"))

        XCTAssertFalse(decision.userMessage.localizedCaseInsensitiveContains("record now"))
        XCTAssertFalse(decision.userMessage.localizedCaseInsensitiveContains("stop recording"))
        XCTAssertFalse(decision.userMessage.contains("/Users/"))
        XCTAssertTrue(decision.userMessage.contains("app shell"))
    }

    private func url(_ path: String) throws -> URL {
        try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
    }
}
#endif
