import CryptoKit
import Foundation
import TwoBrainRecShared

public protocol DesktopUploadClientProtocol: Sendable {
    func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult
}

public struct DesktopUploadResult: Sendable {
    public let state: UploadItemState
    public let serverTruth: ServerTruthFingerprint

    public init(state: UploadItemState, serverTruth: ServerTruthFingerprint) {
        self.state = state
        self.serverTruth = serverTruth
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
        case .httpStatus(let status, _):
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
    public static let defaultPartSizeBytes = 5 * 1024 * 1024
    public static let uploadBearerTokenEnvironmentKey = "TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN"

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

    public static func configuredFromEnvironment() -> DesktopUploadClient? {
        let environment = ProcessInfo.processInfo.environment
        let rawURL = environment["TWO_BRAIN_REC_UPLOAD_BASE_URL"] ??
            UserDefaults.standard.string(forKey: "TWO_BRAIN_REC_UPLOAD_BASE_URL")
        guard let rawURL, let url = URL(string: rawURL), url.scheme?.hasPrefix("http") == true else {
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

    public func upload(_ item: DesktopUploadQueueItem) async throws -> DesktopUploadResult {
        try ensureLocalFilesExist(item)

        let meeting = if let meetingId = item.meetingId {
            MeetingResponse(
                meeting_id: meetingId,
                local_recording_id: item.directoryId,
                status: "uploading",
                processing_status: "not_submitted"
            )
        } else {
            try await createMeeting(item)
        }

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
        let serverTruth = ServerTruthFingerprint(
            meetingId: finalSession.meeting_id,
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

    public static func backendRole(for localRole: AudioTrackRole) -> DesktopUploadTransportRole? {
        DesktopUploadTransportRole.role(forLocalTrackRole: localRole)
    }

    public static func idempotencyKey(item: DesktopUploadQueueItem, scope: String) -> String {
        "desktop-upload:\(scope):\(item.directoryId):\(item.sessionId)"
    }

    public static func partNumber(forByteOffset byteOffset: Int64, partSizeBytes: Int) -> Int {
        max(0, Int(max(0, byteOffset) / Int64(max(1, partSizeBytes))))
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

    private func createMeeting(_ item: DesktopUploadQueueItem) async throws -> MeetingResponse {
        var request = try jsonRequest(
            path: "/api/v1/meetings",
            method: "POST",
            body: CreateMeetingRequest(
                local_recording_id: item.directoryId,
                title: nil,
                started_at: nil,
                ended_at: nil,
                duration_seconds: item.artifactProfile.durationSeconds
            )
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

    private func request(path: String, method: String) throws -> URLRequest {
        guard var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw DesktopUploadClientError.invalidBaseURL
        }
        let basePath = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let requestPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        components.path = "/" + [basePath, requestPath].filter { !$0.isEmpty }.joined(separator: "/")
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

private struct CreateMeetingRequest: Encodable {
    let local_recording_id: String
    let title: String?
    let started_at: Date?
    let ended_at: Date?
    let duration_seconds: Int
}

private struct MeetingResponse: Decodable {
    let meeting_id: String
    let local_recording_id: String
    let status: String
    let processing_status: String
}

private struct CreateUploadSessionRequest: Encodable {
    let expected_tracks: [String]
    let expected_track_sizes: [String: Int64]
    let manifest_sha256: String?
}

private struct UploadSessionResponse: Decodable {
    let session_id: String
    let meeting_id: String
    let status: String
    let expires_at: Date?
    let accepted_bytes_by_track: [String: Int64]?
    let processing_status: String?
    let desktop_truth_rule: String?
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
    let upload_session: UploadSessionResponse
    let object_count: Int
}

private struct UploadPartResponse: Decodable {
    let byte_offset: Int64
    let byte_length: Int64
}

private struct Problem: Decodable {
    let code: String
}
