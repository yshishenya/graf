import Foundation
import TwoBrainRecShared

public struct LocalCacheEvictionFootprint: Equatable, Sendable {
    public let usedBytes: Int64
    public let freeDiskBytes: Int64?
    public let diskCapacityBytes: Int64?

    public init(usedBytes: Int64, freeDiskBytes: Int64?, diskCapacityBytes: Int64?) {
        self.usedBytes = max(0, usedBytes)
        self.freeDiskBytes = freeDiskBytes
        self.diskCapacityBytes = diskCapacityBytes
    }
}

public struct LocalCacheEvictionCandidate: Equatable, Sendable {
    public let itemID: String
    public let localRecordingFingerprint: String
    public let verifiedAt: Date?
    public let finalizedAt: Date?
    /// Only the transcription WAV is removed, so only its bytes count as freed.
    public let bytes: Int64

    public init(
        itemID: String,
        localRecordingFingerprint: String,
        verifiedAt: Date?,
        finalizedAt: Date?,
        bytes: Int64
    ) {
        self.itemID = itemID
        self.localRecordingFingerprint = localRecordingFingerprint
        self.verifiedAt = verifiedAt
        self.finalizedAt = finalizedAt
        self.bytes = max(0, bytes)
    }
}

public enum LocalCacheEvictionTrigger: String, Equatable, Sendable {
    case launch
    case uploadFinalized = "upload_finalized"
    case recordingStopped = "recording_stopped"
    case footprintRefresh = "footprint_refresh"
}

public enum LocalCacheEvictionRunResult: Equatable, Sendable {
    case completed(evaluated: Int, deleted: Int, freedBytes: Int64)
    case belowThreshold
    case debounced
    case disabled
    case operatorDisabled
    case failed(code: String)
}

public struct LocalCacheEvictionConfiguration: Equatable, Sendable {
    public var debounce: TimeInterval
    public var maximumCandidates: Int
    public var maximumDeletionsPerRun: Int

    public init(
        debounce: TimeInterval = 60,
        maximumCandidates: Int = 20,
        maximumDeletionsPerRun: Int = 50
    ) {
        self.debounce = max(0, debounce)
        self.maximumCandidates = max(0, maximumCandidates)
        self.maximumDeletionsPerRun = max(0, maximumDeletionsPerRun)
    }
}

