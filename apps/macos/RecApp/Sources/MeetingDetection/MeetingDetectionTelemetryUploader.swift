import Foundation
import TwoBrainRecShared

public struct MeetingDetectionTelemetryUploadRequest: Equatable, Sendable {
    public let path: String
    public let idempotencyKey: String
    public let body: Data
    public let document: MeetingDetectionTelemetryDocument

    public init(
        path: String,
        idempotencyKey: String,
        body: Data,
        document: MeetingDetectionTelemetryDocument
    ) {
        self.path = path
        self.idempotencyKey = idempotencyKey
        self.body = body
        self.document = document
    }
}

public struct MeetingDetectionTelemetryUploadResponse: Codable, Equatable, Sendable {
    public let batchId: String?
    public let dedupeStatus: String
    public let nextUploadAfter: Date?

    public init(batchId: String? = nil, dedupeStatus: String = "created", nextUploadAfter: Date? = nil) {
        self.batchId = batchId
        self.dedupeStatus = dedupeStatus
        self.nextUploadAfter = nextUploadAfter
    }

    private enum CodingKeys: String, CodingKey {
        case batchId = "batch_id"
        case dedupeStatus = "dedupe_status"
        case nextUploadAfter = "next_upload_after"
    }
}

public protocol MeetingDetectionTelemetryTransport: Sendable {
    func upload(_ request: MeetingDetectionTelemetryUploadRequest) async throws -> MeetingDetectionTelemetryUploadResponse
}

public struct MeetingDetectionTelemetryUploaderState: Codable, Equatable, Sendable {
    public var nextAttemptAt: Date?
    public var failureCount: Int

    public init(nextAttemptAt: Date? = nil, failureCount: Int = 0) {
        self.nextAttemptAt = nextAttemptAt
        self.failureCount = failureCount
    }
}

public struct MeetingDetectionTelemetryUploadOutcome: Equatable, Sendable {
    public let attemptedCount: Int
    public let uploadedCount: Int
    public let skippedReason: String?

    public init(attemptedCount: Int, uploadedCount: Int, skippedReason: String? = nil) {
        self.attemptedCount = attemptedCount
        self.uploadedCount = uploadedCount
        self.skippedReason = skippedReason
    }
}

public final class MeetingDetectionTelemetryUploader: @unchecked Sendable {
    public static let telemetryPath = "/api/v1/desktop/meeting-detection/telemetry"

    private let rollupStore: MeetingDetectionTelemetryRollupStore
    private let settingsStore: MeetingDetectionSettingsStore
    private let transport: MeetingDetectionTelemetryTransport
    private let stateURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private let clock: @Sendable () -> Date

    public init(
        rollupStore: MeetingDetectionTelemetryRollupStore,
        settingsStore: MeetingDetectionSettingsStore,
        transport: MeetingDetectionTelemetryTransport,
        stateURL: URL,
        encoder: JSONEncoder = MeetingDetectionCoding.encoder(),
        decoder: JSONDecoder = MeetingDetectionCoding.decoder(),
        clock: @escaping @Sendable () -> Date = Date.init
    ) {
        self.rollupStore = rollupStore
        self.settingsStore = settingsStore
        self.transport = transport
        self.stateURL = stateURL
        self.encoder = encoder
        self.decoder = decoder
        self.clock = clock
    }

    public func uploadPending() async throws -> MeetingDetectionTelemetryUploadOutcome {
        let now = clock()
        _ = try rollupStore.prune(now: now)
        let settings = try settingsStore.load()
        guard settings.uploadMode == .automaticCandidateUpload,
              settings.unknownIdentityUploadAllowed
        else {
            return MeetingDetectionTelemetryUploadOutcome(
                attemptedCount: 0,
                uploadedCount: 0,
                skippedReason: "upload_disabled"
            )
        }
        let state = try loadState()
        if let nextAttemptAt = state.nextAttemptAt, nextAttemptAt > now {
            return MeetingDetectionTelemetryUploadOutcome(
                attemptedCount: 0,
                uploadedCount: 0,
                skippedReason: "backoff"
            )
        }

        var attempted = 0
        var uploaded = 0
        for url in try rollupStore.pendingDocumentURLs() {
            let document = try decoder.decode(MeetingDetectionTelemetryDocument.self, from: Data(contentsOf: url))
            guard let uploadable = MeetingDetectionTelemetryRollupStore.uploadableCopy(of: document) else {
                continue
            }
            attempted += 1
            do {
                let response = try await transport.upload(
                    MeetingDetectionTelemetryUploadRequest(
                        path: Self.telemetryPath,
                        idempotencyKey: Self.idempotencyKey(for: uploadable),
                        body: try encoder.encode(uploadable),
                        document: uploadable
                    )
                )
                try rollupStore.removeDocument(at: url)
                uploaded += 1
                try saveState(
                    MeetingDetectionTelemetryUploaderState(
                        nextAttemptAt: response.nextUploadAfter,
                        failureCount: 0
                    )
                )
                if let nextUploadAfter = response.nextUploadAfter, nextUploadAfter > now {
                    break
                }
            } catch {
                let failures = state.failureCount + 1
                try saveState(
                    MeetingDetectionTelemetryUploaderState(
                        nextAttemptAt: now.addingTimeInterval(Self.backoffSeconds(failureCount: failures)),
                        failureCount: failures
                    )
                )
                throw error
            }
        }
        return MeetingDetectionTelemetryUploadOutcome(attemptedCount: attempted, uploadedCount: uploaded)
    }

    public func loadState() throws -> MeetingDetectionTelemetryUploaderState {
        guard FileManager.default.fileExists(atPath: stateURL.path) else {
            return MeetingDetectionTelemetryUploaderState()
        }
        return try decoder.decode(
            MeetingDetectionTelemetryUploaderState.self,
            from: Data(contentsOf: stateURL)
        )
    }

    public func saveState(_ state: MeetingDetectionTelemetryUploaderState) throws {
        try FileManager.default.createDirectory(
            at: stateURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try encoder.encode(state).write(to: stateURL, options: [.atomic])
    }

    public static func idempotencyKey(for document: MeetingDetectionTelemetryDocument) -> String {
        let startedAt = Int(document.rollupWindow.startedAt.timeIntervalSince1970)
        return "meeting-detection:\(document.registryVersion):\(startedAt)"
    }

    public static func backoffSeconds(failureCount: Int) -> TimeInterval {
        min(TimeInterval(max(1, failureCount)) * 15 * 60, 6 * 60 * 60)
    }
}
