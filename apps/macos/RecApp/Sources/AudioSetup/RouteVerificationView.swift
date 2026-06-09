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
                    Text("Recording Status")
                        .font(.headline)
                    Text("Refreshes local audio status. Recording permissions and meters are checked when you press Record.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button(action: onVerify) {
                    if isVerifying {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Text("Refresh Status")
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
                Label("Local audio status refreshed, not recording", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(.green)
                    .accessibilityLabel("Local audio status refreshed, not recording")
            } else if isVerifying {
                Label("Checking", systemImage: "waveform")
                    .foregroundStyle(.blue)
                    .accessibilityLabel("Audio route check is running")
            } else if let snapshot, snapshot.hasDegradedOrStaleRoute {
                Label("Status needs refresh", systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .accessibilityLabel("Local audio status needs refresh")
            } else {
                Label("Ready to try recording", systemImage: "record.circle")
                    .foregroundStyle(.secondary)
                    .accessibilityLabel("Ready to try recording")
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
                Text(statusText(title: title, for: verification))
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

    private func statusText(title: String, for verification: RouteVerification?) -> String {
        guard let verification else {
            if title == "Speaker" {
                return SystemAudioStatusLabels.speakerPendingStatus
            }
            return SystemAudioStatusLabels.microphonePendingStatus
        }
        let label = AdaptiveStatusText.routeStatusLabel(verification.status)
        if verification.status == .passed {
            switch verification.path {
            case .micToVirtualInput:
                return "Available: physical microphone can be used for recording, not recording"
            case .remoteOutputToVirtualSpeaker:
                return "Available: system audio capture is checked when recording starts, not recording"
            case .speakerPassthrough:
                return "Active: speaker passthrough is usable, not recording"
            case .captureMirror:
                return "Active: capture mirror is usable, not recording"
            }
        }
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
        case "physical_microphone_not_selected":
            return "macOS input is not a physical microphone."
        case "physical_speaker_not_selected":
            return "macOS output is not a physical speaker."
        case "physical_input_missing":
            return "select a physical microphone."
        case "physical_output_missing":
            return "select a physical speaker."
        case "physical_microphone_muted":
            return "physical microphone is muted."
        case "physical_microphone_silent":
            return "physical microphone is silent."
        case "physical_microphone_unavailable":
            return "physical microphone is unavailable."
        case "physical_microphone_unsupported":
            return "select a built-in or wired microphone for release readiness."
        case "physical_speaker_muted":
            return "physical speaker is muted."
        case "physical_speaker_silent":
            return "physical speaker is silent."
        case "physical_speaker_unavailable":
            return "physical speaker is unavailable."
        case "physical_speaker_unsupported":
            return "select a built-in or wired speaker for release readiness."
        case "aggregate_output_unmanaged":
            return "aggregate or multi-output speaker route is not managed for release readiness."
        case "bluetooth_profile_switching":
            return "Bluetooth profile is switching; recheck after it is stable."
        case "app_io_heartbeat_missing":
            return "app audio route is not active yet."
        case "virtual_device_visible_but_audio_path_not_implemented":
            return "legacy virtual-device diagnostics are parked for MVP recording."
        default:
            if reason.hasPrefix("virtual_") {
                return "driver diagnostics are parked for MVP recording."
            }
            return reason.replacingOccurrences(of: "_", with: " ")
        }
    }
}

private extension RouteVerificationSnapshot {
    var hasDegradedOrStaleRoute: Bool {
        mic.status == .stale || speaker.status == .stale
    }
}
