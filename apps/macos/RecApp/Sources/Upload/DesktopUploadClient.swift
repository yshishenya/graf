import CryptoKit
import Foundation
import TwoBrainRecShared

public protocol DesktopUploadClientProtocol: Sendable {
    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation?
    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult
    func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask]
    func acknowledgeLocalPurgeTask(
        _ task: DesktopLocalPurgeTask,
        state: DesktopLocalPurgeTaskState,
        reasonCode: String,
        completedAt: Date?
    ) async throws -> DesktopLocalPurgeTask
}

public extension DesktopUploadClientProtocol {
    func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        nil
    }
}

public struct DesktopUploadReconciliation: Equatable, Sendable {
    public let serverTruth: ServerTruthFingerprint
    public let conflictState: DesktopSyncConflictState
    public let conflictReason: String?
    public let nextAction: String?

    public init(
        serverTruth: ServerTruthFingerprint,
        conflictState: DesktopSyncConflictState = .none,
        conflictReason: String? = nil,
        nextAction: String? = nil
    ) {
        self.serverTruth = serverTruth
        self.conflictState = conflictState
        self.conflictReason = conflictReason
        self.nextAction = nextAction
    }

    public var canContinueUpload: Bool {
        conflictState == .none ||
            (conflictState == .uploadSessionExpired && nextAction == "create_upload_session")
    }
}

public struct DesktopUploadResult: Sendable {
    public let state: UploadItemState
    public let serverTruth: ServerTruthFingerprint

    public init(state: UploadItemState, serverTruth: ServerTruthFingerprint) {
        self.state = state
        self.serverTruth = serverTruth
    }
}

public enum DesktopLocalPurgeTaskType: String, Codable, Sendable {
    case purgeLocalBuffers = "purge_local_buffers"
    case purgeLocalExports = "purge_local_exports"
    case confirmLocalExpiry = "confirm_local_expiry"
}

public enum DesktopLocalPurgeTaskState: String, Codable, Sendable {
    case pending
    case claimed
    case acknowledged
    case failed
    case unreachable
    case expired
    case localExpiryReliedUpon = "local_expiry_relied_upon"
}

public enum DesktopLocalPurgeVerificationState: String, Codable, CaseIterable, Sendable {
    case deleted
    case tombstoned
    case cryptographicallyUnrecoverable = "cryptographically_unrecoverable"
    case failed
    case unverified
}

public struct DesktopLocalPurgeTask: Decodable, Equatable, Sendable {
    public let taskId: String
    public let meetingId: String
    public let taskType: DesktopLocalPurgeTaskType
    public let state: DesktopLocalPurgeTaskState
    public let safeReason: String?
    public let expiresAt: Date
    public let ackURL: URL?

    private enum CodingKeys: String, CodingKey {
        case taskId = "task_id"
        case meetingId = "meeting_id"
        case taskType = "task_type"
        case state
        case safeReason = "safe_reason"
        case expiresAt = "expires_at"
        case ackURL = "ack_url"
    }
}

public struct DesktopLocalPurgeAcknowledgement: Encodable, Equatable, Sendable {
    public let state: DesktopLocalPurgeTaskState
    public let reasonCode: String
    public let clientVersion: String?
    public let completedAt: Date?

    public init(
        state: DesktopLocalPurgeTaskState,
        reasonCode: String,
        clientVersion: String? = nil,
        completedAt: Date? = nil
    ) {
        self.state = state
        self.reasonCode = reasonCode
        self.clientVersion = clientVersion
        self.completedAt = completedAt
    }

    public init(
        verificationState: DesktopLocalPurgeVerificationState,
        clientVersion: String? = nil,
        completedAt: Date? = nil
    ) {
        let mapped = Self.stateAndReason(for: verificationState)
        self.init(
            state: mapped.state,
            reasonCode: mapped.reasonCode,
            clientVersion: clientVersion,
            completedAt: completedAt
        )
    }

