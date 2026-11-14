import Foundation
import TwoBrainRecShared

public struct LocalRecordingFootprintSnapshot: Equatable, Sendable {
    public let bytes: Int64
    public let fileCount: Int
    public let measuredAt: Date
    public let rootPath: String

    public init(bytes: Int64, fileCount: Int, measuredAt: Date, rootPath: String) {
        self.bytes = bytes
        self.fileCount = fileCount
        self.measuredAt = measuredAt
        self.rootPath = rootPath
    }
}

public enum LocalRecordingFootprintError: Error, Equatable, Sendable {
    case rootIsNotDirectory
    case enumerationFailed
}

public enum LocalRecordingFootprintMeasurer {
    public static func measure(
        at rootURL: URL,
        fileManager: FileManager = .default,
        now: Date = Date()
    ) throws -> LocalRecordingFootprintSnapshot {
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: rootURL.path, isDirectory: &isDirectory) else {
            return LocalRecordingFootprintSnapshot(
                bytes: 0,
                fileCount: 0,
                measuredAt: now,
                rootPath: rootURL.path
            )
        }
        guard isDirectory.boolValue else {
            throw LocalRecordingFootprintError.rootIsNotDirectory
        }
        let rootValues = try rootURL.resourceValues(forKeys: [.isSymbolicLinkKey])
        guard rootValues.isSymbolicLink != true else {
            throw LocalRecordingFootprintError.rootIsNotDirectory
        }

        let keys: [URLResourceKey] = [
            .isRegularFileKey,
            .isSymbolicLinkKey,
            .totalFileAllocatedSizeKey,
            .fileAllocatedSizeKey,
            .fileSizeKey,
        ]
        let keySet = Set(keys)
        var enumerationFailed = false
        guard let enumerator = fileManager.enumerator(
            at: rootURL,
            includingPropertiesForKeys: keys,
            options: [.skipsHiddenFiles, .skipsPackageDescendants],
            errorHandler: { _, _ in
                enumerationFailed = true
                return false
            }
        ) else {
            throw LocalRecordingFootprintError.enumerationFailed
        }

        var bytes: Int64 = 0
        var fileCount = 0
        for case let fileURL as URL in enumerator {
            let values: URLResourceValues
            do {
                values = try fileURL.resourceValues(forKeys: keySet)
            } catch let error as NSError where error.domain == NSCocoaErrorDomain
                && [NSFileNoSuchFileError, NSFileReadNoSuchFileError].contains(error.code) {
                // A recording may be deleted while the scan is in flight.
                continue
            }
            guard values.isSymbolicLink != true, values.isRegularFile == true else {
                continue
            }
            let fileBytes = values.totalFileAllocatedSize
                ?? values.fileAllocatedSize
                ?? values.fileSize
                ?? 0
            guard fileBytes > 0 else { continue }
            let (next, overflow) = bytes.addingReportingOverflow(Int64(fileBytes))
            bytes = overflow ? Int64.max : next
            fileCount += 1
        }
        guard !enumerationFailed else {
            throw LocalRecordingFootprintError.enumerationFailed
        }
        return LocalRecordingFootprintSnapshot(
            bytes: bytes,
            fileCount: fileCount,
            measuredAt: now,
            rootPath: rootURL.path
        )
    }
}

