import XCTest
@testable import TwoBrainRecShared

final class MeetingDetectionCountdownTests: XCTestCase {
    func testStartReasonsRemainDistinctAndTruthful() {
        XCTAssertEqual(MeetingDetectionStartReason.promptButton.rawValue, "prompt_button")
        XCTAssertEqual(MeetingDetectionStartReason.promptTimeout.rawValue, "prompt_timeout")
        XCTAssertEqual(MeetingDetectionStartReason.savedTargetPolicy.rawValue, "saved_target_policy")
        XCTAssertFalse(MeetingDetectionStartReason.promptButton.isAutomatic)
        XCTAssertTrue(MeetingDetectionStartReason.promptTimeout.isAutomatic)
        XCTAssertTrue(MeetingDetectionStartReason.savedTargetPolicy.isAutomatic)
    }

    func testTimeoutDoesNotResolveBeforeEightSecondsAndResolvesOnceAtBoundary() {
        let start = Date(timeIntervalSince1970: 1_800_000_000)
        var countdown = MeetingDetectionCountdown(startedAt: start)

        XCTAssertNil(countdown.resolveStart(reason: .promptTimeout, at: start.addingTimeInterval(7.999)))
        XCTAssertEqual(countdown.remainingWholeSeconds(at: start), 8)
        XCTAssertEqual(
            countdown.resolveStart(reason: .promptTimeout, at: start.addingTimeInterval(8)),
            .promptTimeout
        )
        XCTAssertNil(countdown.resolveStart(reason: .promptButton, at: start.addingTimeInterval(8)))
    }

    func testButtonResolvesImmediatelyAndCancellationPreventsLateStart() {
        let start = Date(timeIntervalSince1970: 1_800_000_000)
        var button = MeetingDetectionCountdown(startedAt: start)
        XCTAssertEqual(
            button.resolveStart(reason: .promptButton, at: start.addingTimeInterval(1)),
            .promptButton
        )
        XCTAssertNil(button.resolveStart(reason: .promptTimeout, at: start.addingTimeInterval(9)))

        var cancelled = MeetingDetectionCountdown(startedAt: start)
        XCTAssertTrue(cancelled.cancel())
        XCTAssertFalse(cancelled.cancel())
        XCTAssertNil(cancelled.resolveStart(reason: .promptTimeout, at: start.addingTimeInterval(9)))
    }

    func testDisabledButtonStillDeliversElapsedTimeoutForFreshConsumerRecheck() {
        let start = Date(timeIntervalSince1970: 1_800_000_000)
        var countdown = MeetingDetectionCountdown(startedAt: start)

        XCTAssertNil(
            countdown.resolveStart(
                reason: .promptButton,
                at: start.addingTimeInterval(1),
                startIsTemporarilyDisabled: true
            )
        )
        XCTAssertEqual(
            countdown.resolveStart(
                reason: .promptTimeout,
                at: start.addingTimeInterval(8),
                startIsTemporarilyDisabled: true
            ),
            .promptTimeout
        )
    }
}
