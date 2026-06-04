import Foundation
import TwoBrainRecShared

public struct LocalRecordingManifestService: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock
    private let encoder: JSONEncoder

    public init(clock: @escaping Clock = Date.init) {
        self.clock = clock
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder
    }

    public func manifest(
        sessionId: String,
        directoryId: String,
        startedAt: Date,
        stoppedAt: Date,
        tracks: [LocalRecordingTrack],
        failureReason: LocalRecordingFailureReason = .none,
        routeSessionId: String? = nil,
        autorepairAttemptIds: [String] = [],
        routeInterruptionCategory: RouteInterruptionCategory = .none
    ) -> LocalRecordingManifest {
        let hasBothRoles = Set(tracks.map(\.role)) == Set([.localMic, .remoteSpeaker])
        let complete = hasBothRoles && tracks.allSatisfy(\.isMediaScribeReady)
        let status: LocalRecordingSessionStatus = if complete {
            .saved
        } else if tracks.contains(where: { $0.status == .failed }) {
            .failed
        } else {
            .degraded
        }
        let readiness: TranscriptionReadinessState = if complete {
            .ready
        } else if status == .failed {
            .failed
        } else {
            .degraded
        }
        let resolvedFailure: LocalRecordingFailureReason = complete ? .none : Self.resolveFailureReason(
            tracks: tracks,
            fallback: failureReason
        )

        return LocalRecordingManifest(
            sessionId: sessionId,
            createdAt: clock(),
            startedAt: startedAt,
            stoppedAt: stoppedAt,
            status: status,
            directoryId: directoryId,
            transcriptionReadiness: readiness,
            mediaScribeSourceMode: "dual",
            tracks: tracks,
            failureReason: resolvedFailure,
            recordingTimelineEvidence: routeTimelineEvidence(
                routeSessionId: routeSessionId,
                tracks: tracks,
                autorepairAttemptIds: autorepairAttemptIds,
                interruptionCategory: routeInterruptionCategory
            )
        )
    }

    public func write(_ manifest: LocalRecordingManifest, to url: URL) throws {
        let data = try encoder.encode(manifest)
        try data.write(to: url, options: [.atomic])
    }

    private static func resolveFailureReason(
        tracks: [LocalRecordingTrack],
        fallback: LocalRecordingFailureReason
    ) -> LocalRecordingFailureReason {
        if fallback != .none {
            return fallback
        }
        if tracks.contains(where: { !$0.timelineAligned }) {
            return .timelineMisaligned
        }
        if tracks.contains(where: { $0.isComplete && !$0.isMediaScribeReady }) {
            return .formatNotReady
        }
        return .emptyRequiredTrack
    }

    private func routeTimelineEvidence(
        routeSessionId: String?,
        tracks: [LocalRecordingTrack],
        autorepairAttemptIds: [String],
        interruptionCategory: RouteInterruptionCategory
    ) -> RecordingTimelineIntegrityEvidence? {
        guard let routeSessionId else { return nil }
        let micDurationMs = tracks.first { $0.role == .localMic }?.durationMs ?? 0
        let incomingDurationMs = tracks.first { $0.role == .remoteSpeaker }?.durationMs ?? 0
        return RecordingTimelineEvidenceBuilder().evidence(
            routeSessionId: routeSessionId,
            autorepairAttemptIds: autorepairAttemptIds,
            microphoneDurationMs: micDurationMs,
            incomingDurationMs: incomingDurationMs,
            interruptionCategory: interruptionCategory
        )
    }
}
