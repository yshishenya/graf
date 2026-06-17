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

        let login = policy.decision(for: try url("/login?next=/desktop/meetings"))
        XCTAssertEqual(login.decision, .allow)
        XCTAssertEqual(login.route.kind, .authLogin)
        XCTAssertEqual(login.reason, .allowedAuthLogin)
        XCTAssertEqual(policy.decision(for: try url("/login/email/start")).decision, .allow)
        XCTAssertEqual(policy.decision(for: try url("/login/email/verify")).decision, .allow)

        let signup = policy.decision(for: try url("/sign-up?next=/desktop/meetings"))
        XCTAssertEqual(signup.decision, .allow)
        XCTAssertEqual(signup.route.kind, .authSignup)
        XCTAssertEqual(signup.reason, .allowedAuthSignup)
        XCTAssertEqual(policy.decision(for: try url("/sign-up?next=/desktop/meetings&mode=email")).decision, .allow)
        XCTAssertEqual(policy.decision(for: try url("/sign-up/email/start")).decision, .allow)
        XCTAssertEqual(policy.decision(for: try url("/sign-up/email/verify")).decision, .allow)
    }

    func testBlocksFutureGovernanceAndNativeCaptureRoutes() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/share")).decision, .blockWithMessage)
        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/download")).reason, .blockedFutureGovernance)
        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/delete")).reason, .blockedFutureGovernance)
        XCTAssertEqual(policy.decision(for: try url("/desktop/meetings/meeting-033/retention")).reason, .blockedFutureGovernance)
        XCTAssertEqual(policy.decision(for: try url("/desktop/capture/record")).reason, .blockedNativeCaptureControl)
        XCTAssertEqual(policy.decision(for: try url("/desktop/diagnostics/bundle")).reason, .blockedLocalFileOrDiagnostic)
    }

    func testBlocksLocalUploadDeviceAndPermissionRoutes() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        XCTAssertEqual(policy.decision(for: try url("/desktop/upload")).reason, .blockedLocalFileOrDiagnostic)
        XCTAssertEqual(policy.decision(for: try url("/desktop/upload/picker")).reason, .blockedLocalFileOrDiagnostic)
        XCTAssertEqual(policy.decision(for: try url("/desktop/audio-devices")).reason, .blockedNativeCaptureControl)
        XCTAssertEqual(policy.decision(for: try url("/desktop/permissions/recover")).reason, .blockedNativeCaptureControl)
    }

    func testExternalLinksDoNotEmbedByDefault() throws {
        let policy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))

        XCTAssertEqual(policy.decision(for: try XCTUnwrap(URL(string: "https://docs.2brain.dev/help"))).decision, .openExternally)
        XCTAssertEqual(policy.decision(for: try XCTUnwrap(URL(string: "https://evil.example/desktop/meetings"))).decision, .blockWithMessage)
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
