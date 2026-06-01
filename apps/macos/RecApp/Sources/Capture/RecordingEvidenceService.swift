import Foundation
import TwoBrainRecShared

public struct RecordingEvidenceService: Sendable {
    public typealias Clock = @Sendable () -> Date
    public typealias IdFactory = @Sendable () -> String

    private let clock: Clock
    private let idFactory: IdFactory

    public init(
        clock: @escaping Clock = Date.init,
        idFactory: @escaping IdFactory = { UUID().uuidString }
    ) {
        self.clock = clock
        self.idFactory = idFactory
    }

    public func event(
        for session: CaptureSession,
        type: RecordingEvidenceEventType,
        initiator: RecordingEvidenceInitiator,
        routeState: LivePassthroughStatus,
        blockedReason: RecordingStartBlocker = .none,
        recoveryAction: String? = nil
    ) -> RecordingEvidenceEvent {
        RecordingEvidenceEvent(
            eventId: idFactory(),
            sessionId: session.id,
            eventType: type,
            occurredAt: clock(),
            initiator: initiator,
            routeState: routeState,
            indicatorState: session.visibleIndicatorState,
            stopActionAvailable: session.stopActionAvailable,
            blockedReason: blockedReason,
            recoveryAction: recoveryAction,
            durationMs: durationMs(for: session),
            diagnosticSafe: true
        )
    }

    public func startBlocked(
        session: CaptureSession,
        prerequisite: RecordingPrerequisiteSnapshot
    ) -> RecordingEvidenceEvent {
        event(
            for: session,
            type: .startBlocked,
            initiator: .user,
            routeState: prerequisite.routeState,
            blockedReason: prerequisite.blockedReason,
            recoveryAction: prerequisite.recoveryAction
        )
    }

    private func durationMs(for session: CaptureSession) -> Int? {
        guard let startedAt = session.startedAt else {
            return nil
        }
        let end = session.stoppedAt ?? clock()
        return max(0, Int(end.timeIntervalSince(startedAt) * 1000))
    }
}
