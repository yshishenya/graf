import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceStartupAttemptTests: XCTestCase {
    func testReadyStartupAttemptWithinThreeSecondsPassesGate() {
        let attempt = StartupAttemptEvidence(
            attemptId: "startup-ready",
            trigger: .clientIOOpened,
            startedAt: Date(timeIntervalSince1970: 10),
            completedAt: Date(timeIntervalSince1970: 12),
            durationMs: 2000,
            outcome: .ready
        )

        XCTAssertTrue(attempt.isWithinAcceptedWindow)
    }

    func testBlockedStartupAttemptBeyondThreeSecondsFailsGate() {
        let attempt = StartupAttemptEvidence(
            attemptId: "startup-blocked",
            trigger: .testFixture,
            startedAt: Date(timeIntervalSince1970: 10),
            completedAt: Date(timeIntervalSince1970: 14),
            durationMs: 4000,
            outcome: .blocked,
            blockedReason: "audio_unit_setup_timeout"
        )

        XCTAssertFalse(attempt.isWithinAcceptedWindow)
        XCTAssertEqual(attempt.outcome, .blocked)
    }
}
#endif
