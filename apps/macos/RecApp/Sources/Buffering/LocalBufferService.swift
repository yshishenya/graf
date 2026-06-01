import CryptoKit
import Foundation
import TwoBrainRecShared

public struct LocalBufferArtifactWriterInput: Sendable {
    public let sessionId: String
    public let trackId: String?
    public let artifactType: LocalBufferArtifactType
    public let data: Data
    public let createdAt: Date

    public init(
        sessionId: String,
        trackId: String? = nil,
        artifactType: LocalBufferArtifactType,
        data: Data,
        createdAt: Date = Date()
    ) {
        self.sessionId = sessionId
        self.trackId = trackId
        self.artifactType = artifactType
        self.data = data
        self.createdAt = createdAt
    }
}

public struct LocalBufferArtifactResult: Sendable {
    public let item: LocalBufferItem
    public let riskState: LocalBufferRiskState
    public let requiresDegradeOrStop: Bool
}

public protocol LocalBufferEncryptionService: Sendable {
    func encrypt(_ plaintext: Data) throws -> Data
    func keyFingerprint() -> String
}

public final class NoOpBufferEncryptionService: LocalBufferEncryptionService {
    public init() {}

    public func encrypt(_ plaintext: Data) throws -> Data {
        plaintext
    }

    public func keyFingerprint() -> String {
        "local"
    }
}

public final class AESGCMBufferEncryptionService: LocalBufferEncryptionService {
    private let key: SymmetricKey

    public init(key: SymmetricKey = SymmetricKey(size: .bits256)) {
        self.key = key
    }

    public func encrypt(_ plaintext: Data) throws -> Data {
        let sealed = try AES.GCM.seal(plaintext, using: key)
        return sealed.combined ?? Data()
    }

    public func keyFingerprint() -> String {
        let keyData = key.withUnsafeBytes { Data($0) }
        return SHA256.hash(data: keyData).compactMap { String(format: "%02x", $0) }.joined()
    }
}

public final class LocalBufferService: LocalBufferWriting {
    public static let defaultPolicy = LocalBufferPolicy(
        maxBytesPerDevice: 2_000_000_000,
        warningFraction: 0.75,
        criticalFraction: 0.9,
        minimumDiskReserveBytes: 20 * 1024 * 1024,
        retentionDays: 7
    )

    public let policy: LocalBufferPolicy
    public private(set) var usedBytes: Int64
    public private(set) var freeDiskBytes: Int64
    public let encryptionService: LocalBufferEncryptionService

    public init(
        policy: LocalBufferPolicy = LocalBufferService.defaultPolicy,
        usedBytes: Int64 = 0,
        freeDiskBytes: Int64 = .max,
        encryptionService: LocalBufferEncryptionService = NoOpBufferEncryptionService()
    ) {
        self.policy = policy
        self.usedBytes = usedBytes
        self.freeDiskBytes = freeDiskBytes
        self.encryptionService = encryptionService
    }

    public func riskState(usedBytes: Int64, freeDiskBytes: Int64, policy: LocalBufferPolicy) -> LocalBufferRiskState {
        guard policy.maxBytesPerDevice > 0 else {
            return .critical
        }

        let clampedWarning = min(max(policy.warningFraction, 0), 1)
        let clampedCritical = min(max(policy.criticalFraction, clampedWarning), 1)
        let warningLimit = Int64(Double(policy.maxBytesPerDevice) * clampedWarning)
        let criticalLimit = Int64(Double(policy.maxBytesPerDevice) * clampedCritical)

        if freeDiskBytes <= policy.minimumDiskReserveBytes {
            return .mustDegradeOrStop
        }

        if usedBytes >= policy.maxBytesPerDevice {
            return .mustDegradeOrStop
        }

        if usedBytes >= criticalLimit {
            return .critical
        }

        if usedBytes >= warningLimit {
            return .warning
        }

        return .healthy
    }

    public func writeChunk(_ input: LocalBufferArtifactWriterInput) throws -> LocalBufferArtifactResult {
        let encryptedData = try encryptionService.encrypt(input.data)

        usedBytes += Int64(encryptedData.count)

        let risk = riskState(usedBytes: usedBytes, freeDiskBytes: freeDiskBytes, policy: policy)
        let retentionDeadline = Calendar.current.date(
            byAdding: .day,
            value: policy.retentionDays,
            to: input.createdAt
        ) ?? Date()

        let uploadState: UploadState = (risk == .critical || risk == .mustDegradeOrStop) ? .notReady : .queued

        let item = LocalBufferItem(
            id: UUID().uuidString,
            sessionId: input.sessionId,
            trackId: input.trackId,
            artifactType: input.artifactType,
            encryptedSizeBytes: Int64(encryptedData.count),
            createdAt: input.createdAt,
            retentionDeadline: retentionDeadline,
            uploadState: uploadState,
            purgeState: .retained,
            deletionReportState: .notRequested
        )

        return LocalBufferArtifactResult(
            item: item,
            riskState: risk,
            requiresDegradeOrStop: risk == .mustDegradeOrStop
        )
    }

    public func withUpdatedDiskBudget(freeDiskBytes: Int64) -> LocalBufferService {
        let service = LocalBufferService(
            policy: policy,
            usedBytes: usedBytes,
            freeDiskBytes: freeDiskBytes,
            encryptionService: encryptionService
        )
        return service
    }

    public func projectedRiskState(afterAppending bytes: Int64) -> LocalBufferRiskState {
        riskState(
            usedBytes: usedBytes + max(bytes, 0),
            freeDiskBytes: freeDiskBytes,
            policy: policy
        )
    }
}
