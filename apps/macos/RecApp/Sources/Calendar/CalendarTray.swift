import AppKit
import Combine
import SwiftUI
import TwoBrainRecShared

public enum GrafTrayRecordingState: Equatable, Sendable {
    case idle, recording, paused, stopping

    public static func resolve(sessionState: CaptureSessionState?, writerActive: Bool, stopping: Bool) -> Self {
        if stopping { return .stopping }
        guard writerActive else { return .idle }
        return sessionState == .paused ? .paused : .recording
    }

    var label: String? {
        switch self {
        case .idle: nil
        case .recording: "Идёт запись"
        case .paused: "Запись на паузе"
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

    var preferredPanelHeight: CGFloat {
        let content: CGFloat = events.isEmpty ? 64 : 420
        return content + (appUpdatePresentation.showsSidebarBadge ? 144 : 0)
            + (recordingState == .idle ? 0 : 32)
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
public struct CalendarTrayView: View {
    @ObservedObject private var userTimeContext = DesktopUserTimeContext.shared
    @ObservedObject private var model: CalendarTrayModel
    private let onOpenCalendar: () -> Void
    private let onOpenMeetings: () -> Void
    private let onOpenMeetingLink: (URL) -> Void
    private let onUpdate: () -> Void
    private let panelSize: NSSize

    public init(
        model: CalendarTrayModel,
        onOpenCalendar: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void,
        onOpenMeetingLink: @escaping (URL) -> Void,
        onUpdate: @escaping () -> Void = {},
        panelSize: NSSize = NSSize(width: 344, height: 420)
    ) {
        self.model = model
        self.onOpenCalendar = onOpenCalendar
        self.onOpenMeetings = onOpenMeetings
        self.onOpenMeetingLink = onOpenMeetingLink
        self.onUpdate = onUpdate
        self.panelSize = panelSize
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            AppUpdateNotice(presentation: model.appUpdatePresentation,
                            isActionEnabled: model.canCheckForUpdates, onUpdate: onUpdate)
            if !model.events.isEmpty {
                header
                Divider()
                ScrollView(.vertical, showsIndicators: true) {
                    VStack(alignment: .leading, spacing: 0) {
                        ForEach(model.events) { event in
                            eventRow(event)
                        }
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                Divider()
            }
            if let label = model.recordingState.label {
                Label(label, systemImage: model.recordingState == .paused ? "pause.fill" : "record.circle")
                    .font(.caption)
                    .padding(.horizontal, 16)
                    .frame(height: 32)
                    .accessibilityIdentifier("graf.menu.recordingState")
            }
            footer
        }
        .frame(width: panelSize.width, height: panelSize.height)
        .background(.regularMaterial)
        .tint(DesktopMeetingShellChrome.shellAccentColor)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Меню GRAF")
    }

    private var header: some View {
        HStack(spacing: 10) {
            Image(systemName: "calendar.badge.clock")
                .font(.title3)
                .foregroundStyle(.tint)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 2) {
                Text("Ближайшие встречи")
                    .font(.headline)
                Text("На ближайшие 24 часа")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(16)
    }

    private func eventRow(_ event: DesktopCalendarPromptEvent) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .top, spacing: 10) {
                Circle()
                    .fill(event.overlaps(Date()) ? DesktopMeetingShellChrome.shellAccentColor : Color.secondary.opacity(0.45))
                    .frame(width: 8, height: 8)
                    .padding(.top, 5)
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 3) {
                    Text(model.showUpcomingTitle ? event.safeDisplayTitle() : "Название скрыто настройкой")
                        .font(.body.weight(.medium))
                        .lineLimit(2)
                    if model.showUpcomingTime {
                        Text(timeText(for: event))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if event.meetingLinkPresent {
                        Text("Есть ссылка на встречу")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer(minLength: 0)
            }
            if let link = safeMeetingLink(for: event) {
                Button("Открыть встречу") {
                    onOpenMeetingLink(link)
                }
                .buttonStyle(.link)
                .font(.caption)
                .accessibilityLabel("Открыть встречу")
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(eventAccessibilityLabel(event))
    }

    private var footer: some View {
        HStack {
            Button("Открыть GRAF", action: onOpenMeetings)
                .buttonStyle(.borderedProminent)
                .tint(Color(red: 98.0 / 255, green: 72.0 / 255, blue: 213.0 / 255))
                .keyboardShortcut(.defaultAction)
            Spacer()
            Button("Настройки календаря", action: onOpenCalendar)
                .buttonStyle(.link)
                .foregroundStyle(.primary)
        }
        .font(.caption)
        .padding(16)
    }

    private func timeText(for event: DesktopCalendarPromptEvent) -> String {
        if event.allDay == true {
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "ru_RU")
            formatter.dateFormat = "dd.MM.yyyy"
            formatter.timeZone = TimeZone(secondsFromGMT: 0)
            return "\(formatter.string(from: event.startsAt)) · Весь день"
        }
        return UserTime.interval(start: event.startsAt, end: event.endsAt, timeZone: userTimeContext.timeZone)
    }

    private func safeMeetingLink(for event: DesktopCalendarPromptEvent) -> URL? {
        guard event.meetingLinkPresent,
              let url = event.openMeetingURL,
              let scheme = url.scheme?.lowercased(),
              scheme == "https",
              url.host != nil else {
            return nil
        }
        return url
    }

    private func eventAccessibilityLabel(_ event: DesktopCalendarPromptEvent) -> String {
        let title = model.showUpcomingTitle ? event.safeDisplayTitle() : "Название скрыто настройкой"
        return model.showUpcomingTime ? "\(title), \(timeText(for: event))" : title
    }
}

@MainActor
public final class CalendarTrayController: NSObject, NSPopoverDelegate {
    private let model: CalendarTrayModel
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let popover = NSPopover()
    private var localMouseMonitor: Any?
    private var globalMouseMonitor: Any?
    private let onOpenCalendar: () -> Void
    private let onOpenMeetings: () -> Void
    private let onUpdate: () -> Void
    private var refreshTask: Task<Void, Never>?
    private var observers: [(NotificationCenter, NSObjectProtocol)] = []

    public init(
        model: CalendarTrayModel,
        onOpenCalendar: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void,
        onUpdate: @escaping () -> Void = {}
    ) {
        self.model = model
        self.onOpenCalendar = onOpenCalendar
        self.onOpenMeetings = onOpenMeetings
        self.onUpdate = onUpdate
        super.init()
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
        button.target = self
        button.action = #selector(togglePopover(_:))
        button.setAccessibilityRole(.button)

        popover.delegate = self
        popover.behavior = .transient
        popover.animates = false

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

    public func showPopover() {
        guard !popover.isShown else { return }
        guard let button = statusItem.button,
              let screen = button.window?.screen ?? NSScreen.main else { return }
        let size = Self.panelSize(in: screen.visibleFrame, preferredHeight: model.preferredPanelHeight)
        let rootView = makeRootView(panelSize: size)
        if let hosting = popover.contentViewController as? NSHostingController<CalendarTrayView> {
            hosting.sizingOptions = []
            hosting.rootView = rootView
        } else {
            let hosting = NSHostingController(rootView: rootView)
            hosting.sizingOptions = []
            popover.contentViewController = hosting
        }
        popover.appearance = NSApplication.shared.appearance
        popover.contentSize = size
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        popover.contentViewController?.view.window?.makeKey()
        localMouseMonitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .otherMouseDown]) { [weak self] event in
            if let self, Self.shouldDismissClick(in: event.window,
                popoverWindow: self.popover.contentViewController?.view.window,
                statusItemWindow: self.statusItem.button?.window) {
                self.popover.performClose(nil)
            }
            return event
        }
        globalMouseMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown, .otherMouseDown]) { [weak self] _ in
            self?.popover.performClose(nil)
        }
        refreshNow()
    }

    static func shouldDismissClick(in window: NSWindow?, popoverWindow: NSWindow?, statusItemWindow: NSWindow?) -> Bool {
        window == nil || (window !== popoverWindow && window !== statusItemWindow)
    }

    public func popoverDidClose(_ notification: Notification) {
        if let localMouseMonitor { NSEvent.removeMonitor(localMouseMonitor) }
        if let globalMouseMonitor { NSEvent.removeMonitor(globalMouseMonitor) }
        localMouseMonitor = nil
        globalMouseMonitor = nil
    }

    // Redrawn from GRAF's owned phi/equalizer mark for the 22 pt menu-bar grid.
    // Transparent template geometry lets macOS handle light, dark and selected backgrounds.
    static func statusIcon(recordingState: GrafTrayRecordingState = .idle) -> NSImage {
        let image = NSImage(size: NSSize(width: recordingState == .idle ? 22 : 30, height: 22),
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
            if recordingState == .paused {
                for x in [24.0, 28.0] {
                    NSBezierPath(roundedRect: NSRect(x: x, y: 8, width: 2, height: 6),
                                 xRadius: 0.5, yRadius: 0.5).fill()
                }
            } else if recordingState != .idle {
                NSBezierPath(ovalIn: NSRect(x: 24, y: 8, width: 6, height: 6)).fill()
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
        updatePopoverLayout()
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
        statusItem.button?.title = model.appUpdatePresentation.showsSidebarBadge ? "↑" : ""
        statusItem.button?.toolTip = statusItemLabel
        statusItem.button?.setAccessibilityLabel("Меню \(statusItemLabel)")
    }

    public static func panelSize(in visibleFrame: NSRect, preferredHeight: CGFloat = 420) -> NSSize {
        NSSize(width: max(1, min(344, visibleFrame.width - 24)),
               height: max(1, min(preferredHeight, visibleFrame.height - 24)))
    }

    public func showUpdate(_ presentation: AppUpdatePresentation, actionEnabled: Bool) {
        model.appUpdatePresentation = presentation
        model.canCheckForUpdates = actionEnabled
        updateStatusItem()
        updatePopoverLayout()
    }

    @objc private func togglePopover(_ sender: Any?) {
        guard statusItem.button != nil else { return }
        if popover.isShown {
            popover.performClose(sender)
        } else {
            showPopover()
        }
    }

    private func refreshNow() {
        Task { [weak self] in
            guard let self else { return }
            await self.model.refresh()
            self.updatePopoverLayout()
        }
    }

    private func makeRootView(panelSize: NSSize) -> CalendarTrayView {
        CalendarTrayView(
            model: model,
            onOpenCalendar: { [weak self] in self?.openCalendar() },
            onOpenMeetings: { [weak self] in self?.openMeetings() },
            onOpenMeetingLink: { [weak self] url in self?.openMeetingLink(url) },
            onUpdate: { [weak self] in
                self?.popover.performClose(nil)
                self?.onUpdate()
            },
            panelSize: panelSize
        )
    }

    private func updatePopoverLayout() {
        guard popover.isShown,
              let button = statusItem.button,
              let screen = button.window?.screen ?? NSScreen.main,
              let hosting = popover.contentViewController as? NSHostingController<CalendarTrayView> else {
            return
        }
        let size = Self.panelSize(in: screen.visibleFrame, preferredHeight: model.preferredPanelHeight)
        hosting.sizingOptions = []
        hosting.rootView = makeRootView(panelSize: size)
        popover.appearance = NSApplication.shared.appearance
        popover.contentSize = size
    }

    private func openCalendar() {
        popover.performClose(nil)
        onOpenCalendar()
    }

    private func openMeetings() {
        popover.performClose(nil)
        onOpenMeetings()
    }

    private func openMeetingLink(_ url: URL) {
        guard url.scheme?.lowercased() == "https", url.host != nil else { return }
        popover.performClose(nil)
        NSWorkspace.shared.open(url)
    }
}
