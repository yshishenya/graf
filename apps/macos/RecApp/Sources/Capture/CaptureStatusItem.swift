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
        let isActive = session.state == .starting ||
            session.state == .active ||
            session.state == .paused ||
            session.state == .degraded ||
            session.state == .stopping

        HStack(spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: iconName(for: session.visibleIndicatorState))
                    .foregroundStyle(color(for: session.visibleIndicatorState))
                Text(label(for: session.mode, state: session.state))
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

    private func label(for mode: CaptureMode, state: CaptureSessionState) -> String {
        switch state {
        case .active:
            return "\(mode.rawValue.replacingOccurrences(of: "_", with: " ")) active"
        case .paused:
            return "\(mode.rawValue.replacingOccurrences(of: "_", with: " ")) paused"
        case .degraded:
            return "\(mode.rawValue.replacingOccurrences(of: "_", with: " ")) degraded"
        case .ready, .detecting:
            return "Ready to capture"
        default:
            return mode.rawValue.replacingOccurrences(of: "_", with: " ")
        }
    }
}
