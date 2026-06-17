import AppKit
import SwiftUI
import TwoBrainRecShared

public enum DesktopMeetingShellChrome {
    public static let sidebarWidth: CGFloat = 152
    public static let collapsedInspectorWidth: CGFloat = 56
    public static let expandedInspectorWidth: CGFloat = 300
    public static let shellBackgroundHex = "#191a1c"
    public static let shellSidebarHex = "#202224"
    public static let shellRailHex = "#202224"
    public static let shellSurfaceHex = "#242629"
    public static let webEmbeddedBackgroundHex = shellBackgroundHex
    public static let shellBackgroundColor = Color(red: 0.098, green: 0.102, blue: 0.110)
    public static let shellSidebarColor = Color(red: 0.125, green: 0.133, blue: 0.141)
    public static let shellRailColor = Color(red: 0.125, green: 0.133, blue: 0.141)
    public static let shellSurfaceColor = Color(red: 0.141, green: 0.149, blue: 0.161)
    public static let shellStrokeColor = Color.white.opacity(0.08)
    public static let webEmbeddedBackgroundNSColor = NSColor(
        srgbRed: 0.098,
        green: 0.102,
        blue: 0.110,
        alpha: 1
    )
    public static let inspectorToggleHitSize: CGFloat = 44
    public static let inspectorToggleCornerRadius: CGFloat = 10
    public static let inspectorToggleCollapsedSymbol = "chevron.left.2"
    public static let inspectorToggleExpandedSymbol = "chevron.right.2"
    public static let inspectorToggleCollapsedLabel = "Показать панель управления"
    public static let inspectorToggleExpandedLabel = "Скрыть панель управления"
    public static let profileMenuLabels = [
        "Внешний вид",
        "Настройки",
        "Диагностика",
        "Ресурсы",
        "Связаться с поддержкой",
        "Оставить отзыв",
        "Сообщество Slack",
        "Выйти",
        "Закрыть 2brain Rec полностью"
    ]
}

public struct DesktopMeetingShellView<CaptureControls: View, MeetingsWorkspace: View, DiagnosticsContent: View>: View {
    private let session: CaptureSession?
    private let uploadQueueItems: [DesktopUploadQueueItem]
    private let pendingUploadCount: Int
    private let cabinetConfigured: Bool
    private let statusSummary: String
    private let lastEventSummary: String
    private let isChecking: Bool
    private let onRefresh: () -> Void
    private let onRunCheck: () -> Void
    private let captureControls: CaptureControls
    private let meetingsWorkspace: MeetingsWorkspace
    private let diagnosticsContent: DiagnosticsContent
    @State private var inspectorExpanded = false

    public init(
        session: CaptureSession?,
        uploadQueueItems: [DesktopUploadQueueItem],
        pendingUploadCount: Int,
        cabinetConfigured: Bool,
        statusSummary: String,
        lastEventSummary: String,
        isChecking: Bool,
        onRefresh: @escaping () -> Void,
        onRunCheck: @escaping () -> Void,
        @ViewBuilder captureControls: () -> CaptureControls,
        @ViewBuilder meetingsWorkspace: () -> MeetingsWorkspace,
        @ViewBuilder diagnosticsContent: () -> DiagnosticsContent
    ) {
        self.session = session
        self.uploadQueueItems = uploadQueueItems
        self.pendingUploadCount = pendingUploadCount
        self.cabinetConfigured = cabinetConfigured
        self.statusSummary = statusSummary
        self.lastEventSummary = lastEventSummary
        self.isChecking = isChecking
        self.onRefresh = onRefresh
        self.onRunCheck = onRunCheck
        self.captureControls = captureControls()
        self.meetingsWorkspace = meetingsWorkspace()
        self.diagnosticsContent = diagnosticsContent()
    }