    public static func stateAndReason(
        for verificationState: DesktopLocalPurgeVerificationState
    ) -> (state: DesktopLocalPurgeTaskState, reasonCode: String) {
        switch verificationState {
        case .deleted:
            return (.acknowledged, "local_artifacts_deleted")
        case .tombstoned:
            return (.acknowledged, "local_tombstone_verified")
        case .cryptographicallyUnrecoverable:
            return (.acknowledged, "cryptographically_unrecoverable")
        case .failed:
            return (.failed, "local_purge_failed")
        case .unverified:
            return (.failed, "local_purge_unverified")
        }
    }

    private enum CodingKeys: String, CodingKey {
        case state
        case reasonCode = "reason_code"
        case clientVersion = "client_version"
        case completedAt = "completed_at"
    }
}

public enum DesktopUploadClientError: Error, CustomStringConvertible, Sendable {
    case invalidBaseURL
    case localFileMissing(String)
    case invalidResponse
    case httpStatus(Int, String)
    case serverStillMissingRanges

    public var description: String {
        switch self {
        case .invalidBaseURL:
            return "invalid_base_url"
        case .localFileMissing(let path):
            return "local_file_missing:\(URL(fileURLWithPath: path).lastPathComponent)"
        case .invalidResponse:
            return "invalid_response"
        case .httpStatus(let status, let code):
            return "http_status_\(status):\(code)"
        case .serverStillMissingRanges:
            return "server_still_missing_ranges"
        }
    }

    public var failureCategory: UploadFailureCategory {
        switch self {
        case .invalidBaseURL, .invalidResponse:
            return .unknown
        case .localFileMissing:
            return .localResource
        case .serverStillMissingRanges:
            return .serverValidation
        case .httpStatus(let status, let code):
            return Self.failureCategory(forHTTPStatus: status, code: code)
        }
    }

    public static func failureCategory(forHTTPStatus status: Int, code: String) -> UploadFailureCategory {
        switch code {
        case "auth_required", "session_expired", "tenant_context_missing", "tenant_scope_denied",
             "meeting_scope_denied", "device_scope_denied":
            return .authSession
        case "upload_part_bytes_exceeded", "track_bytes_exceeded", "package_bytes_exceeded",
             "recording_duration_exceeded":
            return .storageQuota
        case "network_unavailable", "storage_unavailable", "persistence_unavailable",
             "processing_store_unavailable", "cabinet_store_unavailable":
            return .network
        case "checksum_mismatch", "checksum_conflict", "range_conflict", "range_overlap",
             "expected_track_size_exceeded", "invalid_expected_track_size",
             "unexpected_expected_track_size_role", "invalid_part_number", "invalid_byte_offset",
             "idempotency_conflict", "active_upload_session_exists", "media_revision_conflict",
             "session_terminal", "meeting_deletion_active":
            return .serverValidation
        default:
            if status == 401 || status == 403 {
                return .authSession
            }
            if status == 413 {
                return .storageQuota
            }
            if status == 400 || status == 409 || status == 422 {
                return .serverValidation
            }
            if status == 503 || status == 408 || status == 429 {
                return .network
            }
            return .unknown
        }
    }
}

public struct DesktopUploadClient: DesktopUploadClientProtocol {
    public static let defaultPartSizeBytes = 1024 * 1024 * 1024
    public static let baseURLEnvironmentKey = "TWO_BRAIN_REC_UPLOAD_BASE_URL"
    public static let fallbackBaseURLEnvironmentKey = "TWO_BRAIN_REC_CABINET_BASE_URL"
    public static let baseURLUserDefaultsKey = "TWO_BRAIN_REC_UPLOAD_BASE_URL"
    public static let fallbackBaseURLUserDefaultsKey = "TWO_BRAIN_REC_CABINET_BASE_URL"
    public static let packagedDefaultBaseURL = "https://rec.2brain.pro"
    public static let uploadBearerTokenEnvironmentKey = "TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN"
    public static let desktopCalendarUpcomingPath = "/api/v1/desktop/calendar/upcoming"

