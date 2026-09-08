import AppKit
import QuartzCore
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
        case .paused: "Идёт запись · микрофон выключен"
        case .stopping: "Завершаем запись"
        }
    }
}

/// The menu-bar surface intentionally owns only a short-lived safe projection.
/// Server truth remains authoritative; no calendar event is persisted locally.
@MainActor
public final class CalendarTrayModel {
    public private(set) var events: [DesktopCalendarPromptEvent] = []
    public private(set) var showUpcomingTime = true
    public private(set) var showUpcomingTitle = true
    public var appUpdatePresentation: AppUpdatePresentation = .idle
    public var canCheckForUpdates = false
    public var recordingState: GrafTrayRecordingState = .idle

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
        do {
            let response = try await load()
            guard generation == refreshGeneration else { return }
            showUpcomingTime = response.showUpcomingTime
            showUpcomingTitle = response.showUpcomingTitle
            events = response.events
                .sorted { $0.startsAt == $1.startsAt ? $0.eventId < $1.eventId : $0.startsAt < $1.startsAt }
                .prefix(12)
                .map { $0 }
        } catch {
            guard generation == refreshGeneration else { return }
            events = []
        }
    }
}

@MainActor
public final class CalendarTrayController: NSObject, NSMenuDelegate {
    private let model: CalendarTrayModel
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    let menu = NSMenu(title: "GRAF")
    private var menuIsOpen = false
    private var localMouseMonitor: Any?
    private var globalMouseMonitor: Any?
    var hasMouseMonitors: Bool { localMouseMonitor != nil || globalMouseMonitor != nil }
    private let onOpenSettings: () -> Void
    private let onOpenMeetings: () -> Void
    private let onUpdate: () -> Void
    private let onStartRecording: () -> Void
    private let onStopRecording: () -> Void
    private let onMuteMicrophone: () -> Void
    private let onUnmuteMicrophone: () -> Void
    private let onQuit: () -> Void
    let recordingLight = GrafRecordingLightView(frame: NSRect(x: 0, y: 0, width: 22, height: 22))
    private var refreshTask: Task<Void, Never>?
    private var observers: [(NotificationCenter, NSObjectProtocol)] = []

    public init(
        model: CalendarTrayModel,
        onOpenSettings: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void,
        onStartRecording: @escaping () -> Void,
        onStopRecording: @escaping () -> Void,
        onMuteMicrophone: @escaping () -> Void,
        onUnmuteMicrophone: @escaping () -> Void,
        onQuit: @escaping () -> Void,
        onUpdate: @escaping () -> Void = {}
    ) {
        self.model = model
        self.onOpenSettings = onOpenSettings
        self.onOpenMeetings = onOpenMeetings
        self.onUpdate = onUpdate
        self.onStartRecording = onStartRecording
        self.onStopRecording = onStopRecording
        self.onMuteMicrophone = onMuteMicrophone
        self.onUnmuteMicrophone = onUnmuteMicrophone
        self.onQuit = onQuit
        super.init()
        menu.delegate = self
        menu.autoenablesItems = false
        menu.minimumWidth = 240
    }

