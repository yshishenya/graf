import AppKit
import SwiftUI
import TwoBrainRecShared

public enum DesktopMeetingShellChrome {
    public static let spacingSmall: CGFloat = 8
    public static let spacingMedium: CGFloat = 16
    public static let spacingLarge: CGFloat = 16
    public static let spacingXLarge: CGFloat = 24
    public static let controlHeight: CGFloat = 32
    public static let webButtonHeight: CGFloat = 32
    public static let webButtonCornerRadius: CGFloat = 7
    public static let webButtonHorizontalPadding: CGFloat = 12
    public static let webButtonDisabledOpacity: CGFloat = 0.68
    public static let webButtonPrimaryHex = "#8c73ff"
    public static let webButtonSecondaryDarkHex = "#26282c"
    public static let webButtonBorderDarkHex = "#30343a"
    public static let webButtonPrimaryColor = Color(red: 0.549, green: 0.451, blue: 1.000)
    public static let webButtonSecondaryDarkColor = Color(red: 0.149, green: 0.157, blue: 0.173)
    public static let webButtonSecondaryLightColor = Color(red: 0.957, green: 0.961, blue: 0.969)
    public static let webButtonBorderDarkColor = Color(red: 0.188, green: 0.204, blue: 0.227)
    public static let webButtonBorderLightColor = Color(red: 0.788, green: 0.804, blue: 0.827)
    public static let webButtonTextDarkColor = Color(red: 0.910, green: 0.918, blue: 0.933)
    public static let webButtonTextLightColor = Color(red: 0.110, green: 0.125, blue: 0.149)
    public static let webButtonDestructiveColor = Color(red: 1.000, green: 0.420, blue: 0.420)
    public static let minimumInteractiveTarget: CGFloat = 40
    public static let collapsedInspectorWidth: CGFloat = 52
    public static let expandedInspectorWidth: CGFloat = 308
    public static let shellBackgroundHex = "#0a0a0b"
    public static let shellRailHex = "#121214"
    public static let shellSurfaceHex = "#1c1c1f"
    public static let recordingStripHex = "#342087"
    public static let shellAccentHex = "#8c73ff"
    public static let webEmbeddedBackgroundHex = shellBackgroundHex
    public static let shellBackgroundColor = Color(red: 0.039, green: 0.039, blue: 0.043)
    public static let shellRailColor = Color(red: 0.070, green: 0.070, blue: 0.078)
    public static let shellSurfaceColor = Color(red: 0.110, green: 0.110, blue: 0.121)
    public static let shellStrokeColor = Color.white.opacity(0.05)
    public static let shellHighContrastStrokeColor = Color.white.opacity(0.42)
    public static let recordingStripColor = Color(red: 0.204, green: 0.125, blue: 0.529)
    public static let shellAccentColor = Color(red: 0.549, green: 0.451, blue: 1.000)
    public static let recordingStripHeight: CGFloat = 44
    public static let idleShowsNativeTopBar = false
    public static let fontStackDescription = "SF Pro Text / system"
    public static let compactRailLabels = ["Статус записи", "Локальная сохранность"]
    public static let compactRailStartLabel = "Начать запись"
    public static let compactRailStopLabel = "Остановить запись"
    public static let compactRailActionHitSize: CGFloat = 40
    public static let settingsRailLabel = "Настройки"
    public static let appUpdateLabel = "Доступно обновление"
    public static let appUpdateAccessibilityLabel = "Доступно обновление GRAF. Открыть проверку обновлений."
    public static let appUpdateHitSize: CGFloat = 40
    public static let webEmbeddedBackgroundNSColor = NSColor(
        srgbRed: 0.039,
        green: 0.039,
        blue: 0.043,
        alpha: 1
    )
    public static let inspectorToggleHitSize: CGFloat = 44
    public static let inspectorToggleCornerRadius: CGFloat = 12
    public static let inspectorToggleTopInset: CGFloat = 10
    public static let inspectorToggleTrailingInset: CGFloat = 4
    public static let inspectorToggleCollapsedSymbol = "chevron.left.2"
    public static let inspectorToggleExpandedSymbol = "chevron.right.2"
    public static let inspectorToggleCollapsedLabel = "Показать панель управления"
    public static let inspectorToggleExpandedLabel = "Скрыть панель управления"

