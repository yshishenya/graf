import Foundation

/// Stable reason vocabulary shared by the eligibility predicate, the dry-run
/// report and cleanup/eviction receipts. Order is the gate precedence: the
/// first failed gate becomes `primaryReason`.
public enum LocalCacheEligibilityReason: String, Codable, CaseIterable, Sendable {
    case serverPlaybackReady = "server_playback_ready"
    case notUploaded = "not_uploaded"
    case notFinalized = "not_finalized"
    case accountScopeMismatch = "account_scope_mismatch"
    case localUnbound = "local_unbound"
    case lifecycleUnavailable = "lifecycle_unavailable"
    case deletionOperationOpen = "deletion_operation_open"
    case confirmedDeletion = "confirmed_deletion"
    case localPurgePending = "local_purge_pending"
    case syncConflict = "sync_conflict"
    case proofMissing = "proof_missing"
    case proofStale = "proof_stale"
    case meetingMismatch = "meeting_mismatch"
    case revisionMismatch = "revision_mismatch"
    case playbackNotAvailable = "playback_not_available"
    case playbackNotVerified = "playback_not_verified"
    case verificationStale = "verification_stale"
    case archiveAudioFalse = "archive_audio_false"
    case archiveAudioUnknown = "archive_audio_unknown"
    case graceNotElapsed = "grace_not_elapsed"
    case deletionStateUnknown = "deletion_state_unknown"
    case accessStateNotOwner = "access_state_not_owner"
    case retentionUnknown = "retention_unknown"
    case retentionUnsafe = "retention_unsafe"
    case retentionExpired = "retention_expired"
    case retentionTooClose = "retention_too_close"
    case localArtifactsMissing = "local_artifacts_missing"
    case localArtifactsOutsideRoot = "local_artifacts_outside_root"
    case localIntegrityUnverified = "local_integrity_unverified"
    case localBytesUnknown = "local_bytes_unknown"
    case queueItemUndecodable = "queue_item_undecodable"
    case dependencyUnavailable = "dependency_unavailable"

    public static let failureOrder: [LocalCacheEligibilityReason] = allCases.filter {
        $0 != .serverPlaybackReady
    }
}

public enum LocalCacheVerdict: String, Codable, Equatable, Sendable {
    case potentiallyEligible = "potentially_eligible"
    case keep
}

public struct LocalCacheEligibilityPolicy: Equatable, Sendable {
    public var maximumProofAge: TimeInterval
    public var gracePeriod: TimeInterval
    public var minimumRemainingRetention: TimeInterval

    public init(
        maximumProofAge: TimeInterval = 120,
        gracePeriod: TimeInterval = 7 * 24 * 60 * 60,
        minimumRemainingRetention: TimeInterval = 30 * 24 * 60 * 60
    ) {
        self.maximumProofAge = maximumProofAge
        self.gracePeriod = gracePeriod
        self.minimumRemainingRetention = minimumRemainingRetention
    }

    public static let `default` = LocalCacheEligibilityPolicy()
}

public enum LocalArtifactFactsError: String, Equatable, Sendable {
    case missing
    case outsideRoot = "outside_root"
    case integrity
    case unreadable
}

/// A read-only, player-free projection of the local recording package. It is
/// evidence about files, never a UI authorization.
public struct LocalArtifactFacts: Equatable, Sendable {
    public var manifestPresent: Bool
    public var reviewAudioPresent: Bool
    public var transcriptionAudioPresent: Bool
    public var transcriptionBytes: Int64?
    public var transcriptionSha256: String?
    public var reviewPlaybackAvailable: Bool
    public var packageBytes: Int64?
    public var error: LocalArtifactFactsError?

    public init(
        manifestPresent: Bool = false,
        reviewAudioPresent: Bool = false,
        transcriptionAudioPresent: Bool = false,
        transcriptionBytes: Int64? = nil,
        transcriptionSha256: String? = nil,
        reviewPlaybackAvailable: Bool = false,
        packageBytes: Int64? = nil,
        error: LocalArtifactFactsError? = nil
    ) {
        self.manifestPresent = manifestPresent
        self.reviewAudioPresent = reviewAudioPresent
        self.transcriptionAudioPresent = transcriptionAudioPresent
        self.transcriptionBytes = transcriptionBytes
        self.transcriptionSha256 = transcriptionSha256
        self.reviewPlaybackAvailable = reviewPlaybackAvailable
        self.packageBytes = packageBytes
        self.error = error
    }
}

