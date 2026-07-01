public struct LocalBufferPolicy: Codable, Equatable, Sendable {
    public var maxBytesPerDevice: Int64
    public var warningFraction: Double
    public var criticalFraction: Double
    public var minimumDiskReserveBytes: Int64
    public var retentionDays: Int

    public init(
        maxBytesPerDevice: Int64,
        warningFraction: Double,
        criticalFraction: Double,
        minimumDiskReserveBytes: Int64,
        retentionDays: Int
    ) {
        self.maxBytesPerDevice = maxBytesPerDevice
        self.warningFraction = warningFraction
        self.criticalFraction = criticalFraction
        self.minimumDiskReserveBytes = minimumDiskReserveBytes
        self.retentionDays = retentionDays
    }
}

public enum LocalBufferRiskState: String, Codable, Sendable {
    case healthy
    case warning
    case critical
    case mustDegradeOrStop = "must_degrade_or_stop"
}

public protocol LocalBufferWriting {
    func riskState(usedBytes: Int64, freeDiskBytes: Int64, policy: LocalBufferPolicy) -> LocalBufferRiskState
}