    public static func inspectorToggleSymbol(isExpanded: Bool) -> String {
        isExpanded ? inspectorToggleExpandedSymbol : inspectorToggleCollapsedSymbol
    }

    public static func inspectorToggleLabel(isExpanded: Bool) -> String {
        isExpanded ? inspectorToggleExpandedLabel : inspectorToggleCollapsedLabel
    }

    public static func inspectorToggleHint(isExpanded: Bool) -> String {
        isExpanded ? "Сворачивает правую панель" : "Раскрывает правую панель"
    }

    public static func shouldShowExpandedInspector(manualExpanded: Bool, hasActionableProblem: Bool) -> Bool {
        manualExpanded || hasActionableProblem
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

public enum DesktopWebButtonVariant: Equatable, Sendable {
    case secondary
    case primary
    case destructive
}

public struct DesktopWebButtonStyle: ButtonStyle {
    private let variant: DesktopWebButtonVariant
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.isEnabled) private var isEnabled

    public init(_ variant: DesktopWebButtonVariant = .secondary) {
        self.variant = variant
    }

    public func makeBody(configuration: Configuration) -> some View {
        let shape = RoundedRectangle(
            cornerRadius: DesktopMeetingShellChrome.webButtonCornerRadius,
            style: .continuous
        )

        configuration.label
            .font(.system(size: 13, weight: variant == .primary ? .bold : .medium))
            .foregroundStyle(foregroundColor)
            .padding(.horizontal, DesktopMeetingShellChrome.webButtonHorizontalPadding)
            .frame(minHeight: DesktopMeetingShellChrome.webButtonHeight)
            .background(
                backgroundColor.opacity(configuration.isPressed ? 0.86 : 1),
                in: shape
            )
            .overlay(shape.stroke(borderColor, lineWidth: 1))
            .opacity(isEnabled ? 1 : DesktopMeetingShellChrome.webButtonDisabledOpacity)
    }

    private var isDark: Bool {
        colorScheme == .dark
    }

    private var backgroundColor: Color {
        variant == .primary
            ? DesktopMeetingShellChrome.webButtonPrimaryColor
            : (isDark
                ? DesktopMeetingShellChrome.webButtonSecondaryDarkColor
                : DesktopMeetingShellChrome.webButtonSecondaryLightColor)
    }

    private var borderColor: Color {
        variant == .primary
            ? DesktopMeetingShellChrome.webButtonPrimaryColor
            : (isDark
                ? DesktopMeetingShellChrome.webButtonBorderDarkColor
                : DesktopMeetingShellChrome.webButtonBorderLightColor)
    }

    private var foregroundColor: Color {
        switch variant {
        case .primary:
            return .white
        case .secondary:
            return isDark
                ? DesktopMeetingShellChrome.webButtonTextDarkColor
                : DesktopMeetingShellChrome.webButtonTextLightColor
        case .destructive:
            return DesktopMeetingShellChrome.webButtonDestructiveColor
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

    public static func measuredProgress(for item: DesktopUploadQueueItem) -> Double? {
        guard item.state == .uploading else { return nil }
        let roles = item.serverTruth.uploadProgressRoles
        guard item.artifactProfile.totalUploadBytes(limitedToRoles: roles) > 0 else { return nil }
        let fraction = item.progressFraction
        guard fraction.isFinite else { return nil }
        return min(max(fraction, 0), 1)
    }

    public static func progressPercent(for item: DesktopUploadQueueItem) -> Int? {
        guard let fraction = measuredProgress(for: item) else { return nil }
        return min(100, max(0, Int(fraction * 100)))
    }

    public static func progressDetail(for item: DesktopUploadQueueItem) -> String? {
        guard let percent = progressPercent(for: item) else { return nil }
        return percent == 100
            ? "Файлы переданы. Проверяем запись перед просмотром."
            : "Отправка продолжается."
    }

    public static func progressAccessibilityLabel(for item: DesktopUploadQueueItem) -> String? {
        guard let percent = progressPercent(for: item) else { return nil }
        return "Отправка записи: \(percent) процентов."
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

@MainActor
public struct DesktopMeetingShellView<CaptureControls: View, MeetingsWorkspace: View>: View {
    private let session: CaptureSession?
    private let uploadQueueItems: [DesktopUploadQueueItem]
    private let cabinetConfigured: Bool
    private let cabinetState: DesktopCabinetState
    private let startRecordingAvailable: Bool
    private let recordingTransitionInProgress: Bool
    private let hasActionableCaptureProblem: Bool
    private let showsAppUpdateBadge: Bool
    private let onStartRecording: () -> Void
    private let onStopRecording: () -> Void
    private let onPauseRecording: () -> Void
    private let onResumeRecording: () -> Void
    private let onOpenSettings: () -> Void
    private let onCheckForUpdates: () -> Void
    private let onSupportIncidentReport: ([String]) async throws -> DesktopSupportIncidentResponse
    private let onSupportIncidentSync: ([String]) async throws -> DesktopSupportIncidentResponse
    private let onCopySupportIncidentReport: ([String]) throws -> String?
    private let onOpenSupportSignIn: () -> Void
    private let captureControls: CaptureControls
    private let meetingsWorkspace: MeetingsWorkspace
    @State private var inspectorExpanded = false
    @State private var attentionExpansionDismissed = false
    @Environment(\.accessibilityReduceMotion) private var accessibilityReduceMotion
    @Environment(\.colorSchemeContrast) private var colorSchemeContrast

    public init(
        session: CaptureSession?,
        uploadQueueItems: [DesktopUploadQueueItem],
        cabinetConfigured: Bool,
        cabinetState: DesktopCabinetState,
        startRecordingAvailable: Bool = false,
        recordingTransitionInProgress: Bool = false,
        hasActionableCaptureProblem: Bool = false,
        showsAppUpdateBadge: Bool = false,
        onStartRecording: @escaping () -> Void = {},
        onStopRecording: @escaping () -> Void = {},
        onPauseRecording: @escaping () -> Void = {},
        onResumeRecording: @escaping () -> Void = {},
        onOpenSettings: @escaping () -> Void = {},
        onCheckForUpdates: @escaping () -> Void = {},
        onSupportIncidentReport: @escaping ([String]) async throws -> DesktopSupportIncidentResponse = { _ in
            throw DesktopUploadClientError.httpStatus(503, "support_incident.unavailable")
        },
        onSupportIncidentSync: @escaping ([String]) async throws -> DesktopSupportIncidentResponse = { _ in
            throw DesktopUploadClientError.httpStatus(401, "support_incident.auth_session_required")
        },
        onCopySupportIncidentReport: @escaping ([String]) throws -> String? = { _ in nil },
        onOpenSupportSignIn: @escaping () -> Void = {},
        @ViewBuilder captureControls: () -> CaptureControls,
        @ViewBuilder meetingsWorkspace: () -> MeetingsWorkspace
    ) {
        self.session = session
        self.uploadQueueItems = uploadQueueItems
        self.cabinetConfigured = cabinetConfigured
        self.cabinetState = cabinetState
        self.startRecordingAvailable = startRecordingAvailable
        self.recordingTransitionInProgress = recordingTransitionInProgress
        self.hasActionableCaptureProblem = hasActionableCaptureProblem
        self.showsAppUpdateBadge = showsAppUpdateBadge
        self.onStartRecording = onStartRecording
        self.onStopRecording = onStopRecording
        self.onPauseRecording = onPauseRecording
        self.onResumeRecording = onResumeRecording
        self.onOpenSettings = onOpenSettings
        self.onCheckForUpdates = onCheckForUpdates
        self.onSupportIncidentReport = onSupportIncidentReport
        self.onSupportIncidentSync = onSupportIncidentSync
        self.onCopySupportIncidentReport = onCopySupportIncidentReport
        self.onOpenSupportSignIn = onOpenSupportSignIn
        self.captureControls = captureControls()
        self.meetingsWorkspace = meetingsWorkspace()
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
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(DesktopMeetingShellChrome.shellBackgroundColor)
        .tint(DesktopMeetingShellChrome.shellAccentColor)
        .background {
            RecordingTitlebarAccessory(
                session: recordingStripSession,
                transitionInProgress: recordingTransitionInProgress,
                onStop: onStopRecording,
                onPause: onPauseRecording,
                onResume: onResumeRecording
            )
            .frame(width: 0, height: 0)
        }
        .animation(accessibilityReduceMotion ? nil : .easeInOut(duration: 0.18), value: expandedInspectorVisible)
        .onChange(of: hasActionableCaptureProblem) { _, isActionable in
            if isActionable {
                attentionExpansionDismissed = false
            }
        }
        .onChange(of: attentionCustodySignature) { _, attentionSignature in
            if !attentionSignature.isEmpty {
                attentionExpansionDismissed = false
            }
        }
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
        VStack(alignment: .leading, spacing: DesktopMeetingShellChrome.spacingLarge) {
            if showsAppUpdateBadge {
                localAppUpdateBadge
            }
            localCabinetStatus

            VStack(alignment: .leading, spacing: DesktopMeetingShellChrome.spacingMedium) {
                Text("Записи на этом Mac")
                    .font(.subheadline)
                    .fontWeight(.semibold)

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
                            .stroke(shellStrokeColor, lineWidth: 1)
                    )
                }
            }
        }
    }

    private var localAppUpdateBadge: some View {
        Button(action: onCheckForUpdates) {
            HStack(spacing: DesktopMeetingShellChrome.spacingSmall) {
                Image(systemName: "arrow.down.circle.fill")
                    .font(.system(size: 15, weight: .semibold))
                Text(DesktopMeetingShellChrome.appUpdateLabel)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Spacer()
            }
            .padding(.horizontal, DesktopMeetingShellChrome.spacingMedium)
            .frame(
                maxWidth: .infinity,
                minHeight: DesktopMeetingShellChrome.appUpdateHitSize,
                alignment: .leading
            )
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(DesktopMeetingShellChrome.shellAccentColor.opacity(0.16))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(DesktopMeetingShellChrome.shellAccentColor.opacity(0.62), lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .foregroundStyle(DesktopMeetingShellChrome.shellAccentColor)
        .contentShape(Rectangle())
        .help(DesktopMeetingShellChrome.appUpdateAccessibilityLabel)
        .accessibilityLabel(DesktopMeetingShellChrome.appUpdateAccessibilityLabel)
        .accessibilityIdentifier("desktop-meeting-shell-app-update")
    }

    private var localCabinetStatus: some View {
        HStack(spacing: DesktopMeetingShellChrome.spacingMedium) {
            Image(systemName: cabinetStatusPresentation.systemImage)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(cabinetStatusColor)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: 3) {
                Text(cabinetStatusPresentation.tileTitle)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .lineLimit(1)
                Text(cabinetStatusPresentation.tileDetail)
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
                .stroke(shellStrokeColor, lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(cabinetStatusPresentation.tileTitle). \(cabinetStatusPresentation.tileDetail)")
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
                .stroke(shellStrokeColor, lineWidth: 1)
        )
    }

    private var localQueueRows: [DesktopUploadQueueItem] {
        if cabinetConfigured {
            return DesktopMeetingShellLocalQueuePolicy.rowsNeedingNativeVisibility(uploadQueueItems)
        }
        return DesktopMeetingShellLocalQueuePolicy.allRowsForLocalMode(uploadQueueItems)
    }

    private var custodyDetailSummaries: [DesktopUploadCustodySummary] {
        return DesktopUploadCustodySummary.summaries(for: uploadQueueItems)
    }

    private var attentionCustodySummaries: [DesktopUploadCustodySummary] {
        custodyDetailSummaries.filter { summary in
            summary.primaryProjection.requiresUserAttention
        }
    }

    private var attentionCustodyItemCount: Int {
        DesktopUploadCustodySummary.attentionItemCount(for: uploadQueueItems)
    }

    private var attentionCustodySignature: String {
        attentionCustodySummaries.map { summary in
            "\(summary.stableIdentity)|\(summary.primaryProjection.normalUserAction.rawValue)|\(summary.pendingCount)"
        }.joined(separator: ";")
    }

    private var showsLocalDeleteConfirmationCopy: Bool {
        attentionCustodySummaries.contains { summary in
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
                .stroke(shellStrokeColor, lineWidth: 1)
        )
    }

    private func localRecordingRow(_ item: DesktopUploadQueueItem) -> some View {
        HStack(spacing: 12) {
            Image(systemName: localRecordingIcon(for: item))
                .frame(width: 18)
                .foregroundStyle(localRecordingColor(for: item))
            VStack(alignment: .leading, spacing: 4) {
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
                if let progress = DesktopMeetingShellLocalQueuePolicy.measuredProgress(for: item),
                   let percent = DesktopMeetingShellLocalQueuePolicy.progressPercent(for: item) {
                    HStack(spacing: 8) {
                        ProgressView(value: progress)
                            .progressViewStyle(.linear)
                            .tint(localRecordingColor(for: item))
                        Text("\(percent)%")
                            .font(.caption2.monospacedDigit())
                            .foregroundStyle(.secondary)
                    }
                    .accessibilityHidden(true)
                }
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
        if let progressDetail = DesktopMeetingShellLocalQueuePolicy.progressDetail(for: item) {
            return progressDetail
        }
        if item.state == .uploaded {
            return item.serverTruth.meetingId == nil
                ? "Сохранено на Mac; сервер пока не подтвердил запись"
                : "Готово к просмотру"
        }
        if item.state == .queued && item.serverTruth.meetingId == nil {
            return "Сохранено на Mac; отправим автоматически"
        }
        if item.state == .retrying && item.serverTruth.meetingId == nil {
            return "Сохранено на Mac; повторим отправку автоматически"
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
        let reviewState = item.serverTruth.mediaRevisionId == nil ? "" : ". Запись получена сервером"
        let progressState = DesktopMeetingShellLocalQueuePolicy.progressAccessibilityLabel(for: item)
            .map { " \($0)" } ?? ""
        return "\(localRecordingTitle(for: item)), \(localRecordingDetail(for: item)), \(localRecordingDuration(for: item))\(progressState)\(reviewState)"
    }

    private func localRecordingDuration(for item: DesktopUploadQueueItem) -> String {
        let seconds = max(0, item.artifactProfile.durationSeconds)
        let minutes = seconds / 60
        let remainder = seconds % 60
        if minutes == 0 {
            return "\(remainder) с"
        }
        return remainder == 0 ? "\(minutes) мин" : "\(minutes) мин \(remainder) с"
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
        case .saving, .uploading, .queued, .retrying:
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
        case .saving, .uploading, .queued:
            return DesktopMeetingShellChrome.shellAccentColor
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
        VStack(spacing: 0) {
            inspectorDisclosureHeader(isExpanded: false)

            VStack(spacing: DesktopMeetingShellChrome.spacingSmall) {
                railIcon(
                    captureStatusIcon,
                    selected: session != nil || hasActionableCaptureProblem,
                    color: captureStatusColor
                )
                .frame(
                    width: DesktopMeetingShellChrome.compactRailActionHitSize,
                    height: DesktopMeetingShellChrome.compactRailActionHitSize
                )
                .help(captureStatusText)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("\(DesktopMeetingShellChrome.compactRailLabels[0]): \(captureStatusText)")
                .accessibilityIdentifier("desktop-meeting-shell-recording-status")

                compactCaptureAction

                if attentionCustodyItemCount > 0 {
                    Button {
                        attentionExpansionDismissed = false
                        inspectorExpanded = true
                    } label: {
                        Text("\(attentionCustodyItemCount)")
                            .font(.system(size: 10, weight: .semibold, design: .monospaced))
                            .foregroundStyle(.white)
                            .frame(width: 30, height: 24)
                            .background(
                                RoundedRectangle(cornerRadius: 7)
                                    .fill(Color.orange.opacity(0.82))
                            )
                    }
                    .buttonStyle(.plain)
                    .frame(
                        width: DesktopMeetingShellChrome.minimumInteractiveTarget,
                        height: DesktopMeetingShellChrome.minimumInteractiveTarget
                    )
                    .contentShape(Rectangle())
                    .help("\(DesktopMeetingShellChrome.compactRailLabels[1]): требуется внимание")
                    .accessibilityLabel("\(DesktopMeetingShellChrome.compactRailLabels[1]): требуется внимание")
                }
            }
            Spacer()
        }
        .padding(.bottom, DesktopMeetingShellChrome.spacingMedium)
        .background(DesktopMeetingShellChrome.shellRailColor)
    }

    @ViewBuilder
    private var compactCaptureAction: some View {
        if let session = recordingStripSession {
            Button(role: .destructive, action: onStopRecording) {
                Image(systemName: "stop.fill")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(
                        width: DesktopMeetingShellChrome.compactRailActionHitSize,
                        height: DesktopMeetingShellChrome.compactRailActionHitSize
                    )
                    .background(
                        RoundedRectangle(cornerRadius: 9, style: .continuous)
                            .fill(Color.red.opacity(0.88))
                    )
            }
            .buttonStyle(.plain)
            .contentShape(Rectangle())
            .disabled(recordingTransitionInProgress || !session.stopActionAvailable)
            .help(DesktopMeetingShellChrome.compactRailStopLabel)
            .accessibilityLabel(DesktopMeetingShellChrome.compactRailStopLabel)
            .accessibilityIdentifier("desktop-meeting-shell-stop-recording-button")
        } else {
            Button(action: onStartRecording) {
                Image(systemName: recordingTransitionInProgress ? "clock" : "record.circle.fill")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(
                        width: DesktopMeetingShellChrome.compactRailActionHitSize,
                        height: DesktopMeetingShellChrome.compactRailActionHitSize
                    )
                    .background(
                        RoundedRectangle(cornerRadius: 9, style: .continuous)
                            .fill(DesktopMeetingShellChrome.webButtonPrimaryColor)
                    )
            }
            .buttonStyle(.plain)
            .contentShape(Rectangle())
            .disabled(!startRecordingAvailable || recordingTransitionInProgress)
            .keyboardShortcut("r", modifiers: [.command, .shift])
            .help(DesktopMeetingShellChrome.compactRailStartLabel)
            .accessibilityLabel(DesktopMeetingShellChrome.compactRailStartLabel)
            .accessibilityIdentifier("desktop-meeting-shell-start-recording-button")
        }
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
        VStack(spacing: 0) {
            inspectorDisclosureHeader(isExpanded: true)

            ScrollView(.vertical, showsIndicators: true) {
                VStack(alignment: .leading, spacing: DesktopMeetingShellChrome.spacingMedium) {
                    HStack(alignment: .center) {
                        Text("Запись")
                            .font(.system(size: 15, weight: .semibold))
                        Spacer()
                        Button(action: onOpenSettings) {
                            Label(DesktopMeetingShellChrome.settingsRailLabel, systemImage: "gearshape")
                                .labelStyle(.iconOnly)
                        }
                        .buttonStyle(.borderless)
                        .frame(
                            minWidth: DesktopMeetingShellChrome.controlHeight,
                            minHeight: DesktopMeetingShellChrome.controlHeight
                        )
                        .help(DesktopMeetingShellChrome.settingsRailLabel)
                        .accessibilityLabel(DesktopMeetingShellChrome.settingsRailLabel)
                        .accessibilityIdentifier("desktop-meeting-shell-expanded-settings-button")
                    }

                    captureControls
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(shellStrokeColor, lineWidth: 1)
                        )

                    if attentionCustodyItemCount > 0 {
                        custodyDetailsDisclosure
                    }
                }
                .padding(DesktopMeetingShellChrome.spacingLarge)
                .frame(maxWidth: .infinity, alignment: .topLeading)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(DesktopMeetingShellChrome.shellRailColor)
    }

    private func inspectorDisclosureHeader(isExpanded: Bool) -> some View {
        HStack(spacing: 0) {
            Spacer(minLength: 0)
            InspectorDisclosureButton(isExpanded: isExpanded) {
                toggleInspector()
            }
            .accessibilityIdentifier("desktop-meeting-shell-inspector-toggle")
        }
        .frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.inspectorToggleHitSize, alignment: .trailing)
        .padding(.top, DesktopMeetingShellChrome.inspectorToggleTopInset)
        .padding(.trailing, DesktopMeetingShellChrome.inspectorToggleTrailingInset)
    }

    private var custodyDetailsDisclosure: some View {
        DisclosureGroup {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(attentionCustodySummaries, id: \.stableIdentity) { summary in
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
                onSubmit: onSupportIncidentReport,
                onSync: onSupportIncidentSync,
                onCopyReport: onCopySupportIncidentReport,
                onOpenSignIn: onOpenSupportSignIn
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
            return DesktopMeetingShellChrome.shellAccentColor
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
            hasActionableProblem: hasInspectorAttention && !attentionExpansionDismissed
        )
    }

    private var hasInspectorAttention: Bool {
        hasActionableCaptureProblem || attentionCustodyItemCount > 0
    }

    private func toggleInspector() {
        if expandedInspectorVisible {
            inspectorExpanded = false
            attentionExpansionDismissed = hasInspectorAttention
        } else {
            attentionExpansionDismissed = false
            inspectorExpanded = true
        }
    }

    private var recordingStripSession: CaptureSession? {
        guard let session, CaptureStatusItem.showsStopButton(for: session) else {
            return nil
        }
        return session
    }

    private var captureStatusText: String {
        if let session {
            return CaptureStatusItem.statusLabel(for: session)
        }
        return hasInspectorAttention ? "Требуется внимание" : "Готово к записи"
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

    private var shellStrokeColor: Color {
        colorSchemeContrast == .increased
            ? DesktopMeetingShellChrome.shellHighContrastStrokeColor
            : DesktopMeetingShellChrome.shellStrokeColor
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
                tileDetail: "Записи остаются на этом Mac",
                systemImage: "wifi.slash",
                tone: .warning
            )
        }

        switch cabinetState {
        case .ready:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Сервер доступен",
                tileDetail: "Вход выполнен",
                systemImage: "checkmark.circle",
                tone: .success
            )
        case .loading:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Проверяем сервер",
                tileDetail: "Подключаемся…",
                systemImage: "clock",
                tone: .neutral
            )
        case .offline, .timeout:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Сервер недоступен",
                tileDetail: "Записи остаются на этом Mac",
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
        case .workspaceReselectionRequired:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Нужно выбрать пространство",
                tileDetail: "Войдите снова, чтобы продолжить",
                systemImage: "person.crop.circle.badge.xmark",
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
                tileTitle: "Кабинет не открылся",
                tileDetail: "Откройте GRAF в браузере",
                systemImage: "hand.raised",
                tone: .warning
            )
        case .notConfigured:
            return DesktopMeetingShellCabinetStatusPresentation(
                tileTitle: "Локальный режим",
                tileDetail: "Записи остаются на этом Mac",
                systemImage: "wifi.slash",
                tone: .warning
            )
        }
    }
}

private struct RecordingTitlebarAccessory: NSViewRepresentable {
    let session: CaptureSession?
    let transitionInProgress: Bool
    let onStop: () -> Void
    let onPause: () -> Void
    let onResume: () -> Void

    func makeNSView(context _: Context) -> RecordingTitlebarAccessoryAnchor {
        RecordingTitlebarAccessoryAnchor()
    }

    func updateNSView(_ nsView: RecordingTitlebarAccessoryAnchor, context _: Context) {
        nsView.update(
            session: session,
            transitionInProgress: transitionInProgress,
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
    private var transitionInProgress = false
    private var onStop: () -> Void = {}
    private var onPause: () -> Void = {}
    private var onResume: () -> Void = {}
    private weak var installedWindow: NSWindow?
    private var accessoryController: NSTitlebarAccessoryViewController?
    private var hostingView: NSHostingView<AnyView>?

    func update(
        session: CaptureSession?,
        transitionInProgress: Bool,
        onStop: @escaping () -> Void,
        onPause: @escaping () -> Void,
        onResume: @escaping () -> Void
    ) {
        self.session = session
        self.transitionInProgress = transitionInProgress
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
            transitionInProgress: transitionInProgress,
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
    let transitionInProgress: Bool
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
                    Text(CaptureStatusItem.statusLabel(for: session))
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .lineLimit(1)

                    if let sourceLabel = CaptureStatusItem.sourceIndicatorLabel(for: session) {
                        Text(sourceLabel)
                            .font(.system(size: 10.5, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.white.opacity(0.62))
                            .lineLimit(1)
                            .truncationMode(.tail)
                            .frame(minWidth: 0, maxWidth: 180, alignment: .leading)
                            .accessibilityLabel(
                                CaptureStatusItem.sourceAccessibilityLabel(for: session) ?? sourceLabel
                            )
                            .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordingSource)
                            .help(CaptureStatusItem.sourceAccessibilityLabel(for: session) ?? sourceLabel)
                    }
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
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                    .shadow(color: Color.black.opacity(0.2), radius: 4, x: 0, y: 2)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
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
        .accessibilityLabel("\(CaptureStatusItem.statusLabel(for: session)). Остановить запись можно в любой момент.")
        .accessibilityIdentifier("systemAudio.titlebarRecordingHUD")
    }

    @ViewBuilder
    private var controls: some View {
        if CaptureStatusItem.showsPauseButton(for: session) {
            Button(action: onPause) {
                Label(SystemAudioStatusLabels.pauseButtonTitle, systemImage: "pause.fill")
            }
            .buttonStyle(DesktopWebButtonStyle(.secondary))
            .disabled(!session.stopActionAvailable || transitionInProgress)
            .accessibilityLabel(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
            .help(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
        } else if CaptureStatusItem.showsResumeButton(for: session) {
            Button(action: onResume) {
                Label(SystemAudioStatusLabels.resumeButtonTitle, systemImage: "play.fill")
            }
            .buttonStyle(DesktopWebButtonStyle(.secondary))
            .disabled(!session.stopActionAvailable || transitionInProgress)
            .accessibilityLabel(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
            .help(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
        }

        if CaptureStatusItem.showsStopButton(for: session) {
            Button(role: .destructive, action: onStop) {
                Label("Стоп", systemImage: "stop.fill")
            }
            .buttonStyle(DesktopWebButtonStyle(.destructive))
            .disabled(!session.stopActionAvailable || transitionInProgress)
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
    @Environment(\.accessibilityReduceMotion) private var accessibilityReduceMotion

    var body: some View {
        Button(action: action) {
            Image(systemName: DesktopMeetingShellChrome.inspectorToggleSymbol(isExpanded: isExpanded))
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
            isHovering = hovering
        }
        .animation(accessibilityReduceMotion ? nil : .easeOut(duration: 0.12), value: isHovering)
        .help(DesktopMeetingShellChrome.inspectorToggleLabel(isExpanded: isExpanded))
        .accessibilityLabel(DesktopMeetingShellChrome.inspectorToggleLabel(isExpanded: isExpanded))
        .accessibilityHint(DesktopMeetingShellChrome.inspectorToggleHint(isExpanded: isExpanded))
    }
}
