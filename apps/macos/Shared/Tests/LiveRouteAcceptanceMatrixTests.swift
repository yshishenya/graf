import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LiveRouteAcceptanceMatrixTests: XCTestCase {
    func testBluetoothAndAirPodsCanBeRepresentedAsNotAcceptedWithoutCountingAsAcceptance() {
        let entries = [
            LiveRouteAcceptanceMatrixEntry(target: .chrome, deviceClass: .builtIn, result: .accepted),
            LiveRouteAcceptanceMatrixEntry(target: .chrome, deviceClass: .bluetooth, result: .notTested, notes: "backlog"),
            LiveRouteAcceptanceMatrixEntry(target: .chrome, deviceClass: .airpodsClass, result: .notTested, notes: "backlog")
        ]

        let evidence = ValidationRunEvidenceAggregator().aggregate(
            runId: "019-matrix",
            durationGate: .development30Minute,
            entries: entries,
            userActionCount: 0,
            startedAt: LiveRouteStabilityFixtures.now,
            completedAt: nil
        )

        XCTAssertEqual(evidence.result, .notTested)
        XCTAssertFalse(evidence.isAcceptedWithoutNormalUserActions)
        XCTAssertTrue(evidence.deviceClassesCovered.contains(.bluetooth))
        XCTAssertTrue(evidence.deviceClassesCovered.contains(.airpodsClass))
    }
}
#endif
