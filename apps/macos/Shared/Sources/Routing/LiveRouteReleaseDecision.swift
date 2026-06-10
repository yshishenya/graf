import Foundation

public struct LiveRouteReleasePolicy: Sendable {
    private let activityPolicy: LiveRouteClientActivityPolicy

    public init(activityPolicy: LiveRouteClientActivityPolicy = LiveRouteClientActivityPolicy()) {
        self.activityPolicy = activityPolicy
    }

    public func decision(
        for snapshot: ClientActivitySnapshot?,
        requestedReason: RouteReleaseReason,
        decidedAt: Date
    ) -> RouteReleaseDecision {
        guard let snapshot else {
            return RouteReleaseDecision(
                outcome: .denied,
                reason: .deniedAmbiguousEvidence,
                clientEvidenceFresh: false,
                decidedAt: decidedAt
            )
        }

        if activityPolicy.shouldPreserveRoute(for: snapshot) {
            return RouteReleaseDecision(
                outcome: .keepActive,
                reason: .deniedActiveClient,
                clientEvidenceFresh: true,
                decidedAt: decidedAt
            )
        }

        if activityPolicy.status(for: snapshot) == .stale {
            return RouteReleaseDecision(
                outcome: .denied,
                reason: .deniedStaleEvidence,
                clientEvidenceFresh: false,
                decidedAt: decidedAt
            )
        }

        return RouteReleaseDecision(
            outcome: .released,
            reason: requestedReason,
            clientEvidenceFresh: true,
            decidedAt: decidedAt
        )
    }
}
