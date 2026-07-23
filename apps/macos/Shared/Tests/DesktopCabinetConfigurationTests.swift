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
            "GRAF_CLIENT_VERSION": "desktop-033",
            "GRAF_USER_ID": "user-033",
            "GRAF_WORKSPACE_ID": "workspace-033",
            "GRAF_UPLOAD_BEARER_TOKEN": "secret-token"
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

    func testConfiguredAcceptsLegacyTwoBrainCabinetOrigin() throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "DesktopCabinetConfigurationTests.legacy-env"))
        defaults.removePersistentDomain(forName: "DesktopCabinetConfigurationTests.legacy-env")

        let configuration = try XCTUnwrap(DesktopCabinetConfiguration.configured(
            from: [DesktopCabinetConfiguration.legacyBaseURLEnvironmentKey: "https://legacy.rec.example"],
            defaults: defaults,
            includePackagedDefault: false
        ))

        XCTAssertEqual(configuration.baseURL.absoluteString, "https://legacy.rec.example")
        XCTAssertEqual(configuration.source, DesktopCabinetConfiguration.legacyBaseURLEnvironmentKey)
    }

    func testUnavailableMessagesDoNotExposeSecretsOrLivePaths() {
        let message = DesktopCabinetState.expiredSession.userMessage

        XCTAssertFalse(message.contains("/Users/"))
        XCTAssertFalse(message.localizedCaseInsensitiveContains("token"))
        XCTAssertFalse(message.localizedCaseInsensitiveContains("bearer"))
        XCTAssertTrue(message.localizedCaseInsensitiveContains("войдите"))
    }

    func testUnavailableMessagesStayHumanAndMetadataOnly() {
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
            XCTAssertFalse(message.localizedCaseInsensitiveContains("сервером rec"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("пароли календаря"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("oauth"), "\(state)")
            XCTAssertFalse(message.localizedCaseInsensitiveContains("provider"), "\(state)")
        }

        XCTAssertTrue(DesktopCabinetState.offline.userMessage.contains("Запись на этом Mac остаётся доступна"))
        XCTAssertEqual(DesktopCabinetState.offline.recoveryActionTitle, "Повторить")
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

    func testAttachmentResponseBecomesNativeDownloadInsteadOfCabinetNavigation() throws {
        let policy = DesktopCabinetNavigationResponsePolicy(
            routePolicy: DesktopCabinetRoutePolicy(
                baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
            )
        )
        let response = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio")),
            statusCode: 200,
            httpVersion: nil,
            headerFields: [
                "Content-Disposition": "attachment; filename=meeting-review.m4a",
                "Content-Length": "42"
            ]
        ))

        XCTAssertEqual(
            policy.decision(forNavigationResponse: response, isForMainFrame: true),
            .download
        )
    }

    func testAttachmentResponseStillSurfacesAuthenticationFailure() throws {
        let policy = DesktopCabinetNavigationResponsePolicy(
            routePolicy: DesktopCabinetRoutePolicy(
                baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
            )
        )
        let response = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio")),
            statusCode: 401,
            httpVersion: nil,
            headerFields: ["Content-Disposition": "attachment; filename=login.html"]
        ))

        XCTAssertEqual(
            policy.decision(forNavigationResponse: response, isForMainFrame: true),
            .cancel(.expiredSession)
        )
    }

    func testArtifactResponseStillSurfacesWorkspaceReselection() throws {
        let policy = DesktopCabinetNavigationResponsePolicy(
            routePolicy: DesktopCabinetRoutePolicy(
                baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
            )
        )
        let response = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio")),
            statusCode: 401,
            httpVersion: nil,
            headerFields: [
                "X-GRAF-Cabinet-Recovery": "reselect-space",
                "Content-Disposition": "attachment; filename=login.html"
            ]
        ))

        XCTAssertEqual(
            policy.decision(forNavigationResponse: response, isForMainFrame: true),
            .cancel(.workspaceReselectionRequired)
        )
    }

    func testAttachmentOnOrdinaryCabinetDocumentDoesNotBecomeDownload() throws {
        let policy = DesktopCabinetNavigationResponsePolicy(
            routePolicy: DesktopCabinetRoutePolicy(
                baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
            )
        )
        let response = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033")),
            statusCode: 200,
            httpVersion: nil,
            headerFields: ["Content-Disposition": "attachment; filename=unexpected.html"]
        ))

        XCTAssertEqual(
            policy.decision(forNavigationResponse: response, isForMainFrame: true),
            .allow
        )
    }

    func testArtifactFailuresDoNotReplaceTheMeetingDocument() throws {
        let policy = DesktopCabinetNavigationResponsePolicy(
            routePolicy: DesktopCabinetRoutePolicy(
                baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
            )
        )
        let artifactURL = try XCTUnwrap(
            URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio")
        )

        for statusCode in [403, 404, 409, 503] {
            let response = try XCTUnwrap(HTTPURLResponse(
                url: artifactURL,
                statusCode: statusCode,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/problem+json"]
            ))

            XCTAssertEqual(
                policy.decision(forNavigationResponse: response, isForMainFrame: true),
                .cancelResource,
                "status=\(statusCode)"
            )
        }
    }

    func testArtifactSuccessWithoutAttachmentDoesNotReplaceTheMeetingDocument() throws {
        let policy = DesktopCabinetNavigationResponsePolicy(
            routePolicy: DesktopCabinetRoutePolicy(
                baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
            )
        )
        let response = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/api/v1/cabinet/meetings/meeting-033/downloads/audio")),
            statusCode: 200,
            httpVersion: nil,
            headerFields: ["Content-Type": "audio/mp4"]
        ))

        XCTAssertEqual(
            policy.decision(forNavigationResponse: response, isForMainFrame: true),
            .cancelResource
        )
    }

    func testOrdinaryDocumentFailureStillTransitionsToUnavailableState() throws {
        let policy = DesktopCabinetNavigationResponsePolicy(
            routePolicy: DesktopCabinetRoutePolicy(
                baseURL: try XCTUnwrap(URL(string: "https://rec.2brain.dev"))
            )
        )
        let response = try XCTUnwrap(HTTPURLResponse(
            url: try XCTUnwrap(URL(string: "https://rec.2brain.dev/desktop/meetings/meeting-033")),
            statusCode: 404,
            httpVersion: nil,
            headerFields: nil
        ))

        XCTAssertEqual(
            policy.decision(forNavigationResponse: response, isForMainFrame: true),
            .cancel(.notFound)
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
        XCTAssertNotEqual(presentation.tileTitle, "Сервер доступен")
        XCTAssertNotEqual(presentation.systemImage, "checkmark.circle")
    }
}
#endif
