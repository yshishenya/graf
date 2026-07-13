import AppKit
import SwiftUI
import TwoBrainRecShared

public enum DesktopMeetingShellChrome {
    public static let collapsedInspectorWidth: CGFloat = 52
    public static let expandedInspectorWidth: CGFloat = 336
    public static let shellBackgroundHex = "#191a1c"
    public static let shellRailHex = "#202224"
    public static let shellSurfaceHex = "#242629"
    public static let recordingStripHex = "#342087"
    public static let shellAccentHex = "#8c73ff"
    public static let webEmbeddedBackgroundHex = shellBackgroundHex
    public static let shellBackgroundColor = Color(red: 0.098, green: 0.102, blue: 0.110)
    public static let shellRailColor = Color(red: 0.125, green: 0.133, blue: 0.141)
    public static let shellSurfaceColor = Color(red: 0.141, green: 0.149, blue: 0.161)
    public static let shellStrokeColor = Color.white.opacity(0.08)
    public static let recordingStripColor = Color(red: 0.204, green: 0.125, blue: 0.529)
    public static let shellAccentColor = Color(red: 0.549, green: 0.451, blue: 1.000)
    public static let recordingStripHeight: CGFloat = 44
    public static let idleShowsNativeTopBar = false
    public static let fontStackDescription = "SF Pro Text / system"
    public static let compactRailLabels = ["Запись", "Сохранность"]
    public static let settingsRailLabel = "Настройки"
    public static let webEmbeddedBackgroundNSColor = NSColor(
        srgbRed: 0.098,
        green: 0.102,
        blue: 0.110,
        alpha: 1
    )
    public static let inspectorToggleHitSize: CGFloat = 44
    public static let inspectorToggleCornerRadius: CGFloat = 10
    public static let inspectorToggleTopInset: CGFloat = 10
    public static let inspectorToggleTrailingInset: CGFloat = 4
    public static let inspectorToggleCollapsedSymbol = "chevron.left.2"
    public static let inspectorToggleExpandedSymbol = "chevron.right.2"
    public static let inspectorToggleCollapsedLabel = "Показать панель управления"
    public static let inspectorToggleExpandedLabel = "Скрыть панель управления"

    public static func shouldShowExpandedInspector(manualExpanded: Bool, hasActiveRecording _: Bool) -> Bool {
        manualExpanded
    }

    public static func recordingTitle(for mode: CaptureMode) -> String {
        switch mode {
        case .audioRecording:
            return "Запись аудио"
        case .transcriptOnly:
            return "Транскрибация"
        }
    }
}

public enum DesktopMeetingShellLocalQueuePolicy {
    public static func rowsNeedingNativeVisibility(
        _ items: [DesktopUploadQueueItem],
        limit: Int = 12
    ) -> [DesktopUploadQueueItem] {
        []
    }

    public static func allRowsForLocalMode(
        _ items: [DesktopUploadQueueItem],
        limit: Int = 12
    ) -> [DesktopUploadQueueItem] {
        Array(items.sortedForNativeLocalDisplay().prefix(limit))
    }
}

private extension Array where Element == DesktopUploadQueueItem {
    func sortedForNativeLocalDisplay() -> [DesktopUploadQueueItem] {
        sorted {
            if $0.createdAt != $1.createdAt {
                return $0.createdAt > $1.createdAt
            }
            if $0.updatedAt != $1.updatedAt {
                return $0.updatedAt > $1.updatedAt
            }
            if $0.state.sortPriority != $1.state.sortPriority {
                return $0.state.sortPriority < $1.state.sortPriority
            }
            return $0.id < $1.id
        }
    }
}

