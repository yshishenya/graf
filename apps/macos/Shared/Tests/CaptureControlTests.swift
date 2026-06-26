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
            reason: .routeNotReady,
            recoveryAction: "Refresh local audio status before recording"
        )

        XCTAssertEqual(blocked.state, .failed)
        XCTAssertEqual(blocked.failureCategory, .routeNotReady)
        XCTAssertEqual(blocked.triggerEvidence["blockedReason"], "route_not_ready")
        XCTAssertEqual(blocked.triggerEvidence["recoveryAction"], "Refresh local audio status before recording")
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

    func testAppleProcessingStatusCopyForGuidanceBlockedAndUnprovenDoesNotClaimCleanRecording() throws {
        let outcomes = [
            controlAppleOutcome(state: .acceptedForGuidanceOnly, nextStep: .guidanceOnly, failureReason: AppleProcessingFailureReason.userSystemControlled.rawValue),
            controlAppleOutcome(state: .blockedRouteTopology, nextStep: .deferToWebRTCAEC3, failureReason: AppleProcessingFailureReason.routeTopologyBlocked.rawValue),
            controlAppleOutcome(state: .deferToWebRTCAEC3, nextStep: .deferToWebRTCAEC3, failureReason: AppleProcessingFailureReason.processingUnavailable.rawValue)
        ]

        for outcome in outcomes {
            let copy = try XCTUnwrap(CaptureControlView.appleProcessingStatusCopy(for: outcome))

            XCTAssertFalse(copy.localizedCaseInsensitiveContains("чист"))
            XCTAssertFalse(copy.localizedCaseInsensitiveContains("clean"))
            XCTAssertTrue(copy.contains("Apple"))
        }
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
            inputDeviceId: SelfRoutingGuard.microphoneUID,
            inputDisplayName: SelfRoutingGuard.microphoneDisplayName,
            deviceClass: .otherVirtual,
            workingDeviceKind: .twoBrainVirtual,
            selectionResult: .rejected,
            rejectionReason: .unsupportedSelfRoutingInput,
            resolvedAt: Date(timeIntervalSince1970: 10)
        )

        XCTAssertEqual(
            CaptureControlView.recordingMicrophoneRecoveryCopy(for: rejected),
            "Выберите обычный микрофон. Виртуальные устройства 2brain нельзя использовать как микрофон записи."
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

        let summary = CaptureControlView.uploadSummary(for: [queued, retrying])

        XCTAssertEqual(summary?.primaryItem.id, "retrying")
        XCTAssertEqual(summary?.pendingCount, 2)
        XCTAssertEqual(summary?.title, "Записи сохранены")
        XCTAssertEqual(summary?.detail, "Отправим автоматически, когда сервер будет доступен.")
    }

    func testQueuedLocalOnlyUploadCopyDoesNotClaimServerReviewExists() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let queued = uploadItem(id: "queued-local", state: .queued, updatedAt: Date(timeIntervalSince1970: 20))

        let summary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [queued]))

        XCTAssertEqual(summary.title, "Запись сохранена")
        XCTAssertEqual(summary.detail, "Отправим автоматически, когда сервер будет доступен.")
        XCTAssertNil(CaptureControlView.uploadReviewLink(for: queued, configuration: configuration))
    }

    func testBlockedLocalUploadCopyDoesNotTreatAudioQualityAsHardGate() throws {
        let blocked = uploadItem(
            id: "blocked-local",
            state: .blocked,
            updatedAt: Date(timeIntervalSince1970: 20),
            failureReason: LocalRecordingFailureReason.leakageDetected.rawValue,
            retryMode: .manualOnly
        )

        let summary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [blocked]))

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

        let manualSummary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [manual]))
        let automaticSummary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [automatic]))

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

        let queuedSummary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [queued]))
        let uploadingSummary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [uploading]))

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

        let summary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [auth]))

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

        let summary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [blocked]))
        let report = try XCTUnwrap(summary.safeReport)

        XCTAssertEqual(report.normalUserAction, .copySafeReport)
        XCTAssertFalse(report.clipboardText.contains("/Users/private"))
        XCTAssertFalse(report.clipboardText.contains("Bearer"))
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

        let deletedSummary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [deleted]))
        let authSummary = try XCTUnwrap(CaptureControlView.uploadSummary(for: [auth]))

        XCTAssertEqual(deletedSummary.detail, "Локальные копии сохранены. Можно скопировать безопасный отчет.")
        XCTAssertFalse(deletedSummary.detail.contains("/Users/test"))
        XCTAssertNil(deletedSummary.primaryItem.nextActionLabel)
        XCTAssertEqual(authSummary.detail, "Войдите, чтобы продолжить отправку. Локальные копии сохранены.")
        XCTAssertNil(authSummary.primaryItem.nextActionLabel)
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

        let link = CaptureControlView.uploadReviewLink(for: uploaded, configuration: configuration)
        XCTAssertEqual(link?.availability, .available)
        XCTAssertEqual(link?.mediaRevisionId, "server-media-revision-033")
        XCTAssertNil(CaptureControlView.uploadReviewLink(for: queued, configuration: configuration))
        XCTAssertNil(CaptureControlView.uploadReviewLink(for: uploaded, configuration: nil))
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
