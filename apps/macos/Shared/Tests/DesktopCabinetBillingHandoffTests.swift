import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetBillingHandoffTests: XCTestCase {
    func testBillingRoutesLeaveTheEmbeddedCabinetWithoutFinancialQueryData() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )

        for path in ["/billing", "/billing/checkout", "/billing/history"] {
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
}
#endif