public struct DesktopMeetingShellView<CaptureControls: View, MeetingsWorkspace: View, DiagnosticsContent: View>: View {
    private let session: CaptureSession?
    private let uploadQueueItems: [DesktopUploadQueueItem]
    private let cabinetConfigured: Bool
    private let cabinetState: DesktopCabinetState
    private let onStopRecording: () -> Void
    private let onPauseRecording: () -> Void
    private let onResumeRecording: () -> Void
    private let onOpenSettings: () -> Void
    private let onSupportIncidentReport: ([String]) async throws -> DesktopSupportIncidentResponse
    private let captureControls: CaptureControls
    private let meetingsWorkspace: MeetingsWorkspace
    private let diagnosticsContent: DiagnosticsContent
    @State private var inspectorExpanded = false

    public init(
        session: CaptureSession?,
        uploadQueueItems: [DesktopUploadQueueItem],
        cabinetConfigured: Bool,
        cabinetState: DesktopCabinetState,
        onStopRecording: @escaping () -> Void = {},
        onPauseRecording: @escaping () -> Void = {},
        onResumeRecording: @escaping () -> Void = {},
        onOpenSettings: @escaping () -> Void = {},
        onSupportIncidentReport: @escaping ([String]) async throws -> DesktopSupportIncidentResponse = { _ in
            throw DesktopUploadClientError.httpStatus(503, "support_incident.unavailable")
        },
        @ViewBuilder captureControls: () -> CaptureControls,
        @ViewBuilder meetingsWorkspace: () -> MeetingsWorkspace,
        @ViewBuilder diagnosticsContent: () -> DiagnosticsContent
    ) {
        self.session = session
        self.uploadQueueItems = uploadQueueItems
        self.cabinetConfigured = cabinetConfigured
        self.cabinetState = cabinetState
        self.onStopRecording = onStopRecording
        self.onPauseRecording = onPauseRecording
        self.onResumeRecording = onResumeRecording
        self.onOpenSettings = onOpenSettings
        self.onSupportIncidentReport = onSupportIncidentReport
        self.captureControls = captureControls()
        self.meetingsWorkspace = meetingsWorkspace()
        self.diagnosticsContent = diagnosticsContent()
    }

