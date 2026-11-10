import XCTest
@testable import TwoBrainRecAppCore

final class AccountSwitchResetTests: XCTestCase {
    func testStandardPlanClearsAllOldAccountSurfaces() {
        let plan = AccountSwitchResetPlan.standard
        XCTAssertTrue(plan.resetCabinetRoute)
        XCTAssertTrue(plan.clearCalendarPrompt)
        XCTAssertTrue(plan.clearPendingCalendarState)
        XCTAssertTrue(plan.closeLocalPlayer)
        XCTAssertTrue(plan.clearSelectedRecording)
        XCTAssertTrue(plan.clearWebBridges)
        XCTAssertTrue(plan.reloadCabinet)
        XCTAssertTrue(plan.clearWebStorage)
    }

    func testStorageCleanupScriptClearsOnlyPageStorage() {
        let script = AccountSwitchResetPolicy.storageCleanupScript
        XCTAssertTrue(script.contains("localStorage.clear"))
        XCTAssertTrue(script.contains("sessionStorage.clear"))
        XCTAssertFalse(script.contains("cookie"))
        XCTAssertFalse(script.contains("indexedDB"))
    }
}
