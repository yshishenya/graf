import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DeferredRecordingAcceptanceTests: XCTestCase {
    func testDeferredRecordingAcceptanceRequiresRecordingPolicyPrerequisites() {
        let state = DeferredRecordingAcceptanceState()

        XCTAssertEqual(state.blockedUntil, "local_recording_support")
        XCTAssertTrue(state.retentionPolicyRequired)
        XCTAssertTrue(state.deletionPolicyRequired)
        XCTAssertEqual(state.result, .blocked)
    }
}
#endif
