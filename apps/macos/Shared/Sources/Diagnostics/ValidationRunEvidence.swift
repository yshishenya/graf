import Foundation

public struct LiveRouteAcceptanceMatrixEntry: Codable, Equatable, Sendable {
    public let target: MeetingTarget
    public let deviceClass: PhysicalDeviceClass
    public let result: ValidationResult
    public let notes: String

    public init(target: MeetingTarget, deviceClass: PhysicalDeviceClass, result: ValidationResult, notes: String = "") {
        self.target = target
        self.deviceClass = deviceClass
        self.result = result
        self.notes = notes
    }
}

public struct ValidationRunEvidenceAggregator: Sendable {
    public init() {}

    public func aggregate(
        runId: String,
        durationGate: DurationGate,
        entries: [LiveRouteAcceptanceMatrixEntry],
        userActionCount: Int,
        startedAt: Date,
        completedAt: Date?
    ) -> ValidationRunEvidence {
        let result: ValidationResult
        if entries.isEmpty {
            result = .notTested
        } else if entries.contains(where: { $0.result == .failed }) {
            result = .failed
        } else if entries.contains(where: { $0.result == .blocked }) {
            result = .blocked
        } else if entries.contains(where: { $0.result == .degraded }) {
            result = .degraded
        } else if entries.contains(where: { $0.result == .notTested }) {
            result = .notTested
        } else if !Self.hasRequiredAcceptedCoverage(entries) {
            result = .notTested
        } else {
            result = .accepted
        }

        return ValidationRunEvidence(
            runId: runId,
            durationGate: durationGate,
            result: result,
            targetsCovered: Array(Set(entries.map(\.target))).sorted { $0.rawValue < $1.rawValue },
            deviceClassesCovered: Array(Set(entries.map(\.deviceClass))).sorted { $0.rawValue < $1.rawValue },
            userActionCount: userActionCount,
            startedAt: startedAt,
            completedAt: completedAt
        )
    }

    public static func hasRequiredAcceptedCoverage(_ entries: [LiveRouteAcceptanceMatrixEntry]) -> Bool {
        let acceptedEntries = entries.filter { $0.result == .accepted }
        let acceptedTargets = Set(acceptedEntries.map(\.target))
        let acceptedDeviceClasses = Set(acceptedEntries.map(\.deviceClass))
        return acceptedTargets.isSuperset(of: Set(MeetingTarget.allCases))
            && acceptedDeviceClasses.isSuperset(of: MacOSDefaultRouteSnapshot.acceptedDeviceClasses)
    }
}
