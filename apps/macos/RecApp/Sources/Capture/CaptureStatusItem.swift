import SwiftUI
import TwoBrainRecShared

public struct CaptureStatusItem: View {
    private let session: CaptureSession?
    private let onStop: () -> Void

    public init(
        session: CaptureSession?,
        onStop: @escaping () -> Void
    ) {
        self.session = session
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
        let canStop = session.stopActionAvailable
        let isActive = Self.showsStopButton(for: session)

        HStack(spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: iconName(for: session.visibleIndicatorState))
                    .foregroundStyle(color(for: session.visibleIndicatorState))
                Text(Self.statusLabel(for: session))
                    .font(.caption)
                    .lineLimit(1)
            }

            if isActive {
                Spacer()

                Button(action: onStop) {
                    Label("Stop", systemImage: "stop.fill")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .disabled(!canStop)
                .accessibilityLabel("Stop recording")
            }
        }
        .padding(8)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(Self.accessibilityLabel(for: session))
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
