import Foundation

/// A server timestamp that must stay decodable when the wire format changes.
/// Sync-state currently emits UTC (`Z`) timestamps, and newer servers may add
/// fractional seconds. A timestamp must never fail the whole proof block.
public struct ServerTimestamp: Equatable, Sendable {
    public let date: Date

    public init(date: Date) {
        self.date = date
    }

    public static func parse(_ raw: String) -> Date? {
        let value = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return nil }
        if let date = internetDate(value, fractional: true) { return date }
        if let date = internetDate(value, fractional: false) { return date }
        return nil
    }

    private static func internetDate(_ value: String, fractional: Bool) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = fractional
            ? [.withInternetDateTime, .withFractionalSeconds]
            : [.withInternetDateTime]
        return formatter.date(from: value)
    }
}

extension ServerTimestamp: Decodable {
    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(String.self)
        guard let date = Self.parse(raw) else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "invalid_server_timestamp"
            )
        }
        self.init(date: date)
    }
}

/// The playback evidence block. Every field is optional on purpose: a missing
/// field is unknown and must never be read as a safe default.
public struct DesktopPlaybackProof: Decodable, Equatable, Sendable {
    public let state: String?
    public let canPlay: Bool?
    public let reasonCode: String?
    /// Server media-revision UUID served by playback.
    public let mediaRevisionId: String?
    /// The local revision string the server identifies for that media revision.
    public let localMediaRevisionId: String?
    public let objectVerified: Bool?
    public let verifiedAt: ServerTimestamp?
    public let automaticRecovery: Bool?

    public init(
        state: String? = nil,
        canPlay: Bool? = nil,
        reasonCode: String? = nil,
        mediaRevisionId: String? = nil,
        localMediaRevisionId: String? = nil,
        objectVerified: Bool? = nil,
        verifiedAt: ServerTimestamp? = nil,
        automaticRecovery: Bool? = nil
    ) {
        self.state = state
        self.canPlay = canPlay
        self.reasonCode = reasonCode
        self.mediaRevisionId = mediaRevisionId
        self.localMediaRevisionId = localMediaRevisionId
        self.objectVerified = objectVerified
        self.verifiedAt = verifiedAt
        self.automaticRecovery = automaticRecovery
    }

    private enum CodingKeys: String, CodingKey {
        case state
        case canPlay = "can_play"
        case reasonCode = "reason_code"
        case mediaRevisionId = "media_revision_id"
        case localMediaRevisionId = "local_media_revision_id"
        case objectVerified = "object_verified"
        case verifiedAt = "verified_at"
        case automaticRecovery = "automatic_recovery"
    }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        state = values.optionalString(.state)
        canPlay = values.optionalBool(.canPlay)
        reasonCode = values.optionalString(.reasonCode)
        mediaRevisionId = values.optionalString(.mediaRevisionId)
        localMediaRevisionId = values.optionalString(.localMediaRevisionId)
        objectVerified = values.optionalBool(.objectVerified)
        verifiedAt = values.optionalTimestamp(.verifiedAt)
        automaticRecovery = values.optionalBool(.automaticRecovery)
    }
}

/// The active upload session only. Custody facts live in
/// `DesktopFinalizedUploadProof`; keeping them out of the active session avoids
/// mixing two different revisions.
public struct DesktopUploadSessionProof: Decodable, Equatable, Sendable {
    public let sessionId: String?
    public let status: String?

    public init(sessionId: String? = nil, status: String? = nil) {
        self.sessionId = sessionId
        self.status = status
    }

    private enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case status
    }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        sessionId = values.optionalString(.sessionId)
        status = values.optionalString(.status)
    }
}

/// The finalized custody block for the same media revision playback serves.
/// `media_revision_id` is the server UUID; `local_media_revision_id` is the local
/// revision string. Both must agree with the playback block.
public struct DesktopFinalizedUploadProof: Decodable, Equatable, Sendable {
    public let sessionId: String?
    public let mediaRevisionId: String?
    public let localMediaRevisionId: String?
    public let archiveAudio: Bool?
    public let finalizedAt: ServerTimestamp?
    public let status: String?

