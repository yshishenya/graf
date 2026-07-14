import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class CaptureControlTests: XCTestCase {
    func testCaptureFailedStartBlockerIsSerializable() {
        XCTAssertEqual(RecordingStartBlocker.captureFailed.rawValue, "capture_failed")
    }

    func testActiveCaptureKeepsVisibleIndicatorAndStopAvailable() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 10) },
            idFactory: { "capture-test-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        let active = try controller.markCapturing()

        XCTAssertEqual(active.visibleIndicatorState, .active)
        XCTAssertTrue(active.stopActionAvailable)
    }

    func testStartingCaptureIsVisibleWhileRuntimeAndWriterStart() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 11) },
            idFactory: { "capture-starting-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        let starting = try controller.start()

        XCTAssertEqual(starting.state, .starting)
        XCTAssertEqual(starting.visibleIndicatorState, .ready)
        XCTAssertTrue(starting.stopActionAvailable)
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: starting))
        XCTAssertFalse(CaptureStatusItem.shouldEnableStopButton(for: starting, stopDisabled: true))
    }

    func testManualStopMovesActiveSessionToStoppedWithReason() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 20) },
            idFactory: { "capture-stop-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        _ = try controller.markCapturing()
        let stopping = try controller.requestStop(reason: .userRequested)
        let stopped = try controller.completeStop()

        XCTAssertEqual(stopping.state, .stopping)
        XCTAssertTrue(stopping.stopActionAvailable)
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: stopping))
        XCTAssertFalse(CaptureStatusItem.showsStopAction(for: stopping))
        XCTAssertEqual(stopped.state, .stopped)
        XCTAssertEqual(stopped.stopReason, .userRequested)
        XCTAssertFalse(stopped.stopActionAvailable)
    }

    func testPauseAndResumeKeepStopAvailable() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 22) },
            idFactory: { "capture-pause-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        _ = try controller.markCapturing()
        let paused = try controller.pause()
        let resumed = try controller.resume()

        XCTAssertEqual(paused.state, .paused)
        XCTAssertEqual(paused.visibleIndicatorState, .paused)
        XCTAssertTrue(paused.stopActionAvailable)
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: paused))
        XCTAssertFalse(CaptureStatusItem.showsPauseButton(for: paused))
        XCTAssertTrue(CaptureStatusItem.showsResumeButton(for: paused))
        XCTAssertTrue(CaptureStatusItem.shouldEnableResumeButton(for: paused, pauseDisabled: false))
        XCTAssertEqual(resumed.state, .active)
        XCTAssertTrue(CaptureStatusItem.showsPauseButton(for: resumed))
    }

    func testStopFailureMovesSessionOutOfStoppingState() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 21) },
            idFactory: { "capture-stop-failed-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        _ = try controller.markCapturing()
        _ = try controller.requestStop(reason: .userRequested)
        let failed = try controller.fail(stopReason: .failed, failureCategory: .storageUnsafe)

        XCTAssertEqual(failed.state, .failed)
        XCTAssertEqual(failed.visibleIndicatorState, .error)
        XCTAssertFalse(failed.stopActionAvailable)
        XCTAssertEqual(failed.failureCategory, .storageUnsafe)
    }

    func testBlockedManualStartRecordsFailureCategory() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 30) },
            idFactory: { "capture-blocked-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        let blocked = try controller.blockStart(
            reason: .captureUnavailable,
            recoveryAction: "Retry current capture setup"
        )

        XCTAssertEqual(blocked.state, .failed)
        XCTAssertEqual(blocked.failureCategory, .captureUnavailable)
        XCTAssertEqual(blocked.triggerEvidence["blockedReason"], "capture_unavailable")
        XCTAssertEqual(blocked.triggerEvidence["recoveryAction"], "Retry current capture setup")
        XCTAssertFalse(blocked.stopActionAvailable)
    }

    func testBlockedOrFailedSessionAllowsRecordRetry() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 31) },
            idFactory: { "capture-retry-id" },
            policySnapshotProvider: { "policy-test" }
        )

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        let blocked = try controller.blockStart(
            reason: .permissionDenied,
            recoveryAction: "Grant permissions, then retry recording"
        )

        XCTAssertFalse(CaptureStatusItem.showsStopButton(for: blocked))
        XCTAssertTrue(CaptureControlView.shouldShowRecordButton(for: blocked))
        XCTAssertTrue(CaptureControlView.shouldEnableRecordButton(for: blocked, recordDisabled: false))

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
    }

    func testPreparingSessionShowsReadinessWithoutStop() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 32) },
            idFactory: { "capture-detecting-id" },
            policySnapshotProvider: { "policy-test" }
        )

        let detecting = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)

        XCTAssertEqual(CaptureStatusItem.statusLabel(for: detecting), "Проверяем готовность")
        XCTAssertFalse(CaptureStatusItem.showsStopButton(for: detecting))
        XCTAssertTrue(CaptureControlView.shouldShowRecordButton(for: detecting))
        XCTAssertFalse(CaptureControlView.shouldEnableRecordButton(for: detecting, recordDisabled: true))
    }

    func testCapturePresentationCoversReadyPermissionDetectedRecordingAndSavedStates() {
        XCTAssertEqual(
            CaptureControlView.primaryStatus(
                for: nil,
                blockedReason: nil,
                localRecordingStatus: nil
            ),
            "Готово к записи"
        )
        XCTAssertEqual(
            CaptureControlView.primaryStatus(
                for: nil,
                blockedReason: "Нужен доступ к микрофону. Откройте настройки.",
                localRecordingStatus: nil
            ),
            "Нужно разрешение"
        )
        XCTAssertTrue(CaptureControlView.hasActionableProblem(
            blockedReason: "Нужен доступ к микрофону"
        ))
        XCTAssertFalse(CaptureControlView.shouldShowIdleStatus(
            blockedReason: "Нужен доступ к микрофону",
            localRecordingStatus: nil,
            calendarPrompt: nil
        ))
        XCTAssertFalse(CaptureControlView.shouldShowIdleStatus(
            blockedReason: nil,
            localRecordingStatus: "Локальная запись сохранена",
            calendarPrompt: nil
        ))
        XCTAssertTrue(CaptureControlView.shouldShowIdleStatus(
            blockedReason: nil,
            localRecordingStatus: nil,
            calendarPrompt: nil
        ))
        let recordPrompt = DesktopCalendarPrompt(
            id: "record-prompt",
            kind: .record,
            eventId: "event",
            title: "Встреча обнаружена",
            message: "Начать запись?",
            primaryActionTitle: "Начать запись",
            accessibilityLabel: "Обнаружена встреча"
        )
        XCTAssertFalse(CaptureControlView.shouldShowIdleStatus(
            blockedReason: nil,
            localRecordingStatus: nil,
            calendarPrompt: recordPrompt
        ))
        XCTAssertFalse(CaptureControlView.shouldShowDirectRecordButton(
            for: nil,
            calendarPrompt: recordPrompt
        ))
        XCTAssertTrue(CaptureControlView.shouldShowDirectRecordButton(
            for: nil,
            calendarPrompt: nil
        ))
        let activeSession = makePresentationSession(
            state: .active,
            indicator: .active,
            canStop: true
        )
        XCTAssertTrue(CaptureControlView.shouldShowSessionStatus(
            for: activeSession,
            blockedReason: "Запись продолжается с ограничением"
        ))
        XCTAssertFalse(CaptureControlView.shouldShowLocalRecordingStatus(
            "Локальная запись идёт",
            for: activeSession
        ))
        let savedSession = makePresentationSession(
            state: .finalized,
            indicator: .hidden,
            canStop: false
        )
        XCTAssertFalse(CaptureControlView.shouldShowLocalRecordingStatus(
            "Локальная запись сохранена",
            for: savedSession
        ))
        XCTAssertTrue(CaptureControlView.shouldShowLocalRecordingStatus(
            "Локальная запись сохранена с ограничениями",
            for: savedSession
        ))
        let failedSession = makePresentationSession(
            state: .failed,
            indicator: .error,
            canStop: false
        )
        XCTAssertFalse(CaptureControlView.shouldShowSessionStatus(
            for: failedSession,
            blockedReason: "Не удалось начать запись"
        ))
        XCTAssertEqual(
            CaptureControlView.meetingDetectionSummary(for: "Найдена встреча: Яндекс Телемост"),
            "Встреча обнаружена"
        )
        XCTAssertEqual(
            CaptureControlView.meetingDetectionSummary(for: "Запрашивать запись включено"),
            "Автоопределение: спрашивать"
        )
        XCTAssertEqual(
            CaptureControlView.primaryStatus(
                for: makePresentationSession(state: .active, indicator: .active, canStop: true),
                blockedReason: nil,
                localRecordingStatus: nil
            ),
            "Идёт запись"
        )
        XCTAssertEqual(
            CaptureControlView.primaryStatus(
                for: makePresentationSession(state: .paused, indicator: .paused, canStop: true),
                blockedReason: nil,
                localRecordingStatus: nil
            ),
            "Запись на паузе"
        )
        XCTAssertEqual(
            CaptureControlView.primaryStatus(
                for: makePresentationSession(state: .stopping, indicator: .active, canStop: true),
                blockedReason: nil,
                localRecordingStatus: nil
            ),
            "Сохраняем запись…"
        )
        XCTAssertEqual(
            CaptureStatusItem.statusLabel(
                for: makePresentationSession(state: .stopped, indicator: .hidden, canStop: false)
            ),
            "Сохранено на Mac"
        )
        XCTAssertEqual(
            CaptureControlView.primaryStatus(
                for: makePresentationSession(state: .stopped, indicator: .hidden, canStop: false),
                blockedReason: nil,
                localRecordingStatus: nil
            ),
            "Сохранено на Mac"
        )
        XCTAssertEqual(
            CaptureControlView.primaryStatus(
                for: nil,
                blockedReason: nil,
                localRecordingStatus: "Локальная запись сохранена"
            ),
            "Сохранено на Mac"
        )
    }

    func testCaptureMetersAreVisibleOnlyWhileRecordingLevelsAreActive() throws {
        let activeLevels = LiveRecordingLevels(
            isRecording: true,
            microphoneLevel: 0.4,
            incomingLevel: 0.7,
            microphoneUpdatedAt: Date(),
            incomingUpdatedAt: Date()
        )
        XCTAssertFalse(CaptureControlView.shouldShowMeters(for: .inactive))
        XCTAssertTrue(CaptureControlView.shouldShowMeters(for: activeLevels))

        let source = try String(
            contentsOf: repositoryRootForCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureControlView.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(source.contains("if Self.shouldShowMeters(for: recordingLevels)"))
    }

    func testOrdinaryCaptureSurfaceDoesNotRenderDebugOrReportInputs() throws {
        let source = try String(
            contentsOf: repositoryRootForCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureControlView.swift"),
            encoding: .utf8
        )
        let bodyStart = try XCTUnwrap(source.range(of: "public var body: some View"))
        let helpersStart = try XCTUnwrap(source.range(of: "public static func shouldShowRecordButton"))
        let ordinaryBody = source[bodyStart.lowerBound..<helpersStart.lowerBound]

        for forbidden in [
            "meetingDetectionHealth",
            "appleProcessingStatus",
            "webRTCAEC3Status",
            "localRecordingLocation",
            "UploadQueueStatusView",
            "onSupportIncidentReport"
        ] {
            XCTAssertFalse(ordinaryBody.contains(forbidden), forbidden)
        }
        XCTAssertFalse(source.contains("appleProcessingStatusCopy"))
        XCTAssertTrue(source.contains("resolvedWebRTCAEC3Status"))
        XCTAssertFalse(ordinaryBody.contains("HStack(alignment: .top, spacing: 18)"))
        XCTAssertTrue(
            ordinaryBody.contains(
                ".frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.controlHeight)"
            )
        )
        XCTAssertFalse(ordinaryBody.contains("Spacer(minLength: 0)"))
    }

    func testMeetingDetectionControlsExposeStatusAndSettingsAccessibility() throws {
        let label = SystemAudioStatusLabels.meetingDetectionAccessibilityLabel(
            status: "detect_and_ask",
            health: "ok"
        )
        let root = try repositoryRootForCaptureTests()
        let settingsSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift"),
            encoding: .utf8
        )

        XCTAssertEqual(SystemAudioAccessibilityIdentifier.meetingDetectionStatus, "systemAudio.meetingDetection.status")
        XCTAssertEqual(
            SystemAudioAccessibilityIdentifier.meetingDetectionSettingsButton,
            "systemAudio.meetingDetection.settingsButton"
        )
        XCTAssertEqual(
            SystemAudioAccessibilityIdentifier.meetingDetectionRecordingToggle,
            "systemAudio.meetingDetection.recordingToggle"
        )
        XCTAssertTrue(label.contains(SystemAudioStatusLabels.meetingDetectionSettingsTitle))
        XCTAssertTrue(label.contains("detect_and_ask"))
        XCTAssertTrue(settingsSource.contains("MeetingDetectionSettingsView"))
        XCTAssertTrue(settingsSource.contains("promptToggleTitle = \"Запрашивать запись\""))
        XCTAssertTrue(settingsSource.contains("Toggle(\"\", isOn: recordingPromptBinding)"))
        XCTAssertTrue(settingsSource.contains("ForEach(promptCapableTargets"))
        XCTAssertTrue(settingsSource.contains("selectAllAutoRecordTargets"))
        XCTAssertTrue(settingsSource.contains("clearAutoRecordTargets"))
        XCTAssertTrue(settingsSource.contains("SystemAudioAccessibilityIdentifier.meetingDetectionRecordingToggle"))
        XCTAssertTrue(settingsSource.contains(".twoBrainRecMeetingTargetRegistryDidChange"))

        let controlsSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureControlView.swift"),
            encoding: .utf8
        )
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        let appSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )
        XCTAssertTrue(controlsSource.contains("onMeetingDetectionSettings"))
        XCTAssertTrue(controlsSource.contains("Image(systemName: \"gearshape\")"))
        XCTAssertTrue(controlsSource.contains("meetingDetectionSettingsButton"))
        XCTAssertTrue(shellSource.contains("settingsRailLabel = \"Настройки\""))
        XCTAssertFalse(shellSource.contains("desktop-meeting-shell-settings-button"))
        XCTAssertTrue(shellSource.contains("desktop-meeting-shell-expanded-settings-button"))
        XCTAssertTrue(appSource.contains("(NSApp.delegate as? AppLifecycleDelegate)?.openSettings(nil)"))
    }

    func testMeetingDetectionPrerequisiteDoesNotUseStopInProgressAsIndicatorAvailability() throws {
        let source = try String(
            contentsOf: repositoryRootForCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("indicatorAvailable: meetingDetectionVisibleIndicatorAvailable"))
        XCTAssertFalse(source.contains("indicatorAvailable: meetingDetectionOneActionStopAvailable"))
    }

    func testMeetingDetectionPromptUsesFloatingCountdownInsteadOfMainSheet() throws {
        let source = try String(
            contentsOf: repositoryRootForCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("presentMeetingDetectionPrompt(prompt)"))
        XCTAssertTrue(source.contains("NSPanel("))
        XCTAssertTrue(source.contains("window.level = .statusBar"))
        XCTAssertTrue(source.contains("window.hidesOnDeactivate = false"))
        XCTAssertTrue(source.contains("meetingDetectionPromptWindowSize = NSSize(width: 360, height: 286)"))
        XCTAssertTrue(source.contains("window.setContentSize(promptWindowSize)"))
        XCTAssertTrue(source.contains("meetingDetectionPromptScreen()"))
        XCTAssertTrue(source.contains("NSEvent.mouseLocation"))
        XCTAssertTrue(source.contains("NSMouseInRect(mouseLocation, $0.frame, false)"))
        XCTAssertTrue(source.contains("visibleFrame.insetBy"))
        XCTAssertTrue(source.contains("clamp(safeFrame.midX - width / 2"))
        XCTAssertTrue(source.contains("window.setFrame(frame, display: true)"))
        XCTAssertTrue(source.contains("orderFrontRegardless()"))
        XCTAssertTrue(source.contains("Task { @MainActor [weak window]"))
        XCTAssertTrue(source.contains("meeting_detection.prompt_presented"))
        XCTAssertTrue(source.contains("meeting_detection.prompt_accepted"))
        XCTAssertTrue(source.contains("TimelineView(.periodic"))
        XCTAssertTrue(source.contains("Запись стартует автоматически"))
        XCTAssertTrue(source.contains("Режим: аудиозапись встречи"))
        XCTAssertTrue(source.contains("Источники: системный звук и микрофон"))
        XCTAssertTrue(source.contains("Политика: запись разрешена"))
        XCTAssertTrue(source.contains("Сигнал: приложение использует аудио встречи"))
        XCTAssertTrue(source.contains("Всегда писать это приложение"))
        XCTAssertTrue(source.contains("Пропустить"))
        XCTAssertFalse(source.contains(".sheet(item: $meetingDetectionPrompt)"))
    }

    func testMeetingDetectionEndStopsMatchingDetectedRecording() throws {
        let source = try String(
            contentsOf: repositoryRootForCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("stopMeetingDetectionRecordingIfNeeded(bundleID: bundleID)"))
        XCTAssertTrue(source.contains("session.triggerEvidence[\"meetingDetectionBundleId\"] == bundleID"))
        XCTAssertTrue(source.contains("CaptureStatusItem.showsStopButton(for: session)"))
        XCTAssertTrue(source.contains("reason: .meetingEnded"))
        XCTAssertTrue(source.contains("evidenceInitiator: .systemFailClosed"))
        XCTAssertTrue(source.contains("enqueueReason: \"meeting_detection_target_ended\""))
    }

    func testCalendarPromptUIWiresManualPrimaryAndDismissActions() throws {
        let source = try String(
            contentsOf: repositoryRootForCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureControlView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(source.contains("CalendarPromptView("))
        XCTAssertTrue(source.contains("onCalendarPromptPrimary"))
        XCTAssertTrue(source.contains("onCalendarPromptDismiss"))
        XCTAssertTrue(source.contains("ForEach(prompt.choices)"))
        XCTAssertTrue(source.contains("selectedPrompt.eventId = choice.eventId"))
        XCTAssertTrue(source.contains("SystemAudioAccessibilityIdentifier.calendarPromptPrimaryButton"))
        XCTAssertTrue(source.contains("SystemAudioAccessibilityIdentifier.calendarPromptDismissButton"))
        XCTAssertFalse(source.contains("calendarPrompt") && source.contains(".task { await startManualRecording() }"))
    }

    func testCalendarPromptSelectionProducesResolveCommandWithEventID() throws {
        let command = try XCTUnwrap(
            DesktopCalendarResolvePolicy.commandAfterCaptureStarted(
                localRecordingActive: true,
                localRecordingId: "synthetic-calendar-recording",
                recordingStartedAt: Date(timeIntervalSince1970: 98),
                decisionIntent: .userSelected,
                eventId: "synthetic-calendar-event"
            )
        )

        XCTAssertEqual(command.localRecordingId, "synthetic-calendar-recording")
        XCTAssertEqual(command.decisionIntent, .userSelected)
        XCTAssertEqual(command.eventId, "synthetic-calendar-event")
    }

    // FR-032, FR-049, SC-010: synthetic calendar resolution stays behind visible capture truth.
    func testCalendarResolveRemainsNonBlockingAndStopStaysAvailable() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 98) },
            idFactory: { "synthetic-calendar-capture" },
            policySnapshotProvider: { "synthetic-policy" }
        )
        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        let active = try controller.markCapturing()
        let beforeCapture = DesktopCalendarResolvePolicy.commandAfterCaptureStarted(
            localRecordingActive: false,
            localRecordingId: "synthetic-calendar-capture",
            recordingStartedAt: Date(timeIntervalSince1970: 98),
            decisionIntent: .automatic,
            eventId: nil
        )
        let afterCapture = DesktopCalendarResolvePolicy.commandAfterCaptureStarted(
            localRecordingActive: true,
            localRecordingId: "synthetic-calendar-capture",
            recordingStartedAt: Date(timeIntervalSince1970: 98),
            decisionIntent: .automatic,
            eventId: nil
        )

        XCTAssertTrue(active.stopActionAvailable)
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: active))
        XCTAssertNil(beforeCapture)
        XCTAssertEqual(afterCapture?.decisionIntent, .automatic)
    }

    // FR-032 and plan performance gate: calendar resolution cannot delay upload startup.
    func testCalendarResolveCannotGateUploadQueueProcessing() throws {
        let source = try String(
            contentsOf: repositoryRootForCaptureTests()
                .appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertFalse(source.contains("shouldWaitForCalendarResolve"))
        XCTAssertFalse(source.contains("if !shouldWaitForCalendarResolve"))
        XCTAssertTrue(source.contains("refreshUploadQueueAndProcess(reason: \"enqueue_\\(reason)\")"))
    }

    func testCaptureControlsCanShowMuteTruthWarningWithoutBlockingStop() {
        let session = CaptureSession(
            id: "warning-session",
            mode: .audioRecording,
            state: .active,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: [:],
            visibleIndicatorState: .active,
            stopActionAvailable: true,
            bufferSummaryId: nil,
            startedAt: nil,
            stoppedAt: nil
        )

        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: false))
        XCTAssertTrue(CaptureStatusItem.shouldEnablePauseButton(for: session, pauseDisabled: false))
        XCTAssertFalse(SystemAudioStatusLabels.meetingMuteTruthLimitationCopy.isEmpty)
    }

    func testWebRTCAEC3StatusCopyCoversEvaluationFallbackRollbackAndAttentionStates() throws {
        let cases: [(WebRTCAEC3AppStatusState, String, String, String)] = [
            (.evaluatingAEC3, "Проверяем AEC3", "исходному микрофону", "waveform.and.mic"),
            (.usingOriginalMicTruth, "Исходный микрофон", "источником правды", "mic.fill"),
            (.candidateBlocked, "AEC3 не включен", "исходному микрофону", "exclamationmark.triangle"),
            (.promotedBuiltinRoute, "AEC3 подтвержден", "проверками", "checkmark.shield"),
            (.rolledBackToOriginal, "AEC3 откатился", "исходному микрофону", "arrow.uturn.backward.circle"),
            (.fallbackRelevant, "Используем фолбэк", "исходный микрофон", "arrow.triangle.2.circlepath"),
            (.requiresUserAttention, "Нужна проверка AEC3", "не повышаем", "exclamationmark.triangle.fill")
        ]

        for (state, title, detailFragment, iconName) in cases {
            let status = controlWebRTCAEC3Status(state: state)
            let copy = try XCTUnwrap(CaptureControlView.webRTCAEC3StatusCopy(for: status), state.rawValue)

            XCTAssertEqual(CaptureControlView.webRTCAEC3StatusTitle(for: state), title)
            XCTAssertTrue(copy.contains(detailFragment), "\(state.rawValue): \(copy)")
            XCTAssertEqual(CaptureControlView.webRTCAEC3StatusIconName(for: state), iconName)
            XCTAssertTrue(CaptureControlView.webRTCAEC3StatusCopyIsClaimSafe(copy, state: state))
        }
    }

    func testWebRTCAEC3StatusPriorityIsCalmAndDoesNotHideStop() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 24) },
            idFactory: { "aec3-status-session" },
            policySnapshotProvider: { "policy-test" }
        )
        let rollbackStatus = controlWebRTCAEC3Status(state: .rolledBackToOriginal)

        _ = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        _ = try controller.markReady()
        _ = try controller.start()
        _ = try controller.markCapturing()
        let activeWithStatus = try controller.updateWebRTCAEC3Status(rollbackStatus)

        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: activeWithStatus))
        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: activeWithStatus, stopDisabled: false))
        XCTAssertEqual(activeWithStatus.webRTCAEC3Status, rollbackStatus)
        XCTAssertEqual(CaptureControlView.webRTCAEC3StatusAccessibilityIdentifier(for: .rolledBackToOriginal), SystemAudioAccessibilityIdentifier.webRTCAEC3RollbackStatus)
        XCTAssertGreaterThan(
            CaptureControlView.webRTCAEC3StatusPriority(for: .requiresUserAttention),
            CaptureControlView.webRTCAEC3StatusPriority(for: .fallbackRelevant)
        )
        XCTAssertGreaterThan(
            CaptureControlView.webRTCAEC3StatusPriority(for: .rolledBackToOriginal),
            CaptureControlView.webRTCAEC3StatusPriority(for: .candidateBlocked)
        )
        XCTAssertFalse(CaptureControlView.webRTCAEC3StatusIsNoisyAlert(for: controlWebRTCAEC3Status(state: .fallbackRelevant)))
        XCTAssertFalse(CaptureControlView.webRTCAEC3StatusIsNoisyAlert(for: rollbackStatus))
    }

    func testWebRTCAEC3BlockedAndUnprovenCopyNeverClaimsCleanRecording() throws {
        let statuses = [
            controlWebRTCAEC3Status(state: .evaluatingAEC3),
            controlWebRTCAEC3Status(state: .usingOriginalMicTruth),
            controlWebRTCAEC3Status(state: .candidateBlocked),
            controlWebRTCAEC3Status(state: .rolledBackToOriginal),
            controlWebRTCAEC3Status(state: .fallbackRelevant),
            controlWebRTCAEC3Status(state: .requiresUserAttention, matchesPackageTruth: false)
        ]
        let forbiddenClaimWords = ["clean", "чист", "не попадает", "без эха"]

        for status in statuses {
            let copy = try XCTUnwrap(CaptureControlView.webRTCAEC3StatusCopy(for: status), status.state.rawValue)
            for word in forbiddenClaimWords {
                XCTAssertFalse(copy.localizedCaseInsensitiveContains(word), "\(status.state.rawValue) contained \(word): \(copy)")
            }
        }
    }

    func testWebRTCAEC3StatusResolverPrefersLiveSessionStatusOverCompletedManifest() throws {
        let liveStatus = controlWebRTCAEC3Status(state: .rolledBackToOriginal)
        let session = CaptureSession(
            id: "aec3-live-status",
            mode: .audioRecording,
            state: .active,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: [:],
            visibleIndicatorState: .active,
            stopActionAvailable: true,
            bufferSummaryId: nil,
            startedAt: Date(timeIntervalSince1970: 1),
            stoppedAt: nil,
            webRTCAEC3Status: liveStatus
        )
        let manifest = controlManifest(webRTCAEC3Outcome: controlWebRTCAEC3Outcome(primaryOutcome: .deferToFallbackDecision))

        let resolved = CaptureControlView.resolvedWebRTCAEC3Status(for: session, manifest: manifest)

        XCTAssertEqual(resolved, liveStatus)
        XCTAssertEqual(CaptureControlView.webRTCAEC3StatusTitle(for: resolved?.state ?? .notEvaluated), "AEC3 откатился")
    }

    func testWebRTCAEC3StatusResolverShowsFallbackFromCompletedManifest() throws {
        let manifest = controlManifest(webRTCAEC3Outcome: controlWebRTCAEC3Outcome(primaryOutcome: .deferToFallbackDecision))

        let resolved = try XCTUnwrap(CaptureControlView.resolvedWebRTCAEC3Status(for: nil, manifest: manifest))
        let copy = try XCTUnwrap(CaptureControlView.webRTCAEC3StatusCopy(for: resolved))

        XCTAssertEqual(resolved.state, .fallbackRelevant)
        XCTAssertEqual(resolved.routeScope, .builtInMacMicAndSpeakers)
        XCTAssertEqual(CaptureControlView.webRTCAEC3StatusTitle(for: resolved.state), "Используем фолбэк")
        XCTAssertEqual(
            CaptureControlView.webRTCAEC3StatusAccessibilityIdentifier(for: resolved.state),
            SystemAudioAccessibilityIdentifier.webRTCAEC3FallbackStatus
        )
        XCTAssertTrue(copy.localizedCaseInsensitiveContains("фолбэк"))
        XCTAssertTrue(CaptureControlView.webRTCAEC3StatusCopyIsClaimSafe(copy, state: resolved.state))
    }

    func testWebRTCAEC3StatusResolverDoesNotPromoteIncompleteImmediateOutcome() throws {
        let manifest = controlManifest(webRTCAEC3Outcome: controlWebRTCAEC3Outcome(primaryOutcome: .acceptedForImmediatePromotion))

        let resolved = try XCTUnwrap(CaptureControlView.resolvedWebRTCAEC3Status(for: nil, manifest: manifest))
        let copy = try XCTUnwrap(CaptureControlView.webRTCAEC3StatusCopy(for: resolved))

        XCTAssertFalse(manifest.webRTCAEC3Outcome?.canClaimCleanBuiltInSpeakerphone ?? true)
        XCTAssertEqual(resolved.state, .requiresUserAttention)
        XCTAssertEqual(CaptureControlView.webRTCAEC3StatusTitle(for: resolved.state), "Нужна проверка AEC3")
        XCTAssertFalse(copy.localizedCaseInsensitiveContains("подтвержден"))
        XCTAssertTrue(CaptureControlView.webRTCAEC3StatusCopyIsClaimSafe(copy, state: resolved.state))
    }

    func testRecordingMicrophoneStatusNamesSelectedAndDefaultInput() {
        let selected = controlRecordingMicrophoneSelection(
            mode: .userSelected,
            name: "USB Microphone"
        )
        let fallback = controlRecordingMicrophoneSelection(
            mode: .macOSDefaultFallback,
            name: "MacBook Pro Microphone"
        )

        XCTAssertEqual(
            CaptureControlView.recordingMicrophoneStatus(for: selected),
            "Микрофон записи: USB Microphone"
        )
        XCTAssertEqual(
            CaptureControlView.recordingMicrophoneStatus(for: fallback),
            "Микрофон записи: MacBook Pro Microphone (по умолчанию macOS)"
        )
    }

    func testRecordingMicrophoneRecoveryCopyRejectsVirtualInputs() {
        let rejected = RecordingMicrophoneSelection(
            selectionId: "rejected",
            mode: .userSelected,
            inputDeviceId: "virtual-input",
            inputDisplayName: "Loopback Virtual Audio",
            deviceClass: .otherVirtual,
            workingDeviceKind: .otherVirtual,
            selectionResult: .rejected,
            rejectionReason: .unsupportedVirtualInput,
            resolvedAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertEqual(
            CaptureControlView.recordingMicrophoneRecoveryCopy(for: rejected),
            "Выберите встроенный, USB, проводной или Bluetooth-микрофон для записи."
        )
    }

    func testTrackEvidenceUsesCurrentSession() throws {
        let controller = CaptureSessionController(
            clock: { Date(timeIntervalSince1970: 10) },
            idFactory: { "track-test-id" },
            policySnapshotProvider: { "policy-test" }
        )

        let session = try controller.beginPreparing(mode: .audioRecording, sourceAppEligibility: .eligible)
        let track = try controller.makeTrackEvidence(role: .localMic)

        XCTAssertEqual(track.sessionId, session.id)
        XCTAssertEqual(track.role, .localMic)
        XCTAssertEqual(track.state, .capturing)
    }

    func testUploadSummaryUsesCustodyCopyForAutomaticWait() {
        let queued = uploadItem(id: "queued", state: .queued, updatedAt: Date(timeIntervalSince1970: 20))
        let retrying = uploadItem(id: "retrying", state: .retrying, updatedAt: Date(timeIntervalSince1970: 30))

        let summary = DesktopUploadCustodySummary.summary(for: [queued, retrying])

        XCTAssertEqual(summary?.primaryItem.id, "retrying")
        XCTAssertEqual(summary?.pendingCount, 2)
        XCTAssertEqual(summary?.title, "Записи сохранены")
        XCTAssertEqual(summary?.detail, "Отправим автоматически, когда сервер будет доступен.")
    }

    func testQueuedLocalOnlyUploadCopyDoesNotClaimServerReviewExists() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let queued = uploadItem(id: "queued-local", state: .queued, updatedAt: Date(timeIntervalSince1970: 20))

        let summary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [queued]))

        XCTAssertEqual(summary.title, "Запись сохранена")
        XCTAssertEqual(summary.detail, "Отправим автоматически, когда сервер будет доступен.")
        XCTAssertEqual(configuration.reviewLink(for: queued).availability, .unavailable)
    }

    func testBlockedLocalUploadCopyDoesNotTreatAudioQualityAsHardGate() throws {
        let blocked = uploadItem(
            id: "blocked-local",
            state: .blocked,
            updatedAt: Date(timeIntervalSince1970: 20),
            failureReason: LocalRecordingFailureReason.leakageDetected.rawValue,
            retryMode: .manualOnly
        )

        let summary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [blocked]))

        XCTAssertEqual(summary.title, "Запись сохранена")
        XCTAssertEqual(summary.detail, "Отправим автоматически, когда сервер будет доступен.")
        XCTAssertNil(summary.primaryItem.nextActionLabel)
    }

    func testUploadStatusDoesNotExposeRetryControlsToNormalUser() throws {
        let manual = uploadItem(
            id: "manual-blocked",
            state: .blocked,
            updatedAt: Date(timeIntervalSince1970: 20),
            failureReason: "local_recording_package_not_uploadable",
            retryMode: .manualOnly
        )
        let automatic = uploadItem(
            id: "automatic-retrying",
            state: .retrying,
            updatedAt: Date(timeIntervalSince1970: 21),
            retryMode: .automatic
        )

        let manualSummary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [manual]))
        let automaticSummary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [automatic]))

        XCTAssertNil(manualSummary.primaryItem.nextActionLabel)
        XCTAssertNil(automaticSummary.primaryItem.nextActionLabel)
    }

    func testUploadSummaryProgressOnlyAppearsForActiveUpload() throws {
        let queued = uploadItem(id: "queued", state: .queued, updatedAt: Date(timeIntervalSince1970: 20))
        let uploading = uploadItem(
            id: "uploading",
            state: .uploading,
            updatedAt: Date(timeIntervalSince1970: 21),
            serverTruth: ServerTruthFingerprint(acceptedBytesByTrack: ["microphone": 64])
        )

        let queuedSummary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [queued]))
        let uploadingSummary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [uploading]))

        XCTAssertFalse(queuedSummary.showsProgress)
        XCTAssertTrue(uploadingSummary.showsProgress)
        XCTAssertGreaterThan(uploadingSummary.progressFraction, 0)
        XCTAssertEqual(uploadingSummary.title, "Отправляем запись")
    }

    func testUploadSummaryAccessibilityUsesCustodyLanguage() throws {
        let auth = uploadItem(
            id: "auth-required",
            state: .blocked,
            updatedAt: Date(timeIntervalSince1970: 20),
            failureReason: "auth_required",
            retryMode: .manualOnly,
            syncConflictState: .authRequired
        )

        let summary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [auth]))

        XCTAssertTrue(summary.accessibilityLabel.contains("Доверие записи"))
        XCTAssertTrue(summary.accessibilityLabel.contains("Нужен вход"))
        XCTAssertTrue(summary.accessibilityLabel.contains("Владелец встречи"))
        XCTAssertFalse(summary.accessibilityLabel.localizedCaseInsensitiveContains("очеред"))
        XCTAssertFalse(summary.accessibilityLabel.localizedCaseInsensitiveContains("retry"))
        XCTAssertFalse(summary.accessibilityLabel.localizedCaseInsensitiveContains("повтор"))
    }

    func testUploadSummaryExposesSafeReportForSupportAction() throws {
        let blocked = uploadItem(
            id: "support-blocked",
            state: .blocked,
            updatedAt: Date(timeIntervalSince1970: 20),
            failureReason: "/Users/private/recording.wav Bearer leaked-token",
            retryMode: .manualOnly,
            syncConflictState: .serverMeetingDeleted
        )

        let summary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [blocked]))
        let report = try XCTUnwrap(summary.safeReport)

        XCTAssertEqual(report.normalUserAction, .sendSupportReport)
        XCTAssertFalse(report.clipboardText.contains("/Users/private"))
        XCTAssertFalse(report.clipboardText.contains("Bearer"))
    }

    func testSupportIncidentActionCopyUsesRequiredSuccessAndFailureText() {
        let sent = DesktopSupportIncidentSubmissionState.sent(
            reportFingerprint: "report_fpr_test",
            dedupeKey: "support_dedupe_test",
            incidentNumber: "CUST-123",
            githubIssueNumber: 123,
            attemptedAt: Date(timeIntervalSince1970: 1),
            copyFallbackAvailable: true
        )
        let failed = DesktopSupportIncidentSubmissionState.failedWithCopyFallback(
            reportFingerprint: "report_fpr_test",
            dedupeKey: "support_dedupe_test",
            attemptedAt: Date(timeIntervalSince1970: 1),
            failureCategory: "network",
            failureCode: "support_incident.github_unavailable"
        )

        XCTAssertEqual(
            DesktopSupportIncidentActionCopy.visibleMessage(for: sent),
            DesktopSupportIncidentFixture.successMessage
        )
        XCTAssertEqual(
            DesktopSupportIncidentActionCopy.visibleMessage(for: failed),
            DesktopSupportIncidentFixture.failureMessage
        )
        XCTAssertEqual(DesktopSupportIncidentActionCopy.sendTitle, DesktopSupportIncidentFixture.supportTitle)
    }

    func testSupportIncidentSuccessWithoutNumberDoesNotExposePlaceholderIdentifier() {
        let sentWithoutNumber = DesktopSupportIncidentSubmissionState(
            state: .sent,
            localReportFingerprint: "report_fpr_test",
            dedupeKey: "support_dedupe_test",
            incidentNumber: nil,
            githubIssueNumber: nil,
            lastSubmissionAttemptAt: Date(timeIntervalSince1970: 1)
        )

        XCTAssertEqual(
            DesktopSupportIncidentActionCopy.visibleMessage(for: sentWithoutNumber),
            "Запрос отправлен в поддержку."
        )
        XCTAssertEqual(sentWithoutNumber.accessibilityLabel, "Запрос отправлен в поддержку.")
        XCTAssertFalse(
            DesktopSupportIncidentActionCopy.visibleMessage(for: sentWithoutNumber)?.contains("?") == true
        )
    }

    func testCompactCustodySurfaceUsesAccessibleSupportIncidentActions() throws {
        let root = try repositoryRootForCaptureTests()
        let stripSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift"),
            encoding: .utf8
        )
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(shellSource.contains("if meetingOwnerCustodyActionCount > 0"))
        XCTAssertTrue(shellSource.contains("DesktopSupportIncidentActionStrip("))
        XCTAssertTrue(shellSource.contains("onSubmit: onSupportIncidentReport"))
        XCTAssertTrue(stripSource.contains("Label(sendButtonTitle, systemImage: \"questionmark.bubble\")"))
        XCTAssertTrue(stripSource.contains(".accessibilityLabel(DesktopSupportIncidentActionCopy.sendTitle)"))
        XCTAssertFalse(stripSource.contains("Скопировать отчет"))
        XCTAssertFalse(stripSource.contains("Отправить отчет"))
        XCTAssertTrue(stripSource.contains("lineLimit(3)"))
        XCTAssertTrue(stripSource.contains("fixedSize(horizontal: false, vertical: true)"))
    }

    func testConflictStateCopyIsSafeAndActionable() throws {
        let deleted = uploadItem(
            id: "deleted-conflict",
            state: .blocked,
            updatedAt: Date(timeIntervalSince1970: 20),
            failureReason: "/Users/test/private/package/mic.wav",
            retryMode: .manualOnly,
            syncConflictState: .serverMeetingDeleted
        )
        let auth = uploadItem(
            id: "auth-conflict",
            state: .blocked,
            updatedAt: Date(timeIntervalSince1970: 21),
            failureReason: "auth_required",
            retryMode: .manualOnly,
            syncConflictState: .authRequired
        )

        let deletedSummary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [deleted]))
        let authSummary = try XCTUnwrap(DesktopUploadCustodySummary.summary(for: [auth]))

        XCTAssertEqual(
            deletedSummary.detail,
            "Проверьте доступ к рабочему пространству или обратитесь к администратору."
        )
        XCTAssertFalse(deletedSummary.detail.contains("/Users/test"))
        XCTAssertFalse(deletedSummary.detail.localizedCaseInsensitiveContains("отчет"))
        XCTAssertFalse(deletedSummary.detail.localizedCaseInsensitiveContains("диагност"))
        XCTAssertNil(deletedSummary.primaryItem.nextActionLabel)
        XCTAssertEqual(authSummary.detail, "Войдите, чтобы продолжить отправку. Локальные копии сохранены.")
        XCTAssertNil(authSummary.primaryItem.nextActionLabel)
    }

    func testCustodyFallbackCopyKeepsDiagnosticsOutOfTheUserInterface() {
        let copyKeys = [
            "custody.needs_admin",
            "custody.cannot_send",
            "custody.terminal_undelivered",
            "custody.unknown_blocked",
        ]

        for copyKey in copyKeys {
            let detail = DesktopUploadCustodyCopy.detail(
                copyKey: copyKey,
                count: 1,
                deadline: nil
            )
            XCTAssertFalse(detail.localizedCaseInsensitiveContains("отчет"), copyKey)
            XCTAssertFalse(detail.localizedCaseInsensitiveContains("диагност"), copyKey)
            XCTAssertFalse(detail.localizedCaseInsensitiveContains("телеметр"), copyKey)
        }
    }

    func testUploadReviewActionIsAvailableOnlyForUploadedServerIdentifiedItem() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let uploaded = uploadItem(
            id: "uploaded",
            state: .uploaded,
            updatedAt: Date(timeIntervalSince1970: 30),
            serverTruth: ServerTruthFingerprint(
                meetingId: "server-meeting-033",
                mediaRevisionId: "server-media-revision-033",
                processingStatus: "processed"
            )
        )
        let queued = uploadItem(id: "queued", state: .queued, updatedAt: Date(timeIntervalSince1970: 20))

        let link = configuration.reviewLink(for: uploaded)
        XCTAssertEqual(link.availability, .available)
        XCTAssertEqual(link.mediaRevisionId, "server-media-revision-033")
        XCTAssertEqual(configuration.reviewLink(for: queued).availability, .unavailable)
    }

    private func uploadItem(
        id: String,
        state: UploadItemState,
        updatedAt: Date,
        failureReason: String? = nil,
        retryMode: UploadRetryMode = .automatic,
        serverTruth: ServerTruthFingerprint = ServerTruthFingerprint(),
        syncConflictState: DesktopSyncConflictState = .none
    ) -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            manifestPresent: true,
            microphonePresent: true,
            systemAudioPresent: true,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: String(repeating: "b", count: 64),
            systemAudioSha256: String(repeating: "c", count: 64),
            manifestSizeBytes: 64,
            microphoneSizeBytes: 128,
            systemAudioSizeBytes: 128,
            durationSeconds: 1,
            trackCompleteness: [],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: id,
            sessionId: "session-\(id)",
            directoryId: "directory-\(id)",
            directoryPath: "/tmp/\(id)",
            manifestPath: "/tmp/\(id)/manifest.json",
            microphonePath: "/tmp/\(id)/mic.wav",
            systemAudioPath: "/tmp/\(id)/incoming.wav",
            state: state,
            failureReason: failureReason,
            retryMode: retryMode,
            retentionDeadline: Date(timeIntervalSince1970: 1_800_000_000),
            createdAt: Date(timeIntervalSince1970: 1),
            updatedAt: updatedAt,
            syncConflictState: syncConflictState,
            artifactProfile: profile,
            serverTruth: serverTruth,
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: Date(timeIntervalSince1970: 1),
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
    }
}

