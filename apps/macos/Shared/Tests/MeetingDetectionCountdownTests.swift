import AppKit
import XCTest
@testable import TwoBrainRecAppCore
@testable import TwoBrainRecShared

@MainActor
final class MeetingDetectionCountdownTests: XCTestCase {
    func testStartReasonsRemainDistinctAndTruthful() {
        XCTAssertEqual(MeetingDetectionStartReason.promptButton.rawValue, "prompt_button")
        XCTAssertEqual(MeetingDetectionStartReason.promptTimeout.rawValue, "prompt_timeout")
        XCTAssertEqual(MeetingDetectionStartReason.savedTargetPolicy.rawValue, "saved_target_policy")
        XCTAssertFalse(MeetingDetectionStartReason.promptButton.isAutomatic)
        XCTAssertTrue(MeetingDetectionStartReason.promptTimeout.isAutomatic)
        XCTAssertTrue(MeetingDetectionStartReason.savedTargetPolicy.isAutomatic)
    }

    func testTimeoutDoesNotResolveBeforeEightSecondsAndResolvesOnceAtBoundary() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let start = f.now
        var reasons: [MeetingDetectionStartReason] = []
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting", remainingSeconds: 8,
            onStart: { reasons.append(.promptButton) }, onDismiss: {}, onRememberChoiceChanged: { _ in },
            onExpire: { reasons.append(.promptTimeout) }))
        XCTAssertEqual(p.card.presentedContent,
                       .recordingPrompt(displayName: "Test meeting", remainingSeconds: 8, rememberChoice: false))
        let oldStart = try startButton(p)
        for second in 1...7 { f.now = start.addingTimeInterval(Double(second)); p.card.refresh() }
        f.now = start.addingTimeInterval(7.999); p.card.refresh()
        XCTAssertTrue(reasons.isEmpty)
        XCTAssertEqual(p.card.presentedContent,
                       .recordingPrompt(displayName: "Test meeting", remainingSeconds: 1, rememberChoice: false))
        f.now = start.addingTimeInterval(8); p.card.refresh()
        XCTAssertEqual(reasons, [.promptTimeout])
        XCTAssertNil(p.card.presentedContent)
        oldStart.performClick(nil)
        f.now = start.addingTimeInterval(9); p.card.refresh()
        XCTAssertEqual(reasons, [.promptTimeout])
    }

    func testButtonResolvesImmediatelyAndCancellationPreventsLateStart() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        var reasons: [MeetingDetectionStartReason] = [], closes = 0
        func present() {
            XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting", remainingSeconds: 8,
                onStart: { reasons.append(.promptButton) }, onDismiss: { closes += 1 },
                onRememberChoiceChanged: { _ in }, onExpire: { reasons.append(.promptTimeout) }))
        }
        present()
        f.now = f.now.addingTimeInterval(1); p.card.refresh()
        let button = try startButton(p)
        button.performClick(nil); button.performClick(nil)
        XCTAssertEqual(reasons, [.promptButton])
        XCTAssertNil(p.card.presentedContent)
        for _ in 1...9 { f.now = f.now.addingTimeInterval(1); p.card.refresh() }
        XCTAssertEqual(reasons, [.promptButton])

        present()
        let cancelledStart = try startButton(p)
        let close = try XCTUnwrap(notificationButtons(p.card.window?.contentView)
            .first { $0.toolTip == "Закрыть уведомление" })
        close.performClick(nil); close.performClick(nil); cancelledStart.performClick(nil)
        for _ in 1...9 { f.now = f.now.addingTimeInterval(1); p.card.refresh() }
        XCTAssertEqual(closes, 1)
        XCTAssertEqual(reasons, [.promptButton])
        XCTAssertNil(p.card.presentedContent)
    }

    func testPromptDecisionPersistsOnlyExplicitButtonChoices() {
        XCTAssertNil(MeetingDetectionPromptDecision(action: .skip, rememberChoice: false).persistedRule)
        XCTAssertEqual(
            MeetingDetectionPromptDecision(action: .start, rememberChoice: false).persistedRule,
            nil
        )
        XCTAssertEqual(
            MeetingDetectionPromptDecision(action: .start, rememberChoice: true).persistedRule,
            .always
        )
        XCTAssertEqual(
            MeetingDetectionPromptDecision(action: .skip, rememberChoice: false).persistedRule,
            nil
        )
        XCTAssertEqual(
            MeetingDetectionPromptDecision(action: .skip, rememberChoice: true).persistedRule,
            .never
        )
        XCTAssertNil(MeetingDetectionPromptDecision(action: .timeout, rememberChoice: false).persistedRule)
        XCTAssertNil(MeetingDetectionPromptDecision(action: .timeout, rememberChoice: true).persistedRule)
    }

    func testStartAndTimeoutConsumersRecheckCurrentCaptureAdmission() throws {
        // Exercise the real presenter and capture gate together. This does not
        // invoke TwoBrainRecApp's executable-only handler or start audio capture.
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        for reason in [MeetingDetectionStartReason.promptButton, .promptTimeout] {
            for initiallyAllowed in [false, true] {
                var permissionGranted = initiallyAllowed
                var evaluated: [RecordingPrerequisiteSnapshot] = []
                var accepted: [MeetingDetectionStartReason] = []
                func consume(_ event: MeetingDetectionStartReason) {
                    let result = RecordingPrerequisiteGate().evaluate(.init(
                        policyAllowsRecording: true, microphonePermissionGranted: true,
                        systemAudioPermissionGranted: permissionGranted, storageRisk: .healthy,
                        indicatorAvailable: true, sourceAppEligibility: .eligible, evaluatedAt: f.now))
                    evaluated.append(result)
                    if result.allowsRecording { accepted.append(event) }
                }
                XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting", remainingSeconds: 8,
                    onStart: { consume(.promptButton) }, onDismiss: {}, onRememberChoiceChanged: { _ in },
                    onExpire: { consume(.promptTimeout) }))
                let button = try startButton(p)
                permissionGranted.toggle()
                if reason == .promptButton {
                    f.now = f.now.addingTimeInterval(1); p.card.refresh()
                    button.performClick(nil)
                } else {
                    for _ in 1...8 { f.now = f.now.addingTimeInterval(1); p.card.refresh() }
                }
                XCTAssertEqual(evaluated.count, 1)
                XCTAssertEqual(evaluated.first?.evaluatedAt, f.now)
                XCTAssertEqual(evaluated.first?.allowsRecording, !initiallyAllowed)
                XCTAssertEqual(accepted, initiallyAllowed ? [] : [reason])
                XCTAssertNil(p.card.presentedContent)
                button.performClick(nil)
                for _ in 1...9 { f.now = f.now.addingTimeInterval(1); p.card.refresh() }
                XCTAssertEqual(evaluated.count, 1)
            }
        }
    }

    private func startButton(_ presenter: DesktopNotificationPresenter) throws -> NSButton {
        try XCTUnwrap(notificationButtons(presenter.card.window?.contentView).first { $0.title == "Записать" })
    }
}
