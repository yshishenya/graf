import TwoBrainRecShared

public struct BluetoothRoutePolicy: Sendable {
    public static let dropoutThreshold = 0.005

    public init() {}

    public func passthroughStatus(for evidence: BluetoothRouteEvidence) -> PassthroughStatus {
        if evidence.profileState != .stable { return .degraded }
        if !evidence.inputAvailable || !evidence.outputAvailable { return .degraded }
        if !evidence.validFrameIntervalsPassed { return .degraded }
        if evidence.oneSidedAudioEvent { return .degraded }
        if evidence.dropoutRate > Self.dropoutThreshold { return .degraded }
        return .healthy
    }

    public func releaseReadinessStatus(for evidence: BluetoothRouteEvidence) -> MeasurementStatus {
        // Bluetooth/AirPods-class routes can be piloted, but they are not
        // equivalent to built-in/wired release-quality routes in this feature.
        passthroughStatus(for: evidence) == .healthy ? .blocked : .degraded
    }

    public func recoveryActions(for evidence: BluetoothRouteEvidence) -> [String] {
        var actions: [String] = []
        if evidence.profileState != .stable {
            actions.append("Recheck Bluetooth profile")
        }
        if !evidence.inputAvailable || !evidence.outputAvailable || evidence.oneSidedAudioEvent {
            actions.append("Select a bidirectional call-capable route")
        }
        if !evidence.validFrameIntervalsPassed || evidence.dropoutRate > Self.dropoutThreshold {
            actions.append("Switch to built-in or wired audio for release-quality route")
        }
        return actions
    }
}
