import CryptoKit
import Foundation
import TwoBrainRecShared

/// Канал доставки вехи на сервер.
public protocol ProductActivationAnalyticsTransport: Sendable {
    func send(
        _ payload: ProductActivationAnalyticsPayload,
        using client: ProductActivationAnalyticsClient
    ) async throws -> Int
}

/// Обычная отправка через сервер: приложение не ходит к счётчикам напрямую.
public struct URLSessionProductActivationAnalyticsTransport: ProductActivationAnalyticsTransport {
    public init() {}

    public func send(
        _ payload: ProductActivationAnalyticsPayload,
        using client: ProductActivationAnalyticsClient
    ) async throws -> Int {
        let request = try client.request(for: payload)
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        return http.statusCode
    }
}

/// Журнал уже отправленных первых вех (FR-025).
///
/// Повторная отправка одной и той же вехи не должна считаться второй раз,
/// поэтому приложение помнит отправленное и после перезапуска.
@MainActor
public protocol ProductActivationMilestoneLedger: AnyObject {
    func hasCounted(_ key: String) -> Bool
    func record(_ key: String)
    func reset()
}

@MainActor
public final class UserDefaultsProductActivationMilestoneLedger: ProductActivationMilestoneLedger {
    public static let defaultsKey = "GRAFProductActivationMilestones"

    private let defaults: UserDefaults
    private let key: String
    private var counted: Set<String>

    public init(defaults: UserDefaults = .standard, key: String = UserDefaultsProductActivationMilestoneLedger.defaultsKey) {
        self.defaults = defaults
        self.key = key
        self.counted = Set(defaults.stringArray(forKey: key) ?? [])
    }

    public func hasCounted(_ key: String) -> Bool {
        counted.contains(key)
    }

    public func record(_ key: String) {
        guard counted.insert(key).inserted else { return }
        defaults.set(Array(counted).sorted(), forKey: self.key)
    }

    public func reset() {
        counted = []
        defaults.removeObject(forKey: key)
    }
}

@MainActor
public final class InMemoryProductActivationMilestoneLedger: ProductActivationMilestoneLedger {
    private var counted: Set<String> = []

    public init() {}

    public func hasCounted(_ key: String) -> Bool {
        counted.contains(key)
    }

    public func record(_ key: String) {
        counted.insert(key)
    }

    public func reset() {
        counted = []
    }
}

/// Что произошло с вехой при попытке отправки.
public enum ProductActivationAnalyticsOutcome: Equatable, Sendable {
    case delivered(ProductActivationEventName)
    case alreadyCounted(ProductActivationEventName)
    case telemetryGateClosed(ProductActivationEventName)
    case analyticsNotConfigured(ProductActivationEventName)
    case handledByServerAuthorization(ProductActivationEventName)
    case notEligible(ProductActivationEventName, reason: String)
    case deliveryFailed(ProductActivationEventName, status: Int?)

    public var event: ProductActivationEventName {
        switch self {
        case let .delivered(event),
             let .alreadyCounted(event),
             let .telemetryGateClosed(event),
             let .analyticsNotConfigured(event),
             let .handledByServerAuthorization(event),
             let .notEligible(event, _),
             let .deliveryFailed(event, _):
            return event
        }
    }

    public var wasDelivered: Bool {
        if case .delivered = self {
            return true
        }
        return false
    }
}

/// Отправка вех активации из настоящих путей приложения (FR-021).
///
/// Отправитель вызывается из реальных мест продукта: первый запуск, включение
/// авто-записи, первая завершённая запись, первый просмотр результата и первая
/// ценность. Веху подключения аккаунта отправляет серверная авторизация —
/// приложение только запоминает, что связь установлена.
///
/// Каждая веха несёт уровень надёжности связи с кампанией, а повторная
/// отправка не считается второй раз ни здесь, ни на сервере (FR-023, FR-025).
@MainActor
public final class ProductActivationAnalyticsReporter {
    public static let usefulResultTypes: Set<String> = [
        "transcript",
        "summary",
        "outcome",
        "action_items",
        "approved_equivalent"
    ]

