import SwiftUI
import TwoBrainRecShared

public struct CaptureControlView: View {
    private let session: CaptureSession?
    private let blockedReason: String?
    private let localRecordingStatus: String?
    private let muteTruthWarning: String?
    private let recordingMicrophoneSelection: RecordingMicrophoneSelection?
    private let recordingMicrophoneInputs: [PhysicalAudioDevice]
    private let selectedRecordingMicrophoneDeviceId: String?
    private let calendarPrompt: DesktopCalendarPrompt?
    private let meetingDetectionStatus: String?
    private let recordingLevels: LiveRecordingLevels
    private let recordDisabled: Bool
    private let stopDisabled: Bool
    private let pauseDisabled: Bool
    private let onRecord: () -> Void
    private let onStop: () -> Void
    private let onPause: () -> Void
    private let onResume: () -> Void
    private let onSelectRecordingMicrophone: (String?) -> Void
    private let onCalendarPromptPrimary: (DesktopCalendarPrompt) -> Void
    private let onCalendarPromptDismiss: (DesktopCalendarPrompt) -> Void
    private let onMeetingDetectionSettings: () -> Void
    @Environment(\.colorSchemeContrast) private var colorSchemeContrast

    public init(
        session: CaptureSession?,
        blockedReason: String? = nil,
        localRecordingStatus: String? = nil,
        muteTruthWarning: String? = nil,
        recordingMicrophoneSelection: RecordingMicrophoneSelection? = nil,
        recordingMicrophoneInputs: [PhysicalAudioDevice] = [],
        selectedRecordingMicrophoneDeviceId: String? = nil,
        calendarPrompt: DesktopCalendarPrompt? = nil,
        meetingDetectionStatus: String? = nil,
        recordingLevels: LiveRecordingLevels = .inactive,
        recordDisabled: Bool = false,
        stopDisabled: Bool = false,
        pauseDisabled: Bool = false,
        onRecord: @escaping () -> Void,
        onStop: @escaping () -> Void,
        onPause: @escaping () -> Void = {},
        onResume: @escaping () -> Void = {},
        onSelectRecordingMicrophone: @escaping (String?) -> Void = { _ in },
        onCalendarPromptPrimary: @escaping (DesktopCalendarPrompt) -> Void = { _ in },
        onCalendarPromptDismiss: @escaping (DesktopCalendarPrompt) -> Void = { _ in },
        onMeetingDetectionSettings: @escaping () -> Void = {}
    ) {
        self.session = session
        self.blockedReason = blockedReason
        self.localRecordingStatus = localRecordingStatus
        self.muteTruthWarning = muteTruthWarning
        self.recordingMicrophoneSelection = recordingMicrophoneSelection
        self.recordingMicrophoneInputs = recordingMicrophoneInputs
        self.selectedRecordingMicrophoneDeviceId = selectedRecordingMicrophoneDeviceId
        self.calendarPrompt = calendarPrompt
        self.meetingDetectionStatus = meetingDetectionStatus
        self.recordingLevels = recordingLevels
        self.recordDisabled = recordDisabled
        self.stopDisabled = stopDisabled
        self.pauseDisabled = pauseDisabled
        self.onRecord = onRecord
        self.onStop = onStop
        self.onPause = onPause
        self.onResume = onResume
        self.onSelectRecordingMicrophone = onSelectRecordingMicrophone
        self.onCalendarPromptPrimary = onCalendarPromptPrimary
        self.onCalendarPromptDismiss = onCalendarPromptDismiss
        self.onMeetingDetectionSettings = onMeetingDetectionSettings
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: DesktopMeetingShellChrome.spacingMedium) {
            VStack(alignment: .leading, spacing: DesktopMeetingShellChrome.spacingMedium) {
                if let session, Self.shouldShowSessionStatus(for: session, blockedReason: blockedReason) {
                    CaptureStatusItem(
                        session: session,
                        stopDisabled: stopDisabled,
                        pauseDisabled: pauseDisabled,
                        onStop: onStop,
                        onPause: onPause,
                        onResume: onResume
                    )
                } else if session == nil && Self.shouldShowIdleStatus(
                    blockedReason: blockedReason,
                    localRecordingStatus: localRecordingStatus,
                    calendarPrompt: calendarPrompt
                ) {
                    Label(
                        Self.primaryStatus(
                            for: session,
                            blockedReason: blockedReason,
                            localRecordingStatus: localRecordingStatus
                        ),
                        systemImage: Self.hasActionableProblem(blockedReason: blockedReason)
                            ? "exclamationmark.triangle.fill"
                            : "record.circle"
                    )
                        .font(.caption)
                        .foregroundStyle(
                            Self.hasActionableProblem(blockedReason: blockedReason)
                                ? Color.orange
                                : secondaryTextColor
                        )
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }

                if Self.shouldShowDirectRecordButton(for: session, calendarPrompt: calendarPrompt) {
                    Button(action: onRecord) {
                        Label(SystemAudioStatusLabels.recordButtonTitle, systemImage: "record.circle")
                            .lineLimit(1)
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.controlHeight)
                    .disabled(!Self.shouldEnableRecordButton(for: session, recordDisabled: recordDisabled))
                    .keyboardShortcut("r", modifiers: [.command, .shift])
                    .accessibilityLabel(SystemAudioStatusLabels.recordButtonAccessibilityLabel)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordButton)
                    .help(SystemAudioStatusLabels.recordButtonAccessibilityLabel)
                }
            }

