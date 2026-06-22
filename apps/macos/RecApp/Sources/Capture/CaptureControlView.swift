import SwiftUI
import TwoBrainRecShared

public struct CaptureControlView: View {
    public static let uploadReviewButtonTitle = "Открыть обзор"

    private let session: CaptureSession?
    private let blockedReason: String?
    private let localRecordingStatus: String?
    private let localRecordingLocation: String?
    private let muteTruthWarning: String?
    private let appleProcessingStatus: String?
    private let recordingMicrophoneSelection: RecordingMicrophoneSelection?
    private let recordingMicrophoneInputs: [PhysicalAudioDevice]
    private let selectedRecordingMicrophoneDeviceId: String?
    private let uploadQueueItems: [DesktopUploadQueueItem]
    private let cabinetConfiguration: DesktopCabinetConfiguration?
    private let routeSignalLevels: LiveRouteSignalLevels
    private let recordDisabled: Bool
    private let stopDisabled: Bool
    private let pauseDisabled: Bool
    private let onRecord: () -> Void
    private let onStop: () -> Void
    private let onPause: () -> Void
    private let onResume: () -> Void
    private let onSelectRecordingMicrophone: (String?) -> Void
    private let onUploadRetry: (String) -> Void
    private let onUploadStopRetry: (String) -> Void
    private let onUploadReview: (URL) -> Void

