import SwiftUI
import TwoBrainRecShared

public struct RouteVerificationView: View {
    private let snapshot: RouteVerificationSnapshot?
    private let canVerify: Bool
    private let isVerifying: Bool
    private let onVerify: () -> Void

    public init(
        snapshot: RouteVerificationSnapshot?,
        canVerify: Bool,
        isVerifying: Bool,
        onVerify: @escaping () -> Void
    ) {
        self.snapshot = snapshot
        self.canVerify = canVerify
        self.isVerifying = isVerifying
        self.onVerify = onVerify
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Readiness Check")
                        .font(.headline)
                    Text("Checks what is safe to use right now. It does not start recording.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button(action: onVerify) {
                    if isVerifying {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Text("Run Check")
                    }
                }
                .disabled(!canVerify || isVerifying)
            }

            VStack(spacing: 10) {
                routeRow(
                    title: "Microphone",
                    verification: snapshot?.mic
                )
                routeRow(
                    title: "Speaker",
                    verification: snapshot?.speaker
                )
            }

            if let snapshot, snapshot.canShowReady {
                Label("Ready", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .accessibilityLabel("Audio routes ready")
            } else {
                Label("Not ready for calls yet", systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .accessibilityLabel("Audio routes are not ready yet")
            }
        }
        .padding(16)
    }

    private func routeRow(title: String, verification: RouteVerification?) -> some View {
        HStack(spacing: 10) {
            Image(systemName: iconName(for: verification?.status))
                .foregroundStyle(color(for: verification?.status))
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text(statusText(for: verification))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }
            Spacer()
        }
        .accessibilityElement(children: .combine)
    }

    private func iconName(for status: RouteVerificationStatus?) -> String {
        switch status {
        case .passed:
            "checkmark.circle.fill"
        case .running:
            "waveform"
        case .failed:
            "xmark.octagon.fill"
        case .stale:
            "exclamationmark.triangle.fill"
        case .notStarted, nil:
            "circle"
        }
    }

    private func color(for status: RouteVerificationStatus?) -> Color {
        switch status {
        case .passed:
            .green
        case .running:
            .blue
        case .failed:
            .red
        case .stale:
            .orange
        case .notStarted, nil:
            .secondary
        }
    }

    private func statusText(for verification: RouteVerification?) -> String {
        guard let verification else {
            return "Not checked yet"
        }
        let label = AdaptiveStatusText.routeStatusLabel(verification.status)
        if let failureReason = verification.failureReason {
            return "\(label): \(humanReason(failureReason))"
        }
        if let recoveryAction = verification.recoveryAction {
            return "\(label): \(AdaptiveStatusText.recoveryActionLabel(recoveryAction))"
        }
        return label
    }

    private func humanReason(_ reason: String) -> String {
        switch reason {
        case "virtual_microphone_not_visible":
            return "2brain Rec Microphone is not visible in macOS."
        case "virtual_speaker_not_visible":
            return "2brain Rec Speaker is not visible in macOS."
        case "physical_microphone_not_selected":
            return "macOS input is not a physical microphone."
        case "physical_speaker_not_selected":
            return "macOS output is not a physical speaker."
        case "virtual_device_visible_but_audio_path_not_implemented":
            return "device is visible, but real audio passthrough is not implemented yet."
        default:
            return reason.replacingOccurrences(of: "_", with: " ")
        }
    }
}