    public var body: some View {
        HStack(spacing: 0) {
            sidebar
                .frame(width: DesktopMeetingShellChrome.sidebarWidth)
            Divider()
            VStack(spacing: 0) {
                topBar
                Divider()
                HStack(spacing: 0) {
                    meetingsSurface
                    Divider()
                    inspectorContainer
                }
            }
        }
        .background(DesktopMeetingShellChrome.shellBackgroundColor)
        .animation(.easeInOut(duration: 0.18), value: expandedInspectorVisible)
        .accessibilityIdentifier("desktop-meeting-shell")
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 10) {
                ZStack {
                    RoundedRectangle(cornerRadius: 7)
                        .fill(.purple.opacity(0.18))
                    Image(systemName: "waveform.badge.mic")
                        .foregroundStyle(.purple)
                }
                .frame(width: 34, height: 34)
                VStack(alignment: .leading, spacing: 2) {
                    Text("2brain Rec")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Text(cabinetConfigured ? "Рабочее место" : "Локальный режим")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.top, 6)

            VStack(alignment: .leading, spacing: 4) {
                navRow("Поиск", "magnifyingglass", selected: false)
                navRow("Мои встречи", "rectangle.stack", selected: true)
                navRow("Общие", "person.2", selected: false)
                navRow("Действия", "checkmark.circle", selected: false, badge: pendingUploadCount)
                navRow("Активность", "waveform.path.ecg", selected: false)
                navRow("Настройки", "gearshape", selected: false)
            }

            Spacer()

            profileMenu
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(DesktopMeetingShellChrome.shellSidebarColor)
    }

