import Foundation
import TwoBrainRecShared

public enum CaptureRecoveryState: String, Codable, Sendable {
    case noSessionToRecover = "no_session_to_recover"
    case noRecoveryNeeded = "no_recovery_needed"
    case recoveredStoppedSession = "recovered_stopped_session"
    case recoveredDegradedSession = "recovered_degraded_session"
    case recoveryNotPossible = "recovery_not_possible"
}

public struct CaptureRecoveryOutcome: Equatable, Sendable {
    public let state: CaptureRecoveryState
    public let session: CaptureSession?
    public let tracks: [AudioTrack]
    public let retainedBufferItems: [LocalBufferItem]
    public let requiresUserReview: Bool
    public let visibleMessage: String
}

public final class CaptureRecoveryService {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock

    public init(clock: @escaping Clock = Date.init) {
        self.clock = clock
    }

    public func recover(
        session: CaptureSession?,
        tracks: [AudioTrack],
        retainedBufferItems: [LocalBufferItem]
    ) -> CaptureRecoveryOutcome {
        guard let session else {
            return CaptureRecoveryOutcome(
                state: .noSessionToRecover,
                session: nil,
                tracks: tracks,
                retainedBufferItems: retainableItems(from: retainedBufferItems),
                requiresUserReview: false,
                visibleMessage: "No active session found. Nothing to recover."
            )
        }

        guard isRecoverable(session.state) else {
            return CaptureRecoveryOutcome(
                state: .noRecoveryNeeded,
                session: session,
                tracks: tracks,
                retainedBufferItems: retainableItems(from: retainedBufferItems),
                requiresUserReview: false,
                visibleMessage: "Session is already finalized. Recovery not required."
            )
        }

        var updatedSession = session
        var updatedTracks = tracks
        let requiresUserReview = !tracks.allSatisfy {
            $0.state == .finalized || $0.state == .missing
        }
        let preservedBufferCount = retainedBufferItems.count

        switch session.state {
        case .active, .paused, .degraded, .starting, .stopping:
            updatedSession = markAbortedAndStopped(session: updatedSession)
            updatedTracks = updatedTracks.map(normalizeInterruptedTrack)
            let message = [
                "Capture was interrupted by app restart.",
                "Local buffer items preserved: \(preservedBufferCount)",
                "Complete session stop manually before deleting artifacts."
            ].joined(separator: " ")

            return CaptureRecoveryOutcome(
                state: .recoveredStoppedSession,
                session: updatedSession,
                tracks: updatedTracks,
                retainedBufferItems: retainableItems(from: retainedBufferItems),
                requiresUserReview: requiresUserReview,
                visibleMessage: message
            )
        case .detecting, .ready, .idle:
            updatedSession = markAbortedAndStopped(session: updatedSession)
            updatedTracks = updatedTracks.map(normalizeInterruptedTrack)
            return CaptureRecoveryOutcome(
                state: .recoveredDegradedSession,
                session: updatedSession,
                tracks: updatedTracks,
                retainedBufferItems: retainableItems(from: retainedBufferItems),
                requiresUserReview: requiresUserReview,
                visibleMessage: """
                    Capture did not reach stable running state before restart.
                    Pending buffers were kept and can be finalized only after review.
                    """
            )
        default:
            return CaptureRecoveryOutcome(
                state: .recoveryNotPossible,
                session: session,
                tracks: tracks,
                retainedBufferItems: retainableItems(from: retainedBufferItems),
                requiresUserReview: false,
                visibleMessage: "Recovery is not supported for this session state."
            )
        }
    }

    public func failClosedForIndicatorLoss(_ session: CaptureSession) -> CaptureSession {
        var updated = session
        if isRecoverable(session.state) || session.state == .active || session.state == .stopping {
            updated.state = .failed
            updated.stoppedAt = clock()
            updated.visibleIndicatorState = .error
            updated.stopActionAvailable = false
            updated.stopReason = .indicatorLost
            updated.failureCategory = .indicatorUnavailable
        }
        return updated
    }

    private func isRecoverable(_ state: CaptureSessionState) -> Bool {
        switch state {
        case .active, .paused, .degraded, .starting, .stopping, .ready, .detecting:
            return true
        default:
            return false
        }
    }

    private func markAbortedAndStopped(session: CaptureSession) -> CaptureSession {
        var updated = session
        updated.state = .stopped
        updated.stoppedAt = clock()
        updated.visibleIndicatorState = .error
        updated.stopActionAvailable = false
        updated.stopReason = .appRestarted
        return updated
    }

    private func normalizeInterruptedTrack(_ track: AudioTrack) -> AudioTrack {
        var result = track
        if result.state == .capturing || result.state == .pending || result.state == .degraded {
            result.state = .degraded
            result.finalizedAt = clock()
        }
        return result
    }

    private func retainableItems(from items: [LocalBufferItem]) -> [LocalBufferItem] {
        items.filter { item in
            item.uploadState != .uploaded
        }
    }
}
