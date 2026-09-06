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
    public func claim(id: String, owner: String, expires: Date, scheduledFor: Date? = nil, now: Date = Date()) -> Bool {
        guard !owner.isEmpty, expires > now else { return false }
        let name = key(owner) + ".attempts"
        var claims = defaults.dictionary(forKey: name) ?? [:]
        claims = claims.filter {
            let expiry = ($0.value as? Double) ?? ($0.value as? [String: Double])?["expires"] ?? 0
            return expiry > now.timeIntervalSince1970
        }
        let digest = SHA256.hash(data: Data(id.utf8)).map { String(format: "%02x", $0) }.joined()
        if let previous = claims[digest] {
            // A future reservation can be replaced after cancellation/restart. Once
            // its due time has passed (or with a legacy claim), never deliver again.
            guard let reservation = previous as? [String: Double],
                  let due = reservation["scheduledFor"], due > now.timeIntervalSince1970,
                  scheduledFor != nil else { return false }
        }
        var reservation = ["expires": expires.timeIntervalSince1970]
        if let scheduledFor { reservation["scheduledFor"] = scheduledFor.timeIntervalSince1970 }
        claims[digest] = reservation
        defaults.set(claims, forKey: name)
        return true
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
        let issues = snapshot.localIssues.filter { store.ownsSession($0.primaryItem.sessionId, context: context) }
        var incidents = issues.map { (id: "graf.local.incident." + $0.primaryItem.id,
            expires: $0.primaryItem.retentionDeadline, fresh: (0..<300).contains(Date().timeIntervalSince($0.primaryItem.updatedAt))) }
        if let session = snapshot.session, store.ownsSession(session.id, context: context),
           snapshot.blocker?.isEmpty == false {
            incidents.append((id: "graf.local.capture." + session.id, expires: Date().addingTimeInterval(86400), fresh: true))
        }
        let desired = Set(incidents.map(\.id))
        let obsolete = requests.filter { $0.value.event == nil && !desired.contains($0.key) }.map(\.key)
        center.removePendingNotificationRequests(withIdentifiers: obsolete)
        center.removeDeliveredNotifications(withIdentifiers: obsolete)
        obsolete.forEach { requests.removeValue(forKey: $0) }
        guard !incidents.isEmpty, !owner.isEmpty, await allowed(), epoch == generation, snapshot == lastSnapshot, !snapshot.active, !NSApp.isActive else { return }
        for incident in incidents where incident.fresh {
            guard store.claim(id: incident.id, owner: owner, expires: incident.expires) else { continue }
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
    }
}