    private let baseURL: URL
    private let headers: [String: String]
    private let partSizeBytes: Int
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(
        baseURL: URL,
        headers: [String: String] = [:],
        partSizeBytes: Int = Self.defaultPartSizeBytes
    ) {
        self.baseURL = baseURL
        self.headers = headers
        self.partSizeBytes = max(64 * 1024, partSizeBytes)
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder
    }

    public var baseOrigin: URL {
        baseURL
    }

    public var sanitizedHeaderPreview: [String: String] {
        headers.reduce(into: [:]) { result, pair in
            result[pair.key] = Self.shouldRedactHeader(named: pair.key) ? "<redacted>" : pair.value
        }
    }

    public static func configuredFromEnvironment() -> DesktopUploadClient? {
        configured(from: ProcessInfo.processInfo.environment)
    }

    public static func configured(
        from environment: [String: String],
        defaults: UserDefaults = .standard,
        includePackagedDefault: Bool = true
    ) -> DesktopUploadClient? {
        guard let rawURL = configuredBaseURLCandidate(
            from: environment,
            defaults: defaults,
            includePackagedDefault: includePackagedDefault
        ),
            let url = normalizedHTTPOrigin(rawURL)
        else {
            return nil
        }

        let headers = configuredHeaders(from: environment)
        return DesktopUploadClient(baseURL: url, headers: headers)
    }

    public static func configuredHeaders(from environment: [String: String]) -> [String: String] {
        var headers: [String: String] = [
            "X-Client-Version": environment["TWO_BRAIN_REC_CLIENT_VERSION"] ?? "local-macos"
        ]
        let headerEnvironmentKeys: [(String, String)] = [
            ("TWO_BRAIN_REC_USER_ID", "X-User-Id"),
            ("TWO_BRAIN_REC_ORGANIZATION_ID", "X-Organization-Id"),
            ("TWO_BRAIN_REC_WORKSPACE_ID", "X-Workspace-Id"),
            ("TWO_BRAIN_REC_DEVICE_ID", "X-Device-Id")
        ]
        for (environmentKey, header) in headerEnvironmentKeys {
            if let value = environment[environmentKey], !value.isEmpty {
                headers[header] = value
            }
        }

        let rawBearerToken = environment[uploadBearerTokenEnvironmentKey]
        if let authorization = authorizationHeaderValue(forBearerToken: rawBearerToken) {
            headers["Authorization"] = authorization
        }
        return headers
    }

    public static func authorizationHeaderValue(forBearerToken rawToken: String?) -> String? {
        guard let rawToken else { return nil }
        let trimmed = rawToken.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if trimmed.range(of: "Bearer ", options: [.anchored, .caseInsensitive]) != nil {
            return trimmed
        }
        return "Bearer \(trimmed)"
    }

    private static func configuredBaseURLCandidate(
        from environment: [String: String],
        defaults: UserDefaults,
        includePackagedDefault: Bool
    ) -> String? {
        let candidates = [
            environment[baseURLEnvironmentKey],
            environment[fallbackBaseURLEnvironmentKey],
            defaults.string(forKey: baseURLUserDefaultsKey),
            defaults.string(forKey: fallbackBaseURLUserDefaultsKey),
            includePackagedDefault ? packagedDefaultBaseURL : nil
        ]
        return candidates.lazy
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .first { !$0.isEmpty }
    }

    private static func normalizedHTTPOrigin(_ rawURL: String) -> URL? {
        guard let url = URL(string: rawURL),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              url.host?.isEmpty == false
        else {
            return nil
        }
        var components = URLComponents()
        components.scheme = scheme
        components.host = url.host
        components.port = url.port
        return components.url
    }

    private static func shouldRedactHeader(named name: String) -> Bool {
        let lowered = name.lowercased()
        return lowered.contains("authorization") ||
            lowered.contains("token") ||
            lowered.contains("cookie") ||
            lowered.contains("secret")
    }

    public func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        try ensureLocalFilesExist(item)

