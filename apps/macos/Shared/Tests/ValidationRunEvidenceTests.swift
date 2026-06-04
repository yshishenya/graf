import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class ValidationRunEvidenceTests: XCTestCase {
    func testAggregatesAcceptedTargetAndDeviceCoverage() {
        let entries = MeetingTarget.allCases.flatMap { target in
            [PhysicalDeviceClass.builtIn, .wired, .usb].map {
                LiveRouteAcceptanceMatrixEntry(target: target, deviceClass: $0, result: .accepted)
            }
        }

        let evidence = ValidationRunEvidenceAggregator().aggregate(
            runId: "019-accepted",
            durationGate: .development30Minute,
            entries: entries,
            userActionCount: 0,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: LiveRouteStabilityFixtures.now.addingTimeInterval(1_800)
        )

        XCTAssertEqual(evidence.result, .accepted)
        XCTAssertEqual(Set(evidence.targetsCovered), Set(MeetingTarget.allCases))
        XCTAssertEqual(Set(evidence.deviceClassesCovered), [.builtIn, .wired, .usb])
        XCTAssertTrue(evidence.isAcceptedWithoutNormalUserActions)
    }
}
#endif