private func makePresentationSession(
    state: CaptureSessionState,
    indicator: VisibleIndicatorState,
    canStop: Bool
) -> CaptureSession {
    CaptureSession(
        id: "presentation-\(state.rawValue)",
        mode: .audioRecording,
        state: state,
        sourceAppEligibility: .eligible,
        policySnapshotRef: "policy",
        triggerEvidence: [:],
        visibleIndicatorState: indicator,
        stopActionAvailable: canStop,
        bufferSummaryId: nil,
        startedAt: Date(timeIntervalSince1970: 1_000),
        stoppedAt: nil
    )
}

private func repositoryRootForCaptureTests() throws -> URL {
    var candidate = URL(fileURLWithPath: #filePath)
    while candidate.path != "/" {
        let appSourceURL = candidate.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
        if FileManager.default.fileExists(atPath: appSourceURL.path) {
            return candidate
        }
        candidate.deleteLastPathComponent()
    }
    throw NSError(
        domain: "CaptureControlTests",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
    )
}

private func controlRecordingMicrophoneSelection(
    mode: RecordingMicrophoneSelectionMode,
    name: String
) -> RecordingMicrophoneSelection {
    RecordingMicrophoneSelection(
        selectionId: "control-selection-\(mode.rawValue)",
        mode: mode,
        inputDeviceId: "control-input",
        inputDisplayName: name,
        deviceClass: .builtIn,
        workingDeviceKind: .physical,
        selectionResult: .accepted,
        resolvedAt: Date(timeIntervalSince1970: 10)
    )
}

private func controlAppleOutcome(
    state: AppleProcessingOutcomeState,
    nextStep: AppleProcessingNextStepRecommendation,
    failureReason: String
) -> AppleProcessingOutcome {
    AppleProcessingOutcome(
        candidateId: "apple-\(state.rawValue)",
        primaryOutcome: state,
        validationRows: [
            AppleProcessingValidationRow(
                candidateId: "apple-\(state.rawValue)",
                candidateKind: state == .acceptedForGuidanceOnly ? .micModeGuidance : .appOwnedGraphVoiceProcessing,
                routeClass: .builtInSpeakerphone,
                scenario: .routeChange,
                baselineStatus: .degraded,
                candidateStatus: .unproven,
                lineageStatus: state == .acceptedForGuidanceOnly ? .guidanceOnly : .unproven,
                speechPreservationStatus: .notMeasured,
                alignmentStatus: .notMeasured,
                stabilityStatus: .unproven,
                diagnosticSafe: true,
                failureReason: failureReason
            )
        ],
        nextStepRecommendation: nextStep,
        failureReason: failureReason
    )
}

private func controlWebRTCAEC3Status(
    state: WebRTCAEC3AppStatusState,
    matchesPackageTruth: Bool = true
) -> AppRecordingStatus {
    AppRecordingStatus(
        statusId: "status-\(state.rawValue)",
        candidateId: "aec3-\(state.rawValue)",
        state: state,
        routeScope: state == .promotedBuiltinRoute ? .builtInMacMicAndSpeakers : .notApplicable,
        copySafety: .safe,
        actionHint: state == .requiresUserAttention ? .reviewStatus : .continueRecording,
        matchesPackageTruth: matchesPackageTruth,
        diagnosticSafe: true
    )
}

private func controlManifest(webRTCAEC3Outcome: WebRTCAEC3DecisionRecord?) -> LocalRecordingManifest {
    LocalRecordingManifest(
        sessionId: "manifest-aec3-status",
        createdAt: Date(timeIntervalSince1970: 1),
        startedAt: Date(timeIntervalSince1970: 2),
        stoppedAt: Date(timeIntervalSince1970: 3),
        status: .degraded,
        directoryId: "manifest-dir",
        tracks: [],
        webRTCAEC3Outcome: webRTCAEC3Outcome
    )
}

private func controlWebRTCAEC3Outcome(primaryOutcome: WebRTCAEC3OutcomeState) -> WebRTCAEC3DecisionRecord {
    WebRTCAEC3DecisionRecord(
        candidateId: "aec3-\(primaryOutcome.rawValue)",
        primaryOutcome: primaryOutcome,
        validationRows: [
            WebRTCAEC3ValidationRow(
                rowId: "row-\(primaryOutcome.rawValue)",
                candidateId: "aec3-\(primaryOutcome.rawValue)",
                scenarioFamily: .farEndOnlyLeakage,
                validationKind: .fullFile,
                routeClass: .builtInSpeakerphone,
                baselineStatus: .leakageDetected,
                candidateStatus: .blocked,
                lineageStatus: .originalOnly,
                speechPreservationStatus: .notMeasured,
                residualLeakageStatus: .unproven,
                timingConfidence: .notMeasured,
                referenceStatus: .present,
                stabilityStatus: .unproven,
                thresholdProfileId: WebRTCAEC3AcceptanceThresholdProfile.standardV1.thresholdProfileId,
                thresholdSummary: primaryOutcome.rawValue,
                appStatusState: .candidateBlocked,
                diagnosticSafe: true
            )
        ],
        nextStepRecommendation: primaryOutcome == .deferToFallbackDecision ? .fallbackDecision : .guidanceOnly,
        diagnosticSafe: true,
        fallbackFeatureId: primaryOutcome == .deferToFallbackDecision ? "040-speakerphone-recording-fallback-decision" : nil,
        failureReason: primaryOutcome.rawValue
    )
}
#endif
