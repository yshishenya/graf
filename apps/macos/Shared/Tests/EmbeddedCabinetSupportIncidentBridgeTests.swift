import Foundation
import TwoBrainRecAppCore

#if canImport(WebKit) && canImport(XCTest)
import XCTest

final class EmbeddedCabinetSupportIncidentBridgeTests: XCTestCase {
    @MainActor
    func testBridgeUsesFixedSameOriginFetchWithoutCookieOrTokenExtraction() {
        let script = EmbeddedCabinetSupportIncidentBridge.requestScript

        XCTAssertEqual(
            EmbeddedCabinetSupportIncidentBridge.intakePath,
            "/api/v1/desktop/support-incidents"
        )
        XCTAssertTrue(script.contains("fetch(request.path"))
        XCTAssertTrue(script.contains("credentials: \"same-origin\""))
        XCTAssertTrue(script.contains("X-CSRF-Token"))
        XCTAssertTrue(script.contains("arguments.request"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("document.cookie"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("authorization"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("x-auth-session"))
        XCTAssertFalse(script.localizedCaseInsensitiveContains("cookie"))
    }

    func testBridgeOnlyUsesAnAllowedAuthenticatedCabinetDocument() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.pro"))
        )

        XCTAssertTrue(
            EmbeddedCabinetSupportIncidentBridge.isAllowedCabinetDocument(
                try XCTUnwrap(URL(string: "https://rec.2brain.pro/desktop/meetings")),
                routePolicy: policy
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetSupportIncidentBridge.isAllowedCabinetDocument(
                try XCTUnwrap(URL(string: "https://rec.2brain.pro/login")),
                routePolicy: policy
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetSupportIncidentBridge.isAllowedCabinetDocument(
                try XCTUnwrap(URL(string: "https://example.test/desktop/meetings")),
                routePolicy: policy
            )
        )
    }
}
#endif
