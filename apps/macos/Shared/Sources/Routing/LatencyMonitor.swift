import Foundation

public struct LatencyMonitor: Sendable {
    public var builtInWiredThresholdMs: Double

    public init(builtInWiredThresholdMs: Double = RouteLatencyEvidence.builtInWiredThresholdMs) {
        self.builtInWiredThresholdMs = builtInWiredThresholdMs
    }

    public func passthroughStatus(for evidence: RouteLatencyEvidence) -> PassthroughStatus {
        switch evidence.routeClass {
        case .builtIn, .wired, .usb:
            return evidence.measuredLatencyMs <= builtInWiredThresholdMs ? .healthy : .latencyExceeded
        case .bluetooth, .airpodsClass:
            return .degraded
        case .unknown:
            return .unknown
        }
    }
}
