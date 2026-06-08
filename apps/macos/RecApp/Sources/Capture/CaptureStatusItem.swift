import SwiftUI
import TwoBrainRecShared

public struct CaptureStatusItem: View {
    private let session: CaptureSession?
    private let stopDisabled: Bool
    private let onStop: () -> Void

    public init(
        session: CaptureSession?,
        stopDisabled: Bool = false,
        onStop: @escaping () -> Void
    ) {
        self.session = session
        self.stopDisabled = stopDisabled
        self.onStop = onStop
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
            return "Recording idle"
        case .detecting:
            return "Checking recording readiness"
        case .ready:
            return "Ready to record"
        case .starting:
            return "Recording starting"
        case .active:
            return "Recording active"
        case .paused:
            return "Recording paused"
        case .degraded:
            return "Recording degraded"
        case .stopping:
            return "Recording stopping"
        case .stopped:
            return "Recording stopped"
        case .failed:
            return "Recording failed"
        case .finalized:
            return "Recording finalized"
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

    public static func accessibilityLabel(for session: CaptureSession) -> String {
        let prefix = statusLabel(for: session)
        if session.stopActionAvailable {
            return "\(prefix). Stop recording is available."
        }
        if session.state == .idle || session.state == .detecting || session.state == .ready {
            return "\(prefix). Recording is not active."
        }
        return prefix
    }
}
