import Foundation
import TwoBrainRecShared

public struct CaptureTrackFinalizationResult: Sendable {
    public let session: CaptureSession
    public let finalizedTracks: [AudioTrack]
    public let missingRoles: Set<AudioTrackRole>
    public let degradedRoles: Set<AudioTrackRole>
    public let requiresReview: Bool
}

public final class CaptureFinalizationService {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock
    private let requiredRolesByMode: [CaptureMode: Set<AudioTrackRole>]

    public init(
        clock: @escaping Clock = Date.init,
        requiredRolesByMode: [CaptureMode: Set<AudioTrackRole>] = [
            .audioRecording: [.localMic, .remoteSpeaker],
            .transcriptOnly: [.localMic, .remoteSpeaker]
        ]
    ) {
        self.clock = clock
        self.requiredRolesByMode = requiredRolesByMode
    }

    public func finalize(
        session: CaptureSession,
        tracks: [AudioTrack],
        streamHealth: [StreamHealthEvidence] = []
    ) -> CaptureTrackFinalizationResult {
        let requiredRoles = requiredRolesByMode[session.mode] ?? [.localMic, .remoteSpeaker]
        let finalizeAt = clock()

        var current = session
        current.stoppedAt = finalizeAt

        let presentRoles = Set(
            tracks.filter { $0.sessionId == session.id && $0.state != .missing }
                .map { $0.role }
        )
        let missingRoles = requiredRoles.subtracting(presentRoles)
        let degradedRoles = Set(
            streamHealth
                .filter { requiredRoles.contains($0.track) && $0.hardFailure }
                .map(\.track)
        )

        var updatedTracks: [AudioTrack] = tracks

        for index in updatedTracks.indices {
            var track = updatedTracks[index]
            switch track.state {
            case .pending, .capturing, .degraded:
                if degradedRoles.contains(track.role) {
                    track.state = .degraded
                } else {
                    track.state = requiredRoles.contains(track.role) ? .finalized : track.state
                }
            case .missing, .finalized:
                break
            }
            track.finalizedAt = finalizeAt
            updatedTracks[index] = track
        }

        if !missingRoles.isEmpty || !degradedRoles.isEmpty {
            current.state = .degraded
            current.visibleIndicatorState = .degraded
            current.stopActionAvailable = false
        } else {
            current.state = .finalized
            current.visibleIndicatorState = .hidden
            current.stopActionAvailable = false
        }

        return CaptureTrackFinalizationResult(
            session: current,
            finalizedTracks: updatedTracks,
            missingRoles: missingRoles,
            degradedRoles: degradedRoles,
            requiresReview: !missingRoles.isEmpty || !degradedRoles.isEmpty
        )
    }

    public func missingTrackRoles(
        for mode: CaptureMode,
        from tracks: [AudioTrack]
    ) -> Set<AudioTrackRole> {
        let requiredRoles = requiredRolesByMode[mode] ?? [.localMic, .remoteSpeaker]
        let presentRoles = Set(
            tracks.filter { $0.state != .missing }
                .map { $0.role }
        )
        return requiredRoles.subtracting(presentRoles)
    }
}
