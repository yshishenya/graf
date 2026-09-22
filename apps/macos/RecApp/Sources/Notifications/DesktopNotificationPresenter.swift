import AppKit
import Combine
import CryptoKit
import Network
import SwiftUI
import TwoBrainRecShared
import UserNotifications

public struct DesktopNotificationPreferences: Codable, Equatable {
    public var reminders = true
    public var offsetMinutes = 1
    public var showTitles = false
    public var sound = false
    public init() {}
}

public final class DesktopNotificationPreferencesStore {
    private let defaults: UserDefaults
    public init(defaults: UserDefaults = .standard) { self.defaults = defaults }
    private func key(_ owner: String) -> String {
        "graf.notifications." + SHA256.hash(data: Data(owner.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    public func load(owner: String) -> DesktopNotificationPreferences {
        guard !owner.isEmpty, let data = defaults.data(forKey: key(owner)),
              let value = try? JSONDecoder().decode(DesktopNotificationPreferences.self, from: data) else { return .init() }
        return value
    }
    public func save(_ value: DesktopNotificationPreferences, owner: String) throws {
        guard !owner.isEmpty, [0, 1, 5].contains(value.offsetMinutes) else { throw CocoaError(.validationMissingMandatoryProperty) }
        defaults.set(try JSONEncoder().encode(value), forKey: key(owner))
    }
    // A session keeps its first notification owner across account changes and restarts.
    // Unknown ownership stays silent; capture never waits for authentication.
    public func bindSession(_ id: String, context: String) {
        let name = key("session:" + id)
        if defaults.string(forKey: name) == nil { defaults.set(key(context), forKey: name) }
    }
    public func ownsSession(_ id: String, context: String) -> Bool {
        !context.isEmpty && defaults.string(forKey: key("session:" + id)) == key(context)
    }
    // Share the old capture claim and every related legacy upload claim. Updating
    // them together also prevents repeat delivery when rolling back to old code.
    func claimLocalIncident(_ incident: DesktopLocalNotificationIncident, owner: String, now: Date) -> Bool {
        guard !owner.isEmpty, incident.expires > now else { return false }
        let name = key(owner) + ".attempts"
        var claims = (defaults.dictionary(forKey: name) as? [String: Double] ?? [:])
            .filter { $0.value > now.timeIntervalSince1970 }
        let ids = [incident.id] + incident.itemIDs.map { "graf.local.incident." + $0 }
        let digests = ids.map { SHA256.hash(data: Data($0.utf8)).map { String(format: "%02x", $0) }.joined() }
        let previous = digests.compactMap { claims[$0] }.max()
        let expires = Date.distantFuture.timeIntervalSince1970
        for digest in digests { claims[digest] = expires }
        defaults.set(claims, forKey: name)
        return previous == nil
    }
    func reconcileIncidents(_ incidents: [DesktopLocalNotificationIncident], knownSessions: Set<String>, owner: String) {
        guard !owner.isEmpty else { return }
        let stateKey = key(owner) + ".activeIncidents"
        var previous = defaults.dictionary(forKey: stateKey) as? [String: [String]] ?? [:]
        let current = Set(incidents.map(\.sessionID))
        let claimsKey = key(owner) + ".attempts"
        var claims = defaults.dictionary(forKey: claimsKey) as? [String: Double] ?? [:]
        for session in knownSessions.subtracting(current) {
            guard let items = previous.removeValue(forKey: session) else { continue }
            for id in ["graf.local.capture." + session] + items.map({ "graf.local.incident." + $0 }) {
                let digest = SHA256.hash(data: Data(id.utf8)).map { String(format: "%02x", $0) }.joined()
                claims.removeValue(forKey: digest)
            }
        }
        for incident in incidents { previous[incident.sessionID] = incident.itemIDs }
        defaults.set(claims, forKey: claimsKey)
        defaults.set(previous, forKey: stateKey)
    }
    public func claim(id: String, aliases: [String] = [], owner: String, expires: Date, scheduledFor: Date? = nil, now: Date = Date()) -> Bool {
        guard !owner.isEmpty, expires > now else { return false }
        let name = key(owner) + ".attempts"
        var claims = defaults.dictionary(forKey: name) as? [String: Double] ?? [:]
        claims = claims.filter { $0.value > now.timeIntervalSince1970 }
        let reservationKey = name + ".reservations"
        var reservations = defaults.dictionary(forKey: reservationKey) as? [String: [String: Double]] ?? [:]
        reservations = reservations.filter { ($0.value["expires"] ?? 0) > now.timeIntervalSince1970 }
        let digests = ([id] + aliases).map { id in
            SHA256.hash(data: Data(id.utf8)).map { String(format: "%02x", $0) }.joined()
        }
        for digest in digests where claims[digest] != nil {
            // A future reservation can be replaced after cancellation/restart. Once
            // its due time has passed (or with a legacy claim), never deliver again.
            guard let due = reservations[digest]?["scheduledFor"], due > now.timeIntervalSince1970,
                  scheduledFor != nil else {
                // Migrate a delivered legacy alias to the stable occurrence key too.
                for value in digests {
                    claims[value] = max(claims[value] ?? 0, expires.timeIntervalSince1970)
                    reservations.removeValue(forKey: value)
                }
                defaults.set(claims, forKey: name)
                defaults.set(reservations, forKey: reservationKey)
                return false
            }
        }
        // Keep the old numeric ledger readable on rollback. Write its deny marker
        // first: interruption before the atomic reservation write stays silent.
        for digest in digests { claims[digest] = expires.timeIntervalSince1970 }
        defaults.set(claims, forKey: name)
        var reservation = ["expires": expires.timeIntervalSince1970]
        if let scheduledFor { reservation["scheduledFor"] = scheduledFor.timeIntervalSince1970 }
        for digest in digests { reservations[digest] = reservation }
        defaults.set(reservations, forKey: reservationKey)
        return true
    }
}

struct DesktopLocalNotificationIncident {
    var sessionID: String
    var itemIDs: [String]
    var expires: Date
    var fresh: Bool
    var id: String { "graf.local.capture." + sessionID }

    static func incidents(in snapshot: DesktopControlSnapshot, now: Date) -> [Self] {
        var grouped: [String: Self] = [:]
        for item in snapshot.uploadItems where item.state != .terminalDeleted {
            let custody = DesktopUploadCustodyProjection(item: item, now: now)
            // Opening a delivered result is not a local failure. Server-side
            // processing owns its own outcome, not the local custody alarm.
            guard custody.requiresUserAttention, custody.normalUserAction != .openReview,
                  custody.custodyState != .processing else { continue }
            let previous = grouped[item.sessionId]
            grouped[item.sessionId] = Self(sessionID: item.sessionId,
                itemIDs: snapshot.uploadItems.filter { $0.sessionId == item.sessionId }.map(\.id),
                expires: now.addingTimeInterval(300),
                fresh: previous?.fresh == true || (0..<300).contains(now.timeIntervalSince(item.updatedAt)))
        }
        if let session = snapshot.session, snapshot.blocker?.isEmpty == false {
            if var incident = grouped[session.id] {
                incident.fresh = true
                grouped[session.id] = incident
            } else {
                grouped[session.id] = Self(sessionID: session.id,
                    itemIDs: snapshot.uploadItems.filter { $0.sessionId == session.id }.map(\.id),
                    expires: now.addingTimeInterval(86400), fresh: true)
            }
        }
        return grouped.values.sorted { $0.sessionID < $1.sessionID }
    }


}

@MainActor
public final class DesktopNotificationPresenter: NSObject, ObservableObject, UNUserNotificationCenterDelegate {
    public static let shared = DesktopNotificationPresenter()
    @Published public private(set) var preferences = DesktopNotificationPreferences()
    @Published public var draft = DesktopNotificationPreferences()
    @Published public private(set) var canRequestPermission = false
    @Published public private(set) var permissionText = "Проверяем разрешение macOS"
    @Published public private(set) var owner = ""
    @Published public private(set) var message = ""
    @Published public private(set) var saveFailed = false
    public var onOpenCalendar: (() -> Void)?
    public var onOpenSettings: (() -> Void)?
    private let center: UNUserNotificationCenter?
    private let store: DesktopNotificationPreferencesStore
    private let model: DesktopControlModel
    private let statusProvider: (@MainActor () async -> UNAuthorizationStatus)?
    private let submit: (@MainActor (UNNotificationRequest) async throws -> Void)?
    private let remove: (@MainActor ([String]?) -> Void)?
    private let requestPermission: (@MainActor () async throws -> Bool)?
    private let contextProvider: (@MainActor () async throws -> DesktopNotificationContext)?
    private var context = ""
    @Published private(set) var authEpoch = 0
    private var generation = 0
    private var schedulingReminders = false
    private var calendarEvents: [DesktopCalendarPromptEvent] = []
    private var requests: [String: (owner: String, event: DesktopCalendarPromptEvent?, sessionID: String?)] = [:]
    // Поверхности показа доступны проверкам: окно карточки измеряется на
    // настоящем окне, а индикатор проверяется по показанному состоянию.
    public let card = DesktopNotificationCardPresenter()
    private var lastRecordingNotice: RecordingNoticeState?
    private var cardTimer: Task<Void, Never>?
    private var cardDeadline: Date?
    private var dismissedCards: Set<String> = []
    private var presentedCardID: String?
    private var activeCardOwner: CardOwner?

    private enum CardOwner: Equatable {
        case meeting(String)
        case problem(String)
        case preview
        case shortRecording
        case recordingPrompt
    }

    private static func cardPriority(_ owner: CardOwner) -> Int {
        switch owner {
        case .preview: return 1
        case .meeting: return 2
        case .recordingPrompt, .shortRecording: return 3
        case .problem: return 4
        }
    }

    private func canPresent(_ owner: CardOwner) -> Bool {
        guard card.isVisible, let activeCardOwner else { return true }
        return activeCardOwner == owner || Self.cardPriority(owner) > Self.cardPriority(activeCardOwner)
    }

    /// Сбрасывает только состояние согласователя. Само окно заменяется новым
    /// вызовом карточки или снимается вызывающим методом.
    private func resetCardState() {
        cardTimer?.cancel()
        cardTimer = nil
        cardDeadline = nil
        presentedCardID = nil
        activeCardOwner = nil
    }

    private func finishExternalCard(_ owner: CardOwner) {
        guard activeCardOwner == owner else { return }
        resetCardState()
    }

    private func dismissExternalCard(_ owner: CardOwner) {
        guard activeCardOwner == owner else { return }
        resetCardState()
        card.dismiss()
    }

    @discardableResult
    public func presentPreview(title: String,
                               message: String,
                               duration: TimeInterval = DesktopNotificationCardPresenter.previewDisplayDuration,
                               onExpire: (() -> Void)? = nil) -> Bool {
        let owner: CardOwner = .preview
        guard canPresent(owner) else { return false }
        resetCardState()
        activeCardOwner = owner
        card.presentPreview(title: title, message: message, duration: duration,
                            onExpire: { [weak self] in
                                self?.finishExternalCard(owner)
                                onExpire?()
                                self?.reconcileCard()
                            })
        return true
    }

    @discardableResult
    public func presentShortRecording(title: String,
                                      message: String,
                                      duration: TimeInterval = DesktopNotificationCardPresenter.noticeDisplayDuration,
                                      onExpire: (() -> Void)? = nil) -> Bool {
        let owner: CardOwner = .shortRecording
        guard canPresent(owner) else { return false }
        resetCardState()
        activeCardOwner = owner
        card.presentShortRecording(title: title, message: message, duration: duration,
                                   onExpire: { [weak self] in
                                       self?.finishExternalCard(owner)
                                       onExpire?()
                                       self?.reconcileCard()
                                   })
        return true
    }

    @discardableResult
    public func presentRecordingPrompt(
        displayName: String,
        remainingSeconds: Int,
        progress: Double,
        rememberChoice: Bool = false,
        duration: TimeInterval = DesktopNotificationCardPresenter.recordingPromptDisplayDuration,
        onStart: @escaping () -> Void,
        onDismiss: @escaping () -> Void,
        onRememberChoiceChanged: @escaping (Bool) -> Void,
        onTick: (() -> DesktopNotificationCardContent?)? = nil,
        onExpire: (() -> Void)? = nil,
        onSkip: ((Bool) -> Void)? = nil
    ) -> Bool {
        let owner: CardOwner = .recordingPrompt
        guard canPresent(owner) else { return false }
        resetCardState()
        activeCardOwner = owner
        card.presentRecordingPrompt(
            displayName: displayName,
            remainingSeconds: remainingSeconds,
            progress: progress,
            rememberChoice: rememberChoice,
            duration: duration,
            onStart: { [weak self] in
                onStart()
                self?.dismissExternalCard(owner)
            },
            onDismiss: { [weak self] in
                onDismiss()
                self?.dismissExternalCard(owner)
            },
            onRememberChoiceChanged: onRememberChoiceChanged,
            onTick: { [weak self] in
                guard self?.activeCardOwner == owner else { return nil }
                return onTick?()
            },
            onExpire: { [weak self] in
                onExpire?()
                // Обработчик тайм-аута сначала убирает вопрос и запускает
                // запись. Не показываем встречу между этими двумя шагами:
                // состояние записи само вызовет следующую сверку.
                self?.finishExternalCard(owner)
            },
            onSkip: { [weak self] rememberChoice in
                onSkip?(rememberChoice)
                self?.dismissExternalCard(owner)
            }
        )
        return true
    }

    public func dismissPreview() { dismissExternalCard(.preview) }
    public func dismissShortRecording() { dismissExternalCard(.shortRecording) }
    public func dismissRecordingPrompt() { dismissExternalCard(.recordingPrompt) }
    private var observation: AnyCancellable?
    private var activationObservation: AnyCancellable?
    private var settingsObservation: AnyCancellable?
    private var authObservation: AnyCancellable?
    private var wakeObservation: AnyCancellable?
    private var contextGeneration = 0
    private var permissionGeneration = 0
    private var lastSnapshot = DesktopControlSnapshot()
    // Inject the OS boundary and model so orchestration tests never initialize
    // the system notification center, observers, or a configured network client.
    init(center: UNUserNotificationCenter? = nil, store: DesktopNotificationPreferencesStore,
         model: DesktopControlModel, status: (@MainActor () async -> UNAuthorizationStatus)? = nil,
         submit: (@MainActor (UNNotificationRequest) async throws -> Void)? = nil,
         remove: (@MainActor ([String]?) -> Void)? = nil,
         requestPermission: (@MainActor () async throws -> Bool)? = nil,
         contextProvider: (@MainActor () async throws -> DesktopNotificationContext)? = nil) {
        self.center = center; self.store = store; self.model = model
        self.statusProvider = status; self.submit = submit; self.remove = remove
        self.requestPermission = requestPermission; self.contextProvider = contextProvider
        super.init()
    }
    public override convenience init() {
        self.init(center: .current(), store: .init(), model: .shared)
        center?.delegate = self
        center?.setNotificationCategories(Self.notificationCategories)
        removeNotifications()
        authObservation = NotificationCenter.default.publisher(for: .twoBrainRecDesktopAuthSessionDidChange).sink { [weak self] _ in
            // Auth notifications are delivered synchronously on the main queue.
            if Thread.isMainThread {
                MainActor.assumeIsolated { self?.invalidate() }
            } else {
                DispatchQueue.main.sync { MainActor.assumeIsolated { self?.invalidate() } }
            }
            Task { @MainActor in await self?.refreshContext() }
        }
        wakeObservation = NSWorkspace.shared.notificationCenter.publisher(for: NSWorkspace.didWakeNotification).sink { [weak self] _ in
            Task { await self?.refreshContext(); await self?.refreshPermission() }
        }
        Task { await refreshContext() }
        activationObservation = NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification).sink { [weak self] _ in
            Task { await self?.refreshContext(); await self?.refreshPermission() }
        }
        settingsObservation = NotificationCenter.default.publisher(for: NSWindow.didBecomeKeyNotification)
            .filter { ($0.object as? NSWindow)?.identifier?.rawValue == "graf-settings-window" }
            .sink { [weak self] _ in Task { await self?.refreshPermission() } }
        observation = model.$snapshot.sink { [weak self] snapshot in
            self?.updateSnapshot(snapshot)
        }
    }
    @discardableResult
    func updateSnapshot(_ snapshot: DesktopControlSnapshot) -> Task<Void, Never>? {
        guard snapshot != lastSnapshot else { return nil }
        let remindersChanged = snapshot.active != lastSnapshot.active || snapshot.calendarContextEventID != lastSnapshot.calendarContextEventID
        if snapshot.active, snapshot.session?.id != lastSnapshot.session?.id || !lastSnapshot.active,
           let id = snapshot.session?.id { store.bindSession(id, context: context) }
        if remindersChanged { generation += 1 }
        lastSnapshot = snapshot
        updateRecordingIndicator(snapshot, elapsed: model.elapsed())
        return Task {
            if remindersChanged { await scheduleReminders() }
            await refreshLocal(lastSnapshot)
        }
    }
    private func removeNotifications(_ ids: [String]? = nil) {
        if let ids {
            center?.removePendingNotificationRequests(withIdentifiers: ids)
            center?.removeDeliveredNotifications(withIdentifiers: ids)
        } else {
            center?.removeAllPendingNotificationRequests()
            center?.removeAllDeliveredNotifications()
        }
        remove?(ids)
    }
    public func invalidate() {
        contextGeneration += 1
        permissionGeneration += 1
        authEpoch += 1
        generation += 1
        removeNotifications()
        requests.removeAll(); calendarEvents.removeAll()
        dismissAllCards()
        owner = ""; context = ""; preferences = .init(); draft = preferences; message = ""; saveFailed = false
    }
    public func clearCalendar() {
        generation += 1
        let ids = requests.filter { $0.value.event != nil }.map(\.key)
        removeNotifications(ids)
        ids.forEach { requests.removeValue(forKey: $0) }
        calendarEvents = []
        reconcileCard()
    }
    public func updateCalendar(_ response: DesktopCalendarPromptResponse) {
        guard let user = response.notificationOwnerID, let workspace = response.notificationWorkspaceID else {
            clearCalendar(); return
        }
        updateContext(user: user, workspace: workspace)
        generation += 1
        calendarEvents = response.events
        Task { await scheduleReminders() }
        reconcileCard()
    }
    func updateContext(user: String, workspace: String) {
        let newContext = user.lowercased() + ":" + workspace.lowercased()
        if context != newContext {
            invalidate(); owner = user.lowercased(); context = newContext; preferences = store.load(owner: owner); draft = preferences
        }
    }
    @discardableResult
    public func refreshContext() async -> Int? {
        contextGeneration += 1
        let epoch = contextGeneration
        do {
            let value: DesktopNotificationContext
            if let contextProvider { value = try await contextProvider() }
            else if let client = DesktopUploadClient.configuredFromEnvironment() { value = try await client.notificationContext() }
            else { return nil }
            guard epoch == contextGeneration else { return nil }
            updateContext(user: value.user_id.uuidString, workspace: value.workspace_id.uuidString)
            let confirmedEpoch = authEpoch
            await refreshLocal(lastSnapshot)
            return confirmedEpoch == authEpoch ? confirmedEpoch : nil
        } catch let error as DesktopUploadClientError {
            if epoch == contextGeneration && error.failureCategory == .authSession { invalidate() }
        } catch { /* Keep only the already confirmed context in this auth epoch. */ }
        return nil
    }
    public func refreshPermission() async {
        permissionGeneration += 1
        let request = permissionGeneration
        let previous = permissionText
        let status = await authorizationStatus()
        guard request == permissionGeneration else { return }
        canRequestPermission = status == .notDetermined
        switch status {
        case .notDetermined: permissionText = "Разрешение еще не запрашивалось"
        case .denied: permissionText = "Уведомления macOS выключены"
        case .authorized, .provisional, .ephemeral: permissionText = "Уведомления macOS разрешены"
        @unknown default: permissionText = "Статус разрешения неизвестен"
        }
        if permissionText != previous {
            message = ""
            await scheduleReminders()
        }
        await refreshLocal(lastSnapshot)
    }
    public func enable(isCurrent: () -> Bool = { true }) async {
        let epoch = authEpoch
        // Системное разрешение не требует аккаунта: вход нужен только для
        // серверных предпочтений, которые без владельца остаются отключёнными.
        do {
            if let requestPermission { _ = try await requestPermission() }
            else if let center {
                _ = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Bool, Error>) in
                    center.requestAuthorization(options: [.alert, .sound]) { granted, error in
                        if let error { continuation.resume(throwing: error) }
                        else { continuation.resume(returning: granted) }
                    }
                }
            } else { return }
        } catch {
            guard epoch == authEpoch, isCurrent() else { return }
            message = "Не удалось запросить разрешение. Откройте настройки macOS."
            return
        }
        guard epoch == authEpoch, isCurrent() else { return }
        await refreshPermission()
        guard epoch == authEpoch, isCurrent() else { return }
        await scheduleReminders()
    }
    @discardableResult
    public func save(_ value: DesktopNotificationPreferences) -> Bool {
        do {
            try store.save(value, owner: owner); generation += 1; preferences = value; draft = value; saveFailed = false
            if !value.showTitles { center?.removeAllDeliveredNotifications() }
            message = "Сохранено на этом Mac"
            reconcileCard()
            Task { await scheduleReminders() }
            return true
        } catch {
            draft = value
            saveFailed = true
            message = "Не сохранено. Действуют прежние настройки."
            return false
        }
    }
    private func authorizationStatus() async -> UNAuthorizationStatus {
        if let statusProvider { return await statusProvider() }
        guard let center else { return .denied }
        return await withCheckedContinuation { continuation in
            center.getNotificationSettings { settings in
                continuation.resume(returning: settings.authorizationStatus)
            }
        }
    }
    private func addNotification(_ request: UNNotificationRequest) async throws {
        if let submit { try await submit(request); return }
        guard let center else { throw CocoaError(.featureUnsupported) }
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            center.add(request) { error in
                if let error { continuation.resume(throwing: error) }
                else { continuation.resume() }
            }
        }
    }
    private func allowed() async -> Bool {
        let status = await authorizationStatus()
        return status == .authorized || status == .provisional
    }
    /// Проверка показа: показывает ту же карточку, что и настоящее напоминание.
    /// Проверка не зависит от разрешения macOS и режима «Не беспокоить» — именно
    /// эта поверхность и должна быть видна пользователю.
    public func test(isCurrent: () -> Bool = { true }) async {
        let epoch = authEpoch
        guard epoch == authEpoch, isCurrent() else { return }
        // Предпросмотр не обновляет разрешение, календарь, очередь инцидентов,
        // системные запросы и состояние закрытых реальных карточек.
        guard presentPreview(title: "Проверка уведомлений GRAF",
                             message: "Так выглядит напоминание о встрече.",
                             duration: DesktopNotificationCardPresenter.previewDisplayDuration) else {
            message = "Проверочное уведомление не заменило уже показанное важное сообщение."
            return
        }
        message = "Проверочное уведомление показано в правом верхнем углу."
    }
    private func scheduleReminders() async {
        guard !schedulingReminders else { return }
        schedulingReminders = true
        defer { schedulingReminders = false }
        // Serialize OS writes: an older add must finish before its replacement.
        repeat {
            let epoch = generation
            await reconcileReminders()
            if epoch == generation { return }
        } while true
    }
    private func reconcileReminders() async {
        let epoch = generation
        let desired = Set(calendarEvents.filter { Self.shouldRemind($0, snapshot: lastSnapshot, now: Date()) }.map { reminderID($0) })
        let obsolete = requests.filter { $0.value.event != nil && (!desired.contains($0.key) || !preferences.reminders) }.map(\.key)
        center?.removePendingNotificationRequests(withIdentifiers: obsolete)
        center?.removeDeliveredNotifications(withIdentifiers: obsolete)
        obsolete.forEach { requests.removeValue(forKey: $0) }
        guard !owner.isEmpty, preferences.reminders, await allowed(), epoch == generation else { return }
        let now = Date()
        for event in calendarEvents {
            guard epoch == generation else { return }
            guard Self.shouldRemind(event, snapshot: lastSnapshot, now: now) else { continue }
            let due = event.startsAt.addingTimeInterval(-Double(preferences.offsetMinutes)*60)
            let id = reminderID(event)
            if let previous = requests[id]?.event, previous.startsAt != event.startsAt {
                removeNotifications([id])
            }
            requests[id] = (owner, event, nil)
            center?.removePendingNotificationRequests(withIdentifiers: [id])
            guard store.claim(id: id, aliases: [Self.legacyReminderID(event, context: context)], owner: owner, expires: .distantFuture, scheduledFor: due, now: now) else { continue }
            let content = Self.reminderContent(event: event, preferences: preferences, recording: lastSnapshot.active)
            let trigger = UNTimeIntervalNotificationTrigger(timeInterval: max(1, due.timeIntervalSince(now)), repeats: false)
            do { try await addNotification(UNNotificationRequest(identifier: id, content: content, trigger: trigger)) }
            catch { message = "Напоминание не передано macOS. Встреча доступна в календаре GRAF." }
            if epoch != generation { center?.removePendingNotificationRequests(withIdentifiers: [id]); center?.removeDeliveredNotifications(withIdentifiers: [id]); return }
        }
        reconcileCard()
    }
    static func shouldRemind(_ event: DesktopCalendarPromptEvent, snapshot: DesktopControlSnapshot, now: Date) -> Bool {
        event.joinPromptState.canSurfacePrompt && min(event.endsAt, event.startsAt.addingTimeInterval(300)) > now
            // Пока запись идёт или завершается, не предлагаем пользователю
            // вторую запись ни для текущей, ни для другой встречи.
            && !snapshot.active
            && !snapshot.stopping
    }

    // MARK: - Собственная карточка GRAF

    /// Наблюдаемый эталон: карточка встречи показывается за 15 минут до начала и
    /// держится 120 секунд. Карточка не зависит от разрешения macOS и режима
    /// «Не беспокоить».
    static let cardLeadTime: TimeInterval = 15 * 60
    static let cardDisplayDuration: TimeInterval = 120

    static func cardDeadline(for event: DesktopCalendarPromptEvent) -> Date {
        // Окно начинается за 15 минут до встречи и длится не более 120 секунд;
        // если встреча начинается раньше, карточка исчезает в момент начала.
        let appearanceExpiry = event.startsAt
            .addingTimeInterval(-cardLeadTime + cardDisplayDuration)
        return min(event.endsAt, event.startsAt, appearanceExpiry)
    }

    static func shouldPresentCard(_ event: DesktopCalendarPromptEvent, snapshot: DesktopControlSnapshot, now: Date) -> Bool {
        shouldRemind(event, snapshot: snapshot, now: now)
            && now >= event.startsAt.addingTimeInterval(-cardLeadTime)
            && now < cardDeadline(for: event)
    }

    static func meetingCardContent(event: DesktopCalendarPromptEvent,
                                   preferences: DesktopNotificationPreferences,
                                   timeZone: TimeZone = .current) -> DesktopNotificationCardContent {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.timeZone = timeZone
        formatter.dateFormat = "HH:mm"
        let start = formatter.string(from: event.startsAt)
        let title = preferences.showTitles ? event.safeDisplayTitle() : "Встреча в календаре"
        return .meeting(title: title,
                        startText: "Начало в \(start)",
                        hasJoinLink: safeMeetingURL(event.openMeetingURL) != nil)
    }

    static func cardDismissalKey(_ event: DesktopCalendarPromptEvent, context: String) -> String {
        reminderID(event, context: context)
    }

    /// Приводит карточку в соответствие с текущим набором напоминаний: показывает
    /// актуальную встречу, убирает устаревшую и никогда не возвращает закрытую.
    public func reconcileCard(now: Date = Date()) {
        guard !owner.isEmpty, preferences.reminders, !context.isEmpty else {
            clearCard()
            return
        }
        let candidates = calendarEvents
            .filter { Self.shouldPresentCard($0, snapshot: lastSnapshot, now: now) }
            .filter { !dismissedCards.contains(Self.cardDismissalKey($0, context: context)) }
            .sorted { $0.startsAt < $1.startsAt }
        guard let event = candidates.first else {
            if activeCardOwner == nil || isMeetingCardActive {
                clearCard()
            }
            scheduleCardAppearance(now: now)
            return
        }
        let id = Self.cardDismissalKey(event, context: context)
        if case let .meeting(currentID) = activeCardOwner,
           currentID != id,
           !candidates.contains(where: { Self.cardDismissalKey($0, context: context) == currentID }) {
            clearCard()
        }
        guard canPresent(.meeting(id)) else { return }
        let content = Self.meetingCardContent(event: event, preferences: preferences)
        let deadline = Self.cardDeadline(for: event)
        let unchanged = presentedCardID == id && card.isVisible && card.presentedContent == content
        activeCardOwner = .meeting(id)
        presentedCardID = id
        if !unchanged {
            card.present(content,
                        dismissAfter: deadline,
                        onAction: { [weak self] action in self?.handleCardAction(action, eventID: event.eventId) },
                        onTick: { [weak self] in self?.tickCard(eventID: event.eventId) },
                        onExpire: { [weak self] in
                            // Карточка закрылась сама: следующий показ решает
                            // общая сверка, а не прежнее состояние окна.
                            self?.presentedCardID = nil
                            self?.reconcileCard()
                        },
                        onClose: { [weak self] in self?.dismissCard(eventID: event.eventId) })
        }
        scheduleCardTimer(until: deadline, now: now)
    }

    private var isMeetingCardActive: Bool {
        if case .meeting = activeCardOwner { return true }
        return false
    }

    private func tickCard(eventID: String) -> DesktopNotificationCardContent? {
        guard let event = calendarEvents.first(where: { $0.eventId == eventID }),
              Self.shouldPresentCard(event, snapshot: lastSnapshot, now: Date()),
              let presented = card.presentedContent,
              !dismissedCards.contains(Self.cardDismissalKey(event, context: context)) else { return nil }
        return presented
    }

    private func scheduleCardTimer(until deadline: Date, now: Date) {
        cardTimer?.cancel()
        cardDeadline = deadline
        let delay = max(1, deadline.timeIntervalSince(now))
        cardTimer = Task { [weak self] in
            do { try await Task.sleep(for: .seconds(delay)) } catch { return }
            guard let self else { return }
            await MainActor.run { self.reconcileCard() }
        }
    }

    /// Показывает карточку в момент, когда напоминание становится уместным, даже
    /// если между планированием и этим моментом ничего не менялось.
    private func scheduleCardAppearance(now: Date = Date()) {
        guard !owner.isEmpty, preferences.reminders, !context.isEmpty else { return }
        let upcoming = calendarEvents
            .filter { Self.shouldRemind($0, snapshot: lastSnapshot, now: now) }
            .filter { !dismissedCards.contains(Self.cardDismissalKey($0, context: context)) }
            .map { $0.startsAt.addingTimeInterval(-Self.cardLeadTime) }
            .filter { $0 > now }
        guard let next = upcoming.min() else { return }
        let delay = max(1, next.timeIntervalSince(now))
        cardTimer?.cancel()
        cardTimer = Task { [weak self] in
            do { try await Task.sleep(for: .seconds(delay)) } catch { return }
            guard let self else { return }
            await MainActor.run { self.reconcileCard() }
        }
    }

    private func clearCard() {
        resetCardState()
        card.dismiss()
    }

    private func handleCardAction(_ action: DesktopNotificationCardAction, eventID: String) {
        let now = Date()
        let event = calendarEvents.first { $0.eventId == eventID }
        switch action {
        case .joinAndRecord:
            guard let event, Self.shouldPresentCard(event, snapshot: lastSnapshot, now: now),
                  let url = Self.currentMeetingURL(for: event, events: calendarEvents, now: now) else { return }
            NSWorkspace.shared.open(url)
            model.send(.start)
        case .join:
            guard let event, Self.shouldPresentCard(event, snapshot: lastSnapshot, now: now),
                  let url = Self.currentMeetingURL(for: event, events: calendarEvents, now: now) else { return }
            NSWorkspace.shared.open(url)
        case .record:
            guard let event, Self.shouldPresentCard(event, snapshot: lastSnapshot, now: now) else { return }
            model.send(.start)
        case .openCalendar:
            onOpenCalendar?()
        case .openSettings:
            onOpenSettings?()
        case .stopRecording:
            model.send(.stop)
        case let .openRecording(sessionID):
            model.send(.localRecording(sessionID))
        case .skipRecordingPrompt, .toggleRecordingPromptRemember:
            return
        }
        if action != .stopRecording { dismissCard(eventID: eventID) }
    }

    func dismissCard(eventID: String) {
        guard let event = calendarEvents.first(where: { $0.eventId == eventID }) else {
            clearCard()
            return
        }
        dismissedCards.insert(Self.cardDismissalKey(event, context: context))
        clearCard()
    }

    /// Состояние записи отображается только в самом приложении, строке меню и
    /// панели управления. Рутинные переходы не являются уведомлениями: они не
    /// создают ни карточку, ни системный баннер.
    func updateRecordingIndicator(_ snapshot: DesktopControlSnapshot, elapsed: String) {
        // `elapsed` оставлен в сигнатуре, потому что обновление приходит из
        // общего потока состояния записи. Плавающая поверхность здесь намеренно
        // не создаётся.
        lastRecordingNotice = RecordingNoticeState(snapshot: snapshot)
    }

    /// Последний подтверждённый переход нужен только для защиты от повторной
    /// обработки состояния; пользователь видит его в основном интерфейсе.
    enum RecordingNoticeState: Equatable {
        case recording
        case transcribing
        case finished

        init?(snapshot: DesktopControlSnapshot) {
            guard snapshot.session != nil else { return nil }
            if snapshot.active { self = snapshot.stopping ? .transcribing : .recording }
            else if snapshot.completedRecording { self = .finished }
            else { return nil }
        }
    }

    /// Карточка о проблеме с локальной записью: не зависит от системного баннера.
    @discardableResult
    func presentProblemCard(_ incident: DesktopLocalNotificationIncident) -> Bool {
        let owner: CardOwner = .problem(incident.sessionID)
        guard canPresent(owner) else { return false }
        resetCardState()
        activeCardOwner = owner
        card.present(.problem(title: "Запись требует вашего внимания",
                              message: "Откройте запись в GRAF, чтобы проверить ее сохранность и отправку.",
                              actionTitle: "Открыть запись",
                              sessionID: incident.sessionID),
                     dismissAfter: Date().addingTimeInterval(DesktopNotificationCardPresenter.noticeDisplayDuration),
                     onAction: { [weak self] action in
                         if case let .openRecording(sessionID) = action {
                             self?.model.send(.localRecording(sessionID))
                             self?.dismissExternalCard(owner)
                         }
                     },
                     onExpire: { [weak self] in
                         self?.finishExternalCard(owner)
                         self?.reconcileCard()
                     },
                     onClose: { [weak self] in self?.dismissExternalCard(owner) })
        return card.isVisible && card.presentedContent?.identifier == "graf.card.problem"
    }

    public func dismissAllCards() {
        // Закрытие окна или выход из аккаунта убирает поверхность, но не
        // забывает отказ пользователя для текущей встречи.
        lastRecordingNotice = nil
        clearCard()
    }

    public enum ResponseAction: Equatable { case calendar, join, settings, localRecording }

    public static var notificationCategories: Set<UNNotificationCategory> {
        let settings = UNNotificationAction(identifier: "graf.settings", title: "Настроить уведомления…", options: .foreground)
        let join = UNNotificationAction(identifier: "graf.join", title: "Подключиться", options: .foreground)
        let recording = UNNotificationAction(identifier: "graf.openRecording", title: "Открыть запись", options: .foreground)
        return [
            UNNotificationCategory(identifier: "graf.calendar", actions: [settings], intentIdentifiers: [], options: []),
            UNNotificationCategory(identifier: "graf.calendar.join", actions: [join, settings], intentIdentifiers: [], options: []),
            UNNotificationCategory(identifier: "graf.recording", actions: [recording, settings], intentIdentifiers: [], options: [])
        ]
    }

    public static func responseAction(_ identifier: String, calendar: Bool) -> ResponseAction? {
        switch identifier {
        case UNNotificationDefaultActionIdentifier: return calendar ? .calendar : .localRecording
        case "graf.settings": return .settings
        case "graf.join" where calendar: return .join
        case "graf.openRecording" where !calendar: return .localRecording
        default: return nil
        }
    }

    public static func reminderContent(event: DesktopCalendarPromptEvent,
                                       preferences: DesktopNotificationPreferences,
                                       recording: Bool, timeZone: TimeZone = .current) -> UNMutableNotificationContent {
        let content = UNMutableNotificationContent()
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.timeZone = timeZone
        formatter.dateFormat = "HH:mm"
        content.title = preferences.showTitles ? event.safeDisplayTitle() : "Встреча в календаре"
        content.body = "Начало в \(formatter.string(from: event.startsAt)). Запись еще не начата."
        content.categoryIdentifier = safeMeetingURL(event.openMeetingURL) == nil ? "graf.calendar" : "graf.calendar.join"
        if preferences.sound && !recording { content.sound = .default }
        return content
    }

    private static func safeMeetingURL(_ url: URL?) -> URL? {
        guard let url, url.scheme?.lowercased() == "https", let host = url.host, !host.isEmpty,
              url.user == nil, url.password == nil, url.fragment == nil else { return nil }
        let normalizedHost = host.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "."))
        guard normalizedHost != "localhost", !normalizedHost.hasSuffix(".localhost") else { return nil }
        if let address = IPv4Address(normalizedHost) {
            let bytes = address.rawValue
            let privateRange = bytes[0] == 10
                || (bytes[0] == 172 && (16...31).contains(bytes[1]))
                || (bytes[0] == 192 && bytes[1] == 168)
                || bytes[0] == 127
                || bytes.allSatisfy { $0 == 0 }
            guard !privateRange else { return nil }
        }
        return url
    }

    private func reminderID(_ event: DesktopCalendarPromptEvent) -> String {
        Self.reminderID(event, context: context)
    }
    static func reminderID(_ event: DesktopCalendarPromptEvent, context: String) -> String {
        // eventId identifies a calendar occurrence; moving its start is not a new event.
        let raw = context + ":" + event.eventId
        return "graf.local.reminder." + SHA256.hash(data: Data(raw.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    static func legacyReminderID(_ event: DesktopCalendarPromptEvent, context: String) -> String {
        let raw = context + ":" + event.eventId + ":" + String(event.startsAt.timeIntervalSince1970)
        return "graf.local.reminder." + SHA256.hash(data: Data(raw.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    func refreshLocal(_ snapshot: DesktopControlSnapshot) async {
        guard snapshot == lastSnapshot else { return }
        let epoch = authEpoch
        let incidents = DesktopLocalNotificationIncident.incidents(in: snapshot, now: Date())
            .filter { store.ownsSession($0.sessionID, context: context) }
        store.reconcileIncidents(incidents, knownSessions: Set(snapshot.uploadItems.map(\.sessionId)), owner: owner)
        let desired = Set(incidents.map(\.id))
        let obsolete = requests.filter { $0.value.event == nil && !desired.contains($0.key) }.map(\.key)
        removeNotifications(obsolete)
        obsolete.forEach { requests.removeValue(forKey: $0) }
        guard !incidents.isEmpty, !owner.isEmpty, epoch == authEpoch, snapshot == lastSnapshot else { return }
        guard !card.isVisible || activeCardOwner != .meeting(presentedCardID ?? "") else { return }
        for incident in incidents where incident.fresh {
            guard epoch == authEpoch, snapshot == lastSnapshot else { return }
            guard requests[incident.id] == nil else { continue }
            // Инцидент нельзя поглощать очередью до подтверждённого показа:
            // если более важная карточка уже заняла поверхность, он останется
            // доступен для следующей сверки.
            guard presentProblemCard(incident) else { continue }
            guard store.claimLocalIncident(incident, owner: owner, now: Date()) else { continue }
            requests[incident.id] = (owner, nil, incident.sessionID)
            // Карточка GRAF — единственный канал полезного события: не создаём
            // дублирующий системный баннер.
            center?.removePendingNotificationRequests(withIdentifiers: [incident.id])
            center?.removeDeliveredNotifications(withIdentifiers: [incident.id])
            if epoch != authEpoch || requests[incident.id] == nil {
                removeNotifications([incident.id]); return
            }
        }
    }
    public nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        await presentationOptions(for: notification.request.identifier)
    }
    static func isTestNotification(_ id: String) -> Bool {
        let prefix = "graf.local.test."
        return id == "graf.local.test" || (id.hasPrefix(prefix) && UUID(uuidString: String(id.dropFirst(prefix.count))) != nil)
    }
    func presentationOptions(for id: String) -> UNNotificationPresentationOptions {
        guard Self.isTestNotification(id) || requests[id]?.owner == owner else { return [] }
        // Карточка GRAF уже показывает это событие на экране: системный баннер
        // не дублирует его. Если карточка закрыта, баннер остаётся резервным
        // каналом напоминания.
        if let event = requests[id]?.event, card.isVisible, presentedCardID == id,
           card.presentedContent == Self.meetingCardContent(event: event, preferences: preferences) {
            return []
        }
        if let session = requests[id]?.sessionID {
            guard store.ownsSession(session, context: context),
                  DesktopLocalNotificationIncident.incidents(in: lastSnapshot, now: Date()).contains(where: { $0.sessionID == session }) else { return [] }
            if card.isVisible, card.presentedContent?.identifier == "graf.card.problem" { return [] }
        }
        if let event = requests[id]?.event, !Self.shouldRemind(event, snapshot: lastSnapshot, now: Date()) { return [] }
        return preferences.sound && !lastSnapshot.active ? [.banner, .list, .sound] : [.banner, .list]
    }
    public nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        await openResponse(response.notification.request.identifier, actionIdentifier: response.actionIdentifier)
    }
    public static func currentMeeting(for target: DesktopCalendarPromptEvent,
                                      events: [DesktopCalendarPromptEvent], now: Date = Date()) -> DesktopCalendarPromptEvent? {
        guard let event = events.first(where: { $0.eventId == target.eventId && $0.startsAt == target.startsAt }),
              event.joinPromptState.canSurfacePrompt,
              min(event.endsAt, event.startsAt.addingTimeInterval(300)) > now else { return nil }
        return event
    }
    public static func currentMeetingURL(for target: DesktopCalendarPromptEvent,
                                         events: [DesktopCalendarPromptEvent], now: Date = Date()) -> URL? {
        guard let event = currentMeeting(for: target, events: events, now: now),
              event.meetingLinkPresent else { return nil }
        return safeMeetingURL(event.openMeetingURL)
    }
    func openResponse(_ id: String, actionIdentifier: String) {
        if Self.isTestNotification(id) {
            if actionIdentifier == UNNotificationDefaultActionIdentifier { onOpenSettings?() }
            return
        }
        guard let target = requests[id], target.owner == owner, !owner.isEmpty,
              let action = Self.responseAction(actionIdentifier, calendar: target.event != nil) else { return }
        if let event = target.event {
            let now = Date()
            guard Self.currentMeeting(for: event, events: calendarEvents, now: now) != nil else { return }
            switch action {
            case .settings: onOpenSettings?()
            case .calendar: onOpenCalendar?()
            case .join:
                if let url = Self.currentMeetingURL(for: event, events: calendarEvents, now: now) { NSWorkspace.shared.open(url) }
            case .localRecording: break
            }
        } else if let sessionID = target.sessionID,
                  store.ownsSession(sessionID, context: context),
                  DesktopLocalNotificationIncident.incidents(in: lastSnapshot, now: Date()).contains(where: { $0.sessionID == sessionID && $0.expires > Date() }) {
            if action == .settings { onOpenSettings?() }
            else if action == .localRecording { model.send(.localRecording(sessionID)) }
        }
    }

}

@MainActor
public struct DesktopNotificationsSettingsView: View {
    @ObservedObject private var presenter = DesktopNotificationPresenter.shared
    public init() {}
    private func preference<Value>(_ keyPath: WritableKeyPath<DesktopNotificationPreferences, Value>) -> Binding<Value> {
        Binding(get: { presenter.draft[keyPath: keyPath] }, set: { value in
            var next = presenter.draft
            next[keyPath: keyPath] = value
            presenter.save(next)
        })
    }
    public var body: some View {
        Form {
            Section("Уведомления macOS") {
            Text(presenter.permissionText)
            if presenter.canRequestPermission {
                Button("Включить уведомления на этом Mac") { Task { await presenter.enable() } }
            }
            Button("Открыть настройки macOS") {
                if let url = URL(string: "x-apple.systempreferences:com.apple.preference.notifications") { NSWorkspace.shared.open(url) }
            }
            }
            Group {
                Section("Напоминания и приватность") {
                Toggle("Напоминать о встречах", isOn: preference(\.reminders))
                LabeledContent("Когда напоминать") {
                    NativeSettingsComboBox(
                        title: "Когда напоминать",
                        options: [
                            .init(id: "1", label: "За минуту"),
                            .init(id: "5", label: "За 5 минут"),
                            .init(id: "0", label: "В момент начала"),
                        ],
                        selectedID: String(presenter.draft.offsetMinutes)
                    ) { value in
                        guard let minutes = Int(value), [0, 1, 5].contains(minutes) else { return }
                        preference(\.offsetMinutes).wrappedValue = minutes
                    }
                    .frame(width: 190, height: 32)
                    .disabled(!presenter.draft.reminders)
                }
                Toggle("Показывать названия встреч", isOn: preference(\.showTitles))
                Toggle("Звук уведомлений", isOn: preference(\.sound))
                Text("Во время записи звук выключен.").font(.callout).foregroundStyle(.secondary)
                }
                Section {
                HStack {
                    Button("Проверить уведомление") { Task { await presenter.test() } }
                }
                if presenter.owner.isEmpty { Text("Войдите в GRAF, чтобы сохранить настройки для своего аккаунта.") }
                Text(presenter.message).font(.callout)
                if presenter.saveFailed { Button("Повторить") { presenter.save(presenter.draft) } }
                }
            }
            .disabled(presenter.owner.isEmpty)
        }.formStyle(.columns)
        .toggleStyle(.switch)
        .font(.system(size: 13))
        .padding(24)
        .onAppear { Task { await presenter.refreshPermission() } }
        // macOS may persist an authorization change after the activation callback.
        .onReceive(Timer.publish(every: 2, on: .main, in: .common).autoconnect()) { _ in
            guard NSApp.isActive else { return }
            Task { await presenter.refreshPermission() }
        }
    }
}
