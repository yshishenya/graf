import SwiftUI
import TwoBrainRecShared

public struct AudioHealthView: View {
    private let state: AudioHealthState

    public init(state: AudioHealthState) {
        self.state = state
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HeaderView(state: state)
            Divider()
            Section("Permissions", icon: "lock.shield") {
                line(label: "Microphone access", detail: AdaptiveStatusText.permissionLabel(
                    microphone: state.microphonePermission,
                    output: state.outputPermission
                ), icon: permissionIcon)
            }
            Section("Current macOS Devices", icon: "airplayaudio") {
                line(
                    label: "macOS input",
                    detail: deviceLine(for: state.physicalInput),
                    icon: "mic"
                )
                line(
                    label: "macOS output",
                    detail: deviceLine(for: state.physicalOutput),
                    icon: "speaker.wave.2.fill"
                )
                line(
                    label: "Virtual microphone",
                    detail: virtualDeviceLine(name: "2brain Rec Microphone", state: state.virtualMicState),
                    icon: statusIcon(state.virtualMicState == .available),
                    emphasis: state.virtualMicState == .available ? .normal : .warning
                )
                line(
                    label: "Virtual speaker",
                    detail: virtualDeviceLine(name: "2brain Rec Speaker", state: state.virtualSpeakerState),
                    icon: statusIcon(state.virtualSpeakerState == .available),
                    emphasis: state.virtualSpeakerState == .available ? .normal : .warning
                )
            }
            Section("Routes", icon: "link") {
                if let snapshot = state.routeVerification {
                    line(
                        label: "Mic path",
                        detail: routeLine(snapshot.mic),
                        icon: AdaptiveStatusText.routeStatusIcon(snapshot.mic.status)
                    )
                    line(
                        label: "Speaker path",
                        detail: routeLine(snapshot.speaker),
                        icon: AdaptiveStatusText.routeStatusIcon(snapshot.speaker.status)
                    )
                    if let action = snapshot.speaker.recoveryAction ?? snapshot.mic.recoveryAction {
                        line(
                            label: "Recovery",
                            detail: AdaptiveStatusText.recoveryActionLabel(action),
                            icon: "arrow.clockwise"
                        )
                    }
                } else {
                    line(
                        label: "Route status",
                        detail: "No route verification snapshot",
                        icon: "questionmark.circle"
                    )
                }
            }
            Section("Passthrough", icon: "dot.radiowaves.left.and.right") {
                line(
                    label: "Live passthrough",
                    detail: AdaptiveStatusText.passthroughLabel(state.passthroughStatus),
                    icon: passthroughIcon
                )
                if let continuity = state.continuityStatus {
                    line(
                        label: "Continuity",
                        detail: AdaptiveStatusText.safeLabel(continuity, maxLength: 64),
                        icon: "timeline.selection"
                    )
                }
            }
            Section("Browser Targets", icon: "safari") {
                if state.browserTargetEvidence.isEmpty {
                    line(
                        label: "Validation",
                        detail: "No browser target evidence recorded",
                        icon: "circle"
                    )
                } else {
                    ForEach(state.browserTargetEvidence, id: \.target) { evidence in
                        line(
                            label: AdaptiveStatusText.safeLabel(evidence.target),
                            detail: browserEvidenceLine(evidence),
                            icon: browserEvidenceIcon(evidence.status)
                        )
                    }
                }
            }
            Section("Buffer", icon: "internaldrive") {
                line(
                    label: "Local buffer",
                    detail: state.bufferRisk == .healthy
                        ? "Healthy"
                        : String(describing: state.bufferRisk),
                    icon: bufferIcon
                )
            }
            Section("Health Checks", icon: "stethoscope") {
                line(
                    label: "Test recording",
                    detail: actionLine(for: state.testRecording),
                    icon: actionIcon(for: state.testRecording.status)
                )
                line(
                    label: "Test playback",
                    detail: actionLine(for: state.testPlayback),
                    icon: actionIcon(for: state.testPlayback.status)
                )
            }
            if !state.recoveryActions.isEmpty {
                Section("Recovery", icon: "wrench.and.screwdriver") {
                    line(
                        label: "Recheck",
                        detail: AdaptiveStatusText.recoveryActionLabel("rerun_readiness_check"),
                        icon: "arrow.clockwise"
                    )
                    ForEach(state.recoveryActions, id: \.self) { action in
                        line(label: "Action", detail: AdaptiveStatusText.safeLabel(action), icon: "exclamationmark.triangle.fill")
                    }
                }
                .accessibilitySortPriority(1)
            }
        }
        .padding(16)
        .accessibilityElement(children: .contain)
    }

    private var permissionIcon: String {
        if state.microphonePermission == .granted && state.outputPermission == .granted {
            return "lock.open.fill"
        }
        if state.microphonePermission == .denied || state.outputPermission == .denied {
            return "lock.fill"
        }
        return "lock.rotation"
    }

    private var passthroughIcon: String {
        switch state.passthroughStatus {
        case .healthy:
            return "checkmark.circle.fill"
        case .degraded:
            return "exclamationmark.triangle.fill"
        case .failed, .appIOMissing, .latencyExceeded, .mutedByPhysicalDevice, .physicalDeviceMissing:
            return "xmark.octagon.fill"
        case .unknown:
            return "questionmark.circle"
        }
    }

    private var bufferIcon: String {
        switch state.bufferRisk {
        case .healthy:
            return "checkmark.circle.fill"
        case .warning:
            return "exclamationmark.triangle.fill"
        case .critical, .mustDegradeOrStop:
            return "xmark.octagon.fill"
        }
    }

    private func actionIcon(for status: HealthActionStatus) -> String {
        switch status {
        case .notStarted:
            return "circle"
        case .running:
            return "arrow.triangle.2.circlepath"
        case .passed:
            return "checkmark.circle.fill"
        case .failed:
            return "xmark.octagon.fill"
        case .degraded:
            return "exclamationmark.circle.fill"
        }
    }

    private func actionLine(for action: HealthActionState) -> String {
        switch action.status {
        case .notStarted:
            return "Not started"
        case .running:
            return "Running"
        case .passed:
            return "Passed"
        case .failed:
            if let note = action.note {
                return "Failed: \(AdaptiveStatusText.safeLabel(note))"
            }
            return "Failed"
        case .degraded:
            return "Degraded"
        }
    }

    private func statusIcon(_ isReady: Bool) -> String {
        isReady ? "checkmark.circle.fill" : "exclamationmark.triangle.fill"
    }

    private func deviceLine(for summary: HealthPhysicalDeviceSummary?) -> String {
        guard let summary else {
            return "Not selected"
        }
        let name = AdaptiveStatusText.safeLabel(summary.displayName)
        return "\(name) · available"
    }

    private func virtualDeviceLine(name: String, state: VirtualDeviceAvailabilityState) -> String {
        switch state {
        case .available:
            return "\(name) · visible in macOS"
        case .requiresRestart:
            return "\(name) · restart Core Audio"
        case .missing:
            return "\(name) · missing"
        case .hidden:
            return "\(name) · hidden until app route recovers"
        case .installed:
            return "\(name) · installed"
        case .unavailable:
            return "\(name) · unavailable"
        case .incompatible:
            return "\(name) · unsupported"
        }
    }

    private func routeLine(_ verification: RouteVerification) -> String {
        let status = AdaptiveStatusText.routeStatusLabel(verification.status)
        guard let reason = verification.failureReason else {
            return status
        }
        switch reason {
        case "virtual_device_visible_but_audio_path_not_implemented":
            return "\(status): virtual device is visible; real audio passthrough is not implemented yet"
        case "physical_microphone_not_selected":
            return "\(status): macOS input is not a physical microphone"
        case "physical_speaker_not_selected":
            return "\(status): macOS output is not a physical speaker"
        default:
            return "\(status): \(reason.replacingOccurrences(of: "_", with: " "))"
        }
    }

    private func browserEvidenceLine(_ evidence: BrowserTargetEvidence) -> String {
        switch evidence.status {
        case .passed:
            return "Passed: mic and speaker usable"
        case .blocked:
            return "Blocked: \(AdaptiveStatusText.safeLabel(evidence.failureReason, fallback: "Reason required"))"
        case .notAccepted:
            return "Not accepted: \(AdaptiveStatusText.safeLabel(evidence.failureReason, fallback: "Reason required"))"
        }
    }

    private func browserEvidenceIcon(_ status: BrowserTargetEvidenceStatus) -> String {
        switch status {
        case .passed:
            return "checkmark.circle.fill"
        case .blocked:
            return "xmark.octagon.fill"
        case .notAccepted:
            return "exclamationmark.triangle.fill"
        }
    }

    private func line(
        label: String,
        detail: String,
        icon: String,
        emphasis: LineEmphasis = .normal
    ) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(emphasis == .normal ? .secondary : .orange)
            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(detail)
                    .font(.body)
                    .fontWeight(emphasis == .normal ? .regular : .semibold)
                    .lineLimit(3)
                    .minimumScaleFactor(0.85)
                    .accessibilityHint(
                        detail
                    )
            }
            Spacer()
            if state.requiresAttention && emphasis != .normal {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
            }
        }
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder
    private func HeaderView(state: AudioHealthState) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Audio Health")
                .font(.headline)
            Text(AdaptiveStatusText.driverLabel(
                state.driverState,
                virtualInputState: state.virtualMicState,
                virtualOutputState: state.virtualSpeakerState
            ))
            .font(.subheadline)
            .foregroundStyle(state.requiresAttention ? .orange : .green)
            if let browser = state.activeBrowserName {
                Text("Browser: \(AdaptiveStatusText.browserLabel(browser))")
                    .font(.caption)
            }
            if let meeting = state.activeMeetingTitle {
                Text(AdaptiveStatusText.meetingLabel(meeting))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if !state.unsupportedTargets.isEmpty {
                Text(
                    "Best effort targets: \(state.unsupportedTargets.joined(separator: ", "))"
                )
                .font(.caption2)
                .foregroundStyle(.secondary)
            }
        }
    }

    private func Section(
        _ title: String,
        icon: String,
        @ViewBuilder content: () -> some View
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(.blue)
                Text(title)
                    .font(.callout)
                    .fontWeight(.semibold)
            }
            content()
        }
    }

    private enum LineEmphasis {
        case normal
        case warning
    }
}
