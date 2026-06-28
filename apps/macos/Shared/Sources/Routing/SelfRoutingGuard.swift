import Foundation

public enum SelfRoutingViolationCode: String, Codable, Equatable, Sendable {
    case virtualInputSelectedAsPhysicalInput = "virtual_input_selected_as_physical_input"
    case virtualOutputSelectedAsPhysicalOutput = "virtual_output_selected_as_physical_output"
    case unsupportedWorkingInput = "unsupported_working_input"
    case unsupportedWorkingOutput = "unsupported_working_output"
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
    public static let microphoneDisplayName = "GRAF Microphone"
    public static let speakerDisplayName = "GRAF Speaker"
    public static let microphoneUID = "pro.2brain.graf.microphone"
    public static let speakerUID = "pro.2brain.graf.speaker"

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

    public func workingDeviceKind(for device: PhysicalAudioDevice?) -> PhysicalWorkingDeviceKind {
        guard let device else { return .unknown }
        let normalizedId = normalize(device.id)
        let normalizedName = normalize(device.displayName)

        if matchesVirtualMicrophone(device) || matchesVirtualSpeaker(device) {
            return .twoBrainVirtual
        }
        if normalizedName.contains("aggregate") || normalizedId.contains("aggregate") {
            return .aggregate
        }
        if normalizedName.contains("multi-output") ||
            normalizedName.contains("multi output") ||
            normalizedId.contains("multi-output") ||
            normalizedId.contains("multi_output") {
            return .multiOutput
        }
        if normalizedName.contains("virtual") ||
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

    public func physicalWorkingDeviceSelection(
        input: PhysicalAudioDevice?,
        output: PhysicalAudioDevice?
    ) -> PhysicalWorkingDeviceSelection {
        let inputKind = workingDeviceKind(for: input)
        let outputKind = workingDeviceKind(for: output)
        let rejectedReason = rejectionReason(inputKind: inputKind, outputKind: outputKind)

        return PhysicalWorkingDeviceSelection(
            inputDeviceId: input?.id ?? "none",
            inputDeviceName: input?.displayName ?? "none",
            outputDeviceId: output?.id ?? "none",
            outputDeviceName: output?.displayName ?? "none",
            inputKind: inputKind,
            outputKind: outputKind,
            selectionResult: rejectedReason == nil ? .accepted : .rejected,
            rejectionReason: rejectedReason
        )
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

    private func rejectionReason(
        inputKind: PhysicalWorkingDeviceKind,
        outputKind: PhysicalWorkingDeviceKind
    ) -> String? {
        if inputKind != .physical {
            return "input_must_be_physical_working_device"
        }
        if outputKind != .physical {
            return "output_must_be_physical_working_device"
        }
        return nil
    }
}
