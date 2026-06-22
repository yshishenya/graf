import Foundation
import TwoBrainRecShared

public struct WebRTCAEC3AdapterReport: Codable, Equatable, Sendable {
    public var candidateId: String
    public var candidateKind: WebRTCAEC3CandidateKind
    public var dependencyReadiness: WebRTCAEC3DependencyReadiness
    public var referenceStatus: WebRTCAEC3ReferenceStatus
    public var timingStatus: WebRTCAEC3CaptureTimingStatus
    public var metricsStatus: WebRTCAEC3MetricsStatus
    public var diagnosticSafe: Bool
    public var failureReason: WebRTCAEC3FailureReason?

    public init(
        candidateId: String,
        candidateKind: WebRTCAEC3CandidateKind,
        dependencyReadiness: WebRTCAEC3DependencyReadiness,
        referenceStatus: WebRTCAEC3ReferenceStatus,
        timingStatus: WebRTCAEC3CaptureTimingStatus,
        metricsStatus: WebRTCAEC3MetricsStatus,
        diagnosticSafe: Bool = true,
        failureReason: WebRTCAEC3FailureReason? = nil
    ) {
        self.candidateId = candidateId
        self.candidateKind = candidateKind
        self.dependencyReadiness = dependencyReadiness
        self.referenceStatus = referenceStatus
        self.timingStatus = timingStatus
        self.metricsStatus = metricsStatus
        self.diagnosticSafe = diagnosticSafe
        self.failureReason = failureReason
    }
}

public protocol WebRTCAEC3Adapter: Sendable {
    func readinessReport(candidateId: String) -> WebRTCAEC3AdapterReport
}

public struct UnavailableWebRTCAEC3Adapter: WebRTCAEC3Adapter {
    public init() {}

    public func readinessReport(candidateId: String) -> WebRTCAEC3AdapterReport {
        WebRTCAEC3AdapterReport(
            candidateId: candidateId,
            candidateKind: .adapterUnavailable,
            dependencyReadiness: .unavailable,
            referenceStatus: .unknown,
            timingStatus: .unknown,
            metricsStatus: .notAvailable,
            diagnosticSafe: true,
            failureReason: .dependencyUnavailable
        )
    }
}