        let meeting = if let meetingId = item.meetingId {
            MeetingResponse(
                meeting_id: meetingId,
                local_recording_id: item.directoryId,
                local_media_revision_id: item.localMediaRevisionId,
                title: nil,
                title_source: "generic",
                media_revision: item.mediaRevisionId.map {
                    MediaRevisionSummary(media_revision_id: $0, local_media_revision_id: item.localMediaRevisionId)
                },
                status: "uploading",
                processing_status: "not_submitted"
            )
        } else {
            try await createMeeting(item)
        }
        await linkCalendarContextIfNeeded(item, meetingId: meeting.meeting_id)

        let uploadSession = if let sessionId = item.uploadSessionId {
            try await getUploadSession(sessionId: sessionId)
        } else {
            try await createUploadSession(item, meetingId: meeting.meeting_id)
        }

        var acceptedBytes = uploadSession.accepted_bytes_by_track ?? [:]
        for descriptor in Self.uploadFileDescriptors(for: item) {
            let uploaded = try await uploadFile(
                descriptor: descriptor,
                sessionId: uploadSession.session_id,
                alreadyAcceptedBytes: acceptedBytes[descriptor.transportRole.rawValue, default: 0]
            )
            acceptedBytes[descriptor.transportRole.rawValue] = max(
                acceptedBytes[descriptor.transportRole.rawValue, default: 0],
                uploaded
            )
        }

        let missing = try await missingRanges(sessionId: uploadSession.session_id)
        if !missing.missing_ranges_by_track.isEmpty {
            for descriptor in Self.uploadFileDescriptors(for: item) {
                for range in missing.missing_ranges_by_track[descriptor.transportRole.rawValue] ?? [] {
                    _ = try await uploadRange(
                        descriptor: descriptor,
                        sessionId: uploadSession.session_id,
                        range: range
                    )
                }
            }
        }

        let missingAfterRetry = try await missingRanges(sessionId: uploadSession.session_id)
        if !missingAfterRetry.missing_ranges_by_track.isEmpty {
            throw DesktopUploadClientError.serverStillMissingRanges
        }

