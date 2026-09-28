import AppKit
import Combine
import Foundation
import SwiftUI
import TwoBrainRecShared

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
            guard custody.requiresUserAttention, custody.normalUserAction != .openReview,
                  custody.custodyState != .processing else { continue }
            let previous = grouped[item.sessionId]
            grouped[item.sessionId] = Self(sessionID: item.sessionId,
                itemIDs: snapshot.uploadItems.filter { $0.sessionId == item.sessionId }.map(\.id),
                expires: now.addingTimeInterval(300),
                fresh: previous?.fresh == true || (0..<300).contains(now.timeIntervalSince(item.updatedAt)))
        }
        if let session = snapshot.session, snapshot.blocker?.isEmpty == false {
            grouped[session.id] = Self(sessionID: session.id,
                itemIDs: snapshot.uploadItems.filter { $0.sessionId == session.id }.map(\.id),
                expires: now.addingTimeInterval(86_400), fresh: true)
        }
        return grouped.values.sorted { $0.sessionID < $1.sessionID }
    }
}

public enum DesktopNotificationHistoryKind: Equatable, Sendable {
    case problem
    case shortRecording
    public var message: String {
        switch self {
        case .problem: return "Запись требует вашего внимания"
        case .shortRecording: return "Запись не сохранена — короче 30 секунд"
        }
    }
}

public struct DesktopNotificationHistoryEntry: Identifiable, Equatable, Sendable {
    public let id: UUID
    public let occurredAt: Date
    public let kind: DesktopNotificationHistoryKind
    public var message: String { kind.message }
}

@MainActor
public final class DesktopNotificationPresenter: NSObject, ObservableObject {
    public static let shared = DesktopNotificationPresenter()
    @Published public private(set) var preferences = DesktopNotificationPreferences()
    @Published public var draft = DesktopNotificationPreferences()
    @Published public private(set) var owner = ""
    @Published public private(set) var message = ""
    @Published public private(set) var saveFailed = false
    @Published public private(set) var history: [DesktopNotificationHistoryEntry] = []
    @Published public private(set) var isPresentationAvailable = true
    @Published public private(set) var presentationEpoch: UInt64 = 0
    @Published public private(set) var authEpoch = 0
    public var canEdit: Bool { !owner.isEmpty && !context.isEmpty && !resetting }
    public let card: DesktopNotificationCardPresenter

    private let store: DesktopNotificationPreferencesStore
    private let model: DesktopControlModel
    private let contextProvider: (@MainActor () async throws -> DesktopNotificationContext)?
    private let clock: () -> Date
    private let playSound: () -> Void
    private let openMeetingEvent: @MainActor (String, @escaping () -> Bool) async -> Bool
    private var context = ""
    private var legacyContext = ""
    private var serverOrigin: String
    private var contextGeneration = 0
    private(set) var calendarEvents: [DesktopCalendarPromptEvent] = []
    private var lastSnapshot = DesktopControlSnapshot()
    private var observations: [AnyCancellable] = []
    private let distributedObservations = DesktopNotificationLifecycleObservations()
    private var wakeTask: Task<Void, Never>?
    private var wakeGeneration = 0
    private var resetting = false
    private var reconciling = false
    private var terminalMeetings: [String: Date] = [:]
    private var pendingProblems: [String: ProblemCandidate] = [:]
    private var pendingShort: ShortCandidate?
    private var active: Envelope?
    enum PresentationBlock: Hashable { case sleep, screens, session, lock, termination }
    private var presentationBlocks: Set<PresentationBlock> = []

    private enum Kind: Int { case preview = 0, meeting, shortRecording, problem, recordingPrompt }
    private struct ProblemCandidate {
        let incident: DesktopLocalNotificationIncident
        let occurredAt: Date
    }
    private struct ShortCandidate {
        let id: String
        let queuedUntil: Date
    }
    private final class Envelope {
        let token = UUID()
        let epoch: Int
        let identity: String
        let kind: Kind
        var deadline: Date
        var content: DesktopNotificationCardContent
        var event: DesktopCalendarPromptEvent?
        var retainsCalendarProjection = false
        var joinState: DesktopNotificationJoinState = .idle
        var joinTask: Task<Void, Never>?
        var sessionID: String?
        var onStart: (() -> Void)?
        var onDismiss: (() -> Void)?
        var onRemember: ((Bool) -> Void)?
        var onSkip: ((Bool) -> Void)?
        var isStillCurrent: (() -> Bool)?
        var onExpire: (() -> Void)?
        var onInvalidated: (() -> Void)?
        var remember = false
        var lastVisibleTick: Date?
        init(epoch: Int, identity: String, kind: Kind, deadline: Date, content: DesktopNotificationCardContent) {
            self.epoch = epoch; self.identity = identity; self.kind = kind
            self.deadline = deadline; self.content = content
        }
    }

