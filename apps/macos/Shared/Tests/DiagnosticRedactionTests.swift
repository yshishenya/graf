import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class DiagnosticRedactionTests: XCTestCase {
    func testReadinessEvidenceDiagnosticsKeepMetadataAndRemoveSensitiveFields() {
        let manifest: [String: DiagnosticFieldValue] = [
            "liveRouteReadiness": .object([
                "status": .string("failed"),
                "failureReason": .string("missing_valid_frames"),
                "rawAudio": .string("forbidden")
            ]),
            "browserTargetEvidence": .array([
                .object([
                    "target": .string("chrome"),
                    "status": .string("blocked"),
                    "meetingContent": .string("forbidden")
                ])
            ]),
            "transcriptText": .string("forbidden"),
            "routeStatus": .string("failed"),
            "recoveryActionId": .string("rerun_readiness_check")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["liveRouteReadiness"])
        XCTAssertNotNil(result.manifest["browserTargetEvidence"])
        XCTAssertNotNil(result.manifest["routeStatus"])
        XCTAssertNil(result.manifest["transcriptText"])
        XCTAssertTrue(result.removedFields.contains("liveRouteReadiness.rawAudio"))
        XCTAssertTrue(result.removedFields.contains("browserTargetEvidence[0].meetingContent"))
    }
}
#endif
