import AVFoundation
import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheCleanupTests: XCTestCase {
    private var root: URL!
    private var recordingsRoot: URL!
    private var queueURL: URL!
    private var receiptDirectory: URL!
    private var scope: RecordingDeletionScope!
    private var item: DesktopUploadQueueItem!
    private var wavData: Data!
    private var reviewData: Data!
    private var manifestData: Data!
    private let now = Date(timeIntervalSince1970: 1_800_000_000)
    private static let serverRevision = "11111111-1111-4111-8111-111111111111"

    override func setUpWithError() throws {
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("f296-cleanup-\(UUID().uuidString)", isDirectory: true)
        recordingsRoot = root.appendingPathComponent("Recordings", isDirectory: true)
        queueURL = root.appendingPathComponent("upload-queue.json")
        receiptDirectory = root.appendingPathComponent("LocalCacheEviction/receipts", isDirectory: true)
        scope = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace-a",
            actorUserID: "owner-a"
        )
        try FileManager.default.createDirectory(at: recordingsRoot, withIntermediateDirectories: true)
        try makeFixture()
    }

    override func tearDownWithError() throws {
        if let root { try? FileManager.default.removeItem(at: root) }
    }

    func testCleanupRemovesOnlyWAVAndKeepsQueueReviewManifestAndPlayback() async throws {
        let queueBefore = try Data(contentsOf: queueURL)
        let fence = makeFence()
        let service = makeService(fetcher: makeFetcher(), fence: fence)

        let outcome = await service.cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .completed(bytes: Int64(wavData.count)))
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.reviewAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.directoryPath))
        XCTAssertEqual(try Data(contentsOf: queueURL), queueBefore)

        let saved = try XCTUnwrap(try decodedQueue().items.first)
        XCTAssertEqual(saved.state, .uploaded)
        XCTAssertEqual(saved.retryMode, item.retryMode)
        XCTAssertEqual(saved.nextRetryAt, item.nextRetryAt)
        XCTAssertEqual(saved.attemptCount, item.attemptCount)
        XCTAssertEqual(saved.syncGeneration, item.syncGeneration)
        XCTAssertEqual(saved.retentionDecision, item.retentionDecision)
        XCTAssertEqual(saved.serverTruth, item.serverTruth)
        XCTAssertNil(saved.serverTruth.finalizedAt)
        XCTAssertTrue(saved.retentionDecision.localArtifactsRetained)
        XCTAssertTrue(DesktopUploadQueueService.canProjectLocalPlayback(
            item: saved,
            recordingsRootURL: recordingsRoot
        ))
        XCTAssertTrue(DesktopUploadQueueService.canOpenLocalPlayback(
            item: saved,
            recordingsRootURL: recordingsRoot
        ))

        let receipts = try receiptFiles()
        XCTAssertEqual(receipts.count, 1)
        let receipt = try decodeReceipt(receipts[0])
        XCTAssertEqual(receipt.schemaVersion, "local-cache-cleanup-receipt.v1")
        XCTAssertEqual(receipt.action, .manualCleanup)
        XCTAssertEqual(receipt.state, .completed)
        XCTAssertEqual(receipt.bytes, Int64(wavData.count))
        XCTAssertEqual(receipt.verifiedAt, now.addingTimeInterval(-5))
        XCTAssertEqual(receipt.createdAt, now)
        XCTAssertEqual(receipt.localRecordingFingerprint, LocalCacheFingerprint.recording(item.directoryId))
        XCTAssertEqual(receipt.meetingFingerprint, LocalCacheFingerprint.meeting(item.meetingId))
        XCTAssertEqual(receipt.mediaRevisionFingerprint, LocalCacheFingerprint.revision(item.localMediaRevisionId))
        XCTAssertEqual(receipt.playbackRevisionFingerprint, LocalCacheFingerprint.revision(Self.serverRevision))
        XCTAssertEqual(receipt.ownerScopeFingerprint, LocalCacheFingerprint.scope(scope))
        XCTAssertTrue(LocalCustodyFileProtection.isProtected(receipts[0]))
        try assertReceiptContainsNoPrivateIdentity(receipts[0])
    }

    func testReceiptMatchesTheContractShape() async throws {
        _ = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)
        let receiptURL = try XCTUnwrap(try receiptFiles().first)
        let object = try XCTUnwrap(
            try JSONSerialization.jsonObject(with: Data(contentsOf: receiptURL)) as? [String: Any]
        )

        XCTAssertEqual(Set(object.keys), [
            "schemaVersion", "action", "state", "localRecordingFingerprint",
            "meetingFingerprint", "mediaRevisionFingerprint", "playbackRevisionFingerprint",
            "verifiedAt", "bytes", "ownerScopeFingerprint", "appVersion", "createdAt",
        ])
        XCTAssertEqual(object["schemaVersion"] as? String, "local-cache-cleanup-receipt.v1")
        XCTAssertEqual(object["action"] as? String, "manual_cleanup")
        XCTAssertEqual(object["state"] as? String, "completed")
        XCTAssertEqual(object["bytes"] as? Int, wavData.count)
        XCTAssertNotNil(ServerTimestamp.parse(try XCTUnwrap(object["verifiedAt"] as? String)))
        XCTAssertNotNil(ServerTimestamp.parse(try XCTUnwrap(object["createdAt"] as? String)))
        XCTAssertFalse((object["appVersion"] as? String ?? "").isEmpty)
    }

    func testStaleProofKeepsTheWAV() async throws {
        let fetcher = makeFetcher { item in
            DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: Self.proof(for: item, now: Date(timeIntervalSince1970: 1_800_000_000)),
                fetchedAt: Date(timeIntervalSince1970: 1_800_000_000 - 121)
            )
        }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .notEligible(primaryReason: .proofStale, allReasons: [.proofStale]))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testStaleVerificationKeepsTheWAV() async throws {
        let now = self.now
        let fetcher = makeFetcher { item in
            var proof = Self.proof(for: item, now: now)
            proof = DesktopServerProof(
                meetingId: proof.meetingId,
                deletionState: proof.deletionState,
                accessState: proof.accessState,
                conflictState: proof.conflictState,
                playback: DesktopPlaybackProof(
                    state: "available",
                    canPlay: true,
                    reasonCode: "canonical_ready",
                    mediaRevisionId: Self.serverRevision,
                    localMediaRevisionId: item.localMediaRevisionId,
                    objectVerified: true,
                    verifiedAt: ServerTimestamp(date: now.addingTimeInterval(-121)),
                    automaticRecovery: false
                ),
                finalizedUpload: proof.finalizedUpload,
                retention: proof.retention
            )
            return DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: proof,
                fetchedAt: now.addingTimeInterval(-1)
            )
        }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .verificationStale, allReasons: [.verificationStale])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testPlaybackNotVerifiedKeepsTheWAV() async throws {
        let now = self.now
        let fetcher = makeFetcher { item in
            var proof = Self.proof(for: item, now: now)
            proof = DesktopServerProof(
                meetingId: proof.meetingId,
                deletionState: proof.deletionState,
                accessState: proof.accessState,
                conflictState: proof.conflictState,
                playback: DesktopPlaybackProof(
                    state: "available",
                    canPlay: true,
                    reasonCode: "canonical_ready",
                    mediaRevisionId: Self.serverRevision,
                    localMediaRevisionId: item.localMediaRevisionId,
                    objectVerified: false,
                    verifiedAt: ServerTimestamp(date: now.addingTimeInterval(-5)),
                    automaticRecovery: false
                ),
                finalizedUpload: proof.finalizedUpload,
                retention: proof.retention
            )
            return DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: proof,
                fetchedAt: now.addingTimeInterval(-1)
            )
        }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .playbackNotVerified, allReasons: [.playbackNotVerified])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testGraceNotElapsedKeepsTheWAV() async throws {
        let now = self.now
        let fetcher = makeFetcher { item in
            var proof = Self.proof(for: item, now: now)
            proof = DesktopServerProof(
                meetingId: proof.meetingId,
                deletionState: proof.deletionState,
                accessState: proof.accessState,
                conflictState: proof.conflictState,
                playback: proof.playback,
                finalizedUpload: DesktopFinalizedUploadProof(
                    sessionId: "session",
                    mediaRevisionId: Self.serverRevision,
                    localMediaRevisionId: item.localMediaRevisionId,
                    archiveAudio: true,
                    finalizedAt: ServerTimestamp(date: now.addingTimeInterval(-24 * 60 * 60)),
                    status: "finalized"
                ),
                retention: proof.retention
            )
            return DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: proof,
                fetchedAt: now.addingTimeInterval(-1)
            )
        }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .graceNotElapsed, allReasons: [.graceNotElapsed])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testRetentionTooCloseKeepsTheWAV() async throws {
        let now = self.now
        let fetcher = makeFetcher { item in
            var proof = Self.proof(for: item, now: now)
            proof = DesktopServerProof(
                meetingId: proof.meetingId,
                deletionState: proof.deletionState,
                accessState: proof.accessState,
                conflictState: proof.conflictState,
                playback: proof.playback,
                finalizedUpload: proof.finalizedUpload,
                retention: DesktopRetentionProof(
                    deleteAfter: ServerTimestamp(date: now.addingTimeInterval(10 * 24 * 60 * 60)),
                    policyState: "active"
                )
            )
            return DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: proof,
                fetchedAt: now.addingTimeInterval(-1)
            )
        }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .retentionTooClose, allReasons: [.retentionTooClose])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testPendingLocalPurgeKeepsTheWAV() async throws {
        item.failureReason = "local_purge_unverified"
        try writeQueue()

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .localPurgePending, allReasons: [.localPurgePending])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testCorruptReviewAudioKeepsTheWAV() async throws {
        // Keep the profile size intact so this exercises the F284 playback
        // check rather than the cheap size gate.
        try Data(repeating: 0, count: reviewData.count).write(to: URL(fileURLWithPath: item.reviewAudioPath))

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .localArtifactsMissing, allReasons: [.localArtifactsMissing])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
    }

    func testMissingReviewAudioKeepsTheWAV() async throws {
        try FileManager.default.removeItem(atPath: item.reviewAudioPath)

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .localArtifactsMissing, allReasons: [.localArtifactsMissing])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
    }

    func testSecondCleanupIsNoopAndDoesNotDuplicateTheReceipt() async throws {
        let service = makeService(fetcher: makeFetcher(), fence: makeFence())
        let first = await service.cleanup(itemID: item.id, action: .manualCleanup)
        XCTAssertEqual(first, .completed(bytes: Int64(wavData.count)))

        let second = await service.cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(second, .noop)
        XCTAssertEqual(try receiptFiles().count, 1)
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.reviewAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
    }

    func testCrashBetweenUnlinkAndCompletedRecoversWithoutSecondDelete() async throws {
        let store = makeReceiptStore()
        try store.write(pendingReceipt(playbackRevision: item.localMediaRevisionId))
        try FileManager.default.removeItem(atPath: item.transcriptionAudioPath)

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .noop)
        let receipts = try receiptFiles()
        XCTAssertEqual(receipts.count, 1)
        let receipt = try decodeReceipt(receipts[0])
        XCTAssertEqual(receipt.state, .completed)
        XCTAssertEqual(receipt.bytes, Int64(wavData.count))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.reviewAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
    }

    func testMissingWAVWithoutPendingReceiptIsUnexpected() async throws {
        try FileManager.default.removeItem(atPath: item.transcriptionAudioPath)

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .unexpectedMissing)
        XCTAssertFalse(FileManager.default.fileExists(atPath: receiptDirectory.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.reviewAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
    }

    func testReceiptWriteFailureKeepsTheWAV() async throws {
        try FileManager.default.createDirectory(
            at: receiptDirectory.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("not a directory".utf8).write(to: receiptDirectory)

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .failed(code: "receipt_write_failed"))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.reviewAudioPath))
    }

    func testProofMissingKeepsTheWAV() async throws {
        let fetcher = makeFetcher { _ in nil }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .notEligible(primaryReason: .proofMissing, allReasons: [.proofMissing]))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertFalse(FileManager.default.fileExists(atPath: receiptDirectory.path))
    }

    func testProofFetchErrorKeepsTheWAV() async throws {
        enum SyntheticError: Error { case offline }
        let fetcher = makeFetcher { _ in throw SyntheticError.offline }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .dependencyUnavailable, allReasons: [.dependencyUnavailable])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testArchiveAudioFalseKeepsTheWAV() async throws {
        let now = self.now
        let archiveFalse = makeFetcher { item in
            var proof = Self.proof(for: item, now: now)
            proof = DesktopServerProof(
                meetingId: proof.meetingId,
                deletionState: proof.deletionState,
                accessState: proof.accessState,
                conflictState: proof.conflictState,
                playback: proof.playback,
                finalizedUpload: DesktopFinalizedUploadProof(
                    sessionId: "session",
                    mediaRevisionId: Self.serverRevision,
                    localMediaRevisionId: item.localMediaRevisionId,
                    archiveAudio: false,
                    finalizedAt: ServerTimestamp(date: now.addingTimeInterval(-8 * 24 * 60 * 60)),
                    status: "finalized"
                ),
                retention: proof.retention
            )
            return DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: proof,
                fetchedAt: now.addingTimeInterval(-1)
            )
        }
        let outcome = await makeService(fetcher: archiveFalse, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .notEligible(primaryReason: .archiveAudioFalse, allReasons: [.archiveAudioFalse]))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testRevisionMismatchKeepsTheWAV() async throws {
        let now = self.now
        let fetcher = makeFetcher { item in
            var proof = Self.proof(for: item, now: now)
            proof = DesktopServerProof(
                meetingId: proof.meetingId,
                deletionState: proof.deletionState,
                accessState: proof.accessState,
                conflictState: proof.conflictState,
                playback: DesktopPlaybackProof(
                    state: "available",
                    canPlay: true,
                    reasonCode: "canonical_ready",
                    mediaRevisionId: "22222222-2222-4222-8222-222222222222",
                    localMediaRevisionId: "other-local-revision",
                    objectVerified: true,
                    verifiedAt: ServerTimestamp(date: now.addingTimeInterval(-5)),
                    automaticRecovery: false
                ),
                finalizedUpload: DesktopFinalizedUploadProof(
                    sessionId: "session",
                    mediaRevisionId: "22222222-2222-4222-8222-222222222222",
                    localMediaRevisionId: "other-local-revision",
                    archiveAudio: true,
                    finalizedAt: ServerTimestamp(date: now.addingTimeInterval(-8 * 24 * 60 * 60)),
                    status: "finalized"
                ),
                retention: proof.retention
            )
            return DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: proof,
                fetchedAt: now.addingTimeInterval(-1)
            )
        }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .notEligible(primaryReason: .revisionMismatch, allReasons: [.revisionMismatch]))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testQueueDeletionOperationDuringProofFetchKeepsTheWAV() async throws {
        let operation = try RecordingDeletionOperation(
            scope: scope,
            target: .meeting(item.meetingId!),
            requestedAt: now
        )
        try writeQueue(deletionOperations: [operation])
        let queueURL = try XCTUnwrap(self.queueURL)
        let changedQueue = try Data(contentsOf: queueURL)
        try writeQueue()
        let fetcher = makeFetcher { item in
            try? changedQueue.write(to: queueURL, options: .atomic)
            return Self.reconciliation(for: item, now: Date(timeIntervalSince1970: 1_800_000_000))
        }

        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .deletionOperationOpen, allReasons: [.deletionOperationOpen])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertFalse(FileManager.default.fileExists(atPath: receiptDirectory.path))
    }

    func testRetentionUnsafeKeepsTheWAV() async throws {
        let now = self.now
        let fetcher = makeFetcher { item in
            let proof = Self.proof(for: item, now: now)
            let unsafe = DesktopServerProof(
                meetingId: proof.meetingId,
                deletionState: proof.deletionState,
                accessState: proof.accessState,
                conflictState: proof.conflictState,
                playback: proof.playback,
                finalizedUpload: proof.finalizedUpload,
                retention: DesktopRetentionProof(
                    deleteAfter: ServerTimestamp(date: now.addingTimeInterval(10 * 24 * 60 * 60)),
                    policyState: "unsafe"
                )
            )
            return DesktopUploadReconciliation(
                serverTruth: item.serverTruth,
                proof: unsafe,
                fetchedAt: now.addingTimeInterval(-1)
            )
        }
        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .notEligible(primaryReason: .retentionUnsafe, allReasons: [.retentionUnsafe]))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testOpenDeletionOperationKeepsTheWAV() async throws {
        let operation = try RecordingDeletionOperation(
            scope: scope,
            target: .meeting(item.meetingId!),
            requestedAt: now
        )
        try writeQueue(deletionOperations: [operation])

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .deletionOperationOpen, allReasons: [.deletionOperationOpen])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testAccountScopeMismatchKeepsTheWAV() async throws {
        let otherScope = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace-b",
            actorUserID: "owner-b"
        )
        let outcome = await makeService(
            fetcher: makeFetcher(),
            fence: makeFence(scope: otherScope)
        ).cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .accountScopeMismatch, allReasons: [.accountScopeMismatch])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testScopeChangeDuringProofFetchKeepsTheWAV() async throws {
        let fenceState = FenceState()
        let fetcher = makeFetcher { item in
            fenceState.disable()
            return Self.reconciliation(for: item, now: Date(timeIntervalSince1970: 1_800_000_000))
        }

        let outcome = await makeService(
            fetcher: fetcher,
            fence: makeFence(state: fenceState)
        ).cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .scopeChanged)
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertFalse(FileManager.default.fileExists(atPath: receiptDirectory.path))
    }

    func testSymlinkSwapDuringProofFetchKeepsTheTarget() async throws {
        let outside = root.appendingPathComponent("outside.wav")
        let outsideBytes = Data("protected target".utf8)
        try outsideBytes.write(to: outside)
        let fetcher = makeFetcher { item in
            try? FileManager.default.removeItem(atPath: item.transcriptionAudioPath)
            try? FileManager.default.createSymbolicLink(
                atPath: item.transcriptionAudioPath,
                withDestinationPath: outside.path
            )
            return Self.reconciliation(for: item, now: Date(timeIntervalSince1970: 1_800_000_000))
        }

        let outcome = await makeService(fetcher: fetcher, fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .localFileChanged)
        XCTAssertEqual(try Data(contentsOf: outside), outsideBytes)
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testPreexistingSymlinkIsRejectedWithoutTouchingTheTarget() async throws {
        let outside = root.appendingPathComponent("outside.wav")
        let outsideBytes = Data("protected target".utf8)
        try outsideBytes.write(to: outside)
        try FileManager.default.removeItem(atPath: item.transcriptionAudioPath)
        try FileManager.default.createSymbolicLink(
            atPath: item.transcriptionAudioPath,
            withDestinationPath: outside.path
        )

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .localArtifactsOutsideRoot, allReasons: [.localArtifactsOutsideRoot])
        )
        XCTAssertEqual(try Data(contentsOf: outside), outsideBytes)
    }

    func testHashMismatchKeepsTheWAV() async throws {
        var changed = try XCTUnwrap(item)
        changed.artifactProfile.trackCompleteness[1].sha256 = String(repeating: "c", count: 64)
        item = changed
        try writeQueue()

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(
            outcome,
            .notEligible(primaryReason: .localIntegrityUnverified, allReasons: [.localIntegrityUnverified])
        )
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testAutomaticReceiptThenManualCleanupIsNoopWithoutDuplicateReceipt() async throws {
        let service = makeService(fetcher: makeFetcher(), fence: makeFence())
        let automatic = await service.cleanup(itemID: item.id, action: .automaticEviction)
        XCTAssertEqual(automatic, .completed(bytes: Int64(wavData.count)))

        let manual = await service.cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(manual, .noop)
        let receipts = try receiptFiles()
        XCTAssertEqual(receipts.count, 1)
        XCTAssertEqual(try decodeReceipt(receipts[0]).action, .automaticEviction)
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.reviewAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
    }

    func testManualReceiptThenAutomaticCleanupIsNoopWithoutDuplicateReceipt() async throws {
        let service = makeService(fetcher: makeFetcher(), fence: makeFence())
        let manual = await service.cleanup(itemID: item.id, action: .manualCleanup)
        XCTAssertEqual(manual, .completed(bytes: Int64(wavData.count)))

        let automatic = await service.cleanup(itemID: item.id, action: .automaticEviction)

        XCTAssertEqual(automatic, .noop)
        let receipts = try receiptFiles()
        XCTAssertEqual(receipts.count, 1)
        XCTAssertEqual(try decodeReceipt(receipts[0]).action, .manualCleanup)
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    func testCrossActionPendingReceiptIsCompletedWithoutDuplicate() async throws {
        let autoStore = LocalCacheCleanupReceiptStore(
            receiptDirectoryURL: receiptDirectory,
            action: .automaticEviction,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
            mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId)
        )
        try autoStore.write(pendingReceipt(
            playbackRevision: item.localMediaRevisionId,
            action: .automaticEviction
        ))
        try FileManager.default.removeItem(atPath: item.transcriptionAudioPath)

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .noop)
        let receipts = try receiptFiles()
        XCTAssertEqual(receipts.count, 1)
        let receipt = try decodeReceipt(receipts[0])
        XCTAssertEqual(receipt.action, .automaticEviction)
        XCTAssertEqual(receipt.state, .completed)
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.reviewAudioPath))
        XCTAssertTrue(FileManager.default.fileExists(atPath: item.manifestPath))
    }

    func testMissingWAVWithoutAnyReceiptStillReportsUnexpected() async throws {
        try FileManager.default.removeItem(atPath: item.transcriptionAudioPath)

        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)

        XCTAssertEqual(outcome, .unexpectedMissing)
        XCTAssertFalse(FileManager.default.fileExists(atPath: receiptDirectory.path))
    }

    func testAutomaticEvictionUsesTheSameReceiptWithAutomaticAction() async throws {
        let outcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .automaticEviction)

        XCTAssertEqual(outcome, .completed(bytes: Int64(wavData.count)))
        let receipts = try receiptFiles()
        XCTAssertEqual(receipts.count, 1)
        XCTAssertEqual(try decodeReceipt(receipts[0]).action, .automaticEviction)
    }

    func testPurgeAfterCleanupStillDeletesReviewManifestAndAcknowledges() async throws {
        let cleanupOutcome = await makeService(fetcher: makeFetcher(), fence: makeFence())
            .cleanup(itemID: item.id, action: .manualCleanup)
        XCTAssertEqual(cleanupOutcome, .completed(bytes: Int64(wavData.count)))
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))

        let purgeClient = PurgeClient(meetingID: item.meetingId!)
        let queueService = DesktopUploadQueueService(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            client: purgeClient
        )
        queueService.setDeletionScope(scope)
        let tasks = try await queueService.acknowledgePendingLocalPurgeTasks()

        XCTAssertEqual(tasks.map(\.state), [.acknowledged])
        let acknowledgements = await purgeClient.acknowledgements
        XCTAssertEqual(acknowledgements.map(\.reason), ["local_artifacts_deleted"])
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.directoryPath))
        let saved = try XCTUnwrap(try queueService.loadItems().first)
        XCTAssertEqual(saved.state, .terminalDeleted)
        XCTAssertFalse(saved.retentionDecision.localArtifactsRetained)
    }

    func testConcurrentCleanupForTheSameItemHasNoSecondDeletion() async throws {
        let gate = CleanupGate()
        let fetcher = makeFetcher { item in
            await gate.wait()
            return Self.reconciliation(for: item, now: Date(timeIntervalSince1970: 1_800_000_000))
        }
        let service = makeService(fetcher: fetcher, fence: makeFence())
        let itemID = item.id
        let expectedBytes = Int64(wavData.count)

        let first = Task { await service.cleanup(itemID: itemID, action: .manualCleanup) }
        await gate.waitForArrival()
        let second = await service.cleanup(itemID: itemID, action: .automaticEviction)

        XCTAssertEqual(second, .failed(code: "cleanup_in_progress"))
        await gate.release()
        let firstOutcome = await first.value
        XCTAssertEqual(firstOutcome, .completed(bytes: expectedBytes))
        let receipts = try receiptFiles()
        XCTAssertEqual(receipts.count, 1)
        XCTAssertEqual(try decodeReceipt(receipts[0]).action, .manualCleanup)
        XCTAssertFalse(FileManager.default.fileExists(atPath: item.transcriptionAudioPath))
    }

    // MARK: - Fixtures

    private func makeFixture() throws {
        let directory = recordingsRoot.appendingPathComponent("recording-1", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        wavData = Data(repeating: 0x2A, count: 4_096)
        manifestData = Data(repeating: 0x7B, count: 128)
        try wavData.write(to: directory.appendingPathComponent("meeting-transcription.wav"))
        try manifestData.write(to: directory.appendingPathComponent("manifest.json"))
        reviewData = try writeReviewM4A(at: directory.appendingPathComponent("meeting-review.m4a"))

        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: true,
            microphonePresent: false,
            systemAudioPresent: false,
            manifestSha256: LocalCacheFingerprint.sha256Hex(manifestData),
            microphoneSha256: nil,
            systemAudioSha256: nil,
            manifestSizeBytes: Int64(manifestData.count),
            microphoneSizeBytes: 0,
            systemAudioSizeBytes: 0,
            durationSeconds: 60,
            trackCompleteness: [
                UploadTrackCompleteness(
                    transportRole: .manifest,
                    fileName: "manifest.json",
                    present: true,
                    byteCount: Int64(manifestData.count),
                    sha256: LocalCacheFingerprint.sha256Hex(manifestData),
                    durationSeconds: 1
                ),
                UploadTrackCompleteness(
                    transportRole: .media,
                    fileName: "meeting-transcription.wav",
                    present: true,
                    byteCount: Int64(wavData.count),
                    sha256: LocalCacheFingerprint.sha256Hex(wavData),
                    durationSeconds: 60
                ),
                UploadTrackCompleteness(
                    transportRole: .playback,
                    fileName: "meeting-review.m4a",
                    present: true,
                    byteCount: Int64(reviewData.count),
                    sha256: LocalCacheFingerprint.sha256Hex(reviewData),
                    durationSeconds: 60
                ),
            ],
            isUploadable: true
        )
        item = DesktopUploadQueueItem(
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
            attemptCount: 1,
            retentionDeadline: now.addingTimeInterval(300 * 24 * 60 * 60),
            createdAt: now.addingTimeInterval(-400 * 24 * 60 * 60),
            updatedAt: now.addingTimeInterval(-60 * 24 * 60 * 60),
            meetingId: "meeting-1",
            mediaRevisionId: "media-revision-1",
            uploadSessionId: "session-1",
            syncGeneration: 2,
            lastReconciledAt: now.addingTimeInterval(-120),
            artifactProfile: profile,
            serverTruth: ServerTruthFingerprint(
                meetingId: "meeting-1",
                mediaRevisionId: "media-revision-1",
                uploadSessionId: "session-1",
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
        item.ownerScope = scope
        item.isLocalUnbound = false
        item.serverCreationAttempted = true
        try writeQueue()
    }

    private func writeReviewM4A(at url: URL) throws -> Data {
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 48_000.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderBitRateKey: 64_000,
        ]
        let format = try XCTUnwrap(AVAudioFormat(standardFormatWithSampleRate: 48_000, channels: 1))
        let buffer = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 48_000))
        buffer.frameLength = 48_000
        buffer.floatChannelData![0].initialize(repeating: 0, count: 48_000)
        do {
            let file = try AVAudioFile(forWriting: url, settings: settings)
            try file.write(from: buffer)
        }
        return try Data(contentsOf: url)
    }

    private func writeQueue(
        deletionOperations: [RecordingDeletionOperation] = []
    ) throws {
        let document = DesktopUploadQueueDocument(
            updatedAt: now,
            items: [item],
            deletionOperations: deletionOperations
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(document).write(to: queueURL, options: .atomic)
    }

    private func decodedQueue() throws -> DesktopUploadQueueDocument {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(DesktopUploadQueueDocument.self, from: Data(contentsOf: queueURL))
    }

    private func makeReceiptStore() -> LocalCacheCleanupReceiptStore {
        LocalCacheCleanupReceiptStore(
            receiptDirectoryURL: receiptDirectory,
            action: .manualCleanup,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
            mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId)
        )
    }

    private func pendingReceipt(
        playbackRevision: String,
        action: LocalCacheCleanupAction = .manualCleanup
    ) -> LocalCacheCleanupReceipt {
        LocalCacheCleanupReceipt(
            action: action,
            state: .pending,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
            meetingFingerprint: LocalCacheFingerprint.meeting(item.meetingId),
            mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId),
            playbackRevisionFingerprint: LocalCacheFingerprint.revision(playbackRevision),
            verifiedAt: now.addingTimeInterval(-5),
            bytes: Int64(wavData.count),
            ownerScopeFingerprint: LocalCacheFingerprint.scope(scope),
            appVersion: "2026.11.16 (296)",
            createdAt: now.addingTimeInterval(-100)
        )
    }

    private func receiptFiles() throws -> [URL] {
        guard FileManager.default.fileExists(atPath: receiptDirectory.path) else { return [] }
        return try FileManager.default.contentsOfDirectory(
            at: receiptDirectory,
            includingPropertiesForKeys: [.isRegularFileKey]
        ).filter { $0.pathExtension == "json" }.sorted { $0.path < $1.path }
    }

    private func decodeReceipt(_ url: URL) throws -> LocalCacheCleanupReceipt {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(LocalCacheCleanupReceipt.self, from: Data(contentsOf: url))
    }

    private func assertReceiptContainsNoPrivateIdentity(_ url: URL) throws {
        let json = String(decoding: try Data(contentsOf: url), as: UTF8.self)
        XCTAssertFalse(json.contains(root.path))
        XCTAssertFalse(json.contains("recording-1"))
        XCTAssertFalse(json.contains("meeting-1"))
        XCTAssertFalse(json.contains("rev-1"))
        XCTAssertFalse(json.contains("meeting-transcription.wav"))
    }

    private func makeFetcher(
        _ handler: @escaping @Sendable (DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? = { item in
            LocalCacheCleanupTests.reconciliation(for: item, now: Date(timeIntervalSince1970: 1_800_000_000))
        }
    ) -> CleanupProofFetcher {
        CleanupProofFetcher(fingerprint: "session", handler: handler)
    }

    private func makeFence(
        state: FenceState = FenceState(),
        scope: RecordingDeletionScope? = nil
    ) -> LocalCacheCleanupScopeFence {
        LocalCacheCleanupScopeFence(scope: scope ?? self.scope, generation: 7) {
            state.isCurrent()
        }
    }

    private func makeService(
        fetcher: CleanupProofFetcher,
        fence: LocalCacheCleanupScopeFence
    ) -> LocalCacheCleanupService {
        let now = self.now
        return LocalCacheCleanupService(
            queueURL: queueURL,
            recordingsRootURL: recordingsRoot,
            receiptDirectoryURL: receiptDirectory,
            client: fetcher,
            appVersion: "2026.11.16 (296)",
            proofTimeout: 1,
            clock: { now },
            fenceProvider: { fence }
        )
    }

    static func reconciliation(
        for item: DesktopUploadQueueItem,
        now: Date
    ) -> DesktopUploadReconciliation {
        DesktopUploadReconciliation(
            serverTruth: item.serverTruth,
            conflictState: .none,
            proof: proof(for: item, now: now),
            fetchedAt: now.addingTimeInterval(-1)
        )
    }

    static func proof(for item: DesktopUploadQueueItem, now: Date) -> DesktopServerProof {
        DesktopServerProof(
            meetingId: item.meetingId,
            deletionState: "none",
            accessState: "owner",
            conflictState: "none",
            playback: DesktopPlaybackProof(
                state: "available",
                canPlay: true,
                reasonCode: "canonical_ready",
                mediaRevisionId: Self.serverRevision,
                localMediaRevisionId: item.localMediaRevisionId,
                objectVerified: true,
                verifiedAt: ServerTimestamp(date: now.addingTimeInterval(-5)),
                automaticRecovery: false
            ),
            uploadSession: DesktopUploadSessionProof(sessionId: "active-session", status: "active"),
            finalizedUpload: DesktopFinalizedUploadProof(
                sessionId: "session-1",
                mediaRevisionId: Self.serverRevision,
                localMediaRevisionId: item.localMediaRevisionId,
                archiveAudio: true,
                finalizedAt: ServerTimestamp(date: now.addingTimeInterval(-8 * 24 * 60 * 60)),
                status: "finalized"
            ),
            retention: DesktopRetentionProof(
                deleteAfter: ServerTimestamp(date: now.addingTimeInterval(300 * 24 * 60 * 60)),
                policyState: "active"
            )
        )
    }
}

