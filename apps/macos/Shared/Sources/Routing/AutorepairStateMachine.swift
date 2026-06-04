import Foundation

public enum AutorepairState: String, Codable, Sendable {
    case inactive
    case armed
    case active
    case preserving
    case recovering
    case verifyingFreshEvidence = "verifying_fresh_evidence"
    case healthyAfterFreshEvidence = "healthy_after_fresh_evidence"
    case degraded
    case blockedNonRecoverable = "blocked_non_recoverable"
    case failed
    case retryBudgetExhausted = "retry_budget_exhausted"
    case released
}

public enum AutorepairTrigger: String, Codable, Sendable {
    case coreaudiodRestart = "coreaudiod_restart"
    case halReload = "hal_reload"
    case sleepWake = "sleep_wake"
    case physicalDeviceDisappeared = "physical_device_disappeared"
    case physicalDeviceReturned = "physical_device_returned"
    case macOSDefaultRouteChanged = "macos_default_route_changed"
    case browserStreamRecreated = "browser_stream_recreated"
    case staleBrowserDeviceId = "stale_browser_device_id"
    case appRouteEngineRestart = "app_route_engine_restart"
    case unknownExternalDisruption = "unknown_external_disruption"
}

public enum AutorepairOutcome: String, Codable, Sendable {
    case notStarted = "not_started"
    case succeeded
    case degradedSlow = "degraded_slow"
    case blockedNonRecoverable = "blocked_non_recoverable"
    case failed
    case retryBudgetExhausted = "retry_budget_exhausted"
}

public enum AutorepairTimingTier: String, Codable, Sendable {
    case normal
    case osDeviceHeavy = "os_device_heavy"

    public var acceptedRecoverySeconds: Double {
        switch self {
        case .normal:
            10
        case .osDeviceHeavy:
            30
        }
    }
}

public enum AutorepairNonRecoverableReason: String, Codable, CaseIterable, Sendable {
    case permissionDenied = "permission_denied"
    case unsupportedPhysicalRoute = "unsupported_physical_route"
    case missingVirtualDevice = "missing_virtual_device"
    case missingPhysicalDevice = "missing_physical_device"
    case meetingDeviceChangedAwayFromVirtual = "meeting_device_changed_away_from_virtual"
    case recordingIndicatorUnavailable = "recording_indicator_unavailable"
}

public struct AutorepairStateMachine: Sendable {
    public init() {}

    public func canTransition(from: AutorepairState, to: AutorepairState) -> Bool {
        Self.allowedTransitions[from, default: []].contains(to)
    }

    public static let allowedTransitions: [AutorepairState: Set<AutorepairState>] = [
        .inactive: [.armed],
        .armed: [.active, .released, .blockedNonRecoverable],
        .active: [.preserving, .recovering, .released, .blockedNonRecoverable, .failed],
        .preserving: [.active, .recovering, .released],
        .recovering: [.verifyingFreshEvidence, .degraded, .blockedNonRecoverable, .failed, .retryBudgetExhausted],
        .verifyingFreshEvidence: [.healthyAfterFreshEvidence, .recovering, .degraded, .failed],
        .healthyAfterFreshEvidence: [.active, .released],
        .degraded: [.recovering, .blockedNonRecoverable, .failed, .released],
        .failed: [.recovering, .released],
        .retryBudgetExhausted: [.blockedNonRecoverable, .released],
        .blockedNonRecoverable: [.released],
        .released: [.inactive]
    ]
}

public struct AutorepairAttempt: Codable, Equatable, Sendable {
    public let attemptId: String
    public let trigger: AutorepairTrigger
    public let timingTier: AutorepairTimingTier
    public let outcome: AutorepairOutcome
    public let startedAt: Date
    public let completedAt: Date?
    public let freshEvidenceObservedAt: Date?
    public let nonRecoverableReason: AutorepairNonRecoverableReason?

    public init(attemptId: String, trigger: AutorepairTrigger, timingTier: AutorepairTimingTier, outcome: AutorepairOutcome, startedAt: Date, completedAt: Date? = nil, freshEvidenceObservedAt: Date? = nil, nonRecoverableReason: AutorepairNonRecoverableReason? = nil) {
        self.attemptId = attemptId
        self.trigger = trigger
        self.timingTier = timingTier
        self.outcome = outcome
        self.startedAt = startedAt
        self.completedAt = completedAt
        self.freshEvidenceObservedAt = freshEvidenceObservedAt
        self.nonRecoverableReason = nonRecoverableReason
    }

    public var isAcceptedSuccess: Bool {
        guard outcome == .succeeded, let completedAt else { return false }
        return freshEvidenceObservedAt != nil && completedAt.timeIntervalSince(startedAt) <= timingTier.acceptedRecoverySeconds
    }
}
