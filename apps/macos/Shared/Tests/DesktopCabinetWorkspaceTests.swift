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

    func testCabinetUrlRequestKeepsDesktopHeadersOnSameOriginOnly() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [
                "Authorization": "Bearer SECRET",
                "X-Workspace-Id": "workspace-033",
                "X-Device-Id": "device-033",
                "X-User-Id": "user-033",
                "X-Organization-Id": "organization-033"
            ]
        ))

        let sameOriginRequest = configuration.urlRequest(for: try url("/desktop/meetings"))
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "Authorization"), "Bearer SECRET")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")

        let externalProviderRequest = configuration.urlRequest(
            for: try XCTUnwrap(URL(string: "https://attacker.example/oauth/authorize?state=state"))
        )
        XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: "Authorization"))
        XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: "X-Workspace-Id"))
        XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: "X-Device-Id"))
        XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: "X-User-Id"))
        XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: "X-Organization-Id"))
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

    func testEmbeddedWebViewTracksMainFrameRouteChangesForNativeNavigation() throws {
        let list = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings"))
        let detail = try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033"))

        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: nil, loaded: list), list)
        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: list, loaded: detail), detail)
        XCTAssertEqual(EmbeddedCabinetWebView.trackedRoute(current: detail, loaded: detail), detail)
    }

    func testSuccessfulLoginPageLoadDoesNotMarkCabinetReady() {
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .meetingList), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .meetingDetail), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .calendarSettings), .ready)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authLogin), .expiredSession)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authSignup), .expiredSession)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authProvider), .expiredSession)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authCallback), .expiredSession)
    }

    func testExpiredSessionRecoveryUsesEmbeddedLoginForDesktopMeetings() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: ["X-Workspace-Id": "workspace-033"]
        ))

        let route = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .expiredSession, configuration: configuration),
            .embedded(route)
        )
        let components = try XCTUnwrap(URLComponents(url: route, resolvingAgainstBaseURL: false))
        let query = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).compactMap { item in
            item.value.map { (item.name, $0) }
        })

        XCTAssertEqual(route.path, "/login")
        XCTAssertEqual(query["next"], "/desktop/meetings")
        XCTAssertEqual(query["workspace_id"], "workspace-033")
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .offline, configuration: configuration),
            nil
        )
    }

    func testExpiredSessionKeepsEmbeddedLoginSurfaceVisible() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let provider = try XCTUnwrap(URL(string: "https://oauth.yandex.ru/authorize?state=state"))
        let futureProvider = try XCTUnwrap(URL(string: "https://id.future-provider.example/authorize?state=state"))
        let callback = try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/auth/callback/yandex?state=state&code=code"))

        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: provider,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: futureProvider,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: callback,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: configuration.meetingsURL(),
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .offline,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
    }

    func testOfflineUnavailableWorkspaceStatesStayNativeWithoutOnlineRecoveryAction() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let unavailableStates: [DesktopCabinetState] = [
            .notConfigured,
            .offline,
            .timeout,
            .accessDenied,
            .notFound,
            .malformedResponse,
            .blockedRoute
        ]

        for state in unavailableStates {
            XCTAssertFalse(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
                for: state,
                currentRoute: configuration.meetingsURL(),
                initialRoute: nil,
                configuration: configuration
            ), "\(state)")
            XCTAssertNil(DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration), "\(state)")
            XCTAssertNil(state.recoveryActionTitle, "\(state)")
            XCTAssertNotEqual(
                DesktopMeetingShellCabinetStatusPresentation.resolved(
                    cabinetConfigured: true,
                    cabinetState: state
                ).tileTitle,
                "Сервер доступен",
                "\(state)"
            )
        }
    }

    func testExpiredSessionCanShowOnlyAuthRecoveryInsideEmbeddedSurface() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: ["X-Workspace-Id": "workspace-033"]
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)

        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .expiredSession, configuration: configuration),
            .embedded(login)
        )
        XCTAssertNotEqual(
            DesktopMeetingShellCabinetStatusPresentation.resolved(
                cabinetConfigured: true,
                cabinetState: .expiredSession
            ).tileTitle,
            "Сервер доступен"
        )
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

    func test052ExpiredOwnerSessionKeepsNativeShellTruthVisible() {
        let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .expiredSession
        )
        let invariant = NativeShellInvariant(
            recordVisible: true,
            stopVisible: true,
            uploadTruthVisible: true,
            focusCanReachStop: true,
            embeddedSurfaceLoaded: false
        )

        XCTAssertEqual(presentation.tileTitle, "Нужен вход")
        XCTAssertEqual(presentation.tileDetail, "Откройте кабинет заново")
        XCTAssertEqual(presentation.tone, .warning)
        XCTAssertFalse(DesktopCabinetState.expiredSession.shouldShowEmbeddedSurface)
        XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: .expiredSession))
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
        let acceptedRuntimePath = "/Applications/GRAF.app"

        XCTAssertEqual(acceptedRuntimePath, "/Applications/GRAF.app")
        XCTAssertFalse(acceptedRuntimePath.hasPrefix("/Users/"))
        XCTAssertTrue(acceptedRuntimePath.hasSuffix("GRAF.app"))
    }

    func testConfiguredCabinetDoesNotShowHealthyShellStatusBeforeRuntimeProof() {
        let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .loading
        )

        XCTAssertEqual(presentation.tileTitle, "Проверяем сервер")
        XCTAssertEqual(presentation.systemImage, "clock")
        XCTAssertEqual(presentation.tone, .neutral)
        XCTAssertFalse(presentation.tileTitle.localizedCaseInsensitiveContains("задан"))
        XCTAssertNotEqual(presentation.systemImage, "checkmark.circle")
    }

    func testShellShowsServerUnavailableWhenCabinetNavigationFails() {
        for state in [DesktopCabinetState.offline, .timeout] {
            let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
                cabinetConfigured: true,
                cabinetState: state
            )

            XCTAssertEqual(presentation.tileTitle, "Сервер недоступен", "\(state)")
            XCTAssertEqual(presentation.tileDetail, "Запись работает локально", "\(state)")
            XCTAssertEqual(presentation.systemImage, "wifi.slash", "\(state)")
            XCTAssertEqual(presentation.tone, .error, "\(state)")
        }
    }

    func testShellShowsSuccessOnlyAfterCabinetReadyState() {
        let ready = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .ready
        )
        let expired = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .expiredSession
        )

        XCTAssertEqual(ready.tileTitle, "Сервер доступен")
        XCTAssertEqual(ready.systemImage, "checkmark.circle")
        XCTAssertEqual(ready.tone, .success)
        XCTAssertEqual(expired.tileTitle, "Нужен вход")
        XCTAssertEqual(expired.systemImage, "person.crop.circle.badge.exclamationmark")
        XCTAssertEqual(expired.tone, .warning)
    }

    func testShellNeverCarriesCachedReadyAcrossAuthOrServerFailureStates() {
        let nonReadyStates: [DesktopCabinetState] = [
            .loading,
            .offline,
            .timeout,
            .expiredSession,
            .accessDenied,
            .notFound,
            .malformedResponse,
            .blockedRoute,
        ]

        for state in nonReadyStates {
            let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
                cabinetConfigured: true,
                cabinetState: state
            )

            XCTAssertNotEqual(presentation.tileTitle, "Сервер доступен", "\(state)")
            XCTAssertNotEqual(presentation.systemImage, "checkmark.circle", "\(state)")
            XCTAssertNotEqual(presentation.tone, .success, "\(state)")
        }
    }

    func testHTTPStatusMappingPreventsFalseGreenCabinetState() {
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 200))
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 401), .expiredSession)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 403), .accessDenied)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 404), .notFound)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 504), .timeout)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 503), .offline)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 429), .malformedResponse)
    }

    func testOwnerReviewDetailRouteUsesServerOwnedDesktopCabinetOnlyWhenReady() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let route = DesktopCabinetWorkspace.detailRoute(meetingId: "meeting-051", configuration: configuration)
        let loading = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .loading
        )
        let ready = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: .ready
        )

        XCTAssertEqual(route.path, "/desktop/meetings/meeting-051")
        XCTAssertNil(route.fragment)
        XCTAssertNotEqual(loading.tileTitle, "Сервер доступен")
        XCTAssertEqual(ready.tileTitle, "Сервер доступен")
        XCTAssertEqual(ready.systemImage, "checkmark.circle")
    }

    func testCalendarSettingsUnavailableStatesKeepCredentialBoundaryAndManualRecording() {
        let unavailableStates: [DesktopCabinetState] = [
            .notConfigured,
            .offline,
            .timeout,
            .expiredSession,
            .accessDenied,
            .notFound,
            .malformedResponse,
            .blockedRoute
        ]

        for state in unavailableStates {
            let message = state.userMessage
            let invariant = NativeShellInvariant(
                recordVisible: true,
                stopVisible: true,
                uploadTruthVisible: true,
                focusCanReachStop: true,
                embeddedSurfaceLoaded: false
            )

            XCTAssertTrue(message.contains("Mac не хранит пароли календаря"), "\(state)")
            XCTAssertTrue(message.contains("ручная запись доступна без календаря"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("token"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("password"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("app password"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("refresh"), "\(state)")
            XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: state), "\(state)")
        }
    }

    func testCalendarSettingsExpiredSessionRecoveryReturnsToEmbeddedSettings() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: ["X-Workspace-Id": "workspace-063"]
        ))
        let target = DesktopCabinetWorkspace.calendarSettingsRecoveryTarget(
            for: .expiredSession,
            configuration: configuration
        )
        guard case let .embedded(route)? = target else {
            XCTFail("Expected embedded calendar settings login recovery target")
            return
        }
        let components = try XCTUnwrap(URLComponents(url: route, resolvingAgainstBaseURL: false))
        let query = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).compactMap { item in
            item.value.map { (item.name, $0) }
        })

        XCTAssertEqual(route.path, "/login")
        XCTAssertEqual(query["next"], "/desktop/settings/integrations/calendar")
        XCTAssertEqual(query["workspace_id"], "workspace-063")
        XCTAssertNil(DesktopCabinetWorkspace.calendarSettingsRecoveryTarget(
            for: .offline,
            configuration: configuration
        ))
    }
}
#endif
