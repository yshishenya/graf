import Foundation

public enum LowResourcePromotionStatus: String, Codable, Sendable {
    case promoted
    case fallback
    case blocked
}

public struct LowResourcePromotionDecision: Codable, Equatable, Sendable {
    public var status: LowResourcePromotionStatus
    public var decidedAt: Date
    public var reason: String
    public var fallbackBaseline: String

    public init(
        status: LowResourcePromotionStatus,
        decidedAt: Date,
        reason: String,
        fallbackBaseline: String = "005-macos-passthrough-release-hardening"
    ) {
        self.status = status
        self.decidedAt = decidedAt
        self.reason = reason
        self.fallbackBaseline = fallbackBaseline
    }

    public var shouldUseFallback: Bool {
        status != .promoted
    }
}

public struct LowResourcePromotionGate: Sendable {
    private let now: @Sendable () -> Date

    public init(now: @escaping @Sendable () -> Date = Date.init) {
        self.now = now
    }

    public func decision(for validationRun: LowResourceValidationRun?) -> LowResourcePromotionDecision {
        guard let validationRun else {
            return LowResourcePromotionDecision(
                status: .fallback,
                decidedAt: now(),
                reason: "low_resource_acceptance_missing"
            )
        }

        guard validationRun.result == .passed else {
            return LowResourcePromotionDecision(
                status: .fallback,
                decidedAt: now(),
                reason: "validation_run_not_passed"
            )
        }
        guard validationRun.startupAttempts.allSatisfy(\.isWithinAcceptedWindow) else {
            return LowResourcePromotionDecision(
                status: .fallback,
                decidedAt: now(),
                reason: "startup_attempt_exceeded_3000_ms"
            )
        }
        guard validationRun.realtimeSafety.result == .passed else {
            return LowResourcePromotionDecision(
                status: .fallback,
                decidedAt: now(),
                reason: "realtime_safety_not_passed"
            )
        }
        guard validationRun.routeTruthSnapshots.allSatisfy({ snapshot in
            let state = LowResourceRouteTruthEvaluator.readinessState(for: snapshot)
            return state != .blocked && state != .failed
        }) else {
            return LowResourcePromotionDecision(
                status: .fallback,
                decidedAt: now(),
                reason: "route_truth_blocked_or_failed"
            )
        }

        return LowResourcePromotionDecision(
            status: .promoted,
            decidedAt: now(),
            reason: "all_p1_gates_passed"
        )
    }
}
