import Foundation

/// Уровень надёжности связи конверсии с кампанией (FR-023).
///
/// Словарь ровно из трёх значений. `direct` уровнем не является: если кампания
/// неизвестна, конверсия честно помечается `unknown` (FR-024).
public enum ProductActivationAttributionReliability: String, Codable, CaseIterable, Sendable {
    case linked
    case weak
    case unknown

    /// Переводит любое известное написание в уровень контракта.
    public static func normalized(_ rawValue: String?) -> ProductActivationAttributionReliability? {
        guard let rawValue else { return nil }
        switch rawValue.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "linked", "campaign_linked_reliable":
            return .linked
        case "weak", "campaign_linked_weak":
            return .weak
        case "unknown", "counted_unlinked", "not_linkable":
            return .unknown
        default:
            return nil
        }
    }
}

/// Ссылка передачи атрибуции: страница загрузки → приложение (FR-022).
///
/// Запасной путь нужен потому, что вход и регистрация внутри приложения
/// происходят во встроенном окне кабинета, которое не видит состояние
/// браузера посетителя. В ссылке едут только метки кампании: идентификатор
/// клика Яндекс.Директа остаётся в записи посещения и в ссылку не попадает
/// (FR-016, FR-028).
public struct ProductAttributionHandoff: Codable, Equatable, Sendable {
    public static let urlScheme = "grafrec"
    public static let urlHost = "attribution"
    public static let bridgeQueryItem = "bridge"
    public static let fallbackQueryItem = "fallback"
    public static let landingPathQueryItem = "landing_path"
    public static let signInAttributionRefQueryItem = "graf_attribution_ref"
    public static let signInFallbackQueryItem = "graf_attribution_fallback"
    public static let campaignQueryItems = [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term"
    ]
    public static let bridgeIdentifierPrefix = "graf_attr_"
    public static let validityWindowDays = 90
    public static let maxLabelLength = 96
    /// Состояние метки кампании в конверсионной вехе: кампания известна или
    /// нет. Отдельное значение нужно затем, чтобы «неизвестно» нельзя было
    /// прочитать как «прямой заход» (FR-018, FR-024).
    public static let campaignLabelStateKnown = "known"
    public static let campaignLabelStateUnknown = "unknown"

    public let bridgeID: String?
    public let campaign: [String: String]
    public let landingPath: String?
    public let fallbackRecovered: Bool
    public let receivedAt: Date

    public init(
        bridgeID: String?,
        campaign: [String: String],
        landingPath: String? = nil,
        fallbackRecovered: Bool = true,
        receivedAt: Date = Date()
    ) {
        self.bridgeID = Self.isSafeBridgeIdentifier(bridgeID) ? bridgeID : nil
        self.campaign = campaign.filter { key, value in
            Self.campaignQueryItems.contains(key) && Self.isSafeCampaignLabel(value)
        }
        self.landingPath = Self.safeLandingPath(landingPath)
        self.fallbackRecovered = fallbackRecovered
        self.receivedAt = receivedAt
    }

    /// Разбирает ссылку передачи атрибуции. Всё, что не похоже на ссылку
    /// приложения ГРАФ, отвергается целиком.
    public init?(link rawValue: String, receivedAt: Date = Date()) {
        guard let components = URLComponents(string: rawValue.trimmingCharacters(in: .whitespacesAndNewlines)),
              components.scheme?.lowercased() == Self.urlScheme,
              components.host?.lowercased() == Self.urlHost
        else {
            return nil
        }
        var values: [String: String] = [:]
        for item in components.queryItems ?? [] where values[item.name] == nil {
            values[item.name] = item.value ?? ""
        }
        self.init(
            bridgeID: values[Self.bridgeQueryItem],
            campaign: values,
            landingPath: values[Self.landingPathQueryItem],
            fallbackRecovered: Self.isFallbackFlag(values[Self.fallbackQueryItem]),
            receivedAt: receivedAt
        )
    }