public actor LocalRecordingFootprintProvider {
    public typealias Measure = @Sendable (URL) throws -> LocalRecordingFootprintSnapshot
    public typealias AvailableBytes = @Sendable (URL) throws -> Int64
    public typealias Clock = @Sendable () -> Date

    private struct CachedMeasurement: Sendable {
        let risk: LocalBufferRiskState
        let snapshot: LocalRecordingFootprintSnapshot
        let recordedAt: Date
    }

    private struct MeasurementResult: Sendable {
        let risk: LocalBufferRiskState
        let snapshot: LocalRecordingFootprintSnapshot?
    }

    private final class MeasurementWaiter: @unchecked Sendable {
        private let lock = NSLock()
        private var continuation: CheckedContinuation<MeasurementResult?, Never>?
        private var resumed = false

        func install(_ continuation: CheckedContinuation<MeasurementResult?, Never>) {
            lock.lock()
            if resumed {
                lock.unlock()
                continuation.resume(returning: nil)
                return
            }
            self.continuation = continuation
            lock.unlock()
        }

        func resume(_ result: MeasurementResult?) {
            lock.lock()
            guard !resumed else {
                lock.unlock()
                return
            }
            resumed = true
            let continuation = continuation
            self.continuation = nil
            lock.unlock()
            continuation?.resume(returning: result)
        }
    }

    private let rootURL: URL
    private let policy: LocalBufferPolicy
    private let measure: Measure
    private let availableBytes: AvailableBytes
    private let ttl: TimeInterval
    private let timeout: TimeInterval
    private let clock: Clock
    private var cached: CachedMeasurement?
    private var inFlight: Task<MeasurementResult, Never>?
    private var generation = 0

    public init(
        rootURL: URL,
        policy: LocalBufferPolicy = LocalBufferService.defaultPolicy,
        ttl: TimeInterval = 60,
        timeout: TimeInterval = 2,
        clock: @escaping Clock = Date.init,
        measure: @escaping Measure = { try LocalRecordingFootprintMeasurer.measure(at: $0) },
        availableBytes: @escaping AvailableBytes = LocalRecordingStorageProbe.measureAvailableBytes
    ) {
        self.rootURL = rootURL
        self.policy = policy
        self.ttl = max(0, ttl)
        self.timeout = max(0.05, timeout)
        self.clock = clock
        self.measure = measure
        self.availableBytes = availableBytes
    }

    public func cachedRisk(maxAge: TimeInterval? = nil) -> LocalBufferRiskState? {
        guard let cached else { return nil }
        let allowedAge = maxAge ?? ttl
        guard clock().timeIntervalSince(cached.recordedAt) <= allowedAge else {
            return nil
        }
        return cached.risk
    }

    public func lastSnapshot() -> LocalRecordingFootprintSnapshot? {
        cached?.snapshot
    }

    public func invalidate() {
        generation += 1
        cached = nil
        inFlight?.cancel()
        inFlight = nil
    }

    /// Return a fresh cached value when possible; only scan the folder when the
    /// cache is missing or older than the requested age.
    public func risk(maxAge: TimeInterval? = nil) async -> LocalBufferRiskState {
        if let cached = cachedRisk(maxAge: maxAge) {
            return cached
        }
        return await refresh()
    }

    public func refresh() async -> LocalBufferRiskState {
        let generation = generation
        if let inFlight {
            let result = await waitForMeasurement(inFlight)
            guard generation == self.generation else {
                return .mustDegradeOrStop
            }
            return result?.risk ?? .mustDegradeOrStop
        }

        let rootURL = rootURL
        let policy = policy
        let measure = measure
        let availableBytes = availableBytes
        let task = Task.detached(priority: .utility) { () -> MeasurementResult in
            do {
                let snapshot = try measure(rootURL)
                let freeDiskBytes = try availableBytes(rootURL)
                let risk = LocalBufferService().riskState(
                    usedBytes: snapshot.bytes,
                    freeDiskBytes: freeDiskBytes,
                    policy: policy
                )
                return MeasurementResult(risk: risk, snapshot: snapshot)
            } catch {
                return MeasurementResult(risk: .mustDegradeOrStop, snapshot: nil)
            }
        }
        inFlight = task
        let result = await waitForMeasurement(task)
        inFlight = nil
        guard generation == self.generation else {
            return .mustDegradeOrStop
        }
        guard let result else {
            return .mustDegradeOrStop
        }
        if let snapshot = result.snapshot {
            cached = CachedMeasurement(
                risk: result.risk,
                snapshot: snapshot,
                recordedAt: clock()
            )
        }
        return result.risk
    }

    private func waitForMeasurement(
        _ task: Task<MeasurementResult, Never>
    ) async -> MeasurementResult? {
        let waiter = MeasurementWaiter()
        return await withCheckedContinuation { continuation in
            waiter.install(continuation)
            Task.detached {
                let result = await task.value
                waiter.resume(result)
            }
            Task.detached { [timeout] in
                try? await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                task.cancel()
                waiter.resume(nil)
            }
        }
    }
}
