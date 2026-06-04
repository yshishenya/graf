import Foundation
import TwoBrainRecShared

enum LiveRouteStabilityEvidenceFixtures {
    static let sampleEvents: [RouteEvidenceEvent] = [
        LiveRouteStabilityFixtures.routeEvent(family: .routeLifecycle, name: "route.started"),
        LiveRouteStabilityFixtures.routeEvent(family: .clientActivity, name: "client_activity.fresh"),
        RouteEvidenceEvent(
            eventId: "evt-validation",
            sessionId: "route-session-019",
            family: .validationRun,
            name: "validation.accepted",
            observedAt: LiveRouteStabilityFixtures.now,
            source: .validationScript,
            routeState: .healthyAfterFreshEvidence,
            target: .chrome,
            validationRun: LiveRouteStabilityFixtures.validationRun()
        )
    ]
}