    init(store: DesktopNotificationPreferencesStore, model: DesktopControlModel,
         contextProvider: (@MainActor () async throws -> DesktopNotificationContext)? = nil,
         clock: @escaping () -> Date = Date.init, playSound: @escaping () -> Void = { NSSound.beep() },
         openMeetingEvent: @escaping @MainActor (String, @escaping () -> Bool) async -> Bool = {
             await CalendarMeetingOpener.openEvent($0, isCurrent: $1)
         },
         serverOrigin: String = "", card: DesktopNotificationCardPresenter = .init()) {
        self.store = store; self.model = model; self.contextProvider = contextProvider
        self.clock = clock; self.playSound = playSound; self.serverOrigin = Self.normalizedOrigin(serverOrigin)
        self.openMeetingEvent = openMeetingEvent
        self.card = card
        super.init()
        store.beginCalendarRetirement(at: clock())
    }

    public override convenience init() {
        self.init(store: .init(), model: .shared,
                  serverOrigin: DesktopUploadClient.configuredFromEnvironment()?.baseOrigin.absoluteString ?? "")
        DesktopNotificationRetirement.run()
        observeLifecycle()
        observations.append(model.$snapshot.sink { [weak self] in self?.updateSnapshot($0) })
        Task { [weak self] in await self?.refreshContext() }
    }

    deinit {
        wakeTask?.cancel()
    }

