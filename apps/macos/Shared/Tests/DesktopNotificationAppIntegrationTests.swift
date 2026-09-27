import Foundation
import XCTest

/// Executable app entry-point wiring is not imported into the unit-test target.
/// These checks complement the runtime presenter/decision tests, not replace them.
final class DesktopNotificationAppIntegrationTests: XCTestCase {
    private var root: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }

    func testShortRecordingHasOnlyTheSharedDeliveryPath() throws {
        let app = try String(contentsOf: root.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"), encoding: .utf8)
        XCTAssertFalse(app.contains("DesktopRecordingNoticePresenter"))
        XCTAssertTrue(app.contains("DesktopNotificationPresenter.shared.presentShortRecording()"))
        XCTAssertFalse(FileManager.default.fileExists(atPath: root.appendingPathComponent("apps/macos/RecApp/Sources/Notifications/DesktopRecordingNoticePresenter.swift").path))
    }

    func testAppOwnsPromptIdentityAndChecksPresentationFailure() throws {
        let app = try String(contentsOf: root.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"), encoding: .utf8)
        XCTAssertTrue(app.contains("meetingDetectionPromptToken"))
        XCTAssertTrue(app.contains("isCurrentMeetingDetectionPrompt"))
        XCTAssertTrue(app.contains("let shown = DesktopNotificationPresenter.shared.presentRecordingPrompt("))
        XCTAssertTrue(app.contains("guard shown else"))
        XCTAssertFalse(app.contains("_ = DesktopNotificationPresenter.shared.presentRecordingPrompt("))
    }

    func testNoRetiredNotificationNavigationCallbacksRemain() throws {
        for path in ["apps/macos/RecApp/App/TwoBrainRecApp.swift", "apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift", "apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift"] {
            let source = try String(contentsOf: root.appendingPathComponent(path), encoding: .utf8)
            XCTAssertFalse(source.contains("onOpenNotificationSettings"), path)
        }
    }

    func testDetectedStartCommitsAfterRevalidationWithoutAnotherSuspension() throws {
        let app = try String(contentsOf: root.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"), encoding: .utf8)
        let start = try XCTUnwrap(app.range(of: "let directory = try await localRecordingWriter.startAsync("))
        let end = try XCTUnwrap(app.range(of: "captureSession = active", range: start.upperBound..<app.endIndex))
        let boundary = String(app[start.lowerBound..<end.lowerBound])
        XCTAssertTrue(boundary.contains("requiresStartAcceptance: meetingDetectionTarget != nil"))
        let recheck = try XCTUnwrap(boundary.range(of: "!isCurrentMeetingDetectionDecision(meetingDetectionTarget)"))
        let mark = try XCTUnwrap(boundary.range(of: "try captureController.markCapturing()"))
        let accept = try XCTUnwrap(boundary.range(of: "try localRecordingWriter.acceptStart(sessionId: starting.id)"))
        XCTAssertLessThan(recheck.lowerBound, mark.lowerBound)
        XCTAssertLessThan(mark.lowerBound, accept.lowerBound)
        XCTAssertFalse(boundary[recheck.lowerBound...].contains("await"))

        let decisionStart = try XCTUnwrap(app.range(of: "private func isCurrentMeetingDetectionDecision("))
        let decisionEnd = try XCTUnwrap(app.range(of: "private func saveMeetingDetectionRule(", range: decisionStart.upperBound..<app.endIndex))
        let decisionBody = app[decisionStart.lowerBound..<decisionEnd.lowerBound]
        XCTAssertTrue(decisionBody.contains("MeetingDetectionAppModule.allowsPendingStart("))
        XCTAssertTrue(decisionBody.contains("decisionIsCurrent: current == decision"))
        XCTAssertTrue(decisionBody.contains("bundleID: decision.bundleID"))
        XCTAssertTrue(decisionBody.contains("pendingStopBundleID: pendingMeetingDetectionStopBundleID"))
    }

    func testRetirementGuardRunsInTheMacOSTestLane() throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", root.appendingPathComponent("scripts/check_notification_retirement.py").path]
        process.currentDirectoryURL = root
        let output = Pipe()
        process.standardOutput = output
        process.standardError = output
        try process.run()
        let data = output.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        XCTAssertEqual(process.terminationStatus, 0, String(decoding: data, as: UTF8.self))
    }
}
