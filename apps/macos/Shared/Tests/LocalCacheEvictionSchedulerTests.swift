import Foundation
import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class LocalCacheEvictionSchedulerTests: XCTestCase {
    private let now = Date(timeIntervalSince1970: 1_800_000_000)
    private let gigabyte: Int64 = 1_000_000_000

    func testBelowWarningDoesNotScanOrDelete() async {
        let candidateCalls = Counter()
        let evictCalls = Counter()
        let items = [candidate("a")]
        let scheduler = makeScheduler(
            usedBytes: 3_900_000_000,
            candidates: { candidateCalls.increment(); return items },
            evict: { _ in evictCalls.increment(); return .completed(bytes: 1) }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .belowThreshold)
        XCTAssertEqual(candidateCalls.value, 0)
        XCTAssertEqual(evictCalls.value, 0)
    }

    func testEvictsOldestFirstAndStopsAtWarning() async {
        let recorder = EvictionRecorder()
        let base = now
        let items = [
            candidate("old", finalizedAt: base.addingTimeInterval(-300), bytes: 300_000_000),
            candidate("middle", finalizedAt: base.addingTimeInterval(-200), bytes: 300_000_000),
            candidate("new", finalizedAt: base.addingTimeInterval(-100), bytes: 300_000_000),
        ]
        let scheduler = makeScheduler(
            usedBytes: 4_500_000_000,
            candidates: { items },
            evict: { candidate in
                recorder.record(candidate.itemID)
                return .completed(bytes: candidate.bytes)
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .completed(evaluated: 2, deleted: 2, freedBytes: 600_000_000))
        XCTAssertEqual(recorder.items, ["old", "middle"])
    }

    func testStopsAtWarningForManyCandidates() async {
        let recorder = EvictionRecorder()
        let base = now
        let items = (0..<10).map {
            candidate("item-\($0)", finalizedAt: base.addingTimeInterval(Double($0)), bytes: 100_000_000)
        }
        let scheduler = makeScheduler(
            usedBytes: 4_100_000_000,
            candidates: { items },
            evict: { candidate in
                recorder.record(candidate.itemID)
                return .completed(bytes: candidate.bytes)
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .completed(evaluated: 2, deleted: 2, freedBytes: 200_000_000))
        XCTAssertEqual(recorder.items, ["item-0", "item-1"])
    }

    func testMaximumDeletionsPerRunIsBounded() async {
        let recorder = EvictionRecorder()
        let base = now
        let items = (0..<10).map {
            candidate("item-\($0)", finalizedAt: base.addingTimeInterval(Double($0)), bytes: 100_000_000)
        }
        let scheduler = makeScheduler(
            usedBytes: 9_000_000_000,
            configuration: LocalCacheEvictionConfiguration(
                debounce: 0,
                maximumCandidates: 10,
                maximumDeletionsPerRun: 2
            ),
            candidates: { items },
            evict: { candidate in
                recorder.record(candidate.itemID)
                return .completed(bytes: candidate.bytes)
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .completed(evaluated: 2, deleted: 2, freedBytes: 200_000_000))
        XCTAssertEqual(recorder.items.count, 2)
    }

    func testUserKillSwitchDisabledDoesNotDelete() async {
        let evictCalls = Counter()
        let settings = SettingsBox(userEnabled: false, operatorDisabled: false)
        let items = [candidate("a")]
        let scheduler = makeScheduler(
            usedBytes: 9_000_000_000,
            settings: settings,
            candidates: { items },
            evict: { _ in evictCalls.increment(); return .completed(bytes: 1) }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .disabled)
        XCTAssertEqual(evictCalls.value, 0)
    }

    func testOperatorOverrideDoesNotDelete() async {
        let evictCalls = Counter()
        let settings = SettingsBox(userEnabled: true, operatorDisabled: true)
        let items = [candidate("a")]
        let scheduler = makeScheduler(
            usedBytes: 9_000_000_000,
            settings: settings,
            candidates: { items },
            evict: { _ in evictCalls.increment(); return .completed(bytes: 1) }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .operatorDisabled)
        XCTAssertEqual(evictCalls.value, 0)
    }

    func testDebounceSkipsRepeatedTriggersButLaunchAlwaysRuns() async {
        let clock = ClockBox(now)
        let evictCalls = Counter()
        let items = [candidate("a", bytes: 1_000_000_000)]
        let scheduler = makeScheduler(
            usedBytes: 4_500_000_000,
            clock: clock,
            candidates: { items },
            evict: { _ in evictCalls.increment(); return .completed(bytes: 1_000_000_000) }
        )

        let first = await scheduler.run(.uploadFinalized)
        let second = await scheduler.run(.footprintRefresh)
        let launch = await scheduler.run(.launch)

        XCTAssertEqual(first, .completed(evaluated: 1, deleted: 1, freedBytes: 1_000_000_000))
        XCTAssertEqual(second, .debounced)
        XCTAssertNotEqual(launch, .debounced)
        XCTAssertEqual(evictCalls.value, 2)
    }

    func testSingleFlightCoalescesConcurrentRuns() async {
        let gate = AsyncGate()
        let evictCalls = Counter()
        let items = [candidate("a", bytes: 1_000_000_000)]
        let scheduler = makeScheduler(
            usedBytes: 4_500_000_000,
            candidates: { items },
            evict: { _ in
                evictCalls.increment()
                await gate.wait()
                return .completed(bytes: 1_000_000_000)
            }
        )

        let first = Task { await scheduler.run(.launch) }
        await gate.waitForArrival()
        let second = Task { await scheduler.run(.uploadFinalized) }
        // Give the second caller time to join the in-flight task before the
        // first run is released.
        try? await Task.sleep(nanoseconds: 20_000_000)
        await gate.release()
        let results = await (first.value, second.value)

        XCTAssertEqual(results.0, .completed(evaluated: 1, deleted: 1, freedBytes: 1_000_000_000))
        XCTAssertEqual(results.1, results.0)
        XCTAssertEqual(evictCalls.value, 1)
    }

    func testScopeChangeStopsTheRunAfterTheCurrentItem() async {
        let recorder = EvictionRecorder()
        let base = now
        let items = [
            candidate("first", finalizedAt: base.addingTimeInterval(-2), bytes: 100_000_000),
            candidate("second", finalizedAt: base.addingTimeInterval(-1), bytes: 100_000_000),
        ]
        let scheduler = makeScheduler(
            usedBytes: 5_000_000_000,
            candidates: { items },
            evict: { candidate in
                recorder.record(candidate.itemID)
                return candidate.itemID == "first" ? .completed(bytes: 100_000_000) : .scopeChanged
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .failed(code: "scope_changed"))
        XCTAssertEqual(recorder.items, ["first", "second"])
    }

    func testIneligibleCandidatesAreSkippedAndCountedAsEvaluated() async {
        let base = now
        let items = [
            candidate("proof-missing", finalizedAt: base.addingTimeInterval(-3), bytes: 100_000_000),
            candidate("eligible", finalizedAt: base.addingTimeInterval(-2), bytes: 600_000_000),
        ]
        let scheduler = makeScheduler(
            usedBytes: 4_500_000_000,
            candidates: { items },
            evict: { candidate in
                candidate.itemID == "eligible"
                    ? .completed(bytes: candidate.bytes)
                    : .notEligible(primaryReason: .proofMissing, allReasons: [.proofMissing])
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .completed(evaluated: 2, deleted: 1, freedBytes: 600_000_000))
    }

    func testAlreadyCleanedCandidateIsNotCountedAsDeleted() async {
        let recorder = EvictionRecorder()
        let base = now
        let items = [
            candidate("a", finalizedAt: base.addingTimeInterval(-2), bytes: 100_000_000),
            candidate("a", finalizedAt: base.addingTimeInterval(-1), bytes: 100_000_000),
            candidate("b", finalizedAt: base.addingTimeInterval(-1), bytes: 600_000_000),
        ]
        let scheduler = makeScheduler(
            usedBytes: 4_500_000_000,
            candidates: { items },
            evict: { candidate in
                recorder.record(candidate.itemID)
                return recorder.items.filter { $0 == candidate.itemID }.count > 1
                    ? .noop
                    : .completed(bytes: candidate.bytes)
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .completed(evaluated: 3, deleted: 2, freedBytes: 700_000_000))
        XCTAssertEqual(recorder.items, ["a", "a", "b"])
    }

    func testKillSwitchIsReReadBeforeEveryCandidate() async {
        let settings = SettingsBox(userEnabled: true, operatorDisabled: false)
        let recorder = EvictionRecorder()
        let base = now
        let items = [
            candidate("first", finalizedAt: base.addingTimeInterval(-3), bytes: 100_000_000),
            candidate("second", finalizedAt: base.addingTimeInterval(-2), bytes: 100_000_000),
            candidate("third", finalizedAt: base.addingTimeInterval(-1), bytes: 100_000_000),
        ]
        let scheduler = makeScheduler(
            usedBytes: 5_000_000_000,
            settings: settings,
            candidates: { items },
            evict: { candidate in
                recorder.record(candidate.itemID)
                if candidate.itemID == "first" {
                    settings.set(userEnabled: false)
                }
                return .completed(bytes: candidate.bytes)
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(recorder.items, ["first"])
        XCTAssertEqual(result, .completed(evaluated: 1, deleted: 1, freedBytes: 100_000_000))
    }

    func testOperatorSwitchIsReReadBeforeEveryCandidate() async {
        let settings = SettingsBox(userEnabled: true, operatorDisabled: false)
        let recorder = EvictionRecorder()
        let base = now
        let items = [
            candidate("first", finalizedAt: base.addingTimeInterval(-2), bytes: 100_000_000),
            candidate("second", finalizedAt: base.addingTimeInterval(-1), bytes: 100_000_000),
        ]
        let scheduler = makeScheduler(
            usedBytes: 5_000_000_000,
            settings: settings,
            candidates: { items },
            evict: { candidate in
                recorder.record(candidate.itemID)
                if candidate.itemID == "first" {
                    settings.set(operatorDisabled: true)
                }
                return .completed(bytes: candidate.bytes)
            }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(recorder.items, ["first"])
        XCTAssertEqual(result, .completed(evaluated: 1, deleted: 1, freedBytes: 100_000_000))
    }

    func testKillSwitchReadAfterCandidateDiscoveryStopsBeforeEviction() async {
        let settings = SettingsBox(userEnabled: true, operatorDisabled: false)
        let evictCalls = Counter()
        let items = [candidate("a", bytes: 100_000_000)]
        let scheduler = makeScheduler(
            usedBytes: 5_000_000_000,
            settings: settings,
            candidates: {
                settings.set(userEnabled: false)
                return items
            },
            evict: { _ in evictCalls.increment(); return .completed(bytes: 1) }
        )

        let result = await scheduler.run(.launch)

        XCTAssertEqual(result, .disabled)
        XCTAssertEqual(evictCalls.value, 0)
    }

    func testStatusReportsBudgetThresholdAndOperatorOverride() async {
        let settings = SettingsBox(userEnabled: false, operatorDisabled: true)
        let scheduler = makeScheduler(
            usedBytes: 4_100_000_000,
            settings: settings,
            candidates: { [] },
            evict: { _ in .noop }
        )

        let status = await scheduler.status()

        XCTAssertEqual(status?.usedBytes, 4_100_000_000)
        XCTAssertEqual(status?.budgetBytes, 5_000_000_000)
        XCTAssertEqual(status?.threshold, .warning80)
        XCTAssertEqual(status?.settings.effectiveEnabled, false)
        XCTAssertEqual(
            status?.disabledExplanation,
            LocalCacheCleanupCopy.autoEvictionOperatorOverride
        )
    }

    func testUnknownFreeDiskFailsClosedWithoutDeletion() async {
        let evictCalls = Counter()
        let items = [candidate("a", bytes: 1_000_000_000)]
        let scheduler = LocalCacheEvictionScheduler(
            footprintProvider: {
                LocalCacheEvictionFootprint(
                    usedBytes: 9_000_000_000,
                    freeDiskBytes: nil,
                    diskCapacityBytes: 200_000_000_000
                )
            },
            settingsProvider: { .init(userEnabled: true, operatorDisabled: false) },
            candidateProvider: { items },
            evictor: { _ in evictCalls.increment(); return .completed(bytes: 1_000_000_000) }
        )

        let result = await scheduler.run(.launch)
        let status = await scheduler.status()

        XCTAssertEqual(result, .failed(code: "free_disk_unknown"))
        XCTAssertEqual(evictCalls.value, 0)
        XCTAssertEqual(status?.threshold, .unknown)
    }

    func testStatusFailsClosedWithoutFootprint() async {
        let scheduler = LocalCacheEvictionScheduler(
            footprintProvider: { nil },
            settingsProvider: { .init(userEnabled: true, operatorDisabled: false) },
            candidateProvider: { [] },
            evictor: { _ in .noop }
        )

        let status = await scheduler.status()
        let run = await scheduler.run(.launch)

        XCTAssertNil(status)
        XCTAssertEqual(run, .failed(code: "footprint_unavailable"))
    }

    // MARK: - Fixtures

    private func candidate(
        _ id: String,
        finalizedAt: Date? = nil,
        bytes: Int64 = 500_000_000
    ) -> LocalCacheEvictionCandidate {
        LocalCacheEvictionCandidate(
            itemID: id,
            localRecordingFingerprint: "rec_fpr_\(id)",
            verifiedAt: nil,
            finalizedAt: finalizedAt ?? now.addingTimeInterval(-100),
            bytes: bytes
        )
    }

    private func makeScheduler(
        usedBytes: Int64,
        configuration: LocalCacheEvictionConfiguration = LocalCacheEvictionConfiguration(debounce: 60),
        settings: SettingsBox = SettingsBox(userEnabled: true, operatorDisabled: false),
        clock: ClockBox = ClockBox(Date(timeIntervalSince1970: 1_800_000_000)),
        candidates: @escaping @Sendable () async -> [LocalCacheEvictionCandidate],
        evict: @escaping @Sendable (LocalCacheEvictionCandidate) async -> LocalCacheCleanupOutcome
    ) -> LocalCacheEvictionScheduler {
        let used = usedBytes
        return LocalCacheEvictionScheduler(
            configuration: configuration,
            footprintProvider: {
                LocalCacheEvictionFootprint(
                    usedBytes: used,
                    freeDiskBytes: 100_000_000_000,
                    diskCapacityBytes: 200_000_000_000
                )
            },
            settingsProvider: { settings.snapshot },
            candidateProvider: candidates,
            evictor: evict,
            clock: { clock.now }
        )
    }
}

// MARK: - Test doubles

private final class SettingsBox: @unchecked Sendable {
    private let lock = NSLock()
    private var userEnabled: Bool
    private var operatorDisabled: Bool

    init(userEnabled: Bool, operatorDisabled: Bool) {
        self.userEnabled = userEnabled
        self.operatorDisabled = operatorDisabled
    }

    var snapshot: LocalCacheEvictionSettingSnapshot {
        lock.lock(); defer { lock.unlock() }
        return LocalCacheEvictionSettingSnapshot(
            userEnabled: userEnabled,
            operatorDisabled: operatorDisabled
        )
    }

    func set(userEnabled: Bool? = nil, operatorDisabled: Bool? = nil) {
        lock.lock()
        if let userEnabled { self.userEnabled = userEnabled }
        if let operatorDisabled { self.operatorDisabled = operatorDisabled }
        lock.unlock()
    }
}

private final class ClockBox: @unchecked Sendable {
    private let lock = NSLock()
    private var date: Date

    init(_ date: Date) {
        self.date = date
    }

    var now: Date {
        lock.lock(); defer { lock.unlock() }
        return date
    }
}

private final class Counter: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0

    var value: Int {
        lock.lock(); defer { lock.unlock() }
        return count
    }

    func increment() {
        lock.lock(); count += 1; lock.unlock()
    }
}

private final class EvictionRecorder: @unchecked Sendable {
    private let lock = NSLock()
    private var values: [String] = []

    var items: [String] {
        lock.lock(); defer { lock.unlock() }
        return values
    }

    func record(_ id: String) {
        lock.lock(); values.append(id); lock.unlock()
    }
}

private actor AsyncGate {
    private var continuation: CheckedContinuation<Void, Never>?
    private var arrived = false
    private var arrivedContinuation: CheckedContinuation<Void, Never>?

    func wait() async {
        arrived = true
        arrivedContinuation?.resume()
        arrivedContinuation = nil
        await withCheckedContinuation { self.continuation = $0 }
    }

    func waitForArrival() async {
        if arrived { return }
        await withCheckedContinuation { self.arrivedContinuation = $0 }
    }

    func release() {
        continuation?.resume()
        continuation = nil
    }
}
