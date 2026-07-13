import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RecordingRouteMetadataTests: XCTestCase {
    func testSnapshotCapturesSafeRouteFactsOnly() {
        let metadata = RecordingRouteMetadataService().snapshot(
            inputRouteClass: "built_in",
            outputRouteClass: "built_in",
            outputVolumeBucket: .medium,
            muteState: .unmuted,
            browserTarget: "chrome",
            routeChangeCount: 2,
            sleepWakeObserved: true
        )

        XCTAssertEqual(metadata.inputRouteClass, "built_in")
        XCTAssertEqual(metadata.outputRouteClass, "built_in")
        XCTAssertEqual(metadata.outputVolumeBucket, .medium)
        XCTAssertEqual(metadata.muteState, .unmuted)
        XCTAssertEqual(metadata.browserTarget, "chrome")
        XCTAssertEqual(metadata.routeChangeCount, 2)
        XCTAssertTrue(metadata.sleepWakeObserved)
    }

    func testSnapshotDefaultsRemainNeutralForLeakageEvaluation() {
        let metadata = RecordingRouteMetadataService().snapshot()

        XCTAssertEqual(metadata.outputVolumeBucket, .unknown)
        XCTAssertEqual(metadata.muteState, .unknown)
        XCTAssertEqual(metadata.routeChangeCount, 0)
        XCTAssertFalse(metadata.sleepWakeObserved)
    }
}
#endif
