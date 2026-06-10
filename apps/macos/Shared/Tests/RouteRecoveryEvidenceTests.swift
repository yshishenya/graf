import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class RouteRecoveryEvidenceTests: XCTestCase {
    func testRouteRecoveryEvidenceUsesCommonResultValues() {
        let evidence = RouteRecoveryEvidence(
            trigger: "coreaudiod_restart",
            detectedWithinSeconds: 2.0,
            expectedState: .stale,
            actualState: .stale,
            recoveryAction: "rerun_live_passthrough_check",
            result: .passed
        )

        XCTAssertEqual(evidence.result, .passed)
        XCTAssertLessThanOrEqual(evidence.detectedWithinSeconds, 5.0)
        XCTAssertEqual(evidence.expectedState, .stale)
    }

    func testCoreAudiodRestartProducesRecoveryEvent() {
        let monitor = AudioEnvironmentMonitor(now: { Date(timeIntervalSince1970: 1_780_284_000) })

        let events = monitor.livePassthroughRecoveryEvents(
            for: [.coreaudiodRestarted],
            previousStatus: .active
        )

        XCTAssertEqual(events.map(\.eventType), [.coreaudiodRestarted])
        XCTAssertEqual(events.first?.newStatus, .stale)
        XCTAssertEqual(events.first?.recoveryAction, "rerun_live_passthrough_check")
    }

    func testSleepWakeProducesSafeRouteInvalidation() {
        let monitor = AudioEnvironmentMonitor(now: { Date(timeIntervalSince1970: 1_780_284_000) })

        let events = monitor.routeInvalidationEvents(
            for: [.sleepWake],
            previousStatus: .ready
        )

        XCTAssertEqual(events.map(\.source), [.appIO])
        XCTAssertEqual(events.first?.newReadinessStatus, .stale)
    }

    func testRouteEngineMarksCoreAudioRestartAsStale() {
        let engine = PassthroughRouteEngine(sharedMemory: nil)
        let log = RouteRecoveryTestLog()

        let state = engine.markCoreAudioRestarted { event, detail in
            log.append(event, detail)
        }

        XCTAssertEqual(state, .stale("coreaudiod_restarted"))
        XCTAssertTrue(log.contains { $0.0 == "passthrough_bridge_stale" })
    }
}

private final class RouteRecoveryTestLog: @unchecked Sendable {
    private let lock = NSLock()
    private var entries: [(String, String)] = []

    func append(_ event: String, _ detail: String) {
        lock.lock()
        entries.append((event, detail))
        lock.unlock()
    }

    func contains(where predicate: ((String, String)) -> Bool) -> Bool {
        lock.lock()
        let snapshot = entries
        lock.unlock()
        return snapshot.contains(where: predicate)
    }
}
#endif