            if let blockedReason, !blockedReason.isEmpty {
                StatusNoteView(
                    icon: "exclamationmark.triangle.fill",
                    title: Self.primaryStatus(
                        for: session,
                        blockedReason: blockedReason,
                        localRecordingStatus: localRecordingStatus
                    ),
                    detail: blockedReason,
                    iconColor: .orange
                )
                    .accessibilityLabel(blockedReason)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.blockerBanner)
            }

            if let calendarPrompt {
                CalendarPromptView(
                    prompt: calendarPrompt,
                    onPrimary: onCalendarPromptPrimary,
                    onDismiss: onCalendarPromptDismiss
                )
            }

            if calendarPrompt == nil,
               let meetingDetectionSummary = Self.meetingDetectionSummary(for: meetingDetectionStatus) {
                HStack(alignment: .top, spacing: 10) {
                    StatusNoteView(
                        icon: "dot.radiowaves.left.and.right",
                        title: meetingDetectionSummary,
                        detail: "Настройте, когда GRAF должен предлагать запись.",
                        iconColor: secondaryTextColor
                    )
                    .accessibilityLabel(meetingDetectionSummary)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meetingDetectionStatus)

                    Button(action: onMeetingDetectionSettings) {
                        Image(systemName: "gearshape")
                            .frame(width: 18, height: 18)
                    }
                    .buttonStyle(.borderless)
                    .accessibilityLabel(SystemAudioStatusLabels.meetingDetectionSettingsTitle)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meetingDetectionSettingsButton)
                    .help(SystemAudioStatusLabels.meetingDetectionSettingsTitle)
                }
            }

            if !recordingMicrophoneInputs.isEmpty || recordingMicrophoneSelection != nil {
                DisclosureGroup {
                    HStack(alignment: .firstTextBaseline, spacing: 10) {
                        Menu {
                            Button("По умолчанию macOS") {
                                onSelectRecordingMicrophone(nil)
                            }
                            ForEach(recordingMicrophoneInputs, id: \.id) { input in
                                Button(input.displayName) {
                                    onSelectRecordingMicrophone(input.id)
                                }
                            }
                        } label: {
                            Label(recordingMicrophoneMenuTitle, systemImage: "mic")
                        }
                        .menuStyle(.borderlessButton)
                        .accessibilityLabel(SystemAudioStatusLabels.recordingMicrophoneMenuAccessibilityLabel)
                        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordingMicrophoneMenu)

                        if let status = Self.recordingMicrophoneStatus(for: recordingMicrophoneSelection) {
                            Text(status)
                                .font(.caption2)
                                .foregroundStyle(secondaryTextColor)
                                .lineLimit(2)
                                .fixedSize(horizontal: false, vertical: true)
                                .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordingMicrophoneStatus)
                        }
                    }
                    .padding(.top, 8)
                } label: {
                    Label("Микрофон", systemImage: "mic")
                        .font(.caption.weight(.semibold))
                }
            }

            if let recoveryCopy = Self.recordingMicrophoneRecoveryCopy(for: recordingMicrophoneSelection) {
                Label(recoveryCopy, systemImage: "mic.badge.xmark")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordingMicrophoneRecovery)
            }

            if let localRecordingStatus,
               Self.shouldShowLocalRecordingStatus(localRecordingStatus, for: session) {
                StatusNoteView(
                    icon: localRecordingStatusIcon,
                    title: Self.localRecordingSummary(for: localRecordingStatus),
                    detail: localRecordingStatusDetail,
                    iconColor: localRecordingStatusStyle
                )
                    .accessibilityLabel(localRecordingStatus)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.localRecordingStatus)
            }

            if let muteTruthWarning, !muteTruthWarning.isEmpty {
                StatusNoteView(
                    icon: "shield.lefthalf.filled.badge.checkmark",
                    title: "Не удалось проверить микрофон во встрече",
                    detail: muteTruthWarning,
                    iconColor: secondaryTextColor
                )
                    .accessibilityLabel(muteTruthWarning)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.muteTruthWarning)
            }

            if Self.shouldShowMeters(for: recordingLevels) {
                Divider()

                LiveRecordingMetersView(
                    recordingLevels: recordingLevels
                )
            }
        }
        .padding(DesktopMeetingShellChrome.spacingLarge)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(SystemAudioStatusLabels.captureRegion)
        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.captureControls)
    }

    public static func shouldShowRecordButton(for session: CaptureSession?) -> Bool {
        guard let session else { return true }
        return !CaptureStatusItem.showsStopButton(for: session)
    }

    public static func shouldEnableRecordButton(
        for session: CaptureSession?,
        recordDisabled: Bool
    ) -> Bool {
        shouldShowRecordButton(for: session) && !recordDisabled
    }

    public static func shouldShowDirectRecordButton(
        for session: CaptureSession?,
        calendarPrompt: DesktopCalendarPrompt?
    ) -> Bool {
        shouldShowRecordButton(for: session) && calendarPrompt?.kind != .record
    }

    public static func hasActionableProblem(blockedReason: String?) -> Bool {
        guard let blockedReason else { return false }
        return !blockedReason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    public static func shouldShowSessionStatus(
        for session: CaptureSession,
        blockedReason: String?
    ) -> Bool {
        CaptureStatusItem.showsStopButton(for: session) ||
            !hasActionableProblem(blockedReason: blockedReason)
    }

    public static func shouldShowIdleStatus(
        blockedReason: String?,
        localRecordingStatus: String?,
        calendarPrompt: DesktopCalendarPrompt?
    ) -> Bool {
        guard !hasActionableProblem(blockedReason: blockedReason) else { return false }
        guard calendarPrompt?.kind != .record else { return false }
        return localRecordingStatus?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true
    }

    public static func shouldShowLocalRecordingStatus(
        _ localRecordingStatus: String,
        for session: CaptureSession?
    ) -> Bool {
        let normalized = localRecordingStatus.lowercased()
        let carriesActionableDetail = ["огранич", "заблок", "не сохран", "degraded", "blocked", "failed"]
            .contains { normalized.contains($0) }
        if carriesActionableDetail {
            return true
        }
        guard let session else { return true }
        return localRecordingSummary(for: localRecordingStatus) != captureStatus(for: session.state)
    }

    public static func primaryStatus(
        for session: CaptureSession?,
        blockedReason: String?,
        localRecordingStatus: String?
    ) -> String {
        if let session, CaptureStatusItem.showsStopButton(for: session) {
            return captureStatus(for: session.state)
        }
        if hasActionableProblem(blockedReason: blockedReason) {
            let normalized = blockedReason?.lowercased() ?? ""
            if normalized.contains("разреш") || normalized.contains("доступ") {
                return "Нужно разрешение"
            }
            return "Нужна помощь"
        }
        if let localRecordingStatus, !localRecordingStatus.isEmpty {
            return localRecordingSummary(for: localRecordingStatus)
        }
        guard let session else {
            return "Готово к записи"
        }
        return captureStatus(for: session.state)
    }

    public static func meetingDetectionSummary(for status: String?) -> String? {
        guard let status else { return nil }
        let normalized = status.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty else { return nil }
        if normalized.contains("Найдена встреча") || normalized.contains("Найден кандидат") {
            return "Встреча обнаружена"
        }
        if normalized.contains("Запрашивать запись включено") {
            return "Автоопределение: спрашивать"
        }
        if normalized.contains("Запрос записи отключен") {
            return "Автоопределение выключено"
        }
        if normalized.contains("Автозапись") {
            return "Автоопределение: включено"
        }
        if normalized == "Недоступно" {
            return "Автоопределение недоступно"
        }
        return "Автоопределение: включено"
    }

    public static func localRecordingSummary(for status: String) -> String {
        let normalized = status.lowercased()
        if normalized.contains("не сохран") || normalized.contains("заблок") {
            return "Нужна помощь"
        }
        if normalized.contains("сохран") {
            return "Сохранено на Mac"
        }
        if normalized.contains("пауз") {
            return "Запись на паузе"
        }
        if normalized.contains("идет") || normalized.contains("идёт") {
            return "Идёт запись"
        }
        return status
    }

    public static func shouldShowMeters(for recordingLevels: LiveRecordingLevels) -> Bool {
        recordingLevels.isRecording
    }

    private static func captureStatus(for state: CaptureSessionState) -> String {
        switch state {
        case .idle, .ready:
            return "Готово к записи"
        case .detecting:
            return "Проверяем готовность"
        case .starting:
            return "Начинаем запись…"
        case .active:
            return "Идёт запись"
        case .paused:
            return "Запись на паузе"
        case .degraded:
            return "Запись с ограничением"
        case .stopping:
            return "Сохраняем запись…"
        case .stopped, .finalized:
            return "Сохранено на Mac"
        case .failed:
            return "Нужна помощь"
        }
    }

    public static func recordingMicrophoneStatus(
        for selection: RecordingMicrophoneSelection?
    ) -> String? {
        guard let selection else { return nil }
        let name = selection.inputDisplayName?.trimmingCharacters(in: .whitespacesAndNewlines)
        let displayName = (name?.isEmpty == false ? name : nil) ?? "текущий микрофон macOS"

        switch selection.selectionResult {
        case .accepted:
            if selection.mode == .macOSDefaultFallback {
                return "Микрофон записи: \(displayName) (по умолчанию macOS)"
            }
            return "Микрофон записи: \(displayName)"
        case .rejected:
            return "Микрофон записи не подходит: \(displayName)"
        case .unavailable:
            return "Микрофон записи недоступен: \(displayName)"
        }
    }

    public static func recordingMicrophoneRecoveryCopy(
        for selection: RecordingMicrophoneSelection?
    ) -> String? {
        guard let selection else { return nil }
        switch selection.rejectionReason {
        case .unsupportedVirtualInput:
            return "Выберите встроенный, USB, проводной или Bluetooth-микрофон для записи."
        case .deviceUnavailable:
            return "Выбранный микрофон недоступен. Подключите его снова или выберите другой вход."
        case .inputIdentityUnproven:
            return "Не удалось надежно определить микрофон записи. Выберите другой вход."
        case .none:
            return nil
        }
    }

    private var recordingMicrophoneMenuTitle: String {
        if let selectedRecordingMicrophoneDeviceId,
           let input = recordingMicrophoneInputs.first(where: { $0.id == selectedRecordingMicrophoneDeviceId }) {
            return input.displayName
        }
        return "По умолчанию macOS"
    }

    private var secondaryTextColor: Color {
        colorSchemeContrast == .increased ? Color.primary.opacity(0.82) : Color.secondary
    }

    private var localRecordingStatusIcon: String {
        guard let localRecordingStatus else { return "waveform.path.badge.plus" }
        if localRecordingStatus.localizedCaseInsensitiveContains("blocked") ||
            localRecordingStatus.localizedCaseInsensitiveContains("permission") ||
            localRecordingStatus.localizedCaseInsensitiveContains("заблок") ||
            localRecordingStatus.localizedCaseInsensitiveContains("не сохран") {
            return "lock.trianglebadge.exclamationmark"
        }
        if localRecordingStatus.localizedCaseInsensitiveContains("degraded") ||
            localRecordingStatus.localizedCaseInsensitiveContains("огранич") {
            return "exclamationmark.triangle.fill"
        }
        return "waveform.path.badge.plus"
    }

    private var localRecordingStatusStyle: Color {
        guard let localRecordingStatus else { return .secondary }
        if localRecordingStatus.localizedCaseInsensitiveContains("blocked") ||
            localRecordingStatus.localizedCaseInsensitiveContains("permission") ||
            localRecordingStatus.localizedCaseInsensitiveContains("degraded") ||
            localRecordingStatus.localizedCaseInsensitiveContains("заблок") ||
            localRecordingStatus.localizedCaseInsensitiveContains("не сохран") ||
            localRecordingStatus.localizedCaseInsensitiveContains("огранич") {
            return .orange
        }
        return .secondary
    }

    private var localRecordingStatusTitle: String {
        guard let localRecordingStatus else { return "Локальная запись" }
        if localRecordingStatus.localizedCaseInsensitiveContains("огранич") ||
            localRecordingStatus.localizedCaseInsensitiveContains("degraded") {
            return "Локальная копия сохранена"
        }
        if localRecordingStatus.localizedCaseInsensitiveContains("заблок") ||
            localRecordingStatus.localizedCaseInsensitiveContains("blocked") {
            return "Запись требует внимания"
        }
        if localRecordingStatus.localizedCaseInsensitiveContains("не сохран") {
            return "Локальная копия не сохранена"
        }
        return localRecordingStatus
    }

    private var localRecordingStatusDetail: String? {
        guard let localRecordingStatus else { return nil }
        if localRecordingStatus.localizedCaseInsensitiveContains("огранич") ||
            localRecordingStatus.localizedCaseInsensitiveContains("degraded") {
            return "Есть ограничения проверки"
        }
        if localRecordingStatus == localRecordingStatusTitle {
            return nil
        }
        return localRecordingStatus
    }

}

