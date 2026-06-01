import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class InstallerLifecycleEvidenceTests: XCTestCase {
    func testInstallerLifecycleEvidenceUsesCommonResultValues() {
        let evidence = InstallerLifecycleEvidence(
            operation: "repair",
            preState: "installed",
            postState: "repaired",
            coreAudioRefreshRequired: true,
            runtimeProbeResult: "accepted",
            result: .passed
        )

        XCTAssertEqual(evidence.operation, "repair")
        XCTAssertTrue(evidence.coreAudioRefreshRequired)
        XCTAssertEqual(evidence.runtimeProbeResult, "accepted")
        XCTAssertEqual(evidence.result, .passed)
    }

    func testSkippedLifecycleOperationIsNotAccepted() {
        let evidence = InstallerLifecycleEvidence(
            operation: "uninstall",
            preState: "installed",
            postState: "unknown",
            coreAudioRefreshRequired: true,
            runtimeProbeResult: "not_run",
            result: .notAccepted
        )

        XCTAssertEqual(evidence.result, .notAccepted)
        XCTAssertEqual(evidence.runtimeProbeResult, "not_run")
    }
}
#endif
