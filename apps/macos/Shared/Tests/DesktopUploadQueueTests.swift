import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DesktopUploadQueueTests: XCTestCase {
    func testBackendRoleMappingUsesTransportVocabulary() {
        XCTAssertEqual(DesktopUploadTransportRole.role(forLocalTrackRole: .localMic), .microphone)
        XCTAssertEqual(DesktopUploadTransportRole.role(forLocalTrackRole: .remoteSpeaker), .system)
        XCTAssertNil(DesktopUploadTransportRole.role(forLocalTrackRole: .derivedLocalMic))
    }

    func testTerminalUploadStateDoesNotRegressToQueued() {
        let item = makeQueueItem(state: .uploaded, retryMode: .terminal)
        let changed = item.withTransition(to: .queued, now: Date(timeIntervalSince1970: 20))

        XCTAssertEqual(changed.state, .uploaded)
        XCTAssertEqual(changed.retryMode, .terminal)
    }

    func testScanEnqueuesCompletedRecordingOnce() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        let package = try makeRecordingPackage(root: root, directoryId: "package-1", sessionId: "session-1")
        let queueURL = root.appendingPathComponent("queue.json")
        let service = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let firstScan = try service.scanAndEnqueueCompletedRecordings()
        let secondScan = try service.scanAndEnqueueCompletedRecordings()

        XCTAssertTrue(FileManager.default.fileExists(atPath: package.manifestURL.path))
        XCTAssertEqual(firstScan.count, 1)
        XCTAssertEqual(secondScan.count, 1)
        XCTAssertEqual(secondScan.first?.directoryId, "package-1")
        XCTAssertEqual(secondScan.first?.sessionId, "session-1")
        XCTAssertEqual(secondScan.first?.state, .queued)
        XCTAssertTrue(secondScan.first?.artifactProfile.isUploadable == true)
    }

    func testIncompletePackageBecomesBlockedAndManualOnly() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "package-2", sessionId: "session-2", includeIncoming: false)
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )

        let items = try service.scanAndEnqueueCompletedRecordings()

        XCTAssertEqual(items.first?.state, .blocked)
        XCTAssertEqual(items.first?.retryMode, .manualOnly)
        XCTAssertEqual(items.first?.failureCategory, .schemaIncompatibility)
    }

    func testRetentionExpiryMovesRetryingItemToManualOnlyWithoutDeletingArtifacts() throws {
        let root = temporaryRoot()
        defer { try? FileManager.default.removeItem(at: root) }
        _ = try makeRecordingPackage(root: root, directoryId: "package-3", sessionId: "session-3")
        let service = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            policy: LocalBufferPolicy(
                maxBytesPerDevice: 2_000_000_000,
                warningFraction: 0.75,
                criticalFraction: 0.9,
                minimumDiskReserveBytes: 20 * 1024 * 1024,
                retentionDays: 1
            ),
            client: nil,
            clock: { Date(timeIntervalSince1970: 100) }
        )
        let item = try service.scanAndEnqueueCompletedRecordings().first!
        _ = try service.stopRetry(itemId: item.id)
        _ = try service.retry(itemId: item.id)
        let expiredService = DesktopUploadQueueService(
            queueURL: root.appendingPathComponent("queue.json"),
            recordingsRootURL: root,
            policy: LocalBufferPolicy(
                maxBytesPerDevice: 2_000_000_000,
                warningFraction: 0.75,
                criticalFraction: 0.9,
                minimumDiskReserveBytes: 20 * 1024 * 1024,
                retentionDays: 1
            ),
            client: nil,
            clock: { Date(timeIntervalSince1970: 200_000) }
        )

        let expired = try expiredService.applyRetentionExpiry()

        XCTAssertEqual(expired.first?.state, .blocked)
        XCTAssertEqual(expired.first?.retryMode, .manualOnly)
        XCTAssertEqual(expired.first?.retentionDecision.localArtifactsRetained, true)
        XCTAssertEqual(expired.first?.failureReason, "automatic_retry_window_expired")
    }

    private func makeQueueItem(
        state: UploadItemState = .queued,
        retryMode: UploadRetryMode = .automatic
    ) -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: true,
            microphonePresent: true,
            systemAudioPresent: true,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: String(repeating: "b", count: 64),
            systemAudioSha256: String(repeating: "c", count: 64),
            manifestSizeBytes: 128,
            microphoneSizeBytes: 100,
            systemAudioSizeBytes: 100,
            durationSeconds: 1,
            trackCompleteness: [],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: "queue-id",
            sessionId: "session",
            directoryId: "directory",
            directoryPath: "/tmp/directory",
            manifestPath: "/tmp/directory/manifest.json",
            microphonePath: "/tmp/directory/mic.wav",
            systemAudioPath: "/tmp/directory/incoming.wav",
            state: state,
            retryMode: retryMode,
            retentionDeadline: Date(timeIntervalSince1970: 1_000),
            createdAt: Date(timeIntervalSince1970: 1),
            updatedAt: Date(timeIntervalSince1970: 1),
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

    private func temporaryRoot() -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("desktop-upload-queue-tests-\(UUID().uuidString)", isDirectory: true)
    }

    private func makeRecordingPackage(
        root: URL,
        directoryId: String,
        sessionId: String,
        includeIncoming: Bool = true
    ) throws -> TestRecordingPackage {
        let directoryURL = root.appendingPathComponent(directoryId, isDirectory: true)
        try FileManager.default.createDirectory(at: directoryURL, withIntermediateDirectories: true)
        let package = TestRecordingPackage(
            directoryURL: directoryURL,
            manifestURL: directoryURL.appendingPathComponent("manifest.json"),
            localMicURL: directoryURL.appendingPathComponent("mic.wav"),
            remoteSpeakerURL: directoryURL.appendingPathComponent("incoming.wav")
        )
        try Data(repeating: 1, count: 128).write(to: package.localMicURL)
        if includeIncoming {
            try Data(repeating: 2, count: 128).write(to: package.remoteSpeakerURL)
        }
        let manifest = makeManifest(directoryId: directoryId, sessionId: sessionId)
        try LocalRecordingManifestService().write(manifest, to: package.manifestURL)
        return package
    }

    private func makeManifest(directoryId: String, sessionId: String) -> LocalRecordingManifest {
        let startedAt = Date(timeIntervalSince1970: 10)
        let stoppedAt = Date(timeIntervalSince1970: 20)
        let tracks = [
            LocalRecordingTrack(
                trackId: "mic-track",
                role: .localMic,
                sourceKind: .microphone,
                status: .saved,
                fileName: "mic.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 10_000,
                byteCount: 128,
                frameCount: 160_000,
                timelineAligned: true
            ),
            LocalRecordingTrack(
                trackId: "incoming-track",
                role: .remoteSpeaker,
                sourceKind: .systemAudio,
                status: .saved,
                fileName: "incoming.wav",
                format: "wav-pcm-s16le",
                sampleRate: 16_000,
                channelCount: 1,
                bitsPerSample: 16,
                durationMs: 10_000,
                byteCount: 128,
                frameCount: 160_000,
                timelineAligned: true
            )
        ]
        return LocalRecordingManifest(
            sessionId: sessionId,
            createdAt: startedAt,
            startedAt: startedAt,
            stoppedAt: stoppedAt,
            status: .saved,
            directoryId: directoryId,
            transcriptionReadiness: .ready,
            tracks: tracks,
            durationDifferenceSeconds: 0,
            scopeApproval: CaptureScopeApproval(
                scopeApprovalId: "scope",
                scopeKind: .display,
                sourceDisplayName: "Display",
                approvedAt: startedAt,
                approvalMode: .userConfirmedSuggestedScope,
                eligibleReason: .manualMeetingScope
            ),
            permissions: SystemAudioPermissionSnapshot(
                microphone: .granted,
                systemAudio: .granted,
                evaluatedAt: startedAt
            )
        )
    }

    private struct TestRecordingPackage {
        let directoryURL: URL
        let manifestURL: URL
        let localMicURL: URL
        let remoteSpeakerURL: URL
    }
}
#endif