    public func start() {
        guard let button = statusItem.button else { return }
        recordingLight.translatesAutoresizingMaskIntoConstraints = false
        recordingLight.wantsLayer = true
        recordingLight.setAccessibilityElement(false)
        button.addSubview(recordingLight)
        NSLayoutConstraint.activate([
            recordingLight.widthAnchor.constraint(equalToConstant: 22),
            recordingLight.heightAnchor.constraint(equalToConstant: 22),
            recordingLight.centerXAnchor.constraint(equalTo: button.centerXAnchor),
            recordingLight.centerYAnchor.constraint(equalTo: button.centerYAnchor)
        ])
        updateStatusItem()
        button.imagePosition = .imageLeading
        button.imageScaling = .scaleProportionallyDown
        statusItem.menu = menu
        button.setAccessibilityRole(.menuButton)

        observers = [
            (NSWorkspace.shared.notificationCenter, NSWorkspace.shared.notificationCenter.addObserver(
                forName: NSWorkspace.accessibilityDisplayOptionsDidChangeNotification, object: nil, queue: .main
            ) { [weak self] _ in
                Task { @MainActor in self?.updateStatusItem() }
            }),
            (NotificationCenter.default, NotificationCenter.default.addObserver(
                forName: NSApplication.didResignActiveNotification, object: nil, queue: .main
            ) { [weak self] _ in
                Task { @MainActor in self?.menu.cancelTracking() }
            }),
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
        // Finish the invoking app menu's tracking before opening the status menu.
        DispatchQueue.main.async { [weak self] in
            guard let self, !self.menuIsOpen else { return }
            if let button = self.statusItem.button, button.window?.isVisible == true {
                button.performClick(nil)
            } else {
                self.menu.popUp(positioning: nil, at: NSEvent.mouseLocation, in: nil)
            }
        }
    }

    public func menuNeedsUpdate(_ menu: NSMenu) {
        rebuildMenu()
    }

    public func menuWillOpen(_ menu: NSMenu) {
        guard !menuIsOpen else { return }
        menuIsOpen = true
        localMouseMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .otherMouseDown]) { [weak self] event in
            if Self.isOutsideMenuWindow(event.window) { self?.menu.cancelTracking() }
            return event
        }
        globalMouseMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .otherMouseDown]) { [weak self] _ in
            self?.menu.cancelTracking()
        }
        refreshNow()
    }

    public func menuDidClose(_ menu: NSMenu) {
        menuIsOpen = false
        if let localMouseMonitor { NSEvent.removeMonitor(localMouseMonitor) }
        if let globalMouseMonitor { NSEvent.removeMonitor(globalMouseMonitor) }
        localMouseMonitor = nil
        globalMouseMonitor = nil
    }

    static func isOutsideMenuWindow(_ window: NSWindow?) -> Bool {
        guard let window else { return false }
        return window.level.rawValue < NSWindow.Level.mainMenu.rawValue
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
            let muted = model.recordingState == .paused
            let item = addItem(muted ? SystemAudioStatusLabels.resumeButtonTitle : "Mute микрофона",
                               action: muted ? #selector(unmuteMicrophone) : #selector(muteMicrophone),
                               id: muted ? "graf.menu.unmute" : "graf.menu.mute")
            item.toolTip = muted ? SystemAudioStatusLabels.resumeButtonAccessibilityLabel
                                : SystemAudioStatusLabels.pauseButtonAccessibilityLabel
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
        addItem("Настройки…", action: #selector(openSettings), id: "graf.menu.settings")
        if model.appUpdatePresentation.showsSidebarBadge,
           let version = model.appUpdatePresentation.availableVersion {
            menu.addItem(.separator())
            let item = addItem("Обновление GRAF \(version)…", action: #selector(updateApp), id: "graf.menu.update")
            item.isEnabled = model.canCheckForUpdates
        }
        menu.addItem(.separator())
        addItem("Выйти из GRAF", action: #selector(quitApp), id: "graf.menu.quit")
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
                         NSRect(x: 10, y: 18, width: 2, height: 3.5)] {
                NSBezierPath(roundedRect: rect, xRadius: 0.7, yRadius: 0.7).fill()
            }
            let bars = recordingState == .paused
                ? [NSRect(x: 7, y: 10.5, width: 8, height: 1.8)]
                : [NSRect(x: 7, y: 8, width: 1.8, height: 5),
                   NSRect(x: 10.1, y: 8, width: 1.8, height: 7),
                   NSRect(x: 13.2, y: 8, width: 1.8, height: 4)]
            for rect in bars {
                NSBezierPath(roundedRect: rect, xRadius: 0.7, yRadius: 0.7).fill()
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
        recordingLight.update(state: model.recordingState,
                              reduceMotion: NSWorkspace.shared.accessibilityDisplayShouldReduceMotion)
        statusItem.button?.title = ""
        statusItem.button?.toolTip = statusItemLabel
        statusItem.button?.setAccessibilityLabel("Меню \(statusItemLabel)")
    }

    public func showUpdate(_ presentation: AppUpdatePresentation, actionEnabled: Bool) {
        guard model.appUpdatePresentation != presentation || model.canCheckForUpdates != actionEnabled else { return }
        model.appUpdatePresentation = presentation
        model.canCheckForUpdates = actionEnabled
        updateStatusItem()
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

    @objc func muteMicrophone() {
        guard model.recordingState == .recording else { return }
        onMuteMicrophone()
    }

    @objc func unmuteMicrophone() {
        guard model.recordingState == .paused else { return }
        onUnmuteMicrophone()
    }

    @objc private func openSettings() { onOpenSettings() }
    @objc private func quitApp() { onQuit() }
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

// A separate drawing layer keeps the logo a native template while preserving the red light.
// It occupies the same 22 pt canvas and never intercepts the status button's mouse events.
@MainActor
final class GrafRecordingLightView: NSView {
    override func hitTest(_ point: NSPoint) -> NSView? { nil }

    override func draw(_ dirtyRect: NSRect) {
        NSColor.systemRed.setFill()
        NSBezierPath(ovalIn: NSRect(x: 9.4, y: 4.4, width: 3.2, height: 3.2)).fill()
    }

    func update(state: GrafTrayRecordingState, reduceMotion: Bool) {
        isHidden = state == .idle || state == .starting
        let animate = !reduceMotion && (state == .recording || state == .paused)
        if animate {
            guard layer?.animation(forKey: "recordingPulse") == nil else { return }
            let pulse = CABasicAnimation(keyPath: "opacity")
            pulse.fromValue = 1
            pulse.toValue = 0.55
            pulse.duration = 0.9
            pulse.autoreverses = true
            pulse.repeatCount = .infinity
            pulse.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            layer?.add(pulse, forKey: "recordingPulse")
        } else {
            layer?.removeAnimation(forKey: "recordingPulse")
        }
    }
}
