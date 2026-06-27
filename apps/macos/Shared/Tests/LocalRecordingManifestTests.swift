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

    func testRecordingMetadataBasenameDoesNotRenameRequiredPackageFiles() throws {
        let metadata = RecordingDisplayMetadata(
            recordingStartedAt: Date(timeIntervalSince1970: 10),
            recordingStoppedAt: Date(timeIntervalSince1970: 20),
            title: "Zoom - 1970-01-01 00:00",
            titleStatus: .generated,
            titleSource: .appContext,
            titleConfidence: .high,
            titleGeneratedAt: Date(timeIntervalSince1970: 30),
            safeFileBasename: "1970-01-01_00-00_zoom-1970-01-01-00-00_ab12cd",
            stableSuffix: "ab12cd"
        )
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .saved,
            directoryId: "dir",
            transcriptionReadiness: .ready,
            tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
            recordingMetadata: metadata
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let decoded = try decoder.decode(LocalRecordingManifest.self, from: encoder.encode(manifest))

        XCTAssertEqual(decoded.recordingMetadata, metadata)
        XCTAssertEqual(decoded.manifestFileName, "manifest.json")
        XCTAssertEqual(decoded.tracks.first { $0.role == .localMic }?.fileName, "mic.wav")
        XCTAssertEqual(decoded.tracks.first { $0.role == .remoteSpeaker }?.fileName, "incoming.wav")
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

    func testReadNormalizesCaptureHealthAgainstMicrophoneStreamFailure() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-manifest-mic-health-\(UUID().uuidString).json")
        defer { try? FileManager.default.removeItem(at: url) }
        let selection = manifestRecordingMicrophoneSelection()
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .degraded,
            directoryId: "dir",
            transcriptionReadiness: .degraded,
            tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
            failureReason: .none,
            durationDifferenceSeconds: 0,
            microphoneSelection: selection,
            microphoneStream: AppOwnedMicrophoneStreamSession(
                sessionId: "session",
                selection: selection,
                permissionState: .granted,
                streamKind: .appOwnedSampleSource,
                frameCount: 0,
                failureReason: .noFrames
            ),
            microphoneStreamHealth: MicrophoneStreamHealth(
                gateStatus: .failed,
                failureReason: .noFrames,
                framesObserved: false,
                timingConfidence: .missing,
                silenceStatus: .unknown,
                cleanupReadiness: .unproven,
                evidenceCodes: ["no_frames"]
            ),
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

        try service.write(manifest, to: url)
        let normalized = try service.read(from: url)

        XCTAssertEqual(normalized.captureHealth?.failureReason, .noFrames)
        XCTAssertEqual(normalized.captureHealth?.gateStatus, .degraded)
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

    func testManifestCarriesMicrophoneStreamMetadata() {
        let selection = manifestRecordingMicrophoneSelection()
        let stream = AppOwnedMicrophoneStreamSession(
            sessionId: "session",
            selection: selection,
            permissionState: .granted,
            streamKind: .appOwnedSampleSource,
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            sampleRate: 48_000,
            channelCount: 1,
            writerSampleRate: 16_000,
            writerChannelCount: 1,
            frameCount: 16_000,
            lastFrameAt: Date(timeIntervalSince1970: 19),
            failureReason: .none
        )
        let health = MicrophoneStreamHealth(
            gateStatus: .passed,
            failureReason: .none,
            framesObserved: true,
            timingConfidence: .usable,
            silenceStatus: .audible,
            cleanupReadiness: .readyForFutureProcessing,
            evidenceCodes: ["mic_graph_ready"]
        )

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                microphoneSelection: selection,
                microphoneStream: stream,
                microphoneStreamHealth: health
            )

        XCTAssertEqual(manifest.microphoneSelection, selection)
        XCTAssertEqual(manifest.microphoneStream, stream)
        XCTAssertEqual(manifest.microphoneStreamHealth, health)
        XCTAssertTrue(manifest.microphoneStream?.provesGraphReadiness == true)
        XCTAssertEqual(manifest.microphoneStreamHealth?.cleanupReadiness, .readyForFutureProcessing)
    }

    func testManifestServiceThreadsAppleProcessingOutcomeMetadata() {
        let outcome = AppleProcessingOutcome(
            candidateId: "apple-candidate-001",
            primaryOutcome: .acceptedForGuidanceOnly,
            validationRows: [
                AppleProcessingValidationRow(
                    candidateId: "apple-candidate-001",
                    candidateKind: .micModeGuidance,
                    routeClass: .builtInSpeakerphone,
                    scenario: .farEndOnly,
                    baselineStatus: .degraded,
                    candidateStatus: .unproven,
                    lineageStatus: .guidanceOnly,
                    speechPreservationStatus: .notMeasured,
                    alignmentStatus: .notMeasured,
                    stabilityStatus: .unproven,
                    diagnosticSafe: true,
                    failureReason: "system_controlled_mic_mode"
                )
            ],
            nextStepRecommendation: .deferToWebRTCAEC3
        )

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session",
                directoryId: "dir",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                appleProcessingOutcome: outcome
            )

        XCTAssertEqual(manifest.appleProcessingOutcome, outcome)
        XCTAssertFalse(manifest.appleProcessingOutcome?.canClaimCleanBuiltinSpeakerphone ?? true)
        XCTAssertEqual(manifest.appleProcessingOutcome?.feature, "038-apple-voice-processing-spike")
    }

    func testAppleProcessingLineageLabelsRoundTripWithoutChangingOriginalTracks() throws {
        let outcomes = AppleProcessingLineageStatus.allPackageTruthLabels.map { lineage in
            let candidateId = "apple-candidate-\(lineage.rawValue)"
            let candidateStatus: AppleProcessingEvidenceStatus = lineage == .blocked ? .blocked : .unproven
            let stabilityStatus: AppleProcessingStabilityStatus = lineage == .blocked ? .blockedRouteTopology : .unproven
            return AppleProcessingOutcome(
                candidateId: candidateId,
                primaryOutcome: .deferToWebRTCAEC3,
                validationRows: [
                    AppleProcessingValidationRow(
                        candidateId: candidateId,
                        candidateKind: .appOwnedGraphVoiceProcessing,
                        routeClass: .builtInSpeakerphone,
                        scenario: .farEndOnly,
                        baselineStatus: .degraded,
                        candidateStatus: candidateStatus,
                        lineageStatus: lineage,
                        speechPreservationStatus: .notMeasured,
                        alignmentStatus: .notMeasured,
                        stabilityStatus: stabilityStatus,
                        diagnosticSafe: true
                    )
                ],
                nextStepRecommendation: .deferToWebRTCAEC3
            )
        }
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        for outcome in outcomes {
            let manifest = LocalRecordingManifest(
                sessionId: "session-\(outcome.candidateId)",
                createdAt: Date(timeIntervalSince1970: 30),
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                status: .degraded,
                directoryId: "dir",
                transcriptionReadiness: .degraded,
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
                appleProcessingOutcome: outcome
            )

            let decoded = try decoder.decode(LocalRecordingManifest.self, from: encoder.encode(manifest))

            XCTAssertEqual(decoded.appleProcessingOutcome, outcome)
            XCTAssertEqual(decoded.tracks.first { $0.role == AudioTrackRole.localMic }?.fileName, "mic.wav")
            XCTAssertEqual(decoded.tracks.first { $0.role == AudioTrackRole.remoteSpeaker }?.fileName, "incoming.wav")
            XCTAssertEqual(Set(decoded.tracks.map { $0.evidenceRole }), Set<LeakageEvidenceRole>([.original]))
        }
    }

    func testWebRTCAEC3OutcomeRoundTripsWithoutChangingOriginalTracks() throws {
        let outcome = webRTCAEC3GuidanceOutcome()
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .manifest(
                sessionId: "session-aec3",
                directoryId: "dir-aec3",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                webRTCAEC3Outcome: outcome
            )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let decoded = try decoder.decode(LocalRecordingManifest.self, from: encoder.encode(manifest))

        XCTAssertEqual(decoded.webRTCAEC3Outcome, outcome)
        XCTAssertEqual(decoded.tracks.first { $0.role == .localMic }?.fileName, "mic.wav")
        XCTAssertEqual(decoded.tracks.first { $0.role == .remoteSpeaker }?.fileName, "incoming.wav")
        XCTAssertEqual(Set(decoded.tracks.map { $0.evidenceRole }), Set<LeakageEvidenceRole>([.original]))
        XCTAssertFalse(decoded.webRTCAEC3Outcome?.canClaimCleanBuiltInSpeakerphone ?? true)
    }

    func testReadLegacyManifestWithoutMicrophoneMetadataLeavesOptionalFieldsNil() throws {
        let manifest = LocalRecordingManifest(
            sessionId: "legacy-session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .saved,
            directoryId: "dir",
            transcriptionReadiness: .ready,
            tracks: [completeTrack(role: .localMic), completeTrack(role: .remoteSpeaker)],
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let data = try encoder.encode(manifest)
        let decoded = try decoder.decode(LocalRecordingManifest.self, from: data)

        XCTAssertNil(decoded.microphoneSelection)
        XCTAssertNil(decoded.microphoneStream)
        XCTAssertNil(decoded.microphoneStreamHealth)
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

    func testDiagnosticOnlyReadinessWarningsRemainUploadEligibleWhenFilesArePresent() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-eligibility-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let manifestURL = root.appendingPathComponent("manifest.json")
        let microphoneURL = root.appendingPathComponent("mic.wav")
        let systemAudioURL = root.appendingPathComponent("incoming.wav")
        try Data(repeating: 1, count: 128).write(to: microphoneURL)
        try Data(repeating: 2, count: 128).write(to: systemAudioURL)

        let failedReadiness = LocalRecordingManifest(
            sessionId: "failed-readiness-session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .failed,
            directoryId: "failed-readiness-dir",
            transcriptionReadiness: .failed,
            tracks: [
                completeTrack(role: .localMic),
                completeTrack(role: .remoteSpeaker)
            ],
            failureReason: .leakageDetected,
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )
        try LocalRecordingManifestService().write(failedReadiness, to: manifestURL)
        let failedReadinessProfile = DesktopUploadQueueService.artifactProfile(
            manifest: failedReadiness,
            manifestURL: manifestURL,
            microphoneURL: microphoneURL,
            systemAudioURL: systemAudioURL
        )

        XCTAssertEqual(failedReadiness.status, .failed)
        XCTAssertEqual(failedReadiness.transcriptionReadiness, .failed)
        XCTAssertTrue(failedReadinessProfile.microphonePresent)
        XCTAssertTrue(failedReadinessProfile.systemAudioPresent)
        XCTAssertTrue(failedReadinessProfile.isUploadable)
        XCTAssertEqual(failedReadinessProfile.qualityWarningReason, LocalRecordingFailureReason.leakageDetected.rawValue)
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

    func testBlockedSessionOrMissingTrackCannotBeRescuedByQualityWarningReason() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("local-recording-hard-block-eligibility-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let manifestURL = root.appendingPathComponent("manifest.json")
        let microphoneURL = root.appendingPathComponent("mic.wav")
        let systemAudioURL = root.appendingPathComponent("incoming.wav")
        try Data(repeating: 1, count: 128).write(to: microphoneURL)
        try Data(repeating: 2, count: 128).write(to: systemAudioURL)

        let blockedQualityWarning = LocalRecordingManifest(
            sessionId: "blocked-quality-session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .blocked,
            directoryId: "blocked-quality-dir",
            transcriptionReadiness: .failed,
            tracks: [
                completeTrack(role: .localMic),
                completeTrack(role: .remoteSpeaker)
            ],
            failureReason: .leakageDetected,
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )
        let blockedProfile = DesktopUploadQueueService.artifactProfile(
            manifest: blockedQualityWarning,
            manifestURL: manifestURL,
            microphoneURL: microphoneURL,
            systemAudioURL: systemAudioURL
        )

        let missingTrack = LocalRecordingManifest(
            sessionId: "missing-track-session",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .degraded,
            directoryId: "missing-track-dir",
            transcriptionReadiness: .degraded,
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
                    timelineAligned: false,
                    failureReason: .emptyRequiredTrack
                )
            ],
            failureReason: .emptyRequiredTrack,
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )
        let missingTrackProfile = DesktopUploadQueueService.artifactProfile(
            manifest: missingTrack,
            manifestURL: manifestURL,
            microphoneURL: microphoneURL,
            systemAudioURL: systemAudioURL
        )

        XCTAssertFalse(blockedProfile.isUploadable)
        XCTAssertFalse(missingTrackProfile.isUploadable)
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

private func manifestRecordingMicrophoneSelection() -> RecordingMicrophoneSelection {
    RecordingMicrophoneSelection(
        selectionId: "selection",
        mode: .userSelected,
        inputDeviceId: "built-in",
        inputDisplayName: "Built-in Microphone",
        deviceClass: .builtIn,
        workingDeviceKind: .physical,
        selectionResult: .accepted,
        resolvedAt: Date(timeIntervalSince1970: 9)
    )
}

private func webRTCAEC3GuidanceOutcome() -> WebRTCAEC3DecisionRecord {
    WebRTCAEC3DecisionRecord(
        candidateId: "aec3-guidance",
        primaryOutcome: .acceptedForGuidanceOnly,
        validationRows: [
            WebRTCAEC3ValidationRow(
                rowId: "aec3-guidance-row",
                candidateId: "aec3-guidance",
                scenarioFamily: .farEndOnlyLeakage,
                validationKind: .fullFile,
                routeClass: .builtInSpeakerphone,
                baselineStatus: .leakageDetected,
                candidateStatus: .unproven,
                lineageStatus: .candidateMetadata,
                speechPreservationStatus: .notMeasured,
                residualLeakageStatus: .unproven,
                timingConfidence: .notMeasured,
                referenceStatus: .present,
                stabilityStatus: .unproven,
                thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
                thresholdSummary: "guidance_only",
                appStatusState: .usingOriginalMicTruth,
                diagnosticSafe: true
            )
        ],
        nextStepRecommendation: .guidanceOnly
    )
}
#endif
