import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class BluetoothRoutePolicyTests: XCTestCase {
    func testBluetoothRoutesAreManagedPilotNotReleaseReady() {
        let evidence = BluetoothRouteEvidence(
            profileName: "AirPods Hands-Free",
            profileState: .stable,
            inputAvailable: true,
            outputAvailable: true,
            validFrameIntervalsPassed: true,
            oneSidedAudioEvent: false,
            dropoutRate: 0,
            measuredLatencyMs: 25
        )

        XCTAssertEqual(BluetoothRoutePolicy().releaseReadinessStatus(for: evidence), .blocked)
    }

    func testBluetoothProfileSwitchDegradesRoute() {
        let evidence = BluetoothRouteEvidence(
            profileName: "AirPods A2DP",
            profileState: .switching,
            inputAvailable: false,
            outputAvailable: true,
            validFrameIntervalsPassed: false,
            oneSidedAudioEvent: true,
            dropoutRate: 0.01,
            measuredLatencyMs: nil
        )

        XCTAssertEqual(BluetoothRoutePolicy().passthroughStatus(for: evidence), .degraded)
        XCTAssertFalse(BluetoothRoutePolicy().recoveryActions(for: evidence).isEmpty)
    }
}
#endif
