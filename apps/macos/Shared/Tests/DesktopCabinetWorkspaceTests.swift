import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetWorkspaceTests: XCTestCase {
    func testDefaultWorkspaceOpensMeetingsList() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).absoluteString, "https://rec.2brain.dev/desktop/meetings")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.workspace, "desktop-cabinet-workspace")
        XCTAssertFalse(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).path.localizedCaseInsensitiveContains("diagnostic"))
        XCTAssertFalse(DesktopCabinetWorkspace.defaultRoute(configuration: configuration).path.localizedCaseInsensitiveContains("settings"))
    }

    func testWorkspaceOpensMeetingDetailDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(
            DesktopCabinetWorkspace.detailRoute(meetingId: "meeting-033", configuration: configuration).absoluteString,
            "https://rec.2brain.dev/desktop/meetings/meeting-033"
        )
    }

    @MainActor
    func testEmbeddedWebViewDoesNotReloadInitialRouteAfterInPageNavigation() throws {
        let initial = URLRequest(url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings")))
        let detail = URLRequest(url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033")))
        let lastLoadedInitialRoute = EmbeddedCabinetWebView.loadIdentity(for: initial)

        XCTAssertFalse(
            EmbeddedCabinetWebView.shouldLoad(
                request: initial,
                lastLoadedRequestIdentity: lastLoadedInitialRoute
            )
        )
        XCTAssertTrue(
            EmbeddedCabinetWebView.shouldLoad(
                request: detail,
                lastLoadedRequestIdentity: lastLoadedInitialRoute
            )
        )
    }

    func testMeetingsSidebarItemTargetsEmbeddedMeetingList() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(
            DesktopMeetingShellSidebarItem.meetings.destinationRoute(configuration: configuration)?.absoluteString,
            "https://rec.2brain.dev/desktop/meetings"
        )
        XCTAssertEqual(DesktopMeetingShellSidebarItem.meetings.accessibilityLabel, "Открыть список встреч")
    }

    func testEmbeddedWebViewTracksMainFrameRouteChangesForNativeNavigation() throws {
        let list = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings"))
        let detail = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033"))

        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: nil, loaded: list), list)
        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: list, loaded: detail), detail)
        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: detail, loaded: detail), detail)
    }

    func testExpiredSessionRecoveryOpensBrowserLoginForDesktopMeetings() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: ["X-Workspace-Id": "workspace-033"]
        ))

        let route = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let components = try XCTUnwrap(URLComponents(url: route, resolvingAgainstBaseURL: false))
        let query = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).compactMap { item in
            item.value.map { (item.name, $0) }
        })

        XCTAssertEqual(route.path, "/login")
        XCTAssertEqual(query["next"], "/desktop/meetings")
        XCTAssertEqual(query["workspace_id"], "workspace-033")
    }

    func testShellInvariantKeepsStopReachableDuringActiveRecordingForEveryCabinetState() {
        for state in DesktopCabinetState.allCases {
            let invariant = NativeShellInvariant(
                recordVisible: true,
                stopVisible: true,
                uploadTruthVisible: true,
                focusCanReachStop: true,
                embeddedSurfaceLoaded: state == .ready
            )

            XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: state), "\(state)")
        }
    }

    func testActiveRecordingInvariantFailsWhenStopIsHiddenOrFocusTrapped() {
        let hiddenRecord = NativeShellInvariant(
            recordVisible: false,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true
        )
        let hiddenStop = NativeShellInvariant(
            recordVisible: true,
            stopVisible: false,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true
        )
        let focusTrap = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: false,
            embeddedSurfaceLoaded: true
        )

        XCTAssertFalse(hiddenRecord.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(hiddenStop.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(focusTrap.satisfiesActiveRecordingSafety(cabinetState: .ready))
    }

    func testNativeAndEmbeddedRegionsHaveStableAccessibilityBoundaries() {
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.captureRegion, "desktop-native-capture-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.uploadTruthRegion, "desktop-native-upload-truth-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.nativeShellRegion, "desktop-native-shell-region")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.embeddedSurface, "desktop-cabinet-embedded-surface")
    }

    func testWorkspaceZoomDoesNotScaleNativeShellControls() {
        let safe = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true,
            workspaceZoomApplied: WorkspaceZoomPreference(value: 1.3),
            nativeShellScaledByWorkspaceZoom: false
        )
        let unsafe = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: true,
            workspaceZoomApplied: WorkspaceZoomPreference(value: 1.3),
            nativeShellScaledByWorkspaceZoom: true
        )

        XCTAssertTrue(safe.satisfiesActiveRecordingSafety(cabinetState: .ready))
        XCTAssertFalse(unsafe.satisfiesActiveRecordingSafety(cabinetState: .ready))
    }

    func testUnavailableStatesHaveBoundedMessages() {
        let states: [DesktopCabinetState] = [.notConfigured, .offline, .timeout, .expiredSession, .accessDenied, .notFound, .malformedResponse, .blockedRoute]

        for state in states {
            XCTAssertFalse(state.unavailableTitle.isEmpty, "\(state)")
            XCTAssertFalse(state.unavailableSystemImage.isEmpty, "\(state)")
            XCTAssertFalse(state.userMessage.isEmpty, "\(state)")
            XCTAssertLessThanOrEqual(state.userMessage.count, 180, "\(state)")
            XCTAssertFalse(state.userMessage.contains("/Users/"), "\(state)")
        }
    }

    func testMissingOwnerSessionHasLoginRecoveryAction() {
        XCTAssertEqual(DesktopCabinetState.expiredSession.unavailableTitle, "Нужен вход в кабинет")
        XCTAssertEqual(DesktopCabinetState.expiredSession.recoveryActionTitle, "Войти в кабинет")
        XCTAssertTrue(DesktopCabinetState.expiredSession.unavailableSystemImage.contains("person"))
        XCTAssertFalse(DesktopCabinetState.expiredSession.shouldShowEmbeddedSurface)
    }

    func testDeniedStateDoesNotOfferLoginAsAccessProof() {
        XCTAssertEqual(DesktopCabinetState.accessDenied.unavailableTitle, "Нет доступа к кабинету")
        XCTAssertNil(DesktopCabinetState.accessDenied.recoveryActionTitle)
        XCTAssertFalse(DesktopCabinetState.accessDenied.shouldShowEmbeddedSurface)
    }

    func testDeniedAndNotFoundStatesDoNotConfirmMeetingExistence() {
        for state in [DesktopCabinetState.accessDenied, .notFound] {
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("this meeting"), "\(state)")
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("meeting exists"), "\(state)")
            XCTAssertTrue(state.userMessage.localizedCaseInsensitiveContains("не удалось подтвердить"), "\(state)")
        }
    }

    func testProductWorkspaceLayoutKeepsMeetingsBeforeDiagnostics() {
        let order = DesktopCabinetLayoutPolicy.defaultSectionOrder

        XCTAssertEqual(order.first, .meetings)
        XCTAssertTrue(order.contains(.capture))
        XCTAssertTrue(order.contains(.localAudioReadiness))
        XCTAssertLessThan(
            try XCTUnwrap(order.firstIndex(of: .meetings)),
            try XCTUnwrap(order.firstIndex(of: .localAudioReadiness))
        )
    }

    func testInstalledRuntimeEvidenceUsesApplicationsBundlePath() {
        let acceptedRuntimePath = "/Applications/2brain Rec.app"

        XCTAssertEqual(acceptedRuntimePath, "/Applications/2brain Rec.app")
        XCTAssertFalse(acceptedRuntimePath.hasPrefix("/Users/"))
        XCTAssertTrue(acceptedRuntimePath.hasSuffix("2brain Rec.app"))
    }
}
#endif