/// Single-flight, bounded, off-main WAV eviction. Every deletion goes through
/// `LocalCacheCleanupService`, so the proof and the receipt are revalidated at
/// the moment of unlink.
public actor LocalCacheEvictionScheduler {
    public typealias FootprintProvider = @Sendable () async -> LocalCacheEvictionFootprint?
    public typealias SettingsProvider = @Sendable () -> LocalCacheEvictionSettingSnapshot
    public typealias CandidateProvider = @Sendable () async -> [LocalCacheEvictionCandidate]
    public typealias Evictor = @Sendable (LocalCacheEvictionCandidate) async -> LocalCacheCleanupOutcome
    public typealias Clock = @Sendable () -> Date

    private let policy: LocalCacheEvictionPolicy
    private let configuration: LocalCacheEvictionConfiguration
    private let footprintProvider: FootprintProvider
    private let settingsProvider: SettingsProvider
    private let candidateProvider: CandidateProvider
    private let evictor: Evictor
    private let clock: Clock

    private var inFlight: Task<LocalCacheEvictionRunResult, Never>?
    private var lastRunAt: Date?
    private var lastFreedBytes: Int64?

    public init(
        policy: LocalCacheEvictionPolicy = .productBaseline,
        configuration: LocalCacheEvictionConfiguration = LocalCacheEvictionConfiguration(),
        footprintProvider: @escaping FootprintProvider,
        settingsProvider: @escaping SettingsProvider,
        candidateProvider: @escaping CandidateProvider,
        evictor: @escaping Evictor,
        clock: @escaping Clock = Date.init
    ) {
        self.policy = policy
        self.configuration = configuration
        self.footprintProvider = footprintProvider
        self.settingsProvider = settingsProvider
        self.candidateProvider = candidateProvider
        self.evictor = evictor
        self.clock = clock
    }

    /// Cheap, non-blocking trigger for lifecycle events and UI actions.
    public nonisolated func notify(_ trigger: LocalCacheEvictionTrigger) {
        Task { _ = await self.run(trigger) }
    }

    public func run(_ trigger: LocalCacheEvictionTrigger) async -> LocalCacheEvictionRunResult {
        if let inFlight {
            return await inFlight.value
        }
        let task = Task { await self.perform(trigger) }
        inFlight = task
        let result = await task.value
        inFlight = nil
        return result
    }

    public func status() async -> LocalCacheStatusPresentation? {
        let settings = settingsProvider()
        guard let footprint = await measuredFootprint() else { return nil }
        return LocalCacheStatusPresentation(
            usedBytes: footprint.usedBytes,
            budgetBytes: policy.budgetBytes,
            freeDiskBytes: footprint.freeDiskBytes,
            diskCapacityBytes: footprint.diskCapacityBytes,
            threshold: policy.threshold(
                usedBytes: footprint.usedBytes,
                freeDiskBytes: footprint.freeDiskBytes,
                diskCapacityBytes: footprint.diskCapacityBytes
            ),
            settings: settings,
            lastFreedBytes: lastFreedBytes
        )
    }

    private func perform(_ trigger: LocalCacheEvictionTrigger) async -> LocalCacheEvictionRunResult {
        let settings = settingsProvider()
        guard !settings.operatorDisabled else { return .operatorDisabled }
        guard settings.userEnabled else { return .disabled }

        let now = clock()
        if trigger != .launch,
           let lastRunAt,
           now.timeIntervalSince(lastRunAt) < configuration.debounce {
            return .debounced
        }

        guard let footprint = await measuredFootprint() else {
            return .failed(code: "footprint_unavailable")
        }
        if let stopped = settingsStopResult(settings: settingsProvider(), deleted: 0,
                                            evaluated: 0, freedBytes: 0) {
            return stopped
        }
        // Unknown free disk cannot prove the safe reserve; fail closed even when
        // the used-bytes threshold alone would suggest eviction.
        guard let freeDiskBytes = footprint.freeDiskBytes else {
            return .failed(code: "free_disk_unknown")
        }
        lastRunAt = now

        let warningBytes = policy.warningBytes
        let reserveBytes = policy.resolvedReserveBytes(
            diskCapacityBytes: footprint.diskCapacityBytes
        )
        var usedBytes = footprint.usedBytes
        var freeDisk = freeDiskBytes
        guard usedBytes >= warningBytes || freeDisk <= reserveBytes else {
            return .belowThreshold
        }

        let candidates = Array(
            (await candidateProvider())
                .sorted(by: Self.oldestFirst)
                .prefix(configuration.maximumCandidates)
        )
        if let stopped = settingsStopResult(settings: settingsProvider(), deleted: 0,
                                            evaluated: 0, freedBytes: 0) {
            return stopped
        }
        var evaluated = 0
        var deleted = 0
        var freedBytes: Int64 = 0

        for candidate in candidates {
            if usedBytes < warningBytes && freeDisk > reserveBytes { break }
            if deleted >= configuration.maximumDeletionsPerRun { break }
            // The user or the operator may disable eviction while candidate
            // discovery or an earlier cleanup is awaiting I/O.
            if let stopped = settingsStopResult(
                settings: settingsProvider(),
                deleted: deleted,
                evaluated: evaluated,
                freedBytes: freedBytes
            ) {
                return stopped
            }
            evaluated += 1
            switch await evictor(candidate) {
            case .completed(let bytes):
                deleted += 1
                freedBytes += bytes
                usedBytes = max(0, usedBytes - bytes)
                freeDisk += bytes
            case .scopeChanged:
                lastFreedBytes = freedBytes
                return .failed(code: "scope_changed")
            case .noop, .unexpectedMissing, .notEligible, .localFileChanged, .failed:
                continue
            }
        }

        lastFreedBytes = freedBytes
        return .completed(evaluated: evaluated, deleted: deleted, freedBytes: freedBytes)
    }

    private func settingsStopResult(
        settings: LocalCacheEvictionSettingSnapshot,
        deleted: Int,
        evaluated: Int,
        freedBytes: Int64
    ) -> LocalCacheEvictionRunResult? {
        let stopped: LocalCacheEvictionRunResult?
        if settings.operatorDisabled {
            stopped = .operatorDisabled
        } else if !settings.userEnabled {
            stopped = .disabled
        } else {
            stopped = nil
        }
        guard let stopped else { return nil }
        lastFreedBytes = freedBytes
        if deleted > 0 {
            return .completed(evaluated: evaluated, deleted: deleted, freedBytes: freedBytes)
        }
        return stopped
    }

    private func measuredFootprint() async -> LocalCacheEvictionFootprint? {
        let provider = footprintProvider
        return await Task.detached(priority: .utility) {
            await provider()
        }.value
    }

    private static func oldestFirst(
        _ lhs: LocalCacheEvictionCandidate,
        _ rhs: LocalCacheEvictionCandidate
    ) -> Bool {
        let lhsDate = lhs.finalizedAt ?? lhs.verifiedAt ?? .distantFuture
        let rhsDate = rhs.finalizedAt ?? rhs.verifiedAt ?? .distantFuture
        if lhsDate != rhsDate { return lhsDate < rhsDate }
        return lhs.localRecordingFingerprint < rhs.localRecordingFingerprint
    }
}

