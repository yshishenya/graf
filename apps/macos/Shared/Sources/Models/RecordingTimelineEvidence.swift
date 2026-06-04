import Foundation

public struct RecordingTimelineEvidenceBuilder: Sendable {
    public init() {}

    public func evidence(
        routeSessionId: String,
        autorepairAttemptIds: [String] = [],
        microphoneDurationMs: Int,
        incomingDurationMs: Int,
        interruptionCategory: RouteInterruptionCategory
    ) -> RecordingTimelineIntegrityEvidence {
        RecordingTimelineIntegrityEvidence(
            routeSessionId: routeSessionId,
            autorepairAttemptIds: autorepairAttemptIds,
            micDurationSeconds: Double(microphoneDurationMs) / 1_000,
            incomingDurationSeconds: Double(incomingDurationMs) / 1_000,
            interruptionCategory: interruptionCategory
        )
    }
}
