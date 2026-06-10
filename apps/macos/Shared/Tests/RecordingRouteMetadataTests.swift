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
            coreaudiodState: "running",
            sleepWakeObserved: true,
            selfRoutingRejected: false
        )

        XCTAssertEqual(metadata.inputRouteClass, "built_in")
        XCTAssertEqual(metadata.outputRouteClass, "built_in")
        XCTAssertEqual(metadata.outputVolumeBucket, .medium)
        XCTAssertEqual(metadata.muteState, .unmuted)
        XCTAssertEqual(metadata.browserTarget, "chrome")
        XCTAssertEqual(metadata.routeChangeCount, 2)
        XCTAssertEqual(metadata.coreaudiodState, "running")
        XCTAssertTrue(metadata.sleepWakeObserved)
        XCTAssertFalse(metadata.selfRoutingRejected)
    }

    func testSelfRoutingRejectedIsEvidenceFlagNotLeakageReadiness() {
        let metadata = RecordingRouteMetadataService().snapshot(selfRoutingRejected: true)

        XCTAssertTrue(metadata.selfRoutingRejected)
        XCTAssertEqual(metadata.outputVolumeBucket, .unknown)
        XCTAssertEqual(metadata.muteState, .unknown)
    }
}
#endif
