import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LocalRecordingManifestTests: XCTestCase {
    func testCompleteTracksProduceSavedManifest() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    completeTrack(role: .remoteSpeaker)
                ],
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions()
            )

        XCTAssertEqual(manifest.status, .saved)
        XCTAssertEqual(manifest.transcriptionReadiness, .ready)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertFalse(manifest.externalEgressStarted)
        XCTAssertFalse(manifest.transcriptionStarted)
    }

    func testMissingRequiredTrackProducesDegradedManifest() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    LocalRecordingTrack(
                        trackId: "remote",
                        role: .remoteSpeaker,
                        status: .missing,
                        fileName: "incoming.wav",
                        format: "wav-pcm-s16le",
                        sampleRate: 16_000,
                        channelCount: 1,
                        bitsPerSample: 16,
                        durationMs: 0,
                        byteCount: 44,
                        frameCount: 0,
                        timelineStartMs: 0,
                        timelineAligned: false,
                        failureReason: .emptyRequiredTrack
                    )
                ]
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertEqual(manifest.failureReason, .emptyRequiredTrack)
    }

    func testMisalignedTrackProducesDegradedReadiness() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    LocalRecordingTrack(
                        trackId: "remote",
                        role: .remoteSpeaker,
                        status: .saved,
                        fileName: "incoming.wav",
                        format: "wav-pcm-s16le",
                        sampleRate: 16_000,
                        channelCount: 1,
                        bitsPerSample: 16,
                        durationMs: 1000,
                        byteCount: 32_044,
                        frameCount: 16_000,
                        timelineStartMs: 0,
                        timelineAligned: false
                    )
                ]
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertEqual(manifest.failureReason, .timelineMisaligned)
    }

    func testManifestWritesJSON() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-manifest-\(UUID().uuidString).json")
        defer { try? FileManager.default.removeItem(at: url) }
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions()
            )

        try LocalRecordingManifestService().write(manifest, to: url)

        let data = try Data(contentsOf: url)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        XCTAssertEqual(object?["schemaVersion"] as? String, LocalRecordingManifest.schemaVersion)
        XCTAssertEqual(object?["mediaScribeSourceMode"] as? String, "dual")
        XCTAssertEqual(object?["transcriptionReadiness"] as? String, "ready")
    }

    func testCompleteTracksWithoutScopeAndPermissionsStayDegraded() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)]
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertEqual(manifest.failureReason, .permissionDenied)
        XCTAssertFalse(manifest.isComplete)
    }

    func testDuplicateRequiredRoleDoesNotProduceSavedManifest() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [
                    completeTrack(role: .localMic),
                    completeTrack(role: .remoteSpeaker),
                    completeTrack(role: .remoteSpeaker)
                ],
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions()
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertFalse(manifest.isComplete)
    }

    func testManifestCarriesRouteTimelineCorrelation() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
                routeSessionId: "route-session-019",
                autorepairAttemptIds: ["repair-1"],
                routeInterruptionCategory: .autorepairCovered,
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions()
            )

        XCTAssertEqual(manifest.recordingTimelineEvidence?.routeSessionId, "route-session-019")
        XCTAssertEqual(manifest.recordingTimelineEvidence?.autorepairAttemptIds, ["repair-1"])
        XCTAssertEqual(manifest.recordingTimelineEvidence?.interruptionCategory, .autorepairCovered)
        XCTAssertEqual(manifest.recordingTimelineEvidence?.alignmentBand, .accepted)
    }

    func testLegacySchemaIsNotTranscriptionReady() {
        XCTAssertEqual(
            LocalRecordingManifest.transcriptionReadiness(forSchemaVersion: "local-recording-manifest.v1"),
            .legacyNotReady
        )
    }
}

private func completeTrack(role: AudioTrackRole) -> LocalRecordingTrack {
    LocalRecordingTrack(
        trackId: role.rawValue,
        role: role,
        status: .saved,
        fileName: role == .localMic ? "mic.wav" : "incoming.wav",
        format: "wav-pcm-s16le",
        sampleRate: 16_000,
        channelCount: 1,
        bitsPerSample: 16,
        durationMs: 1000,
        byteCount: 32_044,
        frameCount: 16_000,
        timelineStartMs: 0,
        timelineAligned: true
    )
}

private func acceptedScopeApproval() -> CaptureScopeApproval {
    CaptureScopeApproval(
        scopeApprovalId: "scope",
        scopeKind: .display,
        sourceDisplayName: "Current Display",
        approvedAt: Date(timeIntervalSince1970: 9),
        approvalMode: .userConfirmedSuggestedScope,
        eligibleReason: .manualMeetingScope
    )
}

private func grantedPermissions() -> SystemAudioPermissionSnapshot {
    SystemAudioPermissionSnapshot(
        microphone: .granted,
        systemAudio: .granted,
        evaluatedAt: Date(timeIntervalSince1970: 9)
    )
}
#endif
