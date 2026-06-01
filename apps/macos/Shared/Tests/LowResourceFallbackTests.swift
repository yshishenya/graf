import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourceFallbackTests: XCTestCase {
    func testRouteEngineCanSwitchToAccepted005Fallback() {
        let engine = PassthroughRouteEngine(sharedMemory: nil)
        var log: [(String, String)] = []

        let state = engine.switchToAccepted005Fallback(reason: "low_resource_p1_gate_blocked") { event, detail in
            log.append((event, detail))
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
#endif