        let finalize = try await finalizeUpload(
            item: item,
            sessionId: uploadSession.session_id,
            meetingId: meeting.meeting_id
        )
        let finalSession = finalize.upload_session
        let finalMediaRevisionId = finalSession.media_revision_id ??
            finalize.meeting.media_revision?.media_revision_id ??
            meeting.media_revision?.media_revision_id ??
            item.mediaRevisionId
        let serverTruth = ServerTruthFingerprint(
            meetingId: finalSession.meeting_id,
            mediaRevisionId: finalMediaRevisionId,
            uploadSessionId: finalSession.session_id,
            serverStatus: finalSession.status,
            processingStatus: finalSession.processing_status,
            acceptedBytesByTrack: finalSession.accepted_bytes_by_track ?? acceptedBytes,
            requiredTrackSha256: item.artifactProfile.trackCompleteness.reduce(into: [:]) { result, track in
                result[track.transportRole.rawValue] = track.sha256
            },
            finalizedAt: Date(),
            desktopTruthRule: finalSession.desktop_truth_rule
        )
        return DesktopUploadResult(state: .uploaded, serverTruth: serverTruth)
    }

    public func reconcile(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? {
        let request = try request(
            path: "/api/v1/desktop/recordings/\(item.directoryId)/sync-state",
            method: "GET",
            queryItems: [URLQueryItem(name: "local_media_revision_id", value: item.localMediaRevisionId)]
        )
        do {
            let response: DesktopRecordingSyncStateResponse = try await perform(request)
            let conflictState = DesktopSyncConflictState(rawValue: response.conflict.state) ?? .dependencyUnavailable
            let serverTruth = ServerTruthFingerprint(
                meetingId: response.meeting.meeting_id,
                mediaRevisionId: response.media_revision.media_revision_id,
                uploadSessionId: response.upload_session.session_id,
                serverStatus: response.meeting.status,
                processingStatus: response.processing.status,
                acceptedBytesByTrack: response.upload_session.accepted_bytes_by_track,
                requiredTrackSha256: response.media_revision.track_sha256_by_role,
                desktopTruthRule: response.upload_session.desktop_truth_rule
            )
            return DesktopUploadReconciliation(
                serverTruth: serverTruth,
                conflictState: conflictState,
                conflictReason: response.conflict.reason,
                nextAction: response.conflict.next_action
            )
        } catch DesktopUploadClientError.httpStatus(let status, let code)
            where Self.isServerUnknownRecording(status: status, code: code) {
            return nil
        }
    }

    public func listLocalPurgeTasks() async throws -> [DesktopLocalPurgeTask] {
        let request = try request(path: "/api/v1/desktop/local-purge-tasks", method: "GET")
        let response: LocalPurgeTaskListResponse = try await perform(request)
        return response.tasks
    }

    public func listDesktopCalendarUpcoming(
        beforeMinutes: Int = 15,
        afterMinutes: Int = 60
    ) async throws -> DesktopCalendarPromptResponse {
        let request = try request(
            path: Self.desktopCalendarUpcomingPath,
            method: "GET",
            queryItems: [
                URLQueryItem(name: "before_minutes", value: String(beforeMinutes)),
                URLQueryItem(name: "after_minutes", value: String(afterMinutes))
            ]
        )
        return try await perform(request)
    }

    public func acknowledgeLocalPurgeTask(
        _ task: DesktopLocalPurgeTask,
        state: DesktopLocalPurgeTaskState,
        reasonCode: String,
        completedAt: Date? = nil
    ) async throws -> DesktopLocalPurgeTask {
        let path: String
        if let ackPath = task.ackURL?.path, !ackPath.isEmpty {
            path = ackPath
        } else {
            path = "/api/v1/desktop/local-purge-tasks/\(task.taskId)/ack"
        }
        let request = try jsonRequest(
            path: path,
            method: "POST",
            body: DesktopLocalPurgeAcknowledgement(
                state: state,
                reasonCode: reasonCode,
                clientVersion: headers["X-Client-Version"],
                completedAt: completedAt
            )
        )
        return try await perform(request)
    }

    public static func backendRole(for localRole: AudioTrackRole) -> DesktopUploadTransportRole? {
        DesktopUploadTransportRole.role(forLocalTrackRole: localRole)
    }

    public static func idempotencyKey(item: DesktopUploadQueueItem, scope: String) -> String {
        "desktop-upload:\(scope):\(item.directoryId):\(item.sessionId)"
    }

    public static func partNumber(forByteOffset byteOffset: Int64, partSizeBytes: Int) -> Int {
        max(0, Int(max(0, byteOffset) / Int64(max(1, partSizeBytes))))
    }

    public static func isServerUnknownRecording(status: Int, code: String) -> Bool {
        status == 404 && code == "recording_not_found"
    }

    public static func uploadFileDescriptors(for item: DesktopUploadQueueItem) -> [DesktopUploadFileDescriptor] {
        [
            DesktopUploadFileDescriptor(
                transportRole: .microphone,
                url: URL(fileURLWithPath: item.microphonePath),
                byteCount: item.artifactProfile.microphoneSizeBytes,
                sha256: item.artifactProfile.microphoneSha256,
                codec: "wav-pcm-s16le",
                sampleRateHz: 16_000,
                channelCount: 1,
                durationSeconds: item.artifactProfile.durationSeconds
            ),
            DesktopUploadFileDescriptor(
                transportRole: .system,
                url: URL(fileURLWithPath: item.systemAudioPath),
                byteCount: item.artifactProfile.systemAudioSizeBytes,
                sha256: item.artifactProfile.systemAudioSha256,
                codec: "wav-pcm-s16le",
                sampleRateHz: 16_000,
                channelCount: 1,
                durationSeconds: item.artifactProfile.durationSeconds
            ),
            DesktopUploadFileDescriptor(
                transportRole: .manifest,
                url: URL(fileURLWithPath: item.manifestPath),
                byteCount: item.artifactProfile.manifestSizeBytes,
                sha256: item.artifactProfile.manifestSha256,
                codec: "json",
                sampleRateHz: 1,
                channelCount: 1,
                durationSeconds: 1
            )
        ]
    }

    public static func createMeetingPayload(for item: DesktopUploadQueueItem) -> DesktopCreateMeetingPayload {
        DesktopCreateMeetingPayload(
            local_recording_id: item.directoryId,
            local_media_revision_id: item.localMediaRevisionId,
            title: item.recordingMetadata?.title,
            started_at: item.recordingStartedAt,
            ended_at: item.recordingStoppedAt,
            duration_seconds: item.artifactProfile.durationSeconds
        )
    }

    private func createMeeting(_ item: DesktopUploadQueueItem) async throws -> MeetingResponse {
        var request = try jsonRequest(
            path: "/api/v1/meetings",
            method: "POST",
            body: Self.createMeetingPayload(for: item)
        )
        request.setValue(Self.idempotencyKey(item: item, scope: "meeting"), forHTTPHeaderField: "Idempotency-Key")
        return try await perform(request)
    }

    private func createUploadSession(
        _ item: DesktopUploadQueueItem,
        meetingId: String
    ) async throws -> UploadSessionResponse {
        var request = try jsonRequest(
            path: "/api/v1/meetings/\(meetingId)/upload-sessions",
            method: "POST",
            body: CreateUploadSessionRequest(
                expected_tracks: DesktopUploadTransportRole.allCases.map(\.rawValue),
                expected_track_sizes: [
                    DesktopUploadTransportRole.microphone.rawValue: item.artifactProfile.microphoneSizeBytes,
                    DesktopUploadTransportRole.system.rawValue: item.artifactProfile.systemAudioSizeBytes,
                    DesktopUploadTransportRole.manifest.rawValue: item.artifactProfile.manifestSizeBytes
                ],
                manifest_sha256: item.artifactProfile.manifestSha256
            )
        )
        request.setValue(Self.idempotencyKey(item: item, scope: "upload-session"), forHTTPHeaderField: "Idempotency-Key")
        return try await perform(request)
    }

    private func linkCalendarContextIfNeeded(_ item: DesktopUploadQueueItem, meetingId: String) async {
        guard let eventId = item.calendarContextEventId?.trimmingCharacters(in: .whitespacesAndNewlines),
              !eventId.isEmpty
        else {
            return
        }
        do {
            let request = try jsonRequest(
                path: "/api/v1/meetings/\(meetingId)/calendar-context",
                method: "PUT",
                body: DesktopCalendarContextLinkRequest(
                    eventId: eventId,
                    contextReason: "manual_selection"
                )
            )
            let _: MeetingCalendarContextResponse = try await perform(request)
        } catch {
            return
        }
    }

    private func getUploadSession(sessionId: String) async throws -> UploadSessionResponse {
        let request = try request(path: "/api/v1/upload-sessions/\(sessionId)", method: "GET")
        return try await perform(request)
    }

    private func missingRanges(sessionId: String) async throws -> MissingRangesResponse {
        let request = try request(path: "/api/v1/upload-sessions/\(sessionId)/missing-ranges", method: "GET")
        return try await perform(request)
    }

    private func finalizeUpload(
        item: DesktopUploadQueueItem,
        sessionId: String,
        meetingId _: String
    ) async throws -> FinalizeUploadResponse {
        let descriptors = Self.uploadFileDescriptors(for: item).map {
            TrackDescriptor(
                track_role: $0.transportRole.rawValue,
                codec: $0.codec,
                sample_rate_hz: $0.sampleRateHz,
                channel_count: $0.channelCount,
                duration_seconds: $0.durationSeconds,
                byte_length: $0.byteCount,
                sha256: $0.sha256 ?? ""
            )
        }
        let request = try jsonRequest(
            path: "/api/v1/upload-sessions/\(sessionId)/finalize",
            method: "POST",
            body: FinalizeUploadRequest(
                manifest_sha256: item.artifactProfile.manifestSha256 ?? "",
                tracks: descriptors
            )
        )
        return try await perform(request)
    }

    private func uploadFile(
        descriptor: DesktopUploadFileDescriptor,
        sessionId: String,
        alreadyAcceptedBytes: Int64
    ) async throws -> Int64 {
        let handle = try FileHandle(forReadingFrom: descriptor.url)
        defer { try? handle.close() }

        var offset = max(0, alreadyAcceptedBytes)
        try handle.seek(toOffset: UInt64(offset))
        while offset < descriptor.byteCount {
            let data = try handle.read(upToCount: min(partSizeBytes, Int(descriptor.byteCount - offset))) ?? Data()
            guard !data.isEmpty else { break }
            let partNumber = Self.partNumber(forByteOffset: offset, partSizeBytes: partSizeBytes)
            let response = try await uploadPart(
                sessionId: sessionId,
                descriptor: descriptor,
                data: data,
                byteOffset: offset,
                partNumber: partNumber
            )
            offset = max(offset + Int64(data.count), response.byte_offset + response.byte_length)
        }
        return offset
    }

    private func uploadRange(
        descriptor: DesktopUploadFileDescriptor,
        sessionId: String,
        range: MissingRange
    ) async throws -> Int64 {
        let handle = try FileHandle(forReadingFrom: descriptor.url)
        defer { try? handle.close() }

        let start = max(0, range.start)
        let length = max(0, min(range.end, descriptor.byteCount) - start)
        try handle.seek(toOffset: UInt64(start))
        let data = try handle.read(upToCount: Int(length)) ?? Data()
        let partNumber = Self.partNumber(forByteOffset: start, partSizeBytes: partSizeBytes)
        let response = try await uploadPart(
            sessionId: sessionId,
            descriptor: descriptor,
            data: data,
            byteOffset: start,
            partNumber: partNumber
        )
        return response.byte_offset + response.byte_length
    }

    private func uploadPart(
        sessionId: String,
        descriptor: DesktopUploadFileDescriptor,
        data: Data,
        byteOffset: Int64,
        partNumber: Int
    ) async throws -> UploadPartResponse {
        var request = try request(
            path: "/api/v1/upload-sessions/\(sessionId)/tracks/\(descriptor.transportRole.rawValue)/parts/\(partNumber)",
            method: "PUT"
        )
        request.httpBody = data
        request.setValue(String(byteOffset), forHTTPHeaderField: "X-Byte-Offset")
        request.setValue(Self.sha256Hex(data: data), forHTTPHeaderField: "X-Content-SHA256")
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        return try await perform(request)
    }

    private func ensureLocalFilesExist(_ item: DesktopUploadQueueItem) throws {
        for descriptor in Self.uploadFileDescriptors(for: item) {
            guard FileManager.default.fileExists(atPath: descriptor.url.path) else {
                throw DesktopUploadClientError.localFileMissing(descriptor.url.path)
            }
        }
    }

    private func jsonRequest<T: Encodable>(path: String, method: String, body: T) throws -> URLRequest {
        var request = try request(path: path, method: method)
        request.httpBody = try encoder.encode(body)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return request
    }

    private func request(
        path: String,
        method: String,
        queryItems: [URLQueryItem] = []
    ) throws -> URLRequest {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw DesktopUploadClientError.invalidBaseURL
        }
        let basePath = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let requestPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = "/" + [basePath, requestPath].filter { !$0.isEmpty }.joined(separator: "/")
        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }
        guard let url = components.url else {
            throw DesktopUploadClientError.invalidBaseURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 60
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw DesktopUploadClientError.httpStatus(503, "network_unavailable")
        }
        guard let httpResponse = response as? HTTPURLResponse else {
            throw DesktopUploadClientError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            let problem = try? decoder.decode(Problem.self, from: data)
            throw DesktopUploadClientError.httpStatus(
                httpResponse.statusCode,
                problem?.code ?? "http_error"
            )
        }
        return try decoder.decode(T.self, from: data)
    }

    public static func sha256Hex(data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}

