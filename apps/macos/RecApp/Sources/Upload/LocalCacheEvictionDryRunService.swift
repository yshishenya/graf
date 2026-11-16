import Foundation
import TwoBrainRecShared

/// Bounds for a diagnostics-only pass. The dry run must never starve lifecycle
/// or deletion traffic and must finish in a bounded window.
public struct LocalCacheEvictionDryRunConfiguration: Equatable, Sendable {
    public var maximumItems: Int
    public var maximumConcurrency: Int
    public var requestTimeout: TimeInterval
    public var totalTimeout: TimeInterval
    public var footprintTimeout: TimeInterval
    public var maximumProofAge: TimeInterval
    public var gracePeriod: TimeInterval
    public var minimumRemainingRetention: TimeInterval

    public init(
        maximumItems: Int = 200,
        maximumConcurrency: Int = 2,
        requestTimeout: TimeInterval = 5,
        totalTimeout: TimeInterval = 120,
        footprintTimeout: TimeInterval = 10,
        maximumProofAge: TimeInterval = 120,
        gracePeriod: TimeInterval = 7 * 24 * 60 * 60,
        minimumRemainingRetention: TimeInterval = 30 * 24 * 60 * 60
    ) {
        self.maximumItems = max(0, maximumItems)
        self.maximumConcurrency = max(1, maximumConcurrency)
        self.requestTimeout = max(0.01, requestTimeout)
        self.totalTimeout = max(0.01, totalTimeout)
        self.footprintTimeout = max(0.01, footprintTimeout)
        self.maximumProofAge = max(1, maximumProofAge)
        self.gracePeriod = max(0, gracePeriod)
        self.minimumRemainingRetention = max(0, minimumRemainingRetention)
    }

    var eligibilityPolicy: LocalCacheEligibilityPolicy {
        LocalCacheEligibilityPolicy(
            maximumProofAge: maximumProofAge,
            gracePeriod: gracePeriod,
            minimumRemainingRetention: minimumRemainingRetention
        )
    }
}

public enum LocalCacheEvictionDryRunOutcome: Equatable, Sendable {
    case notRequested
    case completed(reportURL: URL, latestURL: URL, inspected: Int, eligible: Int, eligibleBytes: Int64)
    case abortedScopeChanged
    case reportDirectoryRejected
    case failed(code: String)

    /// No path, title or transcript may appear in a diagnostic log line.
    public var logDetail: String {
        switch self {
        case .notRequested:
            return "outcome=not_requested"
        case .completed(_, _, let inspected, let eligible, let eligibleBytes):
            return "outcome=completed inspected=\(inspected) eligible=\(eligible) eligible_bytes=\(eligibleBytes)"
        case .abortedScopeChanged:
            return "outcome=aborted_scope_changed"
        case .reportDirectoryRejected:
            return "outcome=report_directory_rejected"
        case .failed(let code):
            return "outcome=failed code=\(code)"
        }
    }
}

/// A read-only dry run over the raw upload queue. It deliberately avoids
/// `loadItems()`/`loadDocumentOnQueue()`: those paths migrate, normalize,
/// recover incidents, and can quarantine a malformed queue.
public struct LocalCacheEvictionDryRunService: Sendable {
    public typealias FootprintMeasure = @Sendable (URL) throws -> Int64

    private let queueURL: URL
    private let recordingsRootURL: URL
    private let reportDirectoryURL: URL?
    private let client: (any DesktopServerProofFetching)?
    private let configuration: LocalCacheEvictionDryRunConfiguration
    private let scope: RecordingDeletionScope?
    private let scopeResolver: (@Sendable () async -> RecordingDeletionScope?)?
    private let runFence: (@Sendable () -> Bool)?
    private let clock: @Sendable () -> Date
    private let measureFootprint: FootprintMeasure

