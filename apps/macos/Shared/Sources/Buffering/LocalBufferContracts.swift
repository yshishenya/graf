public struct LocalBufferPolicy: Codable, Equatable, Sendable {
    /// PRD local-cache baseline: 5 GB per device, warning 80%, critical 95%,
    /// free-disk reserve min(10 GB, 10% of the volume), 7-day retention.
    public static let productBudgetBytes: Int64 = 5_000_000_000
    public static let productWarningFraction = 0.8
    public static let productCriticalFraction = 0.95
    public static let productReserveCapBytes: Int64 = 10_000_000_000
    public static let productReserveFraction = 0.1
    public static let productRetentionDays = 7

    public var maxBytesPerDevice: Int64
    public var warningFraction: Double
    public var criticalFraction: Double
    /// Upper bound for the free-disk reserve. The effective reserve is
    /// `min(minimumDiskReserveBytes, 10% of the volume)`.
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

    public static let productBaseline = LocalBufferPolicy(
        maxBytesPerDevice: productBudgetBytes,
        warningFraction: productWarningFraction,
        criticalFraction: productCriticalFraction,
        minimumDiskReserveBytes: productReserveCapBytes,
        retentionDays: productRetentionDays
    )

    /// Resolve the dynamic reserve without changing the configured cap.
    public func resolvedMinimumDiskReserveBytes(diskCapacityBytes: Int64?) -> Int64 {
        let cap = max(0, minimumDiskReserveBytes)
        guard let diskCapacityBytes, diskCapacityBytes > 0 else { return cap }
        let tenPercent = Int64(
            (Double(diskCapacityBytes) * Self.productReserveFraction).rounded(.down)
        )
        return min(cap, max(0, tenPercent))
    }

    public func resolved(diskCapacityBytes: Int64?) -> LocalBufferPolicy {
        var policy = self
        policy.minimumDiskReserveBytes = resolvedMinimumDiskReserveBytes(
            diskCapacityBytes: diskCapacityBytes
        )
        return policy
    }
}

public enum LocalBufferRiskState: String, Codable, Sendable {
    case healthy
    case warning
    case critical
    case mustDegradeOrStop = "must_degrade_or_stop"

    /// A warning leaves headroom for the next recording. Only critical/full
    /// states and reserve violations may block a new capture.
    public var allowsRecordingStart: Bool {
        self != .critical && self != .mustDegradeOrStop
    }
}

public protocol LocalBufferWriting {
    func riskState(usedBytes: Int64, freeDiskBytes: Int64, policy: LocalBufferPolicy) -> LocalBufferRiskState
}
