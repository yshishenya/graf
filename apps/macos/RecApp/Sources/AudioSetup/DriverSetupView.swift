import SwiftUI
import TwoBrainRecShared

public struct DriverSetupView: View {
    public static let installButtonAccessibilityLabel = "Install audio driver"
    public static let repairButtonAccessibilityLabel = "Repair audio driver"

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
                Text("Driver Diagnostics")
                    .font(.headline)
                Spacer()
                actionButton
            }

            VStack(spacing: 10) {
                availabilityRow(title: "Driver package", stateText: Self.driverText(driverState), systemImage: iconName(for: driverState))
                availabilityRow(title: "Virtual microphone", stateText: Self.virtualDeviceText(microphoneState), systemImage: iconName(for: microphoneState))
                availabilityRow(title: "Virtual speaker", stateText: Self.virtualDeviceText(speakerState), systemImage: iconName(for: speakerState))
            }

            Text(Self.mvpBoundaryCopy)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(16)
    }

    @ViewBuilder
    private var actionButton: some View {
        Label("Parked", systemImage: "pause.circle")
            .font(.caption)
            .foregroundStyle(.secondary)
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

    public static var mvpBoundaryCopy: String {
        "System audio recording does not require these virtual devices. Driver controls are parked for future passthrough diagnostics."
    }

    public static func driverText(_ state: DriverInstallationState) -> String {
        switch state {
        case .installed:
            return "Installed, parked for MVP"
        case .requiresRestart:
            return "Restart pending, parked"
        case .needsRepair:
            return "Repair available later"
        case .needsUpdate:
            return "Update available later"
        case .incompatible:
            return "Unsupported for future driver work"
        case .uninstalling:
            return "Removing"
        case .uninstalled:
            return "Removed, not blocking recording"
        case .notInstalled:
            return "Not installed, not blocking recording"
        }
    }

    public static func virtualDeviceText(_ state: VirtualDeviceAvailabilityState) -> String {
        switch state {
        case .available:
            return "Visible for diagnostics"
        case .installed:
            return "Installed for diagnostics"
        case .requiresRestart:
            return "Not required for recording"
        case .missing:
            return "Not required for recording"
        case .hidden:
            return "Hidden, not blocking recording"
        case .unavailable:
            return "Unavailable, not blocking recording"
        case .incompatible:
            return "Unsupported for future driver work"
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