    public init(
        queueURL: URL,
        recordingsRootURL: URL,
        reportDirectoryURL: URL? = nil,
        client: (any DesktopServerProofFetching)? = nil,
        configuration: LocalCacheEvictionDryRunConfiguration = LocalCacheEvictionDryRunConfiguration(),
        scope: RecordingDeletionScope? = nil,
        scopeResolver: (@Sendable () async -> RecordingDeletionScope?)? = nil,
        runFence: (@Sendable () -> Bool)? = nil,
        clock: @escaping @Sendable () -> Date = Date.init,
        measureFootprint: @escaping FootprintMeasure = {
            try LocalRecordingFootprintMeasurer.measure(at: $0).bytes
        }
    ) {
        self.queueURL = queueURL
        self.recordingsRootURL = recordingsRootURL
        self.reportDirectoryURL = reportDirectoryURL
        self.client = client
        self.configuration = configuration
        self.scope = scope
        self.scopeResolver = scopeResolver
        self.runFence = runFence
        self.clock = clock
        self.measureFootprint = measureFootprint
    }

    public func run() async -> LocalCacheEvictionDryRunOutcome {
        let startedAt = clock()
        let deadline = startedAt.addingTimeInterval(configuration.totalTimeout)

        let raw: LocalCacheRawQueueSnapshot
        do {
            raw = try LocalCacheRawQueueSnapshot.read(from: queueURL)
        } catch LocalCacheQueueSnapshotError.deletionOperationsUndecodable {
            return .failed(code: "deletion_operations_undecodable")
        } catch {
            return .failed(code: "queue_unreadable")
        }

        let reportDirectory = reportDirectoryURL
            ?? queueURL.deletingLastPathComponent()
                .appendingPathComponent("LocalCacheEviction", isDirectory: true)
        guard !LocalCacheArtifactProbe.isInside(
            reportDirectory.path,
            root: recordingsRootURL
        ) else {
            return .reportDirectoryRejected
        }

        var resolvedScope = scope
        if resolvedScope == nil, let scopeResolver {
            resolvedScope = await scopeResolver()
        }
        if resolvedScope == nil {
            resolvedScope = raw.persistedScope(matching: client?.recordingSessionFingerprint)
        }

        let document = DesktopUploadQueueDocument(
            updatedAt: raw.updatedAt ?? startedAt,
            items: [],
            deletionOperations: raw.deletionOperations
        )
        let work = Array(raw.items.prefix(configuration.maximumItems))
        let results = await process(
            work: work,
            document: document,
            scope: resolvedScope,
            deadline: deadline
        )
        guard let results else { return .abortedScopeChanged }
        if let runFence, !runFence() { return .abortedScopeChanged }

        let report = LocalCacheEvictionReport(
            generatedAt: clock(),
            scopeFingerprint: LocalCacheFingerprint.scope(resolvedScope),
            policy: configuration.eligibilityPolicy,
            items: results,
            truncated: raw.items.count > work.count,
            availableItemCount: raw.items.count
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        let data: Data
        do {
            data = try encoder.encode(report)
        } catch {
            return .failed(code: "report_encode_failed")
        }

        let stamp = Self.timestamp(from: report.generatedAt)
        let reportURL = reportDirectory.appendingPathComponent("dry-run-\(stamp).json")
        let latestURL = reportDirectory.appendingPathComponent("latest.json")
        do {
            try LocalCustodyFileProtection.write(data, to: reportURL)
            try LocalCustodyFileProtection.write(data, to: latestURL)
        } catch {
            return .failed(code: "report_write_failed")
        }

        return .completed(
            reportURL: reportURL,
            latestURL: latestURL,
            inspected: report.totals.inspected,
            eligible: report.totals.eligible,
            eligibleBytes: report.totals.eligibleBytes
        )
    }

    // MARK: - Bounded processing

    private enum ItemOutcome: Sendable {
        case completed(LocalCacheEvictionReport.Item)
        case aborted
    }

    /// Returns `nil` when the account/workspace fence changed mid-run. A partial
    /// report would be misleading, so no file is written in that case.
    private func process(
        work: [LocalCacheRawQueueItem],
        document: DesktopUploadQueueDocument,
        scope: RecordingDeletionScope?,
        deadline: Date
    ) async -> [LocalCacheEvictionReport.Item]? {
        guard !work.isEmpty else { return [] }
        let concurrency = min(configuration.maximumConcurrency, work.count)
        var collected: [Int: LocalCacheEvictionReport.Item] = [:]
        var nextIndex = concurrency
        var aborted = false

        await withTaskGroup(of: (Int, ItemOutcome).self) { group in
            for index in 0..<concurrency {
                group.addTask {
                    (index, await process(index: index, raw: work[index], document: document,
                                          scope: scope, deadline: deadline))
                }
            }
            while let (index, outcome) = await group.next() {
                switch outcome {
                case .completed(let item):
                    collected[index] = item
                case .aborted:
                    aborted = true
                    group.cancelAll()
                }
                if aborted { continue }
                if nextIndex < work.count {
                    let index = nextIndex
                    nextIndex += 1
                    group.addTask {
                        (index, await process(index: index, raw: work[index], document: document,
                                              scope: scope, deadline: deadline))
                    }
                }
            }
        }

        guard !aborted else { return nil }
        return (0..<work.count).compactMap { collected[$0] }
    }

    private func process(
        index: Int,
        raw: LocalCacheRawQueueItem,
        document: DesktopUploadQueueDocument,
        scope: RecordingDeletionScope?,
        deadline: Date
    ) async -> ItemOutcome {
        if let runFence, !runFence() { return .aborted }

        guard let item = raw.decodeItem() else {
            let identity = raw.rawDirectoryId ?? raw.rawId ?? "unidentified-\(index)"
            let reportItem = LocalCacheEvictionReport.Item(
                localRecordingFingerprint: LocalCacheFingerprint.recording(identity),
                state: "undecodable",
                bytes: 0,
                verdict: .keep,
                primaryReason: LocalCacheEligibilityReason.queueItemUndecodable.rawValue,
                allReasons: [LocalCacheEligibilityReason.queueItemUndecodable.rawValue],
                server: nil
            )
            return .completed(reportItem)
        }

        let localRecordingFingerprint = LocalCacheFingerprint.recording(item.directoryId)
        if clock() >= deadline {
            // The bounded window is exhausted. Report a fail-closed verdict
            // without starting another measurement or lifecycle request.
            return .completed(LocalCacheEvictionReport.Item(
                localRecordingFingerprint: localRecordingFingerprint,
                state: item.state.rawValue,
                bytes: 0,
                verdict: .keep,
                primaryReason: LocalCacheEligibilityReason.dependencyUnavailable.rawValue,
                allReasons: [LocalCacheEligibilityReason.dependencyUnavailable.rawValue],
                server: nil
            ))
        }
        let measurement = await measure(item: item, computeHashes: false)
        if let runFence, !runFence() { return .aborted }

        let proofResult = await fetchProof(for: item, deadline: deadline)
        if let runFence, !runFence() { return .aborted }

        var decision = LocalCacheEligibility.evaluate(
            item: item,
            document: document,
            scope: scope,
            proof: proofResult.reconciliation?.proof,
            proofFetchedAt: proofResult.reconciliation?.fetchedAt,
            proofFetchFailed: proofResult.failed,
            localFacts: measurement.facts,
            policy: configuration.eligibilityPolicy,
            now: clock()
        )
        if decision.verdict == .potentiallyEligible {
            // Only items that pass every other gate pay the hashing cost. A
            // hash-corrupt WAV must never be reported as potentially eligible.
            guard clock() < deadline else {
                return .completed(LocalCacheEvictionReport.Item(
                    localRecordingFingerprint: localRecordingFingerprint,
                    state: item.state.rawValue,
                    bytes: 0,
                    verdict: .keep,
                    primaryReason: LocalCacheEligibilityReason.dependencyUnavailable.rawValue,
                    allReasons: [LocalCacheEligibilityReason.dependencyUnavailable.rawValue],
                    server: nil
                ))
            }
            let hashMeasurement = await measure(item: item, computeHashes: true)
            decision = LocalCacheEligibility.evaluate(
                item: item,
                document: document,
                scope: scope,
                proof: proofResult.reconciliation?.proof,
                proofFetchedAt: proofResult.reconciliation?.fetchedAt,
                proofFetchFailed: proofResult.failed,
                localFacts: hashMeasurement.facts,
                policy: configuration.eligibilityPolicy,
                now: clock()
            )
        }
        return .completed(LocalCacheEvictionReport.Item.make(
            item: item,
            decision: decision,
            localRecordingFingerprint: localRecordingFingerprint
        ))
    }

    // MARK: - Local measurement

    private struct LocalMeasurement: Sendable {
        let facts: LocalArtifactFacts
        let bytes: Int64?
    }

    private func measure(
        item: DesktopUploadQueueItem,
        computeHashes: Bool
    ) async -> LocalMeasurement {
        let root = recordingsRootURL
        let measureFootprint = measureFootprint
        let directoryURL = URL(fileURLWithPath: item.directoryPath)
        do {
            return try await LocalCacheAsyncTimeout.run(seconds: configuration.footprintTimeout) {
                await Task.detached(priority: .utility) {
                    var facts = LocalCacheArtifactProbe.inspect(
                        item: item,
                        recordingsRootURL: root,
                        computeHashes: computeHashes
                    )
                    let bytes = (try? measureFootprint(directoryURL))
                    facts.packageBytes = bytes
                    return LocalMeasurement(facts: facts, bytes: bytes)
                }.value
            }
        } catch {
            return LocalMeasurement(facts: LocalArtifactFacts(error: .unreadable), bytes: nil)
        }
    }

    // MARK: - Bounded proof fetch

    private struct ProofFetchResult: Sendable {
        let reconciliation: DesktopUploadReconciliation?
        let failed: Bool
    }

    private func fetchProof(
        for item: DesktopUploadQueueItem,
        deadline: Date
    ) async -> ProofFetchResult {
        guard let client, clock() < deadline else {
            return ProofFetchResult(reconciliation: nil, failed: true)
        }
        do {
            let reconciliation = try await LocalCacheAsyncTimeout.run(
                seconds: configuration.requestTimeout
            ) {
                try await client.fetchServerProof(for: item)
            }
            return ProofFetchResult(reconciliation: reconciliation, failed: false)
        } catch {
            return ProofFetchResult(reconciliation: nil, failed: true)
        }
    }

    private static func timestamp(from date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyyMMdd-HHmmss-SSS"
        return formatter.string(from: date)
    }
}

// MARK: - Diagnostics entry point

public enum LocalCacheEvictionDryRunDiagnostics {
    public static let environmentKey = "GRAF_RUN_CACHE_EVICTION_DRY_RUN"

