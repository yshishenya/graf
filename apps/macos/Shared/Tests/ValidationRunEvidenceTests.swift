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

    func testEmptyValidationEvidenceIsNotAccepted() {
        let evidence = ValidationRunEvidenceAggregator().aggregate(
            runId: "019-empty",
            durationGate: .development30Minute,
            entries: [],
            userActionCount: 0,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: nil
        )

        XCTAssertEqual(evidence.result, .notTested)
        XCTAssertFalse(evidence.isAcceptedWithoutNormalUserActions)
    }

    func testPartialTargetOrDeviceCoverageIsNotAccepted() {
        let partialTargets = [
            LiveRouteAcceptanceMatrixEntry(target: .chrome, deviceClass: .builtIn, result: .accepted),
            LiveRouteAcceptanceMatrixEntry(target: .opera, deviceClass: .wired, result: .accepted),
            LiveRouteAcceptanceMatrixEntry(target: .zoom, deviceClass: .usb, result: .accepted)
        ]
        let partialDevices = MeetingTarget.allCases.map {
            LiveRouteAcceptanceMatrixEntry(target: $0, deviceClass: .builtIn, result: .accepted)
        }

        let targetEvidence = ValidationRunEvidenceAggregator().aggregate(
            runId: "019-partial-target",
            durationGate: .development30Minute,
            entries: partialTargets,
            userActionCount: 0,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: nil
        )
        let deviceEvidence = ValidationRunEvidenceAggregator().aggregate(
            runId: "019-partial-device",
            durationGate: .development30Minute,
            entries: partialDevices,
            userActionCount: 0,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: nil
        )

        XCTAssertEqual(targetEvidence.result, .notTested)
        XCTAssertEqual(deviceEvidence.result, .notTested)
    }
}
#endif