    public var campaignKnown: Bool {
        !campaign.isEmpty
    }

    /// Уровень надёжности для события, которое отправляет само приложение.
    public func reliability(accountConnected: Bool) -> ProductActivationAttributionReliability {
        guard campaignKnown else { return .unknown }
        if accountConnected && !fallbackRecovered {
            return .linked
        }
        return .weak
    }

    /// Свойства атрибуции, которые разрешены в конверсионной вехе (FR-018).
    ///
    /// Метки кампании едут вместе с уровнем надёжности: без них связать
    /// конверсию с каналом можно только через запись о клиенте. Кампания,
    /// которой нет, помечается явным `unknown` и никогда не читается как
    /// прямой заход (FR-024).
    public func attributionProperties(
        accountConnected: Bool = false
    ) -> [String: String] {
        var properties: [String: String] = [
            "bridge_present": "true",
            "attribution_reliability": reliability(accountConnected: accountConnected).rawValue,
            "campaign_label_state": campaignKnown
                ? ProductAttributionHandoff.campaignLabelStateKnown
                : ProductAttributionHandoff.campaignLabelStateUnknown
        ]
        if let bridgeID {
            properties["graf_attribution_id"] = bridgeID
        }
        for name in Self.campaignQueryItems {
            if let value = campaign[name] {
                properties[name] = value
            }
        }
        return properties
    }

    public var expirationDate: Date {
        receivedAt.addingTimeInterval(TimeInterval(Self.validityWindowDays * 24 * 60 * 60))
    }

    public func isExpired(now: Date = Date()) -> Bool {
        now >= expirationDate
    }

    /// Параметры, с которыми приложение открывает вход во встроенном кабинете.
    ///
    /// Метки едут вместе с идентификатором моста: сервер видит их прямо в
    /// запросе и потому отмечает такую связь как восстановленную запасным
    /// путём (`weak`), а не как автоматическую (`linked`).
    public func signInQueryItems() -> [URLQueryItem] {
        var items: [URLQueryItem] = [
            URLQueryItem(name: Self.signInFallbackQueryItem, value: "1")
        ]
        if let bridgeID {
            items.append(URLQueryItem(name: Self.signInAttributionRefQueryItem, value: bridgeID))
        }
        for name in Self.campaignQueryItems {
            if let value = campaign[name] {
                items.append(URLQueryItem(name: name, value: value))
            }
        }
        if let landingPath {
            items.append(URLQueryItem(name: Self.landingPathQueryItem, value: landingPath))
        }
        return items
    }

    /// Добавляет параметры передачи атрибуции к маршруту входа в кабинете.
    public func applyingSignInQueryItems(to url: URL) -> URL {
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            return url
        }
        let existing = components.queryItems ?? []
        let names = Set(signInQueryItems().map(\.name))
        components.queryItems = existing.filter { !names.contains($0.name) } + signInQueryItems()
        return components.url ?? url
    }

    public static func isSafeBridgeIdentifier(_ value: String?) -> Bool {
        guard let value else { return false }
        guard value.hasPrefix(bridgeIdentifierPrefix) else { return false }
        let suffix = String(value.dropFirst(bridgeIdentifierPrefix.count))
        guard (8...64).contains(suffix.count) else { return false }
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        return suffix.unicodeScalars.allSatisfy { allowed.contains($0) }
    }

    /// Метка кампании сохраняется только тогда, когда она не может быть
    /// персональными данными: почта, телефон, секрет и локальный путь
    /// отбрасываются (FR-011, FR-014).
    public static func isSafeCampaignLabel(_ value: String) -> Bool {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed.count <= maxLabelLength else { return false }
        let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-")
        guard trimmed.unicodeScalars.allSatisfy({ allowed.contains($0) }) else { return false }
        let lowered = trimmed.lowercased()
        if lowered.contains("token") || lowered.contains("secret") || lowered.contains("password")
            || lowered.contains("passcode") || lowered.contains("signed_url") || lowered.contains("api_key")
        {
            return false
        }
        if trimmed.range(of: #"\d[\d\s().-]{8,}\d"#, options: .regularExpression) != nil {
            return false
        }
        return true
    }

    private static func isFallbackFlag(_ value: String?) -> Bool {
        guard let value else { return false }
        return ["1", "true", "yes"].contains(value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased())
    }

    private static func safeLandingPath(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("/"), trimmed.count <= maxLabelLength else { return nil }
        guard trimmed.unicodeScalars.allSatisfy({
            CharacterSet(charactersIn: "/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-").contains($0)
        }) else {
            return nil
        }
        return trimmed
    }
}

