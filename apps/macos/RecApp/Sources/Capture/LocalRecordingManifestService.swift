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
        failureReason: LocalRecordingFailureReason = .none
    ) -> LocalRecordingManifest {
        let hasBothRoles = Set(tracks.map(\.role)) == Set([.localMic, .remoteSpeaker])
        let complete = hasBothRoles && tracks.allSatisfy(\.isComplete)
        let status: LocalRecordingSessionStatus = if complete {
            .saved
        } else if tracks.contains(where: { $0.status == .failed }) {
            .failed
        } else {
            .degraded
        }
        let resolvedFailure: LocalRecordingFailureReason = complete ? .none : (
            failureReason == .none ? .emptyRequiredTrack : failureReason
        )

        return LocalRecordingManifest(
            sessionId: sessionId,
            createdAt: clock(),
            startedAt: startedAt,
            stoppedAt: stoppedAt,
            status: status,
            directoryId: directoryId,
            tracks: tracks,
            failureReason: resolvedFailure
        )
    }

    public func write(_ manifest: LocalRecordingManifest, to url: URL) throws {
        let data = try encoder.encode(manifest)
        try data.write(to: url, options: [.atomic])
    }
}
