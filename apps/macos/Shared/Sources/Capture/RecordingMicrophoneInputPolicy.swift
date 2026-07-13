import Foundation

public struct RecordingMicrophoneInputPolicy: Sendable {
    public init() {}

    public func workingDeviceKind(for device: PhysicalAudioDevice?) -> PhysicalWorkingDeviceKind {
        guard let device else { return .unknown }
        let normalizedId = normalize(device.id)
        let normalizedName = normalize(device.displayName)

        if device.deviceClass == .aggregate ||
            normalizedName.contains("aggregate") ||
            normalizedId.contains("aggregate") {
            return .aggregate
        }
        if device.deviceClass == .multiOutput ||
            normalizedName.contains("multi-output") ||
            normalizedName.contains("multi output") ||
            normalizedId.contains("multi-output") ||
            normalizedId.contains("multi_output") {
            return .multiOutput
        }
        if device.deviceClass == .otherVirtual ||
            normalizedName.contains("virtual") ||
            normalizedId.contains("virtual") ||
            normalizedName.contains("blackhole") ||
            normalizedName.contains("soundflower") {
            return .otherVirtual
        }
        if device.deviceClass == .bluetooth || device.deviceClass == .airpodsClass {
            return .bluetooth
        }
        if [.builtIn, .wired, .usb].contains(device.deviceClass) {
            return .physical
        }
        return .unknown
    }

    public func rejectionReason(
        for workingKind: PhysicalWorkingDeviceKind
    ) -> RecordingMicrophoneSelectionRejectionReason? {
        switch workingKind {
        case .physical, .bluetooth:
            return nil
        case .otherVirtual, .aggregate, .multiOutput:
            return .unsupportedVirtualInput
        case .unknown:
            return .inputIdentityUnproven
        }
    }

    private func normalize(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}
