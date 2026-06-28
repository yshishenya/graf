import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

@MainActor
final class DesktopMeetingShellWebViewBoundaryTests: XCTestCase {
    func testOnlineProductSidebarIsWebOwnedWhileNativeCaptureChromeRemainsNative() {
        XCTAssertFalse(DesktopMeetingShellChrome.idleShowsNativeTopBar)
        XCTAssertEqual(DesktopMeetingShellChrome.compactRailLabels, ["Запись", "Сохранность"])
        XCTAssertGreaterThan(DesktopMeetingShellChrome.recordingStripHeight, 0)
        XCTAssertGreaterThanOrEqual(DesktopMeetingShellChrome.inspectorToggleHitSize, 40)
        XCTAssertTrue(DesktopMeetingShellChrome.shouldShowExpandedInspector(
            manualExpanded: false,
            hasActiveRecording: true
        ))
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

    func testOfflineStatesDoNotExposeOnlineRecoveryRouteFromWorkspace() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))

        for state in [DesktopCabinetState.offline, .timeout, .notConfigured, .malformedResponse] {
            XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
                for: state,
                currentRoute: configuration.meetingsURL(),
                initialRoute: nil,
                configuration: configuration
            ), "\(state)")
            XCTAssertNil(DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration), "\(state)")
            XCTAssertNil(state.recoveryActionTitle, "\(state)")
        }
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
        XCTAssertTrue(shellSource.contains("leadingPadding: 22"))
        XCTAssertTrue(shellSource.contains("onSubmit: onSupportIncidentReport"))
        XCTAssertTrue(shellSource.contains("accessibilityElement(children: summary.safeReport == nil ? .combine : .contain)"))
        XCTAssertTrue(stripSource.contains(DesktopSupportIncidentActionCopy.sendTitle))
        XCTAssertTrue(stripSource.contains(DesktopSupportIncidentActionCopy.copyTitle))
        XCTAssertTrue(stripSource.contains(DesktopSupportIncidentActionCopy.failureMessage))
        XCTAssertTrue(stripSource.contains(".accessibilityLabel(\"Отправить отчет разработчикам\")"))
        XCTAssertTrue(stripSource.contains(".accessibilityLabel(DesktopSupportIncidentActionCopy.copyTitle)"))
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
            schemaVersion: LocalRecordingManifest.schemaVersion,
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
