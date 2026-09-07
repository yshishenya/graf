import AppKit
import Combine
import OSLog
import SwiftUI
import TwoBrainRecShared

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

    private let load: @Sendable () async throws -> DesktopCalendarPromptResponse
    private var refreshGeneration = 0
    public var onAuthInvalidated: (() -> Void)?
    public var onProjection: ((DesktopCalendarPromptResponse?) -> Void)?
    public func invalidate() {
        refreshGeneration += 1
        events = []
        lastUpdatedAt = nil
        state = .needsSignIn
        onProjection?(nil)
        onAuthInvalidated?()
    }

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
            onProjection?(response)
        } catch let error as DesktopUploadClientError {
            guard generation == refreshGeneration else { return }
            events = []
            onProjection?(nil)
            if error.failureCategory == .authSession {
                invalidate()
            } else {
                state = .unavailable
            }
        } catch {
            guard generation == refreshGeneration else { return }
            events = []
            onProjection?(nil)
            state = .unavailable
        }
    }
}

@MainActor
public struct CalendarTrayView: View {
    @ObservedObject private var userTimeContext = DesktopUserTimeContext.shared
    @ObservedObject private var model: CalendarTrayModel
    @ObservedObject private var controls = DesktopControlModel.shared
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
            DesktopControlPanel(model: controls)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    AppUpdateNotice(presentation: model.appUpdatePresentation,
                                    isActionEnabled: model.canCheckForUpdates, onUpdate: onUpdate)
                    DesktopControlPanel(model: controls).details
                    Divider()
                    header
                    content
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
            Divider()
            footer
        }
        .frame(width: panelSize.width, height: panelSize.height)
        .background(.regularMaterial)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Ближайшие встречи GRAF")
    }

    private var header: some View {
        HStack(spacing: 10) {
            Image(systemName: "calendar.badge.clock")
                .font(.title3)
                .foregroundStyle(.tint)
                .accessibilityHidden(true)
            Text("Ближайшие встречи").font(.subheadline.weight(.semibold))
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
            stateRow("Нет ближайших встреч", systemImage: "calendar")
        default:
            if model.events.isEmpty {
                stateRow("Нет ближайших встреч", systemImage: "calendar")
            } else {
                VStack(alignment: .leading, spacing: 0) {
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
                    .fill(event.overlaps(Date()) ? Color.accentColor : Color.secondary.opacity(0.45))
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
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Button("Открыть GRAF", action: onOpenMeetings)
                    .keyboardShortcut(.defaultAction)
                Spacer()
                Button("Настройки календаря", action: onOpenCalendar)
                    .buttonStyle(.link)
            }
            .font(.caption)
        }
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
    private var presentationStartedAt: TimeInterval?
    private let onOpenCalendar: () -> Void
    private let onOpenMeetings: () -> Void
    private let onUpdate: () -> Void
    private var captureObservation: AnyCancellable?
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
        DesktopNotificationPresenter.shared.onOpenCalendar = { [weak self] in self?.showPopover() }
        model.onAuthInvalidated = { DesktopNotificationPresenter.shared.invalidate() }
        model.onProjection = { response in
            if let response { DesktopNotificationPresenter.shared.updateCalendar(response) }
            else { DesktopNotificationPresenter.shared.clearCalendar() }
        }
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
        captureObservation = DesktopControlModel.shared.$snapshot.sink { [weak self] snapshot in
            self?.refreshStatusButton(snapshot)
        }

        popover.delegate = self
        popover.behavior = .transient
        popover.animates = true

        observers = [
            (NotificationCenter.default, NotificationCenter.default.addObserver(
                forName: NSApplication.didChangeScreenParametersNotification, object: nil, queue: .main
            ) { [weak self] _ in
                Task { @MainActor in if self?.popover.isShown == true { self?.showPopover() } }
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
                Task { @MainActor in self?.model.invalidate(); self?.refreshNow() }
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
        guard let button = statusItem.button, let screen = button.window?.screen ?? NSScreen.main else { return }
        if !popover.isShown { presentationStartedAt = ProcessInfo.processInfo.systemUptime }
        let size = Self.panelSize(in: screen.visibleFrame)
        let rootView = CalendarTrayView(model: model,
            onOpenCalendar: { [weak self] in self?.openCalendar() },
            onOpenMeetings: { [weak self] in self?.openMeetings() },
            onOpenMeetingLink: { [weak self] url in self?.openMeetingLink(url) },
            onRefresh: { [weak self] in self?.refreshNow() },
            onUpdate: { [weak self] in
                self?.popover.performClose(nil)
                self?.onUpdate()
            }, panelSize: size)
        if let hosting = popover.contentViewController as? NSHostingController<CalendarTrayView> {
            hosting.rootView = rootView
        } else {
            let hosting = NSHostingController(rootView: rootView)
            hosting.sizingOptions = []
            popover.contentViewController = hosting
        }
        popover.contentSize = size
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        popover.contentViewController?.view.window?.makeKey()
        refreshNow()
    }

    public func popoverDidShow(_ notification: Notification) {
        guard let started = presentationStartedAt else { return }
        presentationStartedAt = nil
        // Dev-only, metadata-only evidence from the native visible lifecycle event.
        guard Bundle.main.bundleIdentifier == "pro.2brain.graf.dev" else { return }
        let milliseconds = (ProcessInfo.processInfo.systemUptime - started) * 1_000
        Logger(subsystem: "pro.2brain.graf.dev", category: "panel-performance")
            .notice("presentation_ms=\(milliseconds, privacy: .public)")
    }

    public func showUpdate(_ presentation: AppUpdatePresentation, actionEnabled: Bool) {
        model.appUpdatePresentation = presentation
        model.canCheckForUpdates = actionEnabled
        refreshStatusButton(DesktopControlModel.shared.snapshot)
    }

    private func refreshStatusButton(_ snapshot: DesktopControlSnapshot) {
        guard let button = statusItem.button else { return }
        let version = model.appUpdatePresentation.showsSidebarBadge ? model.appUpdatePresentation.availableVersion : nil
        let label = snapshot.session.map { CaptureStatusItem.statusLabel(for: $0) }
            ?? (snapshot.startAvailable ? "Готово к записи" : "Проверьте доступ к записи")
        let updateLabel = version.map { ". Доступна версия \($0)" } ?? ""
        button.image = NSImage(systemSymbolName: snapshot.active
            ? (snapshot.session?.state == .paused ? "pause.circle.fill" : "record.circle")
            : (version == nil ? "waveform" : "arrow.down.circle.fill"), accessibilityDescription: nil)
        button.image?.isTemplate = true
        button.title = snapshot.active ? (snapshot.session?.state == .paused ? " Микрофон на паузе" : " Запись") : ""
        button.toolTip = "GRAF · " + label + updateLabel
        button.setAccessibilityLabel("GRAF. " + label + updateLabel + ". Открыть управление")
    }

    public static func panelSize(in visibleFrame: NSRect) -> NSSize {
        NSSize(width: max(1, min(344, visibleFrame.width - 24)),
               height: max(1, min(420, visibleFrame.height - 24)))
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
            await self?.model.refresh()
        }
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