    public static func isRequested(in environment: [String: String]) -> Bool {
        ["1", "true", "yes"].contains(
            environment[environmentKey]?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() ?? ""
        )
    }

    /// Diagnostics only: no UI surface and no render path calls this.
    @discardableResult
    public static func runIfRequested(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        queueURL: URL? = nil,
        recordingsRootURL: URL? = nil,
        reportDirectoryURL: URL? = nil,
        client: DesktopUploadClient? = nil,
        configuration: LocalCacheEvictionDryRunConfiguration = LocalCacheEvictionDryRunConfiguration(),
        scopeResolver: (@Sendable () async -> RecordingDeletionScope?)? = nil,
        fingerprintProvider: (@Sendable () -> String?)? = nil,
        runFence: (@Sendable () -> Bool)? = nil,
        log: (@Sendable (String) -> Void)? = nil
    ) async -> LocalCacheEvictionDryRunOutcome {
        guard isRequested(in: environment) else { return .notRequested }
        let resolvedClient = client ?? DesktopUploadClient.configuredFromEnvironment()
        let fingerprintSource = fingerprintProvider ?? {
            resolvedClient?.recordingSessionFingerprint
        }
        let initialFingerprint = fingerprintSource()
        let fence = runFence ?? {
            fingerprintSource() == initialFingerprint
        }
        let resolver = scopeResolver ?? {
            try? await resolvedClient?.recordingDeletionScope()
        }
        let service = LocalCacheEvictionDryRunService(
            queueURL: queueURL ?? DesktopUploadQueueService.defaultQueueURL(),
            recordingsRootURL: recordingsRootURL ?? LocalRecordingStore().rootURL,
            reportDirectoryURL: reportDirectoryURL,
            client: resolvedClient,
            configuration: configuration,
            scopeResolver: resolver,
            runFence: fence
        )
        let outcome = await service.run()
        let writer = log ?? { detail in
            AppLog.writeRaw(event: "cache_eviction_dry_run", detail: detail)
        }
        writer(outcome.logDetail)
        return outcome
    }
}
