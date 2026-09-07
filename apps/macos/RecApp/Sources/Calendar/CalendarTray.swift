import AppKit
import Combine
import SwiftUI
import TwoBrainRecShared

public enum CalendarTrayState: Equatable, Sendable {
    case idle
    case loading
    case loaded
    case empty
    case needsSignIn
    case unavailable
    case stale
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
        if events.isEmpty {
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
            if error.failureCategory == .authSession {
                state = .needsSignIn
            } else if events.isEmpty {
                state = .unavailable
            } else {
                state = .stale
            }
        } catch {
            guard generation == refreshGeneration else { return }
            state = events.isEmpty ? .unavailable : .stale
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
    private let onRefresh: () -> Void
    private let onUpdate: () -> Void
    private let panelSize: NSSize

    public init(
        model: CalendarTrayModel,
        onOpenCalendar: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void,
        onOpenMeetingLink: @escaping (URL) -> Void,
        onRefresh: @escaping () -> Void,
        onUpdate: @escaping () -> Void = {},
        panelSize: NSSize = NSSize(width: 344, height: 420)
    ) {
        self.model = model
        self.onOpenCalendar = onOpenCalendar
        self.onOpenMeetings = onOpenMeetings
        self.onOpenMeetingLink = onOpenMeetingLink
        self.onRefresh = onRefresh
        self.onUpdate = onUpdate
        self.panelSize = panelSize
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            AppUpdateNotice(presentation: model.appUpdatePresentation,
                            isActionEnabled: model.canCheckForUpdates, onUpdate: onUpdate)
            header
            Divider()
            if shouldRenderContent {
                ScrollView(.vertical, showsIndicators: true) {
                    content
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                Divider()
            }
            footer
        }
        .frame(width: panelSize.width, height: panelSize.height)
        .background(.regularMaterial)
        .tint(DesktopMeetingShellChrome.shellAccentColor)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Ближайшие встречи GRAF")
    }

    private var shouldRenderContent: Bool {
        if !model.events.isEmpty {
            return true
        }
        switch model.state {
        case .loading, .needsSignIn, .unavailable:
            return true
        case .idle, .loaded, .empty, .stale:
            return false
        }
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
                Text(statusText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(action: onRefresh) {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(.borderless)
            .help("Обновить список. Google и Яндекс синхронизируются автоматически каждую минуту.")
            .accessibilityLabel("Обновить список")
            .disabled(model.state == .loading)
        }
        .padding(16)
    }

    @ViewBuilder
    private var content: some View {
        switch model.state {
        case .loading where model.events.isEmpty:
            stateRow("Загружаем календарь…", systemImage: "arrow.triangle.2.circlepath")
        case .needsSignIn:
            stateRow("Войдите в GRAF, чтобы увидеть встречи", systemImage: "person.crop.circle.badge.exclamationmark")
        case .unavailable:
            stateRow("Календарь временно недоступен", systemImage: "exclamationmark.triangle")
        case .empty:
            EmptyView()
        default:
            if model.events.isEmpty {
                EmptyView()
            } else {
                VStack(alignment: .leading, spacing: 0) {
                    if model.state == .stale {
                        Label("Показаны последние данные", systemImage: "clock.arrow.circlepath")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .padding(.horizontal, 16)
                            .padding(.top, 12)
                    }
                    ForEach(model.events) { event in
                        eventRow(event)
                    }
                }
            }
        }
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

    private func stateRow(_ title: String, systemImage: String) -> some View {
        Label {
            Text(title)
                .fixedSize(horizontal: false, vertical: true)
        } icon: {
            Image(systemName: systemImage)
                .foregroundStyle(.secondary)
        }
        .font(.callout)
        .foregroundStyle(.secondary)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(20)
    }

    private var footer: some View {
        HStack {
            Button("Открыть GRAF", action: onOpenMeetings)
                .buttonStyle(.borderedProminent)
                .foregroundStyle(.black)
                .keyboardShortcut(.defaultAction)
            Spacer()
            Button("Настройки календаря", action: onOpenCalendar)
                .buttonStyle(.link)
                .foregroundStyle(.primary)
        }
        .font(.caption)
        .padding(16)
    }

    private var statusText: String {
        switch model.state {
        case .loading: return "Обновляем…"
        case .needsSignIn: return "Нужен вход"
        case .unavailable: return "Недоступен"
        case .stale: return "Последнее обновление не удалось"
        case .empty: return "На ближайшие 24 часа"
        default: return "На ближайшие 24 часа"
        }
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
        button.image = NSImage(systemSymbolName: "calendar.badge.clock", accessibilityDescription: "")
        button.image?.isTemplate = true
        button.toolTip = "Ближайшие встречи GRAF"
        button.target = self
        button.action = #selector(togglePopover(_:))
        button.setAccessibilityLabel("Ближайшие встречи GRAF")
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
        let size = Self.panelSize(in: screen.visibleFrame, compact: isEmptyState)
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

    public static func panelSize(in visibleFrame: NSRect, compact: Bool = false) -> NSSize {
        let height = max(1, min(420, visibleFrame.height - 24))
        return NSSize(width: max(1, min(344, visibleFrame.width - 24)),
                      height: compact ? min(height, 160) : height)
    }

    public func showUpdate(_ presentation: AppUpdatePresentation, actionEnabled: Bool) {
        model.appUpdatePresentation = presentation
        model.canCheckForUpdates = actionEnabled
        let version = presentation.showsSidebarBadge ? presentation.availableVersion : nil
        let label = version.map { "GRAF — доступна версия \($0). Ближайшие встречи." }
            ?? "Ближайшие встречи GRAF"
        statusItem.button?.image = NSImage(
            systemSymbolName: version == nil ? "calendar.badge.clock" : "arrow.down.circle.fill",
            accessibilityDescription: nil
        )
        statusItem.button?.image?.isTemplate = true
        statusItem.button?.toolTip = label
        statusItem.button?.setAccessibilityLabel(label)
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

    private var isEmptyState: Bool {
        model.state == .empty && model.events.isEmpty
    }

    private func makeRootView(panelSize: NSSize) -> CalendarTrayView {
        CalendarTrayView(
            model: model,
            onOpenCalendar: { [weak self] in self?.openCalendar() },
            onOpenMeetings: { [weak self] in self?.openMeetings() },
            onOpenMeetingLink: { [weak self] url in self?.openMeetingLink(url) },
            onRefresh: { [weak self] in self?.refreshNow() },
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
        let size = Self.panelSize(in: screen.visibleFrame, compact: isEmptyState)
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
