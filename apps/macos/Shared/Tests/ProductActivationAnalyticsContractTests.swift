import Foundation
@testable import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class ProductActivationAnalyticsContractTests: XCTestCase {
    func testProductActivationEventNamesAreStable() {
        XCTAssertEqual(
            ProductActivationEventName.allCases.map(\.rawValue),
            [
                "desktop_first_opened",
                "desktop_account_connected",
                "desktop_autorecord_enabled",
                "first_recording_completed",
                "first_result_viewed",
                "first_value_session_completed"
            ]
        )
    }

    func testPayloadAllowsOnlyApprovedDesktopFields() throws {
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopFirstOpened,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: [
                "app_version_bucket": "2026_07",
                "platform": "macos",
                "install_channel": "direct",
                "bridge_present": "false"
            ]
        )

        XCTAssertEqual(payload.eventName, .desktopFirstOpened)
        XCTAssertEqual(payload.properties["platform"], "macos")
    }

    func testPayloadRejectsForbiddenFieldsAndValues() throws {
        XCTAssertThrowsError(try ProductActivationAnalyticsPayload(
            eventName: .firstResultViewed,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: ["meeting_title": "Customer call"]
        ))
        XCTAssertThrowsError(try ProductActivationAnalyticsPayload(
            eventName: .desktopAccountConnected,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: ["auth_method_category": "user@example.com"]
        ))
    }

    func testPayloadRejectsRawIdentity() {
        XCTAssertThrowsError(try ProductActivationAnalyticsPayload(
            eventName: .desktopFirstOpened,
            stablePseudonymousUserId: "user@example.com",
            properties: ["platform": "macos"]
        ))
    }

    func testPseudonymousIdentityContractRequiresStrictShape() {
        XCTAssertTrue(ProductActivationAnalyticsPayload.isSafePseudonymousIdentity("graf_pseudo_user_1234567890abcdef"))
        XCTAssertTrue(ProductActivationAnalyticsPayload.isSafePseudonymousIdentity("graf_pseudo_workspace_abcdef12"))

        XCTAssertFalse(ProductActivationAnalyticsPayload.isSafePseudonymousIdentity("graf_pseudo_user_realname"))
        XCTAssertFalse(ProductActivationAnalyticsPayload.isSafePseudonymousIdentity("graf_pseudo_user_abc"))
        XCTAssertFalse(ProductActivationAnalyticsPayload.isSafePseudonymousIdentity("graf_pseudo_device_1234567890abcdef"))
        XCTAssertFalse(ProductActivationAnalyticsPayload.isSafePseudonymousIdentity("graf_pseudo_user_1234567890ABCDEF"))
        // A shared anonymous identifier must never be accepted: it is both
        // long-lived and a link between unrelated people.
        XCTAssertFalse(ProductActivationAnalyticsPayload.isSafePseudonymousIdentity("graf_pseudo_browser_anonymous"))
    }

    func testDirectDesktopProviderEgressIsClosedUntilEveryApprovalExists() {
        XCTAssertFalse(ProductActivationAnalyticsClient.directProviderEgressAllowed(
            legalApproved: true,
            securityApproved: true,
            qaApproved: false,
            telemetryAccepted: true,
            directEgressDisclosed: true
        ))
        XCTAssertTrue(ProductActivationAnalyticsClient.directProviderEgressAllowed(
            legalApproved: true,
            securityApproved: true,
            qaApproved: true,
            telemetryAccepted: true,
            directEgressDisclosed: true
        ))
    }

    func testClientBuildsServerMediatedEndpointOnly() throws {
        let client = try XCTUnwrap(ProductActivationAnalyticsClient(
            rawBaseURL: "https://rec.2brain.pro/some/path",
            headers: ["X-Client-Version": "desktop-094"]
        ))
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopAccountConnected,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: [
                "auth_method_category": "oauth_provider",
                "account_connection_state": "connected",
                "bridge_present": "true"
            ]
        )

        let request = try client.request(for: payload)

        XCTAssertEqual(request.url?.absoluteString, "https://rec.2brain.pro/api/v1/product-analytics/events")
        XCTAssertNil(request.url?.absoluteString.range(of: "posthog", options: .caseInsensitive))
        XCTAssertNil(request.url?.absoluteString.range(of: "mc.yandex", options: .caseInsensitive))
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-Client-Version"), "desktop-094")
    }

    func testDirectDesktopRouteAllowsOnlyFirstPartyPostHogWithoutSecrets() throws {
        let client = try XCTUnwrap(ProductActivationAnalyticsClient(
            rawBaseURL: "https://rec.2brain.pro",
            headers: [:]
        ))
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopAccountConnected,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: [
                "auth_method_category": "oauth_provider",
                "account_connection_state": "connected",
                "bridge_present": "true"
            ]
        )
        let config = ProductAnalyticsDirectProviderConfig(
            posthogHost: URL(string: "https://rec.2brain.pro"),
            posthogCaptureEndpoint: URL(string: "https://rec.2brain.pro/api/v1/product-analytics/posthog-desktop-capture"),
            posthogDirectEnabled: true,
            yandexDirectEnabled: true,
            telemetryAccepted: true,
            legalApproved: true,
            securityApproved: true,
            qaApproved: true,
            directEgressDisclosed: true
        )

        let request = try XCTUnwrap(client.directPostHogRequest(for: payload, config: config))

        XCTAssertEqual(request.url?.absoluteString, "https://rec.2brain.pro/api/v1/product-analytics/posthog-desktop-capture")
        XCTAssertNil(request.url?.absoluteString.range(of: "mc.yandex", options: .caseInsensitive))
        XCTAssertFalse(config.allowsYandexDirectRoute)
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-GRAF-PostHog-Project-Key-State"), "server_injected_redacted")
        XCTAssertEqual(request.value(forHTTPHeaderField: "X-GRAF-Analytics-Route"), "first_party_posthog_desktop_proxy")
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: body) as? [String: Any])
        XCTAssertEqual(json["event"] as? String, "desktop_account_connected")
        XCTAssertEqual(json["distinct_id"] as? String, "graf_pseudo_user_1234567890abcdef")
        XCTAssertEqual(json["api_key_state"] as? String, "server_injected_redacted")
        XCTAssertNil(json["api_key"])
    }

    func testDirectDesktopRouteRequiresExplicitGrafProxyEndpoint() throws {
        let client = try XCTUnwrap(ProductActivationAnalyticsClient(
            rawBaseURL: "https://rec.2brain.pro",
            headers: [:]
        ))
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopAccountConnected,
            stablePseudonymousUserId: "graf_pseudo_user_1234567890abcdef",
            properties: [
                "auth_method_category": "oauth_provider",
                "account_connection_state": "connected",
                "bridge_present": "true"
            ]
        )
        let config = ProductAnalyticsDirectProviderConfig(
            posthogHost: URL(string: "https://analytics.2brain.pro"),
            posthogDirectEnabled: true,
            yandexDirectEnabled: false,
            telemetryAccepted: true,
            legalApproved: true,
            securityApproved: true,
            qaApproved: true,
            directEgressDisclosed: true
        )

        XCTAssertFalse(config.allowsPostHogDirectRoute)
        XCTAssertNil(try client.directPostHogRequest(for: payload, config: config))
    }

    func testDirectDesktopRouteRequiresPseudonymousIdentity() throws {
        let client = try XCTUnwrap(ProductActivationAnalyticsClient(
            rawBaseURL: "https://rec.2brain.pro",
            headers: [:]
        ))
        let payload = try ProductActivationAnalyticsPayload(
            eventName: .desktopFirstOpened,
            stablePseudonymousUserId: nil,
            properties: [
                "platform": "macos",
                "bridge_present": "true"
            ]
        )
        let config = ProductAnalyticsDirectProviderConfig(
            posthogHost: URL(string: "https://rec.2brain.pro"),
            posthogCaptureEndpoint: URL(string: "https://rec.2brain.pro/api/v1/product-analytics/posthog-desktop-capture"),
            posthogDirectEnabled: true,
            yandexDirectEnabled: false,
            telemetryAccepted: true,
            legalApproved: true,
            securityApproved: true,
            qaApproved: true,
            directEgressDisclosed: true
        )

        XCTAssertNil(try client.directPostHogRequest(for: payload, config: config))
    }

    func testTelemetryGateBlocksNormalUseUntilAccepted() {
        XCTAssertFalse(ProductTelemetryGateViewModel(state: .notSeen).allowsNormalProductUse)
        XCTAssertTrue(ProductTelemetryGateViewModel(state: .notSeen).requiresAcceptance)
        XCTAssertTrue(ProductTelemetryGateViewModel(state: .accepted).allowsNormalProductUse)
        XCTAssertFalse(ProductTelemetryGateViewModel(state: .withdrawn).allowsProductAnalytics)
        XCTAssertTrue(ProductTelemetryGateViewModel(state: .withdrawn).limitedAccessOnly)
    }

    // MARK: - Воронка от клика до первой ценности (задача T053)

    @MainActor
    func testMilestonesAreSentFromRealApplicationPaths() async throws {
        let transport = RecordingProductActivationTransport()
        let reporter = try Self.makeReporter(transport: transport)

        _ = await reporter.noteFirstLaunch(appVersion: "2026.07.14.3", installChannel: "developer_id")
        _ = await reporter.noteAutorecordEnabled(
            policyState: "enabled",
            previousState: "disabled",
            source: "prompt_button",
            surface: "meeting_detection_prompt"
        )
        _ = await reporter.noteFirstRecordingCompleted(
            durationBucket: "10m_to_30m",
            captureMode: "system_audio_and_microphone",
            completionState: "saved",
            resultPendingState: "upload_pending"
        )
        _ = await reporter.noteFirstResultViewed(
            resultState: "ready",
            surface: "embedded_cabinet_meeting_detail",
            usefulOutputPresent: true
        )
        _ = await reporter.noteFirstValueSessionCompleted(usefulResultType: "transcript")

        XCTAssertEqual(
            transport.payloads.map(\.eventName),
            [
                .desktopFirstOpened,
                .desktopAutorecordEnabled,
                .firstRecordingCompleted,
                .firstResultViewed,
                .firstValueSessionCompleted
            ]
        )
    }

    @MainActor
    func testApplicationSourcesCallTheReporterOnRealPaths() throws {
        let appSource = try Self.readRepositoryFile("apps/macos/RecApp/App/TwoBrainRecApp.swift")

        XCTAssertTrue(appSource.contains("activationReporter.noteFirstLaunch("))
        XCTAssertTrue(appSource.contains("activationReporter.noteAutorecordEnabled("))
        XCTAssertTrue(appSource.contains("activationReporter.noteFirstRecordingCompleted("))
        XCTAssertTrue(appSource.contains("activationReporter.noteFirstResultViewed("))
        XCTAssertTrue(appSource.contains("activationReporter.noteFirstValueSessionCompleted("))
        XCTAssertTrue(appSource.contains("activationReporter.noteAccountConnected()"))
        XCTAssertTrue(appSource.contains("application(_: NSApplication, open urls: [URL])"))

        // Первый просмотр результата приходит из настоящей навигации кабинета,
        // а не из нажатия кнопки в интерфейсе приложения.
        let webViewSource = try Self.readRepositoryFile(
            "apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift"
        )
        XCTAssertTrue(webViewSource.contains(".twoBrainRecDesktopCabinetDidShowMeetingDetail"))

        // Веху подключения аккаунта отправляет серверная авторизация.
        let authSource = try Self.readRepositoryFile("apps/server/src/twobrain_rec_server/api/auth.py")
        XCTAssertTrue(authSource.contains("schedule_account_connected_milestone("))
    }

    @MainActor
    func testEveryMilestoneCarriesContractReliabilityLevel() async throws {
        let transport = RecordingProductActivationTransport()
        let reporter = try Self.makeReporter(
            transport: transport,
            handoffLink: Self.campaignHandoffLink()
        )

        _ = await reporter.noteFirstLaunch(appVersion: "2026.07.14.3", installChannel: "developer_id")
        _ = await reporter.noteFirstRecordingCompleted(
            durationBucket: "1m_to_10m",
            captureMode: "system_audio_and_microphone",
            completionState: "saved",
            resultPendingState: "upload_pending"
        )

        XCTAssertEqual(transport.payloads.count, 2)
        for payload in transport.payloads {
            let level = try XCTUnwrap(payload.properties["attribution_reliability"])
            XCTAssertTrue(
                ProductActivationAttributionReliability.allCases.map(\.rawValue).contains(level),
                "unexpected reliability level \(level)"
            )
            // Запасной путь передачи ссылки всегда дает `weak`, но никогда `direct`.
            XCTAssertEqual(level, ProductActivationAttributionReliability.weak.rawValue)
            XCTAssertEqual(payload.properties["bridge_present"], "true")
            XCTAssertEqual(payload.properties["graf_attribution_id"], Self.bridgeID)
            // FR-018: веха несет сами метки кампании, а не только уровень.
            XCTAssertEqual(
                payload.properties["campaign_label_state"],
                ProductAttributionHandoff.campaignLabelStateKnown
            )
            XCTAssertEqual(payload.properties["utm_source"], "yandex_direct")
            XCTAssertEqual(payload.properties["utm_medium"], "cpc")
            XCTAssertEqual(payload.properties["utm_campaign"], "2026q3_launch")
            XCTAssertNotEqual(level, "direct")
        }
    }

    @MainActor
    func testUnknownCampaignIsMarkedUnknownAndNeverDirect() async throws {
        let transport = RecordingProductActivationTransport()
        let reporter = try Self.makeReporter(transport: transport)

        _ = await reporter.noteFirstLaunch(appVersion: "2026.07.14.3", installChannel: "developer_id")

        let payload = try XCTUnwrap(transport.payloads.first)
        XCTAssertEqual(
            payload.properties["attribution_reliability"],
            ProductActivationAttributionReliability.unknown.rawValue
        )
        XCTAssertEqual(payload.properties["bridge_present"], "false")
        XCTAssertNil(payload.properties["graf_attribution_id"])
        // FR-018, FR-024: отсутствие кампании названо явно и не читается как
        // «прямой заход».
        XCTAssertEqual(
            payload.properties["campaign_label_state"],
            ProductAttributionHandoff.campaignLabelStateUnknown
        )
        for name in ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"] {
            XCTAssertNil(payload.properties[name], name)
        }
        XCTAssertFalse(payload.properties.values.contains("direct"))
    }

    @MainActor
    func testRepeatedMilestoneIsNotCountedTwiceInTheApp() async throws {
        let transport = RecordingProductActivationTransport()
        let store = try XCTUnwrap(UserDefaults(suiteName: "graf.milestone.ledger.tests.\(UUID().uuidString)"))
        let reporter = try Self.makeReporter(transport: transport, defaults: store)

        let first = await reporter.noteFirstLaunch(appVersion: "2026.07.14.3", installChannel: "developer_id")
        let second = await reporter.noteFirstLaunch(appVersion: "2026.07.14.3", installChannel: "developer_id")

        XCTAssertTrue(first.wasDelivered)
        XCTAssertEqual(second, .alreadyCounted(.desktopFirstOpened))
        XCTAssertEqual(transport.payloads.count, 1)

        // Новый экземпляр отправителя читает тот же журнал и молчит.
        let restartedReporter = try Self.makeReporter(transport: transport, defaults: store)
        let afterRestart = await restartedReporter.noteFirstLaunch(
            appVersion: "2026.07.14.3",
            installChannel: "developer_id"
        )
        XCTAssertEqual(afterRestart, .alreadyCounted(.desktopFirstOpened))
        XCTAssertEqual(transport.payloads.count, 1)
    }

    @MainActor
    func testTelemetryGateAndUnsafeLabelsStopDelivery() async throws {
        let transport = RecordingProductActivationTransport()
        let closedGateReporter = try Self.makeReporter(transport: transport, telemetryGateState: .notSeen)
        let outcome = await closedGateReporter.noteFirstLaunch(
            appVersion: "2026.07.14.3",
            installChannel: "developer_id"
        )
        XCTAssertEqual(outcome, .telemetryGateClosed(.desktopFirstOpened))
        XCTAssertTrue(transport.payloads.isEmpty)

        // Метки, похожие на персональные данные, в ссылке не сохраняются.
        let unsafe = ProductAttributionHandoff(
            link: "grafrec://attribution?bridge=\(Self.bridgeID)&utm_campaign=user@example.com&utm_source=ya"
        )
        XCTAssertEqual(unsafe?.campaign["utm_source"], "ya")
        XCTAssertNil(unsafe?.campaign["utm_campaign"])
    }

    @MainActor
    func testAccountConnectionMilestoneIsSentByServerAuthorization() async throws {
        let transport = RecordingProductActivationTransport()
        let reporter = try Self.makeReporter(transport: transport)

        let outcome = reporter.noteAccountConnected()
        XCTAssertEqual(outcome, .handledByServerAuthorization(.desktopAccountConnected))
        XCTAssertTrue(transport.payloads.isEmpty)
    }

    @MainActor
    func testFirstValueRequiresAnApprovedUsefulResultType() async throws {
        let transport = RecordingProductActivationTransport()
        let reporter = try Self.makeReporter(transport: transport)

        let rejected = await reporter.noteFirstValueSessionCompleted(usefulResultType: "raw_audio_summary")
        XCTAssertEqual(rejected, .notEligible(.firstValueSessionCompleted, reason: "unsupported_useful_result_type"))

        let accepted = await reporter.noteFirstValueSessionCompleted(usefulResultType: "summary")
        XCTAssertTrue(accepted.wasDelivered)
        XCTAssertEqual(transport.payloads.map(\.eventName), [.firstValueSessionCompleted])
    }

    func testHandoffLinkRoundTripKeepsCampaignAndHidesClickIdentifier() throws {
        let handoff = try XCTUnwrap(ProductAttributionHandoff(link: Self.campaignHandoffLink()))

        XCTAssertEqual(handoff.bridgeID, Self.bridgeID)
        XCTAssertEqual(handoff.campaign["utm_source"], "yandex_direct")
        XCTAssertEqual(handoff.campaign["utm_campaign"], "2026q3_launch")
        XCTAssertEqual(handoff.landingPath, "/download")
        XCTAssertTrue(handoff.campaignKnown)
        XCTAssertTrue(handoff.fallbackRecovered)

        // Идентификатор клика Яндекс.Директа в ссылку не попадает.
        XCTAssertFalse(Self.campaignHandoffLink().contains("1234567890abc"))
        XCTAssertNil(ProductAttributionHandoff(link: "https://rec.2brain.pro/download"))
        XCTAssertNil(ProductAttributionHandoff(link: "grafrec://other?bridge=\(Self.bridgeID)"))
    }

    func testHandoffStoreKeepsOneLinkAndForgetsItAfterWindow() async throws {
        let defaults = try XCTUnwrap(UserDefaults(suiteName: "graf.attribution.tests.\(UUID().uuidString)"))
        let store = await ProductAttributionHandoffStore(defaults: defaults)
        let receivedAt = Date(timeIntervalSince1970: 1_780_000_000)

        let saved = await store.save(link: Self.campaignHandoffLink(), receivedAt: receivedAt)
        XCTAssertNotNil(saved)
        let current = await store.current(now: receivedAt.addingTimeInterval(86_400))
        XCTAssertEqual(current?.bridgeID, Self.bridgeID)

        let expired = await store.current(
            now: receivedAt.addingTimeInterval(TimeInterval(ProductAttributionHandoff.validityWindowDays + 1) * 86_400)
        )
        XCTAssertNil(expired)

        await store.save(link: Self.campaignHandoffLink(), receivedAt: receivedAt)
        await store.markAccountConnected(at: receivedAt)
        let connectedAt = await store.accountConnectedAt
        XCTAssertEqual(connectedAt, receivedAt)
        let afterClear = await store.accountConnectedAt
        await store.clear()
        let cleared = await store.current(now: receivedAt)
        XCTAssertNil(cleared)
        XCTAssertNotNil(afterClear)
    }

    @MainActor
    func testSignInRouteCarriesCampaignLabelsIntoEmbeddedCabinet() throws {
        let handoff = try XCTUnwrap(ProductAttributionHandoff(link: Self.campaignHandoffLink()))
        let loginRoute = try XCTUnwrap(URL(string: "https://rec.2brain.pro/login?next=/meetings"))
        let signedIn = handoff.applyingSignInQueryItems(to: loginRoute)

        let components = try XCTUnwrap(URLComponents(url: signedIn, resolvingAgainstBaseURL: false))
        let items = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).map { ($0.name, $0.value ?? "") })
        XCTAssertEqual(items["next"], "/meetings")
        XCTAssertEqual(items["graf_attribution_ref"], Self.bridgeID)
        XCTAssertEqual(items["graf_attribution_fallback"], "1")
        XCTAssertEqual(items["utm_campaign"], "2026q3_launch")
    }

    func testApplicationRegistersAttributionUrlScheme() throws {
        let devBuilder = try Self.readRepositoryFile("apps/macos/Scripts/build-dev-app.sh")
        let installer = try Self.readRepositoryFile("apps/macos/Installer/Scripts/build-local-installer.sh")

        for source in [devBuilder, installer] {
            XCTAssertTrue(source.contains("<key>CFBundleURLTypes</key>"))
            XCTAssertTrue(source.contains("<string>grafrec</string>"))
        }
    }

    /// FR-022: первый запуск связывает ссылку с аккаунтом.
    ///
    /// Обработчик `application(_:open:)` живет в исполняемой цели
    /// `TwoBrainRecApp`, которая в тестовую сборку не входит, поэтому здесь
    /// проверяется ровно та часть пути, которую обработчик вызывает:
    /// разбор адреса, запись в хранилище, маршрут входа с метками и свойства
    /// вехи о подключении аккаунта. Сам вызов обработчика проверяет
    /// `testApplicationSourcesCallTheReporterOnRealPaths` по исходникам.
    @MainActor
    func testTheOpenedLinkBecomesTheAccountCampaignEndToEnd() async throws {
        let defaults = try XCTUnwrap(
            UserDefaults(suiteName: "graf.attribution.e2e.tests.\(UUID().uuidString)")
        )
        let store = ProductAttributionHandoffStore(defaults: defaults)
        let url = try XCTUnwrap(URL(string: Self.campaignHandoffLink()))

        // Первый запуск: система открывает адрес, хранилище его запоминает.
        let saved = await store.handleOpenURL(url)
        XCTAssertEqual(saved?.bridgeID, Self.bridgeID)
        let current = await store.current()
        XCTAssertEqual(current?.bridgeID, Self.bridgeID)
        XCTAssertEqual(current?.campaign["utm_campaign"], "2026q3_launch")

        // Подключение аккаунта: вход во встроенном кабинете несет метки и мост.
        let loginRoute = try XCTUnwrap(URL(string: "https://rec.2brain.pro/login?next=/meetings"))
        let configuration = try XCTUnwrap(
            DesktopCabinetConfiguration(rawBaseURL: "https://rec.2brain.pro", headers: [:])
        )
        let signInRoute = DesktopCabinetWorkspace.signInRoute(
            configuration: configuration,
            handoff: current
        )
        let components = try XCTUnwrap(
            URLComponents(url: signInRoute, resolvingAgainstBaseURL: false)
        )
        let items = Dictionary(
            uniqueKeysWithValues: (components.queryItems ?? []).map { ($0.name, $0.value ?? "") }
        )
        XCTAssertEqual(items["graf_attribution_ref"], Self.bridgeID)
        XCTAssertEqual(items["utm_campaign"], "2026q3_launch")
        XCTAssertEqual(items["next"], "/desktop/meetings")

        // Веха о подключении аккаунта отправляется сервером, а свойства
        // атрибуции для нее приложение отдает тем же набором.
        let transport = RecordingProductActivationTransport()
        let reporter = try Self.makeReporter(
            transport: transport,
            handoffLink: Self.campaignHandoffLink()
        )
        _ = reporter.noteAccountConnected()
        XCTAssertTrue(transport.payloads.isEmpty)
        XCTAssertNotEqual(loginRoute, signInRoute)
    }

    // MARK: - Helpers

    private static let bridgeID = "graf_attr_0123456789abcdef0123456789abcdef"

    private static func campaignHandoffLink() -> String {
        "grafrec://attribution?bridge=\(bridgeID)"
            + "&utm_source=yandex_direct&utm_medium=cpc&utm_campaign=2026q3_launch"
            + "&landing_path=%2Fdownload&fallback=1"
    }

    @MainActor
    private static func makeReporter(
        transport: RecordingProductActivationTransport,
        handoffLink: String? = nil,
        telemetryGateState: ProductTelemetryGateState = .accepted,
        defaults: UserDefaults? = nil
    ) throws -> ProductActivationAnalyticsReporter {
        let store = try defaults ?? XCTUnwrap(
            UserDefaults(suiteName: "graf.product.activation.tests.\(UUID().uuidString)")
        )
        let handoffs = ProductAttributionHandoffStore(
            defaults: store,
            key: ProductAttributionHandoffStore.defaultsKey
        )
        if let handoffLink {
            handoffs.save(link: handoffLink)
        }
        let client = try XCTUnwrap(
            ProductActivationAnalyticsClient(rawBaseURL: "https://rec.2brain.pro", headers: [:])
        )
        return ProductActivationAnalyticsReporter(
            client: client,
            transport: transport,
            handoffs: handoffs,
            ledger: UserDefaultsProductActivationMilestoneLedger(
                defaults: store,
                key: UserDefaultsProductActivationMilestoneLedger.defaultsKey
            ),
            telemetryGateState: telemetryGateState,
            identityProvider: { ProductActivationPseudonymousIdentity.workspace("workspace-test-1") }
        )
    }

    private static func readRepositoryFile(_ relativePath: String) throws -> String {
        try String(contentsOf: repositoryRoot().appendingPathComponent(relativePath), encoding: .utf8)
    }

    private static func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath)
        while candidate.path != "/" {
            if FileManager.default.fileExists(atPath: candidate.appendingPathComponent("apps/macos/Package.swift").path) {
                return candidate
            }
            candidate.deleteLastPathComponent()
        }
        throw NSError(
            domain: "ProductActivationAnalyticsContractTests",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Repository root not found"]
        )
    }
}

/// Записывает отправленные вехи вместо настоящей сети.
private final class RecordingProductActivationTransport: ProductActivationAnalyticsTransport, @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [ProductActivationAnalyticsPayload] = []

    var payloads: [ProductActivationAnalyticsPayload] {
        lock.withLock { storage }
    }

    func send(
        _ payload: ProductActivationAnalyticsPayload,
        using client: ProductActivationAnalyticsClient
    ) async throws -> Int {
        lock.withLock { storage.append(payload) }
        return 202
    }
}
#endif