    public var body: some View {
        HStack(spacing: 0) {
            VStack(spacing: 0) {
                HStack(alignment: .top, spacing: 0) {
                    meetingsSurface
                    Divider()
                    inspectorContainer
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .clipped()
                .overlay(alignment: .topTrailing) {
                    InspectorDisclosureButton(isExpanded: expandedInspectorVisible) {
                        inspectorExpanded = !expandedInspectorVisible
                    }
                    .padding(.top, DesktopMeetingShellChrome.inspectorToggleTopInset)
                    .padding(.trailing, DesktopMeetingShellChrome.inspectorToggleTrailingInset)
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(DesktopMeetingShellChrome.shellBackgroundColor)
        .background {
            RecordingTitlebarAccessory(
                session: recordingStripSession,
                onStop: onStopRecording,
                onPause: onPauseRecording,
                onResume: onResumeRecording
            )
            .frame(width: 0, height: 0)
        }
        .animation(.easeInOut(duration: 0.18), value: expandedInspectorVisible)
        .accessibilityIdentifier("desktop-meeting-shell")
    }

    private var meetingsSurface: some View {
        VStack(alignment: .leading, spacing: 0) {
            if cabinetConfigured {
                cabinetMeetingsWorkspace
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            } else {
                localMeetingsWorkspace
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }
        .padding(cabinetConfigured ? 0 : 18)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var cabinetMeetingsWorkspace: some View {
        VStack(alignment: .leading, spacing: 0) {
            if !localQueueRows.isEmpty {
                localQueueCompactPanel
                    .padding(.horizontal, 14)
                    .padding(.top, 12)
                    .padding(.bottom, 10)
            }
            meetingsWorkspace
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
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
                    detail: custodySummary?.title ?? "Готово",
                    icon: captureStatusIcon,
                    color: captureStatusColor
                )
                localTodayTile(
                    date: "Кабинет",
                    title: cabinetStatusPresentation.tileTitle,
                    detail: cabinetStatusPresentation.tileDetail,
                    icon: cabinetStatusPresentation.systemImage,
                    color: cabinetStatusColor
                )
            }
        }
    }

    private func localTodayTile(date: String, title: String, detail: String, icon: String, color: Color) -> some View {
        HStack(spacing: 10) {
            VStack(spacing: 2) {
                Text(date)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Image(systemName: icon)
                    .foregroundStyle(color)
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
        if cabinetConfigured {
            return DesktopMeetingShellLocalQueuePolicy.rowsNeedingNativeVisibility(uploadQueueItems)
        }
        return DesktopMeetingShellLocalQueuePolicy.allRowsForLocalMode(uploadQueueItems)
    }

    private var custodySummary: DesktopUploadCustodySummary? {
        DesktopUploadCustodySummary.summary(for: uploadQueueItems)
    }

    private var custodyDetailSummaries: [DesktopUploadCustodySummary] {
        DesktopUploadCustodySummary.summaries(for: uploadQueueItems)
    }

    private var meetingOwnerCustodyActionCount: Int {
        DesktopUploadCustodySummary.meetingOwnerActionCount(for: uploadQueueItems)
    }

    private var showsLocalDeleteConfirmationCopy: Bool {
        custodyDetailSummaries.contains { summary in
            summary.primaryProjection.custodyState == .cannotSend ||
                summary.primaryProjection.custodyState == .terminalUndelivered
        }
    }

    private var localQueueCompactPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Label("Локально на этом Mac", systemImage: "internaldrive")
                    .font(.caption)
                    .fontWeight(.semibold)
                Spacer()
                Text("\(localQueueRows.count)")
                    .font(.caption2.monospacedDigit())
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(DesktopMeetingShellChrome.shellAccentColor.opacity(0.22)))
            }
            VStack(spacing: 0) {
                ForEach(localQueueRows.prefix(3)) { item in
                    localRecordingRow(item)
                    if item.id != localQueueRows.prefix(3).last?.id {
                        Divider()
                            .padding(.leading, 42)
                    }
                }
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 9)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
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
                Text(localRecordingDateText(for: item.createdAt))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Text(localRecordingTimeText(for: item.createdAt))
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
        .contentShape(Rectangle())
        .accessibilityElement(children: .combine)
        .accessibilityLabel(localRecordingAccessibilityLabel(for: item))
    }

    private func localRecordingTitle(for item: DesktopUploadQueueItem) -> String {
        if item.meetingId != nil {
            return "Встреча"
        }
        return "Запись \(localRecordingTimeText(for: item.createdAt))"
    }

    private func localRecordingDetail(for item: DesktopUploadQueueItem) -> String {
        if item.state == .uploaded {
            return item.serverTruth.meetingId == nil
                ? "Локальная копия сохранена, сервер не подтвержден"
                : "Готова к обзору"
        }
        if item.state == .queued && item.serverTruth.meetingId == nil {
            return "Сохранена локально, ждет отправки"
        }
        if item.state == .retrying && item.serverTruth.meetingId == nil {
            return "Сохранена локально, повторим отправку"
        }
        if item.state == .blocked {
            let projection = DesktopUploadCustodyProjection(item: item)
            return DesktopUploadCustodyCopy.detail(
                copyKey: projection.copyKey,
                count: 1,
                deadline: projection.retentionDeadline
            )
        }
        return item.state.displayName
    }

    private func localRecordingAccessibilityLabel(for item: DesktopUploadQueueItem) -> String {
        let reviewState = item.serverTruth.mediaRevisionId == nil ? "" : ". Серверная медиа-ревизия подтверждена"
        return "\(localRecordingTitle(for: item)), \(localRecordingDetail(for: item)), \(localRecordingDuration(for: item))\(reviewState)"
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
                .frame(maxHeight: .infinity, alignment: .top)
        } else {
            compactInspector
                .frame(width: DesktopMeetingShellChrome.collapsedInspectorWidth)
                .frame(maxHeight: .infinity, alignment: .top)
        }
    }

    private var compactInspector: some View {
        VStack(spacing: 12) {
            Color.clear
                .frame(
                    width: DesktopMeetingShellChrome.inspectorToggleHitSize,
                    height: DesktopMeetingShellChrome.inspectorToggleHitSize
                )

            railIcon(
                captureStatusIcon,
                selected: session != nil,
                color: captureStatusColor
            )
            .help(DesktopMeetingShellChrome.compactRailLabels[0])

            if meetingOwnerCustodyActionCount > 0 {
                Text("\(meetingOwnerCustodyActionCount)")
                    .font(.system(size: 10, weight: .semibold, design: .monospaced))
                    .foregroundStyle(.white)
                    .frame(width: 30, height: 24)
                    .background(
                        RoundedRectangle(cornerRadius: 7)
                            .fill(Color.orange.opacity(0.82))
                    )
                    .help("\(DesktopMeetingShellChrome.compactRailLabels[1]): требуется действие")
            } else if let custodySummary {
                railIcon(
                    "internaldrive",
                    selected: false,
                    color: .secondary
                )
                .help(custodySummary.accessibilityLabel)
            }

            Button(action: onOpenSettings) {
                railIcon("gearshape", selected: false, color: .secondary)
            }
            .buttonStyle(.plain)
            .help(DesktopMeetingShellChrome.settingsRailLabel)
            .accessibilityLabel(DesktopMeetingShellChrome.settingsRailLabel)
            .accessibilityIdentifier("desktop-meeting-shell-settings-button")

            Spacer()
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 10)
        .background(DesktopMeetingShellChrome.shellRailColor)
    }

    private func railIcon(_ icon: String, selected: Bool, color: Color = .secondary) -> some View {
        Image(systemName: icon)
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(selected ? color : Color.secondary)
            .frame(width: 30, height: 30)
            .background(
                RoundedRectangle(cornerRadius: 7)
                    .fill(selected ? color.opacity(0.28) : Color.clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 7)
                    .stroke(selected ? color.opacity(0.54) : Color.clear, lineWidth: 1)
            )
    }

    private var inspector: some View {
        ScrollView(.vertical, showsIndicators: true) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .center) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Управление")
                            .font(.system(size: 15, weight: .semibold))
                        Text("Локальное управление")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button(action: onOpenSettings) {
                        Label(DesktopMeetingShellChrome.settingsRailLabel, systemImage: "gearshape")
                            .labelStyle(.iconOnly)
                    }
                    .buttonStyle(.borderless)
                    .help(DesktopMeetingShellChrome.settingsRailLabel)
                    .accessibilityLabel(DesktopMeetingShellChrome.settingsRailLabel)
                    .accessibilityIdentifier("desktop-meeting-shell-expanded-settings-button")
                }
                .padding(.trailing, DesktopMeetingShellChrome.inspectorToggleHitSize)

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
                        .font(.system(size: 13, weight: .semibold))
                    Text("Системный звук и микрофон записываются приложением")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                )

