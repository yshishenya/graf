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
    case copySafeReport = "copy_safe_report"
    case deleteLocalCopy = "delete_local_copy"
}

public enum DesktopUploadCustodyMetadataSafety: String, Codable, CaseIterable, Sendable {
    case metadataOnly = "metadata_only"
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
        if item.state != .uploaded && item.retentionDeadline <= now {
            return Rule(
                custodyState: .terminalUndelivered,
                owner: .policyLifecycle,
                retryClass: .terminal,
                normalUserAction: .copySafeReport,
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
                normalUserAction: .copySafeReport,
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
                normalUserAction: .openDiagnostics,
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
                normalUserAction: .copySafeReport,
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
                normalUserAction: .copySafeReport,
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
                normalUserAction: .copySafeReport,
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
                normalUserAction: .copySafeReport,
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
        case LocalRecordingFailureReason.leakageDetected.rawValue,
             LocalRecordingFailureReason.leakageUnproven.rawValue,
             LocalRecordingFailureReason.leakageNotMeasured.rawValue,
             LocalRecordingFailureReason.insufficientReference.rawValue,
             LocalRecordingFailureReason.silentInput.rawValue:
            return true
        default:
            return false
        }
    }
}

public struct DesktopUploadCustodySummary: Equatable, Sendable {
    public let primaryItem: DesktopUploadQueueItem
    public let primaryProjection: DesktopUploadCustodyProjection
    public let pendingCount: Int
    public let totalCount: Int

    public var copyKey: String { primaryProjection.copyKey }
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
            return "2brain Rec"
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
        return DesktopUploadCustodySummary(
            primaryItem: primary.item,
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

    public static func meetingOwnerActionCount(
        for items: [DesktopUploadQueueItem],
        now: Date = Date()
    ) -> Int {
        visibleCandidates(for: items, now: now).filter { candidate in
            candidate.projection.owner == .meetingOwner &&
                candidate.projection.normalUserAction != .none
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
        projection: DesktopUploadCustodyProjection,
        now _: Date = Date()
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
            "createdAt": .string(Self.dateText(createdAt)),
            "updatedAt": .string(Self.dateText(updatedAt)),
            "lifecycleState": .string(lifecycleState.rawValue),
            "serverIdentityPresent": .bool(serverIdentityPresent),
            "localMediaRetained": .bool(localMediaRetained),
            "metadataSafety": .string(metadataSafety.rawValue)
        ]
        if let retentionDeadline {
            incident["retentionDeadline"] = .string(Self.dateText(retentionDeadline))
        }
        return [
            "schemaVersion": .string(schemaVersion),
            "redactionState": .string(metadataSafety.rawValue),
            "custodyIncident": .object(incident)
        ]
    }

    public var clipboardText: String {
        [
            "2brain Rec: безопасный отчет о локальной записи",
            "Что произошло: \(humanProblemText).",
            "Что делать: \(humanActionText)",
            "Локальная копия: \(localMediaRetained ? "сохранена на этом Mac" : "не хранится на этом Mac").",
            "Серверная копия: \(serverIdentityPresent ? "связана с записью на сервере" : "не подтверждена").",
            "Безопасность: отчет содержит только метаданные, без звука, текста встречи, локальных путей и токенов.",
            "",
            "2brain Rec custody safe report",
            "schema_version=\(schemaVersion)",
            "safe_recording_identity=\(safeRecordingIdentity)",
            "reason_category=\(reasonCategory)",
            "problem_code=\(problemCode)",
            "owner=\(owner.rawValue)",
            "retry_class=\(retryClass.rawValue)",
            "normal_user_action=\(normalUserAction.rawValue)",
            "created_at=\(Self.dateText(createdAt))",
            "updated_at=\(Self.dateText(updatedAt))",
            "lifecycle_state=\(lifecycleState.rawValue)",
            "retention_deadline=\(retentionDeadline.map(Self.dateText) ?? "none")",
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
        switch projection.normalUserAction {
        case .copySafeReport, .openDiagnostics:
            return true
        case .none, .signIn, .chooseWorkspace, .grantPermission, .openReview, .deleteLocalCopy:
            return false
        }
    }

    private static func safeRecordingIdentity(
        for item: DesktopUploadQueueItem,
        projection: DesktopUploadCustodyProjection
    ) -> String {
        if let serverMeetingId = projection.serverMeetingId, !serverMeetingId.isEmpty {
            return "server:\(fingerprint(serverMeetingId))"
        }
        return "local:\(fingerprint(item.directoryId))"
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
        if let reason = item.failureReason, isSafeCode(reason) {
            return reason
        }
        return projection.copyKey.replacingOccurrences(of: "custody.", with: "")
    }

    private static func isSafeCode(_ value: String) -> Bool {
        guard !value.isEmpty, value.count <= 120 else { return false }
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
        return value.unicodeScalars.allSatisfy { allowed.contains($0) }
    }

    private static func fingerprint(_ value: String) -> String {
        let digest = SHA256.hash(data: Data(value.utf8))
        return digest.prefix(8).map { String(format: "%02x", $0) }.joined()
    }

    private static func dateText(_ date: Date) -> String {
        ISO8601DateFormatter().string(from: date)
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
            return "Скопируйте отчет и отправьте администратору или поддержке. Локальные копии сохранены."
        case "custody.cannot_send":
            return "Локальная копия сохранена. Диагностика не содержит аудио и текст встречи."
        case "custody.retention_warning":
            if let deadline {
                return "Локальная копия сохранена до \(dateText(deadline)) по политике хранения."
            }
            return "Локальная копия сохранена до срока политики хранения."
        case "custody.terminal_undelivered":
            return "Скопируйте отчет для поддержки. Метаданные сохранены; восстановление не обещается."
        case "custody.known_by_server":
            return "Серверный список показывает актуальное состояние."
        default:
            return "Локальная копия сохранена. Подробности доступны в безопасном отчете."
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
