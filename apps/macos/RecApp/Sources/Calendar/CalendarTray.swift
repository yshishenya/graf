import AppKit
import Combine
import TwoBrainRecShared

public enum GrafTrayRecordingState: Equatable, Sendable {
    case idle, starting, recording, paused, stopping

    public static func resolve(sessionState: CaptureSessionState?, writerActive: Bool, stopping: Bool, starting: Bool = false) -> Self {
        if stopping { return .stopping }
        if starting { return .starting }
        guard writerActive else { return .idle }
        return sessionState == .paused ? .paused : .recording
    }

    var label: String? {
        switch self {
        case .idle: nil
        case .starting: "Начинаем запись…"
        case .recording: "Идёт запись"
        case .paused: "Идёт запись · микрофон на паузе"
        case .stopping: "Завершаем запись"
        }
    }
}

public enum CalendarTrayState: Equatable, Sendable {
    case idle
    case loading
    case loaded
    case empty
    case needsSignIn
    case unavailable
}

/// The menu-bar surface intentionally owns only a short-lived safe projection.
/// Server truth remains authoritative; no calendar event is persisted locally.
@MainActor
public final class CalendarTrayModel: ObservableObject {
    @Published public private(set) var events: [DesktopCalendarPromptEvent] = []
    @Published public private(set) var state: CalendarTrayState = .idle
    @Published public private(set) var lastUpdatedAt: Date?
    @Published public private(set) var showUpcomingTime = true
    @Published public private(set) var showUpcomingTitle = true
    @Published public var appUpdatePresentation: AppUpdatePresentation = .idle
    @Published public var canCheckForUpdates = false
    @Published public var recordingState: GrafTrayRecordingState = .idle

    private let load: @Sendable () async throws -> DesktopCalendarPromptResponse
    private var refreshGeneration = 0

    public init(
        load: @escaping @Sendable () async throws -> DesktopCalendarPromptResponse
    ) {
        self.load = load
    }

    public func refresh() async {
        refreshGeneration += 1
        let generation = refreshGeneration
        if events.isEmpty && lastUpdatedAt == nil {
            state = .loading
        }
        do {
            let response = try await load()
            guard generation == refreshGeneration else { return }
            showUpcomingTime = response.showUpcomingTime
            showUpcomingTitle = response.showUpcomingTitle
            events = response.events
                .sorted { $0.startsAt == $1.startsAt ? $0.eventId < $1.eventId : $0.startsAt < $1.startsAt }
                .prefix(12)
                .map { $0 }
            state = events.isEmpty ? .empty : .loaded
            lastUpdatedAt = Date()
        } catch let error as DesktopUploadClientError {
            guard generation == refreshGeneration else { return }
            events = []
            state = error.failureCategory == .authSession ? .needsSignIn : .unavailable
        } catch {
            guard generation == refreshGeneration else { return }
            events = []
            state = .unavailable
        }
    }
}

@MainActor
public final class CalendarTrayController: NSObject, NSMenuDelegate {
    private let model: CalendarTrayModel
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let menu = NSMenu(title: "GRAF")
    private var menuIsOpen = false
    private let onOpenCalendar: () -> Void
    private let onOpenMeetings: () -> Void
    private let onUpdate: () -> Void
    private let onStartRecording: () -> Void
    private let onStopRecording: () -> Void
    private var refreshTask: Task<Void, Never>?
    private var observers: [(NotificationCenter, NSObjectProtocol)] = []

    public init(
        model: CalendarTrayModel,
        onOpenCalendar: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void,
        onUpdate: @escaping () -> Void = {},
        onStartRecording: @escaping () -> Void = {},
        onStopRecording: @escaping () -> Void = {}
    ) {
        self.model = model
        self.onOpenCalendar = onOpenCalendar
        self.onOpenMeetings = onOpenMeetings
        self.onUpdate = onUpdate
        self.onStartRecording = onStartRecording
        self.onStopRecording = onStopRecording
        super.init()
        menu.delegate = self
        menu.autoenablesItems = false
        menu.minimumWidth = 240
    }

    public convenience init(
        client: DesktopUploadClient,
        onOpenCalendar: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void
    ) {
        self.init(
            model: CalendarTrayModel {
                try await client.listDesktopCalendarUpcoming(beforeMinutes: 15, afterMinutes: 1_440)
            },
            onOpenCalendar: onOpenCalendar,
            onOpenMeetings: onOpenMeetings
        )
    }

