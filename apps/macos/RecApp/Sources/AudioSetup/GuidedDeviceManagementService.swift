import TwoBrainRecShared

public enum GuidedDeviceManagementDecision: Equatable, Sendable {
    case requiresExplicitApproval
    case applied(GuidedRouteChange)
    case rejected(SelfRoutingViolation)
}

public struct GuidedRouteChange: Codable, Equatable, Sendable {
    public var physicalInputId: String
    public var physicalOutputId: String
    public var virtualInputId: String
    public var virtualOutputId: String
    public var previousInputId: String?
    public var previousOutputId: String?
    public var reversible: Bool

    public init(
        physicalInputId: String,
        physicalOutputId: String,
        virtualInputId: String = SelfRoutingGuard.microphoneUID,
        virtualOutputId: String = SelfRoutingGuard.speakerUID,
        previousInputId: String?,
        previousOutputId: String?,
        reversible: Bool = true
    ) {
        self.physicalInputId = physicalInputId
        self.physicalOutputId = physicalOutputId
        self.virtualInputId = virtualInputId
        self.virtualOutputId = virtualOutputId
        self.previousInputId = previousInputId
        self.previousOutputId = previousOutputId
        self.reversible = reversible
    }
}

public struct GuidedDeviceManagementService: Sendable {
    private let selfRoutingGuard: SelfRoutingGuard

    public init(selfRoutingGuard: SelfRoutingGuard = SelfRoutingGuard()) {
        self.selfRoutingGuard = selfRoutingGuard
    }

    public func prepareRoute(
        physicalInput: PhysicalAudioDevice?,
        physicalOutput: PhysicalAudioDevice?,
        previousInputId: String?,
        previousOutputId: String?,
        userApproved: Bool
    ) -> GuidedDeviceManagementDecision {
        guard userApproved else {
            return .requiresExplicitApproval
        }

        switch selfRoutingGuard.evaluate(physicalInput: physicalInput, physicalOutput: physicalOutput) {
        case let .rejected(violation):
            return .rejected(violation)
        case .allowed:
            break
        }

        guard let physicalInput, let physicalOutput else {
            return .requiresExplicitApproval
        }

        return .applied(
            GuidedRouteChange(
                physicalInputId: physicalInput.id,
                physicalOutputId: physicalOutput.id,
                previousInputId: previousInputId,
                previousOutputId: previousOutputId
            )
        )
    }
}