    private func navRow(_ title: String, _ icon: String, selected: Bool, badge: Int = 0) -> some View {
        HStack(spacing: 9) {
            Image(systemName: icon)
                .frame(width: 17)
            Text(title)
                .lineLimit(1)
            Spacer(minLength: 6)
            if badge > 0 {
                Text("\(badge)")
                    .font(.caption2.monospacedDigit())
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(.purple.opacity(0.22)))
            }
        }
        .font(.caption)
        .fontWeight(selected ? .semibold : .regular)
        .foregroundStyle(selected ? .primary : .secondary)
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 7)
                .fill(selected ? Color.primary.opacity(0.08) : Color.clear)
        )
    }

    private var profileMenu: some View {
        Menu {
            Button("2brain Rec") {}
                .disabled(true)
            Button(cabinetConfigured ? "Кабинет задан" : "Локальный режим") {}
                .disabled(true)
            Divider()
            ForEach(DesktopMeetingShellChrome.profileMenuLabels, id: \.self) { label in
                if label == "Закрыть 2brain Rec полностью" {
                    Button(role: .destructive) {
                        NSApplication.shared.terminate(nil)
                    } label: {
                        Label(label, systemImage: "power")
                    }
                } else {
                    Button {} label: {
                        Label(label, systemImage: profileMenuIcon(for: label))
                    }
                }
                if label == "Сообщество Slack" || label == "Оставить отзыв" {
                    Divider()
                }
            }
        } label: {
            HStack(spacing: 8) {
                ZStack {
                    Circle()
                        .fill(Color.blue.opacity(0.84))
                    Text("2")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)
                }
                .frame(width: 28, height: 28)
                VStack(alignment: .leading, spacing: 1) {
                    Text("2brain Rec")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .lineLimit(1)
                    Text(cabinetConfigured ? "Кабинет задан" : "Кабинет не подключен")
                        .font(.caption2)
                        .foregroundStyle(cabinetConfigured ? Color.secondary : Color.orange)
                        .lineLimit(1)
                }
                Spacer(minLength: 2)
                Image(systemName: "chevron.up.chevron.down")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 7)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.primary.opacity(0.06))
            )
        }
        .menuStyle(.borderlessButton)
        .buttonStyle(.plain)
        .help("Профиль и настройки")
        .accessibilityLabel("Профиль и настройки")
    }

    private func profileMenuIcon(for label: String) -> String {
        switch label {
        case "Внешний вид":
            return "display"
        case "Настройки":
            return "gearshape"
        case "Диагностика":
            return "stethoscope"
        case "Ресурсы":
            return "book"
        case "Связаться с поддержкой":
            return "bubble.left.and.bubble.right"
        case "Оставить отзыв":
            return "square.and.pencil"
        case "Сообщество Slack":
            return "number"
        case "Выйти":
            return "rectangle.portrait.and.arrow.right"
        default:
            return "circle"
        }
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text("Встречи")
                    .font(.headline)
                    .fontWeight(.semibold)
                Text(topBarSubtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            statusChip(title: captureStatusText, icon: captureStatusIcon, color: captureStatusColor)
            if pendingUploadCount > 0 {
                statusChip(title: "Загрузка \(pendingUploadCount)", icon: "tray.and.arrow.up", color: .orange)
            }
            Button(action: onRefresh) {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .accessibilityLabel("Обновить состояние")
            .help("Обновить состояние")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    private var meetingsSurface: some View {
        VStack(alignment: .leading, spacing: 0) {
            if cabinetConfigured {
                meetingsWorkspace
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            } else {
                localMeetingsWorkspace
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }
        .padding(cabinetConfigured ? 0 : 18)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var localMeetingsWorkspace: some View {
        VStack(alignment: .leading, spacing: 18) {
            localTodayStrip

            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .center) {
                    Text("Записи")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                    Spacer()
                    HStack(spacing: 10) {
                        Image(systemName: "bookmark")
                        Image(systemName: "line.3.horizontal.decrease")
                        Image(systemName: "arrow.up.arrow.down")
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }

                if localQueueRows.isEmpty {
                    localEmptyState
                } else {
                    VStack(spacing: 0) {
                        ForEach(localQueueRows) { item in
                            localRecordingRow(item)
                            if item.id != localQueueRows.last?.id {
                                Divider()
                                    .padding(.leading, 42)
                            }
                        }
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
                    )
                }
            }
        }
    }

    private var localTodayStrip: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Сегодня")
                .font(.caption)
                .foregroundStyle(.secondary)
            HStack(spacing: 12) {
                localTodayTile(
                    date: "Сейчас",
                    title: captureStatusText,
                    detail: pendingUploadCount > 0 ? "Загрузка ожидает" : "Готово"
                )
                localTodayTile(
                    date: "Кабинет",
                    title: cabinetConfigured ? "Сервер задан" : "Локальный режим",
                    detail: cabinetConfigured ? "Вход проверяется здесь" : "Сохраняются здесь"
                )
            }
        }
    }

    private func localTodayTile(date: String, title: String, detail: String) -> some View {
        HStack(spacing: 10) {
            VStack(spacing: 2) {
                Text(date)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Image(systemName: date == "Сейчас" ? captureStatusIcon : (cabinetConfigured ? "checkmark.circle" : "wifi.slash"))
                    .foregroundStyle(date == "Сейчас" ? captureStatusColor : (cabinetConfigured ? .green : .orange))
            }
            .frame(width: 52)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 7)
                    .fill(Color.secondary.opacity(0.08))
            )

            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .lineLimit(1)
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
    }

    private var localEmptyState: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Записей пока нет", systemImage: "waveform")
                .font(.subheadline)
                .fontWeight(.semibold)
            Text("Новая локальная запись появится в этом списке после завершения.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .frame(maxWidth: .infinity, minHeight: 180, alignment: .topLeading)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
    }

    private var localQueueRows: [DesktopUploadQueueItem] {
        uploadQueueItems
            .sorted {
                if $0.state.sortPriority != $1.state.sortPriority {
                    return $0.state.sortPriority < $1.state.sortPriority
                }
                if $0.updatedAt != $1.updatedAt {
                    return $0.updatedAt > $1.updatedAt
                }
                return $0.id < $1.id
            }
            .prefix(12)
            .map { $0 }
    }

    private func localRecordingRow(_ item: DesktopUploadQueueItem) -> some View {
        HStack(spacing: 12) {
            Image(systemName: localRecordingIcon(for: item))
                .frame(width: 18)
                .foregroundStyle(localRecordingColor(for: item))
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(localRecordingTitle(for: item))
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .lineLimit(1)
                    Text(localRecordingDuration(for: item))
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Text(localRecordingDetail(for: item))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 3) {
                Text(localRecordingDateText(for: item.updatedAt))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Text(localRecordingTimeText(for: item.updatedAt))
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
        .contentShape(Rectangle())
    }

    private func localRecordingTitle(for item: DesktopUploadQueueItem) -> String {
        if item.meetingId != nil {
            return "Встреча"
        }
        return "Запись \(localRecordingTimeText(for: item.updatedAt))"
    }

    private func localRecordingDetail(for item: DesktopUploadQueueItem) -> String {
        if item.state == .uploaded {
            return "Готова к обзору"
        }
        return item.state.displayName
    }

    private func localRecordingDuration(for item: DesktopUploadQueueItem) -> String {
        let seconds = max(1, item.artifactProfile.durationSeconds)
        let minutes = seconds / 60
        let remainder = seconds % 60
        if minutes == 0 {
            return "\(remainder)с"
        }
        return "\(minutes)м \(remainder)с"
    }

    private func localRecordingDateText(for date: Date) -> String {
        if Calendar.current.isDateInToday(date) {
            return "Сегодня"
        }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.setLocalizedDateFormatFromTemplate("d MMM")
        formatter.timeStyle = .none
        return formatter.string(from: date)
    }

    private func localRecordingTimeText(for date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.dateStyle = .none
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func localRecordingIcon(for item: DesktopUploadQueueItem) -> String {
        switch item.state {
        case .uploaded:
            return "checkmark.circle"
        case .uploading, .queued, .retrying:
            return "speaker.wave.2"
        case .blocked, .degraded, .failed:
            return "exclamationmark.circle"
        case .terminalDeleted:
            return "xmark.circle"
        }
    }

    private func localRecordingColor(for item: DesktopUploadQueueItem) -> Color {
        switch item.state {
        case .uploaded:
            return .green
        case .uploading, .queued:
            return .blue
        case .retrying, .degraded:
            return .orange
        case .blocked:
            return .secondary
        case .failed, .terminalDeleted:
            return .red
        }
    }

    @ViewBuilder
    private var inspectorContainer: some View {
        if expandedInspectorVisible {
            inspector
                .frame(width: DesktopMeetingShellChrome.expandedInspectorWidth)
        } else {
            compactInspector
                .frame(width: DesktopMeetingShellChrome.collapsedInspectorWidth)
        }
    }

    private var compactInspector: some View {
        VStack(spacing: 12) {
            InspectorDisclosureButton(isExpanded: false) {
                inspectorExpanded = true
            }

            VStack(spacing: 7) {
                railIcon("list.bullet.rectangle", selected: false)
                railIcon(captureStatusIcon, selected: true, color: captureStatusColor)
                railIcon("video", selected: false)
                Text("Off")
                    .font(.caption2)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 8)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.primary.opacity(0.05))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.secondary.opacity(0.18), lineWidth: 1)
            )

            compactToggle(title: "Mic", isOn: session != nil, color: captureStatusColor)
            compactToggle(title: "Noise", isOn: true, color: .purple)
            if pendingUploadCount > 0 {
                VStack(spacing: 3) {
                    Image(systemName: "tray.and.arrow.up.fill")
                        .foregroundStyle(.orange)
                    Text("\(pendingUploadCount)")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.orange)
                }
                .padding(.top, 2)
                .help("Ожидают проверки или загрузки: \(pendingUploadCount)")
            }

            Spacer()

            railIcon("mic", selected: false)
            railIcon("speaker.wave.2", selected: false)
            Button(action: onRefresh) {
                Image(systemName: "arrow.clockwise")
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
            .help("Обновить состояние")
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 10)
        .background(DesktopMeetingShellChrome.shellRailColor)
    }

    private func railIcon(_ icon: String, selected: Bool, color: Color = .secondary) -> some View {
        Image(systemName: icon)
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(selected ? color : Color.secondary)
            .frame(width: 28, height: 28)
            .background(
                RoundedRectangle(cornerRadius: 7)
                    .fill(selected ? color.opacity(0.18) : Color.primary.opacity(0.04))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 7)
                    .stroke(selected ? color.opacity(0.44) : Color.secondary.opacity(0.14), lineWidth: 1)
            )
    }

    private func compactToggle(title: String, isOn: Bool, color: Color) -> some View {
        VStack(spacing: 4) {
            Capsule()
                .fill(isOn ? color.opacity(0.84) : Color.secondary.opacity(0.22))
                .frame(width: 28, height: 14)
                .overlay(alignment: isOn ? .trailing : .leading) {
                    Circle()
                        .fill(Color.white.opacity(0.92))
                        .frame(width: 10, height: 10)
                        .padding(.horizontal, 2)
                }
            Text(title)
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
    }

    private var inspector: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Управление")
                        .font(.headline)
                    Text("Локальное управление")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                InspectorDisclosureButton(isExpanded: true) {
                    inspectorExpanded = false
                }
            }

            captureControls
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
                )

            VStack(alignment: .leading, spacing: 8) {
                Label("Доверие записи", systemImage: "lock.shield")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text(statusSummary)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                Text(lastEventSummary)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(DesktopMeetingShellChrome.shellSurfaceColor)
            )

            DisclosureGroup {
                diagnosticsContent
                    .padding(.top, 8)
            } label: {
                Label("Диагностика", systemImage: "stethoscope")
                    .font(.subheadline)
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(DesktopMeetingShellChrome.shellSurfaceColor)
            )

            Spacer()
        }
        .padding(14)
        .background(DesktopMeetingShellChrome.shellRailColor)
    }

    private func statusChip(title: String, icon: String, color: Color) -> some View {
        Label(title, systemImage: icon)
            .font(.caption)
            .foregroundStyle(color)
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .background(
                Capsule()
                    .fill(color.opacity(0.12))
            )
    }

    private var topBarSubtitle: String {
        cabinetConfigured
            ? "Сервер кабинета задан"
            : "Локальные записи и загрузки"
    }

    private var expandedInspectorVisible: Bool {
        inspectorExpanded || session != nil
    }

    private var captureStatusText: String {
        guard let session else { return "Готово к записи" }
        return CaptureStatusItem.statusLabel(for: session)
    }

    private var captureStatusIcon: String {
        guard let session else { return "record.circle" }
        switch session.state {
        case .active, .starting:
            return "dot.radiowaves.left.and.right"
        case .paused:
            return "pause.circle"
        case .failed, .degraded:
            return "exclamationmark.triangle.fill"
        default:
            return "record.circle"
        }
    }

    private var captureStatusColor: Color {
        guard let session else { return .secondary }
        switch session.state {
        case .active, .starting:
            return .green
        case .paused:
            return .orange
        case .failed, .degraded:
            return .red
        default:
            return .secondary
        }
    }

}

