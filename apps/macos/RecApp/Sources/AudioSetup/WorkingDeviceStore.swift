import Foundation
import TwoBrainRecShared

public struct LowResourceAcceptanceMetadata: Codable, Equatable, Sendable {
    public var decision: LowResourcePromotionDecision
    public var validationRunId: String?
    public var updatedAt: Date

    public init(
        decision: LowResourcePromotionDecision,
        validationRunId: String? = nil,
        updatedAt: Date
    ) {
        self.decision = decision
        self.validationRunId = validationRunId
        self.updatedAt = updatedAt
    }
}

public struct WorkingDeviceSnapshot: Codable, Equatable, Sendable {
    public var physicalInput: PhysicalAudioDevice?
    public var physicalOutput: PhysicalAudioDevice?
    public var updatedAt: Date

    public init(
        physicalInput: PhysicalAudioDevice?,
        physicalOutput: PhysicalAudioDevice?,
        updatedAt: Date
    ) {
        self.physicalInput = physicalInput
        self.physicalOutput = physicalOutput
        self.updatedAt = updatedAt
    }
}

public final class WorkingDeviceStore {
    public private(set) var snapshot: WorkingDeviceSnapshot
    public private(set) var lowResourceAcceptanceMetadata: LowResourceAcceptanceMetadata?

    public init(snapshot: WorkingDeviceSnapshot = WorkingDeviceSnapshot(physicalInput: nil, physicalOutput: nil, updatedAt: Date(timeIntervalSince1970: 0))) {
        self.snapshot = snapshot
    }

    public func update(
        physicalInput: PhysicalAudioDevice?,
        physicalOutput: PhysicalAudioDevice?,
        updatedAt: Date = Date()
    ) {
        snapshot = WorkingDeviceSnapshot(
            physicalInput: physicalInput,
            physicalOutput: physicalOutput,
            updatedAt: updatedAt
        )
    }

    public func lowResourceInvalidation(
        newPhysicalInput: PhysicalAudioDevice?,
        newPhysicalOutput: PhysicalAudioDevice?,
        detectedAt: Date = Date()
    ) -> LowResourceRecoveryEvent? {
        guard snapshot.physicalInput?.id != newPhysicalInput?.id ||
            snapshot.physicalOutput?.id != newPhysicalOutput?.id ||
            snapshot.physicalInput?.availabilityState != newPhysicalInput?.availabilityState ||
            snapshot.physicalOutput?.availabilityState != newPhysicalOutput?.availabilityState else {
            return nil
        }

        return LowResourceRecoveryPolicy().event(
            for: .physicalDeviceChanged,
            previousState: .active,
            detectedAt: detectedAt
        )
    }

    public func lowResourceSelectionEvidence(
        physicalInput: PhysicalAudioDevice? = nil,
        physicalOutput: PhysicalAudioDevice? = nil,
        guardrail: SelfRoutingGuard = SelfRoutingGuard()
    ) -> PhysicalWorkingDeviceSelection {
        guardrail.physicalWorkingDeviceSelection(
            input: physicalInput ?? snapshot.physicalInput,
            output: physicalOutput ?? snapshot.physicalOutput
        )
    }

    public func persistLowResourceAcceptance(
        decision: LowResourcePromotionDecision,
        validationRunId: String? = nil,
        updatedAt: Date = Date()
    ) {
        lowResourceAcceptanceMetadata = LowResourceAcceptanceMetadata(
            decision: decision,
            validationRunId: validationRunId,
            updatedAt: updatedAt
        )
    }
}