public struct DesktopUploadFileDescriptor: Equatable, Sendable {
    public let transportRole: DesktopUploadTransportRole
    public let url: URL
    public let byteCount: Int64
    public let sha256: String?
    public let codec: String
    public let sampleRateHz: Int
    public let channelCount: Int
    public let durationSeconds: Int
}

public struct DesktopCreateMeetingPayload: Encodable, Equatable, Sendable {
    public let local_recording_id: String
    public let local_media_revision_id: String
    public let title: String?
    public let started_at: Date?
    public let ended_at: Date?
    public let duration_seconds: Int

    public init(
        local_recording_id: String,
        local_media_revision_id: String,
        title: String?,
        started_at: Date?,
        ended_at: Date?,
        duration_seconds: Int
    ) {
        self.local_recording_id = local_recording_id
        self.local_media_revision_id = local_media_revision_id
        self.title = title
        self.started_at = started_at
        self.ended_at = ended_at
        self.duration_seconds = duration_seconds
    }
}

public struct DesktopCalendarContextLinkRequest: Encodable, Equatable, Sendable {
    public let eventId: String
    public let contextReason: String

    public init(eventId: String, contextReason: String) {
        self.eventId = eventId
        self.contextReason = contextReason
    }

    private enum CodingKeys: String, CodingKey {
        case eventId = "event_id"
        case contextReason = "context_reason"
    }
}

