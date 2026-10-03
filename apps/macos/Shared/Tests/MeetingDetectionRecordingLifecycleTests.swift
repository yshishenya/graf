import Foundation
import XCTest

final class MeetingDetectionRecordingLifecycleTests: XCTestCase {
    func testAutomaticRecordingKeepsDeferredEndSnapshotRecoveryAndManualSuppression() throws {
        let source = try Self.desktopAppSource()

        XCTAssertTrue(source.contains("pendingMeetingDetectionStopBundleID = bundleID"))
        XCTAssertTrue(source.contains("finishMeetingDetectionStart("))
        XCTAssertTrue(source.contains("meeting_detection_target_ended_during_start"))
        XCTAssertTrue(source.contains("activeMeetingDetectionBundleID == bundleID"))
        XCTAssertTrue(source.contains("reconcileMeetingDetectionRecording("))
        XCTAssertTrue(source.contains("MacOSMeetingActivityDetector.recordingEvidenceExpired("))
        XCTAssertTrue(source.contains("manuallyStoppedMeetingDetectionBundleID = detectorBundleID"))
        XCTAssertTrue(source.contains("manually_stopped_current_meeting"))
        XCTAssertTrue(source.contains("guard activeMeetingDetectionBundleID == bundleID else { return }"))
    }

    func testRegistryUnavailableDoesNotBypassProductionLifecycleAdvance() throws {
        let source = try Self.desktopAppSource()
        let start = try XCTUnwrap(source.range(of: "private func advanceMeetingDetection(reason _: String) async {"))
        let end = try XCTUnwrap(source.range(of: "private func processMeetingDetectionOutputs(", range: start.upperBound..<source.endIndex))
        let advance = String(source[start.upperBound..<end.lowerBound])
        XCTAssertTrue(advance.contains("let registry = meetingDetectionRegistry"))
        XCTAssertTrue(advance.contains("meetingDetectionDetector.advance("))
        XCTAssertTrue(advance.contains("processMeetingDetectionOutputs(outputs, registry: registry)"))
        XCTAssertFalse(advance.contains("guard let registry"))
        XCTAssertTrue(source.contains("registry: MeetingTargetRegistryDocument?"))
        XCTAssertTrue(source.contains("} else {\n            meetingDetectionDetector.reconcile(event: event)"))
    }

    private static func desktopAppSource() throws -> String {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let sourceURL = candidate.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
            if FileManager.default.fileExists(atPath: sourceURL.path) {
                return try String(contentsOf: sourceURL, encoding: .utf8)
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "MeetingDetectionRecordingLifecycleTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
