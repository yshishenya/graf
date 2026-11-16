import CryptoKit
import Foundation

/// Stable, non-reversible identifiers for reports and receipts. No path, title,
/// transcript or raw server identifier may leave the device in a report.
public enum LocalCacheFingerprint {
    public static func recording(_ raw: String?) -> String {
        fingerprint(raw, prefix: "rec_fpr", fallback: "rec_fpr_unknown")
    }

    public static func meeting(_ raw: String?) -> String {
        fingerprint(raw, prefix: "meet_fpr", fallback: "meet_fpr_unknown")
    }

    public static func revision(_ raw: String?) -> String {
        fingerprint(raw, prefix: "rev_fpr", fallback: "rev_fpr_unknown")
    }

    public static func scope(_ scope: RecordingDeletionScope?) -> String {
        guard let scope else { return "scope_fpr_unbound" }
        let identity = "\(scope.serverOrigin)\u{0}\(scope.workspaceID)\u{0}\(scope.actorUserID)"
        return fingerprint(identity, prefix: "scope_fpr", fallback: "scope_fpr_unbound")
    }

    public static func sha256Hex(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    private static func fingerprint(_ raw: String?, prefix: String, fallback: String) -> String {
        guard let raw, !raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return fallback
        }
        let hex = sha256Hex(Data(raw.utf8))
        return "\(prefix)_\(String(hex.prefix(16)))"
    }
}

/// The Phase A dry-run report. Its JSON shape is exactly
/// `contracts/dry-run-report.schema.json`; unknown keys would violate the
/// schema, so every nested type lists only contract fields.
public struct LocalCacheEvictionReport: Encodable, Equatable, Sendable {
    public static let schemaVersion = "local-cache-eviction-dry-run.v1"

    public let schemaVersion: String
    public let generatedAt: Date
    public let scopeFingerprint: String
    /// True when the 200-item inspection cap was hit.
    public let truncated: Bool
    /// Number of raw queue items available before the cap.
    public let availableItemCount: Int
    public let policy: Policy
    public let totals: Totals
    public let byReason: [ReasonSummary]
    public let items: [Item]

    public init(
        generatedAt: Date,
        scopeFingerprint: String,
        policy: LocalCacheEligibilityPolicy,
        items: [Item],
        truncated: Bool = false,
        availableItemCount: Int? = nil
    ) {
        self.schemaVersion = Self.schemaVersion
        self.generatedAt = generatedAt
        self.scopeFingerprint = scopeFingerprint
        self.truncated = truncated
        self.availableItemCount = max(0, availableItemCount ?? items.count)
        self.policy = Policy(policy)
        self.totals = Totals(items: items)
        self.byReason = ReasonSummary.summaries(for: items)
        self.items = items
    }

    public struct Policy: Encodable, Equatable, Sendable {
        public let maximumProofAgeSeconds: Int
        public let graceSeconds: Int
        public let minimumRemainingRetentionSeconds: Int

        public init(_ policy: LocalCacheEligibilityPolicy) {
            maximumProofAgeSeconds = max(1, Int(policy.maximumProofAge.rounded()))
            graceSeconds = max(0, Int(policy.gracePeriod.rounded()))
            minimumRemainingRetentionSeconds = max(0, Int(policy.minimumRemainingRetention.rounded()))
        }
    }

    public struct Totals: Encodable, Equatable, Sendable {
        public let inspected: Int
        public let eligible: Int
        public let eligibleBytes: Int64
        public let rejected: Int
        public let rejectedBytes: Int64
        public let unknownBytes: Int64

        public init(items: [Item]) {
            inspected = items.count
            eligible = items.filter { $0.verdict == .potentiallyEligible }.count
            eligibleBytes = items
                .filter { $0.verdict == .potentiallyEligible }
                .reduce(Int64(0)) { $0 + max(0, $1.bytes) }
            rejected = items.filter { $0.verdict == .keep }.count
            rejectedBytes = items
                .filter { $0.verdict == .keep }
                .reduce(Int64(0)) { $0 + max(0, $1.bytes) }
            unknownBytes = items
                .filter { $0.allReasons.contains(LocalCacheEligibilityReason.localBytesUnknown.rawValue) }
                .reduce(Int64(0)) { $0 + max(0, $1.bytes) }
        }
    }

