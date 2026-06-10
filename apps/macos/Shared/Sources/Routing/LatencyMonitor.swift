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
        case .aggregate, .multiOutput, .hdmiAirplay, .otherVirtual, .unknown:
            return .unknown
        }
    }

    public func measurementStatus(for measurement: LatencyMeasurement) -> MeasurementStatus {
        switch measurement.routeClass {
        case .builtIn, .wired, .usb:
            return measurement.addedLatencyMs <= builtInWiredThresholdMs ? .passed : .degraded
        case .bluetooth, .airpodsClass, .aggregate, .multiOutput, .hdmiAirplay, .otherVirtual, .unknown:
            return .blocked
        }
    }
}
