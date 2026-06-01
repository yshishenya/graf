import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class ReleaseHardeningEvidenceTests: XCTestCase {
    func testRunEncodesMetadataOnlyFields() throws {
        let run = ReleaseHardeningRun(
            runId: "005-local",
            createdAt: Date(timeIntervalSince1970: 1_780_284_000),
            macOSVersion: "14.5",
            appBuild: "local",
            driverBuild: "local",
            result: .blocked,
            notes: "No-hang gate pending",
            evidenceFamilies: [.installedRuntime, .noHang]
        )

        let object = try JSONSerialization.jsonObject(with: JSONEncoder().encode(run)) as? [String: Any]

        XCTAssertEqual(object?["runId"] as? String, "005-local")
        XCTAssertEqual(object?["result"] as? String, "blocked")
        XCTAssertNil(object?["rawAudio"])
        XCTAssertNil(object?["transcriptText"])
        XCTAssertNil(object?["meetingContent"])
    }

    func testNoHangEvidencePreservesThresholdMetadata() {
        let evidence = CoreAudioNoHangEvidence(
            targetSurface: "macOS Sound settings",
            openedWithinSeconds: 2.4,
            coreaudiodCPUPeakPercent: 6.0,
            coreaudiodCPUSustainedPercent: 3.0,
            routeStateBefore: .ready,
            routeStateAfter: .ready,
            result: .passed
        )

        XCTAssertLessThanOrEqual(evidence.openedWithinSeconds, 5)
        XCTAssertLessThanOrEqual(evidence.coreaudiodCPUSustainedPercent, 10)
        XCTAssertEqual(evidence.result, .passed)
    }

    func testDeferredRecordingAcceptanceDefaultsToBlocked() {
        let state = DeferredRecordingAcceptanceState()

        XCTAssertEqual(state.blockedUntil, "local_recording_support")
        XCTAssertEqual(state.result, .blocked)
        XCTAssertTrue(state.retentionPolicyRequired)
        XCTAssertTrue(state.deletionPolicyRequired)
    }
}
#endif