    public init(
        session: CaptureSession?,
        blockedReason: String? = nil,
        localRecordingStatus: String? = nil,
        localRecordingLocation: String? = nil,
        muteTruthWarning: String? = nil,
        appleProcessingStatus: String? = nil,
        recordingMicrophoneSelection: RecordingMicrophoneSelection? = nil,
        recordingMicrophoneInputs: [PhysicalAudioDevice] = [],
        selectedRecordingMicrophoneDeviceId: String? = nil,
        uploadQueueItems: [DesktopUploadQueueItem] = [],
        cabinetConfiguration: DesktopCabinetConfiguration? = nil,
        routeSignalLevels: LiveRouteSignalLevels = .inactive,
        recordDisabled: Bool = false,
        stopDisabled: Bool = false,
        pauseDisabled: Bool = false,
        onRecord: @escaping () -> Void,
        onStop: @escaping () -> Void,
        onPause: @escaping () -> Void = {},
        onResume: @escaping () -> Void = {},
        onSelectRecordingMicrophone: @escaping (String?) -> Void = { _ in },
        onUploadRetry: @escaping (String) -> Void = { _ in },
        onUploadStopRetry: @escaping (String) -> Void = { _ in },
        onUploadReview: @escaping (URL) -> Void = { _ in }
    ) {
        self.session = session
        self.blockedReason = blockedReason
        self.localRecordingStatus = localRecordingStatus
        self.localRecordingLocation = localRecordingLocation
        self.muteTruthWarning = muteTruthWarning
        self.appleProcessingStatus = appleProcessingStatus
        self.recordingMicrophoneSelection = recordingMicrophoneSelection
        self.recordingMicrophoneInputs = recordingMicrophoneInputs
        self.selectedRecordingMicrophoneDeviceId = selectedRecordingMicrophoneDeviceId
        self.uploadQueueItems = uploadQueueItems
        self.cabinetConfiguration = cabinetConfiguration
        self.routeSignalLevels = routeSignalLevels
        self.recordDisabled = recordDisabled
        self.stopDisabled = stopDisabled
        self.pauseDisabled = pauseDisabled
        self.onRecord = onRecord
        self.onStop = onStop
        self.onPause = onPause
        self.onResume = onResume
        self.onSelectRecordingMicrophone = onSelectRecordingMicrophone
        self.onUploadRetry = onUploadRetry
        self.onUploadStopRetry = onUploadStopRetry
        self.onUploadReview = onUploadReview
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .center, spacing: 12) {
                if let session {
                    CaptureStatusItem(
                        session: session,
                        stopDisabled: stopDisabled,
                        pauseDisabled: pauseDisabled,
                        onStop: onStop,
                        onPause: onPause,
                        onResume: onResume
                    )
                } else {
                    Label(SystemAudioStatusLabels.recordingIdle, systemImage: "record.circle")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }

                Spacer()

                if Self.shouldShowRecordButton(for: session) {
                    Button(action: onRecord) {
                        Label("Начать", systemImage: "record.circle")
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!Self.shouldEnableRecordButton(for: session, recordDisabled: recordDisabled))
                    .keyboardShortcut("r", modifiers: [.command, .shift])
                    .accessibilityLabel(SystemAudioStatusLabels.recordButtonAccessibilityLabel)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordButton)
                    .help(SystemAudioStatusLabels.recordButtonAccessibilityLabel)
                }
            }

            if let blockedReason, !blockedReason.isEmpty {
                Label(blockedReason, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityLabel(blockedReason)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.blockerBanner)
            }

            if !recordingMicrophoneInputs.isEmpty || recordingMicrophoneSelection != nil {
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
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                            .fixedSize(horizontal: false, vertical: true)
                            .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordingMicrophoneStatus)
                    }
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

            if let localRecordingStatus, !localRecordingStatus.isEmpty {
                StatusNoteView(
                    icon: localRecordingStatusIcon,
                    title: localRecordingStatusTitle,
                    detail: localRecordingStatusDetail,
                    iconColor: localRecordingStatusStyle
                )
                    .accessibilityLabel(localRecordingStatus)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.localRecordingStatus)
            }

            if let muteTruthWarning, !muteTruthWarning.isEmpty {
                StatusNoteView(
                    icon: "shield.lefthalf.filled.badge.checkmark",
                    title: "Mute встречи не подтвержден",
                    detail: muteTruthWarning,
                    iconColor: .secondary
                )
                    .accessibilityLabel(muteTruthWarning)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.muteTruthWarning)
            }

            if let appleProcessingStatus, !appleProcessingStatus.isEmpty {
                StatusNoteView(
                    icon: "waveform.and.mic",
                    title: "Apple voice processing",
                    detail: appleProcessingStatus,
                    iconColor: .secondary
                )
                .accessibilityLabel(appleProcessingStatus)
                .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.appleProcessingStatus)
            }

            if let localRecordingLocation, !localRecordingLocation.isEmpty {
                Text("Локальная копия сохранена")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .accessibilityLabel(SystemAudioStatusLabels.localRecordingLocationAccessibilityLabel(localRecordingLocation))
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.localRecordingLocation)
            }

            if let summary = Self.uploadSummary(for: uploadQueueItems) {
                UploadQueueStatusView(
                    summary: summary,
                    reviewLink: Self.uploadReviewLink(for: summary.primaryItem, configuration: cabinetConfiguration),
                    onRetry: onUploadRetry,
                    onStopRetry: onUploadStopRetry,
                    onReview: onUploadReview
                )
            }

            Divider()

            LiveRecordingMetersView(
                routeSignalLevels: routeSignalLevels
            )
        }
        .padding(16)
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

    public static func uploadSummary(for items: [DesktopUploadQueueItem]) -> DesktopUploadQueueSummary? {
        DesktopUploadQueueService.visibleSummary(for: items)
    }

    public static func uploadReviewLink(
        for item: DesktopUploadQueueItem,
        configuration: DesktopCabinetConfiguration?
    ) -> UploadReviewLink? {
        guard let configuration else { return nil }
        let link = configuration.reviewLink(for: item)
        return link.availability == .available ? link : nil
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
        case .unsupportedSelfRoutingInput:
            return "Выберите обычный микрофон. Виртуальные устройства 2brain нельзя использовать как микрофон записи."
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

    public static func appleProcessingStatusCopy(for outcome: AppleProcessingOutcome?) -> String? {
        guard let outcome else { return nil }
        switch outcome.primaryOutcome {
        case .acceptedForBuiltinSpeakerphone:
            return outcome.canClaimCleanBuiltinSpeakerphone
                ? "Apple проверка принята для встроенного маршрута; итог все равно подтверждается package evidence."
                : "Apple проверка требует полного набора evidence перед пользовательским обещанием."
        case .acceptedForGuidanceOnly:
            return "Apple evidence доступен только как подсказка; запись остается проверкой локального пакета."
        case .acceptedForHeadsetRoutesOnly:
            return "Apple evidence применим только к headset/wired маршрутам; speakerphone остается без нового обещания."
        case .blockedRouteTopology:
            return "Apple route topology заблокирован; продолжаем без повышения speakerphone-обещания."
        case .blockedQuality:
            return "Apple quality gate заблокирован; локальная запись остается с текущими ограничениями."
        case .blockedStability:
            return "Apple stability gate заблокирован; candidate отключен до новой проверки."
        case .deferToWebRTCAEC3:
            return "Apple evidence не доказал production route; следующий кандидат - WebRTC AEC3."
        }
    }

    private var recordingMicrophoneMenuTitle: String {
        if let selectedRecordingMicrophoneDeviceId,
           let input = recordingMicrophoneInputs.first(where: { $0.id == selectedRecordingMicrophoneDeviceId }) {
            return input.displayName
        }
        return "По умолчанию macOS"
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
    }
}