// MARK: - Test doubles

private struct CleanupProofFetcher: DesktopServerProofFetching {
    let fingerprint: String?
    let handler: @Sendable (DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation?

    var recordingSessionFingerprint: String? { fingerprint }

    func fetchServerProof(for item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        try await handler(item)
    }
}

private final class FenceState: @unchecked Sendable {
    private let lock = NSLock()
    private var current = true

    func isCurrent() -> Bool {
        lock.lock(); defer { lock.unlock() }
        return current
    }

    func disable() {
        lock.lock(); current = false; lock.unlock()
    }
}

private actor CleanupGate {
    private var continuation: CheckedContinuation<Void, Never>?
    private var arrived = false
    private var arrivedContinuation: CheckedContinuation<Void, Never>?

    func wait() async {
        arrived = true
        arrivedContinuation?.resume()
        arrivedContinuation = nil
        await withCheckedContinuation { self.continuation = $0 }
    }

    func waitForArrival() async {
        if arrived { return }
        await withCheckedContinuation { self.arrivedContinuation = $0 }
    }

    func release() {
        continuation?.resume()
        continuation = nil
    }
}

private actor PurgeClient: DesktopUploadClientProtocol {
    struct Acknowledgement: Sendable {
        let reason: String
    }

    let meetingID: String
    var acknowledgements: [Acknowledgement] = []

    init(meetingID: String) {
        self.meetingID = meetingID
    }

    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        DesktopUploadReconciliation(
            serverTruth: ServerTruthFingerprint(
                meetingId: item.meetingId,
                deletionState: "none",
                accessState: "owner"
            ),
            conflictState: .none
        )
    }

    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        DesktopUploadResult(state: item.state, serverTruth: item.serverTruth)
    }

    func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
        let body = [
            "task_id": UUID().uuidString,
            "meeting_id": meetingID,
            "task_type": "purge_local_buffers",
            "state": "pending",
            "safe_reason": "delete_requested",
            "expires_at": "2020-01-01T00:00:00Z",
        ]
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return [
            try decoder.decode(
                DesktopLocalPurgeTask.self,
                from: JSONSerialization.data(withJSONObject: body)
            ),
        ]
    }

    func acknowledgeLocalPurgeTask(
        _ task: DesktopLocalPurgeTask,
        state: DesktopLocalPurgeTaskState,
        reasonCode: String,
        completedAt: Date?
    ) async throws -> DesktopLocalPurgeTask {
        acknowledgements.append(Acknowledgement(reason: reasonCode))
        let body = [
            "task_id": task.taskId,
            "meeting_id": task.meetingId,
            "task_type": "purge_local_buffers",
            "state": state.rawValue,
            "safe_reason": reasonCode,
            "expires_at": "2020-01-01T00:00:00Z",
        ]
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(
            DesktopLocalPurgeTask.self,
            from: JSONSerialization.data(withJSONObject: body)
        )
    }
}
