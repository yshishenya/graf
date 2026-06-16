import SwiftUI
import TwoBrainRecShared

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
                .frame(width: 188)
            Divider()
            VStack(spacing: 0) {
                topBar
                Divider()
                HStack(spacing: 0) {
                    meetingsSurface
                    Divider()
                    inspector
                        .frame(width: 338)
                }
            }
        }
        .background(Color(nsColor: .windowBackgroundColor))
        .accessibilityIdentifier("desktop-meeting-shell")
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 18) {
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
                        .font(.headline)
                    Text(cabinetConfigured ? "Рабочее место" : "Локальный режим")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.top, 8)

            VStack(alignment: .leading, spacing: 4) {
                navRow("Поиск", "magnifyingglass", selected: false)
                navRow("Мои встречи", "rectangle.stack", selected: true)
                navRow("Общие", "person.2", selected: false)
                navRow("Действия", "checkmark.circle", selected: false, badge: pendingUploadCount)
                navRow("Активность", "waveform.path.ecg", selected: false)
                navRow("Настройки", "gearshape", selected: false)
            }

            Spacer()

            VStack(alignment: .leading, spacing: 6) {
                Label(cabinetConfigured ? "Кабинет подключен" : "Кабинет не подключен", systemImage: cabinetConfigured ? "checkmark.seal" : "wifi.slash")
                    .font(.caption)
                    .foregroundStyle(cabinetConfigured ? .green : .orange)
            }
        }
        .padding(14)
        .background(Color(nsColor: .controlBackgroundColor))
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
        .font(.subheadline)
        .foregroundStyle(selected ? .primary : .secondary)
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
        .background(
            RoundedRectangle(cornerRadius: 7)
                .fill(selected ? Color.primary.opacity(0.08) : Color.clear)
        )
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text("Встречи")
                    .font(.title2)
                    .fontWeight(.semibold)
                Text(topBarSubtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            statusChip(title: captureStatusText, icon: captureStatusIcon, color: captureStatusColor)
            statusChip(title: pendingUploadCount > 0 ? "Загрузка \(pendingUploadCount)" : "Загрузок нет", icon: "tray.and.arrow.up", color: pendingUploadCount > 0 ? .orange : .secondary)
            Button(action: onRefresh) {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .accessibilityLabel("Обновить состояние")
            .help("Обновить состояние")
        }
        .padding(.horizontal, 22)
        .padding(.vertical, 14)
    }

    private var meetingsSurface: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Мои встречи")
                        .font(.headline)
                    Text(cabinetConfigured ? "Сегодня и последние записи" : "Локальные записи")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button {
                    onRunCheck()
                } label: {
                    Label(isChecking ? "Проверяем" : "Проверить звук", systemImage: "waveform")
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .disabled(isChecking)
            }

            if cabinetConfigured {
                meetingsWorkspace
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            } else {
                localMeetingsWorkspace
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }
        .padding(20)
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
                            .fill(Color(nsColor: .controlBackgroundColor))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.secondary.opacity(0.16), lineWidth: 1)
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
                    title: cabinetConfigured ? "Подключен" : "Локальный режим",
                    detail: cabinetConfigured ? "Синхронизация" : "Сохраняются здесь"
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
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.secondary.opacity(0.14), lineWidth: 1)
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
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.secondary.opacity(0.16), lineWidth: 1)
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

    private var inspector: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Запись")
                        .font(.headline)
                    Text("Локальное управление")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: captureStatusIcon)
                    .foregroundStyle(captureStatusColor)
            }

            captureControls
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color(nsColor: .controlBackgroundColor))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.secondary.opacity(0.16), lineWidth: 1)
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
                    .fill(Color(nsColor: .controlBackgroundColor))
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
                    .fill(Color(nsColor: .controlBackgroundColor))
            )

            Spacer()
        }
        .padding(18)
        .background(Color(nsColor: .underPageBackgroundColor))
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
            ? "Кабинет встреч подключен"
            : "Локальные записи и загрузки"
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
