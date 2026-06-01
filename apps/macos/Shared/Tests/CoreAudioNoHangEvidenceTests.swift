import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class CoreAudioNoHangEvidenceTests: XCTestCase {
    func testPassingNoHangEvidenceMeetsReleaseThresholds() {
        let evidence = CoreAudioNoHangEvidence(
            targetSurface: "Chrome audio settings",
            openedWithinSeconds: 3.2,
            coreaudiodCPUPeakPercent: 7.0,
            coreaudiodCPUSustainedPercent: 4.0,
            routeStateBefore: .ready,
            routeStateAfter: .ready,
            result: .passed
        )

        XCTAssertLessThanOrEqual(evidence.openedWithinSeconds, 5.0)
        XCTAssertLessThanOrEqual(evidence.coreaudiodCPUSustainedPercent, 10.0)
        XCTAssertEqual(evidence.result, .passed)
    }

    func testBlockedNoHangEvidenceCarriesFailureReason() {
        let evidence = CoreAudioNoHangEvidence(
            targetSurface: "Zoom audio settings",
            openedWithinSeconds: 8.5,
            coreaudiodCPUPeakPercent: 25.0,
            coreaudiodCPUSustainedPercent: 14.0,
            routeStateBefore: .ready,
            routeStateAfter: .blocked,
            result: .blocked,
            failureReason: "target_opened_after_threshold"
        )

        XCTAssertEqual(evidence.result, .blocked)
        XCTAssertFalse(evidence.failureReason?.isEmpty ?? true)
    }
}
#endif
