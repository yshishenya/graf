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

    func testDirectDesktopRouteAllowsOnlyFirstPartyPostHogWithoutSecrets() throws {
        let client = try XCTUnwrap(ProductActivationAnalyticsClient(
            rawBaseURL: "https://rec.2brain.pro",
            headers: [:]
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
        let config = ProductAnalyticsDirectProviderConfig(
            posthogHost: URL(string: "https://rec.2brain.pro"),
            posthogCaptureEndpoint: URL(string: "https://rec.2brain.pro/api/v1/product-analytics/posthog-desktop-capture"),
            posthogDirectEnabled: true,
            yandexDirectEnabled: true,
            telemetryAccepted: true,
            legalApproved: true,
            securityApproved: true,
            qaApproved: true,
            directEgressDisclosed: true
        )

        let request = try XCTUnwrap(client.directPostHogRequest(for: payload, config: config))

        XCTAssertEqual(request.url?.absoluteString, "https://rec.2brain.pro/api/v1/product-analytics/posthog-desktop-capture")
        XCTAssertNil(request.url?.absoluteString.range(of: "mc.yandex", options: .caseInsensitive))
        XCTAssertFalse(config.allowsYandexDirectRoute)
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-GRAF-PostHog-Project-Key-State"), "server_injected_redacted")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-GRAF-Analytics-Route"), "first_party_posthog_desktop_proxy")
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: Any])
        XCTAssertEqual(json["event"] as? String, "desktop_account_connected")
        XCTAssertEqual(json["distinct_id"] as? String, "graf_pseudo_user_1234567890abcdef")
        XCTAssertEqual(json["api_key_state"] as? String, "server_injected_redacted")
        XCTAssertNil(json["api_key"])
    }

    func testDirectDesktopRouteRequiresPseudonymousIdentity() throws {
        let client = try XCTUnwrap(ProductActivationAnalyticsClient(
            rawBaseURL: "https://rec.2brain.pro",
            headers: [:]
        ))
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopFirstOpened,
            stablePseudonymousUserId: nil,
            properties: [
                "platform": "macos",
                "bridge_present": "true"
            ]
        )
        let config = ProductAnalyticsDirectProviderConfig(
            posthogHost: URL(string: "https://rec.2brain.pro"),
            posthogCaptureEndpoint: URL(string: "https://rec.2brain.pro/api/v1/product-analytics/posthog-desktop-capture"),
            posthogDirectEnabled: true,
            yandexDirectEnabled: false,
            telemetryAccepted: true,
            legalApproved: true,
            securityApproved: true,
            qaApproved: true,
            directEgressDisclosed: true
        )

        XCTAssertNil(try client.directPostHogRequest(for: payload, config: config))
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