/// Builds the eviction candidate list from the raw queue and fresh proofs. It
/// never hashes or deletes; the cleanup service revalidates each candidate.
public struct LocalCacheEvictionCandidateLoader: Sendable {
    public typealias FootprintMeasure = @Sendable (URL) throws -> Int64

    private let queueURL: URL
    private let recordingsRootURL: URL
    private let receiptDirectoryURL: URL?
    private let client: (any DesktopServerProofFetching)?
    private let scopeProvider: @Sendable () -> RecordingDeletionScope?
    private let maximumCandidates: Int
    private let maximumScan: Int
    private let proofTimeout: TimeInterval
    private let totalTimeout: TimeInterval
    private let policy: LocalCacheEligibilityPolicy
    private let measureFootprint: FootprintMeasure

    public init(
        queueURL: URL,
        recordingsRootURL: URL,
        receiptDirectoryURL: URL? = nil,
        client: (any DesktopServerProofFetching)?,
        scopeProvider: @escaping @Sendable () -> RecordingDeletionScope?,
        maximumCandidates: Int = 20,
        maximumScan: Int = 200,
        proofTimeout: TimeInterval = 5,
        totalTimeout: TimeInterval = 120,
        policy: LocalCacheEligibilityPolicy = .default,
        measureFootprint: @escaping FootprintMeasure = {
            try LocalRecordingFootprintMeasurer.measure(at: $0).bytes
        }
    ) {
        self.queueURL = queueURL
        self.recordingsRootURL = recordingsRootURL
        self.receiptDirectoryURL = receiptDirectoryURL
        self.client = client
        self.scopeProvider = scopeProvider
        self.maximumCandidates = max(0, maximumCandidates)
        self.maximumScan = max(0, maximumScan)
        self.proofTimeout = max(0.01, proofTimeout)
        self.totalTimeout = max(0.01, totalTimeout)
        self.policy = policy
        self.measureFootprint = measureFootprint
    }

