import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class CaptureControlTests: XCTestCase {
    func testCaptureFailedStartBlockerIsSerializable() {
        XCTAssertEqual(RecordingStartBlocker.captureFailed.rawValue, "capture_failed")
    }

    func testActiveCaptureKeepsVisibleIndicatorAndStopAvailable() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 10) },
            idFactory: { "capture-test-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        let active = try controller.markCapturing()

        XCTAssertEqual(active.visibleIndicatorState, .active)
        XCTAssertTrue(active.stopActionAvailable)
    }

    func testManualStopMovesActiveSessionToStoppedWithReason() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 20) },
            idFactory: { "capture-stop-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        _ = try controller.markCapturing()
        let stopping = try controller.requestStop(reason: .userRequested)
        let stopped = try controller.completeStop()

        XCTAssertEqual(stopping.state, .stopping)
        XCTAssertTrue(stopping.stopActionAvailable)
        XCTAssertEqual(stopped.state, .stopped)
        XCTAssertEqual(stopped.stopReason, .userRequested)
        XCTAssertFalse(stopped.stopActionAvailable)
    }

    func testStopFailureMovesSessionOutOfStoppingState() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 21) },
            idFactory: { "capture-stop-failed-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        _ = try controller.markCapturing()
        _ = try controller.requestStop(reason: .userRequested)
        let failed = try controller.fail(stopReason: .failed, failureCategory: .storageUnsafe)

        XCTAssertEqual(failed.state, .failed)
        XCTAssertEqual(failed.visibleIndicatorState, .error)
        XCTAssertFalse(failed.stopActionAvailable)
        XCTAssertEqual(failed.failureCategory, .storageUnsafe)
    }

    func testBlockedManualStartRecordsFailureCategory() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 30) },
            idFactory: { "capture-blocked-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        let blocked = try controller.blockStart(
            reason: .routeNotReady,
            recoveryAction: "Recheck audio route before recording"
        )

        XCTAssertEqual(blocked.state, .failed)
        XCTAssertEqual(blocked.failureCategory, .routeNotReady)
        XCTAssertEqual(blocked.triggerEvidence["blockedReason"], "route_not_ready")
        XCTAssertEqual(blocked.triggerEvidence["recoveryAction"], "Recheck audio route before recording")
        XCTAssertFalse(blocked.stopActionAvailable)
    }

    func testTrackEvidenceUsesCurrentSession() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 10) },
            idFactory: { "track-test-id" },
            policySnapshotProvider: { "policy-test" }
        )

        let session = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        let track = try controller.makeTrackEvidence(role: .localMic)

        XCTAssertEqual(track.sessionId, session.id)
        XCTAssertEqual(track.role, .localMic)
        XCTAssertEqual(track.state, .capturing)
    }
}
#endif