private struct CalendarPromptView: View {
    let prompt: DesktopCalendarPrompt
    let onPrimary: (DesktopCalendarPrompt) -> Void
    let onDismiss: (DesktopCalendarPrompt) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            StatusNoteView(
                icon: prompt.kind == .join ? "video.fill" : "record.circle",
                title: prompt.title,
                detail: prompt.message,
                iconColor: prompt.kind == .join ? .blue : .orange
            )

            VStack(alignment: .leading, spacing: 8) {
                if prompt.choices.isEmpty {
                    Button {
                        onPrimary(prompt)
                    } label: {
                        Label(prompt.primaryActionTitle, systemImage: prompt.kind == .join ? "arrow.up.right.square" : "record.circle")
                    }
                    .font(.caption)
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .accessibilityLabel(prompt.primaryActionTitle)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.calendarPromptPrimaryButton)
                } else {
                    ForEach(prompt.choices) { choice in
                        Button {
                            var selectedPrompt = prompt
                            selectedPrompt.eventId = choice.eventId
                            selectedPrompt.openMeetingURL = choice.openMeetingURL
                            onPrimary(selectedPrompt)
                        } label: {
                            Label(
                                choice.title,
                                systemImage: prompt.kind == .join ? "arrow.up.right.square" : choice.eventId == nil ? "record.circle" : "calendar"
                            )
                        }
                        .font(.caption)
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .accessibilityLabel(choice.title)
                    }
                }

