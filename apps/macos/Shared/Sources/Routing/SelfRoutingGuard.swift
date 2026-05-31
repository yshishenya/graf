import Foundation

public enum SelfRoutingViolationCode: String, Codable, Equatable, Sendable {
    case virtualInputSelectedAsPhysicalInput = "virtual_input_selected_as_physical_input"
    case virtualOutputSelectedAsPhysicalOutput = "virtual_output_selected_as_physical_output"
}

public struct SelfRoutingViolation: Codable, Equatable, Sendable {
    public var code: SelfRoutingViolationCode
    public var selectedDeviceId: String
    public var selectedDeviceName: String
    public var recoveryAction: String

    public init(
        code: SelfRoutingViolationCode,
        selectedDeviceId: String,
        selectedDeviceName: String,
        recoveryAction: String
    ) {
        self.code = code
        self.selectedDeviceId = selectedDeviceId
        self.selectedDeviceName = selectedDeviceName
        self.recoveryAction = recoveryAction
    }
}

public enum SelfRoutingDecision: Codable, Equatable, Sendable {
    case allowed
    case rejected(SelfRoutingViolation)
}

public struct SelfRoutingGuard: Sendable {
    public static let microphoneDisplayName = "2brain Rec Microphone"
    public static let speakerDisplayName = "2brain Rec Speaker"
    public static let microphoneUID = "pro.2brain.rec.microphone"
    public static let speakerUID = "pro.2brain.rec.speaker"

    public init() {}

    public func leakageStatus(for measurement: LeakageMeasurement) -> MeasurementStatus {
        measurement.relativeLeakageDb <= -45
            && measurement.intelligibilityStatus == .notIntelligible
            ? .passed
            : .degraded
    }

    public func evaluate(
        physicalInput: PhysicalAudioDevice?,
        physicalOutput: PhysicalAudioDevice?
    ) -> SelfRoutingDecision {
        if let physicalInput, matchesVirtualMicrophone(physicalInput) {
            return .rejected(
                SelfRoutingViolation(
                    code: .virtualInputSelectedAsPhysicalInput,
                    selectedDeviceId: physicalInput.id,
                    selectedDeviceName: physicalInput.displayName,
                    recoveryAction: "select_physical_microphone"
                )
            )
        }

        if let physicalOutput, matchesVirtualSpeaker(physicalOutput) {
            return .rejected(
                SelfRoutingViolation(
                    code: .virtualOutputSelectedAsPhysicalOutput,
                    selectedDeviceId: physicalOutput.id,
                    selectedDeviceName: physicalOutput.displayName,
                    recoveryAction: "select_physical_speaker"
                )
            )
        }

        return .allowed
    }

    public func matchesVirtualMicrophone(_ device: PhysicalAudioDevice) -> Bool {
        matches(device, knownIdentifiers: [Self.microphoneDisplayName, Self.microphoneUID])
    }

    public func matchesVirtualSpeaker(_ device: PhysicalAudioDevice) -> Bool {
        matches(device, knownIdentifiers: [Self.speakerDisplayName, Self.speakerUID])
    }

    private func matches(_ device: PhysicalAudioDevice, knownIdentifiers: [String]) -> Bool {
        let normalizedDeviceId = normalize(device.id)
        let normalizedDeviceName = normalize(device.displayName)

        return knownIdentifiers.contains { identifier in
            let normalizedIdentifier = normalize(identifier)
            return normalizedDeviceId == normalizedIdentifier || normalizedDeviceName == normalizedIdentifier
        }
    }

    private func normalize(_ value: String) -> String {
        value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}
