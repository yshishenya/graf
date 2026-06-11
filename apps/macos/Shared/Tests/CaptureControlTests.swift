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

    func testStartingCaptureIsVisibleWhileRuntimeAndWriterStart() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 11) },
            idFactory: { "capture-starting-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        let starting = try controller.start()

        XCTAssertEqual(starting.state, .starting)
        XCTAssertEqual(starting.visibleIndicatorState, .ready)
        XCTAssertTrue(starting.stopActionAvailable)
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: starting))
        XCTAssertFalse(CaptureStatusItem.shouldEnableStopButton(for: starting, stopDisabled: true))
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
            recoveryAction: "Refresh local audio status before recording"
        )

        XCTAssertEqual(blocked.state, .failed)
        XCTAssertEqual(blocked.failureCategory, .routeNotReady)
        XCTAssertEqual(blocked.triggerEvidence["blockedReason"], "route_not_ready")
        XCTAssertEqual(blocked.triggerEvidence["recoveryAction"], "Refresh local audio status before recording")
        XCTAssertFalse(blocked.stopActionAvailable)
    }

    func testBlockedOrFailedSessionAllowsRecordRetry() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 31) },
            idFactory: { "capture-retry-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        let blocked = try controller.blockStart(
            reason: .permissionDenied,
            recoveryAction: "Grant permissions, then retry recording"
        )

        XCTAssertFalse(CaptureStatusItem.showsStopButton(for: blocked))
        XCTAssertTrue(CaptureControlView.shouldShowRecordButton(for: blocked))
        XCTAssertTrue(CaptureControlView.shouldEnableRecordButton(for: blocked, recordDisabled: false))

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
    }

    func testPreparingSessionShowsReadinessWithoutStop() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 32) },
            idFactory: { "capture-detecting-id" },
            policySnapshotProvider: { "policy-test" }
        )

        let detecting = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)

        XCTAssertEqual(CaptureStatusItem.statusLabel(for: detecting), "Checking recording readiness")
        XCTAssertFalse(CaptureStatusItem.showsStopButton(for: detecting))
        XCTAssertTrue(CaptureControlView.shouldShowRecordButton(for: detecting))
        XCTAssertFalse(CaptureControlView.shouldEnableRecordButton(for: detecting, recordDisabled: true))
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

    func testUploadSummaryPrefersRetryingItem() {
        let queued = uploadItem(id: "queued", state: .queued, updatedAt: Date(timeIntervalSince1970: 20))
        let retrying = uploadItem(id: "retrying", state: .retrying, updatedAt: Date(timeIntervalSince1970: 10))

        let summary = CaptureControlView.uploadSummary(for: [queued, retrying])

        XCTAssertEqual(summary?.primaryItem.id, "retrying")
        XCTAssertEqual(summary?.pendingCount, 2)
        XCTAssertEqual(summary?.title, "Retrying + 1 more")
    }

    private func uploadItem(
        id: String,
        state: UploadItemState,
        updatedAt: Date
    ) -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: true,
            microphonePresent: true,
            systemAudioPresent: true,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: String(repeating: "b", count: 64),
            systemAudioSha256: String(repeating: "c", count: 64),
            manifestSizeBytes: 64,
            microphoneSizeBytes: 128,
            systemAudioSizeBytes: 128,
            durationSeconds: 1,
            trackCompleteness: [],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: id,
            sessionId: "session-\(id)",
            directoryId: "directory-\(id)",
            directoryPath: "/tmp/\(id)",
            manifestPath: "/tmp/\(id)/manifest.json",
            microphonePath: "/tmp/\(id)/mic.wav",
            systemAudioPath: "/tmp/\(id)/incoming.wav",
            state: state,
            retryMode: .automatic,
            retentionDeadline: Date(timeIntervalSince1970: 100),
            createdAt: Date(timeIntervalSince1970: 1),
            updatedAt: updatedAt,
            artifactProfile: profile,
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: Date(timeIntervalSince1970: 1),
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
    }
}
#endif