                Button {
                    onDismiss(prompt)
                } label: {
                    Label(prompt.dismissActionTitle, systemImage: "xmark")
                }
                .font(.caption)
                .buttonStyle(.bordered)
                .controlSize(.small)
                .accessibilityLabel(prompt.dismissActionTitle)
                .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.calendarPromptDismissButton)
            }
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.accentColor.opacity(0.18), lineWidth: 1)
        )
        .accessibilityElement(children: .contain)
        .accessibilityLabel(prompt.accessibilityLabel)
        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.calendarPrompt)
    }
}

private struct StatusNoteView: View {
    let icon: String
    let title: String
    let detail: String?
    let iconColor: Color

    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            Image(systemName: icon)
                .font(.caption)
                .foregroundStyle(iconColor)
                .frame(width: 16)
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                if let detail, !detail.isEmpty {
                    Text(detail)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .accessibilityElement(children: .combine)
    }
}

private struct LiveRecordingMetersView: View {
    let recordingLevels: LiveRecordingLevels
    private var now: Date { Date() }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(SystemAudioStatusLabels.captureAudioTitle)
                        .font(.headline)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                    Text(liveSummary)
                        .font(.caption)
                        .foregroundStyle(summaryColor)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer()
                Image(systemName: incomingIsLive ? "waveform.circle.fill" : "waveform.circle")
                    .font(.title3)
                    .foregroundStyle(summaryColor)
            }

            VStack(alignment: .leading, spacing: 12) {
                meterRow(
                    title: SystemAudioStatusLabels.microphoneTitle,
                    detail: microphoneDetail,
                    icon: "mic.fill",
                    level: microphoneLevel,
                    isLive: microphoneIsLive,
                    warning: shouldWarnMicrophone
                )
                .frame(maxWidth: .infinity, alignment: .leading)

                meterRow(
                    title: SystemAudioStatusLabels.incomingTitle,
                    detail: incomingDetail,
                    icon: "speaker.wave.2.fill",
                    level: incomingLevel,
                    isLive: incomingIsLive,
                    warning: shouldWarnIncoming
                )
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meters)
    }

    private var liveSummary: String {
        SystemAudioStatusLabels.liveSummary(
            recordingIsActive: recordingLevels.isRecording,
            microphoneIsLive: microphoneIsLive,
            incomingIsLive: incomingIsLive
        )
    }

    private var summaryColor: Color {
        if incomingIsLive && microphoneIsLive {
            return .green
        }
        if shouldWarnIncoming {
            return .orange
        }
        return .secondary
    }

    private var microphoneDetail: String {
        SystemAudioStatusLabels.microphoneDetail(
            recordingIsActive: recordingLevels.isRecording,
            microphoneIsLive: microphoneIsLive
        )
    }

    private var incomingDetail: String {
        SystemAudioStatusLabels.incomingDetail(
            recordingIsActive: recordingLevels.isRecording,
            incomingIsLive: incomingIsLive
        )
    }

    private var microphoneLevel: Double {
        recordingLevels.microphoneLevel
    }

    private var incomingLevel: Double {
        recordingLevels.incomingLevel
    }

    private var microphoneIsLive: Bool {
        recordingLevels.microphoneIsLive(
            now: now,
            staleAfter: SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds
        )
    }

    private var incomingIsLive: Bool {
        recordingLevels.incomingIsLive(
            now: now,
            staleAfter: SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds
        )
    }

    private var shouldWarnIncoming: Bool {
        recordingLevels.isRecording && !incomingIsLive
    }

    private var shouldWarnMicrophone: Bool {
        recordingLevels.isRecording && !microphoneIsLive
    }

    private func meterRow(
        title: String,
        detail: String,
        icon: String,
        level: Double,
        isLive: Bool,
        warning: Bool
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(warning ? .orange : (isLive ? .green : .secondary))
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .center, spacing: 8) {
                    Text(title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                    Text(SystemAudioStatusLabels.meterState(isLive: isLive))
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundStyle(warning ? .orange : (isLive ? .green : .secondary))
                        .lineLimit(1)
                    Spacer(minLength: 4)
                    EqualizerBars(level: level, isLive: isLive, warning: warning)
                }
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(warning ? .orange : .secondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .layoutPriority(1)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(SystemAudioStatusLabels.meterAccessibilityLabel(title: title, detail: detail))
        .accessibilityIdentifier(
            title == SystemAudioStatusLabels.microphoneTitle
                ? SystemAudioAccessibilityIdentifier.microphoneMeter
                : SystemAudioAccessibilityIdentifier.incomingMeter
        )
    }
}

