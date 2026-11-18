import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheEligibilityTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_800_000_000)
    private var scopeA: RecordingDeletionScope!
    private var scopeB: RecordingDeletionScope!

    override func setUpWithError() throws {
        scopeA = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace-a",
            actorUserID: "owner-a"
        )
        scopeB = try RecordingDeletionScope(
            serverOrigin: "https://sync.invalid",
            workspaceID: "workspace-b",
            actorUserID: "owner-b"
        )
    }

    func testFullProofIsPotentiallyEligible() {
        let item = makeItem()
        let decision = evaluate(
            item: item,
            proof: makeProof(),
            facts: makeFacts(),
            proofFetchedAt: now
        )

        XCTAssertEqual(decision.verdict, .potentiallyEligible)
        XCTAssertEqual(decision.primaryReason, .serverPlaybackReady)
        XCTAssertTrue(decision.allReasons.isEmpty)
        XCTAssertEqual(decision.bytes, 1_100)
    }

    func testNotUploadedKeepsLocal() {
        assertKeep(item: makeItem(state: .queued), expected: .notUploaded)
    }

    func testMissingFinalizationProofKeepsLocal() {
        assertKeep(
            item: makeItem(uploadStatus: nil),
            proof: makeProof { $0.sessionStatus = "uploading"; $0.finalizedAt = nil },
            expected: .notFinalized
        )
    }

    func testServerFinalizedAtWithoutStatusStringIsEligible() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof { $0.sessionStatus = nil },
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.verdict, .potentiallyEligible)
        XCTAssertEqual(decision.primaryReason, .serverPlaybackReady)
    }

    func testMissingServerFinalizedAtKeepsLocalEvenWithPersistedStatus() {
        let decision = evaluate(
            item: makeItem(uploadStatus: "finalized"),
            proof: makeProof { $0.sessionStatus = "finalized"; $0.finalizedAt = nil },
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .notFinalized)
        XCTAssertTrue(decision.allReasons.contains(.notFinalized))
    }

    func testAccountScopeMismatchKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts(),
            scope: scopeB,
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .accountScopeMismatch)
    }

    func testLocalUnboundKeepsLocal() {
        assertKeep(item: makeItem(isLocalUnbound: true), expected: .localUnbound)
    }

    func testMissingOwnerKeepsLocal() {
        var item = makeItem()
        item.ownerScope = nil
        assertKeep(item: item, expected: .localUnbound)
    }

    func testLifecycleUnavailableKeepsLocal() {
        assertKeep(item: makeItem(lifecycleAccessAvailable: false), expected: .lifecycleUnavailable)
    }

    func testOpenDeletionOperationKeepsLocal() throws {
        let operation = try RecordingDeletionOperation(
            scope: scopeA,
            target: .meeting("meeting-1"),
            requestedAt: now
        )
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts(),
            document: makeDocument(operations: [operation]),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .deletionOperationOpen)
    }

    func testOwnOriginDeletionOperationKeepsLocal() throws {
        let operation = try RecordingDeletionOperation(
            scope: scopeA,
            target: .ownOrigin("recordings-directory"),
            requestedAt: now
        )
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts(),
            document: makeDocument(operations: [operation]),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .deletionOperationOpen)
    }

    func testConfirmedServerDeletionKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.deletionState = "complete" },
            expected: .confirmedDeletion
        )
    }

    func testPendingLocalPurgeKeepsLocal() {
        assertKeep(
            item: makeItem(failureReason: "local_purge_unverified"),
            expected: .localPurgePending
        )
    }

    func testSyncConflictKeepsLocal() {
        assertKeep(
            item: makeItem(syncConflictState: .accessRevoked),
            expected: .syncConflict
        )
    }

    func testFreshServerConflictKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.conflictState = "server_meeting_deleted" },
            expected: .syncConflict
        )
    }

    func testMissingProofKeepsLocal() {
        let decision = LocalCacheEligibility.evaluate(
            item: makeItem(),
            document: makeDocument(),
            scope: scopeA,
            proof: nil,
            proofFetchedAt: nil,
            localFacts: makeFacts(),
            now: now
        )
        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .proofMissing)
        XCTAssertEqual(decision.allReasons, [.proofMissing])
    }

    func testStaleProofKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts(),
            proofFetchedAt: now.addingTimeInterval(-121)
        )
        XCTAssertEqual(decision.primaryReason, .proofStale)
    }

    func testMissingProofFetchReceiptKeepsLocal() {
        let decision = LocalCacheEligibility.evaluate(
            item: makeItem(),
            document: makeDocument(),
            scope: scopeA,
            proof: makeProof(),
            proofFetchedAt: nil,
            localFacts: makeFacts(),
            now: now
        )
        XCTAssertEqual(decision.primaryReason, .proofStale)
    }

    func testProofInTheFutureBeyondClockSkewKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts(),
            proofFetchedAt: now.addingTimeInterval(61)
        )
        XCTAssertEqual(decision.primaryReason, .proofStale)
    }

    func testMeetingMismatchKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.meetingId = "other-meeting" },
            expected: .meetingMismatch
        )
    }

    func testMissingMeetingIdentityKeepsLocal() {
        assertKeep(item: makeItem(meetingId: nil), expected: .meetingMismatch)
    }

    func testPlaybackRevisionMismatchKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.playbackRevision = "other-revision" },
            expected: .revisionMismatch
        )
    }

    func testCustodyRevisionMismatchKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.sessionRevision = "22222222-2222-4222-8222-222222222222" },
            expected: .revisionMismatch
        )
    }

    func testPlaybackLocalRevisionMismatchKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.playbackLocalRevision = "other-local-revision" },
            expected: .revisionMismatch
        )
    }

    func testMissingPlaybackLocalRevisionKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.playbackLocalRevision = nil },
            expected: .revisionMismatch
        )
    }

    func testFinalizedUploadLocalRevisionMismatchKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.finalizedLocalRevision = "other-local-revision" },
            expected: .revisionMismatch
        )
    }

    func testFinalizedUploadWithoutLocalRevisionStillUsesPlaybackLocalIdentity() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof { $0.finalizedLocalRevision = nil },
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.verdict, .potentiallyEligible)
    }

    func testPlaybackNotAvailableKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.playbackState = "preparing" },
            expected: .playbackNotAvailable
        )
    }

    func testPlaybackCannotPlayKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.canPlay = false },
            expected: .playbackNotAvailable
        )
    }

    func testNonCanonicalPlaybackReasonKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.reasonCode = "audio_not_archived" },
            expected: .playbackNotAvailable
        )
    }

    func testUnknownPlaybackStateKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof { $0.playbackState = "quantum_ready"; $0.reasonCode = "future_reason" },
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .playbackNotAvailable)
    }

    func testPlaybackNotVerifiedKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.objectVerified = false },
            expected: .playbackNotVerified
        )
    }

    func testMissingVerificationTimestampKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.verifiedAt = nil },
            expected: .verificationStale
        )
    }

    func testStaleVerificationKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.verifiedAt = now.addingTimeInterval(-121) },
            expected: .verificationStale
        )
    }

    func testArchiveAudioFalseKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.archiveAudio = false },
            expected: .archiveAudioFalse
        )
    }

    func testArchiveAudioUnknownKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.archiveAudio = nil },
            expected: .archiveAudioUnknown
        )
    }

    func testGracePeriodNotElapsedKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.finalizedAt = now.addingTimeInterval(-24 * 60 * 60) },
            expected: .graceNotElapsed
        )
    }

    func testUnknownDeletionStateKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.deletionState = nil },
            expected: .deletionStateUnknown
        )
    }

    func testUnrecognizedDeletionStateKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof { $0.deletionState = "future_deletion_state" },
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .deletionStateUnknown)
    }

    func testAccessStateNotOwnerKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.accessState = "member" },
            expected: .accessStateNotOwner
        )
    }

    func testMissingAccessStateKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.accessState = nil },
            expected: .accessStateNotOwner
        )
    }

    func testRetentionUnknownKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.retentionState = "not_configured"; $0.deleteAfter = nil },
            expected: .retentionUnknown
        )
    }

    func testRetentionUnsafeKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.retentionState = "unsafe" },
            expected: .retentionUnsafe
        )
    }

    func testRetentionBlockedKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.retentionState = "blocked" },
            expected: .retentionUnsafe
        )
    }

    func testRetentionExpiredKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.retentionState = "expired" },
            expected: .retentionExpired
        )
    }

    func testPastRetentionDeadlineKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.deleteAfter = now.addingTimeInterval(-1) },
            expected: .retentionExpired
        )
    }

    func testRetentionTooCloseKeepsLocal() {
        assertKeep(
            proof: makeProof { $0.deleteAfter = now.addingTimeInterval(10 * 24 * 60 * 60) },
            expected: .retentionTooClose
        )
    }

    func testMissingLocalArtifactsKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts { $0.reviewAudioPresent = false },
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localArtifactsMissing)
    }

    func testMissingLocalPlaybackProjectionKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts { $0.reviewPlaybackAvailable = false },
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localArtifactsMissing)
    }

    func testNonV5PackageKeepsLocal() {
        let decision = evaluate(
            item: makeItem(schemaVersion: LocalRecordingManifest.legacySchemaVersion),
            proof: makeProof(),
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localArtifactsMissing)
    }

    func testPathOutsideRecordingsRootKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: LocalArtifactFacts(error: .outsideRoot),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localArtifactsOutsideRoot)
        XCTAssertFalse(decision.allReasons.contains(.localArtifactsMissing))
    }

    func testUnreadableLocalPackageKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: LocalArtifactFacts(error: .unreadable),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localArtifactsMissing)
        XCTAssertTrue(decision.allReasons.contains(.localIntegrityUnverified))
    }

    func testV5ItemWithoutExpectedTranscriptionSizeKeepsLocal() {
        let item = makeItem(mediaBytes: 0)
        XCTAssertTrue(item.isV5Package)
        let decision = evaluate(
            item: item,
            proof: makeProof(),
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .localIntegrityUnverified)
    }

    func testLocalSizeMismatchKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts { $0.transcriptionBytes = 999 },
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localIntegrityUnverified)
    }

    func testLocalHashMismatchKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts { $0.transcriptionSha256 = String(repeating: "c", count: 64) },
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localIntegrityUnverified)
    }

    func testUnknownLocalFootprintKeepsLocal() {
        let decision = evaluate(
            item: makeItem(),
            proof: makeProof(),
            facts: makeFacts { $0.packageBytes = nil },
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.primaryReason, .localBytesUnknown)
        XCTAssertEqual(decision.bytes, 0)
    }

    func testFetchFailureIsDependencyUnavailable() {
        let decision = LocalCacheEligibility.evaluate(
            item: makeItem(),
            document: makeDocument(),
            scope: scopeA,
            proof: nil,
            proofFetchedAt: nil,
            proofFetchFailed: true,
            localFacts: makeFacts(),
            now: now
        )
        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .dependencyUnavailable)
        XCTAssertEqual(decision.allReasons, [.dependencyUnavailable])
    }

    func testUndecodableQueueItemAlwaysKeepsLocal() {
        let decision = LocalCacheEligibility.undecodableDecision()
        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .queueItemUndecodable)
        XCTAssertEqual(decision.allReasons, [.queueItemUndecodable])
        XCTAssertEqual(decision.bytes, 0)
    }

    func testPrimaryReasonFollowsContractPrecedenceAndAllReasonsAreComplete() {
        let decision = LocalCacheEligibility.evaluate(
            item: makeItem(state: .queued),
            document: makeDocument(),
            scope: scopeA,
            proof: nil,
            proofFetchedAt: nil,
            localFacts: makeFacts { $0.packageBytes = nil; $0.manifestPresent = false },
            now: now
        )

        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .notUploaded)
        XCTAssertEqual(decision.allReasons, [
            .notUploaded,
            .proofMissing,
            .localArtifactsMissing,
            .localBytesUnknown,
        ])
    }

    func testPartialContinuityIsNeverEligibleForEviction() {
        let decision = evaluate(
            item: makeItem(partialContinuity: true),
            proof: makeProof(),
            facts: makeFacts(),
            proofFetchedAt: now
        )

        XCTAssertEqual(decision.verdict, .keep)
        XCTAssertEqual(decision.primaryReason, .localIntegrityUnverified)
        XCTAssertTrue(decision.allReasons.contains(.localIntegrityUnverified))
    }

    // MARK: - Fixtures

    private func assertKeep(
        item: DesktopUploadQueueItem? = nil,
        proof: DesktopServerProof? = nil,
        expected: LocalCacheEligibilityReason,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let decision = evaluate(
            item: item ?? makeItem(),
            proof: proof ?? makeProof(),
            facts: makeFacts(),
            proofFetchedAt: now
        )
        XCTAssertEqual(decision.verdict, .keep, file: file, line: line)
        XCTAssertEqual(decision.primaryReason, expected, file: file, line: line)
        XCTAssertTrue(
            decision.allReasons.contains(expected),
            "allReasons must contain the failed gate",
            file: file,
            line: line
        )
    }

    private func evaluate(
        item: DesktopUploadQueueItem,
        proof: DesktopServerProof?,
        facts: LocalArtifactFacts,
        document: DesktopUploadQueueDocument? = nil,
        scope: RecordingDeletionScope? = nil,
        proofFetchedAt: Date?,
        proofFetchFailed: Bool = false
    ) -> LocalCacheEligibilityDecision {
        LocalCacheEligibility.evaluate(
            item: item,
            document: document ?? makeDocument(),
            scope: scope ?? scopeA,
            proof: proof,
            proofFetchedAt: proofFetchedAt,
            proofFetchFailed: proofFetchFailed,
            localFacts: facts,
            now: now
        )
    }

    private func makeDocument(
        operations: [RecordingDeletionOperation] = []
    ) -> DesktopUploadQueueDocument {
        DesktopUploadQueueDocument(updatedAt: now, items: [], deletionOperations: operations)
    }

    private func makeFacts(
        _ mutate: (inout LocalArtifactFacts) -> Void = { _ in }
    ) -> LocalArtifactFacts {
        var facts = LocalArtifactFacts(
            manifestPresent: true,
            reviewAudioPresent: true,
            transcriptionAudioPresent: true,
            transcriptionBytes: 1_000,
            transcriptionSha256: String(repeating: "b", count: 64),
            reviewPlaybackAvailable: true,
            packageBytes: 1_100
        )
        mutate(&facts)
        return facts
    }

    private struct ProofDraft {
        var meetingId: String? = "meeting-1"
        var deletionState: String? = "none"
        var accessState: String? = "owner"
        var conflictState: String? = "none"
        var playbackState: String? = "available"
        var canPlay: Bool? = true
        var reasonCode: String? = "canonical_ready"
        var playbackRevision: String? = "11111111-1111-4111-8111-111111111111"
        var playbackLocalRevision: String? = "rev-local"
        var objectVerified: Bool? = true
        var verifiedAt: Date?
        var sessionStatus: String? = "finalized"
        var sessionRevision: String? = "11111111-1111-4111-8111-111111111111"
        var finalizedLocalRevision: String? = "rev-local"
        var archiveAudio: Bool? = true
        var finalizedAt: Date?
        var retentionState: String? = "active"
        var deleteAfter: Date?

        init(now: Date) {
            verifiedAt = now.addingTimeInterval(-10)
            finalizedAt = now.addingTimeInterval(-8 * 24 * 60 * 60)
            deleteAfter = now.addingTimeInterval(300 * 24 * 60 * 60)
        }
    }

    private func makeProof(_ mutate: (inout ProofDraft) -> Void = { _ in }) -> DesktopServerProof {
        var draft = ProofDraft(now: now)
        mutate(&draft)
        return DesktopServerProof(
            meetingId: draft.meetingId,
            deletionState: draft.deletionState,
            accessState: draft.accessState,
            conflictState: draft.conflictState,
            playback: DesktopPlaybackProof(
                state: draft.playbackState,
                canPlay: draft.canPlay,
                reasonCode: draft.reasonCode,
                mediaRevisionId: draft.playbackRevision,
                localMediaRevisionId: draft.playbackLocalRevision,
                objectVerified: draft.objectVerified,
                verifiedAt: draft.verifiedAt.map(ServerTimestamp.init),
                automaticRecovery: false
            ),
            uploadSession: DesktopUploadSessionProof(sessionId: "active-session", status: "active"),
            finalizedUpload: DesktopFinalizedUploadProof(
                sessionId: "session-1",
                mediaRevisionId: draft.sessionRevision,
                localMediaRevisionId: draft.finalizedLocalRevision,
                archiveAudio: draft.archiveAudio,
                finalizedAt: draft.finalizedAt.map(ServerTimestamp.init),
                status: draft.sessionStatus
            ),
            retention: DesktopRetentionProof(
                deleteAfter: draft.deleteAfter.map(ServerTimestamp.init),
                policyState: draft.retentionState
            )
        )
    }

    private func makeItem(
        state: UploadItemState = .uploaded,
        isLocalUnbound: Bool? = false,
        ownerScope: RecordingDeletionScope? = nil,
        lifecycleAccessAvailable: Bool = true,
        syncConflictState: DesktopSyncConflictState = .none,
        uploadStatus: String? = "finalized",
        failureReason: String? = nil,
        meetingId: String? = "meeting-1",
        mediaBytes: Int64 = 1_000,
        schemaVersion: String = LocalRecordingManifest.schemaVersion,
        partialContinuity: Bool? = nil
    ) -> DesktopUploadQueueItem {
        var item = DesktopUploadQueueItem(
            id: "queue-item-1",
            sessionId: "session-1",
            directoryId: "recordings-directory",
            localMediaRevisionId: "rev-local",
            directoryPath: "/tmp/f296-recordings/recordings-directory",
            manifestPath: "/tmp/f296-recordings/recordings-directory/manifest.json",
            microphonePath: "metadata-only",
            systemAudioPath: "metadata-only",
            state: state,
            failureReason: failureReason,
            retryMode: .terminal,
            retentionDeadline: now.addingTimeInterval(300 * 24 * 60 * 60),
            createdAt: now.addingTimeInterval(-400 * 24 * 60 * 60),
            updatedAt: now,
            meetingId: meetingId,
            mediaRevisionId: "media-revision-1",
            artifactProfile: ArtifactCompletenessProfile(
                schemaVersion: schemaVersion,
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
                        byteCount: mediaBytes,
                        sha256: String(repeating: "b", count: 64),
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
                meetingId: meetingId,
                uploadStatus: uploadStatus
            ),
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: now,
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            ),
            partialContinuity: partialContinuity
        )
        item.ownerScope = ownerScope ?? scopeA
        item.isLocalUnbound = isLocalUnbound
        item.lifecycleAccessAvailable = lifecycleAccessAvailable
        item.syncConflictState = syncConflictState
        return item
    }
}
