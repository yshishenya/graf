import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheEvictionCandidateLoaderTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_800_000_000)
    private let serverRevision = "11111111-1111-4111-8111-111111111111"
    private var root: URL!
    private var recordingsRoot: URL!
    private var queueURL: URL!
    private var scope: RecordingDeletionScope!

    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("f296-loader-\(UUID().uuidString)", isDirectory: true)
        recordingsRoot = root.appendingPathComponent("Recordings", isDirectory: true)
        queueURL = root.appendingPathComponent("upload-queue.json")
        scope = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace",
            actorUserID: "owner"
        )
        try FileManager.default.createDirectory(
            at: recordingsRoot.appendingPathComponent("package", isDirectory: true),
            withIntermediateDirectories: true
        )
        let package = recordingsRoot.appendingPathComponent("package", isDirectory: true)
        try Data(repeating: 1, count: 128).write(to: package.appendingPathComponent("manifest.json"))
        try Data(repeating: 2, count: 1_000).write(to: package.appendingPathComponent("meeting-transcription.wav"))
        try Data(repeating: 3, count: 500).write(to: package.appendingPathComponent("meeting-review.m4a"))
    }

    override func tearDownWithError() throws {
        if let root { try? FileManager.default.removeItem(at: root) }
    }

    func testNewerEligibleItemIsFoundAfterTwentyIneligibleOldestItems() async throws {
        let items = (0..<21).map { index in
            makeItem(
                index: index,
                // The first 20 are older; the last one is newer.
                createdAt: now.addingTimeInterval(-Double(21 - index) * 60)
            )
        }
        try writeQueue(items)

        let scope = try XCTUnwrap(self.scope)
        let loader = LocalCacheEvictionCandidateLoader(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            client: LoaderProofFetcher(eligibleID: "recording-20", serverRevision: serverRevision),
            scopeProvider: { scope },
            maximumCandidates: 20,
            maximumScan: 200,
            proofTimeout: 2
        )

        let candidates = await loader.load()

        XCTAssertEqual(candidates.map(\.itemID), ["recording-20"])
        XCTAssertEqual(candidates.first?.bytes, 1_000)
        XCTAssertEqual(candidates.first?.localRecordingFingerprint,
                       LocalCacheFingerprint.recording("recording-20"))
    }

    func test205CleanedUploadedItemsDoNotStarveANewerEligibleItem() async throws {
        let cleanedRoot = recordingsRoot.appendingPathComponent("cleaned", isDirectory: true)
        try FileManager.default.createDirectory(at: cleanedRoot, withIntermediateDirectories: true)
        try Data(repeating: 1, count: 128).write(to: cleanedRoot.appendingPathComponent("manifest.json"))
        try Data(repeating: 3, count: 500).write(to: cleanedRoot.appendingPathComponent("meeting-review.m4a"))
        // No meeting-transcription.wav: these items were already cleaned.

        var items: [DesktopUploadQueueItem] = []
        for index in 0..<205 {
            var item = makeItem(
                index: index,
                createdAt: now.addingTimeInterval(-Double(400 - index) * 60)
            )
            item.directoryPath = cleanedRoot.path
            item.manifestPath = cleanedRoot.appendingPathComponent("manifest.json").path
            items.append(item)
        }
        let eligible = makeItem(index: 205, createdAt: now)
        items.append(eligible)
        try writeQueue(items)
        let counter = FetchCounter()
        let scope = try XCTUnwrap(self.scope)

        let loader = LocalCacheEvictionCandidateLoader(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            client: LoaderProofFetcher(
                eligibleID: "recording-205",
                serverRevision: serverRevision,
                counter: counter
            ),
            scopeProvider: { scope },
            maximumCandidates: 20,
            maximumScan: 200,
            proofTimeout: 2
        )

        let candidates = await loader.load()

        XCTAssertEqual(candidates.map(\.itemID), ["recording-205"])
        let fetchCount = await counter.value()
        XCTAssertEqual(fetchCount, 1)
    }

    func testCompletedReceiptsAreSkippedBeforeTheProofScan() async throws {
        let scope = try XCTUnwrap(self.scope)
        let items = (0..<3).map { index in
            makeItem(
                index: index,
                createdAt: now.addingTimeInterval(-Double(3 - index) * 60)
            )
        }
        let receiptDirectory = queueURL.deletingLastPathComponent()
            .appendingPathComponent("LocalCacheEviction/receipts", isDirectory: true)
        for index in 0..<2 {
            let item = items[index]
            let store = LocalCacheCleanupReceiptStore(
                receiptDirectoryURL: receiptDirectory,
                action: .manualCleanup,
                localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
                mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId)
            )
            try store.write(LocalCacheCleanupReceipt(
                action: .manualCleanup,
                state: .completed,
                localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
                meetingFingerprint: LocalCacheFingerprint.meeting(item.meetingId),
                mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId),
                playbackRevisionFingerprint: LocalCacheFingerprint.revision(serverRevision),
                verifiedAt: now,
                bytes: 1_000,
                ownerScopeFingerprint: LocalCacheFingerprint.scope(scope),
                appVersion: "test",
                createdAt: now
            ))
        }
        try writeQueue(items)
        let counter = FetchCounter()

        let loader = LocalCacheEvictionCandidateLoader(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            client: LoaderProofFetcher(
                eligibleID: nil,
                serverRevision: serverRevision,
                counter: counter
            ),
            scopeProvider: { scope },
            maximumCandidates: 20,
            maximumScan: 200,
            proofTimeout: 2
        )

        let candidates = await loader.load()

        XCTAssertEqual(candidates.map(\.itemID), ["recording-2"])
        let fetchCount = await counter.value()
        XCTAssertEqual(fetchCount, 1)
    }

    func testLoaderReturnsAtMostMaximumCandidatesEligibleItems() async throws {
        let items = (0..<6).map { index in
            makeItem(
                index: index,
                createdAt: now.addingTimeInterval(-Double(6 - index) * 60)
            )
        }
        try writeQueue(items)

        let scope = try XCTUnwrap(self.scope)
        let loader = LocalCacheEvictionCandidateLoader(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            client: LoaderProofFetcher(
                eligibleID: nil,
                serverRevision: serverRevision
            ),
            scopeProvider: { scope },
            maximumCandidates: 3,
            maximumScan: 200,
            proofTimeout: 2
        )

        let candidates = await loader.load()

        XCTAssertEqual(candidates.count, 3)
        XCTAssertEqual(Set(candidates.map(\.itemID)).count, 3)
    }

    // MARK: - Fixtures

    private func makeItem(index: Int, createdAt: Date) -> DesktopUploadQueueItem {
        let directoryId = "recording-\(index)"
        let localRevision = "rev-\(index)"
        let package = recordingsRoot.appendingPathComponent("package", isDirectory: true)
        let wavData = Data(repeating: 2, count: 1_000)
        let item = DesktopUploadQueueItem(
            id: directoryId,
            sessionId: "session-\(index)",
            directoryId: directoryId,
            localMediaRevisionId: localRevision,
            directoryPath: package.path,
            manifestPath: package.appendingPathComponent("manifest.json").path,
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
            state: .uploaded,
            retryMode: .terminal,
            retentionDeadline: now.addingTimeInterval(300 * 24 * 60 * 60),
            createdAt: createdAt,
            updatedAt: now,
            meetingId: "meeting-\(index)",
            mediaRevisionId: serverRevision,
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
            serverTruth: ServerTruthFingerprint(
                meetingId: "meeting-\(index)",
                uploadStatus: "finalized"
            ),
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
        var result = item
        result.ownerScope = scope
        result.isLocalUnbound = false
        result.serverCreationAttempted = true
        return result
    }

    private func writeQueue(_ items: [DesktopUploadQueueItem]) throws {
        let document = DesktopUploadQueueDocument(updatedAt: now, items: items)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(document).write(to: queueURL, options: .atomic)
    }
}

