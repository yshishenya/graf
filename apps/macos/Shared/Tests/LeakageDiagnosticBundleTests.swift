import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class LeakageDiagnosticBundleTests: XCTestCase {
    func testLocalRecordingBundleIncludesMetadataOnlyLeakageFinalization() throws {
        let manifest = LocalRecordingManifest(
            sessionId: "session",
            createdAt: Date(timeIntervalSince1970: 1),
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: Date(timeIntervalSince1970: 2),
            finalizedAt: Date(timeIntervalSince1970: 3),
            status: .degraded,
            directoryId: "directory",
            transcriptionReadiness: .degraded,
            tracks: [],
            leakageFinalization: LeakageFinalization(
                status: .leakageDetected,
                evaluatedAt: Date(timeIntervalSince1970: 3),
                measurementAttempted: true,
                measurementApplicable: true,
                alignmentStatus: .aligned,
                confidence: 0.9,
                failureReason: .leakageDetected,
                originalEvidenceStatus: .leakageDetected,
                transcriptionGate: .blockedLeakageDetected,
                routeMetadata: RecordingRouteMetadata(outputRouteClass: "built_in"),
                measurement: LeakageMeasurement(
                    speakerReferenceDb: -10,
                    virtualMicLeakageDb: -20,
                    relativeLeakageDb: -10,
                    intelligibilityStatus: .intelligible,
                    status: .blocked,
                    measuredAt: Date(timeIntervalSince1970: 3),
                    directLoopbackSuspicion: true,
                    acousticLeakageSuspicion: true,
                    confidence: 0.9
                )
            ),
            failureReason: .leakageDetected
        )

        let bundle = try DiagnosticBundleService().buildLocalRecordingBundle(manifest: manifest)

        XCTAssertNotNil(bundle.manifest["leakageFinalization"])
        XCTAssertEqual(bundle.manifest["directLoopbackSuspicion"], .bool(true))
        XCTAssertEqual(bundle.manifest["acousticLeakageSuspicion"], .bool(true))
        XCTAssertNil(bundle.manifest["rawAudio"])
        XCTAssertNil(bundle.manifest["transcriptText"])
    }

    func testRedactorRemovesForbiddenLeakageNestedFields() {
        let result = DiagnosticRedactor().redact([
            "leakageFinalization": .object([
                "status": .string("unproven"),
                "participantSpeech": .string("not allowed"),
                "absolutePath": .string("/Users/example/Meeting/mic.wav")
            ]),
            "leakageMeasurement": .object([
                "confidence": .double(0.42),
                "signedUrls": .string("https://example.presigned/upload")
            ])
        ])

        XCTAssertEqual(result.status, .blockedSensitiveContent)
        guard case .object(let finalization)? = result.manifest["leakageFinalization"] else {
            XCTFail("Expected leakageFinalization object")
            return
        }
        XCTAssertEqual(finalization["status"], .string("unproven"))
        XCTAssertNil(finalization["participantSpeech"])
        XCTAssertNil(finalization["absolutePath"])
    }
}
#endif
