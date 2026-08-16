import SwiftUI
import TwoBrainRecShared

public struct CaptureStatusItem: View {
    private let session: CaptureSession?
    private let stopDisabled: Bool
    private let pauseDisabled: Bool
    private let onStop: () -> Void
    private let onPause: () -> Void
    private let onResume: () -> Void

    public init(
        session: CaptureSession?,
        stopDisabled: Bool = false,
        pauseDisabled: Bool = false,
        onStop: @escaping () -> Void,
        onPause: @escaping () -> Void = {},
        onResume: @escaping () -> Void = {}
    ) {
        self.session = session
        self.stopDisabled = stopDisabled
        self.pauseDisabled = pauseDisabled
        self.onStop = onStop
        self.onPause = onPause
        self.onResume = onResume
    }

    public var body: some View {
        if let session {
            statusSurface(for: session)
        } else {
            EmptyView()
        }
    }

    @ViewBuilder
    private func statusSurface(for session: CaptureSession) -> some View {
        let canStop = Self.shouldEnableStopButton(for: session, stopDisabled: stopDisabled)
        let showsStopAction = Self.showsStopAction(for: session)

        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: iconName(for: session))
                    .foregroundStyle(color(for: session))
                Text(Self.statusLabel(for: session))
                    .font(.caption)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel(Self.accessibilityLabel(for: session))
            .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.statusSurface)
            .accessibilityRemoveTraits(.isSelected)

            if let source = Self.sourceDisplayName(for: session) {
                sourceRow(source: source, for: session)
            }

            if showsStopAction {
                HStack(spacing: 8) {
                    if Self.showsPauseButton(for: session) {
                        Button(action: onPause) {
                            Label(SystemAudioStatusLabels.pauseButtonTitle, systemImage: "pause.fill")
                                .lineLimit(1)
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.controlHeight)
                        .disabled(!Self.shouldEnablePauseButton(for: session, pauseDisabled: pauseDisabled))
                        .accessibilityLabel(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
                        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.pauseButton)
                        .help(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
                    }

                    if Self.showsResumeButton(for: session) {
                        Button(action: onResume) {
                            Label(SystemAudioStatusLabels.resumeButtonTitle, systemImage: "play.fill")
                                .lineLimit(1)
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.controlHeight)
                        .disabled(!Self.shouldEnableResumeButton(for: session, pauseDisabled: pauseDisabled))
                        .accessibilityLabel(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
                        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.resumeButton)
                        .help(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
                    }

                    Button(action: onStop) {
                        Label(SystemAudioStatusLabels.stopButtonTitle, systemImage: "stop.fill")
                            .lineLimit(1)
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .frame(maxWidth: .infinity, minHeight: DesktopMeetingShellChrome.controlHeight)
                    .disabled(!canStop || stopDisabled)
                    .accessibilityLabel(SystemAudioStatusLabels.stopButtonAccessibilityLabel)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.stopButton)
                    .help(SystemAudioStatusLabels.stopButtonAccessibilityLabel)
                }
                .frame(maxWidth: .infinity)
            }
        }
        .padding(8)
        .accessibilityElement(children: .contain)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(.thickMaterial)
        )
        .opacity(statusOpacity(for: session))
    }

    private func iconName(for session: CaptureSession) -> String {
        if session.state == .stopped || session.state == .finalized {
            return "checkmark.circle.fill"
        }
        return iconName(for: session.visibleIndicatorState)
    }

    private func iconName(for state: VisibleIndicatorState) -> String {
        switch state {
        case .ready:
            return "record.circle"
        case .active:
            return "dot.radiowaves.left.and.right"
        case .paused:
            return "pause.circle"
        case .degraded:
            return "exclamationmark.triangle.fill"
        case .error:
            return "xmark.octagon.fill"
        case .hidden:
            return "eye.slash"
        }
    }

    private func color(for state: VisibleIndicatorState) -> Color {
        switch state {
        case .ready:
            return .blue
        case .active:
            return .green
        case .paused:
            return .orange
        case .degraded, .error:
            return .red
        case .hidden:
            return .secondary
        }
    }

    private func color(for session: CaptureSession) -> Color {
        if session.state == .stopped || session.state == .finalized {
            return .green
        }
        return color(for: session.visibleIndicatorState)
    }

    private func sourceRow(source: String, for session: CaptureSession) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Label(SystemAudioStatusLabels.recordingSourceTitle, systemImage: "waveform")
                .font(.caption2.weight(.semibold))
                .foregroundStyle(.secondary)

            Text(source)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.primary)
                .lineLimit(1)
                .truncationMode(.tail)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(Self.sourceAccessibilityLabel(for: session) ?? source)
        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordingSource)
        .help(Self.sourceAccessibilityLabel(for: session) ?? source)
    }

    private func statusOpacity(for session: CaptureSession) -> Double {
        if session.state == .stopped || session.state == .finalized {
            return 1
        }
        return session.visibleIndicatorState == .hidden ? 0.6 : 1
    }

    public static func statusLabel(for session: CaptureSession) -> String {
        switch session.state {
        case .idle:
            return "Готово к записи"
        case .detecting:
            return "Проверяем готовность"
        case .ready:
            return "Готово к записи"
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
        case .stopped:
            return "Сохранено на Mac"
        case .failed:
            return "Нужна помощь"
        case .finalized:
            return "Сохранено на Mac"
        }
    }

    // ponytail: attribution stays bounded to approved session evidence; per-process audio attribution needs a separate capture contract.
    public static func sourceDisplayName(for session: CaptureSession) -> String? {
        guard showsSource(for: session) else { return nil }
        guard let rawSource = session.triggerEvidence["sourceDisplayName"]?
            .trimmingCharacters(in: .whitespacesAndNewlines),
              !rawSource.isEmpty
        else {
            return SystemAudioStatusLabels.recordingSourceUnknown
        }

        if rawSource.compare(
            "Current display/system audio",
            options: [.caseInsensitive, .diacriticInsensitive]
        ) == .orderedSame {
            return SystemAudioStatusLabels.recordingSourceSystemAudio
        }
        return rawSource
    }

    public static func sourceAccessibilityLabel(for session: CaptureSession) -> String? {
        guard let source = sourceDisplayName(for: session) else { return nil }
        return SystemAudioStatusLabels.recordingSourceAccessibilityLabel(source)
    }

    public static func showsSource(for session: CaptureSession) -> Bool {
        switch session.state {
        case .detecting, .ready, .starting, .active, .paused, .degraded, .stopping:
            return true
        case .idle, .stopped, .failed, .finalized:
            return false
        }
    }

    public static func showsStopButton(for session: CaptureSession) -> Bool {
        session.state == .starting ||
            session.state == .active ||
            session.state == .paused ||
            session.state == .degraded ||
            session.state == .stopping
    }

    public static func showsStopAction(for session: CaptureSession) -> Bool {
        showsStopButton(for: session) && session.state != .stopping
    }

    public static func shouldEnableStopButton(
        for session: CaptureSession,
        stopDisabled: Bool
    ) -> Bool {
        showsStopButton(for: session) && session.stopActionAvailable && !stopDisabled
    }

    public static func showsPauseButton(for session: CaptureSession) -> Bool {
        session.state == .active
    }

    public static func showsResumeButton(for session: CaptureSession) -> Bool {
        session.state == .paused
    }

    public static func shouldEnablePauseButton(
        for session: CaptureSession,
        pauseDisabled: Bool
    ) -> Bool {
        showsPauseButton(for: session) && session.stopActionAvailable && !pauseDisabled
    }

    public static func shouldEnableResumeButton(
        for session: CaptureSession,
        pauseDisabled: Bool
    ) -> Bool {
        showsResumeButton(for: session) && session.stopActionAvailable && !pauseDisabled
    }

    public static func accessibilityLabel(for session: CaptureSession) -> String {
        let prefix = statusLabel(for: session)
        if session.stopActionAvailable {
            return "\(prefix). Кнопка остановки доступна."
        }
        if session.state == .idle || session.state == .detecting || session.state == .ready {
            return "\(prefix). Активной записи нет."
        }
        return prefix
    }
}
