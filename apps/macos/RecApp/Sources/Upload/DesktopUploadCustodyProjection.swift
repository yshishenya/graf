import CryptoKit
import Foundation
import TwoBrainRecShared

public enum DesktopUploadCustodyState: String, Codable, CaseIterable, Sendable {
    case serverUnknownLocalSaved = "server_unknown_local_saved"
    case serverRegistered = "server_registered"
    case uploadSessionCreated = "upload_session_created"
    case partialUploaded = "partial_uploaded"
    case finalized
    case processing
    case delivered
    case retainedAwaitingCondition = "retained_awaiting_condition"
    case cannotSend = "cannot_send"
    case terminalUndelivered = "terminal_undelivered"
}

public enum DesktopUploadCustodyOwner: String, Codable, CaseIterable, Sendable {
    case productAutomatic = "product_automatic"
    case meetingOwner = "meeting_owner"
    case workspaceAdmin = "workspace_admin"
    case support
    case policyLifecycle = "policy_lifecycle"
}

public enum DesktopUploadCustodyRetryClass: String, Codable, CaseIterable, Sendable {
    case automatic
    case pausedUntilUserAction = "paused_until_user_action"
    case pausedUntilAdminAction = "paused_until_admin_action"
    case notRetryable = "not_retryable"
    case terminal
}

public enum DesktopUploadCustodyNormalUserAction: String, Codable, CaseIterable, Sendable {
    case none
    case signIn = "sign_in"
    case chooseWorkspace = "choose_workspace"
    case grantPermission = "grant_permission"
    case openReview = "open_review"
    case openDiagnostics = "open_diagnostics"
    case sendSupportReport = "send_support_report"
    case copySafeReport = "copy_safe_report"
    case deleteLocalCopy = "delete_local_copy"
}

public enum DesktopUploadCustodyMetadataSafety: String, Codable, CaseIterable, Sendable {
    case metadataOnly = "metadata_only"
}

private enum DesktopUploadCustodySafeMetadata {
    private static let allowedCodeScalars = CharacterSet(
        charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    )

    static func isSafeCode(_ value: String) -> Bool {
        guard !value.isEmpty, value.count <= 120 else { return false }
        return value.unicodeScalars.allSatisfy { allowedCodeScalars.contains($0) }
    }

    static func optionalPrefixedFingerprint(_ value: String?) -> String {
        guard let value, !value.isEmpty else { return "not_applicable" }
        return prefixedFingerprint(value)
    }

    static func prefixedFingerprint(_ value: String, prefix: String = "fpr", length: Int = 16) -> String {
        "\(prefix)_\(shortFingerprint(value, length: length))"
    }

    static func shortFingerprint(_ value: String, length: Int = 8) -> String {
        let digest = SHA256.hash(data: Data(value.utf8)).prefix(max(4, length))
        return digest.map { String(format: "%02x", $0) }.joined()
    }

    static func isoDateText(_ date: Date) -> String {
        ISO8601DateFormatter().string(from: date)
    }
}

public enum DesktopUploadCustodyUploadState: String, Codable, CaseIterable, Sendable {
    case notStarted = "not_started"
    case sessionCreated = "session_created"
    case partialUploaded = "partial_uploaded"
    case finalized
    case blocked
    case terminal
}

public enum DesktopUploadCustodyProcessingState: String, Codable, CaseIterable, Sendable {
    case notSubmitted = "not_submitted"
    case pendingProcessing = "pending_processing"
    case processing
    case processed
    case blocked
    case failedRetryable = "failed_retryable"
    case failedTerminal = "failed_terminal"
    case canceled
}

public enum DesktopUploadCustodyDeletionState: String, Codable, CaseIterable, Sendable {
    case none
    case serverDeleted = "server_deleted"
    case accessBlocked = "access_blocked"
    case retentionExpired = "retention_expired"
    case localPolicyDeleted = "local_policy_deleted"
}

public enum DesktopUploadCustodyLocalPurgeState: String, Codable, CaseIterable, Sendable {
    case none
    case pending
    case verified
    case failed
    case unverified
}

public struct DesktopUploadCustodyProjection: Equatable, Sendable {
    private static let retentionWarningWindowSeconds: TimeInterval = 24 * 60 * 60

    public let itemId: String
    public let localRecordingId: String
    public let localMediaRevisionId: String
    public let custodyState: DesktopUploadCustodyState
    public let uploadState: DesktopUploadCustodyUploadState
    public let processingState: DesktopUploadCustodyProcessingState
    public let deletionState: DesktopUploadCustodyDeletionState
    public let localPurgeState: DesktopUploadCustodyLocalPurgeState
    public let owner: DesktopUploadCustodyOwner
    public let retryClass: DesktopUploadCustodyRetryClass
    public let normalUserAction: DesktopUploadCustodyNormalUserAction
    public let displayPriority: Int
    public let reviewAvailable: Bool
    public let serverMeetingId: String?
    public let serverMediaRevisionId: String?
    public let retentionDeadline: Date?
    public let copyKey: String
    public let metadataSafety: DesktopUploadCustodyMetadataSafety
    public let progressFraction: Double

    public var requiresUserAttention: Bool {
        normalUserAction != .none || copyKey == "custody.retention_warning"
    }

    public init(item: DesktopUploadQueueItem, now: Date = Date()) {
        let rule = Self.rule(for: item, now: now)
        self.itemId = item.id
        self.localRecordingId = item.directoryId
        self.localMediaRevisionId = item.localMediaRevisionId
        self.custodyState = rule.custodyState
        self.uploadState = Self.uploadState(for: item)
        self.processingState = Self.processingState(for: item)
        self.deletionState = Self.deletionState(for: item, now: now)
        self.localPurgeState = Self.localPurgeState(for: item)
        self.owner = rule.owner
        self.retryClass = rule.retryClass
        self.normalUserAction = rule.normalUserAction
        self.displayPriority = rule.displayPriority
        self.reviewAvailable = rule.reviewAvailable
        self.serverMeetingId = item.serverTruth.meetingId
        self.serverMediaRevisionId = item.serverTruth.mediaRevisionId
        self.retentionDeadline = rule.retentionDeadline
        self.copyKey = rule.copyKey
        self.metadataSafety = .metadataOnly
        self.progressFraction = item.progressFraction
    }

    private struct Rule {
        var custodyState: DesktopUploadCustodyState
        var owner: DesktopUploadCustodyOwner
        var retryClass: DesktopUploadCustodyRetryClass
        var normalUserAction: DesktopUploadCustodyNormalUserAction
        var displayPriority: Int
        var reviewAvailable: Bool
        var retentionDeadline: Date?
        var copyKey: String
    }

    private static func rule(for item: DesktopUploadQueueItem, now: Date) -> Rule {
        if item.serverTruth.deletionState.map({ $0 != "none" }) == true {
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .workspaceAdmin,
                retryClass: .pausedUntilAdminAction,
                normalUserAction: .sendSupportReport,
                displayPriority: 1,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.needs_admin"
            )
        }

