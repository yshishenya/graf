import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LeakageFinalizationModelTests: XCTestCase {
    func testLeakageStatusRawValuesAreStable() {
        XCTAssertEqual(LeakageStatus.clean.rawValue, "clean")
        XCTAssertEqual(LeakageStatus.leakageDetected.rawValue, "leakage_detected")
        XCTAssertEqual(LeakageStatus.unproven.rawValue, "unproven")
        XCTAssertEqual(LeakageStatus.notMeasured.rawValue, "not_measured")
        XCTAssertEqual(LeakageStatus.notApplicable.rawValue, "not_applicable")
    }

    func testCleanFinalizationIsOnlyOriginalDualEligibleGate() {
        let finalization = LeakageFinalization(
            status: .clean,
            evaluatedAt: Date(timeIntervalSince1970: 1),
            measurementAttempted: true,
            measurementApplicable: true,
            alignmentStatus: .aligned,
            confidence: 0.9,
            failureReason: .none,
            originalEvidenceStatus: .clean,
            transcriptionGate: .eligibleOriginalDual
        )

        XCTAssertEqual(finalization.thresholdVersion, "leakage-threshold.v1")
        XCTAssertEqual(finalization.transcriptionGate, .eligibleOriginalDual)
    }

    func testThresholdV1MatchesSpecGates() {
        let threshold = LeakageThresholdVersion.v1

        XCTAssertEqual(threshold.id, "leakage-threshold.v1")
        XCTAssertEqual(threshold.timelineToleranceMs, 1_000)
        XCTAssertEqual(threshold.minimumFarEndOnlyWindowMs, 15_000)
        XCTAssertEqual(threshold.maximumLeakageLevelDb, -45.0)
        XCTAssertEqual(threshold.maximumCorrelationPeak, 0.12)
        XCTAssertEqual(threshold.minimumConfidence, 0.80)
        XCTAssertEqual(threshold.maximumAlignmentDriftMs, 250)
    }
}
#endif
