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

public struct CalendarTrayView: View {
    @ObservedObject private var model: CalendarTrayModel
    private let onOpenCalendar: () -> Void
    private let onOpenMeetings: () -> Void
    private let onOpenMeetingLink: (URL) -> Void
    private let onRefresh: () -> Void

    public init(
        model: CalendarTrayModel,
        onOpenCalendar: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void,
        onOpenMeetingLink: @escaping (URL) -> Void,
        onRefresh: @escaping () -> Void
    ) {
        self.model = model
        self.onOpenCalendar = onOpenCalendar
        self.onOpenMeetings = onOpenMeetings
        self.onOpenMeetingLink = onOpenMeetingLink
        self.onRefresh = onRefresh
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            Divider()
            content
            Divider()
            footer
        }
        .frame(width: 360)
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
            .help("Обновить календарь")
            .accessibilityLabel("Обновить календарь")
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
        VStack(alignment: .leading, spacing: 8) {
            Text("Календарь используется только для контекста. GRAF не изменяет события и не начинает запись сам.")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
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
        let start = event.startsAt.formatted(date: .abbreviated, time: .shortened)
        let endDateStyle: Date.FormatStyle.DateStyle = Calendar.current.isDate(
            event.startsAt,
            inSameDayAs: event.endsAt
        ) ? .omitted : .abbreviated
        let end = event.endsAt.formatted(date: endDateStyle, time: .shortened)
        return "\(start) — \(end)"
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
public final class CalendarTrayController: NSObject {
    private let model: CalendarTrayModel
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let popover = NSPopover()
    private let onOpenCalendar: () -> Void
    private let onOpenMeetings: () -> Void
    private var refreshTask: Task<Void, Never>?
    private var observers: [(NotificationCenter, NSObjectProtocol)] = []

    public init(
        model: CalendarTrayModel,
        onOpenCalendar: @escaping () -> Void,
        onOpenMeetings: @escaping () -> Void
    ) {
        self.model = model
        self.onOpenCalendar = onOpenCalendar
        self.onOpenMeetings = onOpenMeetings
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

        popover.behavior = .transient
        popover.animates = true
        popover.contentViewController = NSHostingController(
            rootView: CalendarTrayView(
                model: model,
                onOpenCalendar: { [weak self] in self?.openCalendar() },
                onOpenMeetings: { [weak self] in self?.openMeetings() },
                onOpenMeetingLink: { [weak self] url in self?.openMeetingLink(url) },
                onRefresh: { [weak self] in self?.refreshNow() }
            )
        )

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
                try? await Task.sleep(for: .seconds(60))
            }
        }
        refreshNow()
    }

    public func showPopover() {
        guard !popover.isShown else { return }
        guard let button = statusItem.button else { return }
        popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
        popover.contentViewController?.view.window?.makeKey()
        refreshNow()
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