public struct LocalCacheEligibilityDecision: Equatable, Sendable {
    public let verdict: LocalCacheVerdict
    public let primaryReason: LocalCacheEligibilityReason
    public let allReasons: [LocalCacheEligibilityReason]
    public let bytes: Int64
    public let proof: DesktopServerProof?

    public init(
        verdict: LocalCacheVerdict,
        primaryReason: LocalCacheEligibilityReason,
        allReasons: [LocalCacheEligibilityReason],
        bytes: Int64,
        proof: DesktopServerProof?
    ) {
        self.verdict = verdict
        self.primaryReason = primaryReason
        self.allReasons = allReasons
        self.bytes = bytes
        self.proof = proof
    }
}

/// A pure fail-closed predicate. It performs no IO and never consults a player
/// or `localPlaybackURL`; the caller supplies freshly fetched proof and a
/// read-only local file projection.
public enum LocalCacheEligibility {
    /// Tolerated positive clock skew for server timestamps.
    public static let maximumClockSkew: TimeInterval = 60

    private static let knownDeletionStates: Set<String> = [
        "requested", "deleting", "active_purge_complete", "pending_backup_expiry",
        "complete", "retryable_failed", "terminal_failed", "policy_blocked",
        "post_egress_limit", "local_purge_unverified", "deleted", "purged"
    ]

    fileprivate static let pendingLocalPurgeReasons: Set<String> = [
        "local_purge_unverified", "local_purge_failed", "local_artifacts_still_present"
    ]

    public static func evaluate(
        item: DesktopUploadQueueItem,
        document: DesktopUploadQueueDocument,
        scope: RecordingDeletionScope?,
        proof: DesktopServerProof?,
        proofFetchedAt: Date?,
        proofFetchFailed: Bool = false,
        localFacts: LocalArtifactFacts,
        policy: LocalCacheEligibilityPolicy = .default,
        now: Date
    ) -> LocalCacheEligibilityDecision {
        var failures: Set<LocalCacheEligibilityReason> = []

        if item.state != .uploaded {
            failures.insert(.notUploaded)
        }

        if item.partialContinuity == true {
            // A partial recording is not a complete local package. Its WAV is
            // the only transcription-grade copy of the preserved prefix, so it
            // must never be evicted even when the server accepted the upload.
            failures.insert(.localIntegrityUnverified)
        }

        if let proof {
            // A fresh server finalization proof is the server-provided
            // timestamp. The persisted upload status is client history and
            // cannot prove custody. A wholly missing proof is reported as
            // `proof_missing` by the proof gate below.
            if proof.finalizedUpload?.finalizedAt == nil {
                failures.insert(.notFinalized)
            }
        }

        if item.isLocalUnbound == true {
            failures.insert(.localUnbound)
        } else if let owner = item.ownerScope {
            if scope != owner { failures.insert(.accountScopeMismatch) }
        } else {
            failures.insert(.localUnbound)
        }

        if item.lifecycleAccessAvailable == false {
            failures.insert(.lifecycleUnavailable)
        }

        if hasOpenDeletionOperation(item: item, document: document) {
            failures.insert(.deletionOperationOpen)
        }

        if item.hasConfirmedDeletion {
            failures.insert(.confirmedDeletion)
        }

        if item.hasPendingLocalPurgeEvidence {
            failures.insert(.localPurgePending)
        }

        if item.syncConflictState != .none {
            failures.insert(.syncConflict)
        }
        if let freshConflict = proof?.conflictState, freshConflict != "none" {
            failures.insert(.syncConflict)
        }

        if proofFetchFailed {
            failures.insert(.dependencyUnavailable)
        } else if proof == nil {
            failures.insert(.proofMissing)
        }

        if let proof, !proofFetchFailed {
            if proof.playback == nil || proof.finalizedUpload == nil || proof.retention == nil {
                failures.insert(.proofMissing)
            }
            if !isFresh(proofFetchedAt, now: now, maximumAge: policy.maximumProofAge) {
                failures.insert(.proofStale)
            }
            evaluate(proof: proof, item: item, policy: policy, now: now, failures: &failures)
        }

        evaluateLocalArtifacts(item: item, localFacts: localFacts, failures: &failures)

        let orderedFailures = LocalCacheEligibilityReason.failureOrder.filter { failures.contains($0) }
        let verdict: LocalCacheVerdict = orderedFailures.isEmpty ? .potentiallyEligible : .keep
        return LocalCacheEligibilityDecision(
            verdict: verdict,
            primaryReason: orderedFailures.first ?? .serverPlaybackReady,
            allReasons: orderedFailures,
            bytes: max(0, localFacts.packageBytes ?? 0),
            proof: proof
        )
    }