                if !custodyDetailSummaries.isEmpty {
                    custodyDetailsDisclosure
                }

                DisclosureGroup {
                    diagnosticsContent
                        .padding(.top, 8)
                } label: {
                    Label("Диагностика", systemImage: "stethoscope")
                        .font(.system(size: 13, weight: .semibold))
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                )
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .frame(maxHeight: .infinity, alignment: .top)
        .background(DesktopMeetingShellChrome.shellRailColor)
    }

    private var custodyDetailsDisclosure: some View {
        DisclosureGroup {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(custodyDetailSummaries, id: \.stableIdentity) { summary in
                    custodyDetailRow(summary)
                }

                if showsLocalDeleteConfirmationCopy {
                    Text("Удаление локальной копии доступно только после отдельного подтверждения: «Удалить локальную копию на этом Mac. Серверные данные не изменятся.»")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityLabel("Удаление локальной копии доступно только после отдельного подтверждения. Серверные данные не изменятся.")
                }
            }
            .padding(.top, 8)
        } label: {
            Label("Локальная сохранность", systemImage: "internaldrive")
                .font(.system(size: 13, weight: .semibold))
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
    }

    private func custodyDetailRow(_ summary: DesktopUploadCustodySummary) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Image(systemName: custodyDetailIcon(for: summary.primaryProjection))
                    .font(.caption)
                    .foregroundStyle(custodyDetailColor(for: summary.primaryProjection))
                    .frame(width: 14)
                VStack(alignment: .leading, spacing: 3) {
                    Text(summary.title)
                        .font(.caption)
                        .fontWeight(.semibold)
                        .lineLimit(1)
                        .minimumScaleFactor(0.82)
                    Text(summary.detail)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 8)
                Text(summary.pendingCount > 1 ? "\(summary.pendingCount)" : summary.ownerLabel)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.78)
            }

            DesktopSupportIncidentActionStrip(
                summary: summary,
                leadingPadding: 22,
                onSubmit: onSupportIncidentReport
            )
        }
        .accessibilityElement(children: summary.safeReport == nil ? .combine : .contain)
        .accessibilityLabel("\(summary.title). \(summary.detail). Ответственный: \(summary.ownerLabel).")
    }

    private func custodyDetailIcon(for projection: DesktopUploadCustodyProjection) -> String {
        switch projection.custodyState {
        case .delivered, .finalized, .processing:
            return "checkmark.icloud"
        case .partialUploaded, .uploadSessionCreated:
            return "icloud.and.arrow.up"
        case .serverUnknownLocalSaved, .serverRegistered:
            return "internaldrive"
        case .retainedAwaitingCondition, .cannotSend:
            return "exclamationmark.triangle"
        case .terminalUndelivered:
            return "xmark.icloud"
        }
    }

    private func custodyDetailColor(for projection: DesktopUploadCustodyProjection) -> Color {
        switch projection.custodyState {
        case .delivered, .finalized:
            return .green
        case .processing:
            return projection.copyKey == "custody.unknown_blocked" ? .orange : .green
        case .partialUploaded, .uploadSessionCreated, .serverRegistered:
            return .blue
        case .serverUnknownLocalSaved:
            return .secondary
        case .retainedAwaitingCondition:
            return .orange
        case .cannotSend, .terminalUndelivered:
            return .red
        }
    }

    private var expandedInspectorVisible: Bool {
        DesktopMeetingShellChrome.shouldShowExpandedInspector(
            manualExpanded: inspectorExpanded,
            hasActiveRecording: recordingStripSession != nil
        )
    }

    private var recordingStripSession: CaptureSession? {
        guard let session, CaptureStatusItem.showsStopButton(for: session) else {
            return nil
        }
        return session
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

    private var cabinetStatusPresentation: DesktopMeetingShellCabinetStatusPresentation {
        DesktopMeetingShellCabinetStatusPresentation.resolved(
            cabinetConfigured: cabinetConfigured,
            cabinetState: cabinetState
        )
    }

    private var cabinetStatusColor: Color {
        switch cabinetStatusPresentation.tone {
        case .success:
            return .green
        case .warning:
            return .orange
        case .error:
            return .red
        case .neutral:
            return .secondary
        }
    }

}

