import SwiftUI
import TwoBrainRecShared

public struct DriverSetupView: View {
    private let driverState: DriverInstallationState
    private let microphoneState: VirtualDeviceAvailabilityState
    private let speakerState: VirtualDeviceAvailabilityState
    private let onInstall: () -> Void
    private let onRepair: () -> Void

    public init(
        driverState: DriverInstallationState,
        microphoneState: VirtualDeviceAvailabilityState,
        speakerState: VirtualDeviceAvailabilityState,
        onInstall: @escaping () -> Void,
        onRepair: @escaping () -> Void
    ) {
        self.driverState = driverState
        self.microphoneState = microphoneState
        self.speakerState = speakerState
        self.onInstall = onInstall
        self.onRepair = onRepair
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Audio Driver")
                    .font(.headline)
                Spacer()
                actionButton
            }

            VStack(spacing: 10) {
                availabilityRow(title: "Driver package", stateText: driverText(driverState), systemImage: iconName(for: driverState))
                availabilityRow(title: "Virtual microphone", stateText: virtualDeviceText(microphoneState), systemImage: iconName(for: microphoneState))
                availabilityRow(title: "Virtual speaker", stateText: virtualDeviceText(speakerState), systemImage: iconName(for: speakerState))
            }

            Text("Visible devices mean macOS loaded the driver. Audio passthrough still needs a separate readiness check.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(16)
    }

    @ViewBuilder
    private var actionButton: some View {
        switch driverState {
        case .notInstalled, .uninstalled:
            Button("Install", action: onInstall)
        case .needsRepair, .needsUpdate, .incompatible:
            Button("Repair", action: onRepair)
        case .requiresRestart:
            Label("Restart Required", systemImage: "arrow.clockwise.circle")
        case .installed, .uninstalling:
            EmptyView()
        }
    }

    private func availabilityRow(title: String, stateText: String, systemImage: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: systemImage)
                .frame(width: 18)
            Text(title)
                .font(.subheadline)
                .fontWeight(.medium)
            Spacer()
            Text(stateText)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .accessibilityElement(children: .combine)
    }

    private func driverText(_ state: DriverInstallationState) -> String {
        switch state {
        case .installed:
            return "Installed"
        case .requiresRestart:
            return "Installed, restart Core Audio"
        case .needsRepair:
            return "Repair needed"
        case .needsUpdate:
            return "Update needed"
        case .incompatible:
            return "Unsupported on this Mac"
        case .uninstalling:
            return "Removing"
        case .uninstalled:
            return "Removed"
        case .notInstalled:
            return "Not installed"
        }
    }

    private func virtualDeviceText(_ state: VirtualDeviceAvailabilityState) -> String {
        switch state {
        case .available:
            return "Visible in macOS"
        case .installed:
            return "Installed"
        case .requiresRestart:
            return "Restart Core Audio"
        case .missing:
            return "Missing"
        case .hidden:
            return "Hidden until app route recovers"
        case .unavailable:
            return "Unavailable"
        case .incompatible:
            return "Unsupported"
        }
    }

    private func iconName(for state: DriverInstallationState) -> String {
        switch state {
        case .installed:
            "checkmark.circle.fill"
        case .requiresRestart:
            "arrow.clockwise.circle"
        case .needsRepair, .needsUpdate:
            "wrench.and.screwdriver.fill"
        case .incompatible, .notInstalled, .uninstalled, .uninstalling:
            "exclamationmark.circle.fill"
        }
    }

    private func iconName(for state: VirtualDeviceAvailabilityState) -> String {
        switch state {
        case .available:
            "checkmark.circle.fill"
        case .installed, .requiresRestart:
            "arrow.clockwise.circle"
        case .missing, .hidden, .unavailable, .incompatible:
            "exclamationmark.circle.fill"
        }
    }
}