    public init(
        sessionId: String? = nil,
        mediaRevisionId: String? = nil,
        localMediaRevisionId: String? = nil,
        archiveAudio: Bool? = nil,
        finalizedAt: ServerTimestamp? = nil,
        status: String? = nil
    ) {
        self.sessionId = sessionId
        self.mediaRevisionId = mediaRevisionId
        self.localMediaRevisionId = localMediaRevisionId
        self.archiveAudio = archiveAudio
        self.finalizedAt = finalizedAt
        self.status = status
    }

    private enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case mediaRevisionId = "media_revision_id"
        case localMediaRevisionId = "local_media_revision_id"
        case archiveAudio = "archive_audio"
        case finalizedAt = "finalized_at"
        case status
    }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        sessionId = values.optionalString(.sessionId)
        mediaRevisionId = values.optionalString(.mediaRevisionId)
        localMediaRevisionId = values.optionalString(.localMediaRevisionId)
        archiveAudio = values.optionalBool(.archiveAudio)
        finalizedAt = values.optionalTimestamp(.finalizedAt)
        status = values.optionalString(.status)
    }
}

/// Effective retention projection. A null deadline is unknown, never forever.
public struct DesktopRetentionProof: Decodable, Equatable, Sendable {
    public let deleteAfter: ServerTimestamp?
    public let policyState: String?

    public init(deleteAfter: ServerTimestamp? = nil, policyState: String? = nil) {
        self.deleteAfter = deleteAfter
        self.policyState = policyState
    }

    private enum CodingKeys: String, CodingKey {
        case deleteAfter = "delete_after"
        case policyState = "policy_state"
    }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        deleteAfter = values.optionalTimestamp(.deleteAfter)
        policyState = values.optionalString(.policyState)
    }
}

/// Read-only storage status projection. It is report metadata only and never
/// authorizes or blocks local cleanup.
public struct DesktopStorageStatusProof: Decodable, Equatable, Sendable {
    public let billingRole: String?
    public let accessMode: String?
    public let planCode: String?
    public let usedBytes: Int64?
    public let reservedBytes: Int64?
    public let capacityBytes: Int64?
    public let availableBytes: Int64?
    public let threshold: String?
    public let action: String?
    public let actionPath: String?
    public let meetingRetentionDays: Int?
    public let sourceAudioRetentionDays: Int?
    public let retentionPolicyState: String?
    public let observedAt: ServerTimestamp?

    public init(
        billingRole: String? = nil,
        accessMode: String? = nil,
        planCode: String? = nil,
        usedBytes: Int64? = nil,
        reservedBytes: Int64? = nil,
        capacityBytes: Int64? = nil,
        availableBytes: Int64? = nil,
        threshold: String? = nil,
        action: String? = nil,
        actionPath: String? = nil,
        meetingRetentionDays: Int? = nil,
        sourceAudioRetentionDays: Int? = nil,
        retentionPolicyState: String? = nil,
        observedAt: ServerTimestamp? = nil
    ) {
        self.billingRole = billingRole
        self.accessMode = accessMode
        self.planCode = planCode
        self.usedBytes = usedBytes
        self.reservedBytes = reservedBytes
        self.capacityBytes = capacityBytes
        self.availableBytes = availableBytes
        self.threshold = threshold
        self.action = action
        self.actionPath = actionPath
        self.meetingRetentionDays = meetingRetentionDays
        self.sourceAudioRetentionDays = sourceAudioRetentionDays
        self.retentionPolicyState = retentionPolicyState
        self.observedAt = observedAt
    }

    private enum CodingKeys: String, CodingKey {
        case billingRole = "billing_role"
        case accessMode = "access_mode"
        case planCode = "plan_code"
        case usedBytes = "used_bytes"
        case reservedBytes = "reserved_bytes"
        case capacityBytes = "capacity_bytes"
        case availableBytes = "available_bytes"
        case threshold
        case action
        case actionPath = "action_path"
        case meetingRetentionDays = "meeting_retention_days"
        case sourceAudioRetentionDays = "source_audio_retention_days"
        case retentionPolicyState = "retention_policy_state"
        case observedAt = "observed_at"
    }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        billingRole = values.optionalString(.billingRole)
        accessMode = values.optionalString(.accessMode)
        planCode = values.optionalString(.planCode)
        usedBytes = values.optionalInt64(.usedBytes)
        reservedBytes = values.optionalInt64(.reservedBytes)
        capacityBytes = values.optionalInt64(.capacityBytes)
        availableBytes = values.optionalInt64(.availableBytes)
        threshold = values.optionalString(.threshold)
        action = values.optionalString(.action)
        actionPath = values.optionalString(.actionPath)
        meetingRetentionDays = values.optionalInt(.meetingRetentionDays)
        sourceAudioRetentionDays = values.optionalInt(.sourceAudioRetentionDays)
        retentionPolicyState = values.optionalString(.retentionPolicyState)
        observedAt = values.optionalTimestamp(.observedAt)
    }
}

