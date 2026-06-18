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

    func testReadNormalizesStaleCaptureHealthAgainstManifestFailure() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-manifest-stale-health-\(UUID().uuidString).json")
        defer { try? FileManager.default.removeItem(at: url) }
        let stale = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .degraded,
            directoryId: "dir",
            transcriptionReadiness: .degraded,
            tracks: [
                completeTrack(role: .localMic),
                LocalRecordingTrack(
                    trackId: "remote",
                    role: .remoteSpeaker,
                    status: .degraded,
                    fileName: "incoming.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1000,
                    byteCount: 32_044,
                    frameCount: 16_000,
                    timelineStartMs: 0,
                    timelineAligned: false,
                    failureReason: .timelineMisaligned
                )
            ],
            failureReason: .timelineMisaligned,
            durationDifferenceSeconds: 0,
            captureHealth: CaptureHealthSnapshot(
                recordingSessionId: "session",
                phase: .stop,
                sampledAt: Date(timeIntervalSince1970: 20),
                coreaudiodCpuPercent: 0,
                appCpuPercent: 0,
                gateStatus: .passed,
                failureReason: .none
            )
        )
        let service = LocalRecordingManifestService()

        try service.write(stale, to: url)
        let normalized = try service.read(from: url)

        XCTAssertEqual(normalized.captureHealth?.failureReason, .timelineMisaligned)
        XCTAssertEqual(normalized.captureHealth?.gateStatus, .failed)
        XCTAssertEqual(normalized.failureReason, .timelineMisaligned)
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

    func testManifestIsCompleteRejectsForgedDurationMismatch() {
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .saved,
            directoryId: "dir",
            transcriptionReadiness: .ready,
            tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
            durationDifferenceSeconds: 3.001,
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )

        XCTAssertFalse(manifest.isComplete)
    }

    func testTrackIsCompleteRejectsHeaderOnlySavedMetadata() {
        let headerOnly = LocalRecordingTrack(
            trackId: "remote",
            role: .remoteSpeaker,
            status: .saved,
            fileName: "incoming.wav",
            format: "wav-pcm-s16le",
            sampleRate: 16_000,
            channelCount: 1,
            bitsPerSample: 16,
            durationMs: 1000,
            byteCount: 44,
            frameCount: 16_000,
            timelineStartMs: 0,
            timelineAligned: true
        )

        XCTAssertFalse(headerOnly.isComplete)
        XCTAssertFalse(headerOnly.isMediaScribeReady)
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

    func testManifestRoundTripsMuteTruthFieldsWithoutChangingTrackRoles() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-manifest-mute-truth-\(UUID().uuidString).json")
        defer { try? FileManager.default.removeItem(at: url) }
        let service = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
        let segment = ProductPrivacySegment(
            segmentId: "segment-1",
            sessionId: "session",
            control: .pause,
            startedAt: Date(timeIntervalSince1970: 12),
            endedAt: Date(timeIntervalSince1970: 13),
            startMonotonicMs: 2_000,
            endMonotonicMs: 3_000
        )
        let manifest = service.manifest(
            sessionId: "session",
            directoryId: "dir",
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions(),
            privacySegments: [segment],
            targetMuteCapability: .chromeTelemost,
            meetingMuteTruthEvidence: [
                MeetingMuteTruthEvidence(
                    evidenceId: "evidence-1",
                    sessionId: "session",
                    targetId: "chrome_telemost",
                    targetDisplayName: "Chrome + Telemost",
                    source: .productPause,
                    status: .meetingMuteUnproven,
                    freshness: .unavailable,
                    limitationCopyShown: true,
                    recordedAt: Date(timeIntervalSince1970: 11)
                )
            ]
        )

        try service.write(manifest, to: url)
        let decoded = try service.read(from: url)

        XCTAssertEqual(decoded.privacySegments?.map(\.segmentId), ["segment-1"])
        XCTAssertEqual(decoded.meetingMuteTruth?.decision, .meetingMuteUnproven)
        XCTAssertEqual(decoded.targetMuteCapability?.targetId, "chrome_telemost")
        XCTAssertEqual(decoded.tracks.map(\.role), [.localMic, .remoteSpeaker])
    }

    func testLegacySchemaIsNotTranscriptionReady() {
        XCTAssertEqual(
            LocalRecordingManifest.transcriptionReadiness(forSchemaVersion: "local-recording-manifest.v1"),
            .legacyNotReady
        )
    }

    func testDegradedSilentInputRecordingPackageRemainsUploadEligibleWhenFilesArePresent() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-eligibility-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let manifestURL = root.appendingPathComponent("manifest.json")
        let microphoneURL = root.appendingPathComponent("mic.wav")
        let systemAudioURL = root.appendingPathComponent("incoming.wav")
        try Data(repeating: 1, count: 128).write(to: microphoneURL)
        try Data(repeating: 2, count: 128).write(to: systemAudioURL)

        let degraded = LocalRecordingManifest(
            sessionId: "degraded-session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .degraded,
            directoryId: "degraded-dir",
            transcriptionReadiness: .degraded,
            tracks: [
                completeTrack(role: .localMic),
                LocalRecordingTrack(
                    trackId: "remote",
                    role: .remoteSpeaker,
                    status: .degraded,
                    fileName: "incoming.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 1000,
                    byteCount: 32_044,
                    frameCount: 16_000,
                    timelineStartMs: 0,
                    timelineAligned: false,
                    failureReason: .silentInput
                )
            ],
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )
        try LocalRecordingManifestService().write(degraded, to: manifestURL)
        let degradedProfile = DesktopUploadQueueService.artifactProfile(
            manifest: degraded,
            manifestURL: manifestURL,
            microphoneURL: microphoneURL,
            systemAudioURL: systemAudioURL
        )

        XCTAssertEqual(degraded.status, .degraded)
        XCTAssertTrue(degradedProfile.microphonePresent)
        XCTAssertTrue(degradedProfile.systemAudioPresent)
        XCTAssertTrue(degradedProfile.isUploadable)
    }

    func testBlockedRecordingPackagesAreNotUploadEligible() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-blocked-eligibility-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let manifestURL = root.appendingPathComponent("manifest.json")
        let microphoneURL = root.appendingPathComponent("mic.wav")
        let systemAudioURL = root.appendingPathComponent("incoming.wav")
        try Data(repeating: 1, count: 128).write(to: microphoneURL)
        try Data(repeating: 2, count: 128).write(to: systemAudioURL)

        let blocked = LocalRecordingManifest(
            sessionId: "blocked-session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .blocked,
            directoryId: "blocked-dir",
            transcriptionReadiness: .failed,
            tracks: [
                LocalRecordingTrack(
                    trackId: "mic",
                    role: .localMic,
                    status: .blocked,
                    fileName: "mic.wav",
                    format: "wav-pcm-s16le",
                    sampleRate: 16_000,
                    channelCount: 1,
                    bitsPerSample: 16,
                    durationMs: 0,
                    byteCount: 44,
                    frameCount: 0,
                    timelineAligned: false,
                    failureReason: .protectedAudioBlocked
                ),
                completeTrack(role: .remoteSpeaker)
            ],
            failureReason: .protectedAudioBlocked,
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )
        try LocalRecordingManifestService().write(blocked, to: manifestURL)
        let blockedProfile = DesktopUploadQueueService.artifactProfile(
            manifest: blocked,
            manifestURL: manifestURL,
            microphoneURL: microphoneURL,
            systemAudioURL: systemAudioURL
        )

        XCTAssertEqual(blocked.status, .blocked)
        XCTAssertFalse(blockedProfile.isUploadable)
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
