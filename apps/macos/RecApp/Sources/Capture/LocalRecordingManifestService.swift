import Foundation
import TwoBrainRecShared

public struct LocalRecordingManifestService: Sendable {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(clock: @escaping Clock = Date.init) {
        self.clock = clock
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder
    }

    /// New capture has one canonical ASR WAV and one playback-only M4A.
    public func v5Manifest(
        sessionId: String,
        directoryId: String,
        startedAt: Date,
        stoppedAt: Date,
        tracks: [LocalRecordingTrack],
        failureReason: LocalRecordingFailureReason = .none,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil,
        microphoneSelection: RecordingMicrophoneSelection? = nil,
        microphoneStream: AppOwnedMicrophoneStreamSession? = nil,
        microphoneStreamHealth: MicrophoneStreamHealth? = nil,
        captureHealth: CaptureHealthSnapshot? = nil,
        privacySegments: [ProductPrivacySegment] = [],
        targetMuteCapability: TargetMuteCapability? = nil,
        meetingMuteTruthEvidence: [MeetingMuteTruthEvidence] = [],
        limitationCopyShownAt: Date? = nil,
        captureFailureCode: String? = nil
    ) -> LocalRecordingManifest {
        // `timeline_misaligned` is a legacy persisted value. Never create it
        // for a new package, even if an older caller passes it through.
        let persistedFailureReason = failureReason == .timelineMisaligned
            ? .captureFailed
            : failureReason
        let durationDifferenceSeconds = Self.v5DurationDifferenceSeconds(tracks: tracks)
        let hasExactV5Artifacts = tracks.count == 2 &&
            Set(tracks.map(\.role)) == Set([.mixedMeetingAudio, .reviewPlayback]) &&
            tracks.first(where: { $0.role == .mixedMeetingAudio })?.isCanonicalTranscriptionArtifact == true &&
            tracks.first(where: { $0.role == .reviewPlayback })?.isReviewPlaybackArtifact == true
        let complete = hasExactV5Artifacts &&
            scopeApproval?.isAcceptedForMeetingRecording == true &&
            permissions?.allowsAcceptedRecording == true &&
            durationDifferenceSeconds <= 0.1 &&
            persistedFailureReason == .none
        let status: LocalRecordingSessionStatus = if complete {
            .saved
        } else if Self.isBlockedFailure(persistedFailureReason) {
            .blocked
        } else if persistedFailureReason != .none || tracks.contains(where: { $0.status == .failed }) {
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
        let createdAt = clock()
        let muteTruthDecision = MuteTruthDecision.mvpDecision(
            sessionId: sessionId,
            privacySegments: privacySegments,
            targetEvidence: meetingMuteTruthEvidence,
            targetCapability: targetMuteCapability,
            decidedAt: createdAt
        )

        return LocalRecordingManifest(
            schemaVersion: LocalRecordingManifest.schemaVersion,
            sessionId: sessionId,
            createdAt: createdAt,
            startedAt: startedAt,
            stoppedAt: stoppedAt,
            finalizedAt: stoppedAt,
            status: status,
            directoryId: directoryId,
            transcriptionReadiness: readiness,
            mediaScribeSourceMode: "single_wav_v1",
            canonicalMixProfile: LocalRecordingManifest.canonicalMixProfileVersion,
            tracks: tracks,
            localDeletionRegistered: false,
            failureReason: complete ? .none : persistedFailureReason,
            captureFailureCode: captureFailureCode,
            durationDifferenceSeconds: durationDifferenceSeconds,
            scopeApproval: scopeApproval,
            permissions: permissions,
            microphoneSelection: microphoneSelection,
            microphoneStream: microphoneStream,
            microphoneStreamHealth: microphoneStreamHealth,
            captureHealth: captureHealth,
            privacySegments: privacySegments,
            meetingMuteTruth: muteTruthDecision,
            meetingMuteTruthEvidence: meetingMuteTruthEvidence,
            targetMuteCapability: targetMuteCapability,
            limitationCopyShownAt: limitationCopyShownAt
        )
    }

    public func write(_ manifest: LocalRecordingManifest, to url: URL) throws {
        let data = try encoder.encode(manifest)
        try LocalCustodyFileProtection.write(data, to: url)
    }

    public func read(from url: URL) throws -> LocalRecordingManifest {
        let data = try Data(contentsOf: url)
        let manifest = try decoder.decode(LocalRecordingManifest.self, from: data)
        return normalized(manifest)
    }

    public func normalized(_ manifest: LocalRecordingManifest) -> LocalRecordingManifest {
        guard let captureHealth = manifest.captureHealth else {
            return manifest
        }

        let failureReason = Self.resolveCaptureHealthFailureReason(for: manifest)
        let gateStatus = Self.gateStatus(for: failureReason)
        guard captureHealth.failureReason != failureReason || captureHealth.gateStatus != gateStatus else {
            return manifest
        }

        var normalizedHealth = captureHealth
        normalizedHealth.failureReason = failureReason
        normalizedHealth.gateStatus = gateStatus
        var normalizedManifest = manifest
        normalizedManifest.captureHealth = normalizedHealth
        return normalizedManifest
    }

    private static func resolveCaptureHealthFailureReason(for manifest: LocalRecordingManifest) -> LocalRecordingFailureReason {
        if manifest.failureReason != .none {
            return manifest.failureReason
        }
        if let trackReason = manifest.tracks.first(where: { $0.failureReason != .none })?.failureReason {
            return trackReason
        }
        if let microphoneReason = manifest.microphoneStreamHealth?.failureReason,
           microphoneReason != .none {
            return microphoneReason
        }
        if manifest.tracks.contains(where: { !$0.timelineAligned }) {
            return .timelineMisaligned
        }
        return .none
    }

    private static func gateStatus(for failureReason: LocalRecordingFailureReason) -> CaptureHealthGateStatus {
        switch failureReason {
        case .none:
            .passed
        case .permissionDenied, .scopeUnavailable, .protectedAudioBlocked:
            .blocked
        case .directoryUnavailable, .captureFailed, .writeFailed, .finalizationFailed,
             .timelineMisaligned, .cpuGateFailed, .deviceUnavailable,
             .appClosed:
            .failed
        case .emptyRequiredTrack, .formatNotReady, .silentInput, .noFrames,
             .stoppedBeforeFrames, .historicalPackage, .unknown:
            .degraded
        }
    }

    private static func isBlockedFailure(_ reason: LocalRecordingFailureReason) -> Bool {
        switch reason {
        case .permissionDenied, .scopeUnavailable, .protectedAudioBlocked:
            return true
        case .none, .directoryUnavailable, .writeFailed, .finalizationFailed,
             .emptyRequiredTrack, .formatNotReady, .timelineMisaligned,
             .silentInput, .noFrames, .captureFailed, .cpuGateFailed,
             .stoppedBeforeFrames, .deviceUnavailable,
             .historicalPackage, .appClosed, .unknown:
            return false
        }
    }

    private static func v5DurationDifferenceSeconds(tracks: [LocalRecordingTrack]) -> Double {
        guard let media = tracks.first(where: { $0.role == .mixedMeetingAudio }),
              let playback = tracks.first(where: { $0.role == .reviewPlayback })
        else {
            return 0
        }
        return Double(abs(media.durationMs - playback.durationMs)) / 1000
    }

}