/// Optional projection of the additive sync-state proof blocks. It is decoded
/// per response and is never persisted in the upload queue.
public struct DesktopServerProof: Decodable, Equatable, Sendable {
    public let meetingId: String?
    public let deletionState: String?
    public let accessState: String?
    public let conflictState: String?
    public let playback: DesktopPlaybackProof?
    public let uploadSession: DesktopUploadSessionProof?
    public let finalizedUpload: DesktopFinalizedUploadProof?
    public let retention: DesktopRetentionProof?
    public let storage: DesktopStorageStatusProof?

    public init(
        meetingId: String? = nil,
        deletionState: String? = nil,
        accessState: String? = nil,
        conflictState: String? = nil,
        playback: DesktopPlaybackProof? = nil,
        uploadSession: DesktopUploadSessionProof? = nil,
        finalizedUpload: DesktopFinalizedUploadProof? = nil,
        retention: DesktopRetentionProof? = nil,
        storage: DesktopStorageStatusProof? = nil
    ) {
        self.meetingId = meetingId
        self.deletionState = deletionState
        self.accessState = accessState
        self.conflictState = conflictState
        self.playback = playback
        self.uploadSession = uploadSession
        self.finalizedUpload = finalizedUpload
        self.retention = retention
        self.storage = storage
    }

    private enum CodingKeys: String, CodingKey {
        case meeting
        case playback
        case uploadSession = "upload_session"
        case finalizedUpload = "finalized_upload"
        case conflict
        case storage
    }

    private enum MeetingKeys: String, CodingKey {
        case meetingId = "meeting_id"
        case deletionState = "deletion_state"
        case accessState = "access_state"
        case retention
    }

    private enum ConflictKeys: String, CodingKey {
        case state
    }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        let meeting = (try? values.nestedContainer(keyedBy: MeetingKeys.self, forKey: .meeting))
        let conflict = (try? values.nestedContainer(keyedBy: ConflictKeys.self, forKey: .conflict))
        meetingId = meeting?.optionalString(.meetingId)
        deletionState = meeting?.optionalString(.deletionState)
        accessState = meeting?.optionalString(.accessState)
        conflictState = conflict?.optionalString(.state)
        playback = (try? values.decodeIfPresent(DesktopPlaybackProof.self, forKey: .playback)) ?? nil
        uploadSession = (try? values.decodeIfPresent(DesktopUploadSessionProof.self, forKey: .uploadSession)) ?? nil
        finalizedUpload = (try? values.decodeIfPresent(DesktopFinalizedUploadProof.self, forKey: .finalizedUpload)) ?? nil
        retention = (try? meeting?.decodeIfPresent(DesktopRetentionProof.self, forKey: .retention)) ?? nil
        storage = (try? values.decodeIfPresent(DesktopStorageStatusProof.self, forKey: .storage)) ?? nil
    }
}

/// Additive fields must never turn a wrong-typed value into a decode failure
/// for the whole sync-state response.
private extension KeyedDecodingContainer {
    func optionalString(_ key: Key) -> String? {
        (try? decodeIfPresent(String.self, forKey: key)) ?? nil
    }

    func optionalBool(_ key: Key) -> Bool? {
        (try? decodeIfPresent(Bool.self, forKey: key)) ?? nil
    }

    func optionalInt(_ key: Key) -> Int? {
        (try? decodeIfPresent(Int.self, forKey: key)) ?? nil
    }

    func optionalInt64(_ key: Key) -> Int64? {
        (try? decodeIfPresent(Int64.self, forKey: key)) ?? nil
    }

    func optionalTimestamp(_ key: Key) -> ServerTimestamp? {
        (try? decodeIfPresent(ServerTimestamp.self, forKey: key)) ?? nil
    }
}
