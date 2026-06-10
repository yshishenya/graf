import Foundation
import TwoBrainRecShared

public struct LiveRouteAutorepairCoordinator: Sendable {
    private let now: @Sendable () -> Date
    private let activityPolicy: LiveRouteClientActivityPolicy

    public init(
        now: @escaping @Sendable () -> Date = Date.init,
        activityPolicy: LiveRouteClientActivityPolicy = LiveRouteClientActivityPolicy()
    ) {
        self.now = now
        self.activityPolicy = activityPolicy
    }

    public func attempt(
        trigger: AutorepairTrigger,
        timingTier: AutorepairTimingTier,
        startedAt: Date,
        completedAt: Date,
        clientActivity: ClientActivitySnapshot
    ) -> AutorepairAttempt {
        let hasFreshEvidence = activityPolicy.shouldPreserveRoute(for: clientActivity)
        let duration = completedAt.timeIntervalSince(startedAt)
        let outcome: AutorepairOutcome

        if hasFreshEvidence && duration <= timingTier.acceptedRecoverySeconds {
            outcome = .succeeded
        } else if hasFreshEvidence {
            outcome = .degradedSlow
        } else {
            outcome = .degradedSlow
        }

        return AutorepairAttempt(
            attemptId: UUID().uuidString,
            trigger: trigger,
            timingTier: timingTier,
            outcome: outcome,
            startedAt: startedAt,
            completedAt: completedAt,
            freshEvidenceObservedAt: hasFreshEvidence ? completedAt : nil
        )
    }

    public func blockedAttempt(
        trigger: AutorepairTrigger,
        reason: AutorepairNonRecoverableReason
    ) -> AutorepairAttempt {
        let timestamp = now()
        return AutorepairAttempt(
            attemptId: UUID().uuidString,
            trigger: trigger,
            timingTier: .normal,
            outcome: .blockedNonRecoverable,
            startedAt: timestamp,
            completedAt: timestamp,
            nonRecoverableReason: reason
        )
    }
}
