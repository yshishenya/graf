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
        let isActive = Self.showsStopButton(for: session)

        HStack(spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: iconName(for: session.visibleIndicatorState))
                    .foregroundStyle(color(for: session.visibleIndicatorState))
                Text(Self.statusLabel(for: session))
                    .font(.caption)
                    .lineLimit(1)
                    .minimumScaleFactor(0.85)
            }

            if isActive {
                Spacer()

                if Self.showsPauseButton(for: session) {
                    Button(action: onPause) {
                        Label(SystemAudioStatusLabels.pauseButtonTitle, systemImage: "pause.fill")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .disabled(!Self.shouldEnablePauseButton(for: session, pauseDisabled: pauseDisabled))
                    .accessibilityLabel(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.pauseButton)
                    .help(SystemAudioStatusLabels.pauseButtonAccessibilityLabel)
                }

                if Self.showsResumeButton(for: session) {
                    Button(action: onResume) {
                        Label(SystemAudioStatusLabels.resumeButtonTitle, systemImage: "play.fill")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .disabled(!Self.shouldEnableResumeButton(for: session, pauseDisabled: pauseDisabled))
                    .accessibilityLabel(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.resumeButton)
                    .help(SystemAudioStatusLabels.resumeButtonAccessibilityLabel)
                }

                Button(action: onStop) {
                    Label(SystemAudioStatusLabels.stopButtonTitle, systemImage: "stop.fill")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .disabled(!canStop || stopDisabled)
                .keyboardShortcut(.escape, modifiers: [])
                .accessibilityLabel(SystemAudioStatusLabels.stopButtonAccessibilityLabel)
                .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.stopButton)
                .help(SystemAudioStatusLabels.stopButtonAccessibilityLabel)
            }
        }
        .padding(8)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(Self.accessibilityLabel(for: session))
        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.statusSurface)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(.thickMaterial)
        )
        .opacity(session.visibleIndicatorState == .hidden ? 0.6 : 1.0)
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

    public static func statusLabel(for session: CaptureSession) -> String {
        switch session.state {
        case .idle:
            return "Запись не идет"
        case .detecting:
            return "Проверяем готовность"
        case .ready:
            return "Готово к записи"
        case .starting:
            return "Запись запускается"
        case .active:
            return "Идет запись"
        case .paused:
            return "Запись на паузе"
        case .degraded:
            return "Запись с ограничением"
        case .stopping:
            return "Останавливаем запись"
        case .stopped:
            return "Запись остановлена"
        case .failed:
            return "Запись не началась"
        case .finalized:
            return "Запись сохранена"
        }
    }

    public static func showsStopButton(for session: CaptureSession) -> Bool {
        session.state == .starting ||
            session.state == .active ||
            session.state == .paused ||
            session.state == .degraded ||
            session.state == .stopping
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