    public func start() {
        guard let button = statusItem.button else { return }
        updateStatusItem()
        button.imagePosition = .imageLeading
        button.imageScaling = .scaleProportionallyDown
        statusItem.menu = menu
        button.setAccessibilityRole(.menuButton)

        observers = [
            (NotificationCenter.default, NotificationCenter.default.addObserver(
                forName: NSApplication.didBecomeActiveNotification,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor in self?.refreshNow() }
            }),
            (NotificationCenter.default, NotificationCenter.default.addObserver(
                forName: .twoBrainRecDesktopAuthSessionDidChange,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor in self?.refreshNow() }
            }),
            (NSWorkspace.shared.notificationCenter, NSWorkspace.shared.notificationCenter.addObserver(
                forName: NSWorkspace.didWakeNotification,
                object: nil,
                queue: .main
            ) { [weak self] _ in
                Task { @MainActor in self?.refreshNow() }
            })
        ]
        refreshTask = Task { [weak self] in
            while !Task.isCancelled {
                self?.refreshNow()
                try? await Task.sleep(for: .seconds(30))
            }
        }
        refreshNow()
    }

    public func showMenu() {
        // The app-menu entry also works when macOS hides a crowded status item.
        if let button = statusItem.button, button.window?.isVisible == true {
            button.performClick(nil)
        } else {
            menu.popUp(positioning: nil, at: NSEvent.mouseLocation, in: nil)
        }
    }

    public func menuNeedsUpdate(_ menu: NSMenu) {
        rebuildMenu()
    }

    public func menuWillOpen(_ menu: NSMenu) {
        menuIsOpen = true
        refreshNow()
    }

    public func menuDidClose(_ menu: NSMenu) {
        menuIsOpen = false
    }

    func rebuildMenu() {
        menu.removeAllItems()
        switch model.recordingState {
        case .idle:
            addItem("Начать запись", action: #selector(startRecording), id: "graf.menu.start")
        case .starting:
            addItem("Начинаем запись…", id: "graf.menu.starting")
        case .recording, .paused:
            addItem("Остановить запись", action: #selector(stopRecording), id: "graf.menu.stop")
            if model.recordingState == .paused {
                addItem("Идёт запись · микрофон на паузе", id: "graf.menu.recordingState")
            }
        case .stopping:
            addItem("Завершаем запись…", id: "graf.menu.stopping")
        }
        menu.addItem(.separator())
        if !model.events.isEmpty {
            addItem("Ближайшие 24 часа", id: "graf.menu.upcoming")
            for event in model.events {
                let title = model.showUpcomingTitle ? event.safeDisplayTitle() : "Встреча"
                let time = model.showUpcomingTime ? timeText(for: event) + " · " : ""
                // Bound dynamic text, not system menu metrics. Full safe text stays in the tooltip.
                let shortTitle = title.count > 36 ? String(title.prefix(35)) + "…" : title
                let item = addItem(time + shortTitle,
                                   action: safeMeetingLink(for: event) == nil ? nil : #selector(openMeetingLink(_:)),
                                   id: "graf.menu.event")
                item.toolTip = time + title
                item.representedObject = event.eventId
            }
            menu.addItem(.separator())
        }
        addItem("Открыть GRAF", action: #selector(openMeetings), id: "graf.menu.open")
        addItem("Настройки календаря…", action: #selector(openCalendar), id: "graf.menu.calendarSettings")
        if model.appUpdatePresentation.showsSidebarBadge,
           let version = model.appUpdatePresentation.availableVersion {
            menu.addItem(.separator())
            let item = addItem("Обновление GRAF \(version)…", action: #selector(updateApp), id: "graf.menu.update")
            item.isEnabled = model.canCheckForUpdates
        }
    }

    @discardableResult
    private func addItem(_ title: String, action: Selector? = nil, id: String) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
        item.target = self
        item.identifier = NSUserInterfaceItemIdentifier(id)
        item.isEnabled = action != nil
        menu.addItem(item)
        return item
    }

    private func timeText(for event: DesktopCalendarPromptEvent) -> String {
        if event.allDay == true { return "Весь день" }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.timeZone = DesktopUserTimeContext.shared.timeZone
        formatter.dateFormat = "HH:mm"
        return formatter.string(from: event.startsAt)
    }

    private func safeMeetingLink(for event: DesktopCalendarPromptEvent) -> URL? {
        guard event.meetingLinkPresent, let url = event.openMeetingURL,
              url.scheme?.lowercased() == "https", let host = url.host, !host.isEmpty else { return nil }
        return url
    }

    // Redrawn from GRAF's owned phi/equalizer mark for the 22 pt menu-bar grid.
    // Transparent template geometry lets macOS handle light, dark and selected backgrounds.
    static func statusIcon(recordingState: GrafTrayRecordingState = .idle) -> NSImage {
        let image = NSImage(size: NSSize(width: 22, height: 22),
                            flipped: false) { _ in
            NSColor.black.setFill()
            NSColor.black.setStroke()
            let ring = NSBezierPath(ovalIn: NSRect(x: 3, y: 3, width: 16, height: 16))
            ring.lineWidth = 1.8
            ring.stroke()
            for rect in [NSRect(x: 10, y: 0.5, width: 2, height: 3.5),
                         NSRect(x: 10, y: 18, width: 2, height: 3.5),
                         NSRect(x: 7, y: 8, width: 1.8, height: 5),
                         NSRect(x: 10.1, y: 8, width: 1.8, height: 7),
                         NSRect(x: 13.2, y: 8, width: 1.8, height: 4)] {
                NSBezierPath(roundedRect: rect, xRadius: 0.7, yRadius: 0.7).fill()
            }
            if recordingState == .recording || recordingState == .paused || recordingState == .stopping {
                // Keep the status item's width stable when capture starts: a wider
                // item can be displaced by macOS on a crowded menu bar.
                NSGraphicsContext.saveGraphicsState()
                NSGraphicsContext.current?.compositingOperation = .clear
                NSBezierPath(ovalIn: NSRect(x: 14.5, y: 14.5, width: 9, height: 9)).fill()
                NSGraphicsContext.restoreGraphicsState()
                // A microphone pause still captures system audio: keep the recording mark.
                NSBezierPath(ovalIn: NSRect(x: 16, y: 16, width: 6, height: 6)).fill()
            }
            return true
        }
        image.isTemplate = true
        return image
    }

    public func showRecordingState(_ state: GrafTrayRecordingState) {
        guard model.recordingState != state else { return }
        model.recordingState = state
        updateStatusItem()
        if menuIsOpen { menu.cancelTracking() }
    }

    var statusItemLabel: String {
        var parts = ["GRAF"]
        if let label = model.recordingState.label { parts.append(label) }
        if model.appUpdatePresentation.showsSidebarBadge,
           let version = model.appUpdatePresentation.availableVersion {
            parts.append("Доступна версия \(version)")
        }
        return parts.joined(separator: " — ")
    }

    private func updateStatusItem() {
        statusItem.button?.image = Self.statusIcon(recordingState: model.recordingState)
        statusItem.button?.title = ""
        statusItem.button?.toolTip = statusItemLabel
        statusItem.button?.setAccessibilityLabel("Меню \(statusItemLabel)")
    }

    public func showUpdate(_ presentation: AppUpdatePresentation, actionEnabled: Bool) {
        guard model.appUpdatePresentation != presentation || model.canCheckForUpdates != actionEnabled else { return }
        model.appUpdatePresentation = presentation
        model.canCheckForUpdates = actionEnabled
        updateStatusItem()
        if menuIsOpen { menu.cancelTracking() }
    }

    private func refreshNow() {
        Task { [weak self] in
            guard let self else { return }
            let previousEvents = self.model.events
            let previousTitle = self.model.showUpcomingTitle
            let previousTime = self.model.showUpcomingTime
            await self.model.refresh()
            if self.menuIsOpen && (previousEvents != self.model.events ||
                previousTitle != self.model.showUpcomingTitle || previousTime != self.model.showUpcomingTime) {
                self.menu.cancelTracking()
            }
        }
    }

    @objc func startRecording() {
        guard model.recordingState == .idle else { return }
        onStartRecording()
    }

    @objc func stopRecording() {
        guard model.recordingState == .recording || model.recordingState == .paused else { return }
        onStopRecording()
    }

    @objc private func openCalendar() { onOpenCalendar() }
    @objc private func openMeetings() { onOpenMeetings() }

    @objc private func updateApp() {
        guard model.canCheckForUpdates else { return }
        onUpdate()
    }

    @objc private func openMeetingLink(_ sender: NSMenuItem) {
        // Re-resolve after selection: a background refresh/sign-out may have removed the event.
        guard let id = sender.representedObject as? String,
              let event = model.events.first(where: { $0.eventId == id }),
              let url = safeMeetingLink(for: event) else { return }
        NSWorkspace.shared.open(url)
    }
}
