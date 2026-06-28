import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LowResourcePromotionTests: XCTestCase {
    func testPassedP1RunPromotesLowResourceMode() {
        let decision = gate().decision(for: validationRun(result: .passed))

        XCTAssertEqual(decision.status, .promoted)
        XCTAssertEqual(decision.reason, "all_p1_gates_passed")
    }

    func testMissingOrBlockedRunUses005Fallback() {
        XCTAssertEqual(gate().decision(for: nil).status, .fallback)

        var run = validationRun(result: .passed)
        run.startupAttempts[0] = StartupAttemptEvidence(
            attemptId: "slow",
            trigger: .clientIOOpened,
            startedAt: Date(timeIntervalSince1970: 1),
            completedAt: Date(timeIntervalSince1970: 5),
            durationMs: 4000,
            outcome: .blocked,
            blockedReason: "startup_timeout"
        )

        let decision = gate().decision(for: run)

        XCTAssertEqual(decision.status, .fallback)
        XCTAssertEqual(decision.reason, "startup_attempt_exceeded_3000_ms")
        XCTAssertEqual(decision.fallbackBaseline, "005-macos-passthrough-release-hardening")
    }

    func testPromotionDecisionDiagnosticsAreMetadataOnly() throws {
        let decision = gate().decision(for: validationRun(result: .passed))
        let bundle = try DiagnosticBundleService().buildLowResourcePromotionBundle(decision: decision)

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["lowResourcePromotionDecision"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }

    func testWorkingDeviceStorePersistsAcceptanceMetadata() {
        let store = WorkingDeviceStore()
        let decision = gate().decision(for: validationRun(result: .passed))

        store.persistLowResourceAcceptance(
            decision: decision,
            validationRunId: "promotion-run",
            updatedAt: Date(timeIntervalSince1970: 3)
        )

        XCTAssertEqual(store.lowResourceAcceptanceMetadata?.decision.status, .promoted)
        XCTAssertEqual(store.lowResourceAcceptanceMetadata?.validationRunId, "promotion-run")
    }

    private func gate() -> LowResourcePromotionGate {
        LowResourcePromotionGate(now: { Date(timeIntervalSince1970: 2) })
    }

    private func validationRun(result: LowResourceEvidenceResult) -> LowResourceValidationRun {
        LowResourceValidationRun(
            runId: "promotion-run",
            createdAt: Date(timeIntervalSince1970: 1),
            appBuild: "local",
            driverBuild: "local",
            routeTruthSnapshots: [LowResourceTestFixtures.readySnapshot(clientOpen: true)],
            startupAttempts: [
                StartupAttemptEvidence(
                    attemptId: "startup",
                    trigger: .clientIOOpened,
                    startedAt: Date(timeIntervalSince1970: 1),
                    completedAt: Date(timeIntervalSince1970: 2),
                    durationMs: 1000,
                    outcome: .ready
                )
            ],
            realtimeSafety: RealtimeSafetyEvidence(
                scanId: "rt",
                checkedPaths: ["apps/macos/AudioDriver/Sources/Plugin/GrafProofDriver.cpp"],
                result: .passed
            ),
            result: result
        )
    }
}
#endif
