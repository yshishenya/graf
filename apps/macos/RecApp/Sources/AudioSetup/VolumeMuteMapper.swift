import Foundation

public struct VolumeMuteState: Codable, Equatable, Sendable {
    public var volume: Double
    public var muted: Bool

    public init(volume: Double, muted: Bool) {
        self.volume = min(max(volume, 0), 1)
        self.muted = muted
    }
}

public struct VolumeMuteMapping: Codable, Equatable, Sendable {
    public var physical: VolumeMuteState
    public var virtual: VolumeMuteState
    public var captureSignalAllowed: Bool
}

public struct VolumeMuteMapper: Sendable {
    public init() {}

    public func mapPhysicalToVirtual(_ physical: VolumeMuteState) -> VolumeMuteMapping {
        VolumeMuteMapping(
            physical: physical,
            virtual: physical,
            captureSignalAllowed: false
        )
    }
}
