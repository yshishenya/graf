import Foundation
import TwoBrainRecShared

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
}
