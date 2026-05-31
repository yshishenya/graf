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

    func testLiveRouteReadinessBundleKeepsOnlyMetadata() throws {
        let now = Date(timeIntervalSince1970: 1_779_887_120)
        let result = LiveRouteReadinessResult(
            status: .failed,
            microphoneEvidence: MicrophonePathEvidence(
                selectedPhysicalDeviceId: "built-in-input",
                selectedPhysicalDeviceName: "MacBook Pro Microphone",
                status: .failed,
                validFrameCount: 0,
                emptyBufferCount: 1,
                capturabilityStatus: .notCapturable,
                selfRoutingRejected: false,
                failureReason: "missing_valid_frames",
                checkedAt: now
            ),
            speakerEvidence: SpeakerPathEvidence(
                selectedPhysicalOutputId: "built-in-output",
                selectedPhysicalOutputName: "MacBook Pro Speakers",
                status: .passed,
                stimulusObserved: true,
                validFrameCount: 1,
                emptyBufferCount: 0,
                selfRoutingRejected: false,
                checkedAt: now
            ),
            checkedAt: now,
            recoveryAction: "rerun_readiness_check"
        )

        let bundle = try DiagnosticBundleService().buildLiveRouteReadinessBundle(result: result)

        XCTAssertEqual(bundle.redactionState, .redacted)
        XCTAssertNotNil(bundle.manifest["liveRouteReadiness"])
        XCTAssertNotNil(bundle.manifest["microphonePathEvidence"])
        XCTAssertNotNil(bundle.manifest["speakerPathEvidence"])
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }
}
#endif
