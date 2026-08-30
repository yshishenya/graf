import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class CanonicalRecordingManifestTests: XCTestCase {
    func testActiveManifestIsDurableBeforeFramesAndFinalWriteReplacesItAtomically() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("active-manifest-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let url = root.appendingPathComponent("manifest.json")
        let service = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
        let active = service.activeV5Manifest(
            sessionId: "active-session",
            directoryId: "active-directory",
            startedAt: Date(timeIntervalSince1970: 10),
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions()
        )

        try service.write(active, to: url)
        XCTAssertEqual(try service.read(from: url).status, .active)
        XCTAssertEqual(active.tracks.map(\.status), [.recording, .recording])

        let final = service.v5Manifest(
            sessionId: active.sessionId,
            directoryId: active.directoryId,
            startedAt: active.startedAt,
            stoppedAt: Date(timeIntervalSince1970: 20),
            tracks: canonicalTracks(),
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions(),
            echoProcessor: .webrtcAEC3,
            echoProcessingHealth: completedEchoHealth()
        )
        try service.write(final, to: url)

        XCTAssertEqual(try service.read(from: url).status, .saved)
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: root.path), ["manifest.json"])
    }

    func testV5FactoryCreatesExactlyOneASRWaveAndOnePlaybackM4A() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .v5Manifest(
                sessionId: "v5-session",
                directoryId: "v5-directory",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: canonicalTracks(),
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                echoProcessor: .webrtcAEC3,
                echoProcessingHealth: completedEchoHealth()
            )

        XCTAssertEqual(manifest.schemaVersion, LocalRecordingManifest.schemaVersion)
        XCTAssertEqual(manifest.mediaScribeSourceMode, "single_wav_v1")
        XCTAssertEqual(manifest.canonicalMixProfile, LocalRecordingManifest.canonicalMixProfileVersion)
        XCTAssertEqual(manifest.status, .saved)
        XCTAssertEqual(manifest.transcriptionReadiness, .ready)
        XCTAssertEqual(
            manifest.tracks.map(\.fileName),
            ["meeting-transcription.wav", "meeting-review.m4a"]
        )
        XCTAssertEqual(manifest.tracks.map(\.mediaScribeField), [.mediaFile, .playbackFile])
        XCTAssertTrue(manifest.isV5Package)
        XCTAssertTrue(manifest.isComplete)
        XCTAssertFalse(manifest.externalEgressStarted)
        XCTAssertFalse(manifest.transcriptionStarted)
        XCTAssertEqual(manifest.echoProcessor, .webrtcAEC3)
        XCTAssertEqual(manifest.echoProcessingHealth?.state, .completed)
    }

    func testV5FactoryFailsClosedWhenTheCanonicalWaveIsUnavailable() {
        var tracks = canonicalTracks()
        tracks[0].status = .missing
        tracks[0].byteCount = 0
        tracks[0].frameCount = 0

        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .v5Manifest(
                sessionId: "missing-media",
                directoryId: "missing-media",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: tracks,
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                echoProcessor: .webrtcAEC3,
                echoProcessingHealth: completedEchoHealth()
            )

        XCTAssertEqual(manifest.status, .degraded)
        XCTAssertEqual(manifest.transcriptionReadiness, .degraded)
        XCTAssertFalse(manifest.isComplete)
        XCTAssertFalse(manifest.tracks[0].isCanonicalTranscriptionArtifact)
    }

    func testV5FactoryBlocksPermissionFailureWithoutPublishingArtifacts() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .v5Manifest(
                sessionId: "blocked",
                directoryId: "blocked",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: canonicalTracks(),
                failureReason: .permissionDenied,
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                echoProcessor: .webrtcAEC3,
                echoProcessingHealth: completedEchoHealth()
            )

        XCTAssertEqual(manifest.status, .blocked)
        XCTAssertEqual(manifest.failureReason, .permissionDenied)
        XCTAssertFalse(manifest.isComplete)
    }

    func testV5PlaybackRequiresRecordedAACPresentationTiming() {
        var tracks = canonicalTracks()
        tracks[1].aacPresentationFrameDelta = LocalRecordingTrack.maximumAACPresentationDeltaFrames + 1

        let manifest = LocalRecordingManifest(
            sessionId: "invalid-playback",
            createdAt: Date(timeIntervalSince1970: 30),
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            status: .saved,
            directoryId: "invalid-playback",
            transcriptionReadiness: .ready,
            mediaScribeSourceMode: "single_wav_v1",
            canonicalMixProfile: LocalRecordingManifest.canonicalMixProfileVersion,
            tracks: tracks,
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions(),
            echoProcessor: .webrtcAEC3,
            echoProcessingHealth: completedEchoHealth()
        )

        XCTAssertTrue(tracks[0].isCanonicalTranscriptionArtifact)
        XCTAssertFalse(tracks[1].isReviewPlaybackArtifact)
        XCTAssertFalse(manifest.isComplete)
    }

    func testV5ManifestRoundTripsWithoutRawAudioOrTranscriptFields() throws {
        let service = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("canonical-manifest-\(UUID().uuidString).json")
        defer { try? FileManager.default.removeItem(at: url) }

        let manifest = service.v5Manifest(
            sessionId: "round-trip",
            directoryId: "round-trip",
            startedAt: Date(timeIntervalSince1970: 10),
            stoppedAt: Date(timeIntervalSince1970: 20),
            tracks: canonicalTracks(),
            scopeApproval: acceptedScopeApproval(),
            permissions: grantedPermissions(),
            echoProcessor: .webrtcAEC3,
            echoProcessingHealth: completedEchoHealth()
        )
        try service.write(manifest, to: url)
        let data = try Data(contentsOf: url)
        let decoded = try service.read(from: url)

        XCTAssertEqual(decoded, manifest)
        XCTAssertEqual(decoded.echoProcessor, .webrtcAEC3)
        XCTAssertEqual(decoded.echoProcessingHealth?.processedFrameCount, 1_000)
        XCTAssertFalse(String(decoding: data, as: UTF8.self).contains("rawAudio"))
        XCTAssertFalse(String(decoding: data, as: UTF8.self).contains("transcriptText"))
    }

    func testV5ManifestPreservesPausePrivacyIntervalWithoutFabricatedTrack() throws {
        let segment = ProductPrivacySegment(
            segmentId: "privacy-1",
            sessionId: "paused-session",
            control: .pause,
            startedAt: Date(timeIntervalSince1970: 14),
            endedAt: Date(timeIntervalSince1970: 16),
            startMonotonicMs: 4_000,
            endMonotonicMs: 6_000,
            localMicTreatment: .silenced
        )
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .v5Manifest(
                sessionId: "paused-session",
                directoryId: "paused-session",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: canonicalTracks(),
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                privacySegments: [segment],
                echoProcessor: .webrtcAEC3,
                echoProcessingHealth: completedEchoHealth()
            )

        XCTAssertEqual(manifest.privacySegments, [segment])
        XCTAssertEqual(manifest.tracks.count, 2)
        XCTAssertEqual(manifest.privacySegments?.first?.durationMs, 2_000)
    }

    func testV5ManifestKeepsSourceFailureTruth() {
        let manifest = LocalRecordingManifestService(clock: { Date(timeIntervalSince1970: 30) })
            .v5Manifest(
                sessionId: "source-loss",
                directoryId: "source-loss",
                startedAt: Date(timeIntervalSince1970: 10),
                stoppedAt: Date(timeIntervalSince1970: 20),
                tracks: canonicalTracks(),
                failureReason: .deviceUnavailable,
                scopeApproval: acceptedScopeApproval(),
                permissions: grantedPermissions(),
                echoProcessor: .webrtcAEC3,
                echoProcessingHealth: completedEchoHealth()
            )

        XCTAssertEqual(manifest.status, .failed)
        XCTAssertEqual(manifest.failureReason, .deviceUnavailable)
        XCTAssertFalse(manifest.isComplete)
    }
}

