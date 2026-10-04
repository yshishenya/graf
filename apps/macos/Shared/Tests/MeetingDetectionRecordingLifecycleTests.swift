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

    func testAuthAndRegistryDismissalRearmOnlyTheOutstandingPrompt() throws {
        let source = try Self.desktopAppSource()
        for signature in ["private func invalidateMeetingDetectionRegistryForAuthChange() {",
                          "private func refreshMeetingDetectionRegistry(reason: String) async {"] {
            let start = try XCTUnwrap(source.range(of: signature))
            let end = source.range(of: "\n    @MainActor", range: start.upperBound..<source.endIndex)?.lowerBound ?? source.endIndex
            XCTAssertTrue(source[start.upperBound..<end].contains("dismissMeetingDetectionPrompt(retryableReason: \"registry_unavailable\")"))
        }
        let start = try XCTUnwrap(source.range(of: "private func dismissMeetingDetectionPrompt("))
        let end = try XCTUnwrap(source.range(of: "private func dismissMeetingDetectionPrompt(\n", range: start.upperBound..<source.endIndex))
        let helper = String(source[start.lowerBound..<end.lowerBound])
        XCTAssertTrue(helper.contains("retryableReason: String? = nil"))
        XCTAssertTrue(helper.contains("if let retryableReason"))
        XCTAssertTrue(helper.contains("outcome: .retryable(reason: retryableReason)"))
        let outcome = try XCTUnwrap(helper.range(of: "outcome: .retryable"))
        let clear = try XCTUnwrap(helper.range(of: "meetingDetectionPromptToken = nil"))
        XCTAssertLessThan(outcome.lowerBound, clear.lowerBound)
        XCTAssertFalse(helper.contains("meetingDetectionDetector.reset()"))
        let presentation = try XCTUnwrap(source.range(of: "private func presentMeetingDetectionPrompt("))
        let presentationEnd = try XCTUnwrap(source.range(of: "private func isCurrentMeetingDetectionPrompt(", range: presentation.upperBound..<source.endIndex))
        let callback = String(source[presentation.lowerBound..<presentationEnd.lowerBound])
        XCTAssertTrue(callback.contains("let authEpoch = DesktopNotificationPresenter.shared.authEpoch"))
        XCTAssertTrue(callback.contains("if DesktopNotificationPresenter.shared.authEpoch != authEpoch"))
        XCTAssertTrue(callback.contains("self.dismissMeetingDetectionPrompt(retryableReason: \"registry_unavailable\")"))
        XCTAssertTrue(callback.contains("self.dismissMeetingDetectionPrompt(prompt, reason: .invalidated)"))
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
