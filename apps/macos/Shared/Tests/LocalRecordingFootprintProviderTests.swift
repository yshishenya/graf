import Foundation
import XCTest
@testable import TwoBrainRecAppCore
@testable import TwoBrainRecShared

final class LocalRecordingFootprintProviderTests: XCTestCase {
    private final class Locked<Value>: @unchecked Sendable {
        private let lock = NSLock()
        private var value: Value

        init(_ value: Value) {
            self.value = value
        }

        func read() -> Value {
            lock.lock(); defer { lock.unlock() }
            return value
        }

        func update(_ body: (inout Value) -> Void) {
            lock.lock(); defer { lock.unlock() }
            body(&value)
        }
    }

    private let policy = LocalBufferPolicy(
        maxBytesPerDevice: 100,
        warningFraction: 0.75,
        criticalFraction: 0.9,
        minimumDiskReserveBytes: 0,
        retentionDays: 7
    )

    private static func snapshot(_ bytes: Int64, at date: Date = Date()) -> LocalRecordingFootprintSnapshot {
        LocalRecordingFootprintSnapshot(
            bytes: bytes,
            fileCount: bytes > 0 ? 1 : 0,
            measuredAt: date,
            rootPath: "/synthetic/recordings"
        )
    }

    private func provider(
        bytes: Int64 = 0,
        freeDiskBytes: Int64 = 1_000_000_000,
        ttl: TimeInterval = 60,
        timeout: TimeInterval = 1,
        clock: @escaping LocalRecordingFootprintProvider.Clock = Date.init,
        measure: @escaping LocalRecordingFootprintProvider.Measure = { _ in
            LocalRecordingFootprintSnapshot(bytes: 0, fileCount: 0, measuredAt: Date(), rootPath: "/synthetic")
        }
    ) -> LocalRecordingFootprintProvider {
        LocalRecordingFootprintProvider(
            rootURL: URL(fileURLWithPath: "/synthetic/recordings"),
            policy: policy,
            ttl: ttl,
            timeout: timeout,
            clock: clock,
            measure: measure,
            availableBytes: { _ in freeDiskBytes }
        )
    }

    func testMeasurementRunsOffMainThread() async {
        let wasMain = Locked<Bool?>(nil)
        let provider = provider(measure: { _ in
            wasMain.update { $0 = Thread.isMainThread }
            return Self.snapshot(0)
        })

        let risk = await provider.refresh()

        XCTAssertEqual(risk, .healthy)
        XCTAssertEqual(wasMain.read(), false)
    }

    func testWarningAllowsStartAtConfiguredThreshold() async {
        let provider = provider(measure: { _ in Self.snapshot(80) })
        let risk = await provider.refresh()
        XCTAssertEqual(risk, .warning)
        XCTAssertTrue(risk.allowsRecordingStart)
        let cached = await provider.cachedRisk()
        XCTAssertEqual(cached, .warning)
    }

    func testCacheExpiresAtTTL() async {
        let clock = Locked<Date>(Date(timeIntervalSince1970: 100))
        let provider = provider(ttl: 60, clock: { clock.read() }, measure: { _ in Self.snapshot(0) })
        _ = await provider.refresh()
        let fresh = await provider.cachedRisk()
        XCTAssertNotNil(fresh)

        clock.update { $0 = $0.addingTimeInterval(61) }
        let stale = await provider.cachedRisk()
        XCTAssertNil(stale)
    }

    func testConcurrentRefreshIsSingleFlight() async {
        let calls = Locked<Int>(0)
        let provider = provider(timeout: 2, measure: { _ in
            calls.update { $0 += 1 }
            Thread.sleep(forTimeInterval: 0.05)
            return Self.snapshot(0)
        })

        async let first = provider.refresh()
        async let second = provider.refresh()
        _ = await (first, second)

        XCTAssertEqual(calls.read(), 1)
    }

    func testMeasurementErrorFailsClosed() async {
        enum SyntheticError: Error { case failed }
        let provider = provider(measure: { _ in throw SyntheticError.failed })
        let risk = await provider.refresh()
        XCTAssertEqual(risk, .mustDegradeOrStop)
    }

    func testTimeoutFailsClosed() async {
        let provider = provider(timeout: 0.05, measure: { _ in
            Thread.sleep(forTimeInterval: 0.2)
            return Self.snapshot(0)
        })
        let risk = await provider.refresh()
        XCTAssertEqual(risk, .mustDegradeOrStop)
    }

    func testInvalidateDuringMeasurementRejectsStaleResult() async {
        let provider = provider(timeout: 2, measure: { _ in
            Thread.sleep(forTimeInterval: 0.1)
            return Self.snapshot(0)
        })

        let task = Task { await provider.refresh() }
        try? await Task.sleep(nanoseconds: 20_000_000)
        await provider.invalidate()
        let risk = await task.value

        XCTAssertEqual(risk, .mustDegradeOrStop)
        let cached = await provider.cachedRisk()
        XCTAssertNil(cached)
    }

    func testRiskUsesFreshCacheWithoutRescanning() async {
        let calls = Locked<Int>(0)
        let provider = provider(measure: { _ in
            calls.update { $0 += 1 }
            return Self.snapshot(0)
        })

        _ = await provider.risk()
        _ = await provider.risk()

        XCTAssertEqual(calls.read(), 1)
    }

    func testInvalidateClearsCache() async {
        let provider = provider(measure: { _ in Self.snapshot(0) })
        _ = await provider.refresh()
        let before = await provider.cachedRisk()
        XCTAssertNotNil(before)

        await provider.invalidate()
        let after = await provider.cachedRisk()
        XCTAssertNil(after)
    }
}
