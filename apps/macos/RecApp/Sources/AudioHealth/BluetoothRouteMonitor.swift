import TwoBrainRecShared

public struct BluetoothRouteMonitor: Sendable {
    public init() {}

    public func evidence(
        profileName: String,
        profileState: BluetoothProfileState,
        inputAvailable: Bool,
        outputAvailable: Bool,
        validFrameIntervalsPassed: Bool,
        oneSidedAudioEvent: Bool,
        dropoutRate: Double,
        measuredLatencyMs: Double?
    ) -> BluetoothRouteEvidence {
        BluetoothRouteEvidence(
            profileName: profileName,
            profileState: profileState,
            inputAvailable: inputAvailable,
            outputAvailable: outputAvailable,
            validFrameIntervalsPassed: validFrameIntervalsPassed,
            oneSidedAudioEvent: oneSidedAudioEvent,
            dropoutRate: dropoutRate,
            measuredLatencyMs: measuredLatencyMs
        )
    }
}