private struct UploadQueueStatusView: View {
    let summary: DesktopUploadQueueSummary
    let reviewLink: UploadReviewLink?
    let onRetry: (String) -> Void
    let onStopRetry: (String) -> Void
    let onReview: (URL) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                HStack(spacing: 6) {
                    Image(systemName: iconName)
                        .foregroundStyle(statusColor)
                    Text(summary.title)
                        .foregroundStyle(.primary)
                }
                .font(.caption)
                .fontWeight(.semibold)
                .lineLimit(1)
                .minimumScaleFactor(0.85)
                Spacer()
                Text("\(Int((summary.primaryItem.progressFraction * 100).rounded()))%")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
            }

            ProgressView(value: summary.primaryItem.progressFraction)
                .progressViewStyle(.linear)

            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(summary.detail)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 8)
                if let destination = reviewLink?.destination {
                    Button {
                        onReview(destination)
                    } label: {
                        Label(CaptureControlView.uploadReviewButtonTitle, systemImage: "rectangle.stack")
                    }
                    .font(.caption)
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
                if let actionLabel = summary.primaryItem.nextActionLabel {
                    Button {
                        if summary.primaryItem.retryMode == .automatic {
                            onStopRetry(summary.primaryItem.id)
                        } else {
                            onRetry(summary.primaryItem.id)
                        }
                    } label: {
                        Label(actionLabel, systemImage: actionIcon(for: actionLabel))
                    }
                    .font(.caption)
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
            }
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(statusColor.opacity(0.18), lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Очередь загрузки: \(summary.title), \(summary.detail)")
        .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.uploadTruthRegion)
    }

    private var iconName: String {
        switch summary.primaryItem.state {
        case .uploaded:
            return "checkmark.icloud.fill"
        case .uploading:
            return "icloud.and.arrow.up"
        case .retrying:
            return "arrow.clockwise.icloud"
        case .blocked, .failed, .degraded:
            return "exclamationmark.icloud.fill"
        case .queued:
            return "tray.and.arrow.up"
        case .terminalDeleted:
            return "xmark.icloud"
        }
    }

    private var statusColor: Color {
        switch summary.primaryItem.state {
        case .uploaded:
            return .green
        case .uploading, .queued:
            return .blue
        case .retrying, .degraded, .blocked:
            return .orange
        case .failed, .terminalDeleted:
            return .red
        }
    }

    private func actionIcon(for label: String) -> String {
        label.localizedCaseInsensitiveContains("stop") ||
            label.localizedCaseInsensitiveContains("останов")
            ? "pause.circle"
            : "arrow.clockwise"
    }
}

private struct LiveRecordingMetersView: View {
    let routeSignalLevels: LiveRouteSignalLevels
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

            HStack(alignment: .top, spacing: 18) {
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
            routeIsActive: routeSignalLevels.isActive,
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
            routeIsActive: routeSignalLevels.isActive,
            microphoneIsLive: microphoneIsLive
        )
    }

    private var incomingDetail: String {
        SystemAudioStatusLabels.incomingDetail(
            routeIsActive: routeSignalLevels.isActive,
            incomingIsLive: incomingIsLive
        )
    }

    private var microphoneLevel: Double {
        routeSignalLevels.microphoneLevel
    }

    private var incomingLevel: Double {
        routeSignalLevels.speakerLevel
    }

    private var microphoneIsLive: Bool {
        routeSignalLevels.microphoneIsLive(
            now: now,
            staleAfter: SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds
        )
    }

    private var incomingIsLive: Bool {
        routeSignalLevels.speakerIsLive(
            now: now,
            staleAfter: SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds
        )
    }

    private var shouldWarnIncoming: Bool {
        routeSignalLevels.isActive && !incomingIsLive
    }

    private var shouldWarnMicrophone: Bool {
        routeSignalLevels.isActive && !microphoneIsLive
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
