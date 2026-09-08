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
    public var recaps = false
    public init() {}
    private enum CodingKeys: String, CodingKey { case reminders, offsetMinutes, showTitles, sound, recaps }
    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        reminders = try values.decodeIfPresent(Bool.self, forKey: .reminders) ?? true
        offsetMinutes = try values.decodeIfPresent(Int.self, forKey: .offsetMinutes) ?? 1
        showTitles = try values.decodeIfPresent(Bool.self, forKey: .showTitles) ?? false
        sound = try values.decodeIfPresent(Bool.self, forKey: .sound) ?? false
        recaps = try values.decodeIfPresent(Bool.self, forKey: .recaps) ?? false
    }
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
    public var onOpenCalendar: (() -> Void)?
    public var onOpenMeeting: ((UUID) -> Void)?
    private let center: UNUserNotificationCenter?
    private let store: DesktopNotificationPreferencesStore
    private let model: DesktopControlModel
    private let statusProvider: (@MainActor () async -> UNAuthorizationStatus)?
    private let submit: (@MainActor (UNNotificationRequest) async throws -> Void)?
    private let remove: (@MainActor ([String]?) -> Void)?
    private let reconcile: @MainActor (DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation?
    private var context = ""
    private var authEpoch = 0
    private var generation = 0
    private var schedulingReminders = false
    private var calendarEvents: [DesktopCalendarPromptEvent] = []
    private var requests: [String: (owner: String, event: DesktopCalendarPromptEvent?)] = [:]
    private var observation: AnyCancellable?
    private var resultVisibilityObservation: AnyCancellable?
    private var activationObservation: AnyCancellable?
    private var settingsObservation: AnyCancellable?
    private var authObservation: AnyCancellable?
    private var wakeObservation: AnyCancellable?
    private var contextGeneration = 0
    private var recapTargets: [String: String] = [:]
    private var permissionGeneration = 0
    private var lastSnapshot = DesktopControlSnapshot()
    // Inject the OS boundary and model so orchestration tests never initialize
    // the system notification center, observers, or a configured network client.
    init(center: UNUserNotificationCenter? = nil, store: DesktopNotificationPreferencesStore,
         model: DesktopControlModel, status: (@MainActor () async -> UNAuthorizationStatus)? = nil,
         submit: (@MainActor (UNNotificationRequest) async throws -> Void)? = nil,
         remove: (@MainActor ([String]?) -> Void)? = nil,
         reconcile: @escaping @MainActor (DesktopUploadQueueItem) async throws -> DesktopUploadReconciliation? = { _ in nil }) {
        self.center = center; self.store = store; self.model = model
        self.statusProvider = status; self.submit = submit; self.remove = remove; self.reconcile = reconcile
        super.init()
    }
    public override convenience init() {
        self.init(center: .current(), store: .init(), model: .shared, reconcile: { item in
            guard let client = DesktopUploadClient.configuredFromEnvironment() else { return nil }
            return try await client.reconcile(item)
        })
        center?.delegate = self
        removeNotifications()
        authObservation = NotificationCenter.default.publisher(for: .twoBrainRecDesktopAuthSessionDidChange).sink { [weak self] _ in
            Task { @MainActor in
                self?.invalidate()
                await self?.refreshContext()
            }
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
        resultVisibilityObservation = model.$visibleResultSessionID.removeDuplicates().sink { [weak self] _ in
            guard let self else { return }
            self.generation += 1
            Task { await self.refreshLocal(self.lastSnapshot) }
        }
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
        return Task {
            if remindersChanged { await scheduleReminders() }
            await refreshLocal(lastSnapshot)
            await notifyReady()
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
        authEpoch += 1
        generation += 1
        removeNotifications()
        requests.removeAll(); calendarEvents.removeAll()
        recapTargets.removeAll()
        owner = ""; context = ""; preferences = .init(); draft = preferences; message = ""
    }
    public func clearCalendar() {
        generation += 1
        let ids = requests.filter { $0.value.event != nil }.map(\.key)
        removeNotifications(ids)
        ids.forEach { requests.removeValue(forKey: $0) }
        calendarEvents = []
    }
    public func updateCalendar(_ response: DesktopCalendarPromptResponse) {
        guard let user = response.notificationOwnerID, let workspace = response.notificationWorkspaceID else {
            clearCalendar(); return
        }
        updateContext(user: user, workspace: workspace)
        generation += 1
        calendarEvents = response.events
        Task { await scheduleReminders(); await notifyReady() }
    }
    func updateContext(user: String, workspace: String) {
        let newContext = user.lowercased() + ":" + workspace.lowercased()
        if context != newContext {
            invalidate(); owner = user.lowercased(); context = newContext; preferences = store.load(owner: owner); draft = preferences
        }
    }
    public func refreshContext() async {
        contextGeneration += 1
        let epoch = contextGeneration
        guard let client = DesktopUploadClient.configuredFromEnvironment() else { return }
        do {
            let value = try await client.notificationContext()
            guard epoch == contextGeneration else { return }
            updateContext(user: value.user_id.uuidString, workspace: value.workspace_id.uuidString)
            await refreshLocal(lastSnapshot)
            await notifyReady()
        } catch let error as DesktopUploadClientError {
            if epoch == contextGeneration && error.failureCategory == .authSession { invalidate() }
        } catch { /* Keep only the already confirmed context in this auth epoch. */ }
    }
    public func refreshPermission() async {
        permissionGeneration += 1
        let request = permissionGeneration
        let previous = permissionText
        let status = await authorizationStatus()
        guard request == permissionGeneration else { return }
        canRequestPermission = status == .notDetermined
        switch status {
        case .notDetermined: permissionText = "Разрешение ещё не запрашивалось"
        case .denied: permissionText = "Уведомления macOS выключены"
        case .authorized, .provisional, .ephemeral: permissionText = "Уведомления macOS разрешены"
        @unknown default: permissionText = "Статус разрешения неизвестен"
        }
        if permissionText != previous {
            message = ""
            await scheduleReminders()
            await refreshLocal(lastSnapshot)
        }
        // A delivery check may observe denial between permission-text refreshes.
        // Reconsider unclaimed current events even when the displayed text matches.
        await notifyReady()
    }
    public func enable() async {
        guard let center else { return }
        do {
            _ = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Bool, Error>) in
                center.requestAuthorization(options: [.alert, .sound]) { granted, error in
                    if let error { continuation.resume(throwing: error) }
                    else { continuation.resume(returning: granted) }
                }
            }
        }
        catch { message = "Не удалось запросить разрешение. Откройте настройки macOS." }
        await refreshPermission(); await scheduleReminders()
    }
    public func save(_ value: DesktopNotificationPreferences) {
        do {
            try store.save(value, owner: owner); generation += 1; preferences = value; draft = value
            if !value.showTitles { center?.removeAllDeliveredNotifications() }
            if !value.recaps {
                let ids = Array(recapTargets.keys)
                removeNotifications(ids)
                ids.forEach { requests.removeValue(forKey: $0) }
                recapTargets.removeAll()
            }
            message = "Сохранено на этом Mac"
            Task { await scheduleReminders(); await notifyReady() }
        } catch { message = "Не удалось сохранить. Проверьте вход в GRAF и повторите попытку." }
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
            try await addNotification(UNNotificationRequest(identifier: "graf.local.test", content: content, trigger: nil))
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
        let desired = Set(calendarEvents.filter { Self.shouldRemind($0, snapshot: lastSnapshot, now: Date()) }.map { reminderID($0) })
        let obsolete = requests.filter { $0.value.event != nil && (!desired.contains($0.key) || !preferences.reminders) }.map(\.key)
        removeNotifications(obsolete)
        obsolete.forEach { requests.removeValue(forKey: $0) }
        guard !owner.isEmpty, preferences.reminders, await allowed(), epoch == generation else { return }
        let now = Date()
        for event in calendarEvents {
            guard epoch == generation else { return }
            let expires = min(event.endsAt, event.startsAt.addingTimeInterval(300))
            guard Self.shouldRemind(event, snapshot: lastSnapshot, now: now) else { continue }
            let due = event.startsAt.addingTimeInterval(-Double(preferences.offsetMinutes)*60)
            let id = reminderID(event)
            requests[id] = (owner, event)
            guard store.claim(id: id, owner: owner, expires: expires, scheduledFor: due, now: now) else { continue }
            let content = UNMutableNotificationContent()
            content.title = preferences.showTitles ? event.safeDisplayTitle() : "Встреча в календаре"
            content.body = Self.reminderBody(startsAt: event.startsAt, due: due, offsetMinutes: preferences.offsetMinutes, now: now)
            if preferences.sound && !lastSnapshot.active { content.sound = .default }
            let trigger = UNTimeIntervalNotificationTrigger(timeInterval: max(1, due.timeIntervalSince(now)), repeats: false)
            do { try await addNotification(UNNotificationRequest(identifier: id, content: content, trigger: trigger)) }
            catch { message = "Напоминание не передано macOS. Встреча доступна в календаре GRAF." }
            if epoch != generation { removeNotifications([id]); return }
        }
    }
    static func shouldRemind(_ event: DesktopCalendarPromptEvent, snapshot: DesktopControlSnapshot, now: Date) -> Bool {
        event.joinPromptState.canSurfacePrompt && min(event.endsAt, event.startsAt.addingTimeInterval(300)) > now
            && !(snapshot.active && snapshot.calendarContextEventID == event.eventId)
    }
    public static func reminderBody(startsAt: Date, due: Date, offsetMinutes: Int, now: Date) -> String {
        let timing = now >= startsAt ? "Встреча уже началась." : due < now ? "Встреча скоро начнётся." : offsetMinutes == 0 ? "Встреча начинается." : "Встреча начнётся через \(offsetMinutes) мин."
        return timing + " Откройте GRAF, чтобы посмотреть встречу."
    }
    private func reminderID(_ event: DesktopCalendarPromptEvent) -> String {
        let raw = context + ":" + event.eventId + ":" + String(event.startsAt.timeIntervalSince1970)
        return "graf.local.reminder." + SHA256.hash(data: Data(raw.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    private func refreshLocal(_ snapshot: DesktopControlSnapshot) async {
        guard snapshot == lastSnapshot else { return }
        let epoch = authEpoch
        let incidents = DesktopLocalNotificationIncident.incidents(in: snapshot, now: Date())
            .filter { store.ownsSession($0.sessionID, context: context) }
        store.reconcileIncidents(incidents, knownSessions: Set(snapshot.uploadItems.map(\.sessionId)), owner: owner)
        for (id, session) in recapTargets {
            if !preferences.recaps || !store.ownsSession(session, context: context) || !snapshot.uploadItems.contains(where: {
                $0.sessionId == session && Self.recapID($0, context: context) == id
            }) {
                removeNotifications([id])
                recapTargets.removeValue(forKey: id)
                requests.removeValue(forKey: id)
            }
        }
        let desired = Set(incidents.map(\.id))
        let obsolete = requests.filter { $0.value.event == nil && recapTargets[$0.key] == nil && !desired.contains($0.key) }.map(\.key)
        removeNotifications(obsolete)
        obsolete.forEach { requests.removeValue(forKey: $0) }
        guard !incidents.isEmpty, !owner.isEmpty, epoch == authEpoch, snapshot == lastSnapshot else { return }
        // A visible result is already communicated, including when macOS delivery
        // is denied or GRAF is foreground. Do not replay it after hiding the panel.
        for incident in incidents where incident.fresh && incident.sessionID == model.visibleResultSessionID {
            _ = store.claimLocalIncident(incident, owner: owner, now: Date())
        }
        guard await allowed(), epoch == authEpoch, snapshot == lastSnapshot else { return }
        for incident in incidents where incident.fresh {
            guard epoch == authEpoch, snapshot == lastSnapshot else { return }
            guard incident.claimForDelivery(store: store, owner: owner,
                visibleResultSessionID: model.visibleResultSessionID, now: Date()) else { continue }
            let content = UNMutableNotificationContent()
            content.title = "Запись требует вашего внимания"
            content.body = "Откройте локальные записи в GRAF, чтобы проверить запись, отправку и восстановление."
            if preferences.sound && !snapshot.active { content.sound = .default }
            requests[incident.id] = (owner, nil)
            do { try await addNotification(UNNotificationRequest(identifier: incident.id, content: content, trigger: nil)) }
            catch { message = "Не удалось передать уведомление macOS. Проверьте локальные записи в GRAF." }
            if epoch != authEpoch || requests[incident.id] == nil {
                removeNotifications([incident.id]); return
            }
        }
    }
    static func canOpenRecap(_ item: DesktopUploadQueueItem) -> Bool {
        item.state == .uploaded && item.syncConflictState == .none && item.serverTruth.reviewAvailable == true
            && item.serverTruth.deletionState == "none" && item.serverTruth.accessState == "owner"
            && item.serverTruth.meetingId.flatMap(UUID.init(uuidString:)) != nil
    }
    static func recapID(_ item: DesktopUploadQueueItem, context: String) -> String? {
        guard canOpenRecap(item), !context.isEmpty, item.serverTruth.transcriptAvailable == true,
              let event = item.serverTruth.summaryEventId.flatMap(UUID.init(uuidString:)),
              let revision = item.serverTruth.mediaRevisionId, !revision.isEmpty,
              ["available", "partial", "failed", "unavailable"].contains(item.serverTruth.summaryStatus ?? "") else { return nil }
        let raw = [context, item.sessionId, item.serverTruth.meetingId ?? "", revision, event.uuidString].joined(separator: ":")
        return "graf.local.ready." + SHA256.hash(data: Data(raw.utf8)).map { String(format: "%02x", $0) }.joined()
    }
    static func freshRecapID(_ item: DesktopUploadQueueItem, context: String, now: Date = Date()) -> String? {
        // Tolerate bounded server clock skew; receiving metadata is not a new event.
        guard let date = item.serverTruth.summaryUpdatedAt, (-60..<300).contains(now.timeIntervalSince(date)) else { return nil }
        return recapID(item, context: context)
    }
    func notifyReady() async {
        let epoch = authEpoch
        guard preferences.recaps, !context.isEmpty, await allowed(), epoch == authEpoch, preferences.recaps else { return }
        // Read current durable events after permission lookup, not a transition
        // between incidental UI snapshots. Claims survive retries and restarts.
        for candidate in lastSnapshot.uploadItems {
            guard epoch == authEpoch, preferences.recaps else { return }
            guard let item = lastSnapshot.uploadItems.first(where: { $0.id == candidate.id }),
                  store.ownsSession(item.sessionId, context: context),
                  let id = Self.freshRecapID(item, context: context) else { continue }
            guard store.claim(id: id, owner: context, expires: .distantFuture) else { continue }
            let content = UNMutableNotificationContent()
            content.title = ["available", "partial"].contains(item.serverTruth.summaryStatus ?? "")
                ? "Итоги встречи готовы" : "Расшифровка готова"
            content.body = item.serverTruth.summaryStatus == "failed" || item.serverTruth.summaryStatus == "unavailable"
                ? "Итоги не удалось подготовить. Запись и расшифровка доступны в GRAF."
                : "Откройте встречу в GRAF, чтобы посмотреть результат."
            if preferences.sound && !lastSnapshot.active { content.sound = .default }
            requests[id] = (owner, nil)
            recapTargets[id] = item.sessionId
            do { try await addNotification(UNNotificationRequest(identifier: id, content: content, trigger: nil)) }
            catch { message = "Не удалось передать уведомление macOS. Результат доступен в GRAF." }
            if epoch != authEpoch || !preferences.recaps || !lastSnapshot.uploadItems.contains(where: {
                $0.id == item.id && Self.recapID($0, context: context) == id
            }) {
                removeNotifications([id])
                requests.removeValue(forKey: id)
                recapTargets.removeValue(forKey: id)
            }
        }
    }
    public nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        let id = notification.request.identifier
        return await MainActor.run {
            guard id == "graf.local.test" || requests[id]?.owner == owner else { return [] }
            if let session = recapTargets[id] {
                guard preferences.recaps, store.ownsSession(session, context: context),
                      lastSnapshot.uploadItems.contains(where: { $0.sessionId == session && Self.recapID($0, context: context) == id }) else { return [] }
            }
            if let event = requests[id]?.event, !Self.shouldRemind(event, snapshot: lastSnapshot, now: Date()) { return [] }
            return preferences.sound && !lastSnapshot.active ? [.banner, .list, .sound] : [.banner, .list]
        }
    }
    public nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        await openResponse(response.notification.request.identifier)
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
              let url = event.openMeetingURL, url.scheme == "https", url.host != nil else { return nil }
        return url
    }
    func openResponse(_ id: String) async {
        if id == "graf.local.test" { model.send(.settings); return }
        guard let target = requests[id], target.owner == owner, !owner.isEmpty else { return }
        if let session = recapTargets[id] {
            guard preferences.recaps, let item = lastSnapshot.uploadItems.first(where: { $0.sessionId == session && Self.recapID($0, context: context) == id }),
                  store.ownsSession(session, context: context) else { return }
            let epoch = authEpoch
            guard let result = try? await reconcile(item), epoch == authEpoch, preferences.recaps,
                  store.ownsSession(session, context: context), requests[id] != nil,
                  lastSnapshot.uploadItems.contains(where: { $0.id == item.id && Self.recapID($0, context: context) == id }),
                  result.conflictState == .none, result.serverTruth.reviewAvailable == true,
                  result.serverTruth.accessState == "owner", result.serverTruth.deletionState == "none",
                  result.serverTruth.meetingId == item.serverTruth.meetingId,
                  result.serverTruth.mediaRevisionId == item.serverTruth.mediaRevisionId,
                  let rawID = result.serverTruth.meetingId, let meetingID = UUID(uuidString: rawID) else { return }
            onOpenMeeting?(meetingID)
            return
        }
        if let event = target.event {
            let now = Date()
            guard Self.currentMeeting(for: event, events: calendarEvents, now: now) != nil else { return }
            if let url = Self.currentMeetingURL(for: event, events: calendarEvents, now: now) {
                NSWorkspace.shared.open(url)
            } else {
                onOpenCalendar?()
            }
        } else { model.send(.localRecordings) }
    }
}

@MainActor
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
            Toggle("Сообщать, когда итоги моей записи готовы", isOn: $presenter.draft.recaps)
            Picker("Когда напоминать", selection: $presenter.draft.offsetMinutes) {
                Text("За минуту").tag(1); Text("За 5 минут").tag(5); Text("В момент начала").tag(0)
            }.disabled(!presenter.draft.reminders)
            Toggle("Показывать названия в системных уведомлениях", isOn: $presenter.draft.showTitles)
            Toggle("Звук уведомлений", isOn: $presenter.draft.sound)
            Text("Во время записи звук выключен. Уведомление о готовности относится только к вашим записям на этом Mac. Запись и остановка всегда видны в GRAF.").font(.callout).foregroundStyle(.secondary)
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