    private func observeLifecycle() {
        observations.append(NotificationCenter.default.publisher(for: .twoBrainRecDesktopAuthSessionDidChange)
            .sink { [weak self] _ in
                if Thread.isMainThread { MainActor.assumeIsolated { self?.invalidate() } }
                else { DispatchQueue.main.sync { MainActor.assumeIsolated { self?.invalidate() } } }
                Task { @MainActor [weak self] in await self?.refreshContext() }
            })
        let workspaceEvents: [(Notification.Name, PresentationBlock, Bool)] = [
            (NSWorkspace.willSleepNotification, .sleep, true),
            (NSWorkspace.didWakeNotification, .sleep, false),
            (NSWorkspace.screensDidSleepNotification, .screens, true),
            (NSWorkspace.screensDidWakeNotification, .screens, false),
            (NSWorkspace.sessionDidResignActiveNotification, .session, true),
            (NSWorkspace.sessionDidBecomeActiveNotification, .session, false)
        ]
        for (name, reason, blocked) in workspaceEvents {
            observations.append(NSWorkspace.shared.notificationCenter.publisher(for: name).sink { [weak self] _ in
                // Cancellation is synchronous on the lifecycle event, before a
                // queued timer can attempt an invisible automatic decision.
                if Thread.isMainThread { MainActor.assumeIsolated { self?.setPresentationBlocked(reason, blocked: blocked) } }
                else { DispatchQueue.main.sync { MainActor.assumeIsolated { self?.setPresentationBlocked(reason, blocked: blocked) } } }
            })
        }
        observations.append(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)
            .sink { [weak self] _ in Task { @MainActor in await self?.refreshContext() } })
        observations.append(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)
            .sink { [weak self] _ in MainActor.assumeIsolated { self?.setPresentationBlocked(.termination, blocked: true) } })
        for (name, blocked) in [("com.apple.screenIsLocked", true), ("com.apple.screenIsUnlocked", false)] {
            distributedObservations.add(DistributedNotificationCenter.default(),
                name: NSNotification.Name(name)) { [weak self] in
                    self?.setPresentationBlocked(.lock, blocked: blocked)
                }
        }
    }

    func setPresentationBlocked(_ reason: PresentationBlock, blocked: Bool) {
        if blocked { presentationEpoch &+= 1 }
        if blocked { presentationBlocks.insert(reason) } else { presentationBlocks.remove(reason) }
        isPresentationAvailable = presentationBlocks.isEmpty && !resetting
        if !isPresentationAvailable { dismissAllCards() }
        else { reconcileCard(now: clock()) }
    }

    public func invalidate() {
        contextGeneration += 1; authEpoch += 1
        presentationEpoch &+= 1
        resetting = true; isPresentationAvailable = false
        owner = ""; context = ""; legacyContext = ""
        calendarEvents.removeAll(); pendingProblems.removeAll(); pendingShort = nil
        terminalMeetings.removeAll(); history.removeAll()
        preferences = .init(); draft = preferences; message = ""; saveFailed = false
        dismissAllCards()
        resetting = false; isPresentationAvailable = presentationBlocks.isEmpty
    }

    private static func normalizedOrigin(_ value: String) -> String {
        guard let url = URL(string: value), let scheme = url.scheme?.lowercased(), let host = url.host?.lowercased() else { return value }
        return scheme + "://" + host + (url.port.map { ":\($0)" } ?? "")
    }

    func updateContext(user: String, workspace: String, serverOrigin: String? = nil) {
        guard !user.isEmpty, !workspace.isEmpty else { invalidate(); return }
        let origin = Self.normalizedOrigin(serverOrigin ?? self.serverOrigin)
        let legacy = user.lowercased() + ":" + workspace.lowercased()
        let next = origin.isEmpty ? legacy : origin + "|" + legacy
        guard context != next else { return }
        invalidate()
        self.serverOrigin = origin
        owner = user.lowercased(); context = next; legacyContext = legacy
        preferences = store.load(owner: owner); draft = preferences
    }

    @discardableResult
    public func refreshContext() async -> Int? {
        contextGeneration += 1
        let request = contextGeneration
        do {
            let value: DesktopNotificationContext
            let origin: String
            if let contextProvider { value = try await contextProvider(); origin = serverOrigin }
            else if let client = DesktopUploadClient.configuredFromEnvironment() {
                value = try await client.notificationContext(); origin = client.baseOrigin.absoluteString
            } else { return nil }
            guard request == contextGeneration else { return nil }
            updateContext(user: value.user_id.uuidString, workspace: value.workspace_id.uuidString, serverOrigin: origin)
            let epoch = authEpoch
            await refreshLocal(lastSnapshot)
            return epoch == authEpoch ? epoch : nil
        } catch let error as DesktopUploadClientError {
            if request == contextGeneration && error.failureCategory == .authSession { invalidate() }
        } catch { /* Transient failure cannot replace a confirmed owner. */ }
        return nil
    }

    @discardableResult
    public func saveDraft() -> Bool { save(draft) }

    @discardableResult
    public func save(_ value: DesktopNotificationPreferences) -> Bool {
        do {
            try store.save(value, owner: owner)
            preferences = value; draft = value; saveFailed = false
            message = "Сохранено на этом Mac"
            if value.quiet { pendingProblems.removeAll(); pendingShort = nil }
            reconcileCard(now: clock())
            return true
        } catch {
            draft = value; saveFailed = true
            message = "Не сохранено. Действуют прежние настройки."
            return false
        }
    }

    public func updateCalendar(_ response: DesktopCalendarPromptResponse) {
        guard let user = response.notificationOwnerID, let workspace = response.notificationWorkspaceID else {
            clearCalendar(); return
        }
        updateContext(user: user, workspace: workspace)
        active?.retainsCalendarProjection = false
        calendarEvents = response.events
        reconcileCard(now: clock())
    }
    public func updateCalendarProjection(_ update: CalendarProjectionUpdate) {
        switch update {
        case let .confirmed(response): updateCalendar(response)
        case .invalidated: clearCalendar()
        case .temporarilyUnavailable:
            let now = clock()
            // Keep only the already visible occurrence, never the stale queue.
            // Its envelope and original deadline remain the authority.
            if let current = active, current.kind == .meeting,
               card.isVisible, isCurrent(current, now: now) {
                current.retainsCalendarProjection = true
                calendarEvents = calendarEvents.filter {
                    Self.reminderID($0, context: context) == current.identity
                }
            } else { calendarEvents.removeAll() }
            reconcileCard(now: now)
        }
    }
    private func clearCalendar() { calendarEvents.removeAll(); reconcileCard(now: clock()) }

    @discardableResult
    func updateSnapshot(_ snapshot: DesktopControlSnapshot) -> Task<Void, Never>? {
        guard snapshot != lastSnapshot else { return nil }
        if snapshot.active, snapshot.session?.id != lastSnapshot.session?.id || !lastSnapshot.active,
           let id = snapshot.session?.id { store.bindSession(id, context: context) }
        lastSnapshot = snapshot
        let epoch = authEpoch
        reconcileCard(now: clock())
        return Task { [weak self] in
            guard let self, epoch == self.authEpoch, snapshot == self.lastSnapshot else { return }
            await self.refreshLocal(snapshot)
        }
    }

    func refreshLocal(_ snapshot: DesktopControlSnapshot) async {
        guard snapshot == lastSnapshot, !owner.isEmpty, !context.isEmpty else { return }
        let now = clock()
        let sessionIDs = Set(snapshot.uploadItems.map(\.sessionId) + [snapshot.session?.id].compactMap { $0 })
        for id in sessionIDs { store.adoptLegacySession(id, context: context, legacyContext: legacyContext) }
        let incidents = DesktopLocalNotificationIncident.incidents(in: snapshot, now: now)
            .filter { store.ownsSession($0.sessionID, context: context) }
        let ownedSessions = Set(sessionIDs.filter { store.ownsSession($0, context: context) })
        store.reconcileIncidents(incidents, knownSessions: ownedSessions, owner: owner)
        let current = Set(incidents.map(\.id))
        pendingProblems = pendingProblems.filter { current.contains($0.key) && $0.value.incident.expires > now }
        for incident in incidents where incident.fresh {
            guard store.claimLocalIncident(incident, owner: owner, now: now) else { continue }
            appendHistory(.problem, now: now)
            guard !preferences.quiet, isPresentationAvailable else { continue }
            let occurred = snapshot.uploadItems.filter { $0.sessionId == incident.sessionID }.map(\.updatedAt).min() ?? now
            pendingProblems[incident.id] = ProblemCandidate(incident: incident, occurredAt: occurred)
        }
        reconcileCard(now: now)
    }

    private func appendHistory(_ kind: DesktopNotificationHistoryKind, now: Date) {
        history.insert(.init(id: UUID(), occurredAt: now, kind: kind), at: 0)
        if history.count > 50 { history.removeLast(history.count - 50) }
    }

    static func reminderID(_ event: DesktopCalendarPromptEvent, context: String) -> String {
        "graf.local.reminder." + DesktopNotificationPreferencesStore.digest(
            context + ":" + event.eventId + ":" + String(event.startsAt.timeIntervalSince1970))
    }
    static func cardDue(for event: DesktopCalendarPromptEvent, offsetMinutes: Int = 1) -> Date {
        event.startsAt.addingTimeInterval(-Double(offsetMinutes * 60))
    }
    static func cardDeadline(for event: DesktopCalendarPromptEvent, offsetMinutes: Int = 1) -> Date {
        min(cardDue(for: event, offsetMinutes: offsetMinutes).addingTimeInterval(120), event.endsAt)
    }
    static func shouldRemind(_ event: DesktopCalendarPromptEvent, snapshot: DesktopControlSnapshot, now: Date) -> Bool {
        event.joinPromptState.canSurfacePrompt && event.endsAt > now && !snapshot.active && !snapshot.stopping
    }
    static func shouldPresentCard(_ event: DesktopCalendarPromptEvent, snapshot: DesktopControlSnapshot,
                                  now: Date, offsetMinutes: Int = 1) -> Bool {
        shouldRemind(event, snapshot: snapshot, now: now)
            && now >= cardDue(for: event, offsetMinutes: offsetMinutes)
            && now < cardDeadline(for: event, offsetMinutes: offsetMinutes)
    }
    static func meetingCardContent(event: DesktopCalendarPromptEvent, preferences: DesktopNotificationPreferences,
                                   timeZone: TimeZone = .current, joinState: DesktopNotificationJoinState = .idle) -> DesktopNotificationCardContent {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU"); formatter.timeZone = timeZone; formatter.dateFormat = "HH:mm"
        return .meeting(title: preferences.showTitles ? event.safeDisplayTitle() : "Встреча в календаре",
                        startText: "Начало в \(formatter.string(from: event.startsAt))",
                        hasJoinLink: event.meetingLinkPresent && safeMeetingURL(event.openMeetingURL) != nil, joinState: joinState)
    }
    private func meetingEligible(_ event: DesktopCalendarPromptEvent, now: Date) -> Bool {
        !owner.isEmpty && preferences.reminders && !preferences.quiet
            && Self.shouldPresentCard(event, snapshot: lastSnapshot, now: now, offsetMinutes: preferences.offsetMinutes)
    }
    private func isCurrent(_ envelope: Envelope, now: Date) -> Bool {
        guard envelope.epoch == authEpoch, isPresentationAvailable else { return false }
        switch envelope.kind {
        case .recordingPrompt:
            return !lastSnapshot.active && !lastSnapshot.stopping && (envelope.isStillCurrent?() ?? true)
        case .meeting:
            guard let target = envelope.event, now < envelope.deadline,
                  let event = Self.currentMeeting(for: target, events: calendarEvents, now: now),
                  event.openMeetingURL == target.openMeetingURL,
                  event.meetingLinkPresent == target.meetingLinkPresent else { return false }
            return meetingEligible(event, now: now)
        case .problem:
            guard !preferences.quiet, let sessionID = envelope.sessionID,
                  store.ownsSession(sessionID, context: context) else { return false }
            return DesktopLocalNotificationIncident.incidents(in: lastSnapshot, now: now).contains { $0.sessionID == sessionID }
        case .shortRecording: return !preferences.quiet
        case .preview: return true
        }
    }

    public func reconcileCard(now: Date = Date()) {
        guard !reconciling else { return }
        reconciling = true
        defer { reconciling = false; armWake(now: now) }
        guard isPresentationAvailable else { return }
        terminalMeetings = terminalMeetings.filter { $0.value > now }
        let currentIncidents = Set(DesktopLocalNotificationIncident.incidents(in: lastSnapshot, now: now).map(\.id))
        pendingProblems = pendingProblems.filter {
            $0.value.incident.expires > now && currentIncidents.contains($0.key)
                && store.ownsSession($0.value.incident.sessionID, context: context)
        }
        if let short = pendingShort, short.queuedUntil <= now { pendingShort = nil }
        if let current = active {
            if !isCurrent(current, now: now) || !card.isVisible { invalidateEnvelope(current) }
            else if current.kind == .meeting, let event = calendarEvents.first(where: {
                Self.reminderID($0, context: context) == current.identity
            }) {
                let content = Self.meetingCardContent(event: event, preferences: preferences, joinState: current.joinState)
                current.content = content
                if !card.update(content) { invalidateEnvelope(current) }
            }
        }
        if active?.kind == .recordingPrompt { return }
        if let problem = pendingProblems.values.sorted(by: {
            $0.occurredAt == $1.occurredAt ? $0.incident.id < $1.incident.id : $0.occurredAt < $1.occurredAt
        }).first, active == nil || active!.kind.rawValue < Kind.problem.rawValue {
            let incident = problem.incident
            let envelope = Envelope(epoch: authEpoch, identity: incident.id, kind: .problem,
                deadline: now.addingTimeInterval(DesktopNotificationCardPresenter.noticeDisplayDuration),
                content: .problem(title: "Запись требует вашего внимания",
                    message: "Откройте запись в GRAF, чтобы проверить её сохранность и отправку.",
                    actionTitle: "Открыть запись", sessionID: incident.sessionID))
            envelope.sessionID = incident.sessionID
            pendingProblems.removeValue(forKey: incident.id)
            _ = show(envelope)
        }
        if let short = pendingShort, active == nil || active!.kind.rawValue < Kind.shortRecording.rawValue {
            pendingShort = nil
            let envelope = Envelope(epoch: authEpoch, identity: short.id, kind: .shortRecording,
                                    deadline: now.addingTimeInterval(DesktopNotificationCardPresenter.noticeDisplayDuration),
                                    content: .shortRecording)
            _ = show(envelope)
        }
        guard active == nil || active!.kind == .preview else { return }
        let events = calendarEvents.filter { meetingEligible($0, now: now) }
            .filter { terminalMeetings[Self.reminderID($0, context: context)] == nil }
            .sorted { $0.startsAt == $1.startsAt ? $0.eventId < $1.eventId : $0.startsAt < $1.startsAt }
        guard let event = events.first(where: {
            store.claimMeeting(eventID: $0.eventId, startsAt: $0.startsAt, endsAt: $0.endsAt,
                owner: owner, context: context, legacyContext: legacyContext, now: now)
        }) else { return }
        let envelope = Envelope(epoch: authEpoch, identity: Self.reminderID(event, context: context), kind: .meeting,
            deadline: Self.cardDeadline(for: event, offsetMinutes: preferences.offsetMinutes),
            content: Self.meetingCardContent(event: event, preferences: preferences))
        envelope.event = event
        _ = show(envelope)
    }

    // One one-shot wake complements the card's sole visible ticker.
    private func armWake(now: Date) {
        wakeTask?.cancel(); wakeTask = nil; wakeGeneration += 1
        guard isPresentationAvailable else { return }
        var dates: [Date] = []
        if !owner.isEmpty, preferences.reminders, !preferences.quiet, !lastSnapshot.active, !lastSnapshot.stopping {
            dates += calendarEvents.filter {
                Self.shouldRemind($0, snapshot: lastSnapshot, now: now)
                    && terminalMeetings[Self.reminderID($0, context: context)] == nil
            }.map { Self.cardDue(for: $0, offsetMinutes: preferences.offsetMinutes) }.filter { $0 > now }
        }
        if let current = active, current.kind == .meeting { dates.append(current.deadline) }
        if let short = pendingShort { dates.append(short.queuedUntil) }
        guard let next = dates.filter({ $0 > now }).min() else { return }
        let generation = wakeGeneration
        let epoch = authEpoch
        let delay = next.timeIntervalSince(now)
        wakeTask = Task { [weak self] in
            do { try await Task.sleep(for: .seconds(delay)) } catch { return }
            guard let self, self.wakeGeneration == generation, self.authEpoch == epoch else { return }
            self.reconcileCard(now: self.clock())
        }
    }

    @discardableResult
    private func show(_ envelope: Envelope) -> Bool {
        guard isPresentationAvailable else { return false }
        if let previous = active {
            guard envelope.kind.rawValue > previous.kind.rawValue else { return false }
            invalidateEnvelope(previous)
            guard active == nil, isPresentationAvailable, envelope.epoch == authEpoch else { return false }
        }
        active = envelope
        let token = envelope.token
        let shown = card.present(envelope.content,
            dismissAfter: envelope.kind == .recordingPrompt ? nil : envelope.deadline,
            onAction: { [weak self] in self?.handleAction($0, token: token) },
            onTick: { [weak self] in self?.tick(token: token) },
            onExpire: { [weak self] in self?.expire(token: token) },
            onClose: { [weak self] in self?.close(token: token) },
            onInvalidated: { [weak self] in self?.surfaceInvalidated(token: token) })
        guard shown, active?.token == token else {
            if active?.token == token { invalidateEnvelope(envelope) }
            return false
        }
        if envelope.kind == .recordingPrompt {
            // Capture the visible surface's single deadline before any terminal
            // callback: the card clears its own fields before delivering it.
            guard let deadline = card.deadline else { invalidateEnvelope(envelope); return false }
            envelope.deadline = deadline
        }
        envelope.lastVisibleTick = clock()
        if envelope.kind != .preview, envelope.kind != .recordingPrompt,
           preferences.sound, !preferences.quiet, !lastSnapshot.active { playSound() }
        return true
    }
    private func retire(_ envelope: Envelope) {
        guard active?.token == envelope.token else { return }
        active = nil
        envelope.joinTask?.cancel(); envelope.joinTask = nil
        if envelope.kind == .meeting {
            terminalMeetings[envelope.identity] = max(envelope.deadline, envelope.event?.endsAt ?? envelope.deadline)
            if envelope.retainsCalendarProjection { calendarEvents.removeAll() }
        }
        card.dismiss()
    }
    private func invalidateEnvelope(_ envelope: Envelope) {
        guard active?.token == envelope.token else { return }
        retire(envelope)
        envelope.onInvalidated?()
    }
    private func surfaceInvalidated(token: UUID) {
        guard let envelope = active, envelope.token == token else { return }
        invalidateEnvelope(envelope)
        reconcileCard(now: clock())
    }
    private func close(token: UUID) {
        guard let envelope = active, envelope.token == token, envelope.epoch == authEpoch else { return }
        retire(envelope)
        envelope.onDismiss?()
        reconcileCard(now: clock())
    }
    private func expire(token: UUID) {
        guard let envelope = active, envelope.token == token else { return }
        let now = clock()
        let visibleRecently = envelope.lastVisibleTick.map { (0...2.5).contains(now.timeIntervalSince($0)) } ?? false
        let valid = isCurrent(envelope, now: now)
            && (envelope.kind != .recordingPrompt || (visibleRecently && now >= envelope.deadline))
        guard active?.token == token else { return }
        retire(envelope)
        if valid { envelope.onExpire?() } else { envelope.onInvalidated?() }
        reconcileCard(now: clock())
    }
    private func tick(token: UUID) -> DesktopNotificationCardContent? {
        let now = clock()
        guard let envelope = active, envelope.token == token, isCurrent(envelope, now: now),
              active?.token == token, card.isVisible else { return nil }
        if envelope.kind == .recordingPrompt, let previous = envelope.lastVisibleTick,
           !(0...2.5).contains(now.timeIntervalSince(previous)) { return nil }
        envelope.lastVisibleTick = now
        guard envelope.kind == .recordingPrompt else { return envelope.content }
        if case let .recordingPrompt(name, _, _) = envelope.content {
            envelope.content = .recordingPrompt(displayName: name,
                remainingSeconds: max(0, Int(ceil(envelope.deadline.timeIntervalSince(now)))), rememberChoice: envelope.remember)
        }
        return envelope.content
    }
    private func handleAction(_ action: DesktopNotificationCardAction, token: UUID) {
        guard let envelope = active, envelope.token == token else { return }
        guard isCurrent(envelope, now: clock()),
              envelope.kind != .recordingPrompt || clock() < envelope.deadline else {
            invalidateEnvelope(envelope)
            reconcileCard(now: clock())
            return
        }
        guard active?.token == token else { return }
        if case let .toggleRecordingPromptRemember(value) = action {
            guard envelope.kind == .recordingPrompt else { return }
            envelope.remember = value
            if case let .recordingPrompt(name, seconds, _) = envelope.content {
                envelope.content = .recordingPrompt(displayName: name, remainingSeconds: seconds, rememberChoice: value)
                _ = card.update(envelope.content)
            }
            envelope.onRemember?(value)
            return
        }
        if envelope.kind == .meeting, action == .join || action == .joinAndRecord {
            guard envelope.joinState != .opening, let event = envelope.event,
                  Self.currentMeetingURL(for: event, events: calendarEvents, now: clock()) != nil else { return }
            envelope.joinState = .opening
            reconcileCard(now: clock())
            let presentation = presentationEpoch
            let isCurrent = { [weak self, weak envelope] in
                guard let self, let envelope else { return false }
                return self.active?.token == token && self.presentationEpoch == presentation
                    && self.card.isVisible && self.isCurrent(envelope, now: self.clock())
            }
            envelope.joinTask = Task { [weak self, weak envelope] in
                guard let self, let envelope else { return }
                let opened = await self.openMeetingEvent(event.eventId, isCurrent)
                guard !Task.isCancelled, isCurrent() else { return }
                envelope.joinTask = nil
                if opened {
                    self.retire(envelope)
                    if action == .joinAndRecord { self.model.send(.start) }
                } else { envelope.joinState = .failed }
                self.reconcileCard(now: self.clock())
            }
            return
        }
        retire(envelope)
        if envelope.kind == .recordingPrompt {
            switch action {
            case .record: envelope.onStart?()
            case .skipRecordingPrompt: envelope.onSkip?(envelope.remember)
            default: break
            }
        } else if envelope.kind == .meeting {
            switch action {
            case .record: model.send(.start)
            default: break
            }
        } else if envelope.kind == .problem, case let .openRecording(sessionID) = action,
                  sessionID == envelope.sessionID { model.send(.localRecording(sessionID)) }
        reconcileCard(now: clock())
    }

    @discardableResult
    public func presentRecordingPrompt(displayName: String, rememberChoice: Bool = false,
        onStart: @escaping () -> Void, onDismiss: @escaping () -> Void,
        onRememberChoiceChanged: @escaping (Bool) -> Void,
        isStillCurrent: (() -> Bool)? = nil, onExpire: (() -> Void)? = nil,
        onSkip: ((Bool) -> Void)? = nil, onInvalidated: (() -> Void)? = nil) -> Bool {
        guard isPresentationAvailable, !lastSnapshot.active, !lastSnapshot.stopping, active?.kind != .recordingPrompt else { return false }
        let envelope = Envelope(epoch: authEpoch, identity: UUID().uuidString, kind: .recordingPrompt,
            deadline: clock().addingTimeInterval(DesktopNotificationCardPresenter.recordingPromptDisplayDuration),
            content: .recordingPrompt(displayName: displayName,
                remainingSeconds: Int(DesktopNotificationCardPresenter.recordingPromptDisplayDuration), rememberChoice: rememberChoice))
        envelope.remember = rememberChoice
        envelope.onStart = onStart; envelope.onDismiss = onDismiss; envelope.onRemember = onRememberChoiceChanged
        envelope.isStillCurrent = isStillCurrent; envelope.onExpire = onExpire; envelope.onSkip = onSkip
        envelope.onInvalidated = onInvalidated
        return show(envelope)
    }
    @discardableResult
    public func presentShortRecording() -> Bool {
        let now = clock()
        appendHistory(.shortRecording, now: now)
        guard !preferences.quiet, isPresentationAvailable else { return false }
        let id = UUID().uuidString
        pendingShort = ShortCandidate(id: id, queuedUntil: now.addingTimeInterval(20))
        reconcileCard(now: now)
        return active?.identity == id && card.isVisible
    }
    @discardableResult
    public func presentPreview(title: String, message: String) -> Bool {
        guard active == nil, isPresentationAvailable else { return false }
        let envelope = Envelope(epoch: authEpoch, identity: UUID().uuidString, kind: .preview,
            deadline: clock().addingTimeInterval(DesktopNotificationCardPresenter.previewDisplayDuration),
            content: .preview(title: title, message: message))
        return show(envelope)
    }
    public func testNotification(isCurrent: () -> Bool = { true }) async {
        guard isCurrent() else { return }
        message = presentPreview(title: "Проверка уведомлений GRAF", message: "Так выглядит напоминание о встрече.")
            ? "Проверочное уведомление показано."
            : "Сейчас показано другое уведомление. Повторите проверку после его закрытия."
    }
    @discardableResult
    public func focusCurrentNotification() -> Bool { card.focus() }
    public func dismissShortRecording() { pendingShort = nil; dismiss(kind: .shortRecording) }
    public func dismissRecordingPrompt() { dismiss(kind: .recordingPrompt) }
    private func dismiss(kind: Kind) {
        guard let current = active, current.kind == kind else { return }
        invalidateEnvelope(current)
        reconcileCard(now: clock())
    }
    public func dismissAllCards() {
        let wasResetting = resetting
        resetting = true; isPresentationAvailable = false
        wakeTask?.cancel(); wakeTask = nil; wakeGeneration += 1
        pendingShort = nil; pendingProblems.removeAll()
        if let current = active { invalidateEnvelope(current) }
        else { card.dismiss() }
        resetting = wasResetting; isPresentationAvailable = presentationBlocks.isEmpty && !resetting
    }

    public static func currentMeeting(for target: DesktopCalendarPromptEvent,
        events: [DesktopCalendarPromptEvent], now: Date = Date()) -> DesktopCalendarPromptEvent? {
        guard let event = events.first(where: { $0.eventId == target.eventId && $0.startsAt == target.startsAt }),
              event.joinPromptState.canSurfacePrompt, event.endsAt > now else { return nil }
        return event
    }
    public static func currentMeetingURL(for target: DesktopCalendarPromptEvent,
        events: [DesktopCalendarPromptEvent], now: Date = Date()) -> URL? {
        guard let event = currentMeeting(for: target, events: events, now: now), event.meetingLinkPresent else { return nil }
        return safeMeetingURL(event.openMeetingURL)
    }
    private static func safeMeetingURL(_ url: URL?) -> URL? {
        guard let url, url.fragment == nil else { return nil }
        return CalendarMeetingOpener.validatedHTTPS(url.absoluteString)
    }
}

