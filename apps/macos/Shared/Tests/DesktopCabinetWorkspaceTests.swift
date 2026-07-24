import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

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

        let sameOriginRequest = configuration.urlRequest(
            for: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings"))
        )
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "Authorization"), "Bearer SECRET")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-Workspace-Id"), "workspace-033")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-Device-Id"), "device-033")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-User-Id"), "user-033")
        XCTAssertEqual(sameOriginRequest.value(forHTTPHeaderField: "X-Organization-Id"), "organization-033")

        for externalURL in [
            "https://attacker.example/oauth/authorize?state=state",
            "http://rec.2brain.dev/desktop/meetings",
            "https://rec.2brain.dev:8443/desktop/meetings",
            "https://sub.rec.2brain.dev/desktop/meetings"
        ] {
            let externalProviderRequest = configuration.urlRequest(
                for: try XCTUnwrap(URL(string: externalURL))
            )
            for header in [
                "Authorization",
                "X-Workspace-Id",
                "X-Device-Id",
                "X-User-Id",
                "X-Organization-Id"
            ] {
                XCTAssertNil(externalProviderRequest.value(forHTTPHeaderField: header), externalURL)
            }
        }
    }

    func testWorkspaceOpensMeetingDetailDestination() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))

        XCTAssertEqual(
            DesktopCabinetWorkspace.detailRoute(meetingId: "meeting-033", configuration: configuration).absoluteString,
            "https://rec.2brain.dev/desktop/meetings/meeting-033"
        )
    }

    func testMeetingDetailBackReturnsToListWhenWebHistoryIsNotAUsableMeetingRoute() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let external = try XCTUnwrap(URL(string: "https://accounts.example/login"))

        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: detail,
                backURL: login,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .meetingsList
        )
        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: detail,
                backURL: external,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .meetingsList
        )
    }

    func testMeetingDetailBackPreservesSafeMeetingHistoryAndListBackDisablesWithoutHistory() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")

        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: detail,
                backURL: configuration.meetingsURL(),
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .history
        )
        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: configuration.meetingsURL(),
                backURL: nil,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy
            ),
            .unavailable
        )
    }

    func testExpiredSessionBackCannotRestoreProtectedCabinetDocument() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")

        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: login,
                backURL: detail,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy,
                sessionExpired: true
            ),
            .unavailable
        )
    }

    func testOnlySafeGetDocumentsCanEnterNativeHistory() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let list = configuration.meetingsURL()
        var getRequest = URLRequest(url: list)
        getRequest.httpMethod = "GET"
        var postRequest = URLRequest(url: list)
        postRequest.httpMethod = "POST"

        XCTAssertTrue(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(getRequest, routePolicy: policy))
        XCTAssertFalse(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(postRequest, routePolicy: policy))
    }

    func testAuthCallbackCannotEnterNativeHistoryOrBackStack() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.dev", headers: [:]))
        let policy = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL)
        let callback = try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/auth/callback/yandex?code=one-time-code"))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        var callbackRequest = URLRequest(url: callback)
        callbackRequest.httpMethod = "GET"

        XCTAssertFalse(EmbeddedCabinetNavigationPolicy.isSafeDocument(callback, routePolicy: policy))
        XCTAssertFalse(EmbeddedCabinetNavigationPolicy.isSafeHistoryRequest(callbackRequest, routePolicy: policy))
        XCTAssertEqual(
            EmbeddedCabinetNavigationPolicy.backDecision(
                currentURL: login,
                backURL: callback,
                fallbackURL: configuration.meetingsURL(),
                routePolicy: policy,
                sessionExpired: true
            ),
            .unavailable
        )
    }

    func testNativeNavigationControlsExposeStableAccessibilityIdentifiers() {
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.navigationBack, "desktop-cabinet-navigation-back")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.navigationForward, "desktop-cabinet-navigation-forward")
        XCTAssertEqual(DesktopCabinetAccessibilityIdentifier.navigationReload, "desktop-cabinet-navigation-reload")
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
            .embedded(configuration.meetingsURL())
        )
    }

    func testRecoveryKeepsLastDocumentRouteAfterResourceFailure() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let detail = configuration.meetingDetailURL(meetingId: "meeting-033")
        let artifact = try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio"))

        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: detail,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(detail)
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: artifact,
                initialRoute: detail,
                configuration: configuration
            ),
            .embedded(detail)
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .accessDenied,
                currentRoute: detail,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(configuration.meetingsURL())
        )
    }

    func testRecoveryKeepsCalendarSettingsRouteAcrossAuthAndBlockedStates() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let settings = configuration.calendarSettingsURL()

        guard case let .embedded(login)? = DesktopCabinetWorkspace.recoveryTarget(
            for: .expiredSession,
            currentRoute: settings,
            initialRoute: nil,
            configuration: configuration
        ) else {
            return XCTFail("Expected embedded login recovery")
        }
        let loginComponents = try XCTUnwrap(URLComponents(url: login, resolvingAgainstBaseURL: false))
        XCTAssertEqual(
            loginComponents.queryItems?.first(where: { $0.name == "next" })?.value,
            settings.path
        )
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(
                for: .blockedRoute,
                currentRoute: settings,
                initialRoute: nil,
                configuration: configuration
            ),
            .embedded(settings)
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

    func testUnavailableWorkspaceStatesStayNativeAndExposeOnlySafeRecoveryActions() throws {
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
            if [.offline, .timeout, .malformedResponse, .accessDenied, .notFound, .blockedRoute].contains(state) {
                XCTAssertEqual(
                    DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration),
                    .embedded(configuration.meetingsURL()),
                    "\(state)"
                )
                if [.offline, .timeout, .malformedResponse].contains(state) {
                    XCTAssertEqual(state.recoveryActionTitle, "Повторить", "\(state)")
                    XCTAssertEqual(state.recoverySystemImage, "arrow.clockwise", "\(state)")
                } else {
                    XCTAssertEqual(state.recoveryActionTitle, "К списку встреч", "\(state)")
                    XCTAssertEqual(state.recoverySystemImage, "arrow.left", "\(state)")
                }
            } else {
                XCTAssertNil(DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration), "\(state)")
                XCTAssertNil(state.recoveryActionTitle, "\(state)")
            }
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
        XCTAssertEqual(DesktopCabinetState.expiredSession.unavailableTitle, "Нужно войти")
        XCTAssertEqual(DesktopCabinetState.expiredSession.recoveryActionTitle, "Войти в кабинет")
        XCTAssertEqual(DesktopCabinetState.expiredSession.recoverySystemImage, "person.crop.circle")
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

    func testDeniedStateOffersSafeReturnWithoutPretendingToGrantAccess() {
        XCTAssertEqual(DesktopCabinetState.accessDenied.unavailableTitle, "Нет доступа к встречам")
        XCTAssertEqual(DesktopCabinetState.accessDenied.recoveryActionTitle, "К списку встреч")
        XCTAssertEqual(DesktopCabinetState.accessDenied.recoverySystemImage, "arrow.left")
        XCTAssertFalse(DesktopCabinetState.accessDenied.shouldShowEmbeddedSurface)
    }

    func testBlockedAndMissingRoutesOfferReturnToMeetings() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))

        for state in [DesktopCabinetState.blockedRoute, .notFound] {
            XCTAssertEqual(state.recoveryActionTitle, "К списку встреч", "\(state)")
            XCTAssertEqual(state.recoverySystemImage, "arrow.left", "\(state)")
            XCTAssertEqual(
                DesktopCabinetWorkspace.recoveryTarget(for: state, configuration: configuration),
                .embedded(configuration.meetingsURL()),
                "\(state)"
            )
        }
    }

    func testDeniedAndNotFoundStatesDoNotConfirmMeetingExistence() {
        for state in [DesktopCabinetState.accessDenied, .notFound] {
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("this meeting"), "\(state)")
            XCTAssertFalse(state.userMessage.localizedCaseInsensitiveContains("meeting exists"), "\(state)")
            XCTAssertTrue(
                state.userMessage.localizedCaseInsensitiveContains("доступ") ||
                    state.userMessage.localizedCaseInsensitiveContains("недоступна"),
                "\(state)"
            )
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
            XCTAssertEqual(presentation.tileDetail, "Записи остаются на этом Mac", "\(state)")
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

    func testRevokedEmbeddedWorkspaceRequiresExplicitReauthenticationAndReselection() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let response = try XCTUnwrap(HTTPURLResponse(
            url: configuration.meetingsURL(),
            statusCode: 403,
            httpVersion: nil,
            headerFields: ["X-GRAF-Cabinet-Recovery": "reselect-space"]
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)

        XCTAssertEqual(DesktopCabinetState.state(forHTTPResponse: response), .workspaceReselectionRequired)
        XCTAssertEqual(
            DesktopCabinetWorkspace.recoveryTarget(for: .workspaceReselectionRequired, configuration: configuration),
            .embedded(login)
        )
        XCTAssertEqual(DesktopCabinetState.workspaceReselectionRequired.recoveryActionTitle, "Войти и выбрать пространство")
        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .workspaceReselectionRequired,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertFalse(DesktopCabinetState.workspaceReselectionRequired.shouldShowEmbeddedSurface)
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

    func testUnavailableStatesUseHumanCopyAndKeepNativeRecordingIndependent() {
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

            XCTAssertFalse(message.localizedCaseInsensitiveContains("сервером rec"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("пароли календаря"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("token"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("password"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("app password"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("refresh"), "\(state)")
            XCTAssertTrue(invariant.satisfiesActiveRecordingSafety(cabinetState: state), "\(state)")
        }

        for state in [DesktopCabinetState.notConfigured, .offline, .timeout, .expiredSession, .malformedResponse] {
            XCTAssertTrue(state.userMessage.contains("Запись на этом Mac остаётся доступна"), "\(state)")
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
        XCTAssertEqual(
            DesktopCabinetWorkspace.calendarSettingsRecoveryTarget(
                for: .offline,
                configuration: configuration
            ),
            .embedded(configuration.calendarSettingsURL())
        )
    }

    func testLocalRecordingLifecycleStaysUsableBeforeServerIdentityExists() {
        let localOnly = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(id: "local-only", state: .queued)
        )
        let uploading = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(id: "uploading", state: .uploading)
        )

        XCTAssertEqual(localOnly.custodyState, .serverUnknownLocalSaved)
        XCTAssertEqual(localOnly.uploadState, .notStarted)
        XCTAssertNil(localOnly.serverMeetingId)
        XCTAssertFalse(localOnly.reviewAvailable)
        XCTAssertEqual(uploading.custodyState, .partialUploaded)
        XCTAssertEqual(uploading.uploadState, .partialUploaded)
        XCTAssertNil(uploading.serverMeetingId)
        XCTAssertFalse(uploading.reviewAvailable)
    }

    func testServerProcessingAndReadyLifecycleDoNotOverwriteLocalCustodyTruth() {
        let processing = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(
                id: "server-processing",
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(
                    meetingId: "meeting-processing",
                    mediaRevisionId: "revision-processing",
                    processingStatus: "pending_processing",
                    finalizedAt: Date(timeIntervalSince1970: 200)
                )
            )
        )
        let ready = DesktopUploadCustodyProjection(
            item: custodyFixtureQueueItem(
                id: "server-ready",
                state: .uploaded,
                serverTruth: ServerTruthFingerprint(
                    meetingId: "meeting-ready",
                    mediaRevisionId: "revision-ready",
                    processingStatus: "processed",
                    finalizedAt: Date(timeIntervalSince1970: 200)
                )
            )
        )

        XCTAssertEqual(processing.custodyState, .processing)
        XCTAssertEqual(processing.uploadState, .finalized)
        XCTAssertFalse(processing.reviewAvailable)
        XCTAssertEqual(ready.custodyState, .delivered)
        XCTAssertEqual(ready.uploadState, .finalized)
        XCTAssertTrue(ready.reviewAvailable)
        XCTAssertEqual(ready.normalUserAction, .openReview)
    }
}
#endif