        if item.serverTruth.accessState.map({ $0 != "owner" }) == true {
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .workspaceAdmin,
                retryClass: .pausedUntilAdminAction,
                normalUserAction: .sendSupportReport,
                displayPriority: 1,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.needs_admin"
            )
        }

        if item.state != .uploaded && item.retentionDeadline <= now {
            return Rule(
                custodyState: .terminalUndelivered,
                owner: .policyLifecycle,
                retryClass: .terminal,
                normalUserAction: .sendSupportReport,
                displayPriority: 0,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.terminal_undelivered"
            )
        }

        if item.failureCategory == .authSession || item.syncConflictState == .authRequired {
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .meetingOwner,
                retryClass: .pausedUntilUserAction,
                normalUserAction: .signIn,
                displayPriority: 1,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.needs_sign_in"
            )
        }

        if item.syncConflictState == .accessRevoked || item.syncConflictState == .staleDeviceIdentity {
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .workspaceAdmin,
                retryClass: .pausedUntilAdminAction,
                normalUserAction: .sendSupportReport,
                displayPriority: 1,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.needs_admin"
            )
        }

        if isQualityWarning(item.failureReason) {
            return Rule(
                custodyState: .serverUnknownLocalSaved,
                owner: .productAutomatic,
                retryClass: .automatic,
                normalUserAction: .none,
                displayPriority: 5,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.saved_will_send"
            )
        }

        if let conflictRule = rule(forConflict: item.syncConflictState, item: item) {
            return conflictRule
        }

        if isLocallyUnsendable(item) {
            return Rule(
                custodyState: .cannotSend,
                owner: .support,
                retryClass: .notRetryable,
                normalUserAction: .sendSupportReport,
                displayPriority: 0,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.cannot_send"
            )
        }

        if item.state != .uploaded &&
            item.retryMode == .automatic &&
            item.retentionDeadline.timeIntervalSince(now) <= retentionWarningWindowSeconds {
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .policyLifecycle,
                retryClass: .automatic,
                normalUserAction: .none,
                displayPriority: 2,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.retention_warning"
            )
        }

        if let rule = serverKnownRule(for: item) {
            return rule
        }

        switch item.state {
        case .queued, .retrying, .degraded:
            return Rule(
                custodyState: .serverUnknownLocalSaved,
                owner: .productAutomatic,
                retryClass: .automatic,
                normalUserAction: .none,
                displayPriority: 5,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.saved_will_send"
            )
        case .uploading:
            return Rule(
                custodyState: .partialUploaded,
                owner: .productAutomatic,
                retryClass: .automatic,
                normalUserAction: .none,
                displayPriority: 4,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.uploading"
            )
        case .uploaded:
            return Rule(
                custodyState: .finalized,
                owner: .productAutomatic,
                retryClass: .terminal,
                normalUserAction: .none,
                displayPriority: 8,
                reviewAvailable: false,
                retentionDeadline: nil,
                copyKey: "custody.known_by_server"
            )
        case .blocked:
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .productAutomatic,
                retryClass: item.retryMode == .automatic ? .automatic : .pausedUntilAdminAction,
                normalUserAction: .none,
                displayPriority: 2,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.unknown_blocked"
            )
        case .failed, .terminalDeleted:
            return Rule(
                custodyState: .terminalUndelivered,
                owner: .policyLifecycle,
                retryClass: .terminal,
                normalUserAction: .sendSupportReport,
                displayPriority: 1,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.terminal_undelivered"
            )
        }
    }

    private static func rule(
        forConflict conflict: DesktopSyncConflictState,
        item: DesktopUploadQueueItem
    ) -> Rule? {
        switch conflict {
        case .serverMeetingDeleted, .serverExpectedMetadataMismatch, .serverRangesInconsistent:
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .workspaceAdmin,
                retryClass: .pausedUntilAdminAction,
                normalUserAction: .sendSupportReport,
                displayPriority: 1,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.needs_admin"
            )
        case .processingFailed, .processingBlocked:
            return Rule(
                custodyState: .processing,
                owner: .support,
                retryClass: .notRetryable,
                normalUserAction: .sendSupportReport,
                displayPriority: 2,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.unknown_blocked"
            )
        case .retentionExpired:
            return Rule(
                custodyState: .terminalUndelivered,
                owner: .policyLifecycle,
                retryClass: .terminal,
                normalUserAction: .sendSupportReport,
                displayPriority: 0,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.terminal_undelivered"
            )
        case .uploadSessionExpired, .dependencyUnavailable:
            return Rule(
                custodyState: .retainedAwaitingCondition,
                owner: .productAutomatic,
                retryClass: .automatic,
                normalUserAction: .none,
                displayPriority: 3,
                reviewAvailable: false,
                retentionDeadline: item.retentionDeadline,
                copyKey: "custody.uploading"
            )
        case .none, .authRequired, .accessRevoked, .staleDeviceIdentity,
             .localFilesMissing, .localChecksumChanged, .queueDocumentMalformed,
             .queueSchemaMigrationBlocked:
            return nil
        }
    }

    private static func serverKnownRule(for item: DesktopUploadQueueItem) -> Rule? {
        guard item.serverTruth.meetingId != nil else { return nil }
        guard item.serverTruth.deletionState == nil || item.serverTruth.deletionState == "none" else {
            return nil
        }
        guard item.serverTruth.accessState == nil || item.serverTruth.accessState == "owner" else {
            return nil
        }
        let reviewAvailable = item.state == .uploaded && item.serverTruth.processingStatus == "processed"
        let state: DesktopUploadCustodyState
        if reviewAvailable {
            state = .delivered
        } else if item.state == .uploaded {
            state = item.serverTruth.processingStatus == nil ? .finalized : .processing
        } else if item.serverTruth.acceptedBytesByTrack.isEmpty {
            state = item.serverTruth.uploadSessionId == nil ? .serverRegistered : .uploadSessionCreated
        } else {
            state = .partialUploaded
        }
        return Rule(
            custodyState: state,
            owner: .productAutomatic,
            retryClass: item.state == .uploaded ? .terminal : .automatic,
            normalUserAction: reviewAvailable ? .openReview : .none,
            displayPriority: reviewAvailable ? 9 : 5,
            reviewAvailable: reviewAvailable,
            retentionDeadline: item.state == .uploaded ? nil : item.retentionDeadline,
            copyKey: state == .partialUploaded ? "custody.uploading" : "custody.known_by_server"
        )
    }

    private static func uploadState(for item: DesktopUploadQueueItem) -> DesktopUploadCustodyUploadState {
        if item.state == .terminalDeleted ||
            item.syncConflictState == .retentionExpired ||
            (item.retentionDecision.decision == .terminalDeleted && !item.retentionDecision.localArtifactsRetained) {
            return .terminal
        }

        let serverStatus = normalizedServerStatus(item.serverTruth.serverStatus)
        if item.state == .uploaded ||
            item.serverTruth.finalizedAt != nil ||
            serverStatus == "ingested_pending_processing" ||
            serverStatus == "degraded" {
            return .finalized
        }

        if !item.serverTruth.acceptedBytesByTrack.isEmpty || item.state == .uploading {
            return .partialUploaded
        }

        if item.uploadSessionId != nil || item.serverTruth.uploadSessionId != nil {
            return .sessionCreated
        }

        if item.state == .blocked || blocksUploadTruth(item.syncConflictState) {
            return .blocked
        }

        return .notStarted
    }

    private static func processingState(for item: DesktopUploadQueueItem) -> DesktopUploadCustodyProcessingState {
        switch item.syncConflictState {
        case .processingFailed:
            return .failedTerminal
        case .processingBlocked:
            return .blocked
        case .none, .localFilesMissing, .localChecksumChanged, .queueDocumentMalformed,
             .queueSchemaMigrationBlocked, .serverMeetingDeleted, .accessRevoked,
             .authRequired, .staleDeviceIdentity, .serverExpectedMetadataMismatch,
             .serverRangesInconsistent, .uploadSessionExpired, .retentionExpired,
             .dependencyUnavailable:
            break
        }

        switch normalizedServerStatus(item.serverTruth.processingStatus) {
        case "pending_processing", "starting", "workflow_started", "submitting", "submitted":
            return .pendingProcessing
        case "polling", "importing", "processing":
            return .processing
        case "processed":
            return .processed
        case "blocked":
            return .blocked
        case "failed_retryable":
            return .failedRetryable
        case "failed_terminal", "failed":
            return .failedTerminal
        case "canceled", "cancelled":
            return .canceled
        default:
            return .notSubmitted
        }
    }

    private static func deletionState(
        for item: DesktopUploadQueueItem,
        now: Date
    ) -> DesktopUploadCustodyDeletionState {
        if let deletionState = item.serverTruth.deletionState, deletionState != "none" {
            return .serverDeleted
        }
        if let accessState = item.serverTruth.accessState, accessState != "owner" {
            return .accessBlocked
        }
        if item.syncConflictState == .serverMeetingDeleted {
            return .serverDeleted
        }
        if item.syncConflictState == .accessRevoked || item.syncConflictState == .staleDeviceIdentity {
            return .accessBlocked
        }
        if item.syncConflictState == .retentionExpired ||
            (item.state != .uploaded && item.retentionDeadline <= now) {
            return .retentionExpired
        }
        if item.retentionDecision.decision == .terminalDeleted {
            return .localPolicyDeleted
        }
        return .none
    }

    private static func localPurgeState(for item: DesktopUploadQueueItem) -> DesktopUploadCustodyLocalPurgeState {
        if item.retentionDecision.decision == .terminalDeleted && !item.retentionDecision.localArtifactsRetained {
            return .verified
        }
        if item.failureReason == "local_purge_unverified" {
            return .unverified
        }
        if item.failureReason == "local_purge_failed" || item.failureReason == "local_artifacts_still_present" {
            return .failed
        }
        if item.syncConflictState == .serverMeetingDeleted && item.retentionDecision.localArtifactsRetained {
            return .pending
        }
        return .none
    }

    private static func normalizedServerStatus(_ status: String?) -> String? {
        let normalized = status?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return normalized?.isEmpty == false ? normalized : nil
    }

    private static func blocksUploadTruth(_ conflict: DesktopSyncConflictState) -> Bool {
        switch conflict {
        case .processingFailed, .processingBlocked, .none:
            return false
        case .localFilesMissing, .localChecksumChanged, .queueDocumentMalformed,
             .queueSchemaMigrationBlocked, .serverMeetingDeleted, .accessRevoked,
             .authRequired, .staleDeviceIdentity, .serverExpectedMetadataMismatch,
             .serverRangesInconsistent, .uploadSessionExpired, .retentionExpired,
             .dependencyUnavailable:
            return true
        }
    }

    private static func isLocallyUnsendable(_ item: DesktopUploadQueueItem) -> Bool {
        if item.failureCategory == .localResource || item.failureCategory == .schemaIncompatibility {
            return true
        }
        switch item.syncConflictState {
        case .localFilesMissing, .localChecksumChanged, .queueDocumentMalformed, .queueSchemaMigrationBlocked:
            return true
        case .none, .serverMeetingDeleted, .accessRevoked, .authRequired, .staleDeviceIdentity,
             .serverExpectedMetadataMismatch, .serverRangesInconsistent, .uploadSessionExpired,
             .processingFailed, .processingBlocked, .retentionExpired, .dependencyUnavailable:
            return false
        }
    }

    private static func isQualityWarning(_ reason: String?) -> Bool {
        switch reason {
        case LocalRecordingFailureReason.historicalPackage.rawValue,
             LocalRecordingFailureReason.silentInput.rawValue:
            return true
        default:
            return false
        }
    }
}