private struct MediaRevisionSummary: Decodable {
    let media_revision_id: String?
    let local_media_revision_id: String?
}

private struct MeetingResponse: Decodable {
    let meeting_id: String
    let local_recording_id: String
    let local_media_revision_id: String?
    let title: String?
    let title_source: String?
    let media_revision: MediaRevisionSummary?
    let status: String
    let processing_status: String
}

private struct MeetingCalendarContextResponse: Decodable {
    let meeting_id: String
    let event_id: String?
    let context_state: String
    let context_confidence: String?
    let title_source: String?
}

private struct CreateUploadSessionRequest: Encodable {
    let expected_tracks: [String]
    let expected_track_sizes: [String: Int64]
    let manifest_sha256: String?
}

private struct UploadSessionResponse: Decodable {
    let session_id: String
    let meeting_id: String
    let media_revision_id: String?
    let status: String
    let expires_at: Date?
    let accepted_bytes_by_track: [String: Int64]?
    let processing_status: String?
    let desktop_truth_rule: String?
}

private struct DesktopRecordingSyncStateResponse: Decodable {
    let local_recording_id: String
    let local_media_revision_id: String
    let meeting: DesktopSyncMeetingState
    let media_revision: DesktopSyncMediaRevisionState
    let upload_session: DesktopSyncUploadSessionState
    let processing: DesktopSyncProcessingState
    let conflict: DesktopSyncConflict
}