final class HistoricalRecordingPackageCompatibilityTests: XCTestCase {
    func testV3AndV4PackagesRemainReadableButAreNeverV5() throws {
        let service = LocalRecordingManifestService()

        for version in ["local-recording-manifest.v3", "local-recording-manifest.v4"] {
            let url = FileManager.default.temporaryDirectory
                .appendingPathComponent("historical-manifest-\(UUID().uuidString).json")
            defer { try? FileManager.default.removeItem(at: url) }
            let historical = historicalManifest(schemaVersion: version)
            try service.write(historical, to: url)
            let decoded = try service.read(from: url)

            XCTAssertTrue(decoded.isHistoricCompatibilityPackage)
            XCTAssertTrue(decoded.isComplete)
            XCTAssertFalse(decoded.isV5Package)
            XCTAssertEqual(decoded.transcriptionReadiness, .ready)
            XCTAssertNil(decoded.echoProcessor)
            XCTAssertNil(decoded.echoProcessingHealth)
        }
    }

    func testUnknownHistoricalFailureDecodesToNeutralCompatibilityState() throws {
        let historical = historicalManifest(schemaVersion: "local-recording-manifest.v3")
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        var object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: encoder.encode(historical)) as? [String: Any]
        )
        object["failureReason"] = "retired_capture_state"
        let data = try JSONSerialization.data(withJSONObject: object)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let decoded = try decoder.decode(LocalRecordingManifest.self, from: data)

        XCTAssertEqual(decoded.failureReason, .historicalPackage)
        XCTAssertTrue(decoded.isHistoricCompatibilityPackage)
    }

    func testHistoricalPackageRemainsUploadableOnlyThroughCompatibilityQueue() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("historical-upload-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = root.appendingPathComponent("historical-recording", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try Data(repeating: 0, count: 128).write(to: directory.appendingPathComponent("mic.wav"))
        try Data(repeating: 0, count: 128).write(to: directory.appendingPathComponent("incoming.wav"))

        let manifest = historicalManifest(schemaVersion: "local-recording-manifest.v3")
        try LocalRecordingManifestService().write(manifest, to: directory.appendingPathComponent("manifest.json"))
        let queue = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let item = try XCTUnwrap(queue.scanAndEnqueueCompletedRecordings().first)
        let descriptors = DesktopUploadClient.uploadFileDescriptors(for: item)
        let payload = DesktopUploadClient.createMeetingPayload(for: item)

        XCTAssertFalse(item.isV5Package)
        XCTAssertTrue(item.artifactProfile.isUploadable)
        XCTAssertEqual(descriptors.map(\.transportRole), [.microphone, .system, .manifest])
        XCTAssertEqual(payload.source_kind, "initial_recording")
        XCTAssertEqual(payload.media_scribe_source_mode, "dual")
    }
}

