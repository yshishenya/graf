import AppKit
import Combine
import CryptoKit
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
        let expires = max(previous ?? 0, incident.expires.timeIntervalSince1970)
        for digest in digests { claims[digest] = expires }
        defaults.set(claims, forKey: name)
        return previous == nil
    }
    public func claim(id: String, owner: String, expires: Date, scheduledFor: Date? = nil, now: Date = Date()) -> Bool {
        guard !owner.isEmpty, expires > now else { return false }
        let name = key(owner) + ".attempts"
        var claims = defaults.dictionary(forKey: name) as? [String: Double] ?? [:]
        claims = claims.filter { $0.value > now.timeIntervalSince1970 }
        let reservationKey = name + ".reservations"
        var reservations = defaults.dictionary(forKey: reservationKey) as? [String: [String: Double]] ?? [:]
        reservations = reservations.filter { ($0.value["expires"] ?? 0) > now.timeIntervalSince1970 }
        let digest = SHA256.hash(data: Data(id.utf8)).map { String(format: "%02x", $0) }.joined()
        if claims[digest] != nil {
            // A future reservation can be replaced after cancellation/restart. Once
            // its due time has passed (or with a legacy claim), never deliver again.
            guard let due = reservations[digest]?["scheduledFor"], due > now.timeIntervalSince1970,
                  scheduledFor != nil else { return false }
        }
        // Keep the old numeric ledger readable on rollback. Write its deny marker
        // first: interruption before the atomic reservation write stays silent.
        claims[digest] = expires.timeIntervalSince1970
        defaults.set(claims, forKey: name)
        var reservation = ["expires": expires.timeIntervalSince1970]
        if let scheduledFor { reservation["scheduledFor"] = scheduledFor.timeIntervalSince1970 }
        reservations[digest] = reservation
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
        for issue in snapshot.localIssues {
            let item = issue.primaryItem
            let previous = grouped[item.sessionId]
            grouped[item.sessionId] = Self(sessionID: item.sessionId,
                itemIDs: snapshot.uploadItems.filter { $0.sessionId == item.sessionId }.map(\.id),
                expires: max(previous?.expires ?? item.retentionDeadline, item.retentionDeadline),
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

    func claimForDelivery(store: DesktopNotificationPreferencesStore, owner: String,
                          visibleResultSessionID: String?, now: Date) -> Bool {
        // Only this recording was shown; another recording must keep its own
        // attention path even while this result is visible.
        if visibleResultSessionID == sessionID {
            _ = store.claimLocalIncident(self, owner: owner, now: now)
            return false
        }
        return store.claimLocalIncident(self, owner: owner, now: now)
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
    private let center = UNUserNotificationCenter.current()
    private let store = DesktopNotificationPreferencesStore()
    private var context = ""
    private var generation = 0
    private var schedulingReminders = false
    private var calendarEvents: [DesktopCalendarPromptEvent] = []
    private var requests: [String: (owner: String, event: DesktopCalendarPromptEvent?)] = [:]
    private var observation: AnyCancellable?
    private var resultVisibilityObservation: AnyCancellable?
    private var activationObservation: AnyCancellable?
    private var settingsObservation: AnyCancellable?
    private var permissionGeneration = 0
    private var lastSnapshot = DesktopControlSnapshot()
    public override init() {
        super.init()
        center.delegate = self
        center.removeAllPendingNotificationRequests()
        center.removeAllDeliveredNotifications()
        activationObservation = NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification).sink { [weak self] _ in
            Task { await self?.refreshPermission() }
        }
        settingsObservation = NotificationCenter.default.publisher(for: NSWindow.didBecomeKeyNotification)
            .filter { ($0.object as? NSWindow)?.identifier?.rawValue == "graf-settings-window" }
            .sink { [weak self] _ in Task { await self?.refreshPermission() } }
        resultVisibilityObservation = DesktopControlModel.shared.$visibleResultSessionID.removeDuplicates().sink { [weak self] _ in
            guard let self else { return }
            self.generation += 1
            Task { await self.refreshLocal(self.lastSnapshot) }
        }
        observation = DesktopControlModel.shared.$snapshot.sink { [weak self] snapshot in
            guard let self, snapshot != self.lastSnapshot else { return }
            let activeChanged = snapshot.active != self.lastSnapshot.active
            if snapshot.active, snapshot.session?.id != self.lastSnapshot.session?.id || !self.lastSnapshot.active,
               let id = snapshot.session?.id { self.store.bindSession(id, context: self.context) }
            if snapshot.active != self.lastSnapshot.active { self.generation += 1 }
            self.lastSnapshot = snapshot
            Task {
                if activeChanged { await self.scheduleReminders() }
                await self.refreshLocal(snapshot)
            }
        }
    }
    public func invalidate() {
        generation += 1
        center.removeAllPendingNotificationRequests()
        center.removeAllDeliveredNotifications()
        requests.removeAll(); calendarEvents.removeAll()
        owner = ""; context = ""; preferences = .init(); draft = preferences; message = ""
    }
    public func clearCalendar() {
        generation += 1
        let ids = requests.filter { $0.value.event != nil }.map(\.key)
        center.removePendingNotificationRequests(withIdentifiers: ids)
        center.removeDeliveredNotifications(withIdentifiers: ids)
        ids.forEach { requests.removeValue(forKey: $0) }
        calendarEvents = []
    }
    public func updateCalendar(_ response: DesktopCalendarPromptResponse) {
        guard let user = response.notificationOwnerID, let workspace = response.notificationWorkspaceID else {
            invalidate(); return
        }
        let newContext = user + ":" + workspace
        if context != newContext {
            invalidate(); owner = user; context = newContext; preferences = store.load(owner: user); draft = preferences
        }
        guard calendarEvents != response.events else { return }
        generation += 1
        calendarEvents = response.events
        Task { await scheduleReminders() }
    }
    public func refreshPermission() async {
        permissionGeneration += 1
        let request = permissionGeneration
        let previous = permissionText
        let settings = await center.notificationSettings()
        guard request == permissionGeneration else { return }
        canRequestPermission = settings.authorizationStatus == .notDetermined
        switch settings.authorizationStatus {
        case .notDetermined: permissionText = "Разрешение ещё не запрашивалось"
        case .denied: permissionText = "Уведомления macOS выключены"
        case .authorized, .provisional, .ephemeral: permissionText = "Уведомления macOS разрешены"
        @unknown default: permissionText = "Статус разрешения неизвестен"
        }
        if permissionText != previous {
            message = ""
            await scheduleReminders()
        }
    }
    public func enable() async {
        do { _ = try await center.requestAuthorization(options: [.alert, .sound]) }
        catch { message = "Не удалось запросить разрешение. Откройте настройки macOS." }
        await refreshPermission(); await scheduleReminders()
    }
    public func save(_ value: DesktopNotificationPreferences) {
        do {
            try store.save(value, owner: owner); generation += 1; preferences = value; draft = value
            if !value.showTitles { center.removeAllDeliveredNotifications() }
            message = "Сохранено на этом Mac"
            Task { await scheduleReminders() }
        } catch { message = "Не удалось сохранить. Проверьте вход в GRAF и повторите попытку." }
    }
    private func allowed() async -> Bool {
        let status = await center.notificationSettings().authorizationStatus
        return status == .authorized || status == .provisional
    }
    public func test() async {
        await refreshPermission()
        guard await allowed() else {
            message = "Разрешите уведомления для GRAF в настройках macOS."; return
        }
        let content = UNMutableNotificationContent()
        content.title = "Проверка уведомлений GRAF"
        content.body = "Это тестовое сообщение. Управление записью всегда доступно в приложении."
        if preferences.sound && !lastSnapshot.active { content.sound = .default }
        do {
            try await center.add(UNNotificationRequest(identifier: "graf.local.test", content: content, trigger: nil))
            message = "Тест передан macOS. Показ зависит от системных настроек и Фокусирования."
        } catch { message = "Не удалось передать тест macOS. Повторите попытку." }
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
        let desired = Set(calendarEvents.filter { $0.joinPromptState.canSurfacePrompt && min($0.endsAt, $0.startsAt.addingTimeInterval(300)) > Date() }.map { reminderID($0) })
        let obsolete = requests.filter { $0.value.event != nil && (!desired.contains($0.key) || !preferences.reminders || lastSnapshot.active) }.map(\.key)
        center.removePendingNotificationRequests(withIdentifiers: obsolete)
        center.removeDeliveredNotifications(withIdentifiers: obsolete)
        obsolete.forEach { requests.removeValue(forKey: $0) }
        guard !owner.isEmpty, preferences.reminders, !lastSnapshot.active, await allowed(), epoch == generation else { return }
        let now = Date()
        for event in calendarEvents {
            guard epoch == generation else { return }
            let expires = min(event.endsAt, event.startsAt.addingTimeInterval(300))
            guard event.joinPromptState.canSurfacePrompt, expires > now else { continue }
            let due = event.startsAt.addingTimeInterval(-Double(preferences.offsetMinutes)*60)
            let id = reminderID(event)
            requests[id] = (owner, event)
            guard store.claim(id: id, owner: owner, expires: expires, scheduledFor: due, now: now) else { continue }
            let content = UNMutableNotificationContent()
            content.title = preferences.showTitles ? event.safeDisplayTitle() : "Встреча в календаре"
            content.body = Self.reminderBody(startsAt: event.startsAt, due: due, offsetMinutes: preferences.offsetMinutes, now: now)
            if preferences.sound { content.sound = .default }
            requests[id] = (owner, event)
            let trigger = UNTimeIntervalNotificationTrigger(timeInterval: max(1, due.timeIntervalSince(now)), repeats: false)
            do { try await center.add(UNNotificationRequest(identifier: id, content: content, trigger: trigger)) }
            catch { message = "Напоминание не передано macOS. Встреча доступна в календаре GRAF." }
            if epoch != generation { center.removePendingNotificationRequests(withIdentifiers: [id]); center.removeDeliveredNotifications(withIdentifiers: [id]); return }
        }
    }
    public static func reminderBody(startsAt: Date, due: Date, offsetMinutes: Int, now: Date) -> String {
        let timing = now >= startsAt ? "Встреча уже началась." : due < now ? "Встреча скоро начнётся." : offsetMinutes == 0 ? "Встреча начинается." : "Встреча начнётся через \(offsetMinutes) мин."
        return timing + " Откройте GRAF, чтобы подключиться."
    }
    private func reminderID(_ event: DesktopCalendarPromptEvent) -> String {
        let raw = context + ":" + event.eventId + ":" + String(event.startsAt.timeIntervalSince1970)
        return "graf.local.reminder." + SHA256.hash(data: Data(raw.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    private func refreshLocal(_ snapshot: DesktopControlSnapshot) async {
        let epoch = generation
        let incidents = DesktopLocalNotificationIncident.incidents(in: snapshot, now: Date())
            .filter { store.ownsSession($0.sessionID, context: context) }
        let desired = Set(incidents.map(\.id))
        let obsolete = requests.filter { $0.value.event == nil && !desired.contains($0.key) }.map(\.key)
        center.removePendingNotificationRequests(withIdentifiers: obsolete)
        center.removeDeliveredNotifications(withIdentifiers: obsolete)
        obsolete.forEach { requests.removeValue(forKey: $0) }
        guard !incidents.isEmpty, !owner.isEmpty, epoch == generation, snapshot == lastSnapshot, !snapshot.active else { return }
        // A visible result is already communicated, including when macOS delivery
        // is denied or GRAF is foreground. Do not replay it after hiding the panel.
        for incident in incidents where incident.fresh && incident.sessionID == DesktopControlModel.shared.visibleResultSessionID {
            _ = store.claimLocalIncident(incident, owner: owner, now: Date())
        }
        guard await allowed(), epoch == generation, snapshot == lastSnapshot, !snapshot.active, !NSApp.isActive else { return }
        for incident in incidents where incident.fresh {
            guard incident.claimForDelivery(store: store, owner: owner,
                visibleResultSessionID: DesktopControlModel.shared.visibleResultSessionID, now: Date()) else { continue }
            let content = UNMutableNotificationContent()
            content.title = "Запись требует вашего внимания"
            content.body = "Откройте локальные записи в GRAF, чтобы проверить запись, отправку и восстановление."
            if preferences.sound && !snapshot.active { content.sound = .default }
            requests[incident.id] = (owner, nil)
            do { try await center.add(UNNotificationRequest(identifier: incident.id, content: content, trigger: nil)) }
            catch { message = "Не удалось передать уведомление macOS. Проверьте локальные записи в GRAF." }
            if epoch != generation || requests[incident.id] == nil {
                center.removePendingNotificationRequests(withIdentifiers: [incident.id])
                center.removeDeliveredNotifications(withIdentifiers: [incident.id]); return
            }
        }
    }
    public nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        guard notification.request.identifier == "graf.local.test" else { return [] }
        return await MainActor.run {
            preferences.sound && !lastSnapshot.active ? [.banner, .list, .sound] : [.banner, .list]
        }
    }
    public nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        await openResponse(response.notification.request.identifier)
    }
    public static func currentMeetingURL(for target: DesktopCalendarPromptEvent,
                                         events: [DesktopCalendarPromptEvent], now: Date = Date()) -> URL? {
        guard let event = events.first(where: { $0.eventId == target.eventId && $0.startsAt == target.startsAt }),
              event.joinPromptState.canSurfacePrompt,
              min(event.endsAt, event.startsAt.addingTimeInterval(300)) > now,
              let url = event.openMeetingURL, url.scheme == "https", url.host != nil else { return nil }
        return url
    }
    private func openResponse(_ id: String) {
        if id == "graf.local.test" { DesktopControlModel.shared.send(.settings); return }
        guard let target = requests[id], target.owner == owner, !owner.isEmpty else { return }
        if let event = target.event {
            guard let url = Self.currentMeetingURL(for: event, events: calendarEvents) else { return }
            NSWorkspace.shared.open(url)
        } else { DesktopControlModel.shared.send(.localRecordings) }
    }
}

public struct DesktopNotificationsSettingsView: View {
    @ObservedObject private var presenter = DesktopNotificationPresenter.shared
    public init() {}
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
            Section("Напоминания и приватность") {
            Toggle("Напоминать о встречах", isOn: $presenter.draft.reminders)
            Picker("Когда напоминать", selection: $presenter.draft.offsetMinutes) {
                Text("За минуту").tag(1); Text("За 5 минут").tag(5); Text("В момент начала").tag(0)
            }.disabled(!presenter.draft.reminders)
            Toggle("Показывать названия в системных уведомлениях", isOn: $presenter.draft.showTitles)
            Toggle("Звук уведомлений", isOn: $presenter.draft.sound)
            Text("Во время записи звук выключен. Результаты встреч доступны в веб-кабинете. Проблемы записи и остановка всегда видны в GRAF.").font(.callout).foregroundStyle(.secondary)
            }
            Section {
            HStack {
                Button("Сохранить") { presenter.save(presenter.draft) }.disabled(presenter.draft == presenter.preferences || presenter.owner.isEmpty)
                Button("Отменить") { presenter.draft = presenter.preferences }.disabled(presenter.draft == presenter.preferences)
                Button("Проверить уведомление") { Task { await presenter.test() } }
            }
            if presenter.owner.isEmpty { Text("Войдите в GRAF, чтобы сохранить настройки для своего аккаунта.") }
            if presenter.draft != presenter.preferences { Text("Изменения не сохранены. Вы можете вернуться к ним в этом окне или отменить их.").font(.callout) }
            Text(presenter.message).font(.callout)
            Text("Проверка использует сохранённые настройки. Показ разрешает macOS.")
                .font(.callout).foregroundStyle(.secondary)
            }
        }.formStyle(.grouped)
        .onAppear { Task { await presenter.refreshPermission() } }
        // macOS may persist an authorization change after the activation callback.
        .onReceive(Timer.publish(every: 2, on: .main, in: .common).autoconnect()) { _ in
            guard NSApp.isActive else { return }
            Task { await presenter.refreshPermission() }
        }
    }
}
