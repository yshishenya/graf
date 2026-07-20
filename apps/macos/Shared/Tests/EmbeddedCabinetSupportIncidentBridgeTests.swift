import Foundation
@testable import TwoBrainRecAppCore

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
        XCTAssertTrue(script.contains("return JSON.stringify([response.status, await response.text()])"))
        XCTAssertTrue(script.contains("request.path"))
        XCTAssertFalse(script.contains("arguments.request"))
        XCTAssertFalse(script.contains("(async () =>"))
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

    @MainActor
    func testBridgeDecodesWebKitObjectResult() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            [
                "status": 202,
                "body": "{\"incident_id\":\"CUST-ABC123\"}"
            ]
        )

        XCTAssertEqual(
            result,
            EmbeddedCabinetSupportIncidentBridge.JavaScriptResult(
                status: 202,
                body: "{\"incident_id\":\"CUST-ABC123\"}"
            )
        )
    }

    @MainActor
    func testBridgeKeepsStringResultCompatibility() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            "{\"status\":200,\"body\":\"{}\"}"
        )

        XCTAssertEqual(result.status, 200)
        XCTAssertEqual(result.body, "{}")
    }

    @MainActor
    func testBridgeDecodesWebKitArrayResult() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            [202, "{\"incident_id\":\"CUST-ARRAY123\"}"]
        )

        XCTAssertEqual(result.status, 202)
        XCTAssertEqual(result.body, "{\"incident_id\":\"CUST-ARRAY123\"}")
    }

    @MainActor
    func testBridgeDecodesStringifiedWebKitArrayResult() throws {
        let result = try EmbeddedCabinetSupportIncidentBridge.decodeJavaScriptResult(
            "[202, \"{\\\"incident_id\\\":\\\"CUST-STRING123\\\"}\"]"
        )

        XCTAssertEqual(result.status, 202)
        XCTAssertEqual(result.body, "{\"incident_id\":\"CUST-STRING123\"}")
    }
}
#endif
