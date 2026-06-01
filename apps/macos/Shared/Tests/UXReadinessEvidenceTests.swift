import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class UXReadinessEvidenceTests: XCTestCase {
    func testReadyUXEvidenceMustBeExplicitlyNonRecording() {
        let evidence = UXReadinessEvidence(
            state: .ready,
            copyClaim: "Audio route ready, not recording",
            nonRecordingExplicit: true,
            recordingImplied: false,
            accessibilityNotes: "Status text and icon are present",
            result: .passed
        )

        XCTAssertTrue(evidence.nonRecordingExplicit)
        XCTAssertFalse(evidence.recordingImplied)
        XCTAssertEqual(evidence.result, .passed)
    }

    func testRecordingImpliedUXEvidenceIsBlocked() {
        let evidence = UXReadinessEvidence(
            state: .active,
            copyClaim: "Recording active",
            nonRecordingExplicit: false,
            recordingImplied: true,
            accessibilityNotes: "Copy implies capture",
            result: .blocked
        )

        XCTAssertTrue(evidence.recordingImplied)
        XCTAssertEqual(evidence.result, .blocked)
    }
}
#endif
