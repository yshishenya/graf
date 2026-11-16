import Foundation

public enum LocalCacheBudgetThreshold: String, Codable, Equatable, Sendable {
    case normal
    case warning80 = "80%"
    case warning95 = "95%"
    case full
    case unknown
}

/// The effective local-cache budget. It follows the PRD baseline and is shared
/// by the status surface, the capture gate and automatic eviction.
public struct LocalCacheEvictionPolicy: Equatable, Sendable {
    public var budgetBytes: Int64
    public var warningFraction: Double
    public var criticalFraction: Double
    public var reserveCapBytes: Int64
    public var reserveFraction: Double
    public var retentionDays: Int

    public init(
        budgetBytes: Int64 = LocalBufferPolicy.productBudgetBytes,
        warningFraction: Double = LocalBufferPolicy.productWarningFraction,
        criticalFraction: Double = LocalBufferPolicy.productCriticalFraction,
        reserveCapBytes: Int64 = LocalBufferPolicy.productReserveCapBytes,
        reserveFraction: Double = LocalBufferPolicy.productReserveFraction,
        retentionDays: Int = LocalBufferPolicy.productRetentionDays
    ) {
        self.budgetBytes = max(0, budgetBytes)
        self.warningFraction = min(max(warningFraction, 0), 1)
        self.criticalFraction = min(max(criticalFraction, self.warningFraction), 1)
        self.reserveCapBytes = max(0, reserveCapBytes)
        self.reserveFraction = min(max(reserveFraction, 0), 1)
        self.retentionDays = max(0, retentionDays)
    }

    public static let productBaseline = LocalCacheEvictionPolicy()

    public var warningBytes: Int64 {
        Int64((Double(budgetBytes) * warningFraction).rounded(.down))
    }

    public var criticalBytes: Int64 {
        Int64((Double(budgetBytes) * criticalFraction).rounded(.down))
    }

    public func resolvedReserveBytes(diskCapacityBytes: Int64?) -> Int64 {
        guard let diskCapacityBytes, diskCapacityBytes > 0 else { return reserveCapBytes }
        let fraction = Int64((Double(diskCapacityBytes) * reserveFraction).rounded(.down))
        return min(reserveCapBytes, max(0, fraction))
    }

    public func threshold(
        usedBytes: Int64,
        freeDiskBytes: Int64?,
        diskCapacityBytes: Int64?
    ) -> LocalCacheBudgetThreshold {
        guard usedBytes >= 0, let freeDiskBytes else { return .unknown }
        if usedBytes >= budgetBytes ||
            freeDiskBytes <= resolvedReserveBytes(diskCapacityBytes: diskCapacityBytes) {
            return .full
        }
        if usedBytes >= criticalBytes { return .warning95 }
        if usedBytes >= warningBytes { return .warning80 }
        return .normal
    }
}

public struct LocalCacheEvictionSettingSnapshot: Equatable, Sendable {
    public let userEnabled: Bool
    public let operatorDisabled: Bool

    public init(userEnabled: Bool, operatorDisabled: Bool) {
        self.userEnabled = userEnabled
        self.operatorDisabled = operatorDisabled
    }

    public var effectiveEnabled: Bool {
        userEnabled && !operatorDisabled
    }
}

public enum LocalCacheEvictionSettings {
    public static let userDefaultsKey = "localCache.autoEvictionEnabled"
    public static let operatorEnvironmentKey = "GRAF_DISABLE_LOCAL_CACHE_AUTO_EVICTION"

    public static func userEnabled(defaults: UserDefaults = .standard) -> Bool {
        guard defaults.object(forKey: userDefaultsKey) != nil else { return true }
        return defaults.bool(forKey: userDefaultsKey)
    }

    public static func operatorDisabled(
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> Bool {
        isTruthy(environment[operatorEnvironmentKey])
    }

    public static func isTruthy(_ raw: String?) -> Bool {
        ["1", "true", "yes"].contains(
            raw?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() ?? ""
        )
    }

    public static func snapshot(
        defaults: UserDefaults = .standard,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> LocalCacheEvictionSettingSnapshot {
        LocalCacheEvictionSettingSnapshot(
            userEnabled: userEnabled(defaults: defaults),
            operatorDisabled: operatorDisabled(environment: environment)
        )
    }
}

public struct LocalCacheStatusPresentation: Equatable, Sendable {
    public let usedBytes: Int64
    public let budgetBytes: Int64
    public let freeDiskBytes: Int64?
    public let diskCapacityBytes: Int64?
    public let threshold: LocalCacheBudgetThreshold
    public let settings: LocalCacheEvictionSettingSnapshot
    public let lastFreedBytes: Int64?

    public init(
        usedBytes: Int64,
        budgetBytes: Int64,
        freeDiskBytes: Int64?,
        diskCapacityBytes: Int64?,
        threshold: LocalCacheBudgetThreshold,
        settings: LocalCacheEvictionSettingSnapshot,
        lastFreedBytes: Int64? = nil
    ) {
        self.usedBytes = max(0, usedBytes)
        self.budgetBytes = max(0, budgetBytes)
        self.freeDiskBytes = freeDiskBytes
        self.diskCapacityBytes = diskCapacityBytes
        self.threshold = threshold
        self.settings = settings
        self.lastFreedBytes = lastFreedBytes
    }

    public var showsWarning: Bool {
        threshold == .warning80 || threshold == .warning95 || threshold == .full
    }

    /// The "will be cleaned automatically" warning is only truthful while the
    /// effective kill switch is on; disabled states use their own copy.
    public var showsAutomaticCleanupWarning: Bool {
        showsWarning && settings.effectiveEnabled
    }

    public var disabledExplanation: String? {
        if settings.operatorDisabled { return LocalCacheCleanupCopy.autoEvictionOperatorOverride }
        if !settings.userEnabled { return LocalCacheCleanupCopy.autoEvictionDisabled }
        return nil
    }
}
