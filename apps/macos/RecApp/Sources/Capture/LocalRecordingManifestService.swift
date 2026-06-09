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

    public func manifest(
        sessionId: String,
        directoryId: String,
        startedAt: Date,
        stoppedAt: Date,
        tracks: [LocalRecordingTrack],
        failureReason: LocalRecordingFailureReason = .none,
        routeSessionId: String? = nil,
        autorepairAttemptIds: [String] = [],
        routeInterruptionCategory: RouteInterruptionCategory = .none,
        scopeApproval: CaptureScopeApproval? = nil,
        permissions: SystemAudioPermissionSnapshot? = nil,
        captureHealth: CaptureHealthSnapshot? = nil
    ) -> LocalRecordingManifest {
        let hasExactlyOneRequiredTrackPerRole =
            tracks.count == 2 &&
            tracks.filter { $0.role == .localMic }.count == 1 &&
            tracks.filter { $0.role == .remoteSpeaker }.count == 1
        let durationDifferenceSeconds = Self.durationDifferenceSeconds(tracks: tracks)
        let scopeAllowsAcceptedRecording = scopeApproval?.isAcceptedForMeetingRecording ?? false
        let permissionsAllowAcceptedRecording = permissions?.allowsAcceptedRecording ?? false
        let externallyFailed = failureReason != .none
        let complete = hasExactlyOneRequiredTrackPerRole &&
            tracks.allSatisfy(\.isMediaScribeReady) &&
            scopeAllowsAcceptedRecording &&
            permissionsAllowAcceptedRecording &&
            durationDifferenceSeconds <= 3 &&
            !externallyFailed
        let status: LocalRecordingSessionStatus = if complete {
            .saved
        } else if Self.isBlockedFailure(failureReason) {
            .blocked
        } else if Self.isFailedFailure(failureReason) {
            .failed
        } else if tracks.contains(where: { $0.status == .blocked }) {
            .blocked
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
            scopeApproval: scopeApproval,
            permissions: permissions,
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
            durationDifferenceSeconds: durationDifferenceSeconds,
            recordingTimelineEvidence: routeTimelineEvidence(
                routeSessionId: routeSessionId,
                tracks: tracks,
                autorepairAttemptIds: autorepairAttemptIds,
                interruptionCategory: routeInterruptionCategory
            ),
            scopeApproval: scopeApproval,
            permissions: permissions,
            captureHealth: captureHealth
        )
    }

    public func write(_ manifest: LocalRecordingManifest, to url: URL) throws {
        let data = try encoder.encode(manifest)
        try data.write(to: url, options: [.atomic])
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

    private static func resolveFailureReason(
        tracks: [LocalRecordingTrack],
        scopeApproval: CaptureScopeApproval?,
        permissions: SystemAudioPermissionSnapshot?,
        fallback: LocalRecordingFailureReason
    ) -> LocalRecordingFailureReason {
        if fallback != .none {
            return fallback
        }
        if let permissions, !permissions.allowsAcceptedRecording {
            return .permissionDenied
        }
        if permissions == nil, tracks.allSatisfy(\.isMediaScribeReady) {
            return .permissionDenied
        }
        if scopeApproval == nil, tracks.allSatisfy(\.isMediaScribeReady) {
            return .scopeUnavailable
        }
        if let trackReason = tracks.first(where: { $0.failureReason != .none })?.failureReason {
            return trackReason
        }
        if tracks.contains(where: { !$0.timelineAligned }) {
            return .timelineMisaligned
        }
        if tracks.contains(where: { $0.isComplete && !$0.isMediaScribeReady }) {
            return .formatNotReady
        }
        return .emptyRequiredTrack
    }

    private static func resolveCaptureHealthFailureReason(for manifest: LocalRecordingManifest) -> LocalRecordingFailureReason {
        if manifest.failureReason != .none {
            return manifest.failureReason
        }
        if let trackReason = manifest.tracks.first(where: { $0.failureReason != .none })?.failureReason {
            return trackReason
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
             .timelineMisaligned, .cpuGateFailed, .halProbeObserved, .deviceUnavailable,
             .appClosed:
            .failed
        case .emptyRequiredTrack, .formatNotReady, .silentInput, .noFrames,
             .stoppedBeforeFrames, .legacyNotReady, .unknown:
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
             .stoppedBeforeFrames, .halProbeObserved, .deviceUnavailable,
             .legacyNotReady, .appClosed, .unknown:
            return false
        }
    }

    private static func isFailedFailure(_ reason: LocalRecordingFailureReason) -> Bool {
        switch reason {
        case .directoryUnavailable, .writeFailed, .finalizationFailed, .captureFailed,
             .cpuGateFailed, .halProbeObserved, .deviceUnavailable, .appClosed:
            return true
        case .none, .emptyRequiredTrack, .formatNotReady, .timelineMisaligned,
             .permissionDenied, .scopeUnavailable, .protectedAudioBlocked,
             .silentInput, .noFrames, .stoppedBeforeFrames, .legacyNotReady,
             .unknown:
            return false
        }
    }

    private static func durationDifferenceSeconds(tracks: [LocalRecordingTrack]) -> Double {
        guard let mic = tracks.first(where: { $0.role == .localMic }),
              let incoming = tracks.first(where: { $0.role == .remoteSpeaker })
        else {
            return 0
        }
        return Double(abs(mic.durationMs - incoming.durationMs)) / 1000
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