    private let client: ProductActivationAnalyticsClient?
    private let transport: any ProductActivationAnalyticsTransport
    private let handoffs: ProductAttributionHandoffStore
    private let ledger: any ProductActivationMilestoneLedger
    private let identityProvider: () -> String?
    private let now: () -> Date

    public var telemetryGateState: ProductTelemetryGateState

    public init(
        client: ProductActivationAnalyticsClient?,
        transport: any ProductActivationAnalyticsTransport = URLSessionProductActivationAnalyticsTransport(),
        handoffs: ProductAttributionHandoffStore = ProductAttributionHandoffStore(),
        ledger: any ProductActivationMilestoneLedger = UserDefaultsProductActivationMilestoneLedger(),
        telemetryGateState: ProductTelemetryGateState = .notSeen,
        identityProvider: @escaping () -> String? = { nil },
        now: @escaping () -> Date = { Date() }
    ) {
        self.client = client
        self.transport = transport
        self.handoffs = handoffs
        self.ledger = ledger
        self.telemetryGateState = telemetryGateState
        self.identityProvider = identityProvider
        self.now = now
    }

    /// Собирает отправителя из окружения приложения.
    public static func configured(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        defaults: UserDefaults = .standard,
        transport: any ProductActivationAnalyticsTransport = URLSessionProductActivationAnalyticsTransport(),
        telemetryGateState: ProductTelemetryGateState = .notSeen
    ) -> ProductActivationAnalyticsReporter {
        let configuration = DesktopCabinetConfiguration.configured(from: environment, defaults: defaults)
        let client = configuration.flatMap {
            ProductActivationAnalyticsClient(rawBaseURL: $0.baseURL.absoluteString, headers: $0.headers)
        }
        return ProductActivationAnalyticsReporter(
            client: client,
            transport: transport,
            handoffs: ProductAttributionHandoffStore(defaults: defaults),
            ledger: UserDefaultsProductActivationMilestoneLedger(defaults: defaults),
            telemetryGateState: telemetryGateState,
            identityProvider: { configuration.flatMap { $0.workspaceId.flatMap(ProductActivationPseudonymousIdentity.workspace) } }
        )
    }

    // MARK: - Настоящие пути продукта

    @discardableResult
    public func noteFirstLaunch(
        appVersion: String,
        platform: String = "macos",
        installChannel: String
    ) async -> ProductActivationAnalyticsOutcome {
        await emit(
            .desktopFirstOpened,
            properties: [
                "app_version_bucket": Self.versionBucket(appVersion),
                "platform": platform,
                "install_channel": installChannel
            ]
        )
    }

    /// Подключение аккаунта отправляет серверная авторизация (FR-021).
    ///
    /// Приложение в этот момент только запоминает, что связь с аккаунтом
    /// установлена, и отправляет метки кампании во встроенный вход кабинета.
    @discardableResult
    public func noteAccountConnected(
        authMethodCategory: String = "embedded_cabinet",
        at date: Date? = nil
    ) -> ProductActivationAnalyticsOutcome {
        _ = authMethodCategory
        handoffs.markAccountConnected(at: date ?? now())
        return .handledByServerAuthorization(.desktopAccountConnected)
    }

    @discardableResult
    public func noteAutorecordEnabled(
        policyState: String,
        previousState: String,
        source: String,
        surface: String
    ) async -> ProductActivationAnalyticsOutcome {
        await emit(
            .desktopAutorecordEnabled,
            properties: [
                "policy_state": policyState,
                "previous_state": previousState,
                // Поле названо по смыслу: рядом с метками кампании (FR-018)
                // короткое `source` читалось бы как канал привлечения.
                "autorecord_source": source,
                "surface": surface
            ]
        )
    }

    @discardableResult
    public func noteFirstRecordingCompleted(
        durationBucket: String,
        captureMode: String,
        completionState: String,
        resultPendingState: String
    ) async -> ProductActivationAnalyticsOutcome {
        await emit(
            .firstRecordingCompleted,
            properties: [
                "duration_bucket": durationBucket,
                "capture_mode": captureMode,
                "completion_state": completionState,
                "result_pending_state": resultPendingState
            ]
        )
    }