    public struct ReasonSummary: Encodable, Equatable, Sendable {
        public let code: String
        public let count: Int
        public let bytes: Int64

        public init(code: String, count: Int, bytes: Int64) {
            self.code = code
            self.count = count
            self.bytes = bytes
        }

        public static func summaries(for items: [Item]) -> [ReasonSummary] {
            let grouped = Dictionary(grouping: items, by: \.primaryReason)
            return grouped.map { code, groupedItems in
                ReasonSummary(
                    code: code,
                    count: groupedItems.count,
                    bytes: groupedItems.reduce(Int64(0)) { $0 + max(0, $1.bytes) }
                )
            }
            .sorted {
                if $0.count != $1.count { return $0.count > $1.count }
                return $0.code < $1.code
            }
        }
    }

    public struct Item: Encodable, Equatable, Sendable {
        public let localRecordingFingerprint: String
        public let state: String
        public let bytes: Int64
        public let verdict: LocalCacheVerdict
        public let primaryReason: String
        public let allReasons: [String]
        public let server: Server?

        public init(
            localRecordingFingerprint: String,
            state: String,
            bytes: Int64,
            verdict: LocalCacheVerdict,
            primaryReason: String,
            allReasons: [String],
            server: Server?
        ) {
            self.localRecordingFingerprint = localRecordingFingerprint
            self.state = state
            self.bytes = bytes
            self.verdict = verdict
            self.primaryReason = primaryReason
            self.allReasons = allReasons
            self.server = server
        }

        public static func make(
            item: DesktopUploadQueueItem,
            decision: LocalCacheEligibilityDecision,
            localRecordingFingerprint: String
        ) -> Item {
            let proof = decision.proof
            let server = Server(
                meetingFingerprint: proof?.meetingId.map(LocalCacheFingerprint.meeting),
                mediaRevisionFingerprint: LocalCacheFingerprint.revision(item.localMediaRevisionId),
                playbackRevisionFingerprint: proof?.playback?.mediaRevisionId.map(LocalCacheFingerprint.revision),
                playbackState: proof?.playback?.state,
                canPlay: proof?.playback?.canPlay,
                objectVerified: proof?.playback?.objectVerified,
                archiveAudio: proof?.finalizedUpload?.archiveAudio,
                policyState: proof?.retention?.policyState
            )
            return Item(
                localRecordingFingerprint: localRecordingFingerprint,
                state: item.state.rawValue,
                bytes: max(0, decision.bytes),
                verdict: decision.verdict,
                primaryReason: decision.primaryReason.rawValue,
                allReasons: decision.allReasons.map(\.rawValue),
                server: server
            )
        }
    }

    public struct Server: Encodable, Equatable, Sendable {
        public let meetingFingerprint: String?
        public let mediaRevisionFingerprint: String?
        public let playbackRevisionFingerprint: String?
        public let playbackState: String?
        public let canPlay: Bool?
        public let objectVerified: Bool?
        public let archiveAudio: Bool?
        public let policyState: String?

        public init(
            meetingFingerprint: String? = nil,
            mediaRevisionFingerprint: String? = nil,
            playbackRevisionFingerprint: String? = nil,
            playbackState: String? = nil,
            canPlay: Bool? = nil,
            objectVerified: Bool? = nil,
            archiveAudio: Bool? = nil,
            policyState: String? = nil
        ) {
            self.meetingFingerprint = meetingFingerprint
            self.mediaRevisionFingerprint = mediaRevisionFingerprint
            self.playbackRevisionFingerprint = playbackRevisionFingerprint
            self.playbackState = playbackState
            self.canPlay = canPlay
            self.objectVerified = objectVerified
            self.archiveAudio = archiveAudio
            self.policyState = policyState
        }
    }
}