private struct InspectorDisclosureButton: View {
    let isExpanded: Bool
    let action: () -> Void
    @State private var isHovering = false

    var body: some View {
        Button(action: action) {
            Image(systemName: symbolName)
                .font(.system(size: 18, weight: .bold))
                .symbolRenderingMode(.hierarchical)
                .foregroundStyle(Color.primary.opacity(0.86))
                .frame(
                    width: DesktopMeetingShellChrome.inspectorToggleHitSize,
                    height: DesktopMeetingShellChrome.inspectorToggleHitSize
                )
                .background(
                    RoundedRectangle(
                        cornerRadius: DesktopMeetingShellChrome.inspectorToggleCornerRadius,
                        style: .continuous
                    )
                    .fill(isHovering ? Color.primary.opacity(0.10) : Color.clear)
                )
                .contentShape(
                    RoundedRectangle(
                        cornerRadius: DesktopMeetingShellChrome.inspectorToggleCornerRadius,
                        style: .continuous
                    )
                )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeOut(duration: 0.12)) {
                isHovering = hovering
            }
        }
        .help(accessibilityLabel)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityHint(isExpanded ? "Сворачивает правую панель" : "Раскрывает правую панель")
    }

    private var symbolName: String {
        isExpanded
            ? DesktopMeetingShellChrome.inspectorToggleExpandedSymbol
            : DesktopMeetingShellChrome.inspectorToggleCollapsedSymbol
    }

    private var accessibilityLabel: String {
        isExpanded
            ? DesktopMeetingShellChrome.inspectorToggleExpandedLabel
            : DesktopMeetingShellChrome.inspectorToggleCollapsedLabel
    }
}