private actor FetchCounter {
    private var count = 0

    func increment() {
        count += 1
    }

    func value() -> Int {
        count
    }
}

private struct LoaderProofFetcher: DesktopServerProofFetching {
    /// `nil` means every item is eligible.
    let eligibleID: String?
    let serverRevision: String
    var counter: FetchCounter? = nil

    var recordingSessionFingerprint: String? { "session" }

    func fetchServerProof(for item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        await counter?.increment()
        let now = Date()
        let eligible = eligibleID == nil || item.id == eligibleID
        let proof = DesktopServerProof(
            meetingId: item.meetingId,
            deletionState: "none",
            accessState: "owner",
            conflictState: "none",
            playback: DesktopPlaybackProof(
                state: "available",
                canPlay: true,
                reasonCode: "canonical_ready",
                mediaRevisionId: serverRevision,
                localMediaRevisionId: item.localMediaRevisionId,
                objectVerified: true,
                verifiedAt: ServerTimestamp(date: now.addingTimeInterval(-5)),
                automaticRecovery: false
            ),
            uploadSession: DesktopUploadSessionProof(sessionId: "active-session", status: "active"),
            finalizedUpload: DesktopFinalizedUploadProof(
                sessionId: "finalized-session",
                mediaRevisionId: serverRevision,
                localMediaRevisionId: item.localMediaRevisionId,
                archiveAudio: eligible,
                finalizedAt: ServerTimestamp(date: now.addingTimeInterval(-8 * 24 * 60 * 60)),
                status: "finalized"
            ),
            retention: DesktopRetentionProof(
                deleteAfter: ServerTimestamp(date: now.addingTimeInterval(300 * 24 * 60 * 60)),
                policyState: "active"
            )
        )
        return DesktopUploadReconciliation(
            serverTruth: item.serverTruth,
            proof: proof,
            fetchedAt: now.addingTimeInterval(-1)
        )
    }
}
