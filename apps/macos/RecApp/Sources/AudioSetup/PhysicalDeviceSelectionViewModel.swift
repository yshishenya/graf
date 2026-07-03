import TwoBrainRecShared

public enum PhysicalDeviceSelectionResult: Codable, Equatable, Sendable {
    case accepted
    case rejected(SelfRoutingViolation)
    case unavailable(String)
}

@MainActor
public final class PhysicalDeviceSelectionViewModel {
    public private(set) var availableInputs: [PhysicalAudioDevice]
    public private(set) var availableOutputs: [PhysicalAudioDevice]
    public private(set) var selectedInput: PhysicalAudioDevice?
    public private(set) var selectedOutput: PhysicalAudioDevice?
    public private(set) var lastSelectionResult: PhysicalDeviceSelectionResult

    private let selfRoutingGuard: SelfRoutingGuard

    public init(
        availableInputs: [PhysicalAudioDevice] = [],
        availableOutputs: [PhysicalAudioDevice] = [],
        selectedInput: PhysicalAudioDevice? = nil,
        selectedOutput: PhysicalAudioDevice? = nil,
        selfRoutingGuard: SelfRoutingGuard = SelfRoutingGuard()
    ) {
        self.availableInputs = availableInputs
        self.availableOutputs = availableOutputs
        self.selectedInput = selectedInput
        self.selectedOutput = selectedOutput
        self.selfRoutingGuard = selfRoutingGuard
        self.lastSelectionResult = .accepted
        self.lastSelectionResult = evaluateCurrentSelection()
    }

    public var canAttemptRouteVerification: Bool {
        selectedInput != nil && selectedOutput != nil && lastSelectionResult == .accepted
    }

    @discardableResult
    public func replaceAvailableDevices(
        inputs: [PhysicalAudioDevice],
        outputs: [PhysicalAudioDevice]
    ) -> PhysicalDeviceSelectionResult {
        availableInputs = inputs
        availableOutputs = outputs

        if let selectedInput, !inputs.contains(where: { $0.id == selectedInput.id }) {
            self.selectedInput = nil
        }
        if let selectedOutput, !outputs.contains(where: { $0.id == selectedOutput.id }) {
            self.selectedOutput = nil
        }

        lastSelectionResult = evaluateCurrentSelection()
        return lastSelectionResult
    }

    @discardableResult
    public func selectInput(id: String) -> PhysicalDeviceSelectionResult {
        guard let candidate = availableInputs.first(where: { $0.id == id }) else {
            lastSelectionResult = .unavailable(id)
            return lastSelectionResult
        }

        selectedInput = candidate
        lastSelectionResult = evaluateCurrentSelection()
        if case .rejected = lastSelectionResult {
            selectedInput = nil
        }
        return lastSelectionResult
    }

    @discardableResult
    public func selectOutput(id: String) -> PhysicalDeviceSelectionResult {
        guard let candidate = availableOutputs.first(where: { $0.id == id }) else {
            lastSelectionResult = .unavailable(id)
            return lastSelectionResult
        }

        selectedOutput = candidate
        lastSelectionResult = evaluateCurrentSelection()
        if case .rejected = lastSelectionResult {
            selectedOutput = nil
        }
        return lastSelectionResult
    }

    public func clearSelections() {
        selectedInput = nil
        selectedOutput = nil
        lastSelectionResult = .accepted
    }

    private func evaluateCurrentSelection() -> PhysicalDeviceSelectionResult {
        switch selfRoutingGuard.evaluate(physicalInput: selectedInput, physicalOutput: selectedOutput) {
        case .allowed:
            return .accepted
        case let .rejected(violation):
            return .rejected(violation)
        }
    }
}