private struct DesktopSyncMeetingState: Decodable {
    let meeting_id: String
    let status: String
}

private struct DesktopSyncMediaRevisionState: Decodable {
    let media_revision_id: String?
    let local_media_revision_id: String?
    let track_sha256_by_role: [String: String]
}

private struct DesktopSyncUploadSessionState: Decodable {
    let session_id: String?
    let status: String?
    let accepted_bytes_by_track: [String: Int64]
    let missing_ranges_by_track: [String: [MissingRange]]
    let desktop_truth_rule: String?
}

private struct DesktopSyncProcessingState: Decodable {
    let status: String
}

private struct DesktopSyncConflict: Decodable {
    let state: String
    let reason: String?
    let next_action: String?
}

private struct MissingRange: Decodable {
    let start: Int64
    let end: Int64
}

private struct MissingRangesResponse: Decodable {
    let session_id: String
    let missing_ranges_by_track: [String: [MissingRange]]
}

private struct TrackDescriptor: Encodable {
    let track_role: String
    let codec: String
    let sample_rate_hz: Int
    let channel_count: Int
    let duration_seconds: Int
    let byte_length: Int64
    let sha256: String
}

private struct FinalizeUploadRequest: Encodable {
    let manifest_sha256: String
    let tracks: [TrackDescriptor]
}

private struct FinalizeUploadResponse: Decodable {
    let meeting: MeetingResponse
    let upload_session: UploadSessionResponse
    let object_count: Int
}

private struct UploadPartResponse: Decodable {
    let byte_offset: Int64
    let byte_length: Int64
}

private struct LocalPurgeTaskListResponse: Decodable {
    let tasks: [DesktopLocalPurgeTask]
}

private struct Problem: Decodable {
    let code: String
}