private struct EqualizerBars: View {
    let level: Double
    let isLive: Bool
    let warning: Bool

    private let bars = 10

    var body: some View {
        HStack(alignment: .bottom, spacing: 3) {
            ForEach(0..<bars, id: \.self) { index in
                RoundedRectangle(cornerRadius: 2)
                    .fill(color(for: index))
                    .frame(width: 6, height: height(for: index))
            }
        }
        .frame(width: 87, height: 22, alignment: .bottom)
        .animation(.linear(duration: 0.05), value: level)
        .animation(.linear(duration: 0.05), value: isLive)
        .accessibilityHidden(true)
    }

    private func height(for index: Int) -> CGFloat {
        let base = CGFloat(4 + (index % 3))
        guard isLive else { return base }
        let displayLevel = min(1, pow(max(level, 0) * 7, 0.72))
        let activeBars = max(1, Int((displayLevel * Double(bars)).rounded(.up)))
        guard index < activeBars else { return base }
        let shape = CGFloat([0.42, 0.7, 1.0, 0.56, 0.84][index % 5])
        return 6 + CGFloat(displayLevel) * 17 * shape
    }

    private func color(for index: Int) -> Color {
        guard isLive else {
            return warning ? .orange.opacity(0.28) : .secondary.opacity(0.22)
        }
        let displayLevel = min(1, pow(max(level, 0) * 7, 0.72))
        if index < max(1, Int((displayLevel * Double(bars)).rounded(.up))) {
            return warning ? .orange : .green
        }
        return .secondary.opacity(0.18)
    }
}
