import Foundation
import TwoBrainRecAppCore

#if canImport(XCTest)
import XCTest

final class DesktopCabinetConfigurationTests: XCTestCase {
    func testConfigurationAcceptsHttpOriginsAndBuildsDesktopRoutes() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev/base/",
            headers: ["X-Workspace-Id": "workspace-033"]
        ))

        XCTAssertEqual(configuration.meetingsURL().absoluteString, "https://rec.2brain.dev/desktop/meetings")
        XCTAssertEqual(
            configuration.calendarSettingsURL().absoluteString,
            "https://rec.2brain.dev/desktop/settings/integrations/calendar"
        )
        XCTAssertEqual(
            configuration.meetingDetailURL(meetingId: "meeting-033").absoluteString,
            "https://rec.2brain.dev/desktop/meetings/meeting-033"
        )
        XCTAssertEqual(configuration.workspaceId, "workspace-033")
    }

    func testConfigurationRejectsNonHTTPOrigins() {
        XCTAssertNil(DesktopCabinetConfiguration(rawBaseURL: "file:///tmp/cabinet", headers: [:]))
        XCTAssertNil(DesktopCabinetConfiguration(rawBaseURL: "ftp://rec.2brain.dev", headers: [:]))
        XCTAssertNil(DesktopCabinetConfiguration(rawBaseURL: "not a url", headers: [:]))
    }

    func testConfiguredHeadersReuseDesktopMetadataAndRedactSecretValues() {
        let headers = DesktopCabinetConfiguration.configuredHeaders(from: [
            "TWO_BRAIN_REC_CLIENT_VERSION": "desktop-033",
            "TWO_BRAIN_REC_USER_ID": "user-033",
            "TWO_BRAIN_REC_WORKSPACE_ID": "workspace-033",
            "TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN": "secret-token"
        ])

        XCTAssertEqual(headers["X-Client-Version"], "desktop-033")
        XCTAssertEqual(headers["X-User-Id"], "user-033")
        XCTAssertEqual(headers["X-Workspace-Id"], "workspace-033")
        XCTAssertEqual(headers["Authorization"], "Bearer secret-token")
        XCTAssertEqual(
            DesktopCabinetConfiguration.sanitizedHeaderPreview(headers),
            [
                "Authorization": "<redacted>",
                "X-Client-Version": "desktop-033",
                "X-User-Id": "user-033",
                "X-Workspace-Id": "workspace-033"
            ]
        )
    }

    func testConfiguredFallsBackToPackagedProductionCabinetWithoutShellEnvironment() throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "DesktopCabinetConfigurationTests.packaged-default"))
        defaults.removePersistentDomain(forName: "DesktopCabinetConfigurationTests.packaged-default")

        let configuration = try XCTUnwrap(DesktopCabinetConfiguration.configured(from: [:], defaults: defaults))

        XCTAssertEqual(configuration.baseURL.absoluteString, "https://rec.2brain.pro")
        XCTAssertEqual(configuration.source, "packaged_default")
        XCTAssertEqual(configuration.meetingsURL().absoluteString, "https://rec.2brain.pro/desktop/meetings")
        XCTAssertGreaterThanOrEqual(configuration.loadTimeoutSeconds, 10)
        XCTAssertEqual(configuration.headers["X-Client-Version"], "local-macos")
        XCTAssertNil(configuration.headers["Authorization"])
        XCTAssertNil(configuration.headers["X-User-Id"])
    }

    func testConfiguredPrefersPersistedCabinetOriginBeforePackagedDefault() throws {
        let suiteName = "DesktopCabinetConfigurationTests.persisted-origin"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defaults.removePersistentDomain(forName: suiteName)
        defaults.set("https://pilot.rec.example/workspace/path", forKey: DesktopCabinetConfiguration.baseURLUserDefaultsKey)

        let configuration = try XCTUnwrap(DesktopCabinetConfiguration.configured(from: [:], defaults: defaults))

        XCTAssertEqual(configuration.baseURL.absoluteString, "https://pilot.rec.example")
        XCTAssertEqual(configuration.source, DesktopCabinetConfiguration.baseURLUserDefaultsKey)
    }

    func testConfiguredEnvironmentOriginOverridesPersistedOrigin() throws {
        let suiteName = "DesktopCabinetConfigurationTests.env-overrides-persisted"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defaults.removePersistentDomain(forName: suiteName)
        defaults.set("https://persisted.rec.example", forKey: DesktopCabinetConfiguration.baseURLUserDefaultsKey)

        let configuration = try XCTUnwrap(DesktopCabinetConfiguration.configured(
            from: [DesktopCabinetConfiguration.baseURLEnvironmentKey: "https://env.rec.example"],
            defaults: defaults
        ))

        XCTAssertEqual(configuration.baseURL.absoluteString, "https://env.rec.example")
        XCTAssertEqual(configuration.source, DesktopCabinetConfiguration.baseURLEnvironmentKey)
    }

    func testUnavailableMessagesDoNotExposeSecretsOrLivePaths() {
        let message = DesktopCabinetState.expiredSession.userMessage

        XCTAssertFalse(message.contains("/Users/"))
        XCTAssertFalse(message.localizedCaseInsensitiveContains("token"))
        XCTAssertFalse(message.localizedCaseInsensitiveContains("bearer"))
        XCTAssertTrue(message.localizedCaseInsensitiveContains("войдите"))
    }

    func testCalendarUnavailableMessagesExplainCredentialBoundaryAndManualRecording() {
        let states: [DesktopCabinetState] = [
            .notConfigured,
            .offline,
            .timeout,
            .expiredSession,
            .accessDenied,
            .notFound,
            .malformedResponse,
            .blockedRoute
        ]

        for state in states {
            let message = state.userMessage
            XCTAssertTrue(message.localizedCaseInsensitiveContains("mac не хранит пароли календаря"), "\(state)")
            XCTAssertTrue(message.localizedCaseInsensitiveContains("ручная запись"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("oauth"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("provider"), "\(state)")
        }
    }

    func testAllCabinetStateMessagesStayMetadataOnly() {
        let forbiddenFragments = [
            "/Users/",
            "file://",
            "token",
            "bearer",
            "cookie",
            "signed url",
            "presigned",
            ".wav",
            "transcript:",
            "krisp"
        ]

        for state in DesktopCabinetState.allCases {
            for fragment in forbiddenFragments {
                XCTAssertFalse(
                    state.userMessage.localizedCaseInsensitiveContains(fragment),
                    "\(state) leaked \(fragment)"
                )
            }
        }
    }

    func testHTTPStatusMappingKeepsAuthenticationFailuresTruthful() {
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 200))
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 302))
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 303))
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 304))
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 307))
        XCTAssertNil(DesktopCabinetState.state(forHTTPStatus: 308))
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 401), .expiredSession)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 403), .accessDenied)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 404), .notFound)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 502), .offline)
        XCTAssertEqual(DesktopCabinetState.state(forHTTPStatus: 418), .malformedResponse)
    }

    func testNonMainFrameCabinetResponsesDoNotChangeWorkspaceState() throws {
        let policy = DesktopCabinetNavigationResponsePolicy()
        let iconResponse = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/favicon.ico")),
            statusCode: 404,
            httpVersion: nil,
            headerFields: nil
        ))
        let opaqueResponse = URLResponse(
            url: try XCTUnwrap(URL(string: "data:text/plain,ok")),
            mimeType: "text/plain",
            expectedContentLength: 2,
            textEncodingName: nil
        )

        XCTAssertEqual(policy.decision(forNavigationResponse: iconResponse, isForMainFrame: false), .allow)
        XCTAssertEqual(policy.decision(forNavigationResponse: opaqueResponse, isForMainFrame: false), .allow)
    }

    func testMainFrameCabinetResponsesStillDriveUnavailableState() throws {
        let policy = DesktopCabinetNavigationResponsePolicy()
        let expiredSession = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings")),
            statusCode: 401,
            httpVersion: nil,
            headerFields: nil
        ))
        let opaqueResponse = URLResponse(
            url: try XCTUnwrap(URL(string: "data:text/plain,ok")),
            mimeType: "text/plain",
            expectedContentLength: 2,
            textEncodingName: nil
        )

        XCTAssertEqual(
            policy.decision(forNavigationResponse: expiredSession, isForMainFrame: true),
            .cancel(.expiredSession)
        )
        XCTAssertEqual(
            policy.decision(forNavigationResponse: opaqueResponse, isForMainFrame: true),
            .cancel(.malformedResponse)
        )
    }

    func testNavigationCancellationDoesNotOverwriteHTTPFailureState() {
        let cancelled = NSError(domain: NSURLErrorDomain, code: NSURLErrorCancelled)

        XCTAssertEqual(
            DesktopCabinetState.state(forNavigationError: cancelled, currentState: .expiredSession),
            .expiredSession
        )
        XCTAssertEqual(
            DesktopCabinetState.state(forNavigationError: cancelled, currentState: .blockedRoute),
            .blockedRoute
        )
    }

    func testWebKitPolicyCancellationDoesNotOverwriteCabinetFailureState() {
        let interruptedByPolicy = NSError(domain: "WebKitErrorDomain", code: 102)

        XCTAssertEqual(
            DesktopCabinetState.state(forNavigationError: interruptedByPolicy, currentState: .expiredSession),
            .expiredSession
        )
        XCTAssertEqual(
            DesktopCabinetState.state(forNavigationError: interruptedByPolicy, currentState: .accessDenied),
            .accessDenied
        )
        XCTAssertEqual(
            DesktopCabinetState.state(forNavigationError: interruptedByPolicy, currentState: .blockedRoute),
            .blockedRoute
        )
        XCTAssertEqual(
            DesktopCabinetState.state(forNavigationError: interruptedByPolicy, currentState: .loading),
            .loading
        )
    }

    func testNavigationTimeoutStillMapsToTimeout() {
        let timeout = NSError(domain: NSURLErrorDomain, code: NSURLErrorTimedOut)

        XCTAssertEqual(
            DesktopCabinetState.state(forNavigationError: timeout, currentState: .loading),
            .timeout
        )
    }

    func testWorkspaceShowsEmbeddedSurfaceOnlyForLoadingAndReadyStates() {
        XCTAssertTrue(DesktopCabinetState.loading.shouldShowEmbeddedSurface)
        XCTAssertTrue(DesktopCabinetState.ready.shouldShowEmbeddedSurface)

        for state in DesktopCabinetState.allCases where state != .loading && state != .ready {
            XCTAssertFalse(state.shouldShowEmbeddedSurface, "\(state)")
        }
    }

    func testLoginRecoveryRouteIsVisibleButNeverCountsAsReadyCabinet() throws {
        let configuration = try XCTUnwrap(DesktopCabinetConfiguration(
            rawBaseURL: "https://rec.2brain.dev",
            headers: [:]
        ))
        let login = DesktopCabinetWorkspace.loginRoute(configuration: configuration)
        let presentation = DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: true,
            cabinetState: EmbeddedCabinetWebView.finishedState(for: .authLogin)
        )

        XCTAssertTrue(DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: .expiredSession,
            currentRoute: login,
            initialRoute: nil,
            configuration: configuration
        ))
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authLogin), .expiredSession)
        XCTAssertEqual(EmbeddedCabinetWebView.finishedState(for: .authSignup), .expiredSession)
        XCTAssertNotEqual(presentation.menuStatusText, "Кабинет доступен")
        XCTAssertNotEqual(presentation.systemImage, "checkmark.circle")
    }
}
#endif
