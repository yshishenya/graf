import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceFallbackTests: XCTestCase {
    func testRouteEngineCanSwitchToAccepted005Fallback() {
        let engine = PassthroughRouteEngine(sharedMemory: nil)
        let log = LowResourceFallbackTestLog()

        let state = engine.switchToAccepted005Fallback(reason: "low_resource_p1_gate_blocked") { event, detail in
            log.append(event, detail)
        }

        XCTAssertEqual(state, .fallback("low_resource_p1_gate_blocked"))
        XCTAssertTrue(log.contains { $0.0 == "passthrough_bridge_fallback" })
    }

    func testFallbackStartupAttemptPreservesEvidence() {
        let attempt = PassthroughBridge.startupAttemptEvidence(
            attemptId: "fallback",
            trigger: .recovery,
            startedAt: Date(timeIntervalSince1970: 1),
            completedAt: Date(timeIntervalSince1970: 2),
            outcome: .fallback,
            fallbackUsed: true
        )

        XCTAssertEqual(attempt.outcome, .fallback)
        XCTAssertTrue(attempt.fallbackUsed)
    }
}

private final class LowResourceFallbackTestLog: @unchecked Sendable {
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
