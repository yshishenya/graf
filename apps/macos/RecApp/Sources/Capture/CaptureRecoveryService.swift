import AVFoundation
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

public enum LocalRecordingRecoveryDisposition: String, Sendable {
    case ready
    case damaged
}

public struct LocalRecordingRecoveryOutcome: Equatable, Sendable {
    public let directoryId: String
    public let disposition: LocalRecordingRecoveryDisposition
    public let manifest: LocalRecordingManifest
}

public final class CaptureRecoveryService {
    public typealias Clock = @Sendable () -> Date

    private let clock: Clock

    public init(clock: @escaping Clock = Date.init) {
        self.clock = clock
    }

    public func recoverIncompleteRecordings(
        in rootURL: URL,
        manifestService: LocalRecordingManifestService = LocalRecordingManifestService()
    ) -> [LocalRecordingRecoveryOutcome] {
        let directories = (try? FileManager.default.contentsOfDirectory(
            at: rootURL,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        )) ?? []
        return directories.compactMap { directory in
            let manifestURL = directory.appendingPathComponent("manifest.json")
            guard let manifest = try? manifestService.read(from: manifestURL),
                  manifest.status == .active
            else {
                return nil
            }
            return recoverIncompleteRecording(
                manifest,
                directoryURL: directory,
                manifestURL: manifestURL,
                manifestService: manifestService
            )
        }
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

    private func recoverIncompleteRecording(
        _ activeManifest: LocalRecordingManifest,
        directoryURL: URL,
        manifestURL: URL,
        manifestService: LocalRecordingManifestService
    ) -> LocalRecordingRecoveryOutcome {
        do {
            let transcriptionURL = try recoverTranscriptionAudio(in: directoryURL)
            let reviewURL = try recoverReviewAudio(
                in: directoryURL,
                transcriptionURL: transcriptionURL
            )
            let tracks = try recoveredTracks(
                sessionId: activeManifest.sessionId,
                transcriptionURL: transcriptionURL,
                reviewURL: reviewURL
            )
            let recoveredDurationMs = tracks
                .first(where: { $0.role == .mixedMeetingAudio })?
                .durationMs ?? 0
            let stoppedAt = recoveredDurationMs > 0
                ? activeManifest.startedAt.addingTimeInterval(Double(recoveredDurationMs) / 1_000)
                : clock()
            let privacySegments = finalizedPrivacySegments(
                activeManifest.privacySegments ?? [],
                stoppedAt: stoppedAt,
                startedAt: activeManifest.startedAt
            )
            let manifest = manifestService.v5Manifest(
                sessionId: activeManifest.sessionId,
                directoryId: activeManifest.directoryId,
                startedAt: activeManifest.startedAt,
                stoppedAt: stoppedAt,
                tracks: tracks,
                scopeApproval: activeManifest.scopeApproval,
                permissions: activeManifest.permissions,
                microphoneSelection: activeManifest.microphoneSelection,
                privacySegments: privacySegments,
                targetMuteCapability: activeManifest.targetMuteCapability,
                meetingMuteTruthEvidence: activeManifest.meetingMuteTruthEvidence ?? [],
                limitationCopyShownAt: activeManifest.limitationCopyShownAt,
                captureFailureCode: "recording_recovered_after_interruption",
                echoProcessor: activeManifest.echoProcessor ?? .webrtcAEC3,
                echoProcessingHealth: EchoProcessingHealth(
                    state: .completed,
                    processedFrameCount: tracks.first(where: { $0.role == .reviewPlayback })?.frameCount ?? 0
                )
            )
            try manifestService.write(manifest, to: manifestURL)
            removeRecoveryPartials(in: directoryURL)
            return LocalRecordingRecoveryOutcome(
                directoryId: activeManifest.directoryId,
                disposition: .ready,
                manifest: manifest
            )
        } catch {
            let manifest = damagedManifest(from: activeManifest)
            try? manifestService.write(manifest, to: manifestURL)
            return LocalRecordingRecoveryOutcome(
                directoryId: activeManifest.directoryId,
                disposition: .damaged,
                manifest: manifest
            )
        }
    }

    private func recoverTranscriptionAudio(in directoryURL: URL) throws -> URL {
        let finalURL = directoryURL.appendingPathComponent("meeting-transcription.wav")
        let partialURL = directoryURL.appendingPathComponent("meeting-transcription.partial.wav")
        let candidate = FileManager.default.fileExists(atPath: finalURL.path) ? finalURL : partialURL
        let attributes = try FileManager.default.attributesOfItem(atPath: candidate.path)
        guard let size = (attributes[.size] as? NSNumber)?.uint64Value,
              size > 44
        else {
            throw CanonicalRecordingWriterError.noFrames
        }
        let dataByteCount = (size - 44) & ~UInt64(1)
        guard dataByteCount > 0, dataByteCount <= UInt64(UInt32.max) else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
        let handle = try FileHandle(forUpdating: candidate)
        defer { try? handle.close() }
        try handle.truncate(atOffset: 44 + dataByteCount)
        try handle.seek(toOffset: 0)
        try handle.write(contentsOf: CanonicalRecordingWriter.pcm16MonoWAVHeader(
            dataByteCount: UInt32(dataByteCount)
        ))
        try handle.synchronize()
        if candidate != finalURL {
            try? FileManager.default.removeItem(at: finalURL)
            try FileManager.default.moveItem(at: candidate, to: finalURL)
        }
        try LocalCustodyFileProtection.apply(to: finalURL)
        guard let file = try? AVAudioFile(forReading: finalURL), file.length > 0 else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
        return finalURL
    }

    private func recoverReviewAudio(in directoryURL: URL, transcriptionURL: URL) throws -> URL {
        let finalURL = directoryURL.appendingPathComponent("meeting-review.m4a")
        let partialURL = directoryURL.appendingPathComponent("meeting-review.partial.m4a")
        if Self.isValidReviewAudio(finalURL, matching: transcriptionURL) {
            return finalURL
        }
        if Self.isValidReviewAudio(partialURL, matching: transcriptionURL) {
            try? FileManager.default.removeItem(at: finalURL)
            try FileManager.default.moveItem(at: partialURL, to: finalURL)
            try LocalCustodyFileProtection.apply(to: finalURL)
            return finalURL
        }
        try? FileManager.default.removeItem(at: finalURL)
        _ = try CanonicalRecordingWriter.rebuildReviewAudio(
            from: transcriptionURL,
            to: finalURL
        )
        guard Self.isValidReviewAudio(finalURL) else {
            throw CanonicalRecordingWriterError.finalizationFailed
        }
        return finalURL
    }

    private func recoveredTracks(
        sessionId: String,
        transcriptionURL: URL,
        reviewURL: URL
    ) throws -> [LocalRecordingTrack] {
        let transcription = try AVAudioFile(forReading: transcriptionURL)
        let review = try AVAudioFile(forReading: reviewURL)
        let transcriptionFrames = transcription.length
        let reviewFrames = review.length
        let transcriptionBytes = try Self.fileSize(transcriptionURL)
        let reviewBytes = try Self.fileSize(reviewURL)
        let durationMs = Int(Double(transcriptionFrames) / transcription.fileFormat.sampleRate * 1_000)
        return [
            LocalRecordingTrack(
                trackId: "\(sessionId)-canonical-media",
                role: .mixedMeetingAudio,
                sourceKind: .canonicalMix,
                mediaScribeField: .mediaFile,
                status: .saved,
                fileName: transcriptionURL.lastPathComponent,
                format: "wav-pcm-s16le",
                sampleRate: transcription.fileFormat.sampleRate,
                channelCount: Int(transcription.fileFormat.channelCount),
                bitsPerSample: 16,
                durationMs: durationMs,
                byteCount: transcriptionBytes,
                sha256: try LocalRecordingWriter.sha256(of: transcriptionURL),
                frameCount: transcriptionFrames,
                timelineAligned: true
            ),
            LocalRecordingTrack(
                trackId: "\(sessionId)-review-playback",
                role: .reviewPlayback,
                sourceKind: .canonicalMix,
                mediaScribeField: .playbackFile,
                status: .saved,
                fileName: reviewURL.lastPathComponent,
                format: "m4a-aac-lc",
                sampleRate: review.fileFormat.sampleRate,
                channelCount: Int(review.fileFormat.channelCount),
                durationMs: Int(Double(reviewFrames) / review.fileFormat.sampleRate * 1_000),
                byteCount: reviewBytes,
                sha256: try LocalRecordingWriter.sha256(of: reviewURL),
                frameCount: reviewFrames,
                aacPresentationFrameDelta: reviewFrames - (transcriptionFrames * 3),
                timelineAligned: true
            )
        ]
    }

    private func damagedManifest(from active: LocalRecordingManifest) -> LocalRecordingManifest {
        var manifest = active
        let stoppedAt = clock()
        manifest.stoppedAt = stoppedAt
        manifest.finalizedAt = stoppedAt
        manifest.status = .failed
        manifest.transcriptionReadiness = .failed
        manifest.failureReason = .finalizationFailed
        manifest.captureFailureCode = "recording_recovery_not_possible"
        manifest.tracks = manifest.tracks.map { track in
            var failed = track
            failed.status = .failed
            failed.failureReason = .finalizationFailed
            return failed
        }
        manifest.echoProcessingHealth = EchoProcessingHealth(
            state: .failed,
            reason: .finalizationFailed
        )
        return manifest
    }

    private func removeRecoveryPartials(in directoryURL: URL) {
        for name in ["meeting-transcription.partial.wav", "meeting-review.partial.m4a"] {
            try? FileManager.default.removeItem(at: directoryURL.appendingPathComponent(name))
        }
    }

    private func finalizedPrivacySegments(
        _ segments: [ProductPrivacySegment],
        stoppedAt: Date,
        startedAt: Date
    ) -> [ProductPrivacySegment] {
        let endMonotonicMs = Int(max(0, stoppedAt.timeIntervalSince(startedAt) * 1_000))
        return segments.map { segment in
            guard segment.endedAt == nil else { return segment }
            return segment.finalized(
                endedAt: stoppedAt,
                endMonotonicMs: max(segment.startMonotonicMs, endMonotonicMs),
                treatment: .silenced
            )
        }
    }

    private static func isValidReviewAudio(_ url: URL, matching transcriptionURL: URL? = nil) -> Bool {
        guard let file = try? AVAudioFile(forReading: url) else { return false }
        guard file.length > 0 &&
            Int(file.fileFormat.sampleRate.rounded()) == Int(CanonicalRecordingWriter.canonicalSampleRate) &&
            file.fileFormat.channelCount == 1 &&
            (file.fileFormat.settings[AVFormatIDKey] as? NSNumber)?.intValue == Int(kAudioFormatMPEG4AAC)
        else { return false }
        guard let transcriptionURL,
              let transcription = try? AVAudioFile(forReading: transcriptionURL)
        else { return true }
        let reviewDuration = Double(file.length) / file.fileFormat.sampleRate
        let transcriptionDuration = Double(transcription.length) / transcription.fileFormat.sampleRate
        return abs(reviewDuration - transcriptionDuration) <= 0.1
    }

    private static func fileSize(_ url: URL) throws -> Int64 {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        return (attributes[.size] as? NSNumber)?.int64Value ?? 0
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