/// Хранилище ссылки передачи атрибуции в приложении.
///
/// Метки живут ограниченное время (90 дней) и не превращаются в постоянный
/// идентификатор посетителя: хранится ровно одна последняя ссылка. Чтение
/// всегда идёт из хранилища, поэтому запись из другого места приложения
/// (например, из обработчика открытия ссылки) сразу видна всем читателям.
@MainActor
public final class ProductAttributionHandoffStore {
    public static let defaultsKey = "GRAFAttributionHandoff"

    private struct Payload: Codable, Equatable {
        var handoff: ProductAttributionHandoff?
        var accountConnectedAt: Date?
    }

    private let defaults: UserDefaults
    private let key: String

    public init(defaults: UserDefaults = .standard, key: String = ProductAttributionHandoffStore.defaultsKey) {
        self.defaults = defaults
        self.key = key
    }

    public var accountConnectedAt: Date? {
        read().accountConnectedAt
    }

    /// Сохраняет ссылку, разобранную из адреса `grafrec://attribution?...`.
    @discardableResult
    public func save(link rawValue: String, receivedAt: Date = Date()) -> ProductAttributionHandoff? {
        guard let handoff = ProductAttributionHandoff(link: rawValue, receivedAt: receivedAt) else {
            return nil
        }
        save(handoff)
        return handoff
    }

    /// Обрабатывает адрес, открытый системой: это путь первого запуска (FR-022).
    ///
    /// Разбор и запись живут здесь, а не в обработчике приложения, чтобы
    /// сквозной путь «ссылка → хранилище → вход → запись о клиенте» можно было
    /// проверить тестом: сам обработчик `application(_:open:)` принадлежит
    /// исполняемой цели и в тестовую сборку не входит.
    @discardableResult
    public func handleOpenURL(_ url: URL, receivedAt: Date = Date()) -> ProductAttributionHandoff? {
        save(link: url.absoluteString, receivedAt: receivedAt)
    }

    public func save(_ handoff: ProductAttributionHandoff) {
        write(Payload(handoff: handoff, accountConnectedAt: read().accountConnectedAt))
    }

    /// Текущая действующая ссылка. Просроченная ссылка забывается.
    public func current(now: Date = Date()) -> ProductAttributionHandoff? {
        var payload = read()
        guard let handoff = payload.handoff else { return nil }
        if handoff.isExpired(now: now) {
            payload.handoff = nil
            write(payload)
            return nil
        }
        return handoff
    }

    /// Отмечает, что аккаунт подключён: саму веху отправляет серверная
    /// авторизация, приложение лишь запоминает состояние связи.
    public func markAccountConnected(at date: Date = Date()) {
        var payload = read()
        payload.accountConnectedAt = date
        write(payload)
    }

    public func clear() {
        defaults.removeObject(forKey: key)
    }

    private func write(_ payload: Payload) {
        guard let data = try? JSONEncoder().encode(payload) else { return }
        defaults.set(data, forKey: key)
    }

    private func read() -> Payload {
        guard let data = defaults.data(forKey: key),
              let payload = try? JSONDecoder().decode(Payload.self, from: data)
        else {
            return Payload(handoff: nil, accountConnectedAt: nil)
        }
        return payload
    }
}
