import Foundation

public enum RecordingDeletionError: Error {
    case invalidIdentity
    case unsupportedQueueSchema
    case duplicateOperation
}

/// The account executing a command, not necessarily the creator of its target meeting.
public struct RecordingDeletionScope: Codable, Equatable, Sendable {
    public let serverOrigin: String
    public let workspaceID: String
    public let actorUserID: String

    public init(serverOrigin: String, workspaceID: String, actorUserID: String) throws {
        guard var url = URLComponents(string: serverOrigin),
              let host = url.host?.lowercased(), !host.isEmpty,
              url.user == nil, url.password == nil, url.query == nil, url.fragment == nil,
              url.path.isEmpty || url.path == "/",
              Self.validID(workspaceID), Self.validID(actorUserID)
        else { throw RecordingDeletionError.invalidIdentity }
        let scheme = url.scheme?.lowercased()
        guard scheme == "https" || (scheme == "http" && ["127.0.0.1", "localhost", "[::1]"].contains(host))
        else { throw RecordingDeletionError.invalidIdentity }
        url.scheme = scheme
        url.host = host
        url.path = ""
        if (scheme == "https" && url.port == 443) || (scheme == "http" && url.port == 80) {
            url.port = nil
        }
        guard let origin = url.string else { throw RecordingDeletionError.invalidIdentity }
        self.serverOrigin = origin
        self.workspaceID = workspaceID
        self.actorUserID = actorUserID
    }

    static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 240 &&
            value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) } &&
            value.trimmingCharacters(in: .whitespacesAndNewlines) == value
    }

    enum CodingKeys: String, CodingKey { case serverOrigin, workspaceID, actorUserID }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            serverOrigin: values.decode(String.self, forKey: .serverOrigin),
            workspaceID: values.decode(String.self, forKey: .workspaceID),
            actorUserID: values.decode(String.self, forKey: .actorUserID)
        )
    }
}

public enum RecordingDeletionTarget: Codable, Equatable, Sendable {
    case meeting(String)
    /// This endpoint is owner-only: the creator is the actor in the execution scope.
    case ownOrigin(String)

    public var identifier: String {
        switch self { case .meeting(let id), .ownOrigin(let id): id }
    }
}

public enum RecordingDeletionPhase: String, Codable, Sendable {
    case queued, sending, resolving, accepted, rejected, verified

    public var isAccepted: Bool { self == .accepted || self == .verified }
    public var blocksContent: Bool { self != .rejected }
}

/// Stored independently of audio packages so server-only deletions survive a restart too.
public enum RecordingDeletionWaitReason: String, Codable, Sendable {
    case connection, authentication, rateLimit, serverUpdate, localCleanup
}

public struct RecordingDeletionOperation: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public let scope: RecordingDeletionScope
    public let target: RecordingDeletionTarget
    public let requestedAt: Date
    public private(set) var updatedAt: Date
    public private(set) var phase: RecordingDeletionPhase
    public private(set) var attemptCount: Int = 0
    public private(set) var nextAttemptAt: Date?
    public private(set) var receipt: RecordingDeletionReceipt?
    public private(set) var waitReason: RecordingDeletionWaitReason?

    public var blocksContent: Bool { phase.blocksContent }

    public init(
        id: UUID = UUID(), scope: RecordingDeletionScope, target: RecordingDeletionTarget,
        requestedAt: Date
    ) throws {
        guard RecordingDeletionScope.validID(target.identifier) else {
            throw RecordingDeletionError.invalidIdentity
        }
        self.id = id
        self.scope = scope
        self.target = target
        self.requestedAt = requestedAt
        self.updatedAt = requestedAt
        self.phase = .queued
    }

    public func applying(_ phase: RecordingDeletionPhase, at date: Date) -> Self {
        // Accepted deletion is monotonic even when an earlier HTTP operation returns late.
        guard date >= updatedAt, self.phase != .verified,
              !phase.isAccepted || receipt?.matches(target) == true,
              !self.phase.isAccepted || phase == .verified,
              phase != .verified || self.phase == .accepted
        else { return self }
        var next = self
        next.phase = phase
        next.updatedAt = date
        if phase.isAccepted { next.waitReason = nil; next.nextAttemptAt = nil }
        if phase == .sending { next.attemptCount += 1; next.nextAttemptAt = nil; next.waitReason = nil }
        if phase == .resolving {
            let delays: [TimeInterval] = [5, 15, 30, 60]
            next.nextAttemptAt = date.addingTimeInterval(delays[min(max(0, attemptCount - 1), delays.count - 1)])
        }
        return next
    }

    public func waitingBecause(_ reason: RecordingDeletionWaitReason?) -> Self {
        var next = self
        next.waitReason = reason
        return next
    }

    public func waiting(until date: Date) -> Self {
        var next = self
        if !phase.isAccepted { next.nextAttemptAt = max(nextAttemptAt ?? date, date) }
        return next
    }

    public func accepting(_ receipt: RecordingDeletionReceipt, at date: Date) throws -> Self {
        guard receipt.matches(target) else { throw RecordingDeletionError.invalidIdentity }
        if let existing = self.receipt, existing != receipt { throw RecordingDeletionError.invalidIdentity }
        var next = self
        next.receipt = receipt
        return next.applying(.accepted, at: max(date, updatedAt))
    }

    enum CodingKeys: String, CodingKey { case id, scope, target, requestedAt, updatedAt, phase, receipt, attemptCount, nextAttemptAt, waitReason }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            id: values.decode(UUID.self, forKey: .id),
            scope: values.decode(RecordingDeletionScope.self, forKey: .scope),
            target: values.decode(RecordingDeletionTarget.self, forKey: .target),
            requestedAt: values.decode(Date.self, forKey: .requestedAt)
        )
        updatedAt = try values.decode(Date.self, forKey: .updatedAt)
        phase = try values.decode(RecordingDeletionPhase.self, forKey: .phase)
        receipt = try values.decodeIfPresent(RecordingDeletionReceipt.self, forKey: .receipt)
        waitReason = try values.decodeIfPresent(RecordingDeletionWaitReason.self, forKey: .waitReason)
        attemptCount = try values.decodeIfPresent(Int.self, forKey: .attemptCount) ?? 0
        nextAttemptAt = try values.decodeIfPresent(Date.self, forKey: .nextAttemptAt)
        guard !phase.isAccepted || receipt?.matches(target) == true else { throw RecordingDeletionError.invalidIdentity }
        guard attemptCount >= 0 else { throw RecordingDeletionError.invalidIdentity }
        if let receipt, !receipt.matches(target) { throw RecordingDeletionError.invalidIdentity }
        guard updatedAt >= requestedAt else { throw RecordingDeletionError.invalidIdentity }
    }
}

