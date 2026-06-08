import Foundation
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class SystemAudioDiagnosticRedactionTests: XCTestCase {
    func testSystemAudioEvidenceKeepsSafeMetadataAndRemovesMeetingContent() {
        let manifest: [String: DiagnosticFieldValue] = [
            "systemAudioCaptureSession": .object([
                "sessionId": .string("session"),
                "permissionState": .string("granted"),
                "scopeKind": .string("application"),
                "sourceDisplayName": .string("Telemost"),
                "rawAudio": .string("forbidden")
            ]),
            "captureHealthSnapshot": .object([
                "phase": .string("activeRecording"),
                "coreaudiodCpuPercent": .double(4),
                "appCpuPercent": .double(8),
                "helperCpuPercent": .double(2),
                "meetingContent": .string("forbidden")
            ]),
            "capturePermissions": .object([
                "microphone": .string("granted"),
                "systemAudio": .string("granted")
            ]),
            "transcriptText": .string("forbidden")
        ]

        let result = DiagnosticRedactor().redact(manifest)

        XCTAssertNotNil(result.manifest["systemAudioCaptureSession"])
        XCTAssertNotNil(result.manifest["captureHealthSnapshot"])
        XCTAssertNotNil(result.manifest["capturePermissions"])
        XCTAssertNil(result.manifest["transcriptText"])
        XCTAssertTrue(result.removedFields.contains("systemAudioCaptureSession.rawAudio"))
        XCTAssertTrue(result.removedFields.contains("captureHealthSnapshot.meetingContent"))
    }
}
#endif
