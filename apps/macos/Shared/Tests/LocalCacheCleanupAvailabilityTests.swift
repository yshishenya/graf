import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheCleanupAvailabilityTests: XCTestCase {
    private var root: URL!
    private var recordingsRoot: URL!
    private var queueURL: URL!
    private var receiptDirectory: URL!
    private var scope: RecordingDeletionScope!
    private var item: DesktopUploadQueueItem!
    private let now = Date(timeIntervalSince1970: 1_800_000_000)

    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("f296-availability-\(UUID().uuidString)", isDirectory: true)
        recordingsRoot = root.appendingPathComponent("Recordings", isDirectory: true)
        queueURL = root.appendingPathComponent("upload-queue.json")
        receiptDirectory = root.appendingPathComponent("LocalCacheEviction/receipts", isDirectory: true)
        scope = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace",
            actorUserID: "owner"
        )
        try FileManager.default.createDirectory(at: recordingsRoot, withIntermediateDirectories: true)
        item = try makeFixtureItem()
    }

    override func tearDownWithError() throws {
        if let root { try? FileManager.default.removeItem(at: root) }
    }

    func testWAVPresentWithoutReceiptIsOfferable() async {
        let ids = await probe().offerableItemIDs(among: [item])
        XCTAssertEqual(ids, [item.id])
    }

    func testMissingWAVIsNotOfferable() async throws {
        try FileManager.default.removeItem(atPath: item.transcriptionAudioPath)
        let ids = await probe().offerableItemIDs(among: [item])
        XCTAssertTrue(ids.isEmpty)
    }

    func testCompletedReceiptHidesTheAction() async throws {
        try writeReceipt(action: .manualCleanup, state: .completed)
        let ids = await probe().offerableItemIDs(among: [item])
        XCTAssertTrue(ids.isEmpty)
    }

    func testCompletedAutomaticReceiptHidesTheManualAction() async throws {
        try writeReceipt(action: .automaticEviction, state: .completed)
        let ids = await probe().offerableItemIDs(among: [item])
        XCTAssertTrue(ids.isEmpty)
    }

    func testPendingReceiptKeepsTheActionAvailableForRetry() async throws {
        try writeReceipt(action: .automaticEviction, state: .pending)
        let ids = await probe().offerableItemIDs(among: [item])
        XCTAssertEqual(ids, [item.id])
    }

    func testCorruptReceiptFailsClosed() async throws {
        try FileManager.default.createDirectory(at: receiptDirectory, withIntermediateDirectories: true)
        let store = LocalCacheCleanupReceiptStore(
            receiptDirectoryURL: receiptDirectory,
            action: .manualCleanup,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
            mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId)
        )
        try Data("{".utf8).write(to: store.fileURL)

        let ids = await probe().offerableItemIDs(among: [item])
        XCTAssertTrue(ids.isEmpty)
    }

    func testSymlinkWAVIsNotOfferableAndTargetIsUntouched() async throws {
        let outside = root.appendingPathComponent("outside.wav")
        let outsideBytes = Data("protected target".utf8)
        try outsideBytes.write(to: outside)
        try FileManager.default.removeItem(atPath: item.transcriptionAudioPath)
        try FileManager.default.createSymbolicLink(
            atPath: item.transcriptionAudioPath,
            withDestinationPath: outside.path
        )

        let ids = await probe().offerableItemIDs(among: [item])

        XCTAssertTrue(ids.isEmpty)
        XCTAssertEqual(try Data(contentsOf: outside), outsideBytes)
    }

    func testLocalOnlyItemIsNotOfferable() async {
        var localOnly = item!
        localOnly.meetingId = nil
        localOnly.serverTruth.meetingId = nil
        localOnly.isLocalUnbound = true
        let ids = await probe().offerableItemIDs(among: [localOnly])
        XCTAssertTrue(ids.isEmpty)
    }

    // MARK: - Fixtures

    private func probe() -> LocalCacheCleanupAvailabilityProbe {
        LocalCacheCleanupAvailabilityProbe(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            receiptDirectoryURL: receiptDirectory
        )
    }

    private func makeFixtureItem() throws -> DesktopUploadQueueItem {
        let directory = recordingsRoot.appendingPathComponent("recording-1", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let wavData = Data(repeating: 2, count: 1_000)
        try wavData.write(to: directory.appendingPathComponent("meeting-transcription.wav"))
        try Data(repeating: 1, count: 128).write(to: directory.appendingPathComponent("manifest.json"))
        try Data(repeating: 3, count: 500).write(to: directory.appendingPathComponent("meeting-review.m4a"))

        var item = DesktopUploadQueueItem(
            id: "queue-recording-1",
            sessionId: "session-recording-1",
            directoryId: "recording-1",
            localMediaRevisionId: "rev-1",
            directoryPath: directory.path,
            manifestPath: directory.appendingPathComponent("manifest.json").path,
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
            state: .uploaded,
            retryMode: .terminal,
            retentionDeadline: now.addingTimeInterval(300 * 24 * 60 * 60),
            createdAt: now.addingTimeInterval(-400 * 24 * 60 * 60),
            updatedAt: now,
            meetingId: "meeting-1",
            artifactProfile: ArtifactCompletenessProfile(
                schemaVersion: LocalRecordingManifest.schemaVersion,
                manifestPresent: true,
                microphonePresent: false,
                systemAudioPresent: false,
                manifestSha256: String(repeating: "a", count: 64),
                microphoneSha256: nil,
                systemAudioSha256: nil,
                manifestSizeBytes: 128,
                microphoneSizeBytes: 0,
                systemAudioSizeBytes: 0,
                durationSeconds: 60,
                trackCompleteness: [
                    UploadTrackCompleteness(
                        transportRole: .manifest,
                        fileName: "manifest.json",
                        present: true,
                        byteCount: 128,
                        sha256: String(repeating: "a", count: 64),
                        durationSeconds: 1
                    ),
                    UploadTrackCompleteness(
                        transportRole: .media,
                        fileName: "meeting-transcription.wav",
                        present: true,
                        byteCount: 1_000,
                        sha256: LocalCacheFingerprint.sha256Hex(wavData),
                        durationSeconds: 60
                    ),
                    UploadTrackCompleteness(
                        transportRole: .playback,
                        fileName: "meeting-review.m4a",
                        present: true,
                        byteCount: 500,
                        sha256: String(repeating: "c", count: 64),
                        durationSeconds: 60
                    ),
                ],
                isUploadable: true
            ),
            serverTruth: ServerTruthFingerprint(meetingId: "meeting-1", uploadStatus: "finalized"),
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
        item.ownerScope = scope
        item.isLocalUnbound = false
        item.serverCreationAttempted = true
        return item
    }

    private func writeReceipt(
        action: LocalCacheCleanupAction,
        state: LocalCacheCleanupReceiptState
    ) throws {
        let store = LocalCacheCleanupReceiptStore(
            receiptDirectoryURL: receiptDirectory,
            action: action,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
            mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId)
        )
        try store.write(LocalCacheCleanupReceipt(
            action: action,
            state: state,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
            meetingFingerprint: LocalCacheFingerprint.meeting(item.meetingId),
            mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId),
            playbackRevisionFingerprint: LocalCacheFingerprint.revision("11111111-1111-4111-8111-111111111111"),
            verifiedAt: now.addingTimeInterval(-5),
            bytes: 1_000,
            ownerScopeFingerprint: LocalCacheFingerprint.scope(scope),
            appVersion: "test",
            createdAt: now
        ))
    }
}
