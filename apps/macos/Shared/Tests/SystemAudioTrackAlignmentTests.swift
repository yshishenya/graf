import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioTrackAlignmentTests: XCTestCase {
    func testDurationDifferenceWithinThreeSecondsIsAccepted() {
        let health = CaptureHealthMonitor().snapshot(
            sessionId: "session",
            phase: .activeRecording,
            micDurationMs: 10_000,
            incomingDurationMs: 12_999,
            micFrameCount: 160_000,
            incomingFrameCount: 207_984
        )

        XCTAssertEqual(health.durationDifferenceSeconds, 2.999, accuracy: 0.001)
        XCTAssertEqual(health.gateStatus, .passed)
    }

    func testDurationDifferenceAboveThreeSecondsFailsAlignment() {
        let health = CaptureHealthMonitor().snapshot(
            sessionId: "session",
            phase: .activeRecording,
            micDurationMs: 10_000,
            incomingDurationMs: 13_001,
            micFrameCount: 160_000,
            incomingFrameCount: 208_016
        )

        XCTAssertEqual(health.durationDifferenceSeconds, 3.001, accuracy: 0.001)
        XCTAssertEqual(health.gateStatus, .failed)
        XCTAssertEqual(health.failureReason, .timelineMisaligned)
    }
}
#endif