public enum DesktopMeetingShellCabinetStatusTone: Equatable, Sendable {
    case success
    case neutral
    case warning
    case error
}

public struct DesktopMeetingShellCabinetStatusPresentation: Equatable, Sendable {
    public let tileTitle: String
    public let tileDetail: String
    public let systemImage: String
    public let tone: DesktopMeetingShellCabinetStatusTone

    public static func resolved(
        cabinetConfigured: Bool,
        cabinetState: DesktopCabinetState
    ) -> DesktopMeetingShellCabinetStatusPresentation {
        guard cabinetConfigured else {
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Локальный режим",
                tileDetail: "Сохраняются здесь",
                systemImage: "wifi.slash",
                tone: .warning
            )
        }

        switch cabinetState {
        case .ready:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Сервер доступен",
                tileDetail: "Вход подтвержден",
                systemImage: "checkmark.circle",
                tone: .success
            )
        case .loading:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Проверяем сервер",
                tileDetail: "Ждем ответ кабинета",
                systemImage: "clock",
                tone: .neutral
            )
        case .offline, .timeout:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Сервер недоступен",
                tileDetail: "Запись работает локально",
                systemImage: "wifi.slash",
                tone: .error
            )
        case .expiredSession:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Нужен вход",
                tileDetail: "Откройте кабинет заново",
                systemImage: "person.crop.circle.badge.exclamationmark",
                tone: .warning
            )
        case .accessDenied:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Нет доступа",
                tileDetail: "Проверьте права",
                systemImage: "lock.trianglebadge.exclamationmark",
                tone: .warning
            )
        case .notFound:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Обзор не найден",
                tileDetail: "Проверьте встречу",
                systemImage: "questionmark.folder",
                tone: .warning
            )
        case .malformedResponse:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Нужна проверка",
                tileDetail: "Ответ сервера неожиданный",
                systemImage: "exclamationmark.triangle",
                tone: .warning
            )
        case .blockedRoute:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Ограничено",
                tileDetail: "Откройте снаружи",
                systemImage: "hand.raised",
                tone: .warning
            )
        case .notConfigured:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Локальный режим",
                tileDetail: "Сохраняются здесь",
                systemImage: "wifi.slash",
                tone: .warning
            )
        }
    }
}