    public static func undecodableDecision() -> LocalCacheEligibilityDecision {
        LocalCacheEligibilityDecision(
            verdict: .keep,
            primaryReason: .queueItemUndecodable,
            allReasons: [.queueItemUndecodable],
            bytes: 0,
            proof: nil
        )
    }

    public static func transcriptionTrack(
        for item: DesktopUploadQueueItem
    ) -> UploadTrackCompleteness? {
        item.artifactProfile.trackCompleteness.first { $0.transportRole == .media }
    }

    public static func playbackTrack(
        for item: DesktopUploadQueueItem
    ) -> UploadTrackCompleteness? {
        item.artifactProfile.trackCompleteness.first { $0.transportRole == .playback }
    }

    public static func expectedTranscriptionBytes(for item: DesktopUploadQueueItem) -> Int64? {
        guard let track = transcriptionTrack(for: item), track.present, track.byteCount > 0 else {
            return nil
        }
        return track.byteCount
    }

    public static func expectedPlaybackBytes(for item: DesktopUploadQueueItem) -> Int64? {
        guard let track = playbackTrack(for: item), track.present, track.byteCount > 0 else {
            return nil
        }
        return track.byteCount
    }

    private static func evaluate(
        proof: DesktopServerProof,
        item: DesktopUploadQueueItem,
        policy: LocalCacheEligibilityPolicy,
        now: Date,
        failures: inout Set<LocalCacheEligibilityReason>
    ) {
        let itemMeetingId = item.meetingId ?? item.serverTruth.meetingId
        if itemMeetingId == nil || proof.meetingId != itemMeetingId {
            failures.insert(.meetingMismatch)
        }

        // `media_revision_id` is the server UUID; the local revision string is
        // a separate identity. Compare each in its own namespace and require
        // the finalized custody block to describe the playback revision.
        let playbackRevision = proof.playback?.mediaRevisionId
        let playbackLocalRevision = proof.playback?.localMediaRevisionId
        if playbackRevision == nil ||
            playbackLocalRevision == nil ||
            playbackLocalRevision != item.localMediaRevisionId {
            failures.insert(.revisionMismatch)
        }
        if proof.finalizedUpload?.mediaRevisionId != playbackRevision {
            failures.insert(.revisionMismatch)
        }
        if let finalizedLocalRevision = proof.finalizedUpload?.localMediaRevisionId,
           finalizedLocalRevision != item.localMediaRevisionId {
            failures.insert(.revisionMismatch)
        }

        if let playback = proof.playback {
            if playback.state != "available" ||
                playback.canPlay != true ||
                playback.reasonCode != "canonical_ready" {
                failures.insert(.playbackNotAvailable)
            }
            if playback.objectVerified != true {
                failures.insert(.playbackNotVerified)
            }
            if !isFresh(playback.verifiedAt?.date, now: now, maximumAge: policy.maximumProofAge) {
                failures.insert(.verificationStale)
            }
        }

        if let finalized = proof.finalizedUpload {
            if finalized.archiveAudio == false {
                failures.insert(.archiveAudioFalse)
            } else if finalized.archiveAudio == nil {
                failures.insert(.archiveAudioUnknown)
            }
            if let finalizedAt = finalized.finalizedAt?.date {
                if now.timeIntervalSince(finalizedAt) < policy.gracePeriod {
                    failures.insert(.graceNotElapsed)
                }
            } else {
                failures.insert(.notFinalized)
            }
        } else {
            failures.insert(.notFinalized)
        }

        if let deletionState = proof.deletionState {
            if deletionState != "none" {
                failures.insert(
                    knownDeletionStates.contains(deletionState) ? .confirmedDeletion : .deletionStateUnknown
                )
            }
        } else {
            failures.insert(.deletionStateUnknown)
        }

        if proof.accessState != "owner" {
            failures.insert(.accessStateNotOwner)
        }

        if let retention = proof.retention {
            switch retention.policyState {
            case "active":
                if let deadline = retention.deleteAfter?.date {
                    let remaining = deadline.timeIntervalSince(now)
                    if remaining <= 0 {
                        failures.insert(.retentionExpired)
                    } else if remaining < policy.minimumRemainingRetention {
                        failures.insert(.retentionTooClose)
                    }
                } else {
                    failures.insert(.retentionUnknown)
                }
            case "expired":
                failures.insert(.retentionExpired)
            case "unsafe", "blocked":
                failures.insert(.retentionUnsafe)
            default:
                failures.insert(.retentionUnknown)
            }
        }
    }

