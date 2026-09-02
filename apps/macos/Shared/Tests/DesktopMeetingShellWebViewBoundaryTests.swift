import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class DesktopMeetingShellWebViewBoundaryTests: XCTestCase {
    func testOnlineProductSidebarIsWebOwnedWhileNativeCaptureChromeRemainsNative() {
        XCTAssertFalse(DesktopMeetingShellChrome.idleShowsNativeTopBar)
        XCTAssertEqual(DesktopMeetingShellChrome.compactRailLabels, ["Статус записи", "Локальная сохранность"])
        XCTAssertGreaterThan(DesktopMeetingShellChrome.recordingStripHeight, 0)
        XCTAssertGreaterThanOrEqual(DesktopMeetingShellChrome.inspectorToggleHitSize, 40)
        XCTAssertFalse(DesktopMeetingShellChrome.shouldShowExpandedInspector(
            manualExpanded: false,
            hasActionableProblem: false
        ))
        XCTAssertTrue(DesktopMeetingShellChrome.shouldShowExpandedInspector(
            manualExpanded: false,
            hasActionableProblem: true
        ))
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: makeActiveSession()))
    }

    func testNativeShellOwnsDirectStartStopAndRecordingDoesNotAutoExpandInspector() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        let appSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(shellSource.contains("startRecordingAvailable"))
        XCTAssertTrue(shellSource.contains("onStartRecording"))
        XCTAssertTrue(shellSource.contains("hasActionableCaptureProblem"))
        XCTAssertTrue(shellSource.contains("desktop-meeting-shell-start-recording-button"))
        XCTAssertTrue(shellSource.contains("desktop-meeting-shell-stop-recording-button"))
        XCTAssertTrue(shellSource.contains("RecordingTitlebarHUD("))
        XCTAssertTrue(shellSource.contains("Label(\"Стоп\", systemImage: \"stop.fill\")"))
        XCTAssertFalse(shellSource.contains("hasActiveRecording: recordingStripSession != nil"))
        XCTAssertTrue(appSource.contains("startRecordingAvailable: CaptureControlView.shouldShowDirectRecordButton"))
        XCTAssertTrue(appSource.contains("calendarPrompt: desktopCalendarPrompt"))
        XCTAssertTrue(appSource.contains("|| desktopCalendarPrompt?.kind == .record"))
        XCTAssertTrue(appSource.contains("onStartRecording:"))
    }

    func testNativeShellWidthAndInteractiveTargetsStayStableAtSupportedSizes() {
        XCTAssertEqual(DesktopMeetingShellChrome.collapsedInspectorWidth, 52)
        XCTAssertTrue((304...312).contains(DesktopMeetingShellChrome.expandedInspectorWidth))
        XCTAssertGreaterThanOrEqual(
            DesktopMeetingShellChrome.compactRailActionHitSize,
            DesktopMeetingShellChrome.minimumInteractiveTarget
        )
        XCTAssertGreaterThanOrEqual(
            DesktopMeetingShellChrome.inspectorToggleHitSize,
            DesktopMeetingShellChrome.minimumInteractiveTarget
        )
        XCTAssertFalse(
            DesktopMeetingShellChrome.shouldShowExpandedInspector(
                manualExpanded: false,
                hasActionableProblem: false
            )
        )
    }

    func testOrdinaryNativeInspectorOmitsPermanentTrustDiagnosticsAndGenericReports() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        let appSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        XCTAssertFalse(shellSource.contains("Label(\"Доверие записи\""))
        XCTAssertFalse(shellSource.contains("Label(\"Диагностика\""))
        XCTAssertFalse(shellSource.contains("diagnosticsContent"))
        XCTAssertFalse(appSource.contains("diagnosticsContent:"))
        XCTAssertTrue(shellSource.contains("if attentionCustodyItemCount > 0"))
        XCTAssertTrue(shellSource.contains("attentionCustodySummaries"))
        XCTAssertTrue(shellSource.contains("primaryProjection.requiresUserAttention"))
        XCTAssertTrue(shellSource.contains(".onChange(of: attentionCustodySignature)"))
        XCTAssertTrue(shellSource.contains("summary.stableIdentity"))
        XCTAssertTrue(shellSource.contains("Требуется внимание"))
        XCTAssertFalse(shellSource.contains("Требуется действие"))
        XCTAssertTrue(shellSource.contains("DesktopSupportIncidentActionStrip("))
    }

    func testRemovedNativeMainWindowFragmentsHaveNoCurrentEntryPoint() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        let captureSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift"),
            encoding: .utf8
        )
        let appSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift"),
            encoding: .utf8
        )

        for forbidden in [
            "localTodayStrip",
            "localTodayTile(",
            "Image(systemName: \"bookmark\")",
            "Image(systemName: \"line.3.horizontal.decrease\")",
            "Image(systemName: \"arrow.up.arrow.down\")",
            "Label(\"Доверие записи\"",
            "Label(\"Диагностика\"",
            "diagnosticsContent"
        ] {
            XCTAssertFalse(shellSource.contains(forbidden), forbidden)
        }
        for forbidden in [
            "private struct UploadQueueStatusView",
            "uploadReviewButtonTitle"
        ] {
            XCTAssertFalse(captureSource.contains(forbidden), forbidden)
        }
        for forbidden in [
            "localRecordingLocation",
            "meetingDetectionHealth",
            "recordingBlocker = \"Не удалось поставить запись на паузу: \\(error)\"",
            "recordingBlocker = \"Не удалось продолжить запись: \\(error)\"",
            "recordingBlocker = \"Не удалось остановить запись: \\(error)\"",
            "default:\n            return action"
        ] {
            XCTAssertFalse(appSource.contains(forbidden), forbidden)
        }
    }

    func testNativeProductSidebarImplementationIsRemovedFromShellSource() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )

        XCTAssertFalse(shellSource.contains("showsNativeProductSidebar"))
        XCTAssertFalse(shellSource.contains("DesktopMeetingShellSidebarItem"))
        XCTAssertFalse(shellSource.contains("selectedSidebarItem"))
        XCTAssertFalse(shellSource.contains("onOpenMeetingsList"))
        XCTAssertFalse(shellSource.contains("onOpenCalendarSettings"))
        XCTAssertFalse(shellSource.contains("private var sidebar"))
        XCTAssertFalse(shellSource.contains("sidebarPlaceholder"))
        XCTAssertFalse(shellSource.contains("menuStatusText"))
    }

    func testActiveRecordingStopBoundaryDoesNotDependOnEmbeddedSurfaceState() {
        let session = makeActiveSession()

        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: session))
        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: false))

        for state in DesktopCabinetState.allCases {
            let invariant = NativeShellInvariant(
                recordVisible: true,
                stopVisible: true,
                uploadTruthVisible: true,
                focusCanReachStop: true,
                embeddedSurfaceLoaded: state.shouldShowEmbeddedSurface
            )

            XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: state), "\(state)")
        }
    }

    func testCalendarSettingsEmbeddedSurfaceKeepsNativeStopReachableDuringActiveRecording() throws {
        let configuration = CalendarSettingsFixtures.cabinetConfiguration()
        let settingsURL = CalendarSettingsFixtures.embeddedCalendarSettingsURL()
        let session = makeActiveSession()
        let invariant = CalendarSettingsFixtures.activeRecordingInvariant(embeddedLoaded: true)
        let decision = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL).decision(for: settingsURL)

        XCTAssertEqual(settingsURL.path, "/desktop/settings/integrations/calendar")
        XCTAssertEqual(decision.decision, .allow)
        XCTAssertEqual(decision.route.kind, .calendarSettings)
        XCTAssertTrue(CaptureStatusItem.showsStopButton(for: session))
        XCTAssertTrue(CaptureStatusItem.shouldEnableStopButton(for: session, stopDisabled: false))
        XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertTrue(invariant.embeddedSurfaceLoaded)
    }

    func testLocalQueueTruthStaysInLocalModeUntilServerMeetingIsConfirmed() {
        let localQueued = makeQueueItem(
            id: "local-queued",
            state: .queued,
            retryMode: .automatic,
            createdAt: Date(timeIntervalSince1970: 30)
        )
        let localUploadedWithoutServerTruth = makeQueueItem(
            id: "local-uploaded-no-server-truth",
            state: .uploaded,
            retryMode: .terminal,
            createdAt: Date(timeIntervalSince1970: 40)
        )
        let serverConfirmed = makeQueueItem(
            id: "server-confirmed",
            state: .uploaded,
            retryMode: .terminal,
            meetingId: "meeting-033",
            serverTruth: ServerTruthFingerprint(meetingId: "meeting-033"),
            createdAt: Date(timeIntervalSince1970: 50)
        )

        let cabinetRows = DesktopMeetingShellLocalQueuePolicy.rowsNeedingNativeVisibility([
            localQueued,
            localUploadedWithoutServerTruth,
            serverConfirmed
        ])

        XCTAssertTrue(cabinetRows.isEmpty)

        let localRows = DesktopMeetingShellLocalQueuePolicy.allRowsForLocalMode([
            localQueued,
            localUploadedWithoutServerTruth
        ])

        XCTAssertEqual(localRows.map(\.id), [
            "local-uploaded-no-server-truth",
            "local-queued"
        ])
    }

    func testEmbeddedLocalRecordingRowsExposeOnlyBoundedCopyAndAllowedActions() throws {
        let playbackRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: playbackRoot, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: playbackRoot) }
        try Data([0]).write(to: playbackRoot.appendingPathComponent("meeting-review.m4a"))
        let saving = makeQueueItem(
            id: "saving-row",
            state: .saving,
            retryMode: .manualOnly,
            createdAt: Date(timeIntervalSince1970: 100)
        )
        var failed = makeQueueItem(
            id: "failed-row",
            state: .blocked,
            retryMode: .manualOnly,
            createdAt: Date(timeIntervalSince1970: 90)
        )
        var playable = makeQueueItem(
            id: "playable-row",
            state: .blocked,
            retryMode: .manualOnly,
            createdAt: Date(timeIntervalSince1970: 80)
        )
        playable.directoryPath = playbackRoot.path
        playable.artifactProfile.trackCompleteness = [
            UploadTrackCompleteness(
                transportRole: .playback,
                fileName: "meeting-review.m4a",
                present: true,
                byteCount: 1,
                sha256: String(repeating: "d", count: 64),
                durationSeconds: 9
            )
        ]
        playable.failureCategory = .localResource
        failed.failureReason = "recording_recovery_not_possible"
        let rows = EmbeddedCabinetLocalRecordingRow.rows(for: [saving, failed, playable])
        let encoded = try JSONEncoder().encode(rows)
        let json = String(decoding: encoded, as: UTF8.self)

        XCTAssertEqual(rows.map(\.status), ["Сохраняется", "Запись повреждена", "Сохранена часть записи"])
        XCTAssertFalse(rows[0].canSend)
        XCTAssertFalse(rows[1].canSend)
        XCTAssertFalse(rows[0].canDelete)
        XCTAssertTrue(rows[1].canDelete)
        XCTAssertTrue(rows[2].canOpen)
        XCTAssertFalse(json.contains("directoryPath"))
        XCTAssertFalse(json.contains("manifestPath"))
        XCTAssertFalse(json.contains("sessionId"))
        XCTAssertNil(EmbeddedCabinetLocalRecordingBridge.allowedAction(
            from: ["action": "send", "id": "saving-row"],
            rows: rows
        ))
        XCTAssertNil(
            EmbeddedCabinetLocalRecordingBridge.allowedAction(
                from: ["action": "delete", "id": "saving-row"],
                rows: rows
            )
        )
        XCTAssertEqual(
            EmbeddedCabinetLocalRecordingBridge.allowedAction(
                from: ["action": "delete", "id": "failed-row"],
                rows: rows
            )?.id,
            "failed-row"
        )
        XCTAssertNil(EmbeddedCabinetLocalRecordingBridge.allowedAction(
            from: ["action": "send", "id": "unknown"],
            rows: rows
        ))
        XCTAssertNil(EmbeddedCabinetLocalRecordingBridge.allowedAction(
            from: ["action": "open_path", "id": "saving-row"],
            rows: rows
        ))
        XCTAssertEqual(
            EmbeddedCabinetLocalRecordingBridge.allowedAction(
                from: ["action": "open", "id": "playable-row"],
                rows: rows
            )?.id,
            "playable-row"
        )
        let rowsScript = EmbeddedCabinetLocalRecordingBridge.rowsScript(rows)
        XCTAssertTrue(rowsScript.contains("TextDecoder('utf-8')"))
        XCTAssertFalse(rowsScript.contains("JSON.parse(atob("))
    }

    func testCabinetListOwnsLocalRecordingStatesAndUsesSendCopy() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let cabinetSource = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
            ),
            encoding: .utf8
        )
        let shellSource = try String(
            contentsOf: root.appendingPathComponent(
                "apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"
            ),
            encoding: .utf8
        )

        XCTAssertTrue(cabinetSource.contains("data-graf-local-recording-row"))
        XCTAssertTrue(cabinetSource.contains("send.textContent = \"Отправить\""))
        XCTAssertTrue(cabinetSource.contains("renderLocalRecordingRows"))
        XCTAssertTrue(cabinetSource.contains("item.uploadComplete !== true"))
        XCTAssertTrue(cabinetSource.contains("data-meeting-open"))
        XCTAssertTrue(cabinetSource.contains("data-icon=\"audio\""))
        XCTAssertFalse(cabinetSource.contains("serverRow.dataset.grafLocalRecordingId"))
        XCTAssertTrue(shellSource.contains("DesktopUploadCustodySummary.summaries(for: uploadQueueItems)"))
    }

    func testOfflineStatesExposeOnlySafeSameOriginRetryFromWorkspace() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))

        for state in [DesktopCabinetState.offline, .timeout, .malformedResponse] {
            XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
                for: state,
                currentRoute: configuration.meetingsURL(),
                initialRoute: nil,
                configuration: configuration
            ), "\(state)")
            XCTAssertEqual(
                DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration),
                .embedded(configuration.meetingsURL()),
                "\(state)"
            )
            XCTAssertEqual(state.recoveryActionTitle, "Повторить", "\(state)")
        }

        XCTAssertNil(DesktopCabinetWorkspace.recoveryTarget(for: .notConfigured, configuration: configuration))
        XCTAssertNil(DesktopCabinetState.notConfigured.recoveryActionTitle)
    }

    func testRightNativeCustodyPanelUsesAccessibleSupportIncidentActions() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let shellSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift"),
            encoding: .utf8
        )
        let stripSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(shellSource.contains("DesktopSupportIncidentActionStrip("))
        XCTAssertTrue(shellSource.contains("ScrollView(.vertical, showsIndicators: true)"))
        XCTAssertTrue(shellSource.contains(".clipped()"))
        XCTAssertTrue(shellSource.contains("NSTitlebarAccessoryViewController()"))
        XCTAssertTrue(shellSource.contains("controller.layoutAttribute = .bottom"))
        XCTAssertTrue(shellSource.contains("controller.fullScreenMinHeight = DesktopMeetingShellChrome.recordingStripHeight"))
        XCTAssertTrue(shellSource.contains("RecordingTitlebarHUD("))
        XCTAssertFalse(shellSource.contains("recordingStrip(for:"))
        XCTAssertTrue(shellSource.contains("leadingPadding: 22"))
        XCTAssertTrue(shellSource.contains("onSubmit: onSupportIncidentReport"))
        XCTAssertTrue(shellSource.contains("accessibilityElement(children: summary.safeReport == nil ? .combine : .contain)"))
        XCTAssertTrue(stripSource.contains(DesktopSupportIncidentActionCopy.sendTitle))
        XCTAssertTrue(stripSource.contains(DesktopSupportIncidentActionCopy.failureMessage))
        XCTAssertTrue(stripSource.contains(".accessibilityLabel(DesktopSupportIncidentActionCopy.sendTitle)"))
        XCTAssertFalse(stripSource.contains("Скопировать отчет"))
        XCTAssertFalse(stripSource.contains("Отправить отчет"))
    }

    func testEmbeddedCabinetWebViewIsClippedInsideNativeShell() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let webViewSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(webViewSource.contains("clipsToBounds = true"))
        XCTAssertTrue(webViewSource.contains("layer?.masksToBounds = true"))
        XCTAssertTrue(webViewSource.contains("webView.clipsToBounds = true"))
        XCTAssertTrue(webViewSource.contains("webView.layer?.masksToBounds = true"))
    }

    func testEmbeddedCabinetWebViewSupportsServerOwnedManualUploadFilePicker() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let webViewSource = try String(
            contentsOf: root.appendingPathComponent("apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift"),
            encoding: .utf8
        )

        XCTAssertTrue(webViewSource.contains("webView.uiDelegate = context.coordinator"))
        XCTAssertTrue(webViewSource.contains("WKNavigationDelegate, WKUIDelegate"))
        XCTAssertTrue(webViewSource.contains("runOpenPanelWith parameters: WKOpenPanelParameters"))
        XCTAssertTrue(webViewSource.contains("let panel = NSOpenPanel()"))
        XCTAssertTrue(webViewSource.contains("panel.canChooseFiles = true"))
        XCTAssertTrue(webViewSource.contains("initiatedByFrame: WKFrameInfo"))
        XCTAssertTrue(webViewSource.contains("panel.canChooseDirectories = false"))
        XCTAssertTrue(webViewSource.contains("panel.allowsMultipleSelection = false"))
        XCTAssertTrue(webViewSource.contains("completionHandler(nil)"))
        XCTAssertTrue(webViewSource.contains("completionHandler(urls.isEmpty ? nil : urls)"))
    }

    func testEmbeddedCabinetFilePickerIsBoundToMainFrameSameOriginMeetingList() throws {
        let policy = DesktopCabinetRoutePolicy(
            baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
        )
        let listURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings"))
        let detailURL = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/abc"))
        let externalURL = try XCTUnwrap(URL(string: "https://evil.example/desktop/meetings"))

        XCTAssertTrue(
            EmbeddedCabinetWebView.allowsFilePicker(
                webViewURL: listURL,
                frameURL: listURL,
                frameIsMainFrame: true,
                routePolicy: policy
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetWebView.allowsFilePicker(
                webViewURL: listURL,
                frameURL: listURL,
                frameIsMainFrame: false,
                routePolicy: policy
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetWebView.allowsFilePicker(
                webViewURL: listURL,
                frameURL: detailURL,
                frameIsMainFrame: true,
                routePolicy: policy
            )
        )
        XCTAssertFalse(
            EmbeddedCabinetWebView.allowsFilePicker(
                webViewURL: listURL,
                frameURL: externalURL,
                frameIsMainFrame: true,
                routePolicy: policy
            )
        )
    }

    func testEmbeddedCabinetMeetingDetailUsesSlotBackedSummaryContract() throws {
        let root = try repositoryRootForMeetingShellBoundaryTests()
        let detailSource = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html"
            ),
            encoding: .utf8
        )
        let cabinetSource = try String(
            contentsOf: root.appendingPathComponent(
                "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
            ),
            encoding: .utf8
        )

        for marker in [
            "data-summary-result-state",
            "data-summary-generation-state",
            "data-summary-source-state",
            "data-summary-availability-state",
            "data-summary-reason-code",
            "data-summary-format-controls",
            "data-summary-format-button",
            "data-summary-format-listbox",
            "data-summary-refresh-button",
            "data-summary-format-dialog",
            "data-summary-format-all"
        ] {
            XCTAssertTrue(detailSource.contains(marker), marker)
        }

        XCTAssertTrue(cabinetSource.contains("currentOutcomeSetId"))
        XCTAssertTrue(cabinetSource.contains("current_outcome_set_id"))
        XCTAssertTrue(cabinetSource.contains("summary-candidate-status"))
        XCTAssertTrue(cabinetSource.contains("Текущие итоги остаются доступны."))

        for forbidden in [
            "data-summary-candidate-preview",
            "data-summary-candidate-accept",
            "data-summary-candidate-reject",
            "data-summary-candidate-content"
        ] {
            XCTAssertFalse(detailSource.contains(forbidden), forbidden)
            XCTAssertFalse(cabinetSource.contains(forbidden), forbidden)
        }
    }

    private func makeActiveSession() -> CaptureSession {
        CaptureSession(
            id: "active-recording-boundary",
            mode: .audioRecording,
            state: .active,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "policy",
            triggerEvidence: [:],
            visibleIndicatorState: .active,
            stopActionAvailable: true,
            bufferSummaryId: nil,
            startedAt: Date(timeIntervalSince1970: 1_000),
            stoppedAt: nil
        )
    }

    private func makeQueueItem(
        id: String,
        state: UploadItemState,
        retryMode: UploadRetryMode,
        meetingId: String? = nil,
        serverTruth: ServerTruthFingerprint = ServerTruthFingerprint(),
        createdAt: Date
    ) -> DesktopUploadQueueItem {
        let profile = ArtifactCompletenessProfile(
            schemaVersion: LocalRecordingManifest.legacySchemaVersion,
            manifestPresent: true,
            microphonePresent: true,
            systemAudioPresent: true,
            manifestSha256: String(repeating: "a", count: 64),
            microphoneSha256: String(repeating: "b", count: 64),
            systemAudioSha256: String(repeating: "c", count: 64),
            manifestSizeBytes: 128,
            microphoneSizeBytes: 100,
            systemAudioSizeBytes: 100,
            durationSeconds: 60,
            trackCompleteness: [],
            isUploadable: true
        )
        return DesktopUploadQueueItem(
            id: id,
            sessionId: "session-\(id)",
            directoryId: "directory-\(id)",
            directoryPath: "/tmp/directory-\(id)",
            manifestPath: "/tmp/directory-\(id)/manifest.json",
            microphonePath: "/tmp/directory-\(id)/mic.wav",
            systemAudioPath: "/tmp/directory-\(id)/incoming.wav",
            state: state,
            retryMode: retryMode,
            retentionDeadline: Date(timeIntervalSince1970: 2_000),
            createdAt: createdAt,
            updatedAt: createdAt,
            meetingId: meetingId,
            artifactProfile: profile,
            serverTruth: serverTruth,
            retentionDecision: RetentionDecision(
                decision: .retain,
                decidedAt: Date(timeIntervalSince1970: 1_000),
                reason: "test",
                localArtifactsRetained: true,
                policyReference: "test"
            )
        )
    }

    private func repositoryRootForMeetingShellBoundaryTests() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            let appSourceURL = candidate.appendingPathComponent("apps/macos/RecApp/App/TwoBrainRecApp.swift")
            if FileManager.default.fileExists(atPath: appSourceURL.path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "DesktopMeetingShellWebViewBoundaryTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}
#endif