    @discardableResult
    public func noteFirstResultViewed(
        resultState: String,
        surface: String,
        usefulOutputPresent: Bool
    ) async -> ProductActivationAnalyticsOutcome {
        await emit(
            .firstResultViewed,
            properties: [
                "result_state": resultState,
                "surface": surface,
                "useful_output_present": usefulOutputPresent ? "true" : "false"
            ]
        )
    }

    /// Первая ценность: результат готов и содержит полезный итог.
    @discardableResult
    public func noteFirstValueSessionCompleted(
        usefulResultType: String,
        firstRecordingCompleted: Bool = true,
        firstResultViewed: Bool = true,
        usefulOutputPresent: Bool = true
    ) async -> ProductActivationAnalyticsOutcome {
        guard Self.usefulResultTypes.contains(usefulResultType) else {
            return .notEligible(.firstValueSessionCompleted, reason: "unsupported_useful_result_type")
        }
        guard usefulOutputPresent, firstRecordingCompleted, firstResultViewed else {
            return .notEligible(.firstValueSessionCompleted, reason: "useful_output_absent")
        }
        return await emit(
            .firstValueSessionCompleted,
            properties: [
                "first_recording_completed": "true",
                "first_result_viewed": "true",
                "useful_output_present": "true",
                "useful_result_type": usefulResultType
            ]
        )
    }

    // MARK: - Общая отправка

    private func emit(
        _ event: ProductActivationEventName,
        properties: [String: String]
    ) async -> ProductActivationAnalyticsOutcome {
        guard telemetryGateState.allowsProductAnalytics else {
            return .telemetryGateClosed(event)
        }
        guard let client else {
            return .analyticsNotConfigured(event)
        }
        let identity = identityProvider()
        let ledgerKey = Self.ledgerKey(event: event, identity: identity)
        if ledger.hasCounted(ledgerKey) {
            return .alreadyCounted(event)
        }
        let handoff = handoffs.current(now: now())
        var merged = properties
        for (key, value) in handoff?.attributionProperties() ?? [:] {
            merged[key] = value
        }
        if handoff == nil {
            // Кампании нет вовсе: веха честно помечается неизвестной и никогда
            // не выдаёт себя за прямой заход (FR-018, FR-024).
            merged["bridge_present"] = "false"
            merged["attribution_reliability"] = ProductActivationAttributionReliability.unknown.rawValue
            merged["campaign_label_state"] = ProductAttributionHandoff.campaignLabelStateUnknown
        }
        do {
            let payload = try ProductActivationAnalyticsPayload(
                eventName: event,
                stablePseudonymousUserId: identity,
                occurredAt: now(),
                telemetryGateState: telemetryGateState,
                properties: merged
            )
            let status = try await transport.send(payload, using: client)
            guard (200..<300).contains(status) else {
                // Ответ сервера получен: повторять веху бессмысленно, но и
                // считать её отправленной нельзя.
                return .deliveryFailed(event, status: status)
            }
            ledger.record(ledgerKey)
            return .delivered(event)
        } catch {
            return .deliveryFailed(event, status: nil)
        }
    }

    private static func ledgerKey(event: ProductActivationEventName, identity: String?) -> String {
        "\(event.rawValue)|\(identity ?? "unlinked")"
    }

    private static func versionBucket(_ version: String) -> String {
        let parts = version.split(separator: ".")
        guard parts.count >= 2 else { return "unknown" }
        return "\(parts[0]).\(parts[1])"
    }
}

/// Устойчивый псевдоним для вех приложения.
///
/// Совпадает с серверным выводом для того же исходного значения, поэтому вехи
/// приложения и серверные вехи попадают в одну воронку, не раскрывая
/// идентификатор пользователя.
public enum ProductActivationPseudonymousIdentity {
    public static let salt = "graf-product-analytics-v1"

    public static func workspace(_ workspaceID: String) -> String? {
        pseudonym(kind: "workspace", sourceID: workspaceID)
    }

    public static func user(_ userID: String) -> String? {
        pseudonym(kind: "user", sourceID: userID)
    }

    public static func pseudonym(kind: String, sourceID: String) -> String? {
        let trimmed = sourceID.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let digest = SHA256.hash(data: Data("\(salt):\(kind):\(trimmed)".utf8))
            .map { String(format: "%02x", $0) }
            .joined()
        return "graf_pseudo_\(kind)_\(digest.prefix(32))"
    }
}