private struct RecordingTitlebarAccessory: NSViewRepresentable {
    let session: CaptureSession?
    let onStop: () -> Void
    let onPause: () -> Void
    let onResume: () -> Void

    func makeNSView(context _: Context) -> RecordingTitlebarAccessoryAnchor {
        RecordingTitlebarAccessoryAnchor()
    }

    func updateNSView(_ nsView: RecordingTitlebarAccessoryAnchor, context _: Context) {
        nsView.update(
            session: session,
            onStop: onStop,
            onPause: onPause,
            onResume: onResume
        )
    }

    static func dismantleNSView(_ nsView: RecordingTitlebarAccessoryAnchor, coordinator _: ()) {
        nsView.removeAccessory()
    }
}

private final class RecordingTitlebarAccessoryAnchor: NSView {
    private var session: CaptureSession?
    private var onStop: () -> Void = {}
    private var onPause: () -> Void = {}
    private var onResume: () -> Void = {}
    private weak var installedWindow: NSWindow?
    private var accessoryController: NSTitlebarAccessoryViewController?
    private var hostingView: NSHostingView<AnyView>?

    func update(
        session: CaptureSession?,
        onStop: @escaping () -> Void,
        onPause: @escaping () -> Void,
        onResume: @escaping () -> Void
    ) {
        self.session = session
        self.onStop = onStop
        self.onPause = onPause
        self.onResume = onResume
        syncAccessory()
    }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        syncAccessory()
    }

    func removeAccessory() {
        guard let accessoryController else { return }
        if let installedWindow,
           let index = installedWindow.titlebarAccessoryViewControllers.firstIndex(where: { $0 === accessoryController }) {
            installedWindow.removeTitlebarAccessoryViewController(at: index)
        }
        self.accessoryController = nil
        self.hostingView = nil
        self.installedWindow = nil
    }

    private func syncAccessory() {
        guard let session, CaptureStatusItem.showsStopButton(for: session) else {
            removeAccessory()
            return
        }
        guard let window else { return }

        if installedWindow !== window {
            removeAccessory()
        }

        let rootView = AnyView(RecordingTitlebarHUD(
            session: session,
            onStop: onStop,
            onPause: onPause,
            onResume: onResume
        ))
        let host = hostingView ?? NSHostingView(rootView: rootView)
        host.rootView = rootView
        host.frame = NSRect(
            x: 0,
            y: 0,
            width: window.frame.width,
            height: DesktopMeetingShellChrome.recordingStripHeight
        )
        host.autoresizingMask = [.width]
        hostingView = host

        if accessoryController == nil {
            let controller = NSTitlebarAccessoryViewController()
            controller.layoutAttribute = .bottom
            controller.fullScreenMinHeight = DesktopMeetingShellChrome.recordingStripHeight
            controller.view = host
            accessoryController = controller
            installedWindow = window
            window.addTitlebarAccessoryViewController(controller)
        } else {
            accessoryController?.fullScreenMinHeight = DesktopMeetingShellChrome.recordingStripHeight
        }
    }
}

