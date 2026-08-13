import Foundation
import XCTest
@testable import TwoBrainRecAppCore
@testable import TwoBrainRecShared

final class LocalBufferServiceTests: XCTestCase {
    private let root = URL(fileURLWithPath: "/synthetic-recordings")

    func testStorageProbeUsesActualMeasurements() {
        let healthy = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            availableBytes: { _ in 1_000_000_000 }
        )
        let lowReserve = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            availableBytes: { _ in 1 }
        )
        let overBudget = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: LocalBufferService.defaultPolicy.maxBytesPerDevice,
            availableBytes: { _ in .max }
        )

        XCTAssertEqual(healthy.riskState(), .healthy)
        XCTAssertEqual(lowReserve.riskState(), .mustDegradeOrStop)
        XCTAssertEqual(overBudget.riskState(), .mustDegradeOrStop)
    }

    func testStorageProbeFailsClosedWhenMeasurementFails() {
        let probe = LocalRecordingStorageProbe(
            rootURL: root,
            usedBytes: 100,
            availableBytes: { _ in throw CocoaError(.fileReadUnknown) }
        )

        XCTAssertEqual(probe.riskState(), .mustDegradeOrStop)
    }
}
