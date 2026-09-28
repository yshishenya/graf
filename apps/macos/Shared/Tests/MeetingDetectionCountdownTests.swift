import AppKit
import XCTest
@testable import TwoBrainRecAppCore
@testable import TwoBrainRecShared

@MainActor
final class MeetingDetectionCountdownTests: XCTestCase {
    func testDelayedPresentationAcceptsLastVisibleInstantAndRemembersOnlyExplicitChoice() throws {
        for action in ["Записать", "Не записывать", "close", "timeout"] {
            for remember in [false, true] {
                let f = try notificationFixture(self)
                let p = f.presenter(initialPlacementDelay: 0.5)
                defer { p.dismissAllCards() }
                let requestedAt = f.now
                var checked = false
                var current = true
                var outcomes: [String] = []
                var persisted: [AutomaticRecordingRule] = []
                func consume(_ label: String, decision: MeetingDetectionPromptDecision) {
                    outcomes.append(label)
                    if let rule = decision.persistedRule { persisted.append(rule) }
                }
                XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting",
                    onStart: { consume("start", decision: .init(action: .start, rememberChoice: checked)) },
                    onDismiss: { outcomes.append("close") },
                    onRememberChoiceChanged: { checked = $0 },
                    isStillCurrent: { current },
                    onExpire: { consume("timeout", decision: .init(action: .timeout, rememberChoice: checked)) },
                    onSkip: { consume("skip", decision: .init(action: .skip, rememberChoice: $0)) },
                    onInvalidated: { outcomes.append("invalidated") }))
                let visibleAt = f.now
                XCTAssertEqual(visibleAt, requestedAt.addingTimeInterval(0.5))
                XCTAssertEqual(p.card.deadline, visibleAt.addingTimeInterval(8))
                let buttons = notificationButtons(p.card.window?.contentView)
                let start = try startButton(p)
                let skip = try XCTUnwrap(buttons.first { $0.title == "Не записывать" })
                let close = try XCTUnwrap(buttons.first { $0.toolTip == "Закрыть уведомление" })
                let checkbox = try XCTUnwrap(buttons.first { $0.title.hasPrefix("Запомнить выбор") })
                for second in 1...7 { f.now = visibleAt.addingTimeInterval(Double(second)); p.card.refresh() }
                f.now = visibleAt.addingTimeInterval(7.999)
                p.card.refresh()
                XCTAssertEqual(p.card.presentedContent,
                    .recordingPrompt(displayName: "Test meeting", remainingSeconds: 1, rememberChoice: false))
                let contentView = try XCTUnwrap(p.card.window?.contentView)
                XCTAssertTrue(F277CardTestSupport.labels(contentView).contains {
                    $0.stringValue == "Запись начнётся через 1 секунду"
                })
                if remember { checkbox.performClick(nil) }
                XCTAssertEqual(checked, remember, "Флажок работает до конца видимых восьми секунд")
                XCTAssertEqual(p.card.deadline, visibleAt.addingTimeInterval(8), "Флажок не продлевает срок")
                XCTAssertTrue(outcomes.isEmpty)
                switch action {
                case "Записать": start.performClick(nil)
                case "Не записывать": skip.performClick(nil)
                case "close": close.performClick(nil)
                default: f.now = visibleAt.addingTimeInterval(8); p.card.refresh()
                }
                let expected = action == "Записать" ? "start" : action == "Не записывать" ? "skip" : action
                XCTAssertEqual(outcomes, [expected])
                XCTAssertEqual(persisted, remember && expected == "start" ? [.always]
                    : remember && expected == "skip" ? [.never] : [])
                XCTAssertFalse(p.card.isVisible)
                current = false
                // Old controls and late timer cannot produce a second decision.
                start.performClick(nil); skip.performClick(nil); checkbox.performClick(nil); close.performClick(nil)
                f.now = visibleAt.addingTimeInterval(9); p.card.refresh()
                XCTAssertEqual(outcomes, [expected])
            }
        }
    }

    func testDelayedPromptUsesCurrentOfferValidatorAtTickActionAndExpiry() throws {
        for boundary in ["tick", "action", "expiry"] {
            let f = try notificationFixture(self)
            let p = f.presenter(initialPlacementDelay: 0.5)
            defer { p.dismissAllCards() }
            var current = true
            var invalidated = 0
            XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting",
                onStart: { XCTFail("Устаревшее предложение не начинает запись") },
                onDismiss: {}, onRememberChoiceChanged: { _ in },
                isStillCurrent: { current },
                onExpire: { XCTFail("Устаревшее предложение не запускается по таймеру") },
                onInvalidated: { invalidated += 1 }))
            let visibleAt = f.now
            let button = try startButton(p)
            for second in 1...7 { f.now = visibleAt.addingTimeInterval(Double(second)); p.card.refresh() }
            current = false
            f.now = visibleAt.addingTimeInterval(boundary == "expiry" ? 8 : 7.999)
            if boundary == "action" { button.performClick(nil) } else { p.card.refresh() }
            XCTAssertEqual(invalidated, 1)
            XCTAssertFalse(p.card.isVisible)
            button.performClick(nil); p.card.refresh()
            XCTAssertEqual(invalidated, 1)
        }
    }

    func testStartReasonsRemainDistinctAndTruthful() {
        XCTAssertEqual(MeetingDetectionStartReason.promptButton.rawValue, "prompt_button")
        XCTAssertEqual(MeetingDetectionStartReason.promptTimeout.rawValue, "prompt_timeout")
        XCTAssertEqual(MeetingDetectionStartReason.savedTargetPolicy.rawValue, "saved_target_policy")
        XCTAssertFalse(MeetingDetectionStartReason.promptButton.isAutomatic)
        XCTAssertTrue(MeetingDetectionStartReason.promptTimeout.isAutomatic)
        XCTAssertTrue(MeetingDetectionStartReason.savedTargetPolicy.isAutomatic)
    }

    func testActionAndTickOrdersAtExactVisibleDeadlineResolveOnceWithoutRemembering() throws {
        for actionFirst in [false, true] {
            for action in ["Записать", "Не записывать", "Запомнить выбор"] {
                let f = try notificationFixture(self)
                let p = f.presenter(initialPlacementDelay: 0.5)
                defer { p.dismissAllCards() }
                var outcomes: [String] = []
                var persisted: AutomaticRecordingRule?
                XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting", rememberChoice: true,
                    onStart: { outcomes.append("start"); persisted = .always },
                    onDismiss: { outcomes.append("close") },
                    onRememberChoiceChanged: { _ in outcomes.append("checkbox") },
                    onExpire: {
                        outcomes.append("timeout")
                        persisted = MeetingDetectionPromptDecision(action: .timeout, rememberChoice: true).persistedRule
                    },
                    onSkip: { _ in outcomes.append("skip"); persisted = .never },
                    onInvalidated: { outcomes.append("invalidated") }))
                let visibleAt = f.now
                let button = try XCTUnwrap(notificationButtons(p.card.window?.contentView)
                    .first { $0.title.hasPrefix(action) })
                for second in 1...7 { f.now = visibleAt.addingTimeInterval(Double(second)); p.card.refresh() }
                f.now = visibleAt.addingTimeInterval(8)
                if actionFirst { button.performClick(nil); p.card.refresh() }
                else { p.card.refresh(); button.performClick(nil) }
                // Strict deadline: an expired action cancels; timer-first expires.
                XCTAssertEqual(outcomes, [actionFirst ? "invalidated" : "timeout"])
                XCTAssertNil(persisted)
                XCTAssertFalse(p.card.isVisible)
                button.performClick(nil); p.card.refresh()
                XCTAssertEqual(outcomes, [actionFirst ? "invalidated" : "timeout"])
            }
        }
    }

    func testReplacementDuringOfferValidationCannotConsumeOrInvalidateNewPrompt() throws {
        for boundary in ["tick", "action", "expiry"] {
            let f = try notificationFixture(self)
            let p = f.presenter(initialPlacementDelay: 0.5)
            defer { p.dismissAllCards() }
            var replace = false
            var newStarts = 0
            XCTAssertTrue(p.presentRecordingPrompt(displayName: "Old",
                onStart: { XCTFail("Старый Start не выполняется") }, onDismiss: {},
                onRememberChoiceChanged: { _ in },
                isStillCurrent: {
                    if replace {
                        replace = false
                        p.dismissRecordingPrompt()
                        XCTAssertTrue(p.presentRecordingPrompt(displayName: "New",
                            onStart: { newStarts += 1 }, onDismiss: {}, onRememberChoiceChanged: { _ in }))
                    }
                    return true
                },
                onExpire: { XCTFail("Старый timeout не выполняется") }))
            let oldButton = try startButton(p)
            let visibleAt = f.now
            for second in 1...7 { f.now = visibleAt.addingTimeInterval(Double(second)); p.card.refresh() }
            replace = true
            f.now = visibleAt.addingTimeInterval(boundary == "expiry" ? 8 : 7.999)
            if boundary == "action" { oldButton.performClick(nil) } else { p.card.refresh() }
            XCTAssertEqual(p.card.presentedContent,
                           .recordingPrompt(displayName: "New", remainingSeconds: 8, rememberChoice: false))
            oldButton.performClick(nil)
            XCTAssertEqual(newStarts, 0)
            try startButton(p).performClick(nil)
            XCTAssertEqual(newStarts, 1)
        }
    }

    func testTimeoutDoesNotResolveBeforeEightSecondsAndResolvesOnceAtBoundary() throws {
        let f = try notificationFixture(self)
        let p = f.presenter()
        defer { p.dismissAllCards() }
        let start = f.now
        var reasons: [MeetingDetectionStartReason] = []
        XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting",
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
            XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting",
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
                XCTAssertTrue(p.presentRecordingPrompt(displayName: "Test meeting",
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