    public func load() async -> [LocalCacheEvictionCandidate] {
        guard maximumCandidates > 0, let client else { return [] }
        let snapshot: LocalCacheRawQueueSnapshot
        do {
            snapshot = try LocalCacheRawQueueSnapshot.read(from: queueURL)
        } catch {
            return []
        }
        let scope = scopeProvider()
        let deadline = Date().addingTimeInterval(totalTimeout)
        let document = DesktopUploadQueueDocument(
            updatedAt: snapshot.updatedAt ?? Date(),
            items: [],
            deletionOperations: snapshot.deletionOperations
        )
        let receiptDirectory = receiptDirectoryURL
            ?? queueURL.deletingLastPathComponent()
                .appendingPathComponent("LocalCacheEviction/receipts", isDirectory: true)
        let rawCandidates = snapshot.items
            .compactMap { $0.decodeItem() }
            .filter { item in
                item.ownerScope == scope &&
                    LocalCacheCleanupCandidatePolicy.cleanupBytes(for: item) != nil
            }
        // Cheap, read-only prefilter before the bounded proof scan. Cleaned
        // items keep .uploaded with a missing WAV, so they must not occupy the
        // oldest-first scan window forever.
        let root = recordingsRootURL
        let candidatesToScan = await Task.detached(priority: .utility) {
            rawCandidates.filter { item in
                guard LocalCacheArtifactProbe.isInside(
                    item.transcriptionAudioPath,
                    root: root
                ),
                    case .regular = LocalCacheFileIdentity.state(
                        atPath: item.transcriptionAudioPath
                    ) else {
                    return false
                }
                return !LocalCacheCleanupReceiptLookup.hasCompletedOrNoopReceipt(
                    item: item,
                    receiptDirectory: receiptDirectory
                )
            }
        }.value
        let preCandidates = candidatesToScan
            .sorted {
                let lhs = $0.serverTruth.finalizedAt ?? $0.createdAt
                let rhs = $1.serverTruth.finalizedAt ?? $1.createdAt
                if lhs != rhs { return lhs < rhs }
                return $0.id < $1.id
            }
            .prefix(maximumScan)

        let work = Array(preCandidates)
        guard !work.isEmpty else { return [] }
        let concurrency = min(2, work.count)
        var nextIndex = concurrency
        var collected: [Int: LocalCacheEvictionCandidate] = [:]

        await withTaskGroup(of: (Int, LocalCacheEvictionCandidate?).self) { group in
            for offset in 0..<concurrency {
                group.addTask {
                    (offset, await evaluate(
                        work[offset],
                        document: document,
                        scope: scope,
                        client: client
                    ))
                }
            }
            while let (offset, candidate) = await group.next() {
                if let candidate { collected[offset] = candidate }
                if Date() < deadline, nextIndex < work.count {
                    let next = nextIndex
                    nextIndex += 1
                    group.addTask {
                        (next, await evaluate(
                            work[next],
                            document: document,
                            scope: scope,
                            client: client
                        ))
                    }
                }
            }
        }

        let candidates = (0..<work.count).compactMap { collected[$0] }
        return candidates.sorted {
            let lhs = $0.finalizedAt ?? $0.verifiedAt ?? .distantFuture
            let rhs = $1.finalizedAt ?? $1.verifiedAt ?? .distantFuture
            if lhs != rhs { return lhs < rhs }
            return $0.localRecordingFingerprint < $1.localRecordingFingerprint
        }
        .prefix(maximumCandidates)
        .map { $0 }
    }

    private func evaluate(
        _ item: DesktopUploadQueueItem,
        document: DesktopUploadQueueDocument,
        scope: RecordingDeletionScope?,
        client: any DesktopServerProofFetching
    ) async -> LocalCacheEvictionCandidate? {
        let reconciliation: DesktopUploadReconciliation?
        do {
            reconciliation = try await LocalCacheAsyncTimeout.run(seconds: proofTimeout) {
                try await client.fetchServerProof(for: item)
            }
        } catch {
            return nil
        }
        var facts = LocalCacheArtifactProbe.inspect(
            item: item,
            recordingsRootURL: recordingsRootURL,
            computeHashes: false
        )
        guard facts.transcriptionAudioPresent else { return nil }
        facts.packageBytes = await Task.detached(priority: .utility) {
            try? measureFootprint(URL(fileURLWithPath: item.directoryPath))
        }.value
        var decision = LocalCacheEligibility.evaluate(
            item: item,
            document: document,
            scope: scope,
            proof: reconciliation?.proof,
            proofFetchedAt: reconciliation?.fetchedAt,
            localFacts: facts,
            policy: policy,
            now: Date()
        )
        if decision.verdict == .potentiallyEligible {
            // Hash only candidates that already pass every other gate. A
            // corrupt WAV must not enter the eviction list.
            let root = recordingsRootURL
            let hashedFacts: LocalArtifactFacts
            do {
                hashedFacts = try await LocalCacheAsyncTimeout.run(seconds: 15) {
                    await Task.detached(priority: .utility) {
                        LocalCacheArtifactProbe.inspect(
                            item: item,
                            recordingsRootURL: root,
                            computeHashes: true
                        )
                    }.value
                }
            } catch {
                return nil
            }
            var finalFacts = hashedFacts
            finalFacts.packageBytes = facts.packageBytes
            facts = finalFacts
            decision = LocalCacheEligibility.evaluate(
                item: item,
                document: document,
                scope: scope,
                proof: reconciliation?.proof,
                proofFetchedAt: reconciliation?.fetchedAt,
                localFacts: finalFacts,
                policy: policy,
                now: Date()
            )
        }
        guard decision.verdict == .potentiallyEligible,
              let proof = decision.proof,
              let transcriptionBytes = facts.transcriptionBytes else {
            return nil
        }
        return LocalCacheEvictionCandidate(
            itemID: item.id,
            localRecordingFingerprint: LocalCacheFingerprint.recording(item.directoryId),
            verifiedAt: proof.playback?.verifiedAt?.date,
            finalizedAt: proof.finalizedUpload?.finalizedAt?.date,
            bytes: transcriptionBytes
        )
    }
}