public extension DesktopUploadQueueItem {
    /// A server tombstone is independent of upload progress and of the selected sync conflict.
    var hasConfirmedDeletion: Bool {
        deletionOperation?.phase.isAccepted == true || state == .terminalDeleted || syncConflictState == .serverMeetingDeleted ||
            [
                "requested", "deleting", "active_purge_complete", "pending_backup_expiry",
                "complete", "retryable_failed", "terminal_failed", "policy_blocked",
                "post_egress_limit", "local_purge_unverified", "deleted", "purged"
            ].contains(serverTruth.deletionState ?? "")
    }

    /// Fail closed for unknown lifecycle/access values, without treating them as purge authority.
    var lifecycleBlocksContent: Bool {
        !lifecycleAccessAvailable || deletionOperation?.blocksContent == true || hasConfirmedDeletion ||
            (serverTruth.deletionState != nil && serverTruth.deletionState != "none") ||
            (serverTruth.accessState != nil && serverTruth.accessState != "owner") ||
            [.accessRevoked, .staleDeviceIdentity, .authRequired].contains(syncConflictState)
    }
}

public struct RecordingDeletionReceipt: Codable, Equatable, Sendable {
    public enum Kind: String, Codable, Sendable {
        case meetingDeletion = "meeting_deletion", originCancellation = "origin_cancellation"
    }
    public let receiptType: Kind
    public let requestID: UUID
    public let meetingID: String?
    public let localRecordingID: String?
    public let deletionEpoch: Int?

    enum CodingKeys: String, CodingKey {
        case receiptType = "receipt_type", requestID = "request_id", meetingID = "meeting_id"
        case localRecordingID = "local_recording_id", deletionEpoch = "deletion_epoch"
    }

    public func matches(_ target: RecordingDeletionTarget) -> Bool {
        guard deletionEpoch == nil || deletionEpoch! >= 0 else { return false }
        switch target {
        case .meeting(let id): return receiptType == .meetingDeletion && meetingID == id
        case .ownOrigin(let id): return localRecordingID == id &&
            (receiptType == .originCancellation || meetingID != nil)
        }
    }
}

/// No credential is stored: the digest only recognizes the same native session after restart.
public struct RecordingAuthenticatedContext: Codable, Equatable, Sendable {
    public let scope: RecordingDeletionScope
    public let sessionFingerprint: String
    public init(scope: RecordingDeletionScope, sessionFingerprint: String) {
        self.scope = scope
        self.sessionFingerprint = sessionFingerprint
    }
}

public struct RecordingDeletionRetryAfter: Error, Sendable {
    public let delay: TimeInterval
    public init(delay: TimeInterval) { self.delay = max(1, min(delay, 86400)) }
}
