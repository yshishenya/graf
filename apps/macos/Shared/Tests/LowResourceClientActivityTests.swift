import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceClientActivityTests: XCTestCase {
    func testSilentButOpenStreamRemainsActiveFromClientIO() {
        let activity = ClientActivityEvidence(
            microphoneClientCount: 1,
            speakerClientCount: 0,
            microphoneRunning: true,
            speakerRunning: false,
            source: .driverStartStop,
            naturalSilenceAllowed: true
        )

        XCTAssertTrue(activity.hasOpenStream)
        XCTAssertTrue(activity.naturalSilenceAllowed)
    }

    func testClosedStreamCanReturnToIdle() {
        let activity = ClientActivityEvidence(
            microphoneClientCount: 0,
            speakerClientCount: 0,
            microphoneRunning: false,
            speakerRunning: false,
            source: .deviceIsRunning,
            naturalSilenceAllowed: true
        )

        XCTAssertFalse(activity.hasOpenStream)
    }
}
#endif