public struct DesktopUploadCustodySummary: Equatable, Sendable {
    public let primaryItem: DesktopUploadQueueItem
    public let affectedItems: [DesktopUploadQueueItem]
    public let primaryProjection: DesktopUploadCustodyProjection
    public let pendingCount: Int
    public let totalCount: Int

    public var copyKey: String { primaryProjection.copyKey }
    public var stableIdentity: String {
        "\(copyKey)|\(primaryProjection.owner.rawValue)|\(primaryItem.id)"
    }
    public var progressFraction: Double { primaryItem.progressFraction }
    public var showsProgress: Bool {
        primaryProjection.custodyState == .partialUploaded || primaryItem.state == .uploading
    }

    public var title: String {
        DesktopUploadCustodyCopy.title(copyKey: copyKey, count: pendingCount)
    }

    public var detail: String {
        DesktopUploadCustodyCopy.detail(copyKey: copyKey, count: pendingCount, deadline: primaryProjection.retentionDeadline)
    }

    public var ownerLabel: String {
        switch primaryProjection.owner {
        case .productAutomatic:
            return "GRAF"
        case .meetingOwner:
            return "Владелец встречи"
        case .workspaceAdmin:
            return "Администратор"
        case .support:
            return "Поддержка"
        case .policyLifecycle:
            return "Политика хранения"
        }
    }

    public var accessibilityLabel: String {
        "Доверие записи: \(title). \(detail). Ответственный: \(ownerLabel)."
    }

    public var safeReport: DesktopUploadCustodySafeReport? {
        DesktopUploadCustodySafeReport(item: primaryItem, projection: primaryProjection)
    }

    public static func summary(
        for items: [DesktopUploadQueueItem],
        now: Date = Date()
    ) -> DesktopUploadCustodySummary? {
        let candidates = visibleCandidates(for: items, now: now)
        guard let primary = candidates.sorted(by: sortCandidates).first else { return nil }
        let affectedItems = candidates
            .filter { isSameSupportGroup($0, primary) }
            .map(\.item)
        return DesktopUploadCustodySummary(
            primaryItem: primary.item,
            affectedItems: affectedItems,
            primaryProjection: primary.projection,
            pendingCount: candidates.count,
            totalCount: items.count
        )
    }

    public static func summaries(
        for items: [DesktopUploadQueueItem],
        now: Date = Date(),
        limit: Int = 5
    ) -> [DesktopUploadCustodySummary] {
        let candidates = visibleCandidates(for: items, now: now)
        let grouped = Dictionary(grouping: candidates) { candidate in
            "\(candidate.projection.copyKey)|\(candidate.projection.owner.rawValue)"
        }

        return grouped.values
            .compactMap { group -> DesktopUploadCustodySummary? in
                let sortedGroup = group.sorted(by: sortCandidates)
                guard let primary = sortedGroup.first else { return nil }
                return DesktopUploadCustodySummary(
                    primaryItem: primary.item,
                    affectedItems: sortedGroup.map(\.item),
                    primaryProjection: primary.projection,
                    pendingCount: sortedGroup.count,
                    totalCount: candidates.count
                )
            }
            .sorted { lhs, rhs in
                let lhsCandidate = Candidate(
                    item: lhs.primaryItem,
                    projection: lhs.primaryProjection,
                    priority: priority(for: lhs.primaryItem, projection: lhs.primaryProjection)
                )
                let rhsCandidate = Candidate(
                    item: rhs.primaryItem,
                    projection: rhs.primaryProjection,
                    priority: priority(for: rhs.primaryItem, projection: rhs.primaryProjection)
                )
                return sortCandidates(lhsCandidate, rhsCandidate)
            }
            .prefix(limit)
            .map { $0 }
    }

    public static func attentionItemCount(
        for items: [DesktopUploadQueueItem],
        now: Date = Date()
    ) -> Int {
        visibleCandidates(for: items, now: now).filter { candidate in
            candidate.projection.requiresUserAttention
        }.count
    }

    private struct Candidate: Equatable {
        var item: DesktopUploadQueueItem
        var projection: DesktopUploadCustodyProjection
        var priority: Int
    }

    private static func visibleCandidates(
        for items: [DesktopUploadQueueItem],
        now: Date
    ) -> [Candidate] {
        items.compactMap { item -> Candidate? in
            let projection = DesktopUploadCustodyProjection(item: item, now: now)
            guard shouldShowNativeSummary(for: item, projection: projection) else { return nil }
            return Candidate(
                item: item,
                projection: projection,
                priority: priority(for: item, projection: projection)
            )
        }
    }