private struct RecordingTitlebarHUD: View {
    let session: CaptureSession
    let onStop: () -> Void
    let onPause: () -> Void
    let onResume: () -> Void

    var body: some View {
        HStack {
            Spacer(minLength: 0)

            HStack(spacing: 10) {
                HStack(spacing: 7) {
                    Image(systemName: "waveform")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(.green)
                    Text(DesktopMeetingShellChrome.recordingTitle(for: session.mode))
                        .font(.system(size: 12, weight: .semibold))
                        .lineLimit(1)
                }

                Divider()
                    .frame(height: 16)

                TimelineView(.periodic(from: .now, by: 1)) { context in
                    Text(recordingElapsedText(at: context.date))
                        .font(.system(size: 12, weight: .semibold, design: .monospaced))
                        .foregroundStyle(Color.white.opacity(0.90))
                }
                .frame(width: 54)

                if showsControls {
                    Divider()
                        .frame(height: 16)
                    controls
                }
            }
            .padding(.leading, 10)
            .padding(.trailing, 6)
            .frame(height: 32)
            .background(
                Capsule()
                    .fill(DesktopMeetingShellChrome.shellSurfaceColor)
            )
            .overlay(
                Capsule()
                    .stroke(DesktopMeetingShellChrome.recordingStripColor.opacity(0.58), lineWidth: 1)
            )

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 12)
        .frame(height: DesktopMeetingShellChrome.recordingStripHeight)
        .frame(maxWidth: .infinity)
        .background(DesktopMeetingShellChrome.shellBackgroundColor)
        .overlay(alignment: .bottom) {
            Divider()
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Идет запись. \(CaptureStatusItem.statusLabel(for: session)).")
        .accessibilityIdentifier("systemAudio.titlebarRecordingHUD")
    }

    @ViewBuilder
    private var controls: some View {
        if CaptureStatusItem.showsPauseButton(for: session) {
            Button(action: onPause) {
                Label(SystemAudioStatusLabels.pauseButtonTitle, systemImage: "pause.fill")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .disabled(!session.stopActionAvailable)
            .accessibilityLabel(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
            .help(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
        } else if CaptureStatusItem.showsResumeButton(for: session) {
            Button(action: onResume) {
                Label(SystemAudioStatusLabels.resumeButtonTitle, systemImage: "play.fill")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .disabled(!session.stopActionAvailable)
            .accessibilityLabel(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
            .help(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
        }

        if CaptureStatusItem.showsStopButton(for: session) {
            Button(role: .destructive, action: onStop) {
                Label("Стоп", systemImage: "stop.fill")
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
            .tint(.red)
            .disabled(!session.stopActionAvailable)
            .accessibilityLabel(SystemAudioStatusLabels.stopButtonAccessibilityLabel)
            .help(SystemAudioStatusLabels.stopButtonAccessibilityLabel)
        }
    }

    private var showsControls: Bool {
        CaptureStatusItem.showsPauseButton(for: session) ||
            CaptureStatusItem.showsResumeButton(for: session) ||
            CaptureStatusItem.showsStopButton(for: session)
    }

    private func recordingElapsedText(at date: Date) -> String {
        guard let startedAt = session.startedAt else {
            return "0:00"
        }
        let elapsed = max(0, Int(date.timeIntervalSince(startedAt)))
        let hours = elapsed / 3600
        let minutes = (elapsed % 3600) / 60
        let seconds = elapsed % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, seconds)
        }
        return String(format: "%d:%02d", minutes, seconds)
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
