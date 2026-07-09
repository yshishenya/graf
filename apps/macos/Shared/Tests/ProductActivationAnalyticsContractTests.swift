import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class ProductActivationAnalyticsContractTests: XCTestCase {
    func testProductActivationEventNamesAreStable() {
        XCTAssertEqual(
            ProductActivationEventName.allCases.map(\.rawValue),
            [
                "desktop_first_opened",
                "desktop_account_connected",
                "desktop_autorecord_enabled",
                "first_recording_completed",
                "first_result_viewed",
                "first_value_session_completed"
            ]
        )
    }

    func testPayloadAllowsOnlyApprovedDesktopFields() throws {
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopFirstOpened,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: [
                "app_version_bucket": "2026_07",
                "platform": "macos",
                "install_channel": "direct",
                "bridge_present": "false"
            ]
        )

        XCTAssertEqual(payload.eventName, .desktopFirstOpened)
        XCTAssertEqual(payload.properties["platform"], "macos")
    }

    func testPayloadRejectsForbiddenFieldsAndValues() throws {
        XCTAssertThrowsError(try ProductActivationAnalyticsPayload(
            eventName: .firstResultViewed,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: ["meeting_title": "Customer call"]
        ))
        XCTAssertThrowsError(try ProductActivationAnalyticsPayload(
            eventName: .desktopAccountConnected,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: ["auth_method_category": "user@example.com"]
        ))
    }

    func testPayloadRejectsRawIdentity() {
        XCTAssertThrowsError(try ProductActivationAnalyticsPayload(
            eventName: .desktopFirstOpened,
            stablePseudonymousUserId: "user@example.com",
            properties: ["platform": "macos"]
        ))
    }

    func testDirectDesktopProviderEgressIsClosedUntilEveryApprovalExists() {
        XCTAssertFalse(ProductActivationAnalyticsClient.directProviderEgressAllowed(
            legalApproved: true,
            securityApproved: true,
            qaApproved: false,
            telemetryAccepted: true,
            directEgressDisclosed: true
        ))
        XCTAssertTrue(ProductActivationAnalyticsClient.directProviderEgressAllowed(
            legalApproved: true,
            securityApproved: true,
            qaApproved: true,
            telemetryAccepted: true,
            directEgressDisclosed: true
        ))
    }

    func testClientBuildsServerMediatedEndpointOnly() throws {
        let client = try XCTUnwrap(ProductActivationAnalyticsClient(
            rawBaseURL: "https://rec.2brain.pro/some/path",
            headers: ["X-Client-Version": "desktop-094"]
        ))
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopAccountConnected,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: [
                "auth_method_category": "oauth_provider",
                "account_connection_state": "connected",
                "bridge_present": "true"
            ]
        )

        let request = try client.request(for: payload)

        XCTAssertEqual(request.url?.absoluteString, "https://rec.2brain.pro/api/v1/product-analytics/events")
        XCTAssertNil(request.url?.absoluteString.range(of: "posthog", options: .caseInsensitive))
        XCTAssertNil(request.url?.absoluteString.range(of: "mc.yandex", options: .caseInsensitive))
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Client-Version"), "desktop-094")
    }

    func testTelemetryGateBlocksNormalUseUntilAccepted() {
        XCTAssertFalse(ProductTelemetryGateViewModel(state: .notSeen).allowsNormalProductUse)
        XCTAssertTrue(ProductTelemetryGateViewModel(state: .notSeen).requiresAcceptance)
        XCTAssertTrue(ProductTelemetryGateViewModel(state: .accepted).allowsNormalProductUse)
        XCTAssertFalse(ProductTelemetryGateViewModel(state: .withdrawn).allowsProductAnalytics)
        XCTAssertTrue(ProductTelemetryGateViewModel(state: .withdrawn).limitedAccessOnly)
    }
}
#endif
