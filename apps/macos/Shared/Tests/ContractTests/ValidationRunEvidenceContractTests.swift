import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class ValidationRunEvidenceContractTests: XCTestCase {
    func testAcceptedValidationRequiresAcceptedResultAndZeroUserActions() {
        let accepted = LiveRouteStabilityFixtures.validationRun(result: .accepted)
        let degraded = ValidationRunEvidence(
            runId: "019-degraded",
            durationGate: .development30Minute,
            result: .degraded,
            targetsCovered: [.chrome],
            deviceClassesCovered: [.builtIn],
            userActionCount: 0,
            startedAt: LiveRouteStabilityFixtures.now
        )
        let manualAction = ValidationRunEvidence(
            runId: "019-manual",
            durationGate: .development30Minute,
            result: .accepted,
            targetsCovered: [.chrome],
            deviceClassesCovered: [.builtIn],
            userActionCount: 1,
            startedAt: LiveRouteStabilityFixtures.now
        )

        XCTAssertTrue(accepted.isAcceptedWithoutNormalUserActions)
        XCTAssertFalse(degraded.isAcceptedWithoutNormalUserActions)
        XCTAssertFalse(manualAction.isAcceptedWithoutNormalUserActions)
    }

    func testValidationCoverageContainsRequiredTargetsAndAcceptedDeviceClasses() {
        let evidence = LiveRouteStabilityFixtures.validationRun()

        XCTAssertEqual(Set(evidence.targetsCovered), Set(MeetingTarget.allCases))
        XCTAssertEqual(Set(evidence.deviceClassesCovered), [.builtIn, .wired, .usb])
        XCTAssertEqual(evidence.durationGate, .development30Minute)
    }
}
#endif