    private static func evaluateLocalArtifacts(
        item: DesktopUploadQueueItem,
        localFacts: LocalArtifactFacts,
        failures: inout Set<LocalCacheEligibilityReason>
    ) {
        switch localFacts.error {
        case .outsideRoot:
            failures.insert(.localArtifactsOutsideRoot)
        case .integrity, .unreadable:
            failures.insert(.localIntegrityUnverified)
        case .missing, .none:
            break
        }

        // A path outside the recordings root is its own decisive gate; do not
        // dilute it with a presence reason for the same files.
        if localFacts.error != .outsideRoot,
           (!item.isV5Package ||
                !localFacts.manifestPresent ||
                !localFacts.reviewAudioPresent ||
                !localFacts.transcriptionAudioPresent ||
                !localFacts.reviewPlaybackAvailable) {
            failures.insert(.localArtifactsMissing)
        }

        // A V5 package always needs a known expected transcription size. If the
        // media track lost that evidence, the size gate cannot be skipped.
        if item.isV5Package,
           localFacts.transcriptionAudioPresent,
           expectedTranscriptionBytes(for: item) == nil {
            failures.insert(.localIntegrityUnverified)
        } else if let expectedBytes = expectedTranscriptionBytes(for: item),
                  localFacts.transcriptionBytes != expectedBytes {
            failures.insert(.localIntegrityUnverified)
        }

        if let expectedSha = transcriptionTrack(for: item)?.sha256,
           let localSha = localFacts.transcriptionSha256,
           expectedSha != localSha {
            failures.insert(.localIntegrityUnverified)
        }

        if localFacts.packageBytes == nil {
            failures.insert(.localBytesUnknown)
        }
    }

    private static func hasOpenDeletionOperation(
        item: DesktopUploadQueueItem,
        document: DesktopUploadQueueDocument
    ) -> Bool {
        if item.deletionOperation?.blocksContent == true { return true }
        guard let owner = item.ownerScope else { return false }
        return document.deletionOperations.contains { operation in
            guard operation.blocksContent, operation.scope == owner else { return false }
            switch operation.target {
            case .meeting(let id):
                return id == item.meetingId || id == item.serverTruth.meetingId
            case .ownOrigin(let id):
                return id == item.directoryId
            }
        }
    }

    private static func isFresh(_ timestamp: Date?, now: Date, maximumAge: TimeInterval) -> Bool {
        guard let timestamp else { return false }
        let age = now.timeIntervalSince(timestamp)
        return age <= maximumAge && age >= -maximumClockSkew
    }
}

public extension DesktopUploadQueueItem {
    /// A durable local signal that a server purge task still expects work.
    var hasPendingLocalPurgeEvidence: Bool {
        if let operation = deletionOperation,
           operation.blocksContent,
           operation.waitReason == .localCleanup {
            return true
        }
        return failureReason.map {
            LocalCacheEligibility.pendingLocalPurgeReasons.contains($0)
        } ?? false
    }
}
