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
        XCTAssertTrue(source.contains("now.timeIntervalSince(lastMeetingDetectionEvidenceAt) >= 600"))
        XCTAssertTrue(source.contains("manuallyStoppedMeetingDetectionBundleID = detectorBundleID"))
        XCTAssertTrue(source.contains("manually_stopped_current_meeting"))
        XCTAssertTrue(source.contains("guard activeMeetingDetectionBundleID == bundleID else { return }"))
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
