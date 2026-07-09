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
    private let webRTCAEC3Status: AppRecordingStatus?
    private let recordingMicrophoneSelection: RecordingMicrophoneSelection?
    private let recordingMicrophoneInputs: [PhysicalAudioDevice]
    private let selectedRecordingMicrophoneDeviceId: String?
    private let uploadQueueItems: [DesktopUploadQueueItem]
    private let cabinetConfiguration: DesktopCabinetConfiguration?
    private let calendarPrompt: DesktopCalendarPrompt?
    private let meetingDetectionStatus: String?
    private let meetingDetectionHealth: String?
    private let routeSignalLevels: LiveRouteSignalLevels
    private let recordDisabled: Bool
    private let stopDisabled: Bool
    private let pauseDisabled: Bool
    private let onRecord: () -> Void
    private let onStop: () -> Void
    private let onPause: () -> Void
    private let onResume: () -> Void
    private let onSelectRecordingMicrophone: (String?) -> Void
    private let onUploadReview: (URL) -> Void
    private let onSupportIncidentReport: ([String]) async throws -> DesktopSupportIncidentResponse
    private let onCalendarPromptPrimary: (DesktopCalendarPrompt) -> Void
    private let onCalendarPromptDismiss: (DesktopCalendarPrompt) -> Void

    public init(
        session: CaptureSession?,
        blockedReason: String? = nil,
        localRecordingStatus: String? = nil,
        localRecordingLocation: String? = nil,
        muteTruthWarning: String? = nil,
        appleProcessingStatus: String? = nil,
        webRTCAEC3Status: AppRecordingStatus? = nil,
        recordingMicrophoneSelection: RecordingMicrophoneSelection? = nil,
        recordingMicrophoneInputs: [PhysicalAudioDevice] = [],
        selectedRecordingMicrophoneDeviceId: String? = nil,
        uploadQueueItems: [DesktopUploadQueueItem] = [],
        cabinetConfiguration: DesktopCabinetConfiguration? = nil,
        calendarPrompt: DesktopCalendarPrompt? = nil,
        meetingDetectionStatus: String? = nil,
        meetingDetectionHealth: String? = nil,
        routeSignalLevels: LiveRouteSignalLevels = .inactive,
        recordDisabled: Bool = false,
        stopDisabled: Bool = false,
        pauseDisabled: Bool = false,
        onRecord: @escaping () -> Void,
        onStop: @escaping () -> Void,
        onPause: @escaping () -> Void = {},
        onResume: @escaping () -> Void = {},
        onSelectRecordingMicrophone: @escaping (String?) -> Void = { _ in },
        onUploadReview: @escaping (URL) -> Void = { _ in },
        onSupportIncidentReport: @escaping ([String]) async throws -> DesktopSupportIncidentResponse = { _ in
            throw DesktopUploadClientError.httpStatus(503, "support_incident.unavailable")
        },
        onCalendarPromptPrimary: @escaping (DesktopCalendarPrompt) -> Void = { _ in },
        onCalendarPromptDismiss: @escaping (DesktopCalendarPrompt) -> Void = { _ in }
    ) {
        self.session = session
        self.blockedReason = blockedReason
        self.localRecordingStatus = localRecordingStatus
        self.localRecordingLocation = localRecordingLocation
        self.muteTruthWarning = muteTruthWarning
        self.appleProcessingStatus = appleProcessingStatus
        self.webRTCAEC3Status = webRTCAEC3Status ?? session?.webRTCAEC3Status
        self.recordingMicrophoneSelection = recordingMicrophoneSelection
        self.recordingMicrophoneInputs = recordingMicrophoneInputs
        self.selectedRecordingMicrophoneDeviceId = selectedRecordingMicrophoneDeviceId
        self.uploadQueueItems = uploadQueueItems
        self.cabinetConfiguration = cabinetConfiguration
        self.calendarPrompt = calendarPrompt
        self.meetingDetectionStatus = meetingDetectionStatus
        self.meetingDetectionHealth = meetingDetectionHealth
        self.routeSignalLevels = routeSignalLevels
        self.recordDisabled = recordDisabled
        self.stopDisabled = stopDisabled
        self.pauseDisabled = pauseDisabled
        self.onRecord = onRecord
        self.onStop = onStop
        self.onPause = onPause
        self.onResume = onResume
        self.onSelectRecordingMicrophone = onSelectRecordingMicrophone
        self.onUploadReview = onUploadReview
        self.onSupportIncidentReport = onSupportIncidentReport
        self.onCalendarPromptPrimary = onCalendarPromptPrimary
        self.onCalendarPromptDismiss = onCalendarPromptDismiss
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

            if let calendarPrompt {
                CalendarPromptView(
                    prompt: calendarPrompt,
                    onPrimary: onCalendarPromptPrimary,
                    onDismiss: onCalendarPromptDismiss
                )
            }

            if let meetingDetectionStatus, !meetingDetectionStatus.isEmpty {
                HStack(alignment: .top, spacing: 10) {
                    StatusNoteView(
                        icon: "dot.radiowaves.left.and.right",
                        title: SystemAudioStatusLabels.meetingDetectionSettingsTitle,
                        detail: meetingDetectionHealth.map { "\(meetingDetectionStatus). \($0)" } ?? meetingDetectionStatus,
                        iconColor: .secondary
                    )
                    .accessibilityLabel(
                        SystemAudioStatusLabels.meetingDetectionAccessibilityLabel(
                            status: meetingDetectionStatus,
                            health: meetingDetectionHealth
                        )
                    )
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meetingDetectionStatus)
                }
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

            if let webRTCAEC3Status,
               let statusCopy = Self.webRTCAEC3StatusCopy(for: webRTCAEC3Status) {
                StatusNoteView(
                    icon: Self.webRTCAEC3StatusIconName(for: webRTCAEC3Status.state),
                    title: Self.webRTCAEC3StatusTitle(for: webRTCAEC3Status.state),
                    detail: statusCopy,
                    iconColor: Self.webRTCAEC3StatusStyle(for: webRTCAEC3Status)
                )
                .accessibilityLabel("\(Self.webRTCAEC3StatusTitle(for: webRTCAEC3Status.state)): \(statusCopy)")
                .accessibilityIdentifier(Self.webRTCAEC3StatusAccessibilityIdentifier(for: webRTCAEC3Status.state))
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
                    onReview: onUploadReview,
                    onSupportIncidentReport: onSupportIncidentReport
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

    public static func uploadSummary(for items: [DesktopUploadQueueItem]) -> DesktopUploadCustodySummary? {
        DesktopUploadCustodySummary.summary(for: items)
    }

    public static func uploadReviewLink(
        for item: DesktopUploadQueueItem,
        configuration: DesktopCabinetConfiguration?
    ) -> UploadReviewLink? {
        guard let configuration else { return nil }
        let link = configuration.reviewLink(for: item)
        return link.availability == .available ? link : nil
    }

    nonisolated public static func resolvedWebRTCAEC3Status(
        for session: CaptureSession?,
        manifest: LocalRecordingManifest?
    ) -> AppRecordingStatus? {
        session?.webRTCAEC3Status ?? webRTCAEC3Status(from: manifest?.webRTCAEC3Outcome)
    }

    nonisolated private static func webRTCAEC3Status(
        from outcome: WebRTCAEC3DecisionRecord?
    ) -> AppRecordingStatus? {
        guard let outcome else { return nil }
        let diagnosticSafe = outcome.diagnosticSafe && outcome.validationRows.allSatisfy(\.diagnosticSafe)
        let state = webRTCAEC3StatusState(for: outcome, diagnosticSafe: diagnosticSafe)
        let copySafety: WebRTCAEC3StatusCopySafety = diagnosticSafe ? .safe : .inconsistentWithPackageTruth
        let matchesPackageTruth = webRTCAEC3StatusMatchesPackageTruth(
            outcome,
            state: state,
            diagnosticSafe: diagnosticSafe
        )

        return AppRecordingStatus(
            statusId: "manifest-\(outcome.candidateId)-\(state.rawValue)",
            candidateId: outcome.candidateId,
            state: state,
            routeScope: webRTCAEC3RouteScope(for: outcome),
            copySafety: copySafety,
            actionHint: webRTCAEC3ActionHint(for: state),
            matchesPackageTruth: matchesPackageTruth,
            diagnosticSafe: diagnosticSafe
        )
    }

    nonisolated private static func webRTCAEC3StatusState(
        for outcome: WebRTCAEC3DecisionRecord,
        diagnosticSafe: Bool
    ) -> WebRTCAEC3AppStatusState {
        guard diagnosticSafe else { return .requiresUserAttention }
        let rowStates = Set(outcome.validationRows.map(\.appStatusState))

        if rowStates.contains(.requiresUserAttention) {
            return .requiresUserAttention
        }
        if outcome.rollbackEvents?.contains(where: \.restoresOriginalTruth) == true ||
            rowStates.contains(.rolledBackToOriginal) {
            return .rolledBackToOriginal
        }
        if outcome.nextStepRecommendation == .fallbackDecision ||
            outcome.primaryOutcome == .deferToFallbackDecision {
            return .fallbackRelevant
        }

        switch outcome.primaryOutcome {
        case .acceptedForImmediatePromotion:
            return outcome.canClaimCleanBuiltInSpeakerphone ? .promotedBuiltinRoute : .requiresUserAttention
        case .acceptedForDerivedCandidateOnly, .acceptedForGuidanceOnly:
            return .usingOriginalMicTruth
        case .blockedRouteTopology, .blockedQuality, .blockedStability:
            return .candidateBlocked
        case .deferToFallbackDecision:
            return .fallbackRelevant
        }
    }

    nonisolated private static func webRTCAEC3StatusMatchesPackageTruth(
        _ outcome: WebRTCAEC3DecisionRecord,
        state: WebRTCAEC3AppStatusState,
        diagnosticSafe: Bool
    ) -> Bool {
        guard diagnosticSafe else { return false }
        if outcome.primaryOutcome == .acceptedForImmediatePromotion && !outcome.canClaimCleanBuiltInSpeakerphone {
            return false
        }
        return state != .promotedBuiltinRoute || outcome.canClaimCleanBuiltInSpeakerphone
    }

    nonisolated private static func webRTCAEC3RouteScope(
        for outcome: WebRTCAEC3DecisionRecord
    ) -> WebRTCAEC3StatusRouteScope {
        guard !outcome.validationRows.isEmpty else { return .notApplicable }
        if outcome.validationRows.contains(where: { $0.routeClass == .builtInSpeakerphone }) {
            return .builtInMacMicAndSpeakers
        }
        return .supportingRouteOnly
    }

    nonisolated private static func webRTCAEC3ActionHint(
        for state: WebRTCAEC3AppStatusState
    ) -> WebRTCAEC3StatusActionHint {
        switch state {
        case .candidateBlocked, .fallbackRelevant, .requiresUserAttention, .rolledBackToOriginal:
            return .reviewStatus
        case .evaluatingAEC3, .usingOriginalMicTruth, .promotedBuiltinRoute:
            return .continueRecording
        case .notEvaluated, .notApplicable:
            return .none
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
        case .unsupportedSelfRoutingInput:
            return "Выберите обычный микрофон. Виртуальные устройства GRAF нельзя использовать как микрофон записи."
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
                ? "Apple проверка принята для встроенного маршрута; итог все равно сверяется с локальным пакетом."
                : "Apple проверка требует полного набора подтверждений перед пользовательским обещанием."
        case .acceptedForGuidanceOnly:
            return "Apple проверка доступна только как подсказка; запись остается проверкой локального пакета."
        case .acceptedForHeadsetRoutesOnly:
            return "Apple проверка применима только к гарнитурам и проводным маршрутам; режим встроенных динамиков и микрофона остается без нового обещания."
        case .blockedRouteTopology:
            return "Apple проверка маршрута заблокирована; продолжаем без повышения обещания для встроенных динамиков и микрофона."
        case .blockedQuality:
            return "Apple проверка качества заблокирована; локальная запись остается с текущими ограничениями."
        case .blockedStability:
            return "Apple проверка стабильности заблокирована; вариант отключен до новой проверки."
        case .deferToWebRTCAEC3:
            return "Apple проверка не доказала рабочий маршрут; следующий вариант - WebRTC AEC3."
        }
    }

    nonisolated public static func webRTCAEC3StatusCopy(for status: AppRecordingStatus?) -> String? {
        guard let status else { return nil }
        if !status.diagnosticSafe || status.copySafety != .safe || !status.matchesPackageTruth {
            return "Статус AEC3 требует проверки; запись не повышаем и оставляем исходный микрофон источником правды."
        }

        switch status.state {
        case .notEvaluated, .notApplicable:
            return nil
        case .evaluatingAEC3:
            return "Проверяем AEC3 по служебным признакам; запись сейчас идет по исходному микрофону."
        case .usingOriginalMicTruth:
            return "Записываем исходный микрофон; он остается источником правды для локального пакета."
        case .candidateBlocked:
            return "AEC3 не включен: проверка заблокирована, запись продолжается по исходному микрофону."
        case .promotedBuiltinRoute:
            return status.canSupportPromotion
                ? "Встроенный маршрут подтвержден проверками; AEC3 можно использовать для этой записи."
                : "AEC3 не подтвержден проверками; запись остается по исходному микрофону."
        case .rolledBackToOriginal:
            return "AEC3 откатился после нового риска; запись возвращена к исходному микрофону."
        case .fallbackRelevant:
            return "Используем фолбэк: AEC3 не доказан, исходный микрофон остается источником правды для записи."
        case .requiresUserAttention:
            return "Нужна проверка AEC3: статус не совпал с проверками, запись не повышаем."
        }
    }

    nonisolated public static func webRTCAEC3StatusTitle(for state: WebRTCAEC3AppStatusState) -> String {
        switch state {
        case .notEvaluated:
            return "AEC3 не проверялся"
        case .evaluatingAEC3:
            return "Проверяем AEC3"
        case .usingOriginalMicTruth:
            return "Исходный микрофон"
        case .candidateBlocked:
            return "AEC3 не включен"
        case .promotedBuiltinRoute:
            return "AEC3 подтвержден"
        case .rolledBackToOriginal:
            return "AEC3 откатился"
        case .fallbackRelevant:
            return "Используем фолбэк"
        case .requiresUserAttention:
            return "Нужна проверка AEC3"
        case .notApplicable:
            return "AEC3 не применим"
        }
    }

    nonisolated public static func webRTCAEC3StatusIconName(for state: WebRTCAEC3AppStatusState) -> String {
        switch state {
        case .evaluatingAEC3:
            return "waveform.and.mic"
        case .usingOriginalMicTruth:
            return "mic.fill"
        case .candidateBlocked:
            return "exclamationmark.triangle"
        case .promotedBuiltinRoute:
            return "checkmark.shield"
        case .rolledBackToOriginal:
            return "arrow.uturn.backward.circle"
        case .fallbackRelevant:
            return "arrow.triangle.2.circlepath"
        case .requiresUserAttention:
            return "exclamationmark.triangle.fill"
        case .notEvaluated, .notApplicable:
            return "waveform"
        }
    }

    nonisolated public static func webRTCAEC3StatusPriority(for state: WebRTCAEC3AppStatusState) -> Int {
        switch state {
        case .requiresUserAttention:
            return 50
        case .rolledBackToOriginal:
            return 40
        case .candidateBlocked:
            return 30
        case .fallbackRelevant:
            return 20
        case .evaluatingAEC3, .usingOriginalMicTruth:
            return 10
        case .promotedBuiltinRoute:
            return 5
        case .notEvaluated, .notApplicable:
            return 0
        }
    }

    nonisolated public static func webRTCAEC3StatusToneName(for state: WebRTCAEC3AppStatusState) -> String {
        switch state {
        case .promotedBuiltinRoute:
            return "success"
        case .candidateBlocked, .requiresUserAttention:
            return "attention"
        case .rolledBackToOriginal, .fallbackRelevant:
            return "warning"
        case .evaluatingAEC3, .usingOriginalMicTruth, .notEvaluated, .notApplicable:
            return "secondary"
        }
    }

    nonisolated public static func webRTCAEC3StatusAccessibilityIdentifier(
        for state: WebRTCAEC3AppStatusState
    ) -> String {
        switch state {
        case .rolledBackToOriginal:
            return SystemAudioAccessibilityIdentifier.webRTCAEC3RollbackStatus
        case .fallbackRelevant:
            return SystemAudioAccessibilityIdentifier.webRTCAEC3FallbackStatus
        default:
            return SystemAudioAccessibilityIdentifier.webRTCAEC3Status
        }
    }

    nonisolated public static func webRTCAEC3StatusIsNoisyAlert(for status: AppRecordingStatus) -> Bool {
        status.state == .requiresUserAttention &&
            (status.copySafety != .safe || !status.matchesPackageTruth || !status.diagnosticSafe)
    }

    nonisolated public static func webRTCAEC3StatusCopyIsClaimSafe(
        _ copy: String,
        state: WebRTCAEC3AppStatusState
    ) -> Bool {
        let normalized = copy.lowercased()
        let forbiddenClaimFragments = ["clean", "чист", "не попадает", "без эха"]
        guard !forbiddenClaimFragments.contains(where: { normalized.contains($0) }) else {
            return false
        }
        if state != .promotedBuiltinRoute && normalized.contains("подтвержден") {
            return false
        }
        return true
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

    private static func webRTCAEC3StatusStyle(for status: AppRecordingStatus) -> Color {
        switch webRTCAEC3StatusToneName(for: status.state) {
        case "success":
            return .green
        case "attention", "warning":
            return .orange
        default:
            return .secondary
        }
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
    }
}

private struct UploadQueueStatusView: View {
    let summary: DesktopUploadCustodySummary
    let reviewLink: UploadReviewLink?
    let onReview: (URL) -> Void
    let onSupportIncidentReport: ([String]) async throws -> DesktopSupportIncidentResponse

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
                Text(summary.pendingCount > 1 ? "\(summary.pendingCount)" : summary.ownerLabel)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.secondary)
            }

            if summary.showsProgress {
                ProgressView(value: summary.progressFraction)
                    .progressViewStyle(.linear)
            }

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
            }

            DesktopSupportIncidentActionStrip(
                summary: summary,
                onSubmit: onSupportIncidentReport
            )
            .fixedSize(horizontal: false, vertical: true)
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
        .accessibilityLabel(summary.accessibilityLabel)
        .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.uploadTruthRegion)
    }

    private var iconName: String {
        if summary.copyKey == "custody.unknown_blocked" {
            return "exclamationmark.icloud.fill"
        }
        switch summary.primaryProjection.custodyState {
        case .delivered, .finalized, .processing:
            return "checkmark.icloud.fill"
        case .partialUploaded, .uploadSessionCreated:
            return "icloud.and.arrow.up"
        case .retainedAwaitingCondition, .cannotSend:
            return "exclamationmark.icloud.fill"
        case .serverUnknownLocalSaved, .serverRegistered:
            return "tray.and.arrow.up"
        case .terminalUndelivered:
            return "xmark.icloud"
        }
    }

    private var statusColor: Color {
        if summary.copyKey == "custody.unknown_blocked" {
            return .orange
        }
        switch summary.primaryProjection.custodyState {
        case .delivered, .finalized, .processing:
            return .green
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
