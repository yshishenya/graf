import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetNavigationRequestPolicyTests: XCTestCase {
    func testReloadsMeetingDetailNavigationWithDesktopHeaders() throws {
        let policy = try makePolicy()
        let detailURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033"))
        let request = URLRequest(url: detailURL)

        switch policy.decision(forNavigationRequest: request, isForMainFrame: true) {
        case let .reload(reloaded):
            XCTAssertEqual(reloaded.url, detailURL)
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Client-Version"), "local-macos")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-User-Id"), "user-033")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Device-Id"), "device-033")
        case .allow:
            XCTFail("Expected meeting detail navigation to be reloaded with desktop headers")
        }
    }

    func testReloadsDeletionReportNavigationWithDesktopHeaders() throws {
        let policy = try makePolicy()
        let reportURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033/deletion-report"))
        let request = URLRequest(url: reportURL)

        switch policy.decision(forNavigationRequest: request, isForMainFrame: true) {
        case let .reload(reloaded):
            XCTAssertEqual(reloaded.url, reportURL)
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Client-Version"), "local-macos")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Device-Id"), "device-033")
        case .allow:
            XCTFail("Expected deletion report navigation to be reloaded with desktop headers")
        }
    }

    func testReloadsMeetingShareNavigationWithDesktopHeaders() throws {
        let policy = try makePolicy()
        let shareURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033/share"))
        let request = URLRequest(url: shareURL)

        switch policy.decision(forNavigationRequest: request, isForMainFrame: true) {
        case let .reload(reloaded):
            XCTAssertEqual(reloaded.url, shareURL)
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Client-Version"), "local-macos")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
        case .allow:
            XCTFail("Expected meeting share navigation to be reloaded with desktop headers")
        }
    }

    func testReloadsCalendarSettingsNavigationWithDesktopHeaders() throws {
        let policy = try makePolicy()
        let settingsURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/settings/integrations/calendar"))
        let request = URLRequest(url: settingsURL)

        switch policy.decision(forNavigationRequest: request, isForMainFrame: true) {
        case let .reload(reloaded):
            XCTAssertEqual(reloaded.url, settingsURL)
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Client-Version"), "local-macos")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Device-Id"), "device-033")
        case .allow:
            XCTFail("Expected calendar settings navigation to be reloaded with desktop headers")
        }
    }

    func testReloadsSettingsOverviewNavigationWithDesktopHeaders() throws {
        let policy = try makePolicy()
        let settingsURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/settings"))
        let request = URLRequest(url: settingsURL)

        switch policy.decision(forNavigationRequest: request, isForMainFrame: true) {
        case let .reload(reloaded):
            XCTAssertEqual(reloaded.url, settingsURL)
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Client-Version"), "local-macos")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Device-Id"), "device-033")
        case .allow:
            XCTFail("Expected settings navigation to be reloaded with desktop headers")
        }
    }

    func testReloadsArtifactDownloadNavigationWithDesktopHeaders() throws {
        let policy = try makePolicy()
        let audioURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio"))

        switch policy.decision(forNavigationRequest: URLRequest(url: audioURL), isForMainFrame: true) {
        case let .reload(reloaded):
            XCTAssertEqual(reloaded.url, audioURL)
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
            XCTAssertEqual(reloaded.value(forHTTPHeaderField: "X-Device-Id"), "device-033")
        case .allow:
            XCTFail("Expected artifact download navigation to be reloaded with desktop headers")
        }
    }

    func testAllowsMeetingDetailNavigationWhenHeadersAreAlreadyPresent() throws {
        let policy = try makePolicy()
        let detailURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033"))
        var request = URLRequest(url: detailURL)
        request.setValue("local-macos", forHTTPHeaderField: "X-Client-Version")
        request.setValue("user-033", forHTTPHeaderField: "X-User-Id")
        request.setValue("workspace-033", forHTTPHeaderField: "X-Workspace-Id")
        request.setValue("device-033", forHTTPHeaderField: "X-Device-Id")

        switch policy.decision(forNavigationRequest: request, isForMainFrame: true) {
        case .allow:
            break
        case .reload:
            XCTFail("Expected navigation with desktop headers to be allowed")
        }
    }

    func testDoesNotAttachDesktopHeadersToLoginOrExternalNavigations() throws {
        let policy = try makePolicy()
        let login = try XCTUnwrap(URL(string: "https://rec.2brain.dev/login?next=/desktop/meetings"))
        let external = try XCTUnwrap(URL(string: "https://evil.example/desktop/meetings/meeting-033"))

        for url in [login, external] {
            switch policy.decision(forNavigationRequest: URLRequest(url: url), isForMainFrame: true) {
            case .allow:
                break
            case .reload:
                XCTFail("Expected \(url.absoluteString) to stay outside desktop header reinjection")
            }
        }
    }

    func testDoesNotAttachDesktopHeadersToSubresourceOrPostNavigations() throws {
        let policy = try makePolicy()
        let detailURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033"))
        var post = URLRequest(url: detailURL)
        post.httpMethod = "POST"

        for (request, isMainFrame) in [
            (URLRequest(url: detailURL), false),
            (post, true)
        ] {
            switch policy.decision(forNavigationRequest: request, isForMainFrame: isMainFrame) {
            case .allow:
                break
            case .reload:
                XCTFail("Expected non-main-frame and non-GET navigations to stay untouched")
            }
        }
    }

    func testDesktopUploadRouteRemainsBlockedBecauseUploadStaysInsideMeetings() throws {
        let routePolicy = DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev")))
        let uploadURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/upload"))

        let decision = routePolicy.decision(for: uploadURL)

        XCTAssertEqual(decision.decision, .blockWithMessage)
        XCTAssertEqual(decision.reason, .blockedLocalFileOrDiagnostic)
        XCTAssertEqual(decision.route.kind, .forbiddenAction)
    }

    private func makePolicy() throws -> DesktopCabinetNavigationRequestPolicy {
        DesktopCabinetNavigationRequestPolicy(
            routePolicy: DesktopCabinetRoutePolicy(baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))),
            desktopHeaders: [
                "X-Client-Version": "local-macos",
                "X-User-Id": "user-033",
                "X-Workspace-Id": "workspace-033",
                "X-Device-Id": "device-033"
            ]
        )
    }
}
#endif