    private static func shouldShowNativeSummary(
        for item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> Bool {
        if projection.copyKey == "custody.known_by_server" {
            return false
        }
        if item.state == .terminalDeleted {
            return false
        }
        if projection.custodyState == .delivered {
            return false
        }
        return true
    }

    private static func isSameSupportGroup(_ lhs: Candidate, _ rhs: Candidate) -> Bool {
        lhs.projection.copyKey == rhs.projection.copyKey &&
            lhs.projection.owner == rhs.projection.owner
    }

    private static func priority(
        for item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> Int {
        if isDiskPressure(item) { return 0 }
        switch projection.copyKey {
        case "custody.retention_warning", "custody.terminal_undelivered":
            return 0
        case "custody.cannot_send":
            return 1
        case "custody.needs_sign_in", "custody.needs_workspace":
            return 2
        case "custody.needs_admin", "custody.unknown_blocked":
            return 3
        case "custody.uploading":
            return 4
        case "custody.saved_will_send", "custody.saving_local":
            return 5
        default:
            return 6
        }
    }

    private static func isDiskPressure(_ item: DesktopUploadQueueItem) -> Bool {
        item.failureReason == "disk_pressure" || item.failureReason == "local_disk_pressure"
    }

    private static func sortCandidates(_ lhs: Candidate, _ rhs: Candidate) -> Bool {
        if lhs.priority != rhs.priority {
            return lhs.priority < rhs.priority
        }
        if lhs.projection.displayPriority != rhs.projection.displayPriority {
            return lhs.projection.displayPriority < rhs.projection.displayPriority
        }
        if lhs.item.updatedAt != rhs.item.updatedAt {
            return lhs.item.updatedAt > rhs.item.updatedAt
        }
        return lhs.item.id < rhs.item.id
    }
}

public struct DesktopSupportIncidentReportContext: Equatable, Sendable {
    public let appName: String
    public let bundleID: String
    public let appVersion: String
    public let buildVersion: String
    public let macOSVersion: String
    public let architecture: String
    public let locale: String
    public let timezone: String
    public let environmentBaseURLIdentity: String
    public let workspaceFingerprint: String
    public let userFingerprint: String
    public let deviceFingerprint: String
    public let safeDeviceIdentifier: String

    public init(
        appName: String = "GRAF",
        bundleID: String = Bundle.main.bundleIdentifier ?? "pro.2brain.graf",
        appVersion: String = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "local",
        buildVersion: String = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "local",
        macOSVersion: String = Self.currentMacOSVersion(),
        architecture: String = Self.currentArchitecture(),
        locale: String = Locale.current.identifier,
        timezone: String = TimeZone.current.identifier,
        environmentBaseURLIdentity: String = "unknown",
        workspaceFingerprint: String = "unknown",
        userFingerprint: String = "unknown",
        deviceFingerprint: String = "unknown",
        safeDeviceIdentifier: String = "unknown"
    ) {
        self.appName = appName
        self.bundleID = bundleID
        self.appVersion = appVersion
        self.buildVersion = buildVersion
        self.macOSVersion = macOSVersion
        self.architecture = architecture
        self.locale = locale
        self.timezone = timezone
        self.environmentBaseURLIdentity = environmentBaseURLIdentity
        self.workspaceFingerprint = workspaceFingerprint
        self.userFingerprint = userFingerprint
        self.deviceFingerprint = deviceFingerprint
        self.safeDeviceIdentifier = safeDeviceIdentifier
    }

    public static var unknown: DesktopSupportIncidentReportContext {
        DesktopSupportIncidentReportContext()
    }

    public static func currentMacOSVersion() -> String {
        let version = ProcessInfo.processInfo.operatingSystemVersion
        return "\(version.majorVersion).\(version.minorVersion).\(version.patchVersion)"
    }

    public static func currentArchitecture() -> String {
        #if arch(arm64)
        return "arm64"
        #elseif arch(x86_64)
        return "x86_64"
        #else
        return "unknown"
        #endif
    }
}

public struct DesktopSupportIncidentRangeMismatchMetadata: Codable, Equatable, Sendable {
    public let hasMismatch: Bool
    public let missingRangeCount: Int
    public let corruptRangeCount: Int
    public let expectedRangeCount: Int
    public let uploadedRangeCount: Int

    public init(
        hasMismatch: Bool,
        missingRangeCount: Int = 0,
        corruptRangeCount: Int = 0,
        expectedRangeCount: Int = 0,
        uploadedRangeCount: Int = 0
    ) {
        self.hasMismatch = hasMismatch
        self.missingRangeCount = max(0, missingRangeCount)
        self.corruptRangeCount = max(0, corruptRangeCount)
        self.expectedRangeCount = max(0, expectedRangeCount)
        self.uploadedRangeCount = max(0, uploadedRangeCount)
    }

    private enum CodingKeys: String, CodingKey {
        case hasMismatch = "has_mismatch"
        case missingRangeCount = "missing_range_count"
        case corruptRangeCount = "corrupt_range_count"
        case expectedRangeCount = "expected_range_count"
        case uploadedRangeCount = "uploaded_range_count"
    }
}

public struct DesktopSupportIncidentLocalFileCompletenessProfile: Codable, Equatable, Sendable {
    public let manifestPresent: Bool
    public let manifestSchemaVersion: String
    public let audioFilesPresent: Bool
    public let microphonePresent: Bool
    public let systemAudioPresent: Bool
    public let missingFileCount: Int
    public let corruptFileCount: Int
    public let totalSizeBucket: String
    public let durationBucket: String

    public init(item: DesktopUploadQueueItem) {
        let profile = item.artifactProfile
        self.manifestPresent = profile.manifestPresent
        self.manifestSchemaVersion = DesktopUploadCustodySafeMetadata.isSafeCode(profile.schemaVersion)
            ? profile.schemaVersion
            : "unknown"
        self.audioFilesPresent = profile.microphonePresent && profile.systemAudioPresent
        self.microphonePresent = profile.microphonePresent
        self.systemAudioPresent = profile.systemAudioPresent
        self.missingFileCount = [
            profile.manifestPresent,
            profile.microphonePresent,
            profile.systemAudioPresent
        ].filter { !$0 }.count
        self.corruptFileCount = profile.trackCompleteness.filter { $0.present && !$0.uploadable }.count
        self.totalSizeBucket = Self.sizeBucket(profile.totalUploadBytes)
        self.durationBucket = Self.durationBucket(profile.durationSeconds)
    }

    private enum CodingKeys: String, CodingKey {
        case manifestPresent = "manifest_present"
        case manifestSchemaVersion = "manifest_schema_version"
        case audioFilesPresent = "audio_files_present"
        case microphonePresent = "microphone_present"
        case systemAudioPresent = "system_audio_present"
        case missingFileCount = "missing_file_count"
        case corruptFileCount = "corrupt_file_count"
        case totalSizeBucket = "total_size_bucket"
        case durationBucket = "duration_bucket"
    }

    private static func sizeBucket(_ bytes: Int64) -> String {
        switch max(0, bytes) {
        case 0:
            return "0"
        case 1..<(1024 * 1024):
            return "lt_1mb"
        case ..<(100 * 1024 * 1024):
            return "1mb_100mb"
        case ..<(1024 * 1024 * 1024):
            return "100mb_1gb"
        default:
            return "gt_1gb"
        }
    }

    private static func durationBucket(_ seconds: Int) -> String {
        switch max(0, seconds) {
        case 0..<300:
            return "lt_5m"
        case ..<1800:
            return "5m_30m"
        case ..<7200:
            return "30m_2h"
        default:
            return "gt_2h"
        }
    }
}

public struct DesktopSupportIncidentResponse: Decodable, Equatable, Sendable {
    public let incidentId: String
    public let incidentStatus: String
    public let githubIssueNumber: Int?
    public let githubIssueURL: String?
    public let dedupeStatus: String
    public let affectedCount: Int
    public let copyFallbackAvailable: Bool
    public let userMessage: String

    public init(
        incidentId: String,
        incidentStatus: String,
        githubIssueNumber: Int? = nil,
        githubIssueURL: String? = nil,
        dedupeStatus: String,
        affectedCount: Int,
        copyFallbackAvailable: Bool,
        userMessage: String
    ) {
        self.incidentId = incidentId
        self.incidentStatus = incidentStatus
        self.githubIssueNumber = githubIssueNumber
        self.githubIssueURL = githubIssueURL
        self.dedupeStatus = dedupeStatus
        self.affectedCount = affectedCount
        self.copyFallbackAvailable = copyFallbackAvailable
        self.userMessage = userMessage
    }

    public var isPendingSync: Bool {
        incidentStatus == "pending_sync"
    }

    public var isSynced: Bool {
        incidentStatus == "synced"
    }

    private enum CodingKeys: String, CodingKey {
        case incidentId = "incident_id"
        case incidentStatus = "incident_status"
        case githubIssueNumber = "github_issue_number"
        case githubIssueURL = "github_issue_url"
        case dedupeStatus = "dedupe_status"
        case affectedCount = "affected_count"
        case copyFallbackAvailable = "copy_fallback_available"
        case userMessage = "user_message"
    }
}

public struct DesktopSupportIncidentTimelineEvent: Codable, Equatable, Sendable {
    public let event: String
    public let at: String
    public let source: String

    public init(event: String, at: String, source: String) {
        self.event = event
        self.at = at
        self.source = source
    }

    private enum CodingKeys: String, CodingKey {
        case event
        case at
        case source
    }
}

public struct DesktopSupportIncidentRetryEvent: Codable, Equatable, Sendable {
    public let attemptNumber: Int
    public let startedAt: String
    public let finishedAt: String
    public let stateBefore: String
    public let stateAfter: String
    public let failureCategory: String
    public let problemCode: String
    public let httpStatus: String
    public let nextRetryAt: String

    public init(
        attemptNumber: Int,
        startedAt: String,
        finishedAt: String,
        stateBefore: String,
        stateAfter: String,
        failureCategory: String,
        problemCode: String,
        httpStatus: String,
        nextRetryAt: String
    ) {
        self.attemptNumber = max(0, attemptNumber)
        self.startedAt = startedAt
        self.finishedAt = finishedAt
        self.stateBefore = stateBefore
        self.stateAfter = stateAfter
        self.failureCategory = failureCategory
        self.problemCode = problemCode
        self.httpStatus = httpStatus
        self.nextRetryAt = nextRetryAt
    }

    private enum CodingKeys: String, CodingKey {
        case attemptNumber = "attempt_number"
        case startedAt = "started_at"
        case finishedAt = "finished_at"
        case stateBefore = "state_before"
        case stateAfter = "state_after"
        case failureCategory = "failure_category"
        case problemCode = "problem_code"
        case httpStatus = "http_status"
        case nextRetryAt = "next_retry_at"
    }
}

public struct DesktopSupportIncidentReport: Encodable, Equatable, Sendable {
    public static let schemaVersion = "desktop-support-incident.v2"
    public static let ledgerSchemaVersion = "desktop-support-incident-ledger.v1"

    public let schemaVersion: String
    public let appName: String
    public let bundleID: String
    public let appVersion: String
    public let buildVersion: String
    public let macOSVersion: String
    public let architecture: String
    public let locale: String
    public let timezone: String
    public let environmentBaseURLIdentity: String
    public let workspaceFingerprint: String
    public let userFingerprint: String
    public let deviceFingerprint: String
    public let safeDeviceIdentifier: String
    public let safeRecordingIdentity: String
    public let localRecordingIDFingerprint: String
    public let serverMeetingFingerprint: String
    public let serverMediaRevisionFingerprint: String
    public let serverMeetingPresent: Bool
    public let serverMediaRevisionPresent: Bool
    public let custodyLifecycleState: String
    public let uploadQueueItemState: String
    public let retryClass: String
    public let retryMode: String
    public let normalUserAction: String
    public let failureCategory: String
    public let problemCode: String
    public let syncConflictState: String
    public let createdAt: String
    public let updatedAt: String
    public let retentionDeadline: String
    public let serverIdentityPresent: Bool
    public let localMediaRetained: Bool
    public let dataLossRisk: String
    public let serverCopyKnown: Bool
    public let uploadAttemptCount: Int
    public let lastAttemptAt: String
    public let nextRetryAt: String
    public let lastSafeHTTPStatus: String
    public let lastSafeProblemCode: String
    public let uploadSessionPresent: Bool
    public let uploadSessionFingerprint: String
    public let expectedPartsCount: Int
    public let uploadedPartsCount: Int
    public let rangeMismatchMetadata: DesktopSupportIncidentRangeMismatchMetadata
    public let localFileCompletenessProfile: DesktopSupportIncidentLocalFileCompletenessProfile
    public let localPurgeState: String
    public let localPurgeTasks: [String]
    public let localPurgeAckState: String
    public let processingStatus: String
    public let appQueueSchemaVersion: String
    public let ledgerSchemaVersion: String
    public let redactionState: String
    public let affectedCount: Int
    public let safeAffectedIdentities: [String]
    public let clientReportFingerprint: String
    public let clientDedupeKey: String
    public let canonicalStage: String
    public let custodyOwner: String
    public let uploadState: String
    public let deletionState: String
    public let localCopyState: String
    public let serverCopyState: String
    public let serverDeletionState: String
    public let serverAccessState: String
    public let serverStatus: String
    public let serverUploadStatus: String
    public let serverProcessingStatus: String
    public let serverReviewAvailable: Bool
    public let serverReviewStatus: String
    public let lastReconciledAt: String
    public let serverConflictReason: String
    public let serverNextAction: String
    public let timeline: [DesktopSupportIncidentTimelineEvent]
    public let retryHistory: [DesktopSupportIncidentRetryEvent]

    public init?(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection,
        context: DesktopSupportIncidentReportContext = .unknown,
        affectedItems: [DesktopUploadQueueItem] = []
    ) {
        guard Self.reportAvailable(for: projection) else { return nil }
        let boundedAffectedItems = Self.affectedItems(primary: item, affectedItems: affectedItems)
        let serverMeetingFingerprint = DesktopUploadCustodySafeMetadata.optionalPrefixedFingerprint(
            projection.serverMeetingId
        )
        let serverMediaRevisionFingerprint = DesktopUploadCustodySafeMetadata.optionalPrefixedFingerprint(
            projection.serverMediaRevisionId
        )
        let uploadSessionId = item.uploadSessionId ?? item.serverTruth.uploadSessionId
        let expectedParts = max(item.artifactProfile.trackCompleteness.count, 3)
        let uploadedParts = item.serverTruth.acceptedBytesByTrack.count
        let localMediaRetained = item.retentionDecision.localArtifactsRetained && item.state != .terminalDeleted
        let problemCode = Self.problemCode(
            for: item,
            projection: projection,
            serverIdentityPresent: projection.serverMeetingId != nil,
            localMediaRetained: localMediaRetained
        )
        let lastProblemCode = Self.lastSafeProblemCode(item: item, fallback: problemCode)
        let serverCopyState = Self.serverCopyState(item: item, projection: projection)
        let canonicalStage = Self.canonicalStage(item: item, projection: projection)
        let serverDeletionState = Self.safeCode(item.serverTruth.deletionState)
        let serverAccessState = Self.safeCode(item.serverTruth.accessState)
        let serverStatus = Self.safeCode(item.serverTruth.serverStatus)
        let serverUploadStatus = Self.safeCode(item.serverTruth.uploadStatus)
        let serverProcessingStatus = Self.safeCode(
            item.serverTruth.processingStatus ?? projection.processingState.rawValue
        )
        let serverReviewAvailable = item.serverTruth.reviewAvailable ?? projection.reviewAvailable
        let serverReviewStatus = Self.safeCode(item.serverTruth.reviewStatus)
        let localCopyState = Self.localCopyState(item)
        let retryHistory = Self.retryHistory(item)
        let timeline = Self.timeline(item: item, projection: projection)

        self.schemaVersion = Self.schemaVersion
        self.appName = context.appName
        self.bundleID = context.bundleID
        self.appVersion = context.appVersion
        self.buildVersion = context.buildVersion
        self.macOSVersion = context.macOSVersion
        self.architecture = context.architecture
        self.locale = context.locale
        self.timezone = context.timezone
        self.environmentBaseURLIdentity = context.environmentBaseURLIdentity
        self.workspaceFingerprint = context.workspaceFingerprint
        self.userFingerprint = context.userFingerprint
        self.deviceFingerprint = context.deviceFingerprint
        self.safeDeviceIdentifier = context.safeDeviceIdentifier
        self.safeRecordingIdentity = projection.serverMeetingId.map {
            "server:\(DesktopUploadCustodySafeMetadata.prefixedFingerprint($0))"
        } ?? "local:\(DesktopUploadCustodySafeMetadata.prefixedFingerprint(item.directoryId))"
        self.localRecordingIDFingerprint = DesktopUploadCustodySafeMetadata.prefixedFingerprint(item.directoryId)
        self.serverMeetingFingerprint = serverMeetingFingerprint
        self.serverMediaRevisionFingerprint = serverMediaRevisionFingerprint
        self.serverMeetingPresent = projection.serverMeetingId != nil
        self.serverMediaRevisionPresent = projection.serverMediaRevisionId != nil
        self.custodyLifecycleState = projection.custodyState.rawValue
        self.uploadQueueItemState = item.state.rawValue
        self.retryClass = projection.retryClass.rawValue
        self.retryMode = Self.retryMode(item: item, projection: projection)
        self.normalUserAction = projection.normalUserAction.rawValue
        self.failureCategory = Self.failureCategory(item: item, projection: projection)
        self.problemCode = problemCode
        self.syncConflictState = item.syncConflictState.rawValue
        self.createdAt = DesktopUploadCustodySafeMetadata.isoDateText(item.createdAt)
        self.updatedAt = DesktopUploadCustodySafeMetadata.isoDateText(item.updatedAt)
        self.retentionDeadline = projection.retentionDeadline
            .map(DesktopUploadCustodySafeMetadata.isoDateText) ?? "not_applicable"
        self.serverIdentityPresent = projection.serverMeetingId != nil
        self.localMediaRetained = localMediaRetained
        self.dataLossRisk = serverCopyState == "confirmed" ? "low" : (localMediaRetained ? "possible" : "elevated")
        self.serverCopyKnown = serverCopyState == "confirmed"
        self.uploadAttemptCount = item.attemptCount
        self.lastAttemptAt = Self.lastAttemptAt(item)
            .map(DesktopUploadCustodySafeMetadata.isoDateText) ?? "not_applicable"
        self.nextRetryAt = item.nextRetryAt.map(DesktopUploadCustodySafeMetadata.isoDateText) ?? "not_applicable"
        self.lastSafeHTTPStatus = Self.lastSafeHTTPStatus(Self.lastFailureReason(item))
        self.lastSafeProblemCode = lastProblemCode
        self.uploadSessionPresent = uploadSessionId != nil
        self.uploadSessionFingerprint = DesktopUploadCustodySafeMetadata.optionalPrefixedFingerprint(uploadSessionId)
        self.expectedPartsCount = expectedParts
        self.uploadedPartsCount = uploadedParts
        self.rangeMismatchMetadata = DesktopSupportIncidentRangeMismatchMetadata(
            hasMismatch: item.syncConflictState == .serverRangesInconsistent,
            missingRangeCount: item.syncConflictState == .serverRangesInconsistent ? max(0, expectedParts - uploadedParts) : 0,
            expectedRangeCount: expectedParts,
            uploadedRangeCount: uploadedParts
        )
        self.localFileCompletenessProfile = DesktopSupportIncidentLocalFileCompletenessProfile(item: item)
        self.localPurgeState = projection.localPurgeState.rawValue
        self.localPurgeTasks = projection.localPurgeState == .pending ? ["pending"] : []
        self.localPurgeAckState = projection.localPurgeState == .verified ? "acknowledged" : "not_applicable"
        self.processingStatus = projection.processingState.rawValue
        self.appQueueSchemaVersion = DesktopUploadQueueDocument.schemaVersion
        self.ledgerSchemaVersion = Self.ledgerSchemaVersion
        self.redactionState = DesktopUploadCustodyMetadataSafety.metadataOnly.rawValue
        self.affectedCount = boundedAffectedItems.count
        self.safeAffectedIdentities = Array(boundedAffectedItems.prefix(5)).map(Self.safeAffectedIdentity)
        self.clientReportFingerprint = Self.clientReportFingerprint(
            problemCode: problemCode,
            item: item,
            projection: projection,
            context: context
        )
        self.clientDedupeKey = Self.clientDedupeKey(
            problemCode: problemCode,
            item: item,
            projection: projection,
            context: context
        )
        self.canonicalStage = canonicalStage
        self.custodyOwner = projection.owner.rawValue
        self.uploadState = Self.uploadState(item: item, projection: projection)
        self.deletionState = projection.deletionState.rawValue
        self.localCopyState = localCopyState
        self.serverCopyState = serverCopyState
        self.serverDeletionState = serverDeletionState
        self.serverAccessState = serverAccessState
        self.serverStatus = serverStatus
        self.serverUploadStatus = serverUploadStatus
        self.serverProcessingStatus = serverProcessingStatus
        self.serverReviewAvailable = serverReviewAvailable
        self.serverReviewStatus = serverReviewStatus
        self.lastReconciledAt = item.lastReconciledAt
            .map(DesktopUploadCustodySafeMetadata.isoDateText) ?? "unknown"
        self.serverConflictReason = Self.safeCode(
            item.serverTruth.conflictReason ?? item.failureReason
        )
        self.serverNextAction = Self.safeCode(
            item.serverTruth.nextAction ?? projection.normalUserAction.rawValue
        )
        self.timeline = timeline
        self.retryHistory = retryHistory
    }

    public var safeReportFingerprint: String {
        DesktopUploadCustodySafeMetadata.prefixedFingerprint(
            [
                problemCode,
                failureCategory,
                retryClass,
                syncConflictState,
                workspaceFingerprint,
                deviceFingerprint,
                buildVersion,
                localRecordingIDFingerprint,
                updatedAt
            ].joined(separator: "|"),
            prefix: "report_fpr",
            length: 16
        )
    }

    public var dedupeKey: String {
        DesktopUploadCustodySafeMetadata.prefixedFingerprint(
            [
                problemCode,
                failureCategory,
                retryClass,
                syncConflictState,
                workspaceFingerprint,
                deviceFingerprint,
                buildVersion,
                localRecordingIDFingerprint
            ].joined(separator: "|"),
            prefix: "support_dedupe",
            length: 24
        )
    }

    public var clipboardText: String {
        let json: String
        if let data = try? JSONEncoder().encode(self) {
            json = String(decoding: data, as: UTF8.self)
        } else {
            json = "{}"
        }
        return [
            "GRAF: подробный безопасный отчет о проблеме отправки",
            "Этап: \(canonicalStage)",
            "Проблема: \(problemCode)",
            "Следующее действие: \(serverNextAction)",
            "Серверная копия: \(serverCopyState)",
            "Локальная копия: \(localCopyState)",
            "Схема: \(schemaVersion)",
            "Безопасность: только метаданные; без аудио, текста встречи, путей и токенов.",
            "",
            "GRAF support incident report",
            json
        ].joined(separator: "\n")
    }

    private enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case appName = "app_name"
        case bundleID = "bundle_id"
        case appVersion = "app_version"
        case buildVersion = "build_version"
        case macOSVersion = "macos_version"
        case architecture
        case locale
        case timezone
        case environmentBaseURLIdentity = "environment_base_url_identity"
        case workspaceFingerprint = "workspace_fingerprint"
        case userFingerprint = "user_fingerprint"
        case deviceFingerprint = "device_fingerprint"
        case safeDeviceIdentifier = "safe_device_identifier"
        case safeRecordingIdentity = "safe_recording_identity"
        case localRecordingIDFingerprint = "local_recording_id_fingerprint"
        case serverMeetingFingerprint = "server_meeting_fingerprint"
        case serverMediaRevisionFingerprint = "server_media_revision_fingerprint"
        case serverMeetingPresent = "server_meeting_present"
        case serverMediaRevisionPresent = "server_media_revision_present"
        case custodyLifecycleState = "custody_lifecycle_state"
        case uploadQueueItemState = "upload_queue_item_state"
        case retryClass = "retry_class"
        case retryMode = "retry_mode"
        case normalUserAction = "normal_user_action"
        case failureCategory = "failure_category"
        case problemCode = "problem_code"
        case syncConflictState = "sync_conflict_state"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case retentionDeadline = "retention_deadline"
        case serverIdentityPresent = "server_identity_present"
        case localMediaRetained = "local_media_retained"
        case dataLossRisk = "data_loss_risk"
        case serverCopyKnown = "server_copy_known"
        case uploadAttemptCount = "upload_attempt_count"
        case lastAttemptAt = "last_attempt_at"
        case nextRetryAt = "next_retry_at"
        case lastSafeHTTPStatus = "last_safe_http_status"
        case lastSafeProblemCode = "last_safe_problem_code"
        case uploadSessionPresent = "upload_session_present"
        case uploadSessionFingerprint = "upload_session_fingerprint"
        case expectedPartsCount = "expected_parts_count"
        case uploadedPartsCount = "uploaded_parts_count"
        case rangeMismatchMetadata = "range_mismatch_metadata"
        case localFileCompletenessProfile = "local_file_completeness_profile"
        case localPurgeState = "local_purge_state"
        case localPurgeTasks = "local_purge_tasks"
        case localPurgeAckState = "local_purge_ack_state"
        case processingStatus = "processing_status"
        case appQueueSchemaVersion = "app_queue_schema_version"
        case ledgerSchemaVersion = "ledger_schema_version"
        case redactionState = "redaction_state"
        case affectedCount = "affected_count"
        case safeAffectedIdentities = "safe_affected_identities"
        case clientReportFingerprint = "client_report_fingerprint"
        case clientDedupeKey = "client_dedupe_key"
        case canonicalStage = "canonical_stage"
        case custodyOwner = "custody_owner"
        case uploadState = "upload_state"
        case deletionState = "deletion_state"
        case localCopyState = "local_copy_state"
        case serverCopyState = "server_copy_state"
        case serverDeletionState = "server_deletion_state"
        case serverAccessState = "server_access_state"
        case serverStatus = "server_status"
        case serverUploadStatus = "server_upload_status"
        case serverProcessingStatus = "server_processing_status"
        case serverReviewAvailable = "server_review_available"
        case serverReviewStatus = "server_review_status"
        case lastReconciledAt = "last_reconciled_at"
        case serverConflictReason = "server_conflict_reason"
        case serverNextAction = "server_next_action"
        case timeline
        case retryHistory = "retry_history"
    }

    public static func reportAvailable(for projection: DesktopUploadCustodyProjection) -> Bool {
        switch projection.normalUserAction {
        case .sendSupportReport, .copySafeReport, .openDiagnostics:
            return true
        case .none, .signIn, .chooseWorkspace, .grantPermission, .openReview, .deleteLocalCopy:
            return false
        }
    }

    private static func retryMode(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        switch projection.retryClass {
        case .terminal, .notRetryable:
            return "not_retryable"
        case .automatic, .pausedUntilUserAction, .pausedUntilAdminAction:
            return item.retryMode.rawValue
        }
    }

    private static func failureCategory(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        if projection.copyKey == "custody.terminal_undelivered" || item.syncConflictState == .retentionExpired {
            return "retention_expired"
        }
        if item.syncConflictState != .none {
            return item.syncConflictState.rawValue
        }
        if item.failureCategory != .none {
            return item.failureCategory.rawValue
        }
        return "unknown"
    }

    private static func problemCode(
        for item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection,
        serverIdentityPresent: Bool,
        localMediaRetained: Bool
    ) -> String {
        if item.serverTruth.deletionState.map({ $0 != "none" }) == true ||
            item.syncConflictState == .serverMeetingDeleted {
            return "custody.server_meeting_deleted"
        }
        if item.serverTruth.accessState.map({ $0 != "owner" }) == true ||
            item.syncConflictState == .accessRevoked ||
            item.syncConflictState == .staleDeviceIdentity {
            return "custody.server_access_blocked"
        }
        if projection.copyKey == "custody.terminal_undelivered" && !serverIdentityPresent && localMediaRetained {
            return "custody.retention_expired.local_retained"
        }
        if projection.custodyState == .cannotSend {
            return "custody.local_artifacts_unavailable"
        }
        if item.syncConflictState == .processingFailed || item.syncConflictState == .processingBlocked {
            return "custody.\(item.syncConflictState.rawValue)"
        }
        if let reason = item.failureReason, DesktopUploadCustodySafeMetadata.isSafeCode(reason) {
            return "custody.\(reason)"
        }
        return projection.copyKey
    }

    private static func safeCode(_ value: String?) -> String {
        guard let value, DesktopUploadCustodySafeMetadata.isSafeCode(value) else { return "unknown" }
        return value
    }

    private static func serverCopyState(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        if item.serverTruth.deletionState.map({ $0 != "none" }) == true ||
            projection.deletionState == .serverDeleted {
            return "deleted"
        }
        if item.serverTruth.accessState.map({ $0 != "owner" }) == true ||
            projection.deletionState == .accessBlocked ||
            item.syncConflictState == .accessRevoked ||
            item.syncConflictState == .staleDeviceIdentity {
            return "blocked"
        }
        if item.serverTruth.meetingId != nil ||
            item.serverTruth.finalizedAt != nil ||
            item.state == .uploaded {
            return "confirmed"
        }
        return "unknown"
    }

    private static func canonicalStage(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        if item.serverTruth.deletionState.map({ $0 != "none" }) == true ||
            projection.deletionState == .serverDeleted ||
            item.syncConflictState == .serverMeetingDeleted {
            return "server_deletion"
        }
        if item.serverTruth.accessState.map({ $0 != "owner" }) == true ||
            projection.deletionState == .accessBlocked ||
            item.syncConflictState == .accessRevoked ||
            item.syncConflictState == .staleDeviceIdentity {
            return "server_access"
        }
        if projection.processingState != .notSubmitted ||
            item.syncConflictState == .processingFailed ||
            item.syncConflictState == .processingBlocked {
            return "processing"
        }
        switch projection.uploadState {
        case .finalized:
            return "finalized"
        case .partialUploaded, .sessionCreated:
            return "upload"
        case .blocked:
            return "upload_blocked"
        case .terminal:
            return "retention"
        case .notStarted:
            return "local_queue"
        }
    }

    private static func uploadState(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        projection.uploadState.rawValue
    }

    private static func localCopyState(_ item: DesktopUploadQueueItem) -> String {
        if item.state == .terminalDeleted && !item.retentionDecision.localArtifactsRetained {
            return "deleted"
        }
        if item.retentionDecision.localArtifactsRetained {
            return "retained"
        }
        return "unknown"
    }

    private static func clientReportFingerprint(
        problemCode: String,
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection,
        context: DesktopSupportIncidentReportContext
    ) -> String {
        DesktopUploadCustodySafeMetadata.prefixedFingerprint(
            [problemCode, Self.failureCategory(item: item, projection: projection), projection.retryClass.rawValue,
             item.syncConflictState.rawValue, context.workspaceFingerprint,
             context.deviceFingerprint, context.buildVersion,
             DesktopUploadCustodySafeMetadata.prefixedFingerprint(item.directoryId),
             DesktopUploadCustodySafeMetadata.isoDateText(item.updatedAt)].joined(separator: "|"),
            prefix: "report_fpr",
            length: 16
        )
    }

    private static func clientDedupeKey(
        problemCode: String,
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection,
        context: DesktopSupportIncidentReportContext
    ) -> String {
        DesktopUploadCustodySafeMetadata.prefixedFingerprint(
            [problemCode, Self.failureCategory(item: item, projection: projection), projection.retryClass.rawValue,
             item.syncConflictState.rawValue, context.workspaceFingerprint,
             context.deviceFingerprint, context.buildVersion,
             DesktopUploadCustodySafeMetadata.prefixedFingerprint(item.directoryId)].joined(separator: "|"),
            prefix: "support_dedupe",
            length: 24
        )
    }

    private static func retryHistory(_ item: DesktopUploadQueueItem) -> [DesktopSupportIncidentRetryEvent] {
        item.retryRecords.suffix(5).map { record in
            DesktopSupportIncidentRetryEvent(
                attemptNumber: record.attemptNumber,
                startedAt: DesktopUploadCustodySafeMetadata.isoDateText(record.startedAt),
                finishedAt: record.finishedAt.map(DesktopUploadCustodySafeMetadata.isoDateText) ?? "not_applicable",
                stateBefore: record.stateBefore.rawValue,
                stateAfter: record.stateAfter.rawValue,
                failureCategory: record.failureCategory.rawValue,
                problemCode: safeProblemCode(from: record.failureReason),
                httpStatus: lastSafeHTTPStatus(record.failureReason),
                nextRetryAt: record.nextRetryAt.map(DesktopUploadCustodySafeMetadata.isoDateText) ?? "not_applicable"
            )
        }
    }

    private static func timeline(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> [DesktopSupportIncidentTimelineEvent] {
        var candidates: [(Date, DesktopSupportIncidentTimelineEvent)] = [
            (item.createdAt, DesktopSupportIncidentTimelineEvent(
                event: "created",
                at: DesktopUploadCustodySafeMetadata.isoDateText(item.createdAt),
                source: "local_queue"
            ))
        ]
        for record in item.retryRecords {
            candidates.append((record.startedAt, DesktopSupportIncidentTimelineEvent(
                event: "attempt_started",
                at: DesktopUploadCustodySafeMetadata.isoDateText(record.startedAt),
                source: "local_queue"
            )))
            if let finishedAt = record.finishedAt {
                candidates.append((finishedAt, DesktopSupportIncidentTimelineEvent(
                    event: "attempt_finished",
                    at: DesktopUploadCustodySafeMetadata.isoDateText(finishedAt),
                    source: "local_queue"
                )))
            }
        }
        if let reconciledAt = item.lastReconciledAt {
            candidates.append((reconciledAt, DesktopSupportIncidentTimelineEvent(
                event: "reconciled",
                at: DesktopUploadCustodySafeMetadata.isoDateText(reconciledAt),
                source: "server_truth"
            )))
        }
        if let nextRetryAt = item.nextRetryAt {
            candidates.append((nextRetryAt, DesktopSupportIncidentTimelineEvent(
                event: "next_retry",
                at: DesktopUploadCustodySafeMetadata.isoDateText(nextRetryAt),
                source: "local_queue"
            )))
        }
        if let finalizedAt = item.serverTruth.finalizedAt {
            candidates.append((finalizedAt, DesktopSupportIncidentTimelineEvent(
                event: "finalized",
                at: DesktopUploadCustodySafeMetadata.isoDateText(finalizedAt),
                source: "server_truth"
            )))
        }
        candidates.append((item.retentionDeadline, DesktopSupportIncidentTimelineEvent(
            event: "retention_deadline",
            at: DesktopUploadCustodySafeMetadata.isoDateText(item.retentionDeadline),
            source: "local_queue"
        )))
        return candidates
            .sorted { lhs, rhs in
                if lhs.0 != rhs.0 { return lhs.0 < rhs.0 }
                return lhs.1.event < rhs.1.event
            }
            .suffix(5)
            .map(\.1)
    }

    private static func lastSafeProblemCode(
        item: DesktopUploadQueueItem,
        fallback: String
    ) -> String {
        if item.syncConflictState != .none {
            return item.syncConflictState.rawValue
        }
        guard let reason = item.failureReason else { return fallback }
        let code = reason.split(separator: ":").last.map(String.init) ?? reason
        return DesktopUploadCustodySafeMetadata.isSafeCode(code) ? code : fallback
    }

    private static func safeProblemCode(from reason: String?) -> String {
        guard let reason else { return "unknown" }
        let code = reason.split(separator: ":").last.map(String.init) ?? reason
        return DesktopUploadCustodySafeMetadata.isSafeCode(code) ? code : "unknown"
    }

    private static func lastFailureReason(_ item: DesktopUploadQueueItem) -> String? {
        item.retryRecords.last?.failureReason ?? item.failureReason
    }

    private static func lastSafeHTTPStatus(_ reason: String?) -> String {
        guard let reason, reason.hasPrefix("http_status_") else { return "unknown" }
        let suffix = reason.dropFirst("http_status_".count)
        let status = suffix.split(separator: ":").first.map(String.init) ?? ""
        return status.allSatisfy(\.isNumber) ? status : "unknown"
    }

    private static func lastAttemptAt(_ item: DesktopUploadQueueItem) -> Date? {
        guard let record = item.retryRecords.last else { return nil }
        return record.finishedAt ?? record.startedAt
    }

    private static func affectedItems(
        primary: DesktopUploadQueueItem,
        affectedItems: [DesktopUploadQueueItem]
    ) -> [DesktopUploadQueueItem] {
        var seen = Set<String>()
        var items: [DesktopUploadQueueItem] = []
        for item in [primary] + affectedItems where !seen.contains(item.id) {
            seen.insert(item.id)
            items.append(item)
        }
        return items
    }

    private static func safeAffectedIdentity(_ item: DesktopUploadQueueItem) -> String {
        DesktopUploadCustodySafeMetadata.prefixedFingerprint(
            [
                item.directoryId,
                item.localMediaRevisionId,
                item.serverTruth.meetingId ?? "server_unknown",
                item.syncConflictState.rawValue
            ].joined(separator: "|"),
            prefix: "affected_fpr",
            length: 20
        )
    }
}

public struct DesktopUploadCustodySafeReport: Equatable, Sendable {
    public static let schemaVersion = "desktop-custody-safe-report.v1"

    public let schemaVersion: String
    public let safeRecordingIdentity: String
    public let reasonCategory: String
    public let problemCode: String
    public let owner: DesktopUploadCustodyOwner
    public let retryClass: DesktopUploadCustodyRetryClass
    public let normalUserAction: DesktopUploadCustodyNormalUserAction
    public let createdAt: Date
    public let updatedAt: Date
    public let lifecycleState: DesktopUploadCustodyState
    public let retentionDeadline: Date?
    public let serverIdentityPresent: Bool
    public let localMediaRetained: Bool
    public let metadataSafety: DesktopUploadCustodyMetadataSafety

    public init?(
        item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) {
        guard Self.safeIncidentAvailable(for: projection) else { return nil }
        self.schemaVersion = Self.schemaVersion
        self.safeRecordingIdentity = Self.safeRecordingIdentity(for: item, projection: projection)
        self.reasonCategory = Self.reasonCategory(for: item, projection: projection)
        self.problemCode = Self.problemCode(for: item, projection: projection)
        self.owner = projection.owner
        self.retryClass = projection.retryClass
        self.normalUserAction = projection.normalUserAction
        self.createdAt = item.createdAt
        self.updatedAt = item.updatedAt
        self.lifecycleState = projection.custodyState
        self.retentionDeadline = projection.retentionDeadline
        self.serverIdentityPresent = projection.serverMeetingId != nil
        self.localMediaRetained = item.retentionDecision.localArtifactsRetained
        self.metadataSafety = .metadataOnly
    }

    public var diagnosticManifest: [String: DiagnosticFieldValue] {
        var incident: [String: DiagnosticFieldValue] = [
            "safeRecordingIdentity": .string(safeRecordingIdentity),
            "reasonCategory": .string(reasonCategory),
            "problemCode": .string(problemCode),
            "owner": .string(owner.rawValue),
            "retryClass": .string(retryClass.rawValue),
            "normalUserAction": .string(normalUserAction.rawValue),
            "createdAt": .string(DesktopUploadCustodySafeMetadata.isoDateText(createdAt)),
            "updatedAt": .string(DesktopUploadCustodySafeMetadata.isoDateText(updatedAt)),
            "lifecycleState": .string(lifecycleState.rawValue),
            "serverIdentityPresent": .bool(serverIdentityPresent),
            "localMediaRetained": .bool(localMediaRetained),
            "metadataSafety": .string(metadataSafety.rawValue)
        ]
        if let retentionDeadline {
            incident["retentionDeadline"] = .string(DesktopUploadCustodySafeMetadata.isoDateText(retentionDeadline))
        }
        return [
            "schemaVersion": .string(schemaVersion),
            "redactionState": .string(metadataSafety.rawValue),
            "custodyIncident": .object(incident)
        ]
    }

    public var clipboardText: String {
        [
            "GRAF: безопасный отчет о локальной записи",
            "Что произошло: \(humanProblemText).",
            "Что делать: \(humanActionText)",
            "Локальное хранение: \(localMediaRetained ? "политика считает локальные данные удерживаемыми на этом Mac" : "политика не удерживает локальные данные на этом Mac").",
            "Связь с сервером: \(serverIdentityPresent ? "есть серверный идентификатор записи" : "серверная запись не подтверждена").",
            "Безопасность: отчет содержит только метаданные, без звука, текста встречи, локальных путей и токенов.",
            "",
            "GRAF custody safe report",
            "schema_version=\(schemaVersion)",
            "safe_recording_identity=\(safeRecordingIdentity)",
            "reason_category=\(reasonCategory)",
            "problem_code=\(problemCode)",
            "owner=\(owner.rawValue)",
            "retry_class=\(retryClass.rawValue)",
            "normal_user_action=\(normalUserAction.rawValue)",
            "created_at=\(DesktopUploadCustodySafeMetadata.isoDateText(createdAt))",
            "updated_at=\(DesktopUploadCustodySafeMetadata.isoDateText(updatedAt))",
            "lifecycle_state=\(lifecycleState.rawValue)",
            "retention_deadline=\(retentionDeadline.map(DesktopUploadCustodySafeMetadata.isoDateText) ?? "none")",
            "server_identity_present=\(serverIdentityPresent)",
            "local_media_retained=\(localMediaRetained)",
            "metadata_safety=\(metadataSafety.rawValue)"
        ].joined(separator: "\n")
    }

    private var humanProblemText: String {
        switch lifecycleState {
        case .terminalUndelivered:
            return "истек срок автоматической отправки, запись не отправлена"
        case .retainedAwaitingCondition where owner == .workspaceAdmin:
            return "нужна проверка доступа или политики рабочего пространства"
        case .retainedAwaitingCondition:
            return "отправка остановлена до действия в приложении"
        case .cannotSend:
            return "локальную запись нельзя безопасно отправить"
        case .processing:
            return "серверная обработка требует проверки"
        default:
            return "нужна проверка поддержки"
        }
    }

    private var humanActionText: String {
        switch owner {
        case .workspaceAdmin:
            return "отправьте этот отчет администратору рабочего пространства или поддержке."
        case .support:
            return "отправьте этот отчет поддержке."
        case .policyLifecycle:
            return "отправьте этот отчет поддержке, если запись еще нужна."
        case .meetingOwner:
            return "выполните действие в приложении; отчет можно передать поддержке."
        case .productAutomatic:
            return "приложение продолжит автоматически; отчет можно передать поддержке."
        }
    }

    private static func safeIncidentAvailable(for projection: DesktopUploadCustodyProjection) -> Bool {
        DesktopSupportIncidentReport.reportAvailable(for: projection)
    }

    private static func safeRecordingIdentity(
        for item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        if let serverMeetingId = projection.serverMeetingId, !serverMeetingId.isEmpty {
            return "server:\(DesktopUploadCustodySafeMetadata.shortFingerprint(serverMeetingId))"
        }
        return "local:\(DesktopUploadCustodySafeMetadata.shortFingerprint(item.directoryId))"
    }

    private static func reasonCategory(
        for item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        if item.syncConflictState != .none {
            return item.syncConflictState.rawValue
        }
        if item.failureCategory != .none {
            return item.failureCategory.rawValue
        }
        return projection.copyKey.replacingOccurrences(of: "custody.", with: "")
    }

    private static func problemCode(
        for item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        if item.syncConflictState != .none {
            return item.syncConflictState.rawValue
        }
        if item.failureCategory != .none {
            return item.failureCategory.rawValue
        }
        if let reason = item.failureReason, DesktopUploadCustodySafeMetadata.isSafeCode(reason) {
            return reason
        }
        return projection.copyKey.replacingOccurrences(of: "custody.", with: "")
    }
}

public enum DesktopUploadCustodyCopy {
    public static func title(copyKey: String, count: Int) -> String {
        switch copyKey {
        case "custody.uploading":
            return count > 1 ? "Отправляем записи" : "Отправляем запись"
        case "custody.saved_will_send", "custody.saving_local":
            return count > 1 ? "Записи сохранены" : "Запись сохранена"
        case "custody.needs_sign_in":
            return "Нужен вход"
        case "custody.needs_workspace":
            return "Нужно выбрать рабочее пространство"
        case "custody.needs_admin":
            return "Нужен администратор"
        case "custody.cannot_send":
            return "Не можем отправить запись"
        case "custody.retention_warning":
            return "Срок хранения близко"
        case "custody.terminal_undelivered":
            return "Запись не отправлена"
        case "custody.known_by_server":
            return "Запись на сервере"
        default:
            return "Нужна проверка"
        }
    }

    public static func detail(copyKey: String, count: Int, deadline: Date?) -> String {
        switch copyKey {
        case "custody.uploading":
            return count > 1
                ? "\(count) записи под контролем. Локальные копии сохранены на этом Mac."
                : "Локальная копия сохранена на этом Mac."
        case "custody.saved_will_send", "custody.saving_local":
            return "Отправим автоматически, когда сервер будет доступен."
        case "custody.needs_sign_in":
            return "Войдите, чтобы продолжить отправку. Локальные копии сохранены."
        case "custody.needs_workspace":
            return "Выберите, куда отправить записи. Локальные копии сохранены."
        case "custody.needs_admin":
            return "Проверьте доступ к рабочему пространству или обратитесь к администратору."
        case "custody.cannot_send":
            return "Локальная копия сохранена на этом Mac. Свяжитесь с поддержкой, если проблема повторится."
        case "custody.retention_warning":
            if let deadline {
                return "Локальная копия сохранена до \(dateText(deadline)) по политике хранения."
            }
            return "Локальная копия сохранена до срока политики хранения."
        case "custody.terminal_undelivered":
            return "Автоматическая отправка не выполнится. Локальная копия сохранена на этом Mac. Свяжитесь с поддержкой, если запись ещё нужна."
        case "custody.known_by_server":
            return "Серверный список показывает актуальное состояние."
        default:
            return "Локальная копия сохранена на этом Mac. Свяжитесь с поддержкой, если нужна помощь."
        }
    }

    private static func dateText(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.setLocalizedDateFormatFromTemplate("d MMMM")
        formatter.timeStyle = .none
        return formatter.string(from: date)
    }
}