/// Owns registrations independently of the presenter's actor isolation. Releasing
/// this holder removes every registration without accessing actor state in deinit.
private final class DesktopNotificationLifecycleObservations {
    private var tokens: [(NotificationCenter, NSObjectProtocol)] = []

    @MainActor
    func add(_ center: NotificationCenter, name: Notification.Name,
             handler: @escaping @MainActor @Sendable () -> Void) {
        let token = center.addObserver(forName: name, object: nil, queue: .main) { _ in
            MainActor.assumeIsolated { handler() }
        }
        tokens.append((center, token))
    }

    deinit {
        for (center, token) in tokens { center.removeObserver(token) }
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
            presenter.draft = next
            presenter.saveDraft()
        })
    }
    public var body: some View {
        Form {
            Section("Напоминания и приватность") {
                Toggle("Напоминать о встречах", isOn: preference(\.reminders))
                LabeledContent("Когда напоминать") {
                    NativeSettingsComboBox(title: "Когда напоминать", options: [
                        .init(id: "0", label: "В момент начала"), .init(id: "1", label: "За минуту"),
                        .init(id: "5", label: "За 5 минут")
                    ], selectedID: String(presenter.draft.offsetMinutes)) { value in
                        guard let minutes = Int(value), [0, 1, 5].contains(minutes) else { return }
                        preference(\.offsetMinutes).wrappedValue = minutes
                    }.frame(width: 190, height: 32).disabled(!presenter.draft.reminders)
                }
                Toggle("Показывать названия встреч", isOn: preference(\.showTitles))
                Toggle("Звук уведомлений", isOn: preference(\.sound))
                Toggle("Тихий режим", isOn: preference(\.quiet))
                Text("Тихий режим отключает необязательные сообщения и звук, но сохраняет вопрос о начале записи, индикатор и остановку записи.")
                    .font(.callout).foregroundStyle(.secondary)
            }.disabled(!presenter.canEdit)
            Section {
                Text("Карточки показываются, пока GRAF запущен. Они не следуют настройкам фокусирования macOS автоматически.")
                    .font(.callout).foregroundStyle(.secondary)
                Button("Проверить уведомление") { Task { await presenter.testNotification() } }
                if !presenter.canEdit { Text("Войдите в GRAF, чтобы сохранить настройки для своего аккаунта.") }
                Text(presenter.message).font(.callout)
                if presenter.saveFailed { Button("Повторить") { presenter.saveDraft() } }
            }
        }.formStyle(.columns).toggleStyle(.switch).font(.system(size: 13)).padding(24)
    }
}
