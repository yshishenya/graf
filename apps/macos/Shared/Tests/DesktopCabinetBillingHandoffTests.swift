import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetBillingHandoffTests: XCTestCase {
    func testBrowserHandoffURLCarriesOnlyOpaqueState() throws {
        let billingURL = try XCTUnwrap(URL(string: "https://rec.2brain.pro/billing"))
        let handoff = try XCTUnwrap(
            DesktopCabinetBillingHandoff.browserURL(for: billingURL, state: "opaque-state-123456")
        )

        XCTAssertEqual(handoff.path, "/billing/handoff")
        XCTAssertEqual(handoff.query, "state=opaque-state-123456")
        XCTAssertFalse(handoff.absoluteString.contains("X-Auth-Session"))
        XCTAssertFalse(handoff.absoluteString.contains("amount"))
    }

    func testHandoffEndpointStaysOnTheBillingOrigin() throws {
        let billingURL = try XCTUnwrap(
            URL(string: "https://user:secret@rec.2brain.pro/billing/checkout?amount=790")
        )
        let endpoint = try XCTUnwrap(DesktopCabinetBillingHandoff.endpointURL(for: billingURL))

        XCTAssertEqual(endpoint.absoluteString, "https://rec.2brain.pro/api/v1/cabinet/billing/handoff")
        XCTAssertNil(endpoint.query)
        XCTAssertNil(endpoint.user)
        XCTAssertNil(endpoint.password)
    }

    func testBillingRoutesLeaveTheEmbeddedCabinetWithoutFinancialQueryData() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )

        for path in ["/billing", "/billing/plans", "/billing/usage", "/billing/subscription", "/billing/payment-method", "/billing/storage", "/billing/checkout", "/billing/checkout/return", "/billing/checkout/status/INV-2026-0001", "/billing/discounts", "/billing/history", "/billing/invoices/INV-2026-0001"] {
            let decision = policy.decision(for: try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)")))
            XCTAssertEqual(decision.decision, .openExternally, path)
            XCTAssertEqual(decision.reason, .openBrowserOwnedBilling, path)
            XCTAssertNil(URL(string: "https://rec.2brain.dev\(path)")?.query)
        }
    }

    func testReferralMenuRoutesOpenInTheBrowserWithoutCarryingQueryData() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )

        for path in ["/referrals", "/account/referrals"] {
            let url = try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)"))
            let decision = policy.decision(for: url)
            XCTAssertEqual(decision.decision, .openExternally, path)
            XCTAssertEqual(decision.reason, .openBrowserOwnedAccount, path)
            XCTAssertNil(url.query)
        }

        for path in ["/referrals/extra", "/account/referrals/extra", "/referrals/unsafe/path"] {
            let decision = policy.decision(for: try XCTUnwrap(URL(string: "https://rec.2brain.dev\(path)")))
            XCTAssertEqual(decision.decision, .blockWithMessage, path)
        }
    }

    func testExternalBillingHandoffStripsFinancialAndProviderQueryData() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let source = try XCTUnwrap(URL(string: "https://user:secret@rec.2brain.dev/billing/checkout?amount=790&provider_id=pay_033#payment"))

        let sanitized = try XCTUnwrap(policy.sanitizedExternalURL(for: source))
        XCTAssertEqual(sanitized.absoluteString, "https://rec.2brain.dev/billing/checkout")
        XCTAssertNil(sanitized.query)
        XCTAssertNil(sanitized.fragment)
        XCTAssertNil(sanitized.user)
        XCTAssertNil(sanitized.password)
    }

    func testUnsafeRouteCannotBeSanitizedForExternalHandoff() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let source = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033?provider_id=pay_033"))

        XCTAssertNil(policy.sanitizedExternalURL(for: source))
    }

    func testExternalHelpHandoffRejectsHTTP() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let source = try XCTUnwrap(URL(string: "http://help.2brain.dev/billing?amount=790"))

        XCTAssertEqual(policy.decision(for: source).decision, .blockWithMessage)
        XCTAssertNil(policy.sanitizedExternalURL(for: source))
    }
}
#endif