private func canonicalTracks() -> [LocalRecordingTrack] {
    [
        LocalRecordingTrack(
            trackId: "media",
            role: .mixedMeetingAudio,
            sourceKind: .canonicalMix,
            mediaScribeField: .mediaFile,
            status: .saved,
            fileName: "meeting-transcription.wav",
            format: "wav-pcm-s16le",
            sampleRate: 16_000,
            channelCount: 1,
            bitsPerSample: 16,
            durationMs: 10_000,
            byteCount: 320_044,
            sha256: String(repeating: "a", count: 64),
            frameCount: 160_000,
            timelineStartMs: 0,
            timelineAligned: true
        ),
        LocalRecordingTrack(
            trackId: "playback",
            role: .reviewPlayback,
            sourceKind: .canonicalMix,
            mediaScribeField: .playbackFile,
            status: .saved,
            fileName: "meeting-review.m4a",
            format: "m4a-aac-lc",
            sampleRate: 48_000,
            channelCount: 1,
            bitsPerSample: 0,
            durationMs: 10_000,
            byteCount: 120_000,
            sha256: String(repeating: "b", count: 64),
            frameCount: 480_000,
            aacPresentationFrameDelta: 0,
            timelineStartMs: 0,
            timelineAligned: true
        )
    ]
}

private func completedEchoHealth() -> EchoProcessingHealth {
    EchoProcessingHealth(
        state: .completed,
        processedFrameCount: 1_000,
        estimatedDriftPpm: 0,
        aecDelayMs: 20,
        echoReturnLossDb: 10,
        echoReturnLossEnhancementDb: 25,
        processingTimeP95Ms: 1
    )
}

private func historicalManifest(schemaVersion: String) -> LocalRecordingManifest {
    LocalRecordingManifest(
        schemaVersion: schemaVersion,
        sessionId: "historical-\(schemaVersion)",
        createdAt: Date(timeIntervalSince1970: 30),
        startedAt: Date(timeIntervalSince1970: 10),
        stoppedAt: Date(timeIntervalSince1970: 20),
        status: .saved,
        directoryId: "historical",
        transcriptionReadiness: .ready,
        mediaScribeSourceMode: "dual",
        canonicalMixProfile: nil,
        tracks: [
            LocalRecordingTrack(
                trackId: "mic",
                role: .localMic,
                sourceKind: .microphone,
                mediaScribeField: .micFile,
                status: .saved,
                fileName: "mic.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 10_000,
                byteCount: 320_044,
                frameCount: 160_000,
                timelineStartMs: 0,
                timelineAligned: true
            ),
            LocalRecordingTrack(
                trackId: "system",
                role: .remoteSpeaker,
                sourceKind: .systemAudio,
                mediaScribeField: .incomingFile,
                status: .saved,
                fileName: "incoming.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 10_000,
                byteCount: 320_044,
                frameCount: 160_000,
                timelineStartMs: 0,
                timelineAligned: true
            )
        ],
        scopeApproval: acceptedScopeApproval(),
        permissions: grantedPermissions()
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
